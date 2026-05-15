import "./style.css";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type EventItem = {
  id: string;
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  ai_summary: string | null;
  raw_summary: string | null;
  category: string | null;
  country: string | null;
  city: string | null;
  location_scope: string | null;
  location_confidence: number | null;
  location_reason: string | null;
  lat: number | null;
  lon: number | null;
  severity: number | null;
  confidence?: number | null;
  risk_level: "low" | "medium" | "high" | "critical" | null;
  affected_groups?: string | string[] | null;
  business_impact?: string | null;
  suggested_action?: string | null;
  social_angle?: string | null;
  status: "raw" | "analyzed" | "failed" | null;
  risk_score?: number | null;
  event_count?: number | null;
  source_count?: number | null;
  gdelt_count?: number | null;
  rss_count?: number | null;
  summary?: string | null;
  last_seen?: string | null;
};

type Metrics = {
  total_events: number;
  total_clusters: number;
  analyzed_events: number;
  high_risk_events: number;
  unique_countries: number;
  strategic_risk_index: number;
};

type BriefResponse = {
  brief: string;
  clusters?: EventItem[];
  convergences: Array<{
    lat: number;
    lon: number;
    count: number;
    types: string[];
    country: string;
    city: string;
    severity: number;
  }>;
};

type MapEventsResponse = {
  items: EventItem[];
  total: number;
};

type SingleAnalyzeResponse = {
  ok: boolean;
  message: string;
  item: EventItem | null;
};

type FiltersResponse = {
  countries: string[];
  categories: string[];
  sources: string[];
  risk_levels: string[];
  statuses: string[];
};

type CountryInsight = {
  country: string;
  total_events: number;
  high_risk_events: number;
  categories: Array<{ category: string; count: number }>;
  risk_distribution: Array<{ risk_level: "low" | "medium" | "high" | "critical"; count: number }>;
  daily_trend: Array<{ date: string; count: number }>;
  latest_events: EventItem[];
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "http://localhost:8000";

const appEl = document.querySelector<HTMLDivElement>("#app");
if (!appEl) throw new Error("App container not found");

type Language = "zh" | "en";
type I18nKey =
  | "subtitle"
  | "collect"
  | "analyze"
  | "refresh"
  | "stop"
  | "allCountries"
  | "allCategories"
  | "allRisks"
  | "allStatus"
  | "sortTime"
  | "sortRisk"
  | "sortSeverity"
  | "desc"
  | "asc"
  | "mapTitle"
  | "low"
  | "medium"
  | "high"
  | "critical"
  | "cluster"
  | "countryFocus"
  | "clear"
  | "countryEmpty"
  | "briefTitle"
  | "loading"
  | "mappedSignal"
  | "mappedSignals"
  | "strategicRisk"
  | "totalEvents"
  | "totalClusters"
  | "analyzed"
  | "highRisk"
  | "countries"
  | "noConvergence"
  | "events"
  | "mixed"
  | "unknown"
  | "noSummary"
  | "other"
  | "noTrend"
  | "noDataPrefix"
  | "currentRange"
  | "total"
  | "categories"
  | "dailyTrend"
  | "apiUnreachable"
  | "collecting"
  | "analyzing"
  | "analyzingOne"
  | "collectionDone"
  | "analysisDone"
  | "actionFailed"
  | "cancelling"
  | "cancelRequested"
  | "analysisPanel"
  | "clickMapPoint"
  | "openOriginal"
  | "metricHint"
  | "metricSelected";

const i18n: Record<Language, Record<I18nKey, string>> = {
  zh: {
    subtitle: "出海经营风险雷达",
    collect: "采集",
    analyze: "轻量标记",
    refresh: "刷新",
    stop: "终止",
    allCountries: "全部国家",
    allCategories: "全部分类",
    allRisks: "全部风险",
    allStatus: "全部状态",
    sortTime: "排序：时间",
    sortRisk: "排序：风险",
    sortSeverity: "排序：严重度",
    desc: "降序",
    asc: "升序",
    mapTitle: "全球经营风险地图",
    low: "低",
    medium: "中",
    high: "高",
    critical: "严重",
    cluster: "聚合",
    countryFocus: "国家聚焦",
    clear: "清除",
    countryEmpty: "选择地图点查看国家/地区经营风险。",
    briefTitle: "今日出海风险简报",
    loading: "加载中...",
    mappedSignal: "个地图风险",
    mappedSignals: "个地图风险",
    strategicRisk: "战略风险",
    totalEvents: "事件总数",
    totalClusters: "事件簇",
    analyzed: "已分析",
    highRisk: "高风险",
    countries: "国家数",
    noConvergence: "暂无收敛信号。",
    events: "条经营风险",
    mixed: "混合",
    unknown: "未知",
    noSummary: "暂无摘要。",
    other: "其他",
    noTrend: "暂无趋势点。",
    noDataPrefix: "当前范围内暂无",
    currentRange: "的数据。",
    total: "总数",
    categories: "分类",
    dailyTrend: "每日趋势",
    apiUnreachable: "后端未启动，请运行 start.bat 或启动 uvicorn backend.main:app --reload --port 8000",
    collecting: "正在采集经营风险信息...",
    analyzing: "正在进行轻量地图标记...",
    analyzingOne: "正在生成这条事件的业务影响分析...",
    collectionDone: "采集完成",
    analysisDone: "地图定位完成",
    actionFailed: "操作失败",
    cancelling: "正在请求终止...",
    cancelRequested: "已请求终止",
    analysisPanel: "业务影响分析",
    clickMapPoint: "点击地图点查看业务影响分析。",
    openOriginal: "打开原文",
    metricHint: "点击查看相关信号",
    metricSelected: "已聚焦指标",
  },
  en: {
    subtitle: "Trade Risk Radar",
    collect: "Collect",
    analyze: "Map Tags",
    refresh: "Refresh",
    stop: "Stop",
    allCountries: "All Countries",
    allCategories: "All Categories",
    allRisks: "All Risks",
    allStatus: "All Status",
    sortTime: "Sort: Time",
    sortRisk: "Sort: Risk",
    sortSeverity: "Sort: Severity",
    desc: "Desc",
    asc: "Asc",
    mapTitle: "Global Trade Risk Map",
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
    cluster: "Cluster",
    countryFocus: "Country Focus",
    clear: "Clear",
    countryEmpty: "Select a map point to inspect country-level signals.",
    briefTitle: "Daily Trade Risk Brief",
    loading: "Loading...",
    mappedSignal: "mapped signal",
    mappedSignals: "mapped signals",
    strategicRisk: "Strategic Risk",
    totalEvents: "Total Events",
    totalClusters: "Clusters",
    analyzed: "Analyzed",
    highRisk: "High Risk",
    countries: "Countries",
    noConvergence: "No convergence signals.",
    events: "events",
    mixed: "Mixed",
    unknown: "Unknown",
    noSummary: "No summary available.",
    other: "other",
    noTrend: "No trend points.",
    noDataPrefix: "No data for",
    currentRange: "in current range.",
    total: "Total",
    categories: "Categories",
    dailyTrend: "Daily Trend",
    apiUnreachable: "Backend is not running. Run start.bat or uvicorn backend.main:app --reload --port 8000",
    collecting: "Collecting news...",
    analyzing: "Analyzing intelligence...",
    analyzingOne: "Analyzing this signal...",
    collectionDone: "Collection completed",
    analysisDone: "Map tagging completed",
    actionFailed: "Action failed",
    cancelling: "Requesting stop...",
    cancelRequested: "Stop requested",
    analysisPanel: "Business Impact",
    clickMapPoint: "Click a map point to inspect business impact.",
    openOriginal: "Open Original",
    metricHint: "Click to inspect related signals",
    metricSelected: "Metric focused",
  },
};

let currentLanguage: Language = localStorage.getItem("worldpulse-language") === "en" ? "en" : "zh";

function t(key: I18nKey): string {
  return i18n[currentLanguage][key];
}

appEl.innerHTML = `
  <main class="dashboard">
    <header class="topbar">
      <div>
        <h1>WorldPulse Trade</h1>
        <p data-i18n="subtitle">${t("subtitle")}</p>
        <p class="product-copy">自动监控全球政策、物流、平台规则、战争制裁与市场波动，并转换成中文业务影响分析。</p>
      </div>
      <div class="actions">
        <select id="languageSelect" aria-label="Language">
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
        <select id="timeRange">
          <option value="1h">1小时</option>
          <option value="24h" selected>24小时</option>
          <option value="7d">7天</option>
          <option value="all">全部</option>
        </select>
        <button id="collectBtn" data-i18n="collect">${t("collect")}</button>
        <button id="analyzeBtn" data-i18n="analyze">${t("analyze")}</button>
        <button id="cancelBtn" class="danger-btn" data-i18n="stop" disabled>${t("stop")}</button>
        <button id="refreshBtn" data-i18n="refresh">${t("refresh")}</button>
      </div>
    </header>
    <div id="statusBar" class="status-bar" role="status" aria-live="polite"></div>
    <section class="filters">
      <select id="countryFilter"><option value="">${t("allCountries")}</option></select>
      <select id="categoryFilter"><option value="">${t("allCategories")}</option></select>
      <select id="riskFilter"><option value="">${t("allRisks")}</option></select>
      <select id="statusFilter"><option value="">${t("allStatus")}</option></select>
      <select id="sortBy">
        <option value="published_at" selected>${t("sortTime")}</option>
        <option value="risk_level">${t("sortRisk")}</option>
        <option value="severity">${t("sortSeverity")}</option>
      </select>
      <select id="sortOrder">
        <option value="desc" selected>${t("desc")}</option>
        <option value="asc">${t("asc")}</option>
      </select>
    </section>
    <section class="metrics" id="metrics"></section>
    <section class="map-workspace">
      <article class="map-panel">
        <div class="map-titlebar">
          <div>
            <h2 data-i18n="mapTitle">${t("mapTitle")}</h2>
            <span id="mapCount">0 ${t("mappedSignals")}</span>
          </div>
          <div class="map-controls">
            <label><input type="checkbox" id="layerLow" checked /> <span data-i18n="low">${t("low")}</span></label>
            <label><input type="checkbox" id="layerMedium" checked /> <span data-i18n="medium">${t("medium")}</span></label>
            <label><input type="checkbox" id="layerHigh" checked /> <span data-i18n="high">${t("high")}</span></label>
            <label><input type="checkbox" id="layerCritical" checked /> <span data-i18n="critical">${t("critical")}</span></label>
            <label><input type="checkbox" id="clusterMode" checked /> <span data-i18n="cluster">${t("cluster")}</span></label>
          </div>
        </div>
        <div id="map"></div>
      </article>
      <aside class="panel country-panel">
        <div class="country-head">
          <h2 data-i18n="countryFocus">${t("countryFocus")}</h2>
          <button id="clearCountryBtn" class="tiny-btn" data-i18n="clear">${t("clear")}</button>
        </div>
        <div id="countryDetail">${t("countryEmpty")}</div>
      </aside>
      <aside class="panel keyword-panel">
        <div class="country-head">
          <h2>关键词关注</h2>
          <button id="saveKeywordsBtn" class="tiny-btn">保存</button>
        </div>
        <textarea id="keywordInput" rows="5" spellcheck="false"></textarea>
        <div id="keywordHitBox" class="keyword-hit">你关注的关键词今日命中 0 条事件</div>
      </aside>
    </section>
    <aside class="floating-panel analysis-float open" id="analysisFloat">
      <div class="floating-head">
        <h2 data-i18n="analysisPanel">${t("analysisPanel")}</h2>
        <button id="closeAnalysisBtn" class="tiny-btn">关闭</button>
      </div>
      <div id="analysisDetail" class="floating-body">${t("clickMapPoint")}</div>
    </aside>
    <aside class="floating-panel brief-float open" id="briefFloat">
      <div class="floating-head">
        <h2 data-i18n="briefTitle">${t("briefTitle")}</h2>
        <button id="closeBriefBtn" class="tiny-btn">关闭</button>
      </div>
      <div class="floating-body">
        <div id="briefText">${t("loading")}</div>
        <div id="convergenceList"></div>
      </div>
    </aside>
  </main>
`;

const metricsEl = document.getElementById("metrics") as HTMLDivElement;
const briefEl = document.getElementById("briefText") as HTMLDivElement;
const convergenceEl = document.getElementById("convergenceList") as HTMLDivElement;
const countryDetailEl = document.getElementById("countryDetail") as HTMLDivElement;
const analysisDetailEl = document.getElementById("analysisDetail") as HTMLDivElement;
const analysisFloatEl = document.getElementById("analysisFloat") as HTMLElement;
const briefFloatEl = document.getElementById("briefFloat") as HTMLElement;
const closeAnalysisBtn = document.getElementById("closeAnalysisBtn") as HTMLButtonElement;
const closeBriefBtn = document.getElementById("closeBriefBtn") as HTMLButtonElement;
const mapCountEl = document.getElementById("mapCount") as HTMLSpanElement;
const statusBarEl = document.getElementById("statusBar") as HTMLDivElement;
const keywordInputEl = document.getElementById("keywordInput") as HTMLTextAreaElement;
const keywordHitBoxEl = document.getElementById("keywordHitBox") as HTMLDivElement;
const saveKeywordsBtn = document.getElementById("saveKeywordsBtn") as HTMLButtonElement;

const languageSelectEl = document.getElementById("languageSelect") as HTMLSelectElement;
const timeRangeEl = document.getElementById("timeRange") as HTMLSelectElement;
const countryFilterEl = document.getElementById("countryFilter") as HTMLSelectElement;
const categoryFilterEl = document.getElementById("categoryFilter") as HTMLSelectElement;
const riskFilterEl = document.getElementById("riskFilter") as HTMLSelectElement;
const statusFilterEl = document.getElementById("statusFilter") as HTMLSelectElement;
const sortByEl = document.getElementById("sortBy") as HTMLSelectElement;
const sortOrderEl = document.getElementById("sortOrder") as HTMLSelectElement;

const collectBtn = document.getElementById("collectBtn") as HTMLButtonElement;
const analyzeBtn = document.getElementById("analyzeBtn") as HTMLButtonElement;
const cancelBtn = document.getElementById("cancelBtn") as HTMLButtonElement;
const refreshBtn = document.getElementById("refreshBtn") as HTMLButtonElement;
const clearCountryBtn = document.getElementById("clearCountryBtn") as HTMLButtonElement;
const layerLowEl = document.getElementById("layerLow") as HTMLInputElement;
const layerMediumEl = document.getElementById("layerMedium") as HTMLInputElement;
const layerHighEl = document.getElementById("layerHigh") as HTMLInputElement;
const layerCriticalEl = document.getElementById("layerCritical") as HTMLInputElement;
const clusterModeEl = document.getElementById("clusterMode") as HTMLInputElement;

let activeCountry: string | null = null;
let mapMarkers: maplibregl.Marker[] = [];
let latestRenderedEvents: EventItem[] = [];
let latestMapTotal = 0;
let hoverPopup: maplibregl.Popup | null = null;
let activeAction: "/collect" | "/geotag" | null = null;
let activeActionController: AbortController | null = null;
let briefSortKey: "risk_score" | "last_seen" | "source_count" | "event_count" = "risk_score";
const DEFAULT_KEYWORDS = ["Amazon", "TikTok Shop", "Temu", "关税", "美国海关", "红海", "DHL", "FedEx", "Shopee", "越南", "墨西哥"];

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "&copy; OpenStreetMap contributors",
      },
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }],
  },
  center: [0, 20],
  zoom: 1.6,
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

function riskColor(risk: EventItem["risk_level"]): string {
  if (risk === "critical") return "#d62828";
  if (risk === "high") return "#f77f00";
  if (risk === "medium") return "#2a9d8f";
  return "#457b9d";
}

function riskText(value: string | null | undefined): string {
  if (value === "critical") return t("critical");
  if (value === "high") return t("high");
  if (value === "medium") return t("medium");
  return t("low");
}

function statusText(value: string | null | undefined): string {
  if (value === "analyzed") return currentLanguage === "zh" ? "已分析" : "Analyzed";
  if (value === "failed") return currentLanguage === "zh" ? "失败" : "Failed";
  return currentLanguage === "zh" ? "未分析" : "Raw";
}

function categoryText(value: string | null | undefined): string {
  const zh: Record<string, string> = {
    tariff_policy: "关税政策",
    customs_clearance: "海关清关",
    logistics_delay: "物流延误",
    port_disruption: "港口/航运中断",
    platform_policy: "平台规则",
    sanctions_conflict: "制裁/冲突",
    currency_oil: "汇率/油价",
    supply_chain: "供应链",
    market_demand: "市场需求",
    compliance: "合规监管",
    politics: "政策",
    conflict: "制裁/冲突",
    finance: "汇率/油价",
    disaster: "物流中断",
    technology: "供应链",
    society: "市场需求",
    health: "合规监管",
    energy: "汇率/油价",
    other: "其他",
    world: "国际",
  };
  if (currentLanguage === "zh") return zh[value || "other"] || value || "其他";
  return value || "other";
}

function categoriesText(values: string[]): string {
  return values.map((value) => categoryText(value.toLowerCase())).join("、");
}

function locationText(country: string | null | undefined, city: string | null | undefined): string {
  return `${country || t("unknown")} · ${city || "无城市"}`;
}

function affectedGroupsText(value: EventItem["affected_groups"]): string {
  if (Array.isArray(value)) return value.join("、");
  if (!value) return "跨境电商卖家、外贸企业、物流货代";
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) return parsed.join("、");
  } catch {
    // Keep plain strings from older API responses.
  }
  return value;
}

function businessImpactText(event: EventItem): string {
  return event.business_impact || "该事件可能影响相关地区的跨境经营，请点击分析获取具体影响。";
}

function suggestedActionText(event: EventItem): string {
  return event.suggested_action || "建议先关注物流渠道、清关资料、平台公告和利润测算变化。";
}

function displayTitle(event: EventItem): string {
  if (event.ai_summary) return event.ai_summary;
  if (currentLanguage === "zh" && event.summary && /[\u4e00-\u9fa5]/.test(event.summary)) return event.summary;
  return localizeHeadline(event.title);
}

function localizeHeadline(title: string): string {
  if (currentLanguage !== "zh") return title;
  let text = title;
  const replacements: Array<[RegExp, string]> = [
    [/\bTrump\b/gi, "特朗普"],
    [/\bChina\b/gi, "中国"],
    [/\bChinese\b/gi, "中国"],
    [/\bUK\b/g, "英国"],
    [/\bUnited Kingdom\b/gi, "英国"],
    [/\bBritain\b/gi, "英国"],
    [/\bStarmer\b/gi, "斯塔默"],
    [/\bKing Charles\b/gi, "查尔斯国王"],
    [/\bNissan\b/gi, "日产"],
    [/\bJPMorgan\b/gi, "摩根大通"],
    [/\bAI\b/g, "AI"],
    [/\bleadership battle\b/gi, "领导权之争"],
    [/\bto begin\b/gi, "将开始"],
    [/\bbuilding cars\b/gi, "生产汽车"],
    [/\brivals\b/gi, "竞争对手"],
    [/\bcomes at an awkward time\b/gi, "时机尴尬"],
    [/\bwarns\b/gi, "警告"],
    [/\bmay rethink\b/gi, "可能重新考虑"],
    [/\bLondon office\b/gi, "伦敦办公室"],
    [/\bBond markets on edge\b/gi, "债券市场紧张"],
    [/\bfragile government\b/gi, "脆弱政府"],
    [/\bagenda\b/gi, "议程"],
    [/\bThursday\b/gi, "周四"],
    [/\bRussia-Ukraine War\b/gi, "俄乌战争"],
    [/\bUkraine\b/gi, "乌克兰"],
    [/\bRussia\b/gi, "俄罗斯"],
    [/\bIran war\b/gi, "伊朗战争"],
    [/\bIsraeli base\b/gi, "以色列基地"],
    [/\bIraq\b/gi, "伊拉克"],
    [/\bWhat we know\b/gi, "已知情况"],
    [/\bAnalysis:\s*/gi, "分析："],
    [/\bShows\b/gi, "显示"],
    [/\bCease-Fires\b/gi, "停火"],
    [/\bHave Lost Meaning\b/gi, "已失去意义"],
    [/\bUnder Trump\b/gi, "在特朗普时期"],
    [/\bhangs over\b/gi, "笼罩"],
    [/\bChina trip\b/gi, "中国之行"],
    [/\band his presidency\b/gi, "及其总统任期"],
    [/\bA secret\b/gi, "秘密"],
    [/\bMore than\b/gi, "超过"],
    [/\bconfined on cruise ship\b/gi, "被困邮轮"],
    [/\bafter suspected\b/gi, "疑似事件后"],
    [/\bnorovirus death\b/gi, "诺如病毒死亡事件"],
    [/\bEurope live\b/gi, "欧洲实时动态"],
  ];
  for (const [pattern, replacement] of replacements) {
    text = text.replace(pattern, replacement);
  }
  return text;
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

async function postJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", signal });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

function setActionButtonsBusy(isBusy: boolean): void {
  collectBtn.disabled = isBusy;
  analyzeBtn.disabled = isBusy;
  refreshBtn.disabled = isBusy;
  cancelBtn.disabled = !isBusy;
}

function showStatus(message: string, tone: "idle" | "working" | "success" | "error" = "idle"): void {
  statusBarEl.textContent = message;
  statusBarEl.className = `status-bar ${tone}`;
}

function renderMetrics(metrics: Metrics): void {
  const cards = [
    { action: "all", label: "经营风险", value: metrics.total_events.toString(), hint: "清空筛选，恢复全球经营风险地图", level: "calm" },
    { action: "high-risk", label: "高风险", value: metrics.high_risk_events.toString(), hint: "只显示高风险和严重风险事件", level: metrics.high_risk_events > 0 ? "hot" : "calm" },
    { action: "logistics", label: "物流/港口", value: "物流", hint: "聚焦物流延误、港口罢工、航运中断", level: "watch" },
    { action: "platform", label: "平台规则", value: "平台", hint: "聚焦 Amazon、TikTok Shop、Temu、Shopee 等平台规则", level: "calm" },
    { action: "clusters", label: "风险簇", value: metrics.total_clusters.toString(), hint: "开启聚合模式，按国家和业务分类查看", level: "calm" },
    { action: "countries", label: "涉及国家", value: metrics.unique_countries.toString(), hint: "清空筛选并缩放到所有涉及国家", level: "watch" },
  ];
  metricsEl.innerHTML = cards
    .map(
      (card) => `
      <button class="metric-card ${card.level}" data-metric="${card.label}" data-action="${card.action}" title="${t("metricHint")}">
        <div class="metric-label">${card.label}</div>
        <div class="metric-value">${card.value}</div>
        <div class="metric-hint">${card.hint}</div>
      </button>
    `,
    )
    .join("");
}

function resetSignalFilters(): void {
  countryFilterEl.value = "";
  categoryFilterEl.value = "";
  riskFilterEl.value = "";
  statusFilterEl.value = "";
  sortByEl.value = "published_at";
  sortOrderEl.value = "desc";
  activeCountry = null;
}

function setSelectValue(selectEl: HTMLSelectElement, value: string): void {
  if (![...selectEl.options].some((option) => option.value === value)) {
    selectEl.add(new Option(categoryText(value), value));
  }
  selectEl.value = value;
}

function visibleMapEvents(): EventItem[] {
  const activeRisks = new Set<string>();
  if (layerLowEl.checked) activeRisks.add("low");
  if (layerMediumEl.checked) activeRisks.add("medium");
  if (layerHighEl.checked) activeRisks.add("high");
  if (layerCriticalEl.checked) activeRisks.add("critical");
  return latestRenderedEvents
    .filter((event) => activeRisks.has((event.risk_level || "low").toLowerCase()))
    .filter((event) => typeof event.lat === "number" && typeof event.lon === "number");
}

function fitMapToEvents(events = visibleMapEvents()): void {
  if (!events.length) return;
  const bounds = new maplibregl.LngLatBounds();
  events.forEach((event) => bounds.extend([event.lon as number, event.lat as number]));
  if (events.length === 1) {
    map.flyTo({ center: [events[0].lon as number, events[0].lat as number], zoom: 4, essential: true });
    return;
  }
  map.fitBounds(bounds, { padding: 70, maxZoom: 5, duration: 700 });
}

async function applyMetricAction(action: string): Promise<void> {
  if (action === "all") {
    resetSignalFilters();
    countryDetailEl.innerHTML = t("countryEmpty");
    await loadFilters();
    await loadDashboard();
    fitMapToEvents();
    showStatus("已显示全部地图信号", "success");
    return;
  }

  if (action === "high-risk") {
    riskFilterEl.value = "high";
    statusFilterEl.value = "";
    sortByEl.value = "severity";
    sortOrderEl.value = "desc";
    layerLowEl.checked = false;
    layerMediumEl.checked = false;
    layerHighEl.checked = true;
    layerCriticalEl.checked = true;
    await loadDashboard();
    fitMapToEvents();
    showStatus("已聚焦高风险信号", "success");
    return;
  }

  if (action === "logistics") {
    resetSignalFilters();
    setSelectValue(categoryFilterEl, "logistics_delay");
    layerLowEl.checked = true;
    layerMediumEl.checked = true;
    layerHighEl.checked = true;
    layerCriticalEl.checked = true;
    sortByEl.value = "published_at";
    sortOrderEl.value = "desc";
    await loadDashboard();
    fitMapToEvents();
    showStatus("已筛选物流延误相关事件", "success");
    return;
  }

  if (action === "platform") {
    resetSignalFilters();
    setSelectValue(categoryFilterEl, "platform_policy");
    sortByEl.value = "severity";
    sortOrderEl.value = "desc";
    layerLowEl.checked = false;
    layerMediumEl.checked = true;
    layerHighEl.checked = true;
    layerCriticalEl.checked = true;
    await loadDashboard();
    fitMapToEvents();
    showStatus("已筛选平台规则相关事件", "success");
    return;
  }

  if (action === "analyzed") {
    statusFilterEl.value = "analyzed";
    await loadDashboard();
    fitMapToEvents();
    showStatus("已筛选已分析信号", "success");
    return;
  }

  if (action === "clusters") {
    clusterModeEl.checked = true;
    renderMap(latestRenderedEvents);
    fitMapToEvents();
    showStatus("已开启事件聚合视图", "success");
    return;
  }

  if (action === "countries") {
    resetSignalFilters();
    await loadFilters();
    await loadDashboard();
    fitMapToEvents();
    showStatus("已缩放至全部涉及国家", "success");
    return;
  }

  if (action === "strategic") {
    sortByEl.value = "severity";
    sortOrderEl.value = "desc";
    clusterModeEl.checked = true;
    await loadDashboard();
    fitMapToEvents();
    showStatus("已按战略风险视角重排地图", "success");
  }
}

function renderConvergences(convergences: BriefResponse["convergences"]): void {
  if (!convergences.length) {
    convergenceEl.innerHTML = `<div class="convergence-empty">${t("noConvergence")}</div>`;
    return;
  }
  convergenceEl.innerHTML = convergences
    .slice(0, 6)
    .map((item) => {
      const types = categoriesText(item.types);
      return `<div class="convergence-item"><strong>${item.country}</strong> · ${item.city || "无城市"} · 严重度 ${item.severity}<br/><span>${types}</span></div>`;
    })
    .join("");
}

function renderBriefTable(clusters: EventItem[] = [], briefText = ""): void {
  if (!clusters.length) {
    briefEl.innerHTML = `<pre class="brief-copy">${briefText || "暂无可展示的风险简报。"}</pre><div class="brief-empty">暂无可展示的事件簇。</div>`;
    return;
  }
  const sorted = [...clusters].sort((a, b) => {
    if (briefSortKey === "last_seen") {
      return String(b.last_seen || "").localeCompare(String(a.last_seen || ""));
    }
    return Number(b[briefSortKey] || 0) - Number(a[briefSortKey] || 0);
  });

  briefEl.innerHTML = `
    <pre class="brief-copy">${briefText}</pre>
    <table class="brief-table">
      <thead>
        <tr>
          <th><button data-sort="risk_score">风险</button></th>
          <th>地点</th>
          <th>经营风险</th>
          <th><button data-sort="source_count">来源</button></th>
          <th><button data-sort="event_count">报道</button></th>
          <th><button data-sort="last_seen">时间</button></th>
        </tr>
      </thead>
      <tbody>
        ${sorted
          .map(
            (item) => `
          <tr data-event-id="${item.id}">
            <td><span class="risk-chip" style="background:${riskColor(item.risk_level)}">${riskText(item.risk_level)}</span><b>${item.risk_score || 0}</b></td>
            <td>${item.country || t("unknown")}<small>${item.city || "无城市"}</small></td>
            <td><strong>${displayTitle(item)}</strong><small>${categoryText(item.category)}</small></td>
            <td>${item.source_count || 1}<small>RSS ${item.rss_count || 0} / GDELT ${item.gdelt_count || 0}</small></td>
            <td>${item.event_count || 1}</td>
            <td>${item.last_seen ? new Date(item.last_seen).toLocaleDateString() : "未知"}</td>
          </tr>
        `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderMap(events: EventItem[]): void {
  latestRenderedEvents = events;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
  const activeRisks = new Set<string>();
  if (layerLowEl.checked) activeRisks.add("low");
  if (layerMediumEl.checked) activeRisks.add("medium");
  if (layerHighEl.checked) activeRisks.add("high");
  if (layerCriticalEl.checked) activeRisks.add("critical");

  const visible = events
    .filter((e) => activeRisks.has((e.risk_level || "low").toLowerCase()))
    .filter((event) => typeof event.lat === "number" && typeof event.lon === "number")

  const points = clusterModeEl.checked ? clusterEvents(visible) : visible.map((v) => ({ kind: "single" as const, event: v }));

  points.forEach((point) => {
    if (point.kind === "cluster") {
      const dot = document.createElement("button");
      dot.className = "map-dot cluster-dot";
      dot.style.width = "24px";
      dot.style.height = "24px";
      dot.textContent = String(point.count);
      dot.title = `${point.count} ${t("events")}`;
      dot.addEventListener("click", () => {
        if (point.sample.country) setActiveCountry(point.sample.country);
        renderClusterDetail(point.events);
      });
      const popup = new maplibregl.Popup({ offset: 8 }).setHTML(`<strong>${point.count} ${t("events")}</strong><br/>${point.sample.country || t("mixed")} ${t("cluster").toLowerCase()}`);
      const marker = new maplibregl.Marker({ element: dot, anchor: "center" })
        .setLngLat([point.lon, point.lat])
        .setPopup(popup)
        .addTo(map);
      mapMarkers.push(marker);
      return;
    }
    const event = point.event;
      const dot = document.createElement("button");
      dot.className = "map-dot";
      const size = Math.max(10, (event.severity || 1) * 4);
      dot.style.width = `${size}px`;
      dot.style.height = `${size}px`;
      dot.style.background = riskColor(event.risk_level);
      dot.title = `${displayTitle(event)} (${event.country || t("unknown")})`;
      dot.addEventListener("mouseenter", () => showEventPopup(event));
      dot.addEventListener("mouseleave", hideEventPopup);
      dot.addEventListener("click", () => {
        if (event.country) setActiveCountry(event.country);
        void analyzeMapEvent(event);
      });

      const marker = new maplibregl.Marker({ element: dot, anchor: "center" })
        .setLngLat([event.lon as number, event.lat as number])
        .addTo(map);
      mapMarkers.push(marker);
  });
}

function renderAnalysisDetail(event: EventItem, isLoading = false): void {
  analysisFloatEl.classList.add("open");
  const summary = event.ai_summary || event.summary || event.raw_summary || t("noSummary");
  const impact = businessImpactText(event);
  const action = suggestedActionText(event);
  analysisDetailEl.innerHTML = `
      <div class="analysis-card">
      <div class="event-header">
        <span class="pill" style="background:${riskColor(event.risk_level)}">${riskText(event.risk_level)}</span>
        <span>${event.source}</span>
        <span>${statusText(event.status)}</span>
      </div>
      <h3>${displayTitle(event)}</h3>
      ${displayTitle(event) !== event.title ? `<div class="original-title">${event.title}</div>` : ""}
      <p>${isLoading ? t("analyzingOne") : summary}</p>
      <div class="analysis-meta">
        <span>国家/城市：${locationText(event.country, event.city)}</span>
        <span>业务分类：${categoryText(event.category)} · 严重度 ${event.severity || 1}</span>
        <span>影响对象：${affectedGroupsText(event.affected_groups)}</span>
        ${typeof event.confidence === "number" ? `<span>置信度 ${Math.round(event.confidence * 100)}%</span>` : ""}
      </div>
      <div class="analysis-note"><strong>可能影响</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>建议动作</strong><br/>${action}</div>
      ${event.location_reason ? `<div class="analysis-note">${event.location_reason}</div>` : ""}
      ${event.social_angle ? `<div class="analysis-note">${event.social_angle}</div>` : ""}
      <a class="analysis-link" href="${event.url}" target="_blank" rel="noopener noreferrer">${t("openOriginal")}</a>
    </div>
  `;
}

function renderClusterDetail(events: EventItem[]): void {
  analysisFloatEl.classList.add("open");
  const sorted = [...events].sort((a, b) => (b.severity || 0) - (a.severity || 0));
  analysisDetailEl.innerHTML = `
    <div class="cluster-detail">
      <div class="cluster-summary">
        <strong>${events.length} 条情报</strong>
        <span>${[...new Set(events.map((event) => event.source))].length} 个来源</span>
        <span>${[...new Set(events.map((event) => categoryText(event.category)))].join("、")}</span>
      </div>
      <div class="cluster-event-list">
        ${sorted
          .map(
            (event) => `
          <button class="cluster-event-row" data-event-id="${event.id}">
            <span class="pill" style="background:${riskColor(event.risk_level)}">${riskText(event.risk_level)}</span>
            <b>${displayTitle(event)}</b>
            ${displayTitle(event) !== event.title ? `<small>${event.title}</small>` : ""}
            <em>${event.source} · ${categoryText(event.category)} · 严重度 ${event.severity || 1}</em>
          </button>
        `,
          )
          .join("")}
      </div>
    </div>
  `;
}

async function analyzeMapEvent(event: EventItem): Promise<void> {
  hideEventPopup();
  renderAnalysisDetail(event, event.status !== "analyzed");
  if (event.status === "analyzed") return;

  try {
    const result = await postJson<SingleAnalyzeResponse>(`/events/${event.id}/analyze`);
    if (!result.ok || !result.item) {
      showStatus(result.message || t("actionFailed"), "error");
      return;
    }
    renderAnalysisDetail(result.item);
    showStatus(t("analysisDone"), "success");
    await loadDashboard();
  } catch (error) {
    showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
  }
}

function showEventPopup(event: EventItem): void {
  hideEventPopup();
  const summary = event.summary || event.ai_summary || event.raw_summary || "";
  const published = event.published_at ? new Date(event.published_at).toLocaleString() : "未知时间";
  hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, maxWidth: "320px" })
    .setLngLat([event.lon as number, event.lat as number])
    .setHTML(`
      <div class="intel-popup">
        <div class="intel-popup-meta">
          <span style="background:${riskColor(event.risk_level)}">${riskText(event.risk_level)}</span>
          ${event.source} · ${published}
        </div>
        <strong>${displayTitle(event)}</strong>
        ${displayTitle(event) !== event.title ? `<small>${event.title}</small>` : ""}
        <p>${summary.slice(0, 220) || t("noSummary")}</p>
        <small>${locationText(event.country, event.city)} · ${categoryText(event.category)}</small>
        ${typeof event.event_count === "number" ? `<small>${event.event_count} 条报道 · ${event.source_count || 1} 个来源 · RSS ${event.rss_count || 0} · GDELT ${event.gdelt_count || 0} · 风险 ${event.risk_score || 0}</small>` : ""}
        ${event.location_reason ? `<small>${event.location_reason} · ${Math.round((event.location_confidence || 0) * 100)}%</small>` : ""}
      </div>
    `)
    .addTo(map);
}

function hideEventPopup(): void {
  if (!hoverPopup) return;
  hoverPopup.remove();
  hoverPopup = null;
}

function clusterEvents(events: EventItem[]): Array<{ kind: "single"; event: EventItem } | { kind: "cluster"; lat: number; lon: number; count: number; sample: EventItem; events: EventItem[] }> {
  const buckets = new Map<string, EventItem[]>();
  for (const event of events) {
    const lat = event.lat as number;
    const lon = event.lon as number;
    const key = `${Math.round(lat * 2) / 2}_${Math.round(lon * 2) / 2}`;
    const list = buckets.get(key) || [];
    list.push(event);
    buckets.set(key, list);
  }
  const result: Array<{ kind: "single"; event: EventItem } | { kind: "cluster"; lat: number; lon: number; count: number; sample: EventItem; events: EventItem[] }> = [];
  buckets.forEach((list) => {
    if (list.length === 1) {
      result.push({ kind: "single", event: list[0] });
      return;
    }
    const lat = list.reduce((s, e) => s + (e.lat as number), 0) / list.length;
    const lon = list.reduce((s, e) => s + (e.lon as number), 0) / list.length;
    result.push({ kind: "cluster", lat, lon, count: list.length, sample: list[0], events: list });
  });
  return result;
}

function renderTrendBars(points: CountryInsight["daily_trend"]): string {
  if (!points.length) return `<div class="country-empty">${t("noTrend")}</div>`;
  const max = Math.max(...points.map((p) => p.count), 1);
  return `<div class="trend-bars">${points
    .slice(-10)
    .map((p) => {
      const h = Math.max(8, Math.round((p.count / max) * 72));
      const label = p.date.slice(5);
      return `<div class="bar-wrap"><div class="bar" style="height:${h}px"></div><small>${label}</small></div>`;
    })
    .join("")}</div>`;
}

function renderCountryDetail(insight: CountryInsight): void {
  if (!insight.total_events) {
    const countryName = insight.country || t("countryFocus");
    countryDetailEl.innerHTML = `<div class="country-empty">${t("noDataPrefix")} ${countryName} ${t("currentRange")}</div>`;
    return;
  }

  const categories = insight.categories.slice(0, 6);
  const latest = insight.latest_events.slice(0, 5);
  const riskLine = insight.risk_distribution.map((r) => `${riskText(r.risk_level)}:${r.count}`).join(" · ");

  countryDetailEl.innerHTML = `
    <div class="country-kpis">
      <div><span>${t("total")}</span><strong>${insight.total_events}</strong></div>
      <div><span>${t("highRisk")}</span><strong>${insight.high_risk_events}</strong></div>
      <div><span>${t("categories")}</span><strong>${categories.length}</strong></div>
    </div>
    <div class="country-risk-line">${riskLine || "低:0 · 中:0 · 高:0 · 严重:0"}</div>
    <div class="country-trend">
      <h4>${t("dailyTrend")}</h4>
      ${renderTrendBars(insight.daily_trend)}
    </div>
    <div class="country-tags">${categories.map((cat) => `<span>${categoryText(cat.category)} · ${cat.count}</span>`).join("")}</div>
    <div class="country-list">
      ${latest
        .map(
          (item) => `<a href="${item.url}" target="_blank" rel="noopener noreferrer">
          <b>${displayTitle(item)}</b>
          ${displayTitle(item) !== item.title ? `<em>${item.title}</em>` : ""}
          <small>${item.source} · ${riskText(item.risk_level)}</small>
        </a>`,
        )
        .join("")}
    </div>
  `;
}

async function loadCountryDetail(country: string): Promise<void> {
  const range = timeRangeEl.value;
  const data = await fetchJson<CountryInsight>(`/country-insight?country=${encodeURIComponent(country)}&time_range=${range}`);
  renderCountryDetail(data);
}

function setActiveCountry(country: string): void {
  activeCountry = country;
  countryFilterEl.value = country;
  void Promise.all([loadCountryDetail(country), loadDashboard()]);
}

async function runAction(path: "/collect" | "/geotag"): Promise<void> {
  activeAction = path;
  const actionButton = path === "/collect" ? collectBtn : analyzeBtn;
  const originalText = actionButton.textContent || "";
  const workingText = path === "/collect" ? t("collecting") : t("analyzing");
  const doneText = path === "/collect" ? t("collectionDone") : t("analysisDone");

  setActionButtonsBusy(true);
  actionButton.textContent = workingText;
  showStatus(workingText, "working");
  activeActionController = new AbortController();

  try {
    const result = await postJson<{ ok: boolean; message: string; count?: number }>(path, activeActionController.signal);
    await loadFilters();
    await loadDashboard();
    const countText = typeof result.count === "number" ? ` · ${result.count}` : "";
    showStatus(result.ok ? `${doneText}${countText}` : result.message, result.ok ? "success" : "error");
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      showStatus(t("cancelRequested"), "success");
    } else {
      showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
    }
  } finally {
    activeAction = null;
    activeActionController = null;
    setActionButtonsBusy(false);
    actionButton.textContent = originalText;
  }
}

async function cancelActiveAction(): Promise<void> {
  showStatus(t("cancelling"), "working");
  activeActionController?.abort();
  try {
    await postJson<{ ok: boolean; message: string }>("/cancel");
    showStatus(t("cancelRequested"), "success");
  } catch (error) {
    showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
  }
}

function riskLabel(value: string): string {
  if (value === "low") return t("low");
  if (value === "medium") return t("medium");
  if (value === "high") return t("high");
  if (value === "critical") return t("critical");
  return value;
}

function statusLabel(value: string): string {
  if (value === "raw") return currentLanguage === "zh" ? "未分析" : "Raw";
  if (value === "analyzed") return currentLanguage === "zh" ? "已分析" : "Analyzed";
  if (value === "failed") return currentLanguage === "zh" ? "失败" : "Failed";
  return value;
}

function optionLabel(selectEl: HTMLSelectElement, value: string): string {
  if (selectEl === riskFilterEl) return riskLabel(value);
  if (selectEl === statusFilterEl) return statusLabel(value);
  if (selectEl === categoryFilterEl) return categoryText(value);
  return value;
}

function fillSelect(selectEl: HTMLSelectElement, values: string[], emptyLabel: string): void {
  const selected = selectEl.value;
  selectEl.innerHTML = `<option value="">${emptyLabel}</option>${values.map((v) => `<option value="${v}">${optionLabel(selectEl, v)}</option>`).join("")}`;
  if (selected && values.includes(selected)) selectEl.value = selected;
}

function renderMapCount(total: number): void {
  mapCountEl.textContent = currentLanguage === "zh"
    ? `${total} ${t("mappedSignals")}`
    : `${total} ${total === 1 ? t("mappedSignal") : t("mappedSignals")}`;
}

function loadKeywords(): string[] {
  const saved = localStorage.getItem("worldpulse-trade-keywords");
  if (!saved) return DEFAULT_KEYWORDS;
  return saved
    .split(/\n|,/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

function saveKeywords(): void {
  const keywords = keywordInputEl.value
    .split(/\n|,/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
  localStorage.setItem("worldpulse-trade-keywords", keywords.join("\n"));
  renderKeywordHits(latestRenderedEvents);
  showStatus("关键词关注已保存", "success");
}

function renderKeywordHits(events: EventItem[]): void {
  const keywords = loadKeywords();
  keywordInputEl.value = keywords.join("\n");
  const matched = events.filter((event) => {
    const text = `${event.title || ""} ${event.raw_summary || ""} ${event.ai_summary || ""} ${event.summary || ""}`.toLowerCase();
    return keywords.some((keyword) => text.includes(keyword.toLowerCase()));
  });
  const hitKeywords = keywords.filter((keyword) =>
    matched.some((event) => `${event.title || ""} ${event.raw_summary || ""} ${event.ai_summary || ""} ${event.summary || ""}`.toLowerCase().includes(keyword.toLowerCase())),
  );
  keywordHitBoxEl.innerHTML = `你关注的关键词今日命中 <strong>${matched.length}</strong> 条事件${hitKeywords.length ? `<br/><span>${hitKeywords.slice(0, 8).join("、")}</span>` : ""}`;
}

function updateStaticLanguage(): void {
  document.documentElement.lang = currentLanguage === "zh" ? "zh-CN" : "en";
  languageSelectEl.value = currentLanguage;
  document.querySelectorAll<HTMLElement>("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n as I18nKey | undefined;
    if (key) el.textContent = t(key);
  });

  sortByEl.options[0].textContent = t("sortTime");
  sortByEl.options[1].textContent = t("sortRisk");
  sortByEl.options[2].textContent = t("sortSeverity");
  sortOrderEl.options[0].textContent = t("desc");
  sortOrderEl.options[1].textContent = t("asc");
  renderMapCount(latestMapTotal);
  if (activeAction) {
    showStatus(activeAction === "/collect" ? t("collecting") : t("analyzing"), "working");
  }
}

async function loadFilters(): Promise<void> {
  const range = timeRangeEl.value;
  const filters = await fetchJson<FiltersResponse>(`/filters?time_range=${range}`);
  fillSelect(countryFilterEl, filters.countries, t("allCountries"));
  fillSelect(categoryFilterEl, filters.categories, t("allCategories"));
  fillSelect(riskFilterEl, filters.risk_levels, t("allRisks"));
  fillSelect(statusFilterEl, filters.statuses, t("allStatus"));
}

function buildSignalQuery(): string {
  const params = new URLSearchParams();
  params.set("time_range", timeRangeEl.value);
  params.set("sort_by", sortByEl.value);
  params.set("order", sortOrderEl.value);
  if (countryFilterEl.value) params.set("country", countryFilterEl.value);
  if (categoryFilterEl.value) params.set("category", categoryFilterEl.value);
  if (riskFilterEl.value) params.set("risk_level", riskFilterEl.value);
  if (statusFilterEl.value) params.set("status", statusFilterEl.value);
  return params.toString();
}

async function loadDashboard(): Promise<void> {
  try {
    const range = timeRangeEl.value;
    const [metrics, brief, mapEvents] = await Promise.all([
      fetchJson<Metrics>(`/metrics?time_range=${range}`),
      fetchJson<BriefResponse>(`/brief?time_range=${range}`),
      fetchJson<MapEventsResponse>(`/map-events?${buildSignalQuery()}`),
    ]);
    renderMetrics(metrics);
    renderBriefTable(brief.clusters || [], brief.brief);
    briefFloatEl.classList.add("open");
    renderConvergences(brief.convergences);
    renderMap(mapEvents.items);
    renderKeywordHits(mapEvents.items);
    latestMapTotal = mapEvents.total;
    renderMapCount(mapEvents.total);
    if (activeCountry) {
      await loadCountryDetail(activeCountry);
    } else {
      countryDetailEl.innerHTML = t("countryEmpty");
    }
  } catch (error) {
    briefEl.textContent = `${t("apiUnreachable")}。${(error as Error).message}`;
    showStatus(t("apiUnreachable"), "error");
  }
}

languageSelectEl.addEventListener("change", () => {
  currentLanguage = languageSelectEl.value === "zh" ? "zh" : "en";
  localStorage.setItem("worldpulse-language", currentLanguage);
  updateStaticLanguage();
  void loadFilters().then(loadDashboard);
});

metricsEl.addEventListener("click", (ev) => {
  const card = (ev.target as HTMLElement).closest(".metric-card") as HTMLElement | null;
  if (!card) return;
  metricsEl.querySelectorAll(".metric-card").forEach((el) => el.classList.remove("selected"));
  card.classList.add("selected");
  showStatus(`${t("metricSelected")}：${card.dataset.metric || ""}`, "success");
  void applyMetricAction(card.dataset.action || "");
});

closeAnalysisBtn.addEventListener("click", () => {
  analysisFloatEl.classList.remove("open");
});

closeBriefBtn.addEventListener("click", () => {
  briefFloatEl.classList.remove("open");
});

analysisDetailEl.addEventListener("click", (ev) => {
  const row = (ev.target as HTMLElement).closest(".cluster-event-row") as HTMLButtonElement | null;
  if (!row) return;
  const event = latestRenderedEvents.find((item) => item.id === row.dataset.eventId);
  if (!event) return;
  void analyzeMapEvent(event);
});

briefEl.addEventListener("click", (ev) => {
  const sortBtn = (ev.target as HTMLElement).closest("button[data-sort]") as HTMLButtonElement | null;
  if (sortBtn) {
    briefSortKey = sortBtn.dataset.sort as typeof briefSortKey;
    void loadDashboard();
    return;
  }
  const row = (ev.target as HTMLElement).closest("tr[data-event-id]") as HTMLTableRowElement | null;
  if (!row) return;
  const item = latestRenderedEvents.find((event) => event.id === row.dataset.eventId);
  if (!item) return;
  if (item.country) setActiveCountry(item.country);
  void analyzeMapEvent(item);
});

collectBtn.addEventListener("click", () => void runAction("/collect"));
analyzeBtn.addEventListener("click", () => void runAction("/geotag"));
cancelBtn.addEventListener("click", () => void cancelActiveAction());
refreshBtn.addEventListener("click", () => void loadDashboard());
saveKeywordsBtn.addEventListener("click", saveKeywords);

timeRangeEl.addEventListener("change", () => {
  void loadFilters().then(loadDashboard);
});

[countryFilterEl, categoryFilterEl, riskFilterEl, statusFilterEl, sortByEl, sortOrderEl].forEach((el) => {
  el.addEventListener("change", () => {
    activeCountry = countryFilterEl.value || null;
    if (!activeCountry) countryDetailEl.innerHTML = t("countryEmpty");
    void loadDashboard();
  });
});

clearCountryBtn.addEventListener("click", () => {
  activeCountry = null;
  countryFilterEl.value = "";
  countryDetailEl.innerHTML = t("countryEmpty");
  void loadDashboard();
});

[layerLowEl, layerMediumEl, layerHighEl, layerCriticalEl, clusterModeEl].forEach((el) => {
  el.addEventListener("change", () => {
    renderMap(latestRenderedEvents);
  });
});

keywordInputEl.value = loadKeywords().join("\n");
updateStaticLanguage();
void loadFilters().then(loadDashboard);
