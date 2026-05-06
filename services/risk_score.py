import math
from datetime import datetime, timedelta

class RiskScorer:
    def __init__(self, db):
        self.db = db
        # Baseline risk for major countries (0-50 scale)
        self.country_baselines = {
            "Russia": 45,
            "Ukraine": 50,
            "Israel": 40,
            "Iran": 45,
            "USA": 15,
            "China": 15,
            "Taiwan": 30,
            "North Korea": 45,
            "South Korea": 20,
            "UK": 15,
            "France": 20,
            "Germany": 15,
            "Poland": 25,
            "Turkey": 35,
            "India": 30,
            "Pakistan": 45,
            "Syria": 50,
            "Yemen": 50,
            "Myanmar": 50,
            "Venezuela": 45,
            "Cuba": 30,
            "Mexico": 40,
            "Brazil": 35,
            "UAE": 15
        }
        self.default_baseline = 15

    def calculate_event_score(self, severity, category):
        """
        Calculate event score (0-100) based on category and severity.
        Inspired by World Monitor's blend of Unrest, Conflict, Security, Information.
        """
        category_weights = {
            "conflict": 1.5,
            "politics": 1.2,
            "disaster": 1.3,
            "finance": 1.1,
            "energy": 1.2,
            "health": 1.1,
            "technology": 1.0,
            "society": 1.0,
            "other": 0.8
        }
        
        weight = category_weights.get(category.lower(), 1.0)
        # Base score from severity (1-5) -> (20-100)
        base_score = severity * 20
        return min(100, base_score * weight)

    def get_country_cii(self, country_name, recent_events):
        """
        Calculate Country Instability Index (CII) (0-100).
        CII = Baseline (40%) + Event Score (60%)
        """
        baseline = self.country_baselines.get(country_name, self.default_baseline)
        
        if not recent_events:
            return baseline * 0.4
            
        # Average event score for the country in the last 24h
        avg_event_score = sum(self.calculate_event_score(e['severity'], e['category']) for e in recent_events) / len(recent_events)
        
        cii = (baseline * 0.4) + (avg_event_score * 0.6)
        return min(100, cii)

    def calculate_strategic_risk(self, all_events):
        """
        Calculate Global Strategic Risk Score (0-100).
        Inspired by World Monitor's composite formula.
        """
        if not all_events:
            return 0
            
        # 1. Convergence Score (30%) - 3+ event types in same country/region
        countries = {}
        for e in all_events:
            c = e.get('country', 'Unknown')
            if c not in countries: countries[c] = set()
            countries[c].add(e.get('category', 'other'))
        
        convergence_count = sum(1 for c, types in countries.items() if len(types) >= 3)
        convergence_score = min(100, convergence_count * 25)
        
        # 2. CII Risk Score (50%) - Weighted blend of top countries
        country_scores = []
        for country in countries.keys():
            country_events = [e for e in all_events if e.get('country') == country]
            score = self.get_country_cii(country, country_events)
            country_scores.append(score)
            
        country_scores.sort(reverse=True)
        weights = [0.40, 0.25, 0.20, 0.10, 0.05]
        cii_risk_score = sum(s * w for s, w in zip(country_scores[:5], weights))
        
        # 3. Breaking Boost (20%) - High severity events
        high_severity_count = sum(1 for e in all_events if e.get('severity', 0) >= 4)
        breaking_boost = min(20, high_severity_count * 5)
        
        composite_score = (convergence_score * 0.30) + (cii_risk_score * 0.50) + breaking_boost
        return min(100, composite_score)
