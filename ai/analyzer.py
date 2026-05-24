from ai.ai_client import AIClient
from ai.prompts import LOCATION_TAGGING_PROMPT, NEWS_ANALYSIS_PROMPT, get_industry_analysis_prompt
from db.database import Database
from services.category_validator import CategoryValidator
from services.geocoder import GeocoderService
import logging
import json

logger = logging.getLogger(__name__)

class EventAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.ai_client = AIClient()
        self.geocoder = GeocoderService(db)
        self.category_validator = CategoryValidator()

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

    def analyze_event(self, event_id, industry_config=None, llm=None):
        event = self.db.get_event(event_id)
        if not event:
            return None

        logger.info(f"Analyzing event on demand: {event['title']}")
        prompt = get_industry_analysis_prompt(industry_config) if industry_config else NEWS_ANALYSIS_PROMPT
        analysis = self.ai_client.analyze(prompt, self._event_content(event), llm=llm)
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
            'industry',
            'affected_groups',
            'business_impact',
            'market_impact',
            'opportunity_signal',
            'suggested_action',
            'content_angle',
        }
        normalized = {key: analysis.get(key) for key in allowed_fields if key in analysis}

        for text_key in [
            'country', 'city', 'location_scope', 'location_reason', 'business_impact',
            'market_impact', 'opportunity_signal', 'suggested_action', 'content_angle',
            'social_angle', 'industry', 'ai_summary'
        ]:
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

        normalized = self._enforce_localized_output(normalized)
        category, status = self.category_validator.validate(
            normalized.get("category"),
            normalized.get("ai_summary") or "",
            normalized.get("business_impact") or "",
        )
        normalized["category"] = category
        reason = normalized.get("location_reason") or ""
        normalized["location_reason"] = f"{reason} | category_validation={status}".strip(" |")

        return normalized

    def _contains_cjk(self, text):
        if not isinstance(text, str):
            return False
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    def _is_english_like(self, text):
        if not isinstance(text, str):
            return False
        stripped = text.strip()
        if not stripped:
            return False
        ascii_letters = sum(ch.isalpha() and ord(ch) < 128 for ch in stripped)
        return ascii_letters >= 12 and not self._contains_cjk(stripped)

    def _enforce_localized_output(self, normalized):
        zh_fallback = {
            'ai_summary': "该事件仍在持续发展，需结合后续官方信息判断实际影响。",
            'business_impact': "可能影响经营成本、履约时效或合规决策，建议结合业务场景持续跟踪。",
            'market_impact': "可能引发相关市场情绪或成本端波动，需观察后续数据确认。",
            'opportunity_signal': "可作为风险预警和内部沟通素材，关注后续是否出现可执行窗口。",
            'suggested_action': "建议先核对受影响市场与渠道，建立跟踪清单并等待更多确定性信息。",
            'content_angle': "可从“事件进展+业务影响+应对动作”三个维度进行对内外沟通。",
            'social_angle': "这不是孤立新闻，关键在于它对成本、时效和风险决策的连锁影响。",
            'location_reason': "基于标题与摘要中的地理线索进行保守判断。",
        }
        zh_group_map = {
            "financial institutions": "金融机构",
            "exporters": "出口企业",
            "energy companies": "能源企业",
            "technology firms": "科技企业",
            "importers": "进口企业",
            "ecommerce sellers": "跨境电商卖家",
            "logistics providers": "物流服务商",
            "manufacturers": "制造企业",
        }

        for key, fallback_text in zh_fallback.items():
            value = normalized.get(key)
            if value and self._is_english_like(value):
                normalized[key] = fallback_text
            elif not value and key in {'ai_summary', 'business_impact', 'suggested_action'}:
                normalized[key] = fallback_text

        groups = normalized.get('affected_groups')
        if isinstance(groups, str):
            try:
                parsed = json.loads(groups)
                if isinstance(parsed, list):
                    groups = parsed
            except json.JSONDecodeError:
                groups = [groups]
        if isinstance(groups, list):
            localized_groups = []
            for group in groups:
                text = str(group).strip()
                lower = text.lower()
                if lower in zh_group_map:
                    localized_groups.append(zh_group_map[lower])
                elif self._is_english_like(text):
                    localized_groups.append("相关行业参与方")
                elif text:
                    localized_groups.append(text)
            normalized['affected_groups'] = json.dumps(localized_groups or ["相关经营主体"], ensure_ascii=False)
        elif not groups:
            normalized['affected_groups'] = json.dumps(["相关经营主体"], ensure_ascii=False)

        return normalized

    def _should_geocode(self, analysis):
        country = analysis.get('country')
        scope = str(analysis.get('location_scope') or '').lower()
        location_confidence = float(analysis.get('location_confidence') or 0)
        return bool(country) and scope in {'specific', 'country', 'city'} and location_confidence >= 0.55
