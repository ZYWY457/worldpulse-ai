import json
import os
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import unquote_plus

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.analyzer import EventAnalyzer
from ai.ai_client import AIClient
from ai.prompts import USER_PROFILE_PROMPT
from ai.social_writer import SocialMediaWriter
from collectors.gdelt_collector import GDELTCollector
from collectors.rss_collector import RSSCollector
from collectors.static_page_collector import StaticPageCollector
from backend.demo_loader import load_demo_if_empty
from backend.industries import get_industry, get_industry_ids
from db.database import Database
from services.correlation import EventCorrelator
from services.event_aggregator import EventAggregator
from services.rule_geotagger import RuleBasedGeotagger
from services.risk_score import RiskScorer
from services.task_control import TaskControl


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


class ActionResponse(BaseModel):
    ok: bool
    message: str
    count: int | None = None


class MetricsResponse(BaseModel):
    total_events: int
    total_clusters: int
    analyzed_events: int
    high_risk_events: int
    unique_countries: int
    strategic_risk_index: int


class ProfileAnalyzeRequest(BaseModel):
    text: str
    llm: str | None = None


class UserProfileResponse(BaseModel):
    ok: bool
    message: str
    profile: dict[str, Any]


class LlmStatusResponse(BaseModel):
    ok: bool
    requested: str
    provider: str
    configured: bool
    available: bool
    latency_ms: int | None = None
    message: str
    error: str | None = None


class SourceHealthItem(BaseModel):
    source_name: str
    source_type: str
    endpoint: str
    status: str
    latency_ms: int | None = None
    http_code: int | None = None
    fetched_count: int | None = None
    accepted_count: int | None = None
    error_message: str | None = None
    updated_at: str


class LlmConfigRequest(BaseModel):
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    deepseek_base_url: str | None = None
    deepseek_model: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None


db = Database("storage/worldpulse.db")
task_control = TaskControl()
collector = RSSCollector(db, task_control=task_control)
gdelt_collector = GDELTCollector(db, task_control=task_control)
static_page_collector = StaticPageCollector(db, task_control=task_control)
analyzer = EventAnalyzer(db)
profile_ai = AIClient()
social_writer = SocialMediaWriter()
risk_scorer = RiskScorer(db)
correlator = EventCorrelator(db)
aggregator = EventAggregator(db)
rule_geotagger = RuleBasedGeotagger(db, task_control=task_control)

app = FastAPI(title="WorldPulse Radar API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

demo_count = load_demo_if_empty(db)
if demo_count:
    aggregator.rebuild_recent_clusters(hours=168)


def load_events_df() -> pd.DataFrame:
    with db.get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM events ORDER BY published_at DESC", conn)


def load_clusters_df() -> pd.DataFrame:
    with db.get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM event_clusters ORDER BY risk_score DESC, last_seen DESC", conn)


def apply_time_filter(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    if df.empty:
        return df
    if "published_at" not in df.columns:
        return df
    filtered = df.copy()
    filtered["published_at"] = pd.to_datetime(filtered["published_at"], errors="coerce")
    now = datetime.now()
    if time_range == "1h":
        return filtered[filtered["published_at"] > (now - timedelta(hours=1))]
    if time_range == "24h":
        return filtered[filtered["published_at"] > (now - timedelta(hours=24))]
    if time_range == "7d":
        return filtered[filtered["published_at"] > (now - timedelta(days=7))]
    if time_range == "30d":
        return filtered[filtered["published_at"] > (now - timedelta(days=30))]
    return filtered


def apply_cluster_time_filter(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    if df.empty or "last_seen" not in df.columns:
        return df
    filtered = df.copy()
    filtered["last_seen"] = pd.to_datetime(filtered["last_seen"], errors="coerce")
    now = datetime.now()
    if time_range == "1h":
        return filtered[filtered["last_seen"] > (now - timedelta(hours=1))]
    if time_range == "24h":
        return filtered[filtered["last_seen"] > (now - timedelta(hours=24))]
    if time_range == "7d":
        return filtered[filtered["last_seen"] > (now - timedelta(days=7))]
    if time_range == "30d":
        return filtered[filtered["last_seen"] > (now - timedelta(days=30))]
    return filtered


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    safe_df = df.where(pd.notnull(df), None)
    records = safe_df.to_dict(orient="records")
    return [{key: safe_value(value) for key, value in record.items()} for record in records]


def safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if value is pd.NaT:
        return None
    return value


def sorted_unique_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist())


CATEGORY_LABELS = {
    "tariff_policy": "关税政策",
    "customs_clearance": "海关清关",
    "logistics_delay": "物流延误",
    "port_disruption": "港口/航运中断",
    "platform_policy": "平台规则",
    "sanctions_conflict": "制裁/冲突",
    "currency_oil": "汇率/油价",
    "supply_chain": "供应链",
    "market_demand": "市场需求",
    "compliance": "合规监管",
    "central_bank": "央行政策",
    "commodity_price": "商品价格",
    "stock_market": "股市风险",
    "crypto_market": "加密市场",
    "ai_model": "AI 模型",
    "chips": "芯片限制",
    "cloud_datacenter": "云服务/数据中心",
    "tech_regulation": "科技监管",
    "factory_disruption": "工厂停摆",
    "raw_materials": "原材料",
    "energy_supply": "能源供应",
    "military_conflict": "战争冲突",
    "diplomacy": "外交关系",
    "protest_unrest": "抗议动荡",
    "viral_topic": "热点选题",
    "other": "其他",
}

CATEGORY_INDUSTRY_MAP = {
    "tariff_policy": {"trade", "supply_chain"},
    "customs_clearance": {"trade", "supply_chain"},
    "logistics_delay": {"trade", "supply_chain"},
    "port_disruption": {"trade", "supply_chain", "geopolitics"},
    "platform_policy": {"trade", "tech", "content"},
    "sanctions_conflict": {"trade", "finance", "supply_chain", "geopolitics", "content"},
    "currency_oil": {"trade", "finance", "supply_chain"},
    "supply_chain": {"trade", "supply_chain", "tech"},
    "market_demand": {"trade", "finance", "content"},
    "compliance": {"trade", "tech", "supply_chain"},
    "central_bank": {"finance"},
    "commodity_price": {"finance", "supply_chain"},
    "stock_market": {"finance"},
    "crypto_market": {"finance", "content"},
    "ai_model": {"tech", "content"},
    "chips": {"tech", "supply_chain", "geopolitics"},
    "cloud_datacenter": {"tech", "supply_chain"},
    "tech_regulation": {"tech", "geopolitics"},
    "factory_disruption": {"supply_chain", "trade"},
    "raw_materials": {"supply_chain", "finance"},
    "military_conflict": {"geopolitics", "finance", "content"},
    "diplomacy": {"geopolitics", "finance"},
    "protest_unrest": {"geopolitics", "content"},
    "viral_topic": {"content"},
}

BRIEF_TITLES = {
    "overview": "今日全球信息面简报",
    "trade": "今日出海经营风险简报",
    "finance": "今日金融市场信息面简报",
    "tech": "今日科技 AI 信息面简报",
    "supply_chain": "今日供应链工业风险简报",
    "geopolitics": "今日地缘安全简报",
    "content": "今日内容选题雷达",
}


def category_label(category: str | None) -> str:
    return CATEGORY_LABELS.get(category or "other", category or "其他")


def fallback_profile_from_text(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    lower = raw.lower()
    categories: set[str] = set()
    industries: set[str] = {"overview"}
    keywords: set[str] = set()
    risk_focus: list[str] = []

    category_hints = [
        (("跨境", "外贸", "卖家", "amazon", "tiktok", "temu", "shopee", "物流", "清关", "关税"), "trade", ["tariff_policy", "customs_clearance", "logistics_delay", "platform_policy"]),
        (("供应链", "工厂", "采购", "原料", "能源", "港口", "航运"), "supply_chain", ["supply_chain", "raw_materials", "energy_supply", "port_disruption"]),
        (("金融", "投资", "股票", "基金", "黄金", "油价", "汇率", "比特币", "债券"), "finance", ["central_bank", "stock_market", "commodity_price", "currency_oil", "crypto_market"]),
        (("ai", "人工智能", "科技", "芯片", "模型", "云", "开发者", "创业"), "tech", ["ai_model", "chips", "cloud_datacenter", "tech_regulation"]),
        (("地缘", "战争", "制裁", "政策", "安全", "军事", "外交"), "geopolitics", ["sanctions_conflict", "military_conflict", "diplomacy"]),
        (("自媒体", "内容", "博主", "视频", "选题", "公众号", "小红书"), "content", ["viral_topic", "market_demand", "protest_unrest"]),
    ]
    for terms, industry, matched_categories in category_hints:
        if any(term in lower or term in raw for term in terms):
            industries.add(industry)
            categories.update(matched_categories)
            keywords.update(terms)

    country_hints = {
        "美国": "United States",
        "英国": "United Kingdom",
        "德国": "Germany",
        "法国": "France",
        "日本": "Japan",
        "韩国": "South Korea",
        "越南": "Vietnam",
        "墨西哥": "Mexico",
        "欧盟": "European Union",
        "中东": "Middle East",
        "东南亚": "Southeast Asia",
    }
    countries = [value for key, value in country_hints.items() if key in raw or value.lower() in lower]
    platforms = [name for name in ["Amazon", "TikTok Shop", "Temu", "Shopee", "Shopify"] if name.lower() in lower]
    if not keywords:
        keywords.update([item for item in raw.replace("，", " ").replace(",", " ").split() if len(item) >= 2][:12])
    if not categories:
        categories.add("other")
    if "trade" in industries:
        risk_focus.extend(["清关、关税和平台规则变化", "物流时效和履约成本", "目标市场合规风险"])
    if "finance" in industries:
        risk_focus.extend(["利率、汇率和商品价格波动", "市场风险偏好变化"])
    if "tech" in industries:
        risk_focus.extend(["AI、芯片、云服务和科技监管变化"])
    if not risk_focus:
        risk_focus.append("与自身职业和业务需求相关的政策、市场和供应链变化")

    return {
        "profile_name": raw[:18] or "我的关注画像",
        "summary": f"根据输入，将优先关注与“{raw[:60] or '当前用户需求'}”相关的事件。",
        "industries": sorted(industries),
        "preferred_categories": sorted(categories),
        "keywords": sorted({item for item in keywords if item})[:24],
        "countries": countries,
        "platforms": platforms,
        "products": [],
        "risk_focus": risk_focus[:5],
        "relevance_rules": [
            "优先展示命中职业、业务、平台、国家或关键词的事件。",
            "优先展示会影响成本、时效、合规、市场需求或经营决策的事件。",
            "高风险事件即使关键词较少，也应保留在前列。",
        ],
        "confidence": 0.45,
    }


def normalize_user_profile(profile: dict[str, Any] | None, original_text: str) -> dict[str, Any]:
    fallback = fallback_profile_from_text(original_text)
    if not isinstance(profile, dict):
        return fallback
    normalized = fallback | {key: value for key, value in profile.items() if value not in (None, "", [])}
    for key in ["industries", "preferred_categories", "keywords", "countries", "platforms", "products", "risk_focus", "relevance_rules"]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
        elif not isinstance(value, list):
            normalized[key] = []
        else:
            normalized[key] = [str(item).strip() for item in value if str(item).strip()]
    try:
        normalized["confidence"] = max(0, min(1, float(normalized.get("confidence", fallback["confidence"]))))
    except (TypeError, ValueError):
        normalized["confidence"] = fallback["confidence"]
    return normalized


def parse_profile_param(profile: str | None) -> dict[str, Any] | None:
    if not profile:
        return None
    try:
        parsed = json.loads(unquote_plus(profile))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return normalize_user_profile(parsed, str(parsed.get("summary") or parsed.get("profile_name") or ""))


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in text.replace("，", ",").split(",") if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def event_search_text(event: dict[str, Any]) -> str:
    parts = [
        event.get("title"),
        event.get("summary"),
        event.get("ai_summary"),
        event.get("raw_summary"),
        event.get("business_impact"),
        event.get("market_impact"),
        event.get("opportunity_signal"),
        event.get("suggested_action"),
        event.get("content_angle"),
        event.get("social_angle"),
        event.get("source"),
        event.get("country"),
        event.get("city"),
        event.get("category"),
    ]
    parts.extend(as_list(event.get("affected_groups")))
    parts.extend(as_list(event.get("industry_tags")))
    return " ".join(str(part) for part in parts if part).lower()


def profile_terms(profile: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ["keywords", "platforms", "products", "risk_focus"]:
        terms.extend(as_list(profile.get(key)))
    seen = set()
    unique_terms = []
    for term in terms:
        normalized = term.strip()
        key = normalized.lower()
        if len(normalized) >= 2 and key not in seen:
            seen.add(key)
            unique_terms.append(normalized)
    return unique_terms


def calculate_relevance(event: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    if not profile:
        return {"relevance_score": 0, "relevance_reason": "", "matched_profile_terms": [], "affected_user_needs": []}

    score = 0
    reasons: list[str] = []
    matched_terms: list[str] = []
    search_text = event_search_text(event)

    for term in profile_terms(profile):
        if term.lower() in search_text:
            score += 12 if len(term) >= 6 else 8
            matched_terms.append(term)

    category = str(event.get("category") or "")
    preferred_categories = as_list(profile.get("preferred_categories"))
    if category and category in preferred_categories:
        score += 22
        reasons.append(f"风险分类匹配：{category_label(category)}")

    country = str(event.get("country") or "")
    for profile_country in as_list(profile.get("countries")):
        if country and profile_country.lower() == country.lower():
            score += 18
            reasons.append(f"国家/地区匹配：{country}")
            break

    event_tags = parse_tags(event.get("industry_tags"))
    industries = set(as_list(profile.get("industries")))
    industry = str(event.get("industry") or "")
    if industry and industry in industries:
        score += 10
        reasons.append(f"行业模式匹配：{industry}")
    matched_industries = sorted(event_tags.intersection(industries))
    if matched_industries:
        score += 10
        reasons.append(f"行业标签匹配：{'、'.join(matched_industries)}")

    risk_level = str(event.get("risk_level") or "low")
    if risk_level == "critical":
        score += 8
        reasons.append("事件风险等级严重")
    elif risk_level == "high":
        score += 5
        reasons.append("事件风险等级较高")

    if matched_terms:
        reasons.insert(0, f"命中画像关键词：{'、'.join(matched_terms[:5])}")

    affected_needs = []
    for focus in as_list(profile.get("risk_focus")):
        if focus.lower() in search_text or any(term.lower() in focus.lower() for term in matched_terms):
            affected_needs.append(focus)
    if not affected_needs and score > 0:
        affected_needs = as_list(profile.get("risk_focus"))[:2]

    reason = "；".join(reasons[:4])
    if not reason and score > 0:
        reason = "与当前画像存在弱匹配，建议作为观察项。"

    return {
        "relevance_score": int(score),
        "relevance_reason": reason,
        "matched_profile_terms": matched_terms[:8],
        "affected_user_needs": affected_needs[:5],
    }


def enrich_records_with_relevance(records: list[dict[str, Any]], profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    enriched = []
    for item in records:
        enriched.append(item | calculate_relevance(item, profile))
    return enriched


def sort_records_by_relevance(records: list[dict[str, Any]], profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    enriched = enrich_records_with_relevance(records, profile)
    if not profile:
        return enriched
    return sorted(
        enriched,
        key=lambda item: (
            int(item.get("relevance_score") or 0),
            float(item.get("risk_score") or 0),
            int(item.get("severity") or 0),
            str(item.get("published_at") or item.get("last_seen") or ""),
        ),
        reverse=True,
    )


def parse_tags(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item) for item in value}
    text = str(value).strip()
    if not text:
        return set()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return {str(item) for item in parsed}
    except json.JSONDecodeError:
        pass
    return {item.strip() for item in text.split(",") if item.strip()}


def row_matches_industry(row: pd.Series, industry: str) -> bool:
    if industry == "overview":
        return True
    tags = parse_tags(row.get("industry_tags"))
    if industry in tags:
        return True
    category = str(row.get("category") or "other")
    return industry in CATEGORY_INDUSTRY_MAP.get(category, set())


def apply_industry_filter(df: pd.DataFrame, industry: str) -> pd.DataFrame:
    if df.empty or industry == "overview":
        return df
    return df[df.apply(lambda row: row_matches_industry(row, industry), axis=1)]


def build_industry_brief(df: pd.DataFrame, clusters: list[dict[str, Any]], industry: str, profile: dict[str, Any] | None = None) -> str:
    config = get_industry(industry)
    total = int(len(df))
    high = int(len(df[df["risk_level"].isin(["high", "critical"])])) if "risk_level" in df.columns else 0
    countries = sorted_unique_values(df, "country")[:5]
    category_counts = df["category"].fillna("other").value_counts().head(5) if "category" in df.columns else []
    category_names = [category_label(str(name)) for name in getattr(category_counts, "index", [])]
    top_cluster_titles = [str(item.get("title") or "") for item in clusters[:3] if item.get("title")]
    focus = "、".join(top_cluster_titles) if top_cluster_titles else "暂无"
    risk_focus = str(config.get("risk_focus") or "暂无")
    opportunity = "、".join(str(item.get("opportunity_signal") or item.get("content_angle") or "").strip() for item in clusters[:3] if item.get("opportunity_signal") or item.get("content_angle")) or "关注高热度事件的二次影响和选题价值"

    lines = [
        f"{BRIEF_TITLES.get(industry, BRIEF_TITLES['overview'])}：",
        f"- 今日重点事件数量：{total}",
        f"- 高风险事件 {high} 条",
        f"- 重点地区：{'、'.join(countries) if countries else '暂无'}",
        f"- 重点分类：{'、'.join(category_names) if category_names else '暂无'}",
        f"- 主要风险：{risk_focus}",
        f"- 机会信号：{opportunity}",
        f"- 建议关注：{focus}",
    ]
    if profile:
        relevant = [item for item in clusters if int(item.get("relevance_score") or 0) > 0]
        top_relevant = relevant[:3]
        profile_name = str(profile.get("profile_name") or "当前画像")
        lines.insert(1, f"- 当前画像：{profile_name}")
        lines.insert(2, f"- 与你相关：{len(relevant)} 条")
        if top_relevant:
            lines.append("- 优先处理：" + "；".join(
                f"{item.get('title') or item.get('summary') or '未命名事件'}（相关度 {item.get('relevance_score')}）"
                for item in top_relevant
            ))
    return "\n".join(lines)


def build_trade_brief(df: pd.DataFrame, clusters: list[dict[str, Any]]) -> str:
    return build_industry_brief(df, clusters, "trade")


def build_clusters_from_events(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    grouped: list[dict[str, Any]] = []
    risk_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "after", "over", "into",
        "about", "against", "amid", "says", "said", "will", "new", "news", "live",
        "update", "updates", "report", "reports", "world", "global", "official", "actions"
    }

    def topic_key(text: Any) -> str:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", str(text or "").lower())
        words = [w for w in words if w not in stop_words]
        if not words:
            return "generic"
        freq: dict[str, int] = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
        top = sorted(freq.keys(), key=lambda k: (-freq[k], k))[:4]
        return "-".join(top) if top else "generic"

    group_cols = [
        df["country"].fillna("Unknown"),
        df["category"].fillna("other"),
        df["title"].apply(topic_key),
    ]
    for _, group in df.groupby(group_cols):
        records = df_to_records(group.sort_values(by="published_at", ascending=False))
        if not records:
            continue
        sample = max(records, key=lambda item: (risk_rank.get(item.get("risk_level") or "low", 1), int(item.get("severity") or 1)))
        sources = {item.get("source") for item in records if item.get("source")}
        score = min(100, int(sample.get("severity") or 1) * 18 + len(records) * 5 + len(sources) * 4)
        grouped.append(
            {
                "id": f"cluster-{sample.get('country')}-{sample.get('category')}",
                "title": f"{sample.get('country') or 'Unknown'} · {category_label(sample.get('category'))}",
                "summary": sample.get("ai_summary") or sample.get("raw_summary") or "",
                "business_impact": sample.get("business_impact"),
                "market_impact": sample.get("market_impact"),
                "opportunity_signal": sample.get("opportunity_signal"),
                "content_angle": sample.get("content_angle"),
                "country": sample.get("country"),
                "city": sample.get("city"),
                "lat": sample.get("lat"),
                "lon": sample.get("lon"),
                "category": sample.get("category"),
                "risk_level": sample.get("risk_level") or "low",
                "risk_score": score,
                "event_count": len(records),
                "source_count": len(sources),
                "rss_count": sum(1 for item in records if item.get("source_type") == "rss"),
                "gdelt_count": sum(1 for item in records if item.get("source_type") == "gdelt"),
                "last_seen": max(str(item.get("published_at") or "") for item in records),
            }
        )
    return sorted(grouped, key=lambda item: (float(item.get("risk_score") or 0), int(item.get("event_count") or 0)), reverse=True)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "name": "WorldPulse Radar"}


@app.get("/llm/status", response_model=LlmStatusResponse)
def llm_status(llm: str = Query(default="auto", pattern="^(auto|openai|deepseek|ollama)$")) -> LlmStatusResponse:
    status = profile_ai.check_connectivity(llm=llm)
    return LlmStatusResponse(**status)


@app.get("/sources/health")
def sources_health() -> dict[str, Any]:
    with db.get_connection() as conn:
        rows = pd.read_sql_query(
            "SELECT source_name, source_type, endpoint, status, latency_ms, http_code, fetched_count, accepted_count, error_message, updated_at "
            "FROM source_health ORDER BY updated_at DESC",
            conn,
        )
    items = df_to_records(rows)
    summary = {
        "total": len(items),
        "ok": sum(1 for it in items if it.get("status") == "ok"),
        "degraded": sum(1 for it in items if it.get("status") != "ok"),
    }
    return {"summary": summary, "items": items}


@app.post("/llm/config")
def llm_config(payload: LlmConfigRequest) -> dict[str, Any]:
    profile_ai.update_runtime_config(payload.model_dump())
    status = {
        "openai_configured": bool(profile_ai.runtime_config.get("openai_api_key")),
        "deepseek_configured": bool(profile_ai.runtime_config.get("deepseek_api_key")),
        "deepseek_base_url": profile_ai.runtime_config.get("deepseek_base_url"),
        "deepseek_model": profile_ai.runtime_config.get("deepseek_model"),
        "ollama_base_url": profile_ai.runtime_config.get("ollama_base_url"),
        "ollama_model": profile_ai.runtime_config.get("ollama_model"),
    }
    return {"ok": True, "message": "模型配置已更新（当前进程生效）", "config": status}


@app.post("/profile/analyze", response_model=UserProfileResponse)
def analyze_user_profile(payload: ProfileAnalyzeRequest) -> UserProfileResponse:
    text = payload.text.strip()
    if not text:
        return UserProfileResponse(ok=False, message="请输入职业、业务或关注需求。", profile={})

    profile = profile_ai.analyze(USER_PROFILE_PROMPT, text, llm=payload.llm)
    if not profile:
        return UserProfileResponse(
            ok=True,
            message="已使用本地规则生成画像。配置 LLM 后可获得更细的画像。",
            profile=normalize_user_profile(None, text),
        )
    return UserProfileResponse(ok=True, message="画像生成完成。", profile=normalize_user_profile(profile, text))


@app.get("/industries")
def get_industries() -> dict[str, Any]:
    return {"items": list(get_industry(industry_id) for industry_id in get_industry_ids())}


@app.post("/collect", response_model=ActionResponse)
def collect_news() -> ActionResponse:
    task_control.reset()
    rss_count = collector.collect()
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Collection cancelled. RSS: {rss_count}.", count=rss_count)
    gdelt_count = gdelt_collector.collect()
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Collection cancelled. RSS: {rss_count}, GDELT: {gdelt_count}.", count=rss_count + gdelt_count)
    crawler_count = static_page_collector.collect()
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Collection cancelled. RSS: {rss_count}, GDELT: {gdelt_count}, Crawler: {crawler_count}.", count=rss_count + gdelt_count + crawler_count)
    cluster_count = aggregator.rebuild_recent_clusters()
    total_count = rss_count + gdelt_count + crawler_count
    return ActionResponse(
        ok=True,
        message=f"采集完成。RSS: {rss_count}, GDELT: {gdelt_count}, 轻爬虫: {crawler_count}, 事件簇: {cluster_count}.",
        count=total_count,
    )


@app.post("/analyze", response_model=ActionResponse)
def analyze_news(limit: int = Query(default=20, ge=1, le=200)) -> ActionResponse:
    task_control.reset()
    analyzed_count = rule_geotagger.geotag_unmapped(limit=limit)
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Map tagging cancelled. Mapped: {analyzed_count}.", count=analyzed_count)
    cluster_count = aggregator.rebuild_recent_clusters()
    return ActionResponse(ok=True, message=f"Map tagging completed. Clusters: {cluster_count}.", count=analyzed_count)


@app.post("/geotag", response_model=ActionResponse)
def geotag_news(limit: int = Query(default=20, ge=1, le=200)) -> ActionResponse:
    task_control.reset()
    mapped_count = rule_geotagger.geotag_unmapped(limit=limit)
    repaired_count = rule_geotagger.repair_existing_locations(limit=500)
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Rule map tagging cancelled. Mapped: {mapped_count}, repaired: {repaired_count}.", count=mapped_count)
    cluster_count = aggregator.rebuild_recent_clusters()
    return ActionResponse(ok=True, message=f"定位完成。新增标记: {mapped_count}, 修复: {repaired_count}, 事件簇: {cluster_count}.", count=mapped_count + repaired_count)


@app.post("/cancel", response_model=ActionResponse)
def cancel_running_task() -> ActionResponse:
    task_control.cancel()
    return ActionResponse(ok=True, message="已请求终止")


@app.post("/events/{event_id}/analyze")
def analyze_single_event(
    event_id: str,
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
    llm: str = Query(default="auto", pattern="^(auto|openai|deepseek|ollama)$"),
) -> dict[str, Any]:
    item = analyzer.analyze_event(event_id, get_industry(industry), llm=llm)
    if not item:
        return {"ok": False, "message": "Analysis failed", "item": None}
    aggregator.rebuild_recent_clusters()
    return {"ok": True, "message": "分析完成", "item": item}


@app.get("/events")
def get_events(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
    profile: str | None = None,
    category: str | None = None,
    country: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    source: str | None = None,
    status: str | None = Query(default=None, pattern="^(raw|analyzed|failed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="published_at", pattern="^(published_at|severity|risk_level|source|country|category)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    user_profile = parse_profile_param(profile)
    df = load_events_df()
    df = apply_time_filter(df, time_range)
    df = apply_industry_filter(df, industry)

    if category:
        df = df[df["category"] == category]
    if country:
        df = df[df["country"] == country]
    if risk_level:
        df = df[df["risk_level"] == risk_level]
    if source:
        df = df[df["source"] == source]
    if status:
        df = df[df["status"] == status]

    risk_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if sort_by == "risk_level" and "risk_level" in df.columns:
        df = df.assign(_risk_rank=df["risk_level"].map(risk_rank).fillna(0))
        df = df.sort_values(by="_risk_rank", ascending=(order == "asc"))
        df = df.drop(columns=["_risk_rank"])
    elif sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=(order == "asc"))
    elif "published_at" in df.columns:
        df = df.sort_values(by="published_at", ascending=False)

    records = df_to_records(df)
    records = sort_records_by_relevance(records, user_profile)
    total = int(len(records))
    start = (page - 1) * page_size
    end = start + page_size
    paged = records[start:end]

    return {
        "items": paged,
        "count": int(len(paged)),
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": end < total,
        "has_prev": page > 1,
    }


@app.get("/map-events")
def get_map_events(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
    profile: str | None = None,
    category: str | None = None,
    country: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    source: str | None = None,
    status: str | None = Query(default=None, pattern="^(raw|analyzed|failed)$"),
    sort_by: str = Query(default="published_at", pattern="^(published_at|severity|risk_level|source|country|category)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    user_profile = parse_profile_param(profile)
    df = load_events_df()
    df = apply_time_filter(df, time_range)
    df = apply_industry_filter(df, industry)

    if category:
        df = df[df["category"] == category]
    if country:
        df = df[df["country"] == country]
    if risk_level:
        df = df[df["risk_level"] == risk_level]
    if source:
        df = df[df["source"] == source]
    if status:
        df = df[df["status"] == status]

    if "lat" in df.columns and "lon" in df.columns:
        df = df[pd.notnull(df["lat"]) & pd.notnull(df["lon"])]

    risk_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    if sort_by == "risk_level" and "risk_level" in df.columns:
        df = df.assign(_risk_rank=df["risk_level"].map(risk_rank).fillna(0))
        df = df.sort_values(by="_risk_rank", ascending=(order == "asc"))
        df = df.drop(columns=["_risk_rank"])
    elif sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=(order == "asc"))
    elif "published_at" in df.columns:
        df = df.sort_values(by="published_at", ascending=False)

    return {
        "items": sort_records_by_relevance(df_to_records(df), user_profile),
        "total": int(len(df)),
    }


@app.get("/filters")
def get_filters(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
) -> dict[str, list[str]]:
    df = apply_time_filter(load_events_df(), time_range)
    df = apply_industry_filter(df, industry)
    return {
        "countries": sorted_unique_values(df, "country"),
        "categories": sorted_unique_values(df, "category"),
        "sources": sorted_unique_values(df, "source"),
        "risk_levels": ["low", "medium", "high", "critical"],
        "statuses": ["raw", "analyzed", "failed"],
    }


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
) -> MetricsResponse:
    df = apply_time_filter(load_events_df(), time_range)
    df = apply_industry_filter(df, industry)
    if df.empty:
        return MetricsResponse(
            total_events=0,
            total_clusters=0,
            analyzed_events=0,
            high_risk_events=0,
            unique_countries=0,
            strategic_risk_index=0,
        )

    analyzed_df = df[df["status"] == "analyzed"]
    analyzed_records = df_to_records(analyzed_df)
    clusters_df = apply_cluster_time_filter(load_clusters_df(), time_range) if industry == "overview" else pd.DataFrame()
    risk_df = clusters_df if not clusters_df.empty else df
    high_risk = risk_df[risk_df["risk_level"].isin(["high", "critical"])] if "risk_level" in risk_df.columns else pd.DataFrame()
    unique_countries = int(df["country"].dropna().nunique()) if "country" in df.columns else 0
    strategic_risk_records = df_to_records(clusters_df) if not clusters_df.empty else analyzed_records
    strategic_risk = int(risk_scorer.calculate_strategic_risk(strategic_risk_records))

    return MetricsResponse(
        total_events=int(len(df)),
        total_clusters=int(len(clusters_df)),
        analyzed_events=int(len(analyzed_df)),
        high_risk_events=int(len(high_risk)),
        unique_countries=unique_countries,
        strategic_risk_index=strategic_risk,
    )


@app.get("/brief")
def get_brief(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
    profile: str | None = None,
) -> dict[str, Any]:
    user_profile = parse_profile_param(profile)
    df = apply_time_filter(load_events_df(), time_range)
    df = apply_industry_filter(df, industry)
    if df.empty:
        return {"brief": f"{BRIEF_TITLES.get(industry, BRIEF_TITLES['overview'])}：当前范围内暂无事件。", "clusters": [], "convergences": []}

    clusters_df = apply_cluster_time_filter(load_clusters_df(), time_range) if industry == "overview" else pd.DataFrame()
    cluster_records = df_to_records(clusters_df) if not clusters_df.empty else build_clusters_from_events(df)
    cluster_records = sort_records_by_relevance(cluster_records, user_profile)
    event_records = df_to_records(df)
    event_records = sort_records_by_relevance(event_records, user_profile)
    brief = build_industry_brief(df, cluster_records, industry, user_profile)
    convergences = correlator.detect_convergences(event_records)
    return {
        "brief": brief,
        "convergences": convergences,
        "clusters": cluster_records[:30],
    }


@app.get("/country-insight")
def get_country_insight(
    country: str = Query(..., min_length=1),
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|30d)$"),
    industry: str = Query(default="overview", pattern="^(overview|trade|finance|tech|supply_chain|geopolitics|content)$"),
) -> dict[str, Any]:
    df = apply_time_filter(load_events_df(), time_range)
    df = apply_industry_filter(df, industry)
    if df.empty or "country" not in df.columns:
        return {
            "country": country,
            "total_events": 0,
            "high_risk_events": 0,
            "categories": [],
            "risk_distribution": [],
            "daily_trend": [],
            "latest_events": [],
        }

    country_df = df[df["country"] == country].copy()
    if country_df.empty:
        return {
            "country": country,
            "total_events": 0,
            "high_risk_events": 0,
            "categories": [],
            "risk_distribution": [],
            "daily_trend": [],
            "latest_events": [],
        }

    total_events = int(len(country_df))
    high_risk_events = int(len(country_df[country_df["risk_level"].isin(["high", "critical"])]))

    category_counts: list[dict[str, Any]] = []
    if "category" in country_df.columns:
        category_series = country_df["category"].fillna("other").value_counts()
        category_counts = [{"category": str(name), "count": int(count)} for name, count in category_series.items()]

    risk_counts: list[dict[str, Any]] = []
    if "risk_level" in country_df.columns:
        risk_order = ["critical", "high", "medium", "low"]
        risk_series = country_df["risk_level"].fillna("low").value_counts()
        for risk in risk_order:
            if risk in risk_series:
                risk_counts.append({"risk_level": risk, "count": int(risk_series[risk])})

    trend_items: list[dict[str, Any]] = []
    if "published_at" in country_df.columns:
        country_df["published_at"] = pd.to_datetime(country_df["published_at"], errors="coerce")
        valid = country_df.dropna(subset=["published_at"])
        if not valid.empty:
            trend = valid.groupby(valid["published_at"].dt.date).size().reset_index(name="count")
            trend = trend.sort_values(by="published_at")
            trend_items = [
                {"date": row["published_at"].isoformat(), "count": int(row["count"])}
                for _, row in trend.iterrows()
            ]

    latest_df = country_df.sort_values(by="published_at", ascending=False).head(8)

    return {
        "country": country,
        "total_events": total_events,
        "high_risk_events": high_risk_events,
        "categories": category_counts,
        "risk_distribution": risk_counts,
        "daily_trend": trend_items,
        "latest_events": df_to_records(latest_df),
    }


@app.get("/events/{event_id}")
def get_event_detail(event_id: str) -> dict[str, Any]:
    df = load_events_df()
    target = df[df["id"] == event_id]
    if target.empty:
        return {"ok": False, "message": "Event not found", "item": None}

    item = df_to_records(target.head(1))[0]
    related = df[(df["id"] != event_id)]
    if item.get("country"):
        related = related[related["country"] == item["country"]]
    if item.get("category"):
        related = related[related["category"] == item["category"]]
    related = related.sort_values(by="published_at", ascending=False).head(8)
    related_records = df_to_records(related)
    risk_breakdown = risk_scorer.explain_cluster_score(
        {
            "severity": item.get("severity"),
            "category": item.get("category"),
            "source_count": len(related_records) if related_records else 1,
            "source_weight_sum": float(item.get("source_weight") or 0.7),
            "rss_count": sum(1 for r in related_records if r.get("source_type") == "rss"),
            "gdelt_count": sum(1 for r in related_records if r.get("source_type") == "gdelt"),
        }
    )
    return {"ok": True, "item": item, "related": related_records, "risk_breakdown": risk_breakdown}


@app.post("/events/{event_id}/social")
def generate_social_for_event(event_id: str) -> dict[str, Any]:
    df = load_events_df()
    target = df[df["id"] == event_id]
    if target.empty:
        return {"ok": False, "message": "Event not found", "content": None}

    item = df_to_records(target.head(1))[0]
    content = social_writer.generate_social_content(
        title=str(item.get("title") or ""),
        ai_summary=str(item.get("ai_summary") or item.get("raw_summary") or ""),
        source=str(item.get("source") or "Unknown"),
    )
    if not content:
        return {"ok": False, "message": "Social generation failed", "content": None}
    return {"ok": True, "message": "Generated", "content": content}
