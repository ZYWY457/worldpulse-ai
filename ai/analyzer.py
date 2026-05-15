from ai.ai_client import AIClient
from ai.prompts import LOCATION_TAGGING_PROMPT, NEWS_ANALYSIS_PROMPT
from db.database import Database
from services.geocoder import GeocoderService
import logging
import json

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
            if self.analyze_event(event['id']):
                count += 1
        
        return count

    def geotag_unmapped(self, limit=50):
        events = self.db.get_unmapped_events(limit)
        count = 0
        for event in events:
            logger.info(f"Geotagging event: {event['title']}")
            content = self._event_content(event)
            location = self.ai_client.analyze(LOCATION_TAGGING_PROMPT, content)
            if not location:
                continue

            location = self._normalize_analysis(location)
            if self._should_geocode(location):
                lat, lon = self.geocoder.get_coordinates(location.get('country'), location.get('city'))
            else:
                lat, lon = None, None
                location['country'] = None
                location['city'] = None

            location['lat'] = lat
            location['lon'] = lon
            location.setdefault('severity', 1)
            location.setdefault('risk_level', 'low')
            self.db.update_event_fields(event['id'], location, status='raw')
            if lat is not None and lon is not None:
                count += 1
        return count

    def analyze_event(self, event_id):
        event = self.db.get_event(event_id)
        if not event:
            return None

        logger.info(f"Analyzing event on demand: {event['title']}")
        analysis = self.ai_client.analyze(NEWS_ANALYSIS_PROMPT, self._event_content(event))
        if not analysis:
            self.db.update_event_fields(event_id, {}, status='failed')
            return None

        analysis = self._normalize_analysis(analysis)
        if self._should_geocode(analysis):
            lat, lon = self.geocoder.get_coordinates(analysis.get('country'), analysis.get('city'))
        else:
            lat, lon = event.get('lat'), event.get('lon')
            if lat is None or lon is None:
                analysis['country'] = None
                analysis['city'] = None

        analysis['lat'] = lat
        analysis['lon'] = lon
        self.db.update_event_fields(event_id, analysis, status='analyzed')
        return self.db.get_event(event_id)

    def _event_content(self, event):
        return f"Title: {event['title']}\nSummary: {event.get('raw_summary') or ''}\nSource: {event.get('source') or ''}"

    def _normalize_analysis(self, analysis):
        allowed_fields = {
            'ai_summary',
            'category',
            'country',
            'city',
            'location_scope',
            'location_confidence',
            'location_reason',
            'severity',
            'confidence',
            'risk_level',
            'social_angle',
            'affected_groups',
            'business_impact',
            'suggested_action',
        }
        normalized = {key: analysis.get(key) for key in allowed_fields if key in analysis}

        for text_key in ['country', 'city', 'location_scope', 'location_reason', 'business_impact', 'suggested_action', 'social_angle']:
            value = normalized.get(text_key)
            if isinstance(value, str):
                normalized[text_key] = value.strip() or None
        if isinstance(normalized.get('affected_groups'), list):
            normalized['affected_groups'] = json.dumps(normalized['affected_groups'], ensure_ascii=False)
        elif isinstance(normalized.get('affected_groups'), str):
            normalized['affected_groups'] = normalized['affected_groups'].strip() or None

        normalized['location_scope'] = normalized.get('location_scope') or 'unclear'
        try:
            normalized['location_confidence'] = float(normalized.get('location_confidence') or 0)
        except (TypeError, ValueError):
            normalized['location_confidence'] = 0

        return normalized

    def _should_geocode(self, analysis):
        country = analysis.get('country')
        scope = str(analysis.get('location_scope') or '').lower()
        location_confidence = float(analysis.get('location_confidence') or 0)
        return bool(country) and scope in {'specific', 'country', 'city'} and location_confidence >= 0.55
