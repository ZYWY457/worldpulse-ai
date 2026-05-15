import requests
import hashlib
import logging
import sqlite3
from datetime import datetime
from db.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHotCollector:
    """
    从 AI HOT (aihot.virxact.com) 采集 AI 行业资讯。
    数据直接标记为 analyzed 状态，因为 API 已提供中文摘要。
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.api_base = "https://aihot.virxact.com/api/public"
    
    def fetch_items(self, mode: str = "selected", take: int = 30) -> list[dict]:
        """
        从 AI HOT API 获取资讯条目。

        Args:
            mode: "selected" (精选) 或 "daily" (每日)
            take: 获取数量 (默认 30)

        Returns:
            资讯条目列表
        """
        url = f"{self.api_base}/items?mode={mode}&take={take}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # API 返回格式：{count, hasNext, nextCursor, items: [...]}
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected API response format: {type(data)}")
                return []

        except requests.exceptions.Timeout:
            logger.error("AI HOT API request timed out")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch from AI HOT: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing AI HOT response: {e}")
            return []
    
    def collect(self, mode: str = "selected", take: int = 30) -> int:
        """
        采集 AI 资讯并保存到数据库。
        
        Args:
            mode: 采集模式 ("selected" 或 "daily")
            take: 获取数量
        
        Returns:
            新增条目数量
        """
        items = self.fetch_items(mode=mode, take=take)
        total_new = 0
        
        for item in items:
            # 提取字段（根据 AI HOT API 返回格式）
            # API 字段：id, title, title_en, url, source, publishedAt, summary, category
            title = item.get("title", "No Title")
            summary = item.get("summary", "")
            url = item.get("url", "")
            source = item.get("source", "AI HOT")
            published_at = item.get("publishedAt", item.get("published_at", datetime.now().isoformat()))
            category = item.get("category", "artificial_intelligence")
            
            # 如果没有 URL，用标题 + 时间生成唯一 ID
            if not url:
                url = f"aihot://{hashlib.md5(title.encode()).hexdigest()}"
            
            event_id = hashlib.md5(url.encode()).hexdigest()
            
            # 标准化时间格式（AI HOT API 返回 ISO 8601 格式，如 "2026-05-11T12:36:49.000Z"）
            if isinstance(published_at, int):
                # Unix timestamp
                published_at = datetime.fromtimestamp(published_at).isoformat()
            elif isinstance(published_at, str):
                # ISO 8601 格式，移除毫秒和 Z 后缀以便 SQLite 存储
                try:
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    published_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            event_data = {
                'id': event_id,
                'title': title,
                'url': url,
                'source': source,
                'source_type': 'aihot',
                'category': category,  # 使用 API 返回的分类（如 "tip", "news", "model" 等）
                'published_at': published_at,
                'raw_summary': summary,
                'ai_summary': summary,  # 直接用 API 提供的摘要
                'status': 'analyzed',  # 跳过 AI 分析
                'risk_level': 'low',  # 默认低风险，可后续调整
                'severity': 1,
                'country': None,
                'city': None,
                'social_angle': None,
            }
            
            if self._save_analyzed_event(event_data):
                total_new += 1

        logger.info(f"AI HOT collection finished. Added {total_new} new events.")
        return total_new

    def _save_analyzed_event(self, event_data: dict) -> bool:
        """
        保存已分析的 AI 资讯事件（status='analyzed'）。
        因为 db.save_event() 默认设 status='raw'，这里需要自定义插入。
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Check if exists (by URL or ID)
            cursor.execute("SELECT id FROM events WHERE url = ? OR id = ?",
                          (event_data['url'], event_data['id']))
            if cursor.fetchone():
                return False

            fields = [
                'id', 'title', 'url', 'source', 'source_type', 'published_at',
                'raw_summary', 'ai_summary', 'category', 'status',
                'severity', 'risk_level', 'created_at', 'updated_at'
            ]
            placeholders = ', '.join(['?'] * len(fields))
            values = [
                event_data.get('id'),
                event_data.get('title'),
                event_data.get('url'),
                event_data.get('source'),
                event_data.get('source_type'),
                event_data.get('published_at'),
                event_data.get('raw_summary'),
                event_data.get('ai_summary'),
                event_data.get('category'),
                'analyzed',  # 直接标记为已分析
                event_data.get('severity', 1),
                event_data.get('risk_level', 'low'),
                now,
                now
            ]

            try:
                cursor.execute(f"INSERT INTO events ({', '.join(fields)}) VALUES ({placeholders})", values)
                conn.commit()
                return True
            except sqlite3.IntegrityError as e:
                logger.warning(f"Duplicate event skipped: {e}")
                return False
            except Exception as e:
                logger.error(f"Failed to save event: {e}")
                return False


if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = AIHotCollector(db)
    count = collector.collect()
    print(f"Collected {count} AI news items.")
