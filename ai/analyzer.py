from ai.ai_client import AIClient
from ai.prompts import NEWS_ANALYSIS_PROMPT
from db.database import Database
from services.geocoder import GeocoderService
import logging

logger = logging.getLogger(__name__)

class EventAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.ai_client = AIClient()
        self.geocoder = GeocoderService(db)

    def process_unanalyzed(self, limit=10):
        events = self.db.get_unanalyzed_events(limit)
        count = 0
        for event in events:
            logger.info(f"Analyzing event: {event['title']}")
            content = f"Title: {event['title']}\nSummary: {event['raw_summary']}\nSource: {event['source']}"
            
            analysis = self.ai_client.analyze(NEWS_ANALYSIS_PROMPT, content)
            if analysis:
                # Add coordinates
                lat, lon = self.geocoder.get_coordinates(
                    analysis.get('country'), 
                    analysis.get('city')
                )
                analysis['lat'] = lat
                analysis['lon'] = lon
                
                self.db.update_event_analysis(event['id'], analysis)
                count += 1
            else:
                self.db.update_event_analysis(event['id'], {'status': 'failed'})
        
        return count
