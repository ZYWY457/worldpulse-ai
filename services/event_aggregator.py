import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timedelta

from db.database import Database


class EventAggregator:
    def __init__(self, db: Database):
        self.db = db
        self.stop_words = {
            "the", "and", "for", "with", "from", "that", "this", "after", "over", "into",
            "about", "against", "amid", "says", "said", "will", "new", "news", "live",
            "update", "updates", "report", "reports", "world", "global",
        }

    def rebuild_recent_clusters(self, hours=72):
        events = self._load_recent_analyzed_events(hours)
        clusters = self._build_clusters(events)
        self._save_clusters(clusters)
        return len(clusters)

    def _load_recent_analyzed_events(self, hours):
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events
                WHERE status = 'analyzed'
                  AND published_at >= ?
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                ORDER BY published_at DESC
                """,
                (since,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _build_clusters(self, events):
        buckets = {}
        for event in events:
            key = self._cluster_key(event)
            buckets.setdefault(key, []).append(event)

        return [self._summarize_cluster(key, group) for key, group in buckets.items()]

    def _cluster_key(self, event):
        day = str(event.get("published_at") or "")[:10]
        country = self._clean_key(event.get("country") or "unknown")
        city = self._clean_key(event.get("city") or "")
        category = self._clean_key(event.get("category") or "other")
        title_key = "-".join(self._title_keywords(event.get("title") or "")[:4])
        location_key = city or country
        raw_key = f"{day}|{country}|{location_key}|{category}|{title_key}"
        return hashlib.md5(raw_key.encode()).hexdigest()

    def _title_keywords(self, title):
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", title.lower())
        filtered = [word for word in words if word not in self.stop_words]
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(6)]

    def _clean_key(self, value):
        return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")

    def _summarize_cluster(self, cluster_id, events):
        events = sorted(events, key=lambda e: e.get("published_at") or "", reverse=True)
        representative = max(events, key=lambda e: (float(e.get("source_weight") or 0), int(e.get("severity") or 1)))
        sources = {event.get("source") for event in events if event.get("source")}
        gdelt_count = sum(1 for event in events if event.get("source_type") == "gdelt")
        rss_count = sum(1 for event in events if event.get("source_type") == "rss")
        source_weight_sum = sum(float(event.get("source_weight") or 0.5) for event in events)
        severity = max(int(event.get("severity") or 1) for event in events)
        risk_score = self._risk_score(events, severity, source_weight_sum, len(sources), gdelt_count, rss_count)

        return {
            "id": cluster_id,
            "title": representative.get("title") or "Untitled event",
            "url": representative.get("url"),
            "source": representative.get("source"),
            "category": representative.get("category") or "other",
            "country": representative.get("country"),
            "city": representative.get("city"),
            "lat": representative.get("lat"),
            "lon": representative.get("lon"),
            "severity": severity,
            "risk_level": self._risk_level(risk_score),
            "risk_score": risk_score,
            "event_count": len(events),
            "source_count": len(sources),
            "gdelt_count": gdelt_count,
            "rss_count": rss_count,
            "source_weight_sum": source_weight_sum,
            "first_seen": min(event.get("published_at") or "" for event in events),
            "last_seen": max(event.get("published_at") or "" for event in events),
            "summary": representative.get("ai_summary") or representative.get("raw_summary") or "",
            "events": events,
        }

    def _risk_score(self, events, severity, source_weight_sum, source_count, gdelt_count, rss_count):
        base = severity * 16
        source_diversity = min(18, source_count * 4)
        source_trust = min(18, source_weight_sum * 3)
        gdelt_skeleton = min(10, math.log1p(gdelt_count) * 4)
        rss_validation = min(16, rss_count * 4)
        category_boost = 8 if any((event.get("category") or "").lower() in {"sanctions_conflict", "port_disruption", "customs_clearance", "tariff_policy"} for event in events) else 0
        return round(min(100, base + source_diversity + source_trust + gdelt_skeleton + rss_validation + category_boost), 2)

    def _risk_level(self, risk_score):
        if risk_score >= 85:
            return "critical"
        if risk_score >= 65:
            return "high"
        if risk_score >= 40:
            return "medium"
        return "low"

    def _save_clusters(self, clusters):
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM event_clusters")
            for cluster in clusters:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO event_clusters (
                        id, title, url, source, category, country, city, lat, lon, severity, risk_level,
                        risk_score, event_count, source_count, gdelt_count, rss_count,
                        source_weight_sum, first_seen, last_seen, summary, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cluster["id"], cluster["title"], cluster["url"], cluster["source"],
                        cluster["category"], cluster["country"], cluster["city"],
                        cluster["lat"], cluster["lon"], cluster["severity"], cluster["risk_level"],
                        cluster["risk_score"], cluster["event_count"], cluster["source_count"],
                        cluster["gdelt_count"], cluster["rss_count"], cluster["source_weight_sum"],
                        cluster["first_seen"], cluster["last_seen"], cluster["summary"], now,
                    ),
                )
                cursor.executemany(
                    "UPDATE events SET cluster_id = ? WHERE id = ?",
                    [(cluster["id"], event["id"]) for event in cluster["events"]],
                )
            conn.commit()
