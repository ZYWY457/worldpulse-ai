import hashlib
import logging
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
        for query_config in queries:
            if self._is_cancelled():
                logger.info("GDELT collection cancelled.")
                break
            query = query_config.get("query")
            if not query:
                continue

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
                seen_urls.add(url)

                event_data = self._article_to_event(article, category, config.get("source_weight", 0.55))
                if self.db.save_event(event_data):
                    total_new += 1

            logger.info(f"GDELT query '{query}' returned {len(articles)} articles.")

        logger.info(f"GDELT collection finished. Added {total_new} new events.")
        return total_new

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
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
            return articles if isinstance(articles, list) else []
        except requests.exceptions.Timeout:
            logger.warning(f"GDELT query timed out and was skipped: {query}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"GDELT query failed and was skipped: {query}: {e}")
        except ValueError as e:
            logger.warning(f"GDELT returned invalid JSON for query '{query}': {e}")
        except Exception as e:
            logger.error(f"Unexpected GDELT collection error for query '{query}': {e}")

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
        raw_summary = f"Language: {language}. Source country: {source_country}. Domain: {domain}."

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
