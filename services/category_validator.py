import re


class CategoryValidator:
    def __init__(self):
        self.rules = {
            "tariff_policy": ["tariff", "duty", "trade act", "import tax", "hs code", "关税", "税率"],
            "customs_clearance": ["customs", "clearance", "inspection", "border", "de minimis", "清关", "海关"],
            "logistics_delay": ["delay", "delivery", "shipment", "parcel", "logistics", "物流", "延误"],
            "port_disruption": ["port", "vessel", "shipping", "congestion", "suez", "red sea", "港口", "航运"],
            "platform_policy": ["amazon", "tiktok shop", "temu", "shopee", "marketplace", "platform", "平台"],
            "sanctions_conflict": ["sanction", "war", "missile", "drone", "attack", "ceasefire", "制裁", "冲突", "战争"],
            "currency_oil": ["inflation", "oil", "crude", "exchange rate", "dollar", "央行", "汇率", "油价"],
            "supply_chain": ["supply chain", "factory", "supplier", "chip", "semiconductor", "供应链", "工厂"],
            "market_demand": ["demand", "consumer", "retail sales", "market sentiment", "消费", "需求"],
            "compliance": ["regulation", "compliance", "privacy", "recall", "enforcement", "合规", "监管"],
        }

    def best_category(self, title: str | None, summary: str | None) -> tuple[str, float]:
        text = f"{title or ''} {summary or ''}".lower()
        text = re.sub(r"\s+", " ", text)
        best = "other"
        best_score = 0.0
        for category, keywords in self.rules.items():
            hit = sum(1 for word in keywords if word in text)
            if hit == 0:
                continue
            score = min(1.0, hit / max(2, len(keywords) * 0.35))
            if score > best_score:
                best = category
                best_score = score
        if best_score < 0.2:
            return "other", 0.0
        return best, best_score

    def validate(self, chosen: str | None, title: str | None, summary: str | None) -> tuple[str, str]:
        selected = (chosen or "other").strip().lower()
        inferred, confidence = self.best_category(title, summary)
        if selected == inferred:
            return selected, "ok"
        if inferred == "other" and selected != "other":
            return selected, "weak-evidence"
        if confidence >= 0.55:
            return inferred, "corrected"
        return selected, "kept"
