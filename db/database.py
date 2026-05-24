import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="storage/worldpulse.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT UNIQUE,
                    source TEXT,
                    source_type TEXT,
                    source_weight REAL,
                    published_at DATETIME,
                    raw_summary TEXT,
                    raw_content TEXT,
                    ai_summary TEXT,
                    category TEXT,
                    country TEXT,
                    city TEXT,
                    location_scope TEXT,
                    location_confidence REAL,
                    location_reason TEXT,
                    lat REAL,
                    lon REAL,
                    severity INTEGER,
                    confidence REAL,
                    risk_level TEXT,
                    industry TEXT,
                    industry_tags TEXT,
                    affected_groups TEXT,
                    business_impact TEXT,
                    market_impact TEXT,
                    opportunity_signal TEXT,
                    suggested_action TEXT,
                    content_angle TEXT,
                    social_angle TEXT,
                    status TEXT DEFAULT 'raw',
                    created_at DATETIME,
                    updated_at DATETIME
                )
            ''')
            self._ensure_column(cursor, "events", "source_weight", "REAL")
            self._ensure_column(cursor, "events", "location_scope", "TEXT")
            self._ensure_column(cursor, "events", "location_confidence", "REAL")
            self._ensure_column(cursor, "events", "location_reason", "TEXT")
            self._ensure_column(cursor, "events", "cluster_id", "TEXT")
            self._ensure_column(cursor, "events", "industry", "TEXT")
            self._ensure_column(cursor, "events", "industry_tags", "TEXT")
            self._ensure_column(cursor, "events", "affected_groups", "TEXT")
            self._ensure_column(cursor, "events", "business_impact", "TEXT")
            self._ensure_column(cursor, "events", "market_impact", "TEXT")
            self._ensure_column(cursor, "events", "opportunity_signal", "TEXT")
            self._ensure_column(cursor, "events", "suggested_action", "TEXT")
            self._ensure_column(cursor, "events", "content_angle", "TEXT")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_clusters (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT,
                    source TEXT,
                    category TEXT,
                    country TEXT,
                    city TEXT,
                    lat REAL,
                    lon REAL,
                    severity INTEGER,
                    risk_level TEXT,
                    risk_score REAL,
                    event_count INTEGER,
                    source_count INTEGER,
                    gdelt_count INTEGER,
                    rss_count INTEGER,
                    source_weight_sum REAL,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    summary TEXT,
                    updated_at DATETIME
                )
            ''')
            self._ensure_column(cursor, "event_clusters", "url", "TEXT")
            self._ensure_column(cursor, "event_clusters", "source", "TEXT")
            # Geocode cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    location_name TEXT PRIMARY KEY,
                    country TEXT,
                    city TEXT,
                    lat REAL,
                    lon REAL,
                    created_at DATETIME
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS source_health (
                    id TEXT PRIMARY KEY,
                    source_name TEXT,
                    source_type TEXT,
                    endpoint TEXT,
                    status TEXT,
                    latency_ms INTEGER,
                    http_code INTEGER,
                    fetched_count INTEGER,
                    accepted_count INTEGER,
                    error_message TEXT,
                    updated_at DATETIME
                )
            ''')
            conn.commit()

    def _ensure_column(self, cursor, table_name, column_name, column_type):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def save_event(self, event_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Check if exists
            cursor.execute("SELECT id FROM events WHERE url = ?", (event_data['url'],))
            if cursor.fetchone():
                return False
            
            industry_tags = event_data.get('industry_tags')
            if isinstance(industry_tags, list):
                import json
                industry_tags = json.dumps(industry_tags, ensure_ascii=False)

            fields = [
                'id', 'title', 'url', 'source', 'source_type', 'source_weight', 'published_at',
                'raw_summary', 'raw_content', 'category', 'industry_tags', 'status', 'created_at', 'updated_at'
            ]
            placeholders = ', '.join(['?'] * len(fields))
            values = [
                event_data.get('id'),
                event_data.get('title'),
                event_data.get('url'),
                event_data.get('source'),
                event_data.get('source_type', 'rss'),
                event_data.get('source_weight', 0.7),
                event_data.get('published_at'),
                event_data.get('raw_summary'),
                event_data.get('raw_content'),
                event_data.get('category'),
                industry_tags,
                'raw',
                now,
                now
            ]
            
            cursor.execute(f"INSERT INTO events ({', '.join(fields)}) VALUES ({placeholders})", values)
            conn.commit()
            return True

    def get_unanalyzed_events(self, limit=10):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE status = 'raw' ORDER BY published_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_unmapped_events(self, limit=50):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events
                WHERE status = 'raw'
                  AND lat IS NULL
                  AND lon IS NULL
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_event(self, event_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_event_fields(self, event_id, field_data, status=None):
        allowed_fields = {
            'ai_summary', 'category', 'country', 'city', 'location_scope',
            'location_confidence', 'location_reason', 'lat', 'lon', 'severity',
            'confidence', 'risk_level', 'social_angle', 'cluster_id',
            'industry', 'industry_tags', 'affected_groups', 'business_impact',
            'market_impact', 'opportunity_signal', 'suggested_action', 'content_angle'
        }
        updates = {k: v for k, v in field_data.items() if k in allowed_fields}
        if not updates and status is None:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            update_fields = []
            values = []
            for key, value in updates.items():
                update_fields.append(f"{key} = ?")
                values.append(value)
            update_fields.append("updated_at = ?")
            values.append(now)
            if status is not None:
                update_fields.append("status = ?")
                values.append(status)
            values.append(event_id)
            cursor.execute(f"UPDATE events SET {', '.join(update_fields)} WHERE id = ?", values)
            conn.commit()

    def update_event_analysis(self, event_id, analysis_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            update_fields = []
            values = []
            for k, v in analysis_data.items():
                update_fields.append(f"{k} = ?")
                values.append(v)
            
            update_fields.append("updated_at = ?")
            values.append(now)
            update_fields.append("status = ?")
            values.append('analyzed' if analysis_data.get('ai_summary') else 'failed')
            
            values.append(event_id)
            
            query = f"UPDATE events SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

    def get_geocode(self, location_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM geocode_cache WHERE location_name = ?", (location_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_geocode(self, geocode_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO geocode_cache (location_name, country, city, lat, lon, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                geocode_data['location_name'],
                geocode_data.get('country'),
                geocode_data.get('city'),
                geocode_data.get('lat'),
                geocode_data.get('lon'),
                now
            ))
            conn.commit()

    def record_source_health(self, item):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            source_name = item.get("source_name") or ""
            source_type = item.get("source_type") or "unknown"
            endpoint = item.get("endpoint") or ""
            key = f"{source_type}:{source_name}:{endpoint}"
            import hashlib
            row_id = hashlib.md5(key.encode()).hexdigest()
            cursor.execute(
                '''
                INSERT OR REPLACE INTO source_health
                (id, source_name, source_type, endpoint, status, latency_ms, http_code, fetched_count, accepted_count, error_message, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    row_id,
                    source_name,
                    source_type,
                    endpoint,
                    item.get("status", "unknown"),
                    item.get("latency_ms"),
                    item.get("http_code"),
                    item.get("fetched_count", 0),
                    item.get("accepted_count", 0),
                    item.get("error_message"),
                    now,
                ),
            )
            conn.commit()
