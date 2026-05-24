import json
import os
import sys
from datetime import datetime, timedelta

if __package__ in {None, ""}:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import Database


DEMO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo_events.json")


def database_has_events(db: Database) -> bool:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        return int(cursor.fetchone()[0]) > 0


def database_has_demo_events(db: Database) -> bool:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE source_type = 'demo' OR source IN ('Demo Source', 'Trade Brief Demo', 'Logistics Demo', 'Supply Chain Demo', 'Market Demo')")
        return int(cursor.fetchone()[0]) > 0


def has_corrupted_demo_text(event: dict) -> bool:
    text_fields = [
        "title",
        "raw_summary",
        "ai_summary",
        "business_impact",
        "market_impact",
        "opportunity_signal",
        "suggested_action",
        "content_angle",
        "social_angle",
    ]
    values = [str(event.get(field) or "") for field in text_fields]
    if isinstance(event.get("affected_groups"), list):
        values.extend(str(item) for item in event["affected_groups"])
    return any("????" in value for value in values)


def load_demo_events(db: Database, force: bool = False) -> int:
    if not force and database_has_events(db):
        return 0

    with open(DEMO_PATH, "r", encoding="utf-8") as f:
        events = json.load(f)

    now = datetime.now()
    inserted = 0
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if force:
            cursor.execute("DELETE FROM events WHERE source_type = 'demo' OR url LIKE 'https://example.com/demo/%'")
        for index, event in enumerate(events):
            if has_corrupted_demo_text(event):
                continue
            item = dict(event)
            item["published_at"] = (now - timedelta(hours=index)).isoformat()
            item.setdefault("source_type", "demo")
            item.setdefault("source_weight", 0.65)
            item.setdefault("status", "analyzed")
            item.setdefault("created_at", now.isoformat())
            item.setdefault("updated_at", now.isoformat())
            item.setdefault("confidence", 0.78)
            item.setdefault("location_scope", "specific")
            item.setdefault("location_confidence", 0.9)
            item.setdefault("location_reason", "Demo event coordinates")
            item.setdefault("industry", None)
            item.setdefault("market_impact", "")
            item.setdefault("opportunity_signal", "")
            item.setdefault("content_angle", item.get("social_angle") or "")
            if isinstance(item.get("affected_groups"), list):
                item["affected_groups"] = json.dumps(item["affected_groups"], ensure_ascii=False)
            if isinstance(item.get("industry_tags"), list):
                item["industry_tags"] = json.dumps(item["industry_tags"], ensure_ascii=False)

            cursor.execute(
                """
                INSERT OR REPLACE INTO events (
                    id, title, url, source, source_type, source_weight, published_at,
                    raw_summary, raw_content, ai_summary, category, country, city,
                    location_scope, location_confidence, location_reason, lat, lon,
                    severity, confidence, risk_level, industry, industry_tags, affected_groups,
                    business_impact, market_impact, opportunity_signal, suggested_action,
                    content_angle, social_angle, status, created_at, updated_at
                )
                VALUES (
                    :id, :title, :url, :source, :source_type, :source_weight, :published_at,
                    :raw_summary, :raw_content, :ai_summary, :category, :country, :city,
                    :location_scope, :location_confidence, :location_reason, :lat, :lon,
                    :severity, :confidence, :risk_level, :industry, :industry_tags, :affected_groups,
                    :business_impact, :market_impact, :opportunity_signal, :suggested_action,
                    :content_angle, :social_angle, :status, :created_at, :updated_at
                )
                """,
                item,
            )
            inserted += cursor.rowcount
        conn.commit()
    return inserted


def load_demo_if_empty(db: Database) -> int:
    return load_demo_events(db, force=True)


if __name__ == "__main__":
    count = load_demo_events(Database("storage/worldpulse.db"), force=False)
    print(f"Demo events loaded: {count}")
