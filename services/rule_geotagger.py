import re
from html import unescape

from db.database import Database
from services.category_validator import CategoryValidator
from services.geocoder import GeocoderService


class RuleBasedGeotagger:
    def __init__(self, db: Database, task_control=None):
        self.db = db
        self.task_control = task_control
        self.geocoder = GeocoderService(db)
        self.category_validator = CategoryValidator()
        self.locations = self._build_locations()

    def geotag_unmapped(self, limit=200):
        events = self.db.get_unmapped_events(limit)
        mapped = 0
        for event in events:
            if self._is_cancelled():
                break
            result = self.geotag_event(event)
            if not result:
                continue
            self.db.update_event_fields(event["id"], result, status="raw")
            mapped += 1
        return mapped

    def repair_existing_locations(self, limit=500):
        repaired = 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events
                WHERE lat IS NOT NULL
                  AND lon IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            events = [dict(row) for row in cursor.fetchall()]

        for event in events:
            if self._is_cancelled():
                break
            text = self._normalize_text(f"{event.get('title') or ''} {event.get('raw_summary') or ''}")
            current_country = str(event.get("country") or "")
            if not self._needs_repair(current_country, text):
                continue
            result = self.geotag_event(event)
            if not result:
                continue
            self.db.update_event_fields(event["id"], result, status=event.get("status") or "raw")
            repaired += 1
        return repaired

    def _is_cancelled(self):
        return bool(self.task_control and self.task_control.is_cancelled())

    def geotag_event(self, event):
        text = self._normalize_text(f"{event.get('title') or ''} {event.get('raw_summary') or ''}")
        match = self._find_best_location(text)
        if not match:
            return None

        lat, lon = self._known_coordinates(match["country"], match.get("city"))
        if lat is None or lon is None:
            lat, lon = self.geocoder.get_coordinates(match["country"], match.get("city"))
        if lat is None or lon is None:
            return None

        category = event.get("category") or self._infer_category(text)
        category, status = self.category_validator.validate(category, event.get("title"), event.get("raw_summary"))

        return {
            "country": match["country"],
            "city": match.get("city"),
            "lat": lat,
            "lon": lon,
            "location_scope": "specific",
            "location_confidence": match["confidence"],
            "location_reason": f"Rule match: {match['alias']} | category_validation={status}",
            "category": category,
            "severity": self._infer_severity(text),
            "risk_level": self._infer_risk_level(text),
        }

    def _needs_repair(self, country, text):
        if any(separator in country for separator in [",", "，", "/", "、"]):
            return True
        if "near south africa" in text and country.lower() != "south africa":
            return True
        if "off south africa" in text and country.lower() != "south africa":
            return True
        if "coast of south africa" in text and country.lower() != "south africa":
            return True
        return False

    def _find_best_location(self, text):
        phrase_match = self._find_phrase_location(text)
        if phrase_match:
            return phrase_match

        best = None
        for location in self.locations:
            for alias in location["aliases"]:
                pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
                if not re.search(pattern, text):
                    continue
                confidence = location["confidence"] + min(0.08, len(alias) / 100)
                candidate = {**location, "alias": alias, "confidence": min(0.95, confidence)}
                if best is None or candidate["confidence"] > best["confidence"]:
                    best = candidate
        return best

    def _find_phrase_location(self, text):
        phrase_rules = [
            (r"\bnear south africa\b", "South Africa", None, "near South Africa"),
            (r"\boff south africa\b", "South Africa", None, "off South Africa"),
            (r"\bsouth african waters\b", "South Africa", None, "South African waters"),
            (r"\bcoast of south africa\b", "South Africa", None, "coast of South Africa"),
            (r"\bin johannesburg\b", "South Africa", "Johannesburg", "Johannesburg"),
            (r"\bin gaborone\b", "Botswana", "Gaborone", "Gaborone"),
            (r"\bin botswana\b", "Botswana", None, "Botswana"),
        ]
        for pattern, country, city, alias in phrase_rules:
            if re.search(pattern, text):
                return {
                    "country": country,
                    "city": city,
                    "aliases": [alias],
                    "alias": alias,
                    "confidence": 0.9,
                }
        return None

    def _normalize_text(self, value):
        text = re.sub(r"<[^>]+>", " ", unescape(value))
        text = re.sub(r"\s+", " ", text)
        return text.lower()

    def _infer_category(self, text):
        rules = [
            ("tariff_policy", ["tariff", "duty", "anti-dumping", "import tax", "section 301", "hs code"]),
            ("customs_clearance", ["customs", "clearance", "de minimis", "inspection", "border control"]),
            ("logistics_delay", ["delay", "backlog", "parcel", "delivery", "dhl", "fedex", "ups", "air cargo"]),
            ("port_disruption", ["port", "dockworker", "strike", "shipping lane", "red sea", "suez", "container"]),
            ("platform_policy", ["amazon", "tiktok shop", "temu", "shopee", "marketplace", "seller rule", "platform"]),
            ("sanctions_conflict", ["war", "missile", "drone", "attack", "ceasefire", "military", "sanction", "export control"]),
            ("currency_oil", ["inflation", "central bank", "oil price", "crude", "currency", "exchange rate", "dollar"]),
            ("supply_chain", ["supply chain", "semiconductor", "chip", "factory", "shortage", "supplier"]),
            ("market_demand", ["consumer demand", "retail sales", "market", "holiday season", "spending"]),
            ("compliance", ["regulation", "compliance", "privacy", "product safety", "recall", "data breach"]),
        ]
        for category, keywords in rules:
            if any(keyword in text for keyword in keywords):
                return category
        return "other"

    def _infer_severity(self, text):
        if any(k in text for k in ["killed", "dead", "missile", "war", "explosion", "red sea", "sanction", "strike"]):
            return 4
        if any(k in text for k in ["attack", "protest", "arrest", "customs", "tariff", "delay", "port", "oil price"]):
            return 3
        return 2

    def _infer_risk_level(self, text):
        severity = self._infer_severity(text)
        if severity >= 4:
            return "high"
        if severity == 3:
            return "medium"
        return "low"

    def _build_locations(self):
        country_aliases = {
            "United States": ["united states", "u.s.", "us ", "usa", "america", "washington"],
            "United Kingdom": ["united kingdom", "uk ", "britain", "london"],
            "China": ["china", "beijing", "shanghai", "hong kong", "taiwan"],
            "Russia": ["russia", "moscow", "kremlin"],
            "Ukraine": ["ukraine", "kyiv", "kiev"],
            "Israel": ["israel", "jerusalem", "tel aviv", "gaza"],
            "Iran": ["iran", "tehran"],
            "Iraq": ["iraq", "baghdad"],
            "Syria": ["syria", "damascus"],
            "Yemen": ["yemen", "sanaa"],
            "Philippines": ["philippines", "manila"],
            "Pakistan": ["pakistan", "islamabad", "karachi"],
            "India": ["india", "new delhi", "delhi", "mumbai"],
            "Japan": ["japan", "tokyo"],
            "South Korea": ["south korea", "seoul"],
            "North Korea": ["north korea", "pyongyang"],
            "Australia": ["australia", "canberra", "sydney", "melbourne"],
            "Uzbekistan": ["uzbekistan", "tashkent", "uzbek"],
            "Maldives": ["maldives", "male"],
            "France": ["france", "paris"],
            "Germany": ["germany", "berlin"],
            "Vietnam": ["vietnam", "hanoi", "ho chi minh"],
            "Singapore": ["singapore"],
            "Thailand": ["thailand", "bangkok"],
            "Indonesia": ["indonesia", "jakarta"],
            "Malaysia": ["malaysia", "kuala lumpur"],
            "Netherlands": ["netherlands", "rotterdam", "amsterdam"],
            "Belgium": ["belgium", "antwerp", "brussels"],
            "Poland": ["poland", "warsaw"],
            "Turkey": ["turkey", "ankara", "istanbul"],
            "Mexico": ["mexico", "mexico city"],
            "Brazil": ["brazil", "brasilia", "sao paulo"],
            "Venezuela": ["venezuela", "caracas"],
            "Myanmar": ["myanmar", "burma", "naypyidaw", "yangon"],
            "Afghanistan": ["afghanistan", "kabul"],
            "Sudan": ["sudan", "khartoum"],
            "South Africa": ["south africa", "south african", "pretoria", "johannesburg"],
            "Botswana": ["botswana", "gaborone"],
            "Saudi Arabia": ["saudi arabia", "riyadh"],
            "United Arab Emirates": ["uae", "united arab emirates", "dubai", "abu dhabi"],
            "Egypt": ["egypt", "suez", "cairo"],
        }
        city_overrides = {
            "washington": ("United States", "Washington"),
            "beijing": ("China", "Beijing"),
            "shanghai": ("China", "Shanghai"),
            "hong kong": ("China", "Hong Kong"),
            "moscow": ("Russia", "Moscow"),
            "kyiv": ("Ukraine", "Kyiv"),
            "kiev": ("Ukraine", "Kyiv"),
            "jerusalem": ("Israel", "Jerusalem"),
            "tel aviv": ("Israel", "Tel Aviv"),
            "gaza": ("Palestine", "Gaza"),
            "manila": ("Philippines", "Manila"),
            "canberra": ("Australia", "Canberra"),
            "london": ("United Kingdom", "London"),
            "paris": ("France", "Paris"),
            "berlin": ("Germany", "Berlin"),
            "hanoi": ("Vietnam", "Hanoi"),
            "ho chi minh": ("Vietnam", "Ho Chi Minh City"),
            "singapore": ("Singapore", "Singapore"),
            "bangkok": ("Thailand", "Bangkok"),
            "jakarta": ("Indonesia", "Jakarta"),
            "kuala lumpur": ("Malaysia", "Kuala Lumpur"),
            "rotterdam": ("Netherlands", "Rotterdam"),
            "amsterdam": ("Netherlands", "Amsterdam"),
            "antwerp": ("Belgium", "Antwerp"),
            "brussels": ("Belgium", "Brussels"),
            "suez": ("Egypt", "Suez"),
            "tokyo": ("Japan", "Tokyo"),
            "seoul": ("South Korea", "Seoul"),
            "tashkent": ("Uzbekistan", "Tashkent"),
            "johannesburg": ("South Africa", "Johannesburg"),
            "pretoria": ("South Africa", "Pretoria"),
            "gaborone": ("Botswana", "Gaborone"),
        }

        locations = []
        for country, aliases in country_aliases.items():
            country_only = []
            for alias in aliases:
                if alias in city_overrides:
                    city_country, city = city_overrides[alias]
                    locations.append({
                        "country": city_country,
                        "city": city,
                        "aliases": [alias],
                        "confidence": 0.78,
                    })
                else:
                    country_only.append(alias)
            if country_only:
                locations.append({
                    "country": country,
                    "city": None,
                    "aliases": country_only,
                    "confidence": 0.62,
                })
        return locations

    def _known_coordinates(self, country, city=None):
        key = f"{city or ''}|{country}".lower()
        known = {
            "|united states": (39.7837, -100.4459),
            "washington|united states": (38.8950, -77.0365),
            "|united kingdom": (54.7024, -3.2766),
            "london|united kingdom": (51.5074, -0.1278),
            "|china": (35.0001, 104.9999),
            "beijing|china": (39.9057, 116.3913),
            "shanghai|china": (31.2313, 121.4692),
            "hong kong|china": (22.2793, 114.1628),
            "|russia": (64.6863, 97.7453),
            "moscow|russia": (55.7558, 37.6173),
            "|ukraine": (49.4872, 31.2718),
            "kyiv|ukraine": (50.4500, 30.5241),
            "|israel": (30.8124, 34.8595),
            "jerusalem|israel": (31.7788, 35.2258),
            "tel aviv|israel": (32.0853, 34.7818),
            "gaza|palestine": (31.5017, 34.4668),
            "|iran": (32.6475, 54.5644),
            "tehran|iran": (35.6893, 51.3896),
            "|philippines": (12.7503, 122.7312),
            "manila|philippines": (14.5904, 120.9804),
            "|pakistan": (30.3308, 71.2475),
            "islamabad|pakistan": (33.6938, 73.0652),
            "|india": (22.3511, 78.6677),
            "new delhi|india": (28.6139, 77.2090),
            "|australia": (-24.7761, 134.7550),
            "canberra|australia": (-35.2976, 149.1013),
            "|uzbekistan": (41.3237, 63.9528),
            "tashkent|uzbekistan": (41.3123, 69.2787),
            "|france": (46.6034, 1.8883),
            "paris|france": (48.8535, 2.3484),
            "|germany": (51.1638, 10.4478),
            "berlin|germany": (52.5174, 13.3951),
            "|vietnam": (15.9267, 107.9651),
            "hanoi|vietnam": (21.0285, 105.8542),
            "ho chi minh city|vietnam": (10.7769, 106.7009),
            "|singapore": (1.3571, 103.8195),
            "singapore|singapore": (1.3521, 103.8198),
            "|thailand": (14.8972, 100.8327),
            "bangkok|thailand": (13.7525, 100.4942),
            "|indonesia": (-2.4834, 117.8903),
            "jakarta|indonesia": (-6.1754, 106.8272),
            "|malaysia": (4.5694, 102.2657),
            "kuala lumpur|malaysia": (3.1527, 101.7031),
            "|netherlands": (52.2435, 5.6343),
            "rotterdam|netherlands": (51.9244, 4.4777),
            "amsterdam|netherlands": (52.3731, 4.8925),
            "|belgium": (50.6403, 4.6667),
            "antwerp|belgium": (51.2211, 4.3997),
            "brussels|belgium": (50.8466, 4.3517),
            "|egypt": (26.2540, 29.2675),
            "suez|egypt": (29.9737, 32.5263),
            "|japan": (36.5748, 139.2394),
            "tokyo|japan": (35.6769, 139.7639),
            "|south korea": (36.6384, 127.6961),
            "seoul|south korea": (37.5667, 126.9784),
            "|maldives": (3.7204, 73.2244),
            "male|maldives": (4.1779, 73.5107),
            "|south africa": (-28.8166, 24.9916),
            "johannesburg|south africa": (-26.205, 28.0497),
            "pretoria|south africa": (-25.7479, 28.2293),
            "|botswana": (-23.1682, 24.5929),
            "gaborone|botswana": (-24.6581, 25.9122),
        }
        return known.get(key, (None, None))
