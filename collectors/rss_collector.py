import feedparser
import yaml
import hashlib
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSCollector:
    def __init__(self, db: Database, sources_path="data/sources.yaml", max_workers=10, timeout=5, task_control=None):
        self.db = db
        self.sources_path = sources_path
        self.max_workers = max_workers
        self.timeout = timeout
        self.task_control = task_control
        self.headers = {
            "User-Agent": "WorldPulseAI/0.1 (+https://localhost; RSS intelligence monitor)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        }

    def load_sources(self):
        try:
            with open(self.sources_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('sources', [])
        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
            return []

    def collect(self):
        sources = [source for source in self.load_sources() if source.get('enabled', True)]
        total_new = 0

        if not sources:
            logger.warning("No enabled RSS sources configured.")
            return 0

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(sources))) as executor:
            futures = [executor.submit(self._fetch_source, source) for source in sources]
            for future in as_completed(futures):
                if self._is_cancelled():
                    logger.info("RSS collection cancelled.")
                    break
                source, entries = future.result()
                name = source.get('name')
                for entry in entries:
                    if self._is_cancelled():
                        logger.info("RSS collection cancelled while saving entries.")
                        break
                    event_data = self._entry_to_event(source, entry)
                    if event_data and self.db.save_event(event_data):
                        total_new += 1

                logger.info(f"Collected {len(entries)} parsed entries from {name}.")

        logger.info(f"Collection finished. Added {total_new} new events.")
        return total_new

    def _fetch_source(self, source):
        if self._is_cancelled():
            return source, []

        name = source.get('name')
        url = source.get('url')
        if self._should_skip_source(source, "rss"):
            logger.info(f"Skipping RSS source within crawl interval: {name}")
            return source, []
        timeout = source.get('timeout_seconds', self.timeout)
        max_items = int(source.get('max_items', 30))
        logger.info(f"Collecting from {name}: {url}")
        started = time.perf_counter()

        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, 'bozo', False):
                logger.warning(f"Feed parse warning for {name}: {getattr(feed, 'bozo_exception', 'unknown')}")
            entries = list(feed.entries[:max_items])
            self.db.record_source_health({
                "source_name": name,
                "source_type": "rss",
                "endpoint": url,
                "status": "ok",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "http_code": response.status_code,
                "fetched_count": len(entries),
                "accepted_count": len(entries),
            })
            return source, entries
        except requests.exceptions.Timeout:
            logger.warning(f"RSS source timed out and was skipped: {name}")
            self.db.record_source_health({
                "source_name": name,
                "source_type": "rss",
                "endpoint": url,
                "status": "timeout",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": "timeout",
            })
        except requests.exceptions.HTTPError as e:
            logger.warning(f"RSS source returned HTTP error and was skipped: {name} ({e.response.status_code})")
            self.db.record_source_health({
                "source_name": name,
                "source_type": "rss",
                "endpoint": url,
                "status": "http_error",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "http_code": e.response.status_code,
                "error_message": str(e),
            })
        except requests.exceptions.RequestException as e:
            logger.warning(f"RSS source request failed and was skipped: {name}: {e}")
            self.db.record_source_health({
                "source_name": name,
                "source_type": "rss",
                "endpoint": url,
                "status": "request_error",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })
        except Exception as e:
            logger.exception("rss_collect_error", extra={"source": name, "endpoint": url})
            self.db.record_source_health({
                "source_name": name,
                "source_type": "rss",
                "endpoint": url,
                "status": "exception",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })

        return source, []

    def _is_cancelled(self):
        return bool(self.task_control and self.task_control.is_cancelled())

    def _should_skip_source(self, source, source_type):
        interval = source.get("crawl_interval_minutes")
        if not interval:
            return False
        try:
            interval_minutes = int(interval)
        except (TypeError, ValueError):
            return False
        health = self.db.get_source_health(source_type, source.get("name"), source.get("url"))
        if not health or not health.get("updated_at"):
            return False
        try:
            updated_at = datetime.fromisoformat(str(health["updated_at"]))
        except ValueError:
            return False
        return datetime.now() - updated_at < timedelta(minutes=max(5, interval_minutes))

    def _entry_to_event(self, source, entry):
        name = source.get('name')
        entry_url = entry.get('link')
        if not entry_url:
            return None

        event_id = hashlib.md5(entry_url.encode()).hexdigest()

        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6]).isoformat()
            except (TypeError, ValueError):
                published_at = None
        if not published_at:
            published_at = datetime.now().isoformat()

        industry_tags = source.get('industry_tags') or []
        source_pack = source.get('source_pack')
        if source_pack and source_pack not in industry_tags:
            industry_tags = [*industry_tags, source_pack]

        return {
            'id': event_id,
            'title': entry.get('title', 'No Title'),
            'url': entry_url,
            'source': name,
            'source_type': 'rss',
            'source_weight': source.get('source_weight', 0.75),
            'published_at': published_at,
            'raw_summary': entry.get('summary', '') or entry.get('description', ''),
            'raw_content': entry.get('content', [{}])[0].get('value') if entry.get('content') else None,
            'category': source.get('category'),
            'industry_tags': json.dumps(industry_tags, ensure_ascii=False) if industry_tags else None,
        }

if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = RSSCollector(db)
    collector.collect()
