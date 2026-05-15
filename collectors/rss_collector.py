import feedparser
import yaml
import hashlib
import logging
import requests
from datetime import datetime
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
            with open(self.sources_path, 'r') as f:
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
        timeout = source.get('timeout_seconds', self.timeout)
        max_items = int(source.get('max_items', 30))
        logger.info(f"Collecting from {name}: {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, 'bozo', False):
                logger.warning(f"Feed parse warning for {name}: {getattr(feed, 'bozo_exception', 'unknown')}")
            return source, list(feed.entries[:max_items])
        except requests.exceptions.Timeout:
            logger.warning(f"RSS source timed out and was skipped: {name}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"RSS source returned HTTP error and was skipped: {name} ({e.response.status_code})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"RSS source request failed and was skipped: {name}: {e}")
        except Exception as e:
            logger.error(f"Error collecting from {name}: {e}")

        return source, []

    def _is_cancelled(self):
        return bool(self.task_control and self.task_control.is_cancelled())

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

        return {
            'id': event_id,
            'title': entry.get('title', 'No Title'),
            'url': entry_url,
            'source': name,
            'source_type': 'rss',
            'source_weight': source.get('source_weight', 0.75),
            'published_at': published_at,
            'raw_summary': entry.get('summary', '') or entry.get('description', ''),
            'category': source.get('category'),
        }

if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = RSSCollector(db)
    collector.collect()
