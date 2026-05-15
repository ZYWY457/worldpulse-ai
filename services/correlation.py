from datetime import datetime, timedelta
import math

class EventCorrelator:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _to_finite_float(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

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
            lat = self._to_finite_float(e.get('lat'))
            lon = self._to_finite_float(e.get('lon'))
            if lat is None or lon is None:
                continue

            # Round to nearest degree
            lat_bin = round(lat)
            lon_bin = round(lon)
            key = (lat_bin, lon_bin)
            
            if key not in grid:
                grid[key] = {
                    'events': [],
                    'categories': set(),
                    'country': e.get('country') or 'Unknown',
                    'city': e.get('city') or 'Unknown'
                }
            grid[key]['events'].append(e)
            grid[key]['categories'].add(e.get('category') or 'other')
        
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
            return "暂无显著情报信号。"
            
        convergences = self.detect_convergences(events)
        
        brief = "### 📡 情报简报\n\n"

        cluster_events = [e for e in events if e.get('source_count') is not None or e.get('event_count') is not None]
        if cluster_events:
            top_clusters = sorted(cluster_events, key=lambda e: float(e.get('risk_score') or 0), reverse=True)[:5]
            brief += "#### 🧭 事件簇\n"
            for e in top_clusters:
                source_count = int(e.get('source_count') or 1)
                event_count = int(e.get('event_count') or 1)
                rss_count = int(e.get('rss_count') or 0)
                gdelt_count = int(e.get('gdelt_count') or 0)
                brief += (
                    f"- **[{str(e.get('risk_level') or 'low').upper()}]** {e.get('title')} "
                    f"({e.get('country') or '未知'}): 风险 {e.get('risk_score') or 0}, "
                    f"{event_count} 条报道 / {source_count} 个来源，RSS {rss_count}，GDELT {gdelt_count}\n"
                )
        
        if convergences:
            brief += "#### ⚠️ 地理收敛信号\n"
            for c in convergences:
                types_str = ", ".join([t.upper() for t in c['types']])
                brief += f"- **{c['country']} ({c['city']})**: {len(c['types'])} 类信号聚集（{types_str}）。升级风险：**{c['severity']}**\n"
        
        # Add high risk alerts
        high_risk = [e for e in events if e.get('risk_level') in ['high', 'critical']]
        if high_risk:
            brief += "\n#### 🚨 高风险警报\n"
            for e in high_risk[:3]:
                brief += f"- **[{e['category'].upper()}]** {e['title']} ({e['source']})\n"
                
        return brief
