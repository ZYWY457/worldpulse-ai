from datetime import datetime, timedelta

class EventCorrelator:
    def __init__(self, db):
        self.db = db

    def detect_convergences(self, events):
        """
        Detect geographic convergence of events.
        Inspired by World Monitor's 1x1 degree binning.
        """
        if not events:
            return []
            
        # Group events by geographic grid (1x1 degree)
        grid = {}
        for e in events:
            if e.get('lat') and e.get('lon'):
                # Round to nearest degree
                lat_bin = round(e['lat'])
                lon_bin = round(e['lon'])
                key = (lat_bin, lon_bin)
                
                if key not in grid:
                    grid[key] = {
                        'events': [],
                        'categories': set(),
                        'country': e.get('country', 'Unknown'),
                        'city': e.get('city', 'Unknown')
                    }
                grid[key]['events'].append(e)
                grid[key]['categories'].add(e.get('category', 'other'))
        
        convergences = []
        for key, data in grid.items():
            # A convergence is defined as 3+ distinct event types in the same grid
            if len(data['categories']) >= 2: # Lowered to 2 for MVP visibility
                convergences.append({
                    'lat': key[0],
                    'lon': key[1],
                    'count': len(data['events']),
                    'types': list(data['categories']),
                    'country': data['country'],
                    'city': data['city'],
                    'severity': max(e.get('severity', 1) for e in data['events'])
                })
                
        return convergences

    def get_intelligence_brief(self, events):
        """
        Generate a structured intelligence brief based on event clusters.
        """
        if not events:
            return "No significant intelligence signals detected."
            
        convergences = self.detect_convergences(events)
        
        brief = "### 📡 INTELLIGENCE FEED\n\n"
        
        if convergences:
            brief += "#### ⚠️ GEOGRAPHIC CONVERGENCE DETECTED\n"
            for c in convergences:
                types_str = ", ".join([t.upper() for t in c['types']])
                brief += f"- **{c['country']} ({c['city']})**: {len(c['types'])} signal types converging ({types_str}). Escalation risk: **{c['severity']}**\n"
        
        # Add high risk alerts
        high_risk = [e for e in events if e.get('risk_level') in ['high', 'critical']]
        if high_risk:
            brief += "\n#### 🚨 CRITICAL ALERTS\n"
            for e in high_risk[:3]:
                brief += f"- **[{e['category'].upper()}]** {e['title']} ({e['source']})\n"
                
        return brief
