import feedparser
import yaml
import hashlib
import logging
from datetime import datetime
from db.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSCollector:
    def __init__(self, db: Database, sources_path="data/sources.yaml"):
        self.db = db
        self.sources_path = sources_path

    def load_sources(self):
        try:
            with open(self.sources_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('sources', [])
        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
            return []

    def collect(self):
        sources = self.load_sources()
        total_new = 0
        
        for source in sources:
            name = source.get('name')
            url = source.get('url')
            logger.info(f"Collecting from {name}: {url}")
            
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    # Basic dedup check by URL
                    url = entry.get('link')
                    if not url:
                        continue
                        
                    # Prepare event data
                    event_id = hashlib.md5(url.encode()).hexdigest()
                    
                    # Parse date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6]).isoformat()
                    else:
                        published_at = datetime.now().isoformat()

                    event_data = {
                        'id': event_id,
                        'title': entry.get('title', 'No Title'),
                        'url': url,
                        'source': name,
                        'source_type': 'rss',
                        'published_at': published_at,
                        'raw_summary': entry.get('summary', '') or entry.get('description', ''),
                    }
                    
                    if self.db.save_event(event_data):
                        total_new += 1
                        
            except Exception as e:
                logger.error(f"Error collecting from {name}: {e}")
                continue
                
        logger.info(f"Collection finished. Added {total_new} new events.")
        return total_new

if __name__ == "__main__":
    db = Database("storage/worldpulse.db")
    collector = RSSCollector(db)
    collector.collect()
