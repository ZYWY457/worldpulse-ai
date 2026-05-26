import hashlib
import logging
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
import yaml

from db.database import Database

logger = logging.getLogger(__name__)


class GDELTCollector:
    def __init__(self, db: Database, sources_path="data/sources.yaml", timeout=12, task_control=None):
        self.db = db
        self.sources_path = sources_path
        self.timeout = timeout
        self.task_control = task_control
        self.api_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.headers = {
            "User-Agent": "WorldPulseAI/0.1 (+https://localhost; GDELT intelligence monitor)",
            "Accept": "application/json",
        }

    def load_config(self):
        try:
            with open(self.sources_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                return config.get("gdelt", {})
        except Exception as e:
            logger.error(f"Failed to load GDELT config: {e}")
            return {}

    def collect(self):
        config = self.load_config()
        if not config.get("enabled", True):
            logger.info("GDELT collection is disabled.")
            return 0

        queries = config.get("queries", [])
        if not queries:
            logger.warning("No GDELT queries configured.")
            return 0

        total_new = 0
        seen_urls = set()
        self.rate_limited = False
        max_queries = int(config.get("max_queries_per_run", len(queries)))
        per_query_delay = float(config.get("per_query_delay_seconds", 0))
        for index, query_config in enumerate(queries[:max_queries]):
            if self._is_cancelled():
                logger.info("GDELT collection cancelled.")
                break
            if self.rate_limited:
                logger.info("GDELT collection paused because the API rate limit was reached.")
                break
            query = query_config.get("query")
            if not query:
                continue
            if index > 0 and per_query_delay > 0:
                time.sleep(per_query_delay)

            articles = self._fetch_articles(
                query=query,
                timespan=query_config.get("timespan", config.get("timespan", "24h")),
                max_records=int(query_config.get("max_records", config.get("max_records", 30))),
                sort=query_config.get("sort", config.get("sort", "datedesc")),
            )

            category = query_config.get("category", "world")
            for article in articles:
                if self._is_cancelled():
                    logger.info("GDELT collection cancelled while saving articles.")
                    break
                url = article.get("url")
                if not url or url in seen_urls:
                    continue
                if not self._is_quality_article(article):
                    continue
                seen_urls.add(url)

                event_data = self._article_to_event(article, category, config.get("source_weight", 0.55))
                if self.db.save_event(event_data):
                    total_new += 1

            logger.info(f"GDELT query '{query}' returned {len(articles)} articles.")
            if self.rate_limited:
                logger.info("Stopping remaining GDELT queries for this run after rate limit response.")
                break

        logger.info(f"GDELT collection finished. Added {total_new} new events.")
        return total_new

    def _is_quality_article(self, article):
        title = str(article.get("title") or "").strip()
        if len(title) < 18:
            return False
        lower = title.lower()
        junk_phrases = ["click here", "watch live", "sponsored", "photo gallery", "newsletter", "sign up"]
        if any(phrase in lower for phrase in junk_phrases):
            return False
        has_letters = any(ch.isalpha() for ch in title)
        if not has_letters:
            return False
        return True

    def _fetch_articles(self, query, timespan, max_records, sort):
        if self._is_cancelled():
            return []

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "timespan": timespan,
            "maxrecords": max_records,
            "sort": sort,
        }
        started = time.perf_counter()
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": "ok",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "http_code": response.status_code,
                "fetched_count": len(articles) if isinstance(articles, list) else 0,
                "accepted_count": len(articles) if isinstance(articles, list) else 0,
            })
            return articles if isinstance(articles, list) else []
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            status = "rate_limited" if status_code == 429 else "http_error"
            if status_code == 429:
                self.rate_limited = True
            logger.warning(f"GDELT query failed and was skipped: {query}: {e}")
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": status,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "http_code": status_code,
                "error_message": str(e),
            })
        except requests.exceptions.Timeout:
            logger.warning(f"GDELT query timed out and was skipped: {query}")
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": "timeout",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": "timeout",
            })
        except requests.exceptions.RequestException as e:
            logger.warning(f"GDELT query failed and was skipped: {query}: {e}")
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": "request_error",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })
        except ValueError as e:
            logger.warning(f"GDELT returned invalid JSON for query '{query}': {e}")
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": "invalid_json",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })
        except Exception as e:
            logger.exception("gdelt_collect_error", extra={"query": query})
            self.db.record_source_health({
                "source_name": f"GDELT:{query[:60]}",
                "source_type": "gdelt",
                "endpoint": self.api_url,
                "status": "exception",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })

        return []

    def _is_cancelled(self):
        return bool(self.task_control and self.task_control.is_cancelled())

    def _article_to_event(self, article, category, source_weight):
        url = article.get("url")
        event_id = hashlib.md5(url.encode()).hexdigest()
        domain = article.get("domain") or urlparse(url).netloc or "GDELT"
        language = article.get("language") or "Unknown"
        source_country = article.get("sourcecountry") or "Unknown"
        published_at = self._parse_seen_date(article.get("seendate"))
        raw_summary = f"Title from {domain}. Language={language}. SourceCountry={source_country}."

        return {
            "id": event_id,
            "title": article.get("title", "No Title"),
            "url": url,
            "source": f"GDELT / {domain}",
            "source_type": "gdelt",
            "source_weight": source_weight,
            "published_at": published_at,
            "raw_summary": raw_summary,
            "category": category,
        }

    def _parse_seen_date(self, value):
        if not value:
            return datetime.now().isoformat()
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").isoformat()
        except ValueError:
            return datetime.now().isoformat()


if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = GDELTCollector(db)
    print(f"Collected {collector.collect()} GDELT items.")
