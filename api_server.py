from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.analyzer import EventAnalyzer
from ai.social_writer import SocialMediaWriter
from collectors.gdelt_collector import GDELTCollector
from collectors.rss_collector import RSSCollector
from backend.demo_loader import load_demo_if_empty
from db.database import Database
from services.correlation import EventCorrelator
from services.event_aggregator import EventAggregator
from services.rule_geotagger import RuleBasedGeotagger
from services.risk_score import RiskScorer
from services.task_control import TaskControl


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


db = Database("storage/worldpulse.db")
task_control = TaskControl()
collector = RSSCollector(db, task_control=task_control)
gdelt_collector = GDELTCollector(db, task_control=task_control)
analyzer = EventAnalyzer(db)
social_writer = SocialMediaWriter()
risk_scorer = RiskScorer(db)
correlator = EventCorrelator(db)
aggregator = EventAggregator(db)
rule_geotagger = RuleBasedGeotagger(db, task_control=task_control)

app = FastAPI(title="WorldPulse Trade API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    return filtered


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    safe_df = df.where(pd.notnull(df), None)
    return safe_df.to_dict(orient="records")


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
    "other": "其他",
}


def category_label(category: str | None) -> str:
    return CATEGORY_LABELS.get(category or "other", category or "其他")


def build_trade_brief(df: pd.DataFrame, clusters: list[dict[str, Any]]) -> str:
    total = int(len(df))
    high = int(len(df[df["risk_level"].isin(["high", "critical"])])) if "risk_level" in df.columns else 0
    countries = sorted_unique_values(df, "country")[:5]
    category_counts = df["category"].fillna("other").value_counts().head(5) if "category" in df.columns else []
    category_names = [category_label(str(name)) for name in getattr(category_counts, "index", [])]
    top_cluster_titles = [str(item.get("title") or "") for item in clusters[:3] if item.get("title")]
    focus = "、".join(top_cluster_titles) if top_cluster_titles else "美国清关政策、红海航运、平台新规"

    return "\n".join(
        [
            "今日出海风险简报：",
            f"- 今日监测到 {total} 条经营风险事件",
            f"- 高风险事件 {high} 条",
            f"- 重点地区：{'、'.join(countries) if countries else '暂无'}",
            f"- 重点影响方向：{'、'.join(category_names) if category_names else '暂无'}",
            f"- 建议关注：{focus}",
        ]
    )


def build_clusters_from_events(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    grouped: list[dict[str, Any]] = []
    risk_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    for _, group in df.groupby([df["country"].fillna("Unknown"), df["category"].fillna("other")]):
        records = df_to_records(group.sort_values(by="published_at", ascending=False))
        sample = max(records, key=lambda item: (risk_rank.get(item.get("risk_level") or "low", 1), int(item.get("severity") or 1)))
        sources = {item.get("source") for item in records if item.get("source")}
        score = min(100, int(sample.get("severity") or 1) * 18 + len(records) * 5 + len(sources) * 4)
        grouped.append(
            {
                "id": f"cluster-{sample.get('country')}-{sample.get('category')}",
                "title": f"{sample.get('country') or 'Unknown'} · {category_label(sample.get('category'))}",
                "summary": sample.get("ai_summary") or sample.get("raw_summary") or "",
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
    return {"ok": True, "name": "WorldPulse Trade"}


@app.post("/collect", response_model=ActionResponse)
def collect_news() -> ActionResponse:
    task_control.reset()
    rss_count = collector.collect()
    if task_control.is_cancelled():
        return ActionResponse(ok=False, message=f"Collection cancelled. RSS: {rss_count}.", count=rss_count)
    cluster_count = aggregator.rebuild_recent_clusters()
    return ActionResponse(
        ok=True,
        message=f"采集完成。RSS: {rss_count}, 事件簇: {cluster_count}.",
        count=rss_count,
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
def analyze_single_event(event_id: str) -> dict[str, Any]:
    item = analyzer.analyze_event(event_id)
    if not item:
        return {"ok": False, "message": "Analysis failed", "item": None}
    aggregator.rebuild_recent_clusters()
    return {"ok": True, "message": "分析完成", "item": item}


@app.get("/events")
def get_events(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$"),
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
    df = load_events_df()
    df = apply_time_filter(df, time_range)

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

    total = int(len(df))
    start = (page - 1) * page_size
    end = start + page_size
    paged = df.iloc[start:end]

    return {
        "items": df_to_records(paged),
        "count": int(len(paged)),
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": end < total,
        "has_prev": page > 1,
    }


@app.get("/map-events")
def get_map_events(
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$"),
    category: str | None = None,
    country: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    source: str | None = None,
    status: str | None = Query(default=None, pattern="^(raw|analyzed|failed)$"),
    sort_by: str = Query(default="published_at", pattern="^(published_at|severity|risk_level|source|country|category)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> dict[str, Any]:
    df = load_events_df()
    df = apply_time_filter(df, time_range)

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
        "items": df_to_records(df),
        "total": int(len(df)),
    }


@app.get("/filters")
def get_filters(time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$")) -> dict[str, list[str]]:
    df = apply_time_filter(load_events_df(), time_range)
    return {
        "countries": sorted_unique_values(df, "country"),
        "categories": sorted_unique_values(df, "category"),
        "sources": sorted_unique_values(df, "source"),
        "risk_levels": ["low", "medium", "high", "critical"],
        "statuses": ["raw", "analyzed", "failed"],
    }


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics(time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$")) -> MetricsResponse:
    df = apply_time_filter(load_events_df(), time_range)
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
    clusters_df = apply_cluster_time_filter(load_clusters_df(), time_range)
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
def get_brief(time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$")) -> dict[str, Any]:
    df = apply_time_filter(load_events_df(), time_range)
    if df.empty:
        return {"brief": "今日出海风险简报：当前范围内暂无经营风险事件。", "clusters": [], "convergences": []}

    clusters_df = apply_cluster_time_filter(load_clusters_df(), time_range)
    cluster_records = df_to_records(clusters_df)
    if not cluster_records:
        cluster_records = build_clusters_from_events(df)
    event_records = df_to_records(df)
    brief = build_trade_brief(df, cluster_records)
    convergences = correlator.detect_convergences(event_records)
    return {
        "brief": brief,
        "convergences": convergences,
        "clusters": cluster_records[:30],
    }


@app.get("/country-insight")
def get_country_insight(
    country: str = Query(..., min_length=1),
    time_range: str = Query(default="24h", pattern="^(1h|24h|7d|all)$"),
) -> dict[str, Any]:
    df = apply_time_filter(load_events_df(), time_range)
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
    return {"ok": True, "item": item, "related": df_to_records(related)}


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
