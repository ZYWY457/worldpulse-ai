import hashlib
import logging
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

from db.database import Database

logger = logging.getLogger(__name__)


class StaticPageCollector:
    def __init__(self, db: Database, sources_path="data/sources.yaml", timeout=12, task_control=None):
        self.db = db
        self.sources_path = sources_path
        self.timeout = timeout
        self.task_control = task_control
        self.headers = {
            "User-Agent": "WorldPulseAI/0.1 (+https://localhost; public page monitor)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def load_sources(self):
        try:
            with open(self.sources_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                return config.get("crawler_static", [])
        except Exception as e:
            logger.error(f"Failed to load static page sources: {e}")
            return []

    def collect(self):
        sources = [source for source in self.load_sources() if source.get("enabled", True)]
        total_new = 0
        for source in sources:
            if self._is_cancelled():
                logger.info("Static page collection cancelled.")
                break
            events = self._fetch_source(source)
            for event in events:
                if self._is_cancelled():
                    break
                if self.db.save_event(event):
                    total_new += 1
            logger.info(f"Collected {len(events)} parsed items from {source.get('name')}.")
        logger.info(f"Static page collection finished. Added {total_new} new events.")
        return total_new

    def _fetch_source(self, source):
        url = source.get("url")
        if not url:
            return []
        if self._should_skip_source(source, "crawler_static"):
            logger.info(f"Skipping static source within crawl interval: {source.get('name')}")
            return []
        started = time.perf_counter()
        try:
            response = requests.get(url, headers=self.headers, timeout=source.get("timeout_seconds", self.timeout))
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.warning(f"Static source timed out and was skipped: {source.get('name')}")
            self.db.record_source_health({
                "source_name": source.get("name"),
                "source_type": "crawler_static",
                "endpoint": url,
                "status": "timeout",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": "timeout",
            })
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"Static source request failed and was skipped: {source.get('name')}: {e}")
            self.db.record_source_health({
                "source_name": source.get("name"),
                "source_type": "crawler_static",
                "endpoint": url,
                "status": "request_error",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error_message": str(e),
            })
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = self._select_items(soup, source)
        max_items = int(source.get("max_items", 20))
        events = []
        seen_urls = set()
        for item in items[: max_items * 3]:
            parsed = self._parse_item(item, source, url)
            if not parsed or parsed["url"] in seen_urls:
                continue
            if not self._is_quality_signal(parsed, source):
                continue
            seen_urls.add(parsed["url"])
            events.append(parsed)
            if len(events) >= max_items:
                break
        self.db.record_source_health({
            "source_name": source.get("name"),
            "source_type": "crawler_static",
            "endpoint": url,
            "status": "ok",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "http_code": response.status_code,
            "fetched_count": len(items),
            "accepted_count": len(events),
        })
        return events

    def _select_items(self, soup, source):
        item_selector = source.get("item_selector")
        if item_selector:
            selected = soup.select(item_selector)
            if selected:
                return selected
        return soup.select("article, li, .views-row, .news-item, .item, .card, tr")

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

    def _parse_item(self, item, source, base_url):
        link_el = self._first_selected(item, source.get("link_selector") or "a[href]")
        if not link_el or not link_el.get("href"):
            return None
        link = urljoin(base_url, link_el.get("href"))
        title_el = self._first_selected(item, source.get("title_selector") or "h1, h2, h3, h4, a[href]")
        title = self._clean_text(title_el.get_text(" ", strip=True) if title_el else link_el.get_text(" ", strip=True))
        if not title or len(title) < 8:
            return None

        summary_el = self._first_selected(item, source.get("summary_selector") or "p, .summary, .description, .teaser")
        date_el = self._first_selected(item, source.get("date_selector") or "time, .date, .published, .posted")
        raw_summary = self._clean_text(summary_el.get_text(" ", strip=True) if summary_el else "")
        published_at = self._parse_date(date_el, source)
        event_id = hashlib.md5(link.encode()).hexdigest()
        industry_tags = source.get("industry_tags") or []
        source_pack = source.get("source_pack")
        if source_pack and source_pack not in industry_tags:
            industry_tags = [*industry_tags, source_pack]

        return {
            "id": event_id,
            "title": title,
            "url": link,
            "source": source.get("name") or base_url,
            "source_type": "crawler_static",
            "source_weight": source.get("source_weight", 0.82),
            "published_at": published_at,
            "raw_summary": raw_summary,
            "raw_content": self._clean_text(item.get_text(" ", strip=True))[:3000],
            "category": source.get("category", "other"),
            "industry_tags": industry_tags,
        }

    def _is_quality_signal(self, event, source):
        title = str(event.get("title") or "").strip()
        summary = str(event.get("raw_summary") or "").strip()
        full_text = f"{title} {summary}".lower()

        if len(title) < 12:
            return False
        if title.lower() in {"home", "news", "latest", "read more", "important information"}:
            return False
        junk_phrases = ["cookie", "privacy policy", "sign in", "subscribe", "javascript", "menu"]
        if any(phrase in full_text for phrase in junk_phrases):
            return False

        include_keywords = source.get("include_keywords") or []
        if include_keywords:
            if not any(str(keyword).lower() in full_text for keyword in include_keywords):
                return False

        exclude_keywords = source.get("exclude_keywords") or []
        if exclude_keywords and any(str(keyword).lower() in full_text for keyword in exclude_keywords):
            return False

        category_keywords = {
            "tariff_policy": ["tariff", "duty", "trade act", "customs", "import"],
            "customs_clearance": ["customs", "clearance", "inspection", "border", "entry"],
            "sanctions_conflict": ["sanction", "blocked", "designation", "conflict", "export control"],
            "logistics_delay": ["delay", "service alert", "disruption", "delivery", "transit", "port"],
            "port_disruption": ["port", "vessel", "shipping", "congestion", "route", "suez"],
            "platform_policy": ["seller", "policy", "compliance", "marketplace", "listing", "shop"],
            "compliance": ["compliance", "regulation", "safety", "recall", "enforcement"],
        }
        category = str(source.get("category") or "")
        expected = category_keywords.get(category, [])
        if expected and not any(keyword in full_text for keyword in expected):
            return False

        return True

    def _first_selected(self, item, selector):
        if not selector:
            return None
        for part in str(selector).split(","):
            selected = item.select_one(part.strip())
            if selected:
                return selected
        return None

    def _parse_date(self, date_el, source):
        if date_el:
            value = date_el.get("datetime") or date_el.get("content") or date_el.get_text(" ", strip=True)
            if value:
                parsed = self._try_parse_date(value)
                if parsed:
                    return parsed
        return datetime.now().isoformat()

    def _try_parse_date(self, value):
        text = str(value).strip()
        candidates = [
            text,
            text.replace("Z", "+00:00"),
            text[:10],
        ]
        for candidate in candidates:
            try:
                return datetime.fromisoformat(candidate).isoformat()
            except ValueError:
                continue
        return None

    def _clean_text(self, value):
        return " ".join(str(value or "").split())

    def _is_cancelled(self):
        return bool(self.task_control and self.task_control.is_cancelled())


if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = StaticPageCollector(db)
    print(f"Collected {collector.collect()} static page items.")
