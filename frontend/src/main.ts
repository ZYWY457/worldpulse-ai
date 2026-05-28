import "./style.css";

type EventItem = {
  id: string;
  title: string;
  title_zh?: string | null;
  url: string;
  source: string;
  published_at: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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
  market_impact?: string | null;
  opportunity_signal?: string | null;
  suggested_action?: string | null;
  content_angle?: string | null;
  industry_tags?: string | string[] | null;
  industry?: string | null;
  social_angle?: string | null;
  relevance_score?: number | null;
  relevance_reason?: string | null;
  matched_profile_terms?: string[] | null;
  affected_user_needs?: string[] | null;
  status: "raw" | "analyzed" | "failed" | null;
  risk_score?: number | null;
  event_count?: number | null;
  source_count?: number | null;
  gdelt_count?: number | null;
  rss_count?: number | null;
  summary?: string | null;
  summary_zh?: string | null;
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

type UserProfile = {
  profile_name: string;
  summary: string;
  industries: string[];
  preferred_categories: string[];
  keywords: string[];
  countries: string[];
  platforms: string[];
  products: string[];
  risk_focus: string[];
  relevance_rules: string[];
  confidence: number;
};

type ProfileAnalyzeResponse = {
  ok: boolean;
  message: string;
  profile: UserProfile;
};

type LlmChoice = "auto" | "openai" | "deepseek" | "ollama";
type LlmTone = "idle" | "ok" | "warn" | "error";

type LlmStatusResponse = {
  ok: boolean;
  requested: LlmChoice | "auto";
  provider: "openai" | "deepseek" | "ollama";
  configured: boolean;
  available: boolean;
  latency_ms: number | null;
  message: string;
  error?: string | null;
};
type SourceHealthResponse = {
  summary: { total: number; ok: number; degraded: number };
  items: Array<{
    source_name: string;
    source_type: string;
    status: string;
    latency_ms?: number | null;
    updated_at: string;
  }>;
};
type CollectionStatusResponse = {
  enabled: boolean;
  running: boolean;
  interval_minutes: number;
  last_started_at: string | null;
  last_finished_at: string | null;
  next_run_at: string | null;
  last_count: number | null;
  last_message: string | null;
  last_error: string | null;
  run_count: number;
};
type LlmConfigResponse = {
  ok: boolean;
  message: string;
  config: {
    openai_configured: boolean;
    deepseek_configured: boolean;
    deepseek_base_url: string;
    deepseek_model: string;
    ollama_base_url: string;
    ollama_model: string;
  };
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
type IndustryMode = "overview" | "trade" | "finance" | "tech" | "supply_chain" | "geopolitics" | "content";
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
  | "metricSelected"
  | "profile"
  | "profileTitle"
  | "profilePlaceholder"
  | "profileSave"
  | "profileClear"
  | "profileEmpty"
  | "profileAnalyzing"
  | "profileApplied"
  | "llm"
  | "llmCheck"
  | "llmChecking"
  | "llmUnavailable"
  | "sourceHealth"
  | "llmConfig"
  | "llmSave";

const i18n: Record<Language, Record<I18nKey, string>> = {
  zh: {
    subtitle: "多行业信息面雷达",
    collect: "更新数据",
    analyze: "地图定位",
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
    mapTitle: "全球事件地图",
    low: "低",
    medium: "中",
    high: "高",
    critical: "严重",
    cluster: "聚合",
    countryFocus: "国家聚焦",
    clear: "清除",
    countryEmpty: "选择地图点查看国家/地区信息面。",
    briefTitle: "今日行业简报",
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
    events: "条信息面事件",
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
    analyzingOne: "正在生成这条事件的行业影响分析...",
    collectionDone: "采集完成",
    analysisDone: "地图定位完成",
    actionFailed: "操作失败",
    cancelling: "正在请求终止...",
    cancelRequested: "已请求终止",
    analysisPanel: "行业影响分析",
    clickMapPoint: "点击地图点查看行业影响分析。",
    openOriginal: "打开原文",
    metricHint: "点击查看相关信号",
    metricSelected: "已聚焦指标",
    profile: "用户画像",
    profileTitle: "我的关注画像",
    profilePlaceholder: "例如：我是做东南亚 TikTok Shop 的家居卖家，关注平台政策、物流延误、广告投放和清关风险。",
    profileSave: "生成画像",
    profileClear: "清除",
    profileEmpty: "填写职业、业务或关注需求后，系统会优先显示更相关的事件。",
    profileAnalyzing: "正在生成用户画像...",
    profileApplied: "画像已应用，相关事件会优先展示",
    llm: "模型",
    llmCheck: "检测连通性",
    llmChecking: "模型状态检测中...",
    llmUnavailable: "模型不可用，请检查配置后重试",
    sourceHealth: "源健康",
    llmConfig: "模型设置",
    llmSave: "保存配置",
  },
  en: {
    subtitle: "Multi-Industry Signal Radar",
    collect: "Sync Data",
    analyze: "Map Locate",
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
    mapTitle: "Global Event Map",
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
    cluster: "Cluster",
    countryFocus: "Country Focus",
    clear: "Clear",
    countryEmpty: "Select a map point to inspect country-level signals.",
    briefTitle: "Daily Industry Brief",
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
    analysisPanel: "Industry Impact",
    clickMapPoint: "Click a map point to inspect industry impact.",
    openOriginal: "Open Original",
    metricHint: "Click to inspect related signals",
    metricSelected: "Metric focused",
    profile: "User Profile",
    profileTitle: "My Signal Profile",
    profilePlaceholder: "Example: I sell home goods on TikTok Shop in Southeast Asia and care about platform policy, logistics, ads, and customs risks.",
    profileSave: "Build Profile",
    profileClear: "Clear",
    profileEmpty: "Describe your role, business, or needs to prioritize relevant events.",
    profileAnalyzing: "Building user profile...",
    profileApplied: "Profile applied. Relevant events are prioritized.",
    llm: "LLM",
    llmCheck: "Check",
    llmChecking: "Checking model connectivity...",
    llmUnavailable: "Model unavailable. Check configuration and retry.",
    sourceHealth: "Sources",
    llmConfig: "LLM Settings",
    llmSave: "Save",
  },
};

let currentLanguage: Language = localStorage.getItem("worldpulse-language") === "en" ? "en" : "zh";

function t(key: I18nKey): string {
  return i18n[currentLanguage][key];
}

appEl.innerHTML = `
  <main class="dashboard">
    <header class="topbar">
      <div class="hero-copy">
        <h1>WorldPulse Radar</h1>
        <p class="eyebrow" data-i18n="subtitle">${t("subtitle")}</p>
        <p class="product-copy">把全球新闻、政策、市场、科技、供应链和地缘事件整理成可筛选、可定位、可追踪的业务风险雷达。</p>
      </div>
      <div class="actions command-center" aria-label="控制台">
        <div class="action-cluster">
          <label>
            <span>语言</span>
            <select id="languageSelect" aria-label="Language">
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </label>
          <label>
            <span>时间范围</span>
            <select id="timeRange">
              <option value="1h">1小时</option>
              <option value="24h" selected>24小时</option>
              <option value="7d">7天</option>
              <option value="30d">30天</option>
            </select>
          </label>
          <label>
            <span>分析模型</span>
            <select id="llmSelect" aria-label="LLM">
              <option value="auto">自动选择</option>
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="ollama">本地 Ollama</option>
            </select>
          </label>
        </div>
        <div class="action-cluster model-cluster">
          <button id="llmConfigBtn" data-i18n="llmConfig">${t("llmConfig")}</button>
          <button id="llmCheckBtn" data-i18n="llmCheck">${t("llmCheck")}</button>
          <span id="llmStatus" class="llm-status idle">${t("llmChecking")}</span>
        </div>
        <div class="action-cluster ops-cluster">
          <button id="sourceHealthBtn" data-i18n="sourceHealth">${t("sourceHealth")}</button>
          <button id="collectBtn" data-i18n="collect" title="拉取 RSS/GDELT/轻爬虫新事件">${t("collect")}</button>
          <button id="analyzeBtn" data-i18n="analyze" title="对未定位事件执行地图定位与风险初标记">${t("analyze")}</button>
          <button id="profileBtn" data-i18n="profile" title="填写职业与需求，生成个性化优先级">${t("profile")}</button>
          <button id="cancelBtn" class="danger-btn" data-i18n="stop" disabled>${t("stop")}</button>
          <button id="refreshBtn" data-i18n="refresh">${t("refresh")}</button>
          <span id="collectionStatus" class="collection-status">自动采集准备中</span>
        </div>
      </div>
    </header>
    <section class="industry-tabs" aria-label="行业模式">
      <span>行业模式：</span>
      <button data-industry="overview" class="active">总览</button>
      <button data-industry="trade">出海贸易</button>
      <button data-industry="finance">金融市场</button>
      <button data-industry="tech">科技AI</button>
      <button data-industry="supply_chain">供应链工业</button>
      <button data-industry="geopolitics">地缘安全</button>
      <button data-industry="content">内容创作</button>
    </section>
    <div id="statusBar" class="status-bar" role="status" aria-live="polite"></div>
    <section class="llm-config-panel" id="llmConfigPanel" hidden>
      <div class="profile-head">
        <h2>${t("llmConfig")}</h2>
        <span class="panel-kicker">选择一个可用模型后，AI 会用于画像、摘要和行业影响分析。</span>
      </div>
      <div class="llm-grid">
        <div class="llm-card">
          <strong>OpenAI</strong>
          <small>云端通用模型。填写 Key 后可作为自动模式候选。</small>
          <label><span>API Key</span><input id="openaiKeyInput" type="password" placeholder="sk-..." /></label>
        </div>
        <div class="llm-card">
          <strong>DeepSeek</strong>
          <small>适合中文摘要和成本敏感场景。默认使用 deepseek-chat。</small>
          <label><span>API Key</span><input id="deepseekKeyInput" type="password" placeholder="sk-..." /></label>
          <label><span>Base URL</span><input id="deepseekBaseInput" type="text" value="https://api.deepseek.com" /></label>
          <label><span>模型名称</span><input id="deepseekModelInput" type="text" value="deepseek-chat" /></label>
        </div>
        <div class="llm-card">
          <strong>本地 Ollama</strong>
          <small>适合本机离线测试。需要先启动 Ollama 服务。</small>
          <label><span>Base URL</span><input id="ollamaBaseInput" type="text" value="http://localhost:11434/v1" /></label>
          <label><span>模型名称</span><input id="ollamaModelInput" type="text" value="qwen2.5:7b" /></label>
        </div>
      </div>
      <div class="profile-editor">
        <small>临时配置只保存在当前后端进程内存；重启服务后需要重新填写，或把 Key 写入 .env。</small>
        <button id="saveLlmConfigBtn" data-i18n="llmSave">${t("llmSave")}</button>
      </div>
    </section>
    <section class="profile-panel" id="profilePanel" hidden>
      <div class="profile-head">
        <h2 data-i18n="profileTitle">${t("profileTitle")}</h2>
        <button id="clearProfileBtn" class="tiny-btn" data-i18n="profileClear">${t("profileClear")}</button>
      </div>
      <div class="profile-editor">
        <textarea id="profileInput" rows="3" spellcheck="false" placeholder="${t("profilePlaceholder")}"></textarea>
        <button id="saveProfileBtn" data-i18n="profileSave">${t("profileSave")}</button>
      </div>
      <div id="profileSummary" class="profile-summary">${t("profileEmpty")}</div>
    </section>
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
      <div class="map-main-column">
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
        <aside class="floating-panel analysis-float" id="analysisFloat">
          <div class="floating-head">
            <h2 data-i18n="analysisPanel">${t("analysisPanel")}</h2>
            <button id="closeAnalysisBtn" class="tiny-btn">关闭</button>
          </div>
          <div id="analysisDetail" class="floating-body">${t("clickMapPoint")}</div>
        </aside>
      </div>
      <div class="insight-rail">
        <aside class="side-panel">
          <div class="side-tabs" aria-label="右侧信息面板">
            <button class="active" data-side-tab="brief">简报</button>
            <button data-side-tab="country">国家</button>
            <button data-side-tab="keywords">关键词</button>
          </div>
          <section class="side-pane active" data-side-panel="brief" id="briefFloat">
            <div class="pane-head">
              <h2 data-i18n="briefTitle">${t("briefTitle")}</h2>
              <button id="closeBriefBtn" class="tiny-btn">收起</button>
            </div>
            <div class="pane-body">
              <div id="briefText">${t("loading")}</div>
              <div id="convergenceList"></div>
            </div>
          </section>
          <section class="side-pane" data-side-panel="country">
            <div class="pane-head">
              <h2 data-i18n="countryFocus">${t("countryFocus")}</h2>
              <button id="clearCountryBtn" class="tiny-btn" data-i18n="clear">${t("clear")}</button>
            </div>
            <div id="countryDetail" class="pane-body">${t("countryEmpty")}</div>
          </section>
          <section class="side-pane" data-side-panel="keywords">
            <div class="pane-head">
              <h2>关键词关注</h2>
              <button id="saveKeywordsBtn" class="tiny-btn">保存</button>
            </div>
            <div class="pane-body keyword-pane-body">
              <textarea id="keywordInput" rows="5" spellcheck="false"></textarea>
              <div id="keywordHitBox" class="keyword-hit">你关注的关键词今日命中 0 条事件</div>
            </div>
          </section>
        </aside>
      </div>
    </section>
  </main>
`;

const metricsEl = document.getElementById("metrics") as HTMLDivElement;
const briefEl = document.getElementById("briefText") as HTMLDivElement;
const convergenceEl = document.getElementById("convergenceList") as HTMLDivElement;
const countryDetailEl = document.getElementById("countryDetail") as HTMLDivElement;
const analysisDetailEl = document.getElementById("analysisDetail") as HTMLDivElement;
const analysisFloatEl = document.getElementById("analysisFloat") as HTMLElement;
const closeAnalysisBtn = document.getElementById("closeAnalysisBtn") as HTMLButtonElement;
const closeBriefBtn = document.getElementById("closeBriefBtn") as HTMLButtonElement;
const mapCountEl = document.getElementById("mapCount") as HTMLSpanElement;
const statusBarEl = document.getElementById("statusBar") as HTMLDivElement;
const llmConfigPanelEl = document.getElementById("llmConfigPanel") as HTMLElement;
const llmConfigBtn = document.getElementById("llmConfigBtn") as HTMLButtonElement;
const profilePanelEl = document.getElementById("profilePanel") as HTMLElement;
const profileBtn = document.getElementById("profileBtn") as HTMLButtonElement;
const profileInputEl = document.getElementById("profileInput") as HTMLTextAreaElement;
const profileSummaryEl = document.getElementById("profileSummary") as HTMLDivElement;
const saveProfileBtn = document.getElementById("saveProfileBtn") as HTMLButtonElement;
const clearProfileBtn = document.getElementById("clearProfileBtn") as HTMLButtonElement;
const keywordInputEl = document.getElementById("keywordInput") as HTMLTextAreaElement;
const keywordHitBoxEl = document.getElementById("keywordHitBox") as HTMLDivElement;
const saveKeywordsBtn = document.getElementById("saveKeywordsBtn") as HTMLButtonElement;
const industryTabsEl = document.querySelector(".industry-tabs") as HTMLElement;
const sideTabEls = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-side-tab]"));
const sidePanelEls = Array.from(document.querySelectorAll<HTMLElement>("[data-side-panel]"));

const languageSelectEl = document.getElementById("languageSelect") as HTMLSelectElement;
const timeRangeEl = document.getElementById("timeRange") as HTMLSelectElement;
const llmSelectEl = document.getElementById("llmSelect") as HTMLSelectElement;
const llmCheckBtn = document.getElementById("llmCheckBtn") as HTMLButtonElement;
const llmStatusEl = document.getElementById("llmStatus") as HTMLSpanElement;
const collectionStatusEl = document.getElementById("collectionStatus") as HTMLSpanElement;
const saveLlmConfigBtn = document.getElementById("saveLlmConfigBtn") as HTMLButtonElement;
const openaiKeyInput = document.getElementById("openaiKeyInput") as HTMLInputElement;
const deepseekKeyInput = document.getElementById("deepseekKeyInput") as HTMLInputElement;
const deepseekBaseInput = document.getElementById("deepseekBaseInput") as HTMLInputElement;
const deepseekModelInput = document.getElementById("deepseekModelInput") as HTMLInputElement;
const ollamaBaseInput = document.getElementById("ollamaBaseInput") as HTMLInputElement;
const ollamaModelInput = document.getElementById("ollamaModelInput") as HTMLInputElement;
const sourceHealthBtn = document.getElementById("sourceHealthBtn") as HTMLButtonElement;
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
let maplibre: any = null;
let map: any = null;
let mapReady = false;
let mapMarkers: any[] = [];
let latestRenderedEvents: EventItem[] = [];
let latestBriefItems: EventItem[] = [];
let latestMapTotal = 0;
let hoverPopup: any | null = null;
let activeAction: "/collect" | "/geotag" | null = null;
let activeActionController: AbortController | null = null;
let collectionPollId: number | null = null;
let lastCollectionRunCount: number | null = null;
let lastCollectionFinishedAt: string | null = null;
let reloadingAfterAutoCollection = false;
let briefSortKey: "risk_score" | "last_seen" | "source_count" | "event_count" = "risk_score";
let currentIndustry: IndustryMode = (localStorage.getItem("worldpulse-industry") as IndustryMode | null) || "overview";
let activeProfile: UserProfile | null = loadUserProfile();
let currentLlm: LlmChoice = (localStorage.getItem("worldpulse-llm") as LlmChoice | null) || "auto";
let llmChecking = false;

const INDUSTRIES: Record<IndustryMode, { name: string; description: string; keywords: string[] }> = {
  overview: { name: "总览", description: "综合全球重要事件", keywords: ["突发", "政策", "市场", "科技", "供应链", "战争", "制裁", "油价", "汇率", "AI"] },
  trade: { name: "出海贸易", description: "跨境电商、外贸、物流和出海团队", keywords: ["Amazon", "TikTok Shop", "Temu", "Shopee", "关税", "清关", "DHL", "FedEx", "红海", "港口"] },
  finance: { name: "金融市场", description: "投资者、财经内容创作者和市场观察者", keywords: ["美联储", "CPI", "黄金", "油价", "美元", "比特币", "纳斯达克", "降息", "债券"] },
  tech: { name: "科技 AI", description: "AI 从业者、开发者、创业者和科技媒体", keywords: ["OpenAI", "NVIDIA", "AI芯片", "开源模型", "数据中心", "云服务", "监管", "融资"] },
  supply_chain: { name: "供应链工业", description: "制造业、工厂、贸易商、采购和工业企业", keywords: ["锂", "铜", "稀土", "石油", "天然气", "航运", "港口", "工厂", "矿山"] },
  geopolitics: { name: "地缘安全", description: "政策研究、风险顾问和企业风控", keywords: ["制裁", "战争", "军事", "外交", "抗议", "边境", "导弹", "停火"] },
  content: { name: "内容创作", description: "财经博主、新闻号和自媒体运营", keywords: ["爆火", "争议", "突发", "反转", "影响", "普通人", "价格上涨", "机会"] },
};

async function initMap(): Promise<void> {
  await import("maplibre-gl/dist/maplibre-gl.css");
  const mod = await import("maplibre-gl");
  maplibre = mod.default;
  map = new maplibre.Map({
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
  map.addControl(new maplibre.NavigationControl(), "top-right");
  mapReady = true;
}

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
    central_bank: "央行政策",
    commodity_price: "商品价格",
    stock_market: "股市风险",
    crypto_market: "加密市场",
    ai_model: "AI 模型",
    chips: "芯片限制",
    cloud_datacenter: "云服务/数据中心",
    tech_regulation: "科技监管",
    factory_disruption: "工厂停摆",
    raw_materials: "原材料",
    energy_supply: "能源供应",
    military_conflict: "战争冲突",
    diplomacy: "外交关系",
    protest_unrest: "抗议动荡",
    viral_topic: "热点选题",
    tariff_policy: "关税政策",
    trade_policy: "贸易政策",
    customs_clearance: "海关清关",
    logistics_delay: "物流延误",
    port_disruption: "港口/航运中断",
    platform_policy: "平台规则",
    sanctions_conflict: "制裁/冲突",
    currency_oil: "汇率/油价",
    supply_chain: "供应链",
    market_demand: "市场需求",
    compliance: "合规监管",
    cybersecurity: "网络安全",
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

function eventTimeValue(event: EventItem): string | null {
  return event.last_seen || event.published_at || null;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return currentLanguage === "zh" ? "未知时间" : "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return currentLanguage === "zh" ? "时间格式异常" : "Invalid time";
  return date.toLocaleString(currentLanguage === "zh" ? "zh-CN" : "en-US", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function relativeTime(value: string | null | undefined): string {
  if (!value) return currentLanguage === "zh" ? "未提供时间" : "No timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return currentLanguage === "zh" ? "时间无效" : "Invalid time";
  const diffMinutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (diffMinutes < 60) return currentLanguage === "zh" ? `${diffMinutes || 1} 分钟前` : `${diffMinutes || 1}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 48) return currentLanguage === "zh" ? `${diffHours} 小时前` : `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return currentLanguage === "zh" ? `${diffDays} 天前` : `${diffDays}d ago`;
}

function freshnessClass(value: string | null | undefined): string {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  const ageHours = (Date.now() - date.getTime()) / 3600000;
  if (ageHours <= 24) return "fresh";
  if (ageHours <= 72) return "aging";
  return "stale";
}

function sourceSummary(item: EventItem): string {
  const pieces = [`${item.source_count || 1} 个来源`];
  if (typeof item.rss_count === "number") pieces.push(`RSS ${item.rss_count}`);
  if (typeof item.gdelt_count === "number") pieces.push(`GDELT ${item.gdelt_count}`);
  return pieces.join(" · ");
}

function affectedGroupsText(value: EventItem["affected_groups"]): string {
  if (Array.isArray(value)) return value.join("、");
  if (!value) return "行业观察者、运营团队、风险管理人员";
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) return parsed.join("、");
  } catch {
    // Keep plain strings from older API responses.
  }
  return value;
}

function parseStringList(value: string | string[] | null | undefined): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) return parsed.map(String);
  } catch {
    // Keep compatibility with comma-separated values from older responses.
  }
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function businessImpactText(event: EventItem): string {
  return event.business_impact || "该事件可能影响相关行业的经营、成本、市场情绪或风险判断，请点击分析获取具体影响。";
}

function suggestedActionText(event: EventItem): string {
  return event.suggested_action || "建议先关注后续确认信息、受影响地区、相关资产/成本变化和行业公告。";
}

function displayTitle(event: EventItem): string {
  if (currentLanguage === "zh" && event.title_zh) return event.title_zh;
  if (event.ai_summary) return event.ai_summary;
  if (currentLanguage === "zh" && event.summary && /[\u4e00-\u9fa5]/.test(event.summary)) return event.summary;
  if (currentLanguage === "zh") return zhSignalTitle(event);
  return localizeHeadline(event.title);
}

function displayOriginalTitle(event: EventItem): string {
  if (currentLanguage === "zh" && event.title_zh) return event.title_zh;
  if (!event.title) return "";
  return currentLanguage === "zh" ? localizeHeadline(event.title) : event.title;
}

function displaySummary(event: EventItem): string {
  if (currentLanguage === "zh" && event.summary_zh) return event.summary_zh;
  const candidates = [event.ai_summary, event.summary, event.raw_summary].filter((item): item is string => Boolean(item && item.trim()));
  if (!candidates.length) return t("noSummary");
  if (currentLanguage !== "zh") return candidates[0];
  const zhText = candidates.find((text) => /[\u4e00-\u9fa5]/.test(text));
  if (zhText) return zhText;
  return localizeHeadline(candidates[0]);
}

function zhSignalTitle(event: EventItem): string {
  const title = event.title || "";
  const category = categoryText(event.category);
  const location = event.country || event.city ? locationText(event.country, event.city) : "全球";
  const source = event.source ? event.source.replace(/^GDELT\s*\/\s*/i, "") : "新闻源";
  const lowered = title.toLowerCase();
  const topicRules: Array<[RegExp, string]> = [
    [/tariff|customs|dut(y|ies)|de minimis|trade/i, "贸易/关税信号"],
    [/sanction|export control|ofac|embargo/i, "制裁/出口管制信号"],
    [/shipping|port|logistics|container|red sea|suez/i, "物流/航运信号"],
    [/central bank|interest rate|inflation|cpi|monetary/i, "宏观金融信号"],
    [/cyber|ransomware|data breach|hack|malware/i, "网络安全信号"],
    [/ai|artificial intelligence|chip|semiconductor|gpu|data center/i, "科技/AI 信号"],
    [/war|missile|drone|attack|ceasefire|military/i, "地缘冲突信号"],
    [/protest|strike|unrest|riot|election/i, "社会/政治风险信号"],
    [/oil|crude|gas|energy/i, "能源价格信号"],
    [/factory|plant|production|shutdown/i, "工厂/生产信号"],
  ];
  const topic = topicRules.find(([pattern]) => pattern.test(lowered))?.[1] || `${category}信号`;
  return `${location} · ${topic}（${source}）`;
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

async function postJsonBody<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

function setActionButtonsBusy(isBusy: boolean): void {
  collectBtn.disabled = isBusy;
  analyzeBtn.disabled = isBusy;
  refreshBtn.disabled = isBusy;
  profileBtn.disabled = isBusy;
  llmSelectEl.disabled = isBusy;
  llmConfigBtn.disabled = isBusy;
  llmCheckBtn.disabled = isBusy || llmChecking;
  sourceHealthBtn.disabled = isBusy;
  cancelBtn.disabled = !isBusy;
}

function showStatus(message: string, tone: "idle" | "working" | "success" | "error" = "idle"): void {
  statusBarEl.textContent = message;
  statusBarEl.className = `status-bar ${tone}`;
}

function showLlmStatus(message: string, tone: LlmTone = "idle"): void {
  llmStatusEl.textContent = message;
  llmStatusEl.className = `llm-status ${tone}`;
}

async function refreshLlmStatus(): Promise<LlmStatusResponse | null> {
  llmChecking = true;
  llmCheckBtn.disabled = true;
  showLlmStatus(t("llmChecking"), "idle");
  try {
    const status = await fetchJson<LlmStatusResponse>(`/llm/status?llm=${currentLlm}`);
    const providerLabel = status.provider.toUpperCase();
    const prefix = currentLanguage === "zh" ? `当前 ${providerLabel}` : providerLabel;
    if (!status.configured) {
      showLlmStatus(`${prefix} · Key 未配置`, "warn");
      return status;
    }
    if (!status.available) {
      showLlmStatus(`${prefix} · ${status.message}`, "error");
      return status;
    }
    const latency = typeof status.latency_ms === "number" ? `${status.latency_ms}ms` : "--";
    showLlmStatus(`${prefix} · 可用 · ${latency}`, "ok");
    return status;
  } catch (error) {
    showLlmStatus(t("llmUnavailable"), "error");
    console.error("LLM status check failed", error);
    return null;
  } finally {
    llmChecking = false;
    llmCheckBtn.disabled = false;
  }
}

async function ensureLlmReadyForAnalysis(): Promise<boolean> {
  const status = await refreshLlmStatus();
  if (!status) {
    showStatus(t("llmUnavailable"), "error");
    return false;
  }
  if (!status.configured) {
    showStatus(status.message || t("llmUnavailable"), "error");
    return false;
  }
  if (!status.available) {
    showStatus(status.message || t("llmUnavailable"), "error");
    return false;
  }
  return true;
}

async function showSourceHealthSummary(): Promise<void> {
  try {
    const data = await fetchJson<SourceHealthResponse>("/sources/health");
    const sorted = [...data.items].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
    const topBad = sorted.filter((it) => it.status !== "ok").slice(0, 3);
    const latest = sorted[0];
    const latestText = latest ? `最近检查：${latest.source_name} · ${formatDateTime(latest.updated_at)} · ${relativeTime(latest.updated_at)}` : "暂无检查时间";
    if (!topBad.length) {
      showStatus(`数据源健康：全部正常（${data.summary.ok}/${data.summary.total}）。${latestText}`, "success");
      return;
    }
    const labels = topBad.map((it) => `${it.source_name}:${it.status} · ${formatDateTime(it.updated_at)}`).join("；");
    showStatus(`数据源健康：异常 ${data.summary.degraded}/${data.summary.total}（${labels}）。${latestText}`, "error");
  } catch (error) {
    showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
  }
}

async function refreshCollectionStatus(): Promise<void> {
  try {
    const status = await fetchJson<CollectionStatusResponse>("/collect/status");
    collectionStatusEl.className = `collection-status ${status.running ? "running" : ""}`;
    const previousRunCount = lastCollectionRunCount;
    const previousFinishedAt = lastCollectionFinishedAt;
    lastCollectionRunCount = status.run_count;
    lastCollectionFinishedAt = status.last_finished_at;
    if (!status.enabled) {
      collectionStatusEl.textContent = "自动采集已关闭";
      return;
    }
    if (status.running) {
      collectionStatusEl.textContent = "后台采集中";
      return;
    }
    const last = status.last_finished_at ? `${relativeTime(status.last_finished_at)}更新` : "尚未自动更新";
    const next = status.next_run_at ? `下次 ${formatDateTime(status.next_run_at)}` : `每 ${status.interval_minutes} 分钟`;
    collectionStatusEl.textContent = `${last} · ${next}`;
    const finishedNewRun = previousRunCount !== null && status.run_count > previousRunCount;
    const finishedAtChanged = previousFinishedAt !== null && status.last_finished_at !== previousFinishedAt;
    if (!activeAction && !reloadingAfterAutoCollection && (finishedNewRun || finishedAtChanged)) {
      reloadingAfterAutoCollection = true;
      try {
        await loadFilters();
        await loadDashboard();
        showStatus("自动采集完成，新闻库已更新", status.last_error ? "error" : "success");
      } finally {
        reloadingAfterAutoCollection = false;
      }
    }
  } catch {
    collectionStatusEl.className = "collection-status error";
    collectionStatusEl.textContent = "采集状态不可用";
  }
}

function startJobPolling(path: "/collect" | "/geotag"): void {
  if (collectionPollId !== null) window.clearInterval(collectionPollId);
  const statusPath = path === "/collect" ? "/collect/status" : "/process/status";
  const workingLabel = path === "/collect" ? "后台采集中" : "后台定位处理中";
  collectionPollId = window.setInterval(() => {
    void (async () => {
      const status = await fetchJson<CollectionStatusResponse>(statusPath);
      if (path === "/collect") collectionStatusEl.className = `collection-status ${status.running ? "running" : ""}`;
      if (status.running) {
        if (path === "/collect") collectionStatusEl.textContent = workingLabel;
        showStatus(status.last_message || workingLabel, "working");
        return;
      }
      if (collectionPollId !== null) {
        window.clearInterval(collectionPollId);
        collectionPollId = null;
      }
      if (path === "/collect") await refreshCollectionStatus();
      await loadFilters();
      await loadDashboard();
      showStatus(status.last_message || (path === "/collect" ? "后台采集完成" : "后台定位完成"), status.last_error ? "error" : "success");
    })().catch((error) => {
      showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
    });
  }, 2000);
}

async function saveLlmConfig(): Promise<void> {
  saveLlmConfigBtn.disabled = true;
  try {
    const result = await postJsonBody<LlmConfigResponse>("/llm/config", {
      openai_api_key: openaiKeyInput.value.trim() || null,
      deepseek_api_key: deepseekKeyInput.value.trim() || null,
      deepseek_base_url: deepseekBaseInput.value.trim() || null,
      deepseek_model: deepseekModelInput.value.trim() || null,
      ollama_base_url: ollamaBaseInput.value.trim() || null,
      ollama_model: ollamaModelInput.value.trim() || null,
    });
    if (!result.ok) {
      showStatus(result.message || t("actionFailed"), "error");
      return;
    }
    showStatus(result.message, "success");
    openaiKeyInput.value = "";
    deepseekKeyInput.value = "";
    await refreshLlmStatus();
  } catch (error) {
    showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
  } finally {
    saveLlmConfigBtn.disabled = false;
  }
}

function loadUserProfile(): UserProfile | null {
  const raw = localStorage.getItem("worldpulse-user-profile");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as UserProfile;
    return parsed && Array.isArray(parsed.keywords) ? parsed : null;
  } catch {
    return null;
  }
}

function saveUserProfile(profile: UserProfile): void {
  activeProfile = profile;
  localStorage.setItem("worldpulse-user-profile", JSON.stringify(profile));
  renderProfileSummary();
}

function clearUserProfile(): void {
  activeProfile = null;
  localStorage.removeItem("worldpulse-user-profile");
  profileInputEl.value = "";
  renderProfileSummary();
}

function renderProfileSummary(): void {
  if (!activeProfile) {
    profileSummaryEl.textContent = t("profileEmpty");
    profileBtn.classList.remove("active-profile");
    return;
  }
  profileBtn.classList.add("active-profile");
  const focus = [...(activeProfile.risk_focus || []), ...(activeProfile.keywords || [])].slice(0, 8).join("、");
  profileSummaryEl.innerHTML = `
    <strong>${activeProfile.profile_name || t("profileTitle")}</strong>
    <span>${activeProfile.summary || ""}</span>
    <small>${focus || "暂无关注点"} · 画像置信度 ${Math.round((activeProfile.confidence || 0) * 100)}%</small>
  `;
}

function profileTerms(profile: UserProfile): string[] {
  return [
    ...(profile.keywords || []),
    ...(profile.platforms || []),
    ...(profile.products || []),
    ...(profile.risk_focus || []),
  ]
    .map((item) => item.trim())
    .filter((item) => item.length >= 2);
}

function profileRelevanceScore(event: EventItem): number {
  if (typeof event.relevance_score === "number") return event.relevance_score;
  if (!activeProfile) return 0;
  const searchable = [
    event.title,
    event.summary,
    event.ai_summary,
    event.raw_summary,
    event.business_impact,
    event.market_impact,
    event.opportunity_signal,
    event.suggested_action,
    event.content_angle,
    event.source,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  let score = 0;
  for (const keyword of profileTerms(activeProfile)) {
    const normalized = keyword.toLowerCase();
    if (searchable.includes(normalized)) score += normalized.length >= 6 ? 12 : 8;
  }
  if (event.category && activeProfile.preferred_categories?.includes(event.category)) score += 22;
  if (event.country && activeProfile.countries?.some((country) => country.toLowerCase() === event.country?.toLowerCase())) score += 18;
  if (event.industry && activeProfile.industries?.includes(event.industry)) score += 10;
  const tags = parseStringList(event.industry_tags);
  if (tags.some((tag) => activeProfile?.industries?.includes(tag))) score += 10;
  if (event.risk_level === "critical") score += 8;
  if (event.risk_level === "high") score += 5;
  return score;
}

function prioritizeEvents<T extends EventItem>(events: T[]): T[] {
  if (!activeProfile) return events;
  return [...events].sort((a, b) => {
    const scoreDelta = profileRelevanceScore(b) - profileRelevanceScore(a);
    if (scoreDelta !== 0) return scoreDelta;
    return Number(b.risk_score || b.severity || 0) - Number(a.risk_score || a.severity || 0);
  });
}

function renderRelevanceBadge(event: EventItem): string {
  const score = profileRelevanceScore(event);
  if (!activeProfile || score <= 0) return "";
  const label = score >= 35 ? "高度相关" : "相关";
  return `<small class="relevance-badge">${label} · ${score}</small>`;
}

function relevanceReasonText(event: EventItem): string {
  if (event.relevance_reason) return event.relevance_reason;
  const terms = event.matched_profile_terms || [];
  if (terms.length) return `命中画像关键词：${terms.slice(0, 5).join("、")}`;
  const score = profileRelevanceScore(event);
  return score > 0 ? "与当前画像存在相关信号。" : "";
}

function profileQueryParam(): string {
  if (!activeProfile) return "";
  return JSON.stringify(activeProfile);
}

async function analyzeAndSaveProfile(): Promise<void> {
  const text = profileInputEl.value.trim();
  if (!text) {
    showStatus(t("profileEmpty"), "error");
    return;
  }
  const ready = await ensureLlmReadyForAnalysis();
  if (!ready) return;
  saveProfileBtn.disabled = true;
  showStatus(t("profileAnalyzing"), "working");
  try {
    const result = await postJsonBody<ProfileAnalyzeResponse>("/profile/analyze", { text, llm: currentLlm });
    if (!result.ok || !result.profile) {
      showStatus(result.message || t("actionFailed"), "error");
      return;
    }
    saveUserProfile(result.profile);
    showStatus(result.message || t("profileApplied"), "success");
    await loadDashboard();
  } catch (error) {
    showStatus(`${t("actionFailed")}: ${(error as Error).message}`, "error");
  } finally {
    saveProfileBtn.disabled = false;
  }
}

function renderMetrics(metrics: Metrics): void {
  const focusCards: Record<IndustryMode, Array<{ action: string; label: string; value: string; hint: string; level: string }>> = {
    overview: [
      { action: "all", label: "全球事件", value: metrics.total_events.toString(), hint: "综合全球重要信号", level: "calm" },
      { action: "high-risk", label: "高风险", value: metrics.high_risk_events.toString(), hint: "聚焦高风险和严重事件", level: metrics.high_risk_events > 0 ? "hot" : "calm" },
    ],
    trade: [
      { action: "logistics", label: "物流/港口", value: "物流", hint: "物流延误、港口、航运中断", level: "watch" },
      { action: "platform", label: "平台规则", value: "平台", hint: "Amazon、TikTok Shop、Temu、Shopee", level: "calm" },
    ],
    finance: [
      { action: "finance-market", label: "市场波动", value: "资产", hint: "利率、汇率、油价、黄金、股票", level: "watch" },
      { action: "geo-risk", label: "地缘冲击", value: "冲击", hint: "地缘事件对风险偏好的影响", level: "hot" },
    ],
    tech: [
      { action: "tech-ai", label: "AI/芯片", value: "AI", hint: "模型、芯片、算力和云服务", level: "watch" },
      { action: "tech-reg", label: "科技监管", value: "监管", hint: "AI、数据、平台和出口管制", level: "calm" },
    ],
    supply_chain: [
      { action: "supply-materials", label: "原料能源", value: "原料", hint: "锂、铜、稀土、石油、天然气", level: "watch" },
      { action: "logistics", label: "运输中断", value: "运输", hint: "港口、航运、工厂停摆", level: "hot" },
    ],
    geopolitics: [
      { action: "geo-risk", label: "国家风险", value: "安全", hint: "战争、制裁、军事、外交", level: "hot" },
      { action: "high-risk", label: "升级信号", value: metrics.high_risk_events.toString(), hint: "冲突升级和企业风控", level: "watch" },
    ],
    content: [
      { action: "content-hot", label: "选题热度", value: "热点", hint: "争议、反转、普通人影响", level: "watch" },
      { action: "high-risk", label: "强情绪事件", value: metrics.high_risk_events.toString(), hint: "适合解释型内容的高影响事件", level: "hot" },
    ],
  };
  const cards = [
    { action: "all", label: INDUSTRIES[currentIndustry].name, value: metrics.total_events.toString(), hint: INDUSTRIES[currentIndustry].description, level: "calm" },
    ...focusCards[currentIndustry],
    { action: "clusters", label: "事件簇", value: metrics.total_clusters.toString(), hint: "按国家和分类查看聚合信号", level: "calm" },
    { action: "countries", label: "涉及国家", value: metrics.unique_countries.toString(), hint: "缩放到全部涉及国家", level: "watch" },
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
  if (!mapReady || !maplibre || !map) return;
  if (!events.length) return;
  const bounds = new maplibre.LngLatBounds();
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

  const categoryActions: Record<string, string> = {
    "finance-market": "central_bank",
    "geo-risk": "military_conflict",
    "tech-ai": "ai_model",
    "tech-reg": "tech_regulation",
    "supply-materials": "raw_materials",
    "content-hot": "viral_topic",
  };
  if (categoryActions[action]) {
    resetSignalFilters();
    setSelectValue(categoryFilterEl, categoryActions[action]);
    sortByEl.value = "severity";
    sortOrderEl.value = "desc";
    await loadDashboard();
    fitMapToEvents();
    showStatus(`已筛选${categoryText(categoryActions[action])}相关事件`, "success");
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
  latestBriefItems = clusters;
  if (!clusters.length) {
    briefEl.innerHTML = `<pre class="brief-copy">${briefText || "暂无可展示的风险简报。"}</pre><div class="brief-empty">暂无可展示的事件簇。</div>`;
    return;
  }
  const sorted = [...clusters].sort((a, b) => {
    if (activeProfile) {
      const scoreDelta = profileRelevanceScore(b) - profileRelevanceScore(a);
      if (scoreDelta !== 0) return scoreDelta;
    }
    if (briefSortKey === "last_seen") {
      return String(b.last_seen || "").localeCompare(String(a.last_seen || ""));
    }
    return Number(b[briefSortKey] || 0) - Number(a[briefSortKey] || 0);
  });
  const relevant = activeProfile ? sorted.filter((item) => profileRelevanceScore(item) > 0).slice(0, 5) : [];

  briefEl.innerHTML = `
    <div class="brief-copy">${briefText || "暂无可展示的风险简报。"}</div>
    ${
      relevant.length
        ? `<div class="relevant-brief">
            <h3>与你相关优先</h3>
            ${relevant
              .map(
                (item) => `
              <button class="relevant-row" data-event-id="${item.id}">
                <b>${displayTitle(item)}</b>
                <span>${relevanceReasonText(item)}</span>
                <small>${categoryText(item.category)} · ${locationText(item.country, item.city)} · 相关度 ${profileRelevanceScore(item)}</small>
              </button>
            `,
              )
              .join("")}
          </div>`
        : ""
    }
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
            (item) => {
              const timestamp = eventTimeValue(item);
              return `
          <tr data-event-id="${item.id}">
            <td><span class="risk-chip" style="background:${riskColor(item.risk_level)}">${riskText(item.risk_level)}</span><b>${item.risk_score || 0}</b></td>
            <td>${item.country || t("unknown")}<small>${item.city || "无城市"}</small></td>
            <td><strong>${displayTitle(item)}</strong><small>${categoryText(item.category)}</small>${renderRelevanceBadge(item)}${relevanceReasonText(item) ? `<small>${relevanceReasonText(item)}</small>` : ""}</td>
            <td><span class="source-count">${item.source_count || 1}</span><small>${sourceSummary(item)}</small></td>
            <td>${item.event_count || 1}</td>
            <td>
              <span class="time-chip ${freshnessClass(timestamp)}">${relativeTime(timestamp)}</span>
              <small>${formatDateTime(timestamp)}</small>
            </td>
          </tr>
        `;
            },
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderMap(events: EventItem[]): void {
  latestRenderedEvents = prioritizeEvents(events);
  if (!mapReady || !maplibre || !map) return;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
  const activeRisks = new Set<string>();
  if (layerLowEl.checked) activeRisks.add("low");
  if (layerMediumEl.checked) activeRisks.add("medium");
  if (layerHighEl.checked) activeRisks.add("high");
  if (layerCriticalEl.checked) activeRisks.add("critical");

  const visible = latestRenderedEvents
    .filter((e) => activeRisks.has((e.risk_level || "low").toLowerCase()))
    .filter((event) => typeof event.lat === "number" && typeof event.lon === "number")

  const points = clusterModeEl.checked ? clusterEvents(visible) : visible.map((v) => ({ kind: "single" as const, event: v }));

  points.forEach((point) => {
    if (point.kind === "cluster") {
      const dot = document.createElement("button");
      dot.className = "map-dot cluster-dot";
      const clusterSize = Math.max(26, Math.min(42, 24 + Math.sqrt(point.count) * 5));
      dot.style.width = `${clusterSize}px`;
      dot.style.height = `${clusterSize}px`;
      dot.textContent = String(point.count);
      dot.title = `${point.count} ${t("events")}`;
      dot.setAttribute("aria-label", `${point.count} ${t("events")}`);
      dot.addEventListener("mouseenter", () => showClusterPopup(point));
      dot.addEventListener("mouseleave", hideEventPopup);
      dot.addEventListener("click", () => {
        hideEventPopup();
        if (point.sample.country) setActiveCountry(point.sample.country);
        renderClusterDetail(point.events);
        map.easeTo({
          center: [point.lon, point.lat],
          zoom: Math.min((map.getZoom?.() || 1) + 1.4, 5.5),
          duration: 500,
        });
      });
      const marker = new maplibre.Marker({ element: dot, anchor: "center" })
        .setLngLat([point.lon, point.lat])
        .addTo(map);
      mapMarkers.push(marker);
      return;
    }
    const event = point.event;
      const dot = document.createElement("button");
      dot.className = "map-dot";
      dot.dataset.risk = (event.risk_level || "low").toLowerCase();
      const size = Math.max(12, Math.min(22, 10 + (event.severity || 1) * 2.4));
      dot.style.width = `${size}px`;
      dot.style.height = `${size}px`;
      dot.style.background = riskColor(event.risk_level);
      dot.title = `${displayTitle(event)} (${event.country || t("unknown")})`;
      dot.setAttribute("aria-label", dot.title);
      dot.addEventListener("mouseenter", () => showEventPopup(event));
      dot.addEventListener("mouseleave", hideEventPopup);
      dot.addEventListener("click", () => {
        hideEventPopup();
        if (event.country) setActiveCountry(event.country);
        map.easeTo({
          center: [event.lon as number, event.lat as number],
          zoom: Math.max(map.getZoom?.() || 1, 3.2),
          duration: 450,
        });
        void analyzeMapEvent(event);
      });

      const marker = new maplibre.Marker({ element: dot, anchor: "center" })
        .setLngLat([event.lon as number, event.lat as number])
        .addTo(map);
      mapMarkers.push(marker);
  });
}

function renderAnalysisDetail(event: EventItem, isLoading = false): void {
  analysisFloatEl.classList.add("open");
  const summary = displaySummary(event);
  const impact = businessImpactText(event);
  const action = suggestedActionText(event);
  const market = event.market_impact || "";
  const opportunity = event.opportunity_signal || "";
  const content = event.content_angle || event.social_angle || "";
  const modeBlocks: Record<IndustryMode, string> = {
    overview: `
      <div class="analysis-note"><strong>全球影响</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>后续关注</strong><br/>${action}</div>
    `,
    trade: `
      <div class="analysis-note"><strong>对卖家/外贸/物流影响</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>成本和时效影响</strong><br/>${market || impact}</div>
      <div class="analysis-note"><strong>建议动作</strong><br/>${action}</div>
    `,
    finance: `
      <div class="analysis-note"><strong>市场影响</strong><br/>${market || impact}</div>
      <div class="analysis-note"><strong>可能影响的资产类别</strong><br/>${affectedGroupsText(event.affected_groups)}</div>
      <div class="analysis-note"><strong>风险提示</strong><br/>${action}；以上不构成投资建议。</div>
    `,
    tech: `
      <div class="analysis-note"><strong>对 AI/科技行业影响</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>涉及公司/技术/监管</strong><br/>${market || categoryText(event.category)}</div>
      <div class="analysis-note"><strong>机会信号</strong><br/>${opportunity || content || "关注产品、开发者生态和供应商变化。"}</div>
    `,
    supply_chain: `
      <div class="analysis-note"><strong>对原材料/产能/运输影响</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>供应链中断风险</strong><br/>${market || "关注交期、库存、运输路径和替代供应。"}</div>
      <div class="analysis-note"><strong>替代方案建议</strong><br/>${action}</div>
    `,
    geopolitics: `
      <div class="analysis-note"><strong>国家风险</strong><br/>${impact}</div>
      <div class="analysis-note"><strong>冲突升级可能</strong><br/>${market || "关注官方确认、制裁变化、军事和外交表态。"}</div>
      <div class="analysis-note"><strong>企业风控关注点</strong><br/>${action}</div>
    `,
    content: `
      <div class="analysis-note"><strong>热点价值</strong><br/>${opportunity || impact}</div>
      <div class="analysis-note"><strong>爆款角度 / 标题建议</strong><br/>${content || event.social_angle || summary}</div>
      <div class="analysis-note"><strong>短视频口播方向</strong><br/>${action}</div>
    `,
  };
  analysisDetailEl.innerHTML = `
      <div class="analysis-card">
      <div class="event-header">
        <span class="pill" style="background:${riskColor(event.risk_level)}">${riskText(event.risk_level)}</span>
        <span>${event.source}</span>
        <span>${statusText(event.status)}</span>
      </div>
      <h3>${displayTitle(event)}</h3>
      ${event.title ? `<div class="original-title">${displayOriginalTitle(event)}</div>` : ""}
      <p>${isLoading ? t("analyzingOne") : summary}</p>
      <div class="analysis-meta">
        <span>国家/城市：${locationText(event.country, event.city)}</span>
        <span>业务分类：${categoryText(event.category)} · 严重度 ${event.severity || 1}</span>
        <span>影响对象：${affectedGroupsText(event.affected_groups)}</span>
        ${activeProfile ? `<span>个人相关度：${profileRelevanceScore(event)}</span>` : ""}
        ${activeProfile && relevanceReasonText(event) ? `<span>相关原因：${relevanceReasonText(event)}</span>` : ""}
        ${activeProfile && event.affected_user_needs?.length ? `<span>关联需求：${event.affected_user_needs.join("、")}</span>` : ""}
        ${typeof event.confidence === "number" ? `<span>置信度 ${Math.round(event.confidence * 100)}%</span>` : ""}
      </div>
      ${modeBlocks[currentIndustry]}
      ${event.location_reason ? `<div class="analysis-note">${event.location_reason}</div>` : ""}
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
            ${event.title ? `<small>${displayOriginalTitle(event)}</small>` : ""}
            <em>${event.source} · ${categoryText(event.category)} · 严重度 ${event.severity || 1}</em>
          </button>
        `,
          )
          .join("")}
      </div>
    </div>
  `;
}

function openSignalItem(item: EventItem): void {
  if (latestRenderedEvents.some((event) => event.id === item.id)) {
    void analyzeMapEvent(item);
    return;
  }
  analysisFloatEl.classList.add("open");
  renderAnalysisDetail(item);
}

async function analyzeMapEvent(event: EventItem): Promise<void> {
  hideEventPopup();
  renderAnalysisDetail(event, event.status !== "analyzed");
  if (event.status === "analyzed") return;
  const ready = await ensureLlmReadyForAnalysis();
  if (!ready) return;

  try {
    const result = await postJson<SingleAnalyzeResponse>(`/events/${event.id}/analyze?industry=${currentIndustry}&llm=${currentLlm}&lang=${currentLanguage}`);
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
  if (!mapReady || !maplibre || !map) return;
  hideEventPopup();
  const summary = displaySummary(event);
  const timestamp = eventTimeValue(event);
  hoverPopup = new maplibre.Popup({ closeButton: false, closeOnClick: false, offset: 14, maxWidth: "320px" })
    .setLngLat([event.lon as number, event.lat as number])
    .setHTML(`
      <div class="intel-popup">
        <div class="intel-popup-meta">
          <span style="background:${riskColor(event.risk_level)}">${riskText(event.risk_level)}</span>
          ${event.source} · ${relativeTime(timestamp)} · ${formatDateTime(timestamp)}
        </div>
        <strong>${displayTitle(event)}</strong>
        ${event.title ? `<small>${displayOriginalTitle(event)}</small>` : ""}
        <p>${summary.slice(0, 220) || t("noSummary")}</p>
        <small>${locationText(event.country, event.city)} · ${categoryText(event.category)}</small>
        ${renderRelevanceBadge(event)}
        ${relevanceReasonText(event) ? `<small>${relevanceReasonText(event)}</small>` : ""}
        ${typeof event.event_count === "number" ? `<small>${event.event_count} 条报道 · ${event.source_count || 1} 个来源 · RSS ${event.rss_count || 0} · GDELT ${event.gdelt_count || 0} · 风险 ${event.risk_score || 0}</small>` : ""}
        ${event.location_reason ? `<small>${event.location_reason} · ${Math.round((event.location_confidence || 0) * 100)}%</small>` : ""}
      </div>
    `)
    .addTo(map);
}

function showClusterPopup(point: { lat: number; lon: number; count: number; sample: EventItem; events: EventItem[] }): void {
  if (!mapReady || !maplibre || !map) return;
  hideEventPopup();
  const topRisks = point.events
    .reduce<Record<string, number>>((acc, event) => {
      const key = riskText(event.risk_level);
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
  const riskSummary = Object.entries(topRisks)
    .map(([risk, count]) => `${risk} ${count}`)
    .join(" · ");
  const latest = point.events
    .slice()
    .sort((a, b) => new Date(eventTimeValue(b) || 0).getTime() - new Date(eventTimeValue(a) || 0).getTime())[0];
  hoverPopup = new maplibre.Popup({ closeButton: false, closeOnClick: false, offset: 16, maxWidth: "280px" })
    .setLngLat([point.lon, point.lat])
    .setHTML(`
      <div class="intel-popup compact">
        <div class="intel-popup-meta">
          <span>${t("cluster")}</span>
          ${point.sample.country || t("mixed")} · ${point.count} ${t("events")}
        </div>
        <strong>${displayTitle(latest || point.sample)}</strong>
        <small>${riskSummary || t("unknown")}</small>
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
          ${item.title ? `<em>${displayOriginalTitle(item)}</em>` : ""}
          <small>${item.source} · ${riskText(item.risk_level)} · ${relativeTime(eventTimeValue(item))}</small>
        </a>`,
        )
        .join("")}
    </div>
  `;
}

function activateSidePanel(panel: "brief" | "country" | "keywords"): void {
  sideTabEls.forEach((button) => {
    button.classList.toggle("active", button.dataset.sideTab === panel);
  });
  sidePanelEls.forEach((section) => {
    section.classList.toggle("active", section.dataset.sidePanel === panel);
  });
}

async function loadCountryDetail(country: string): Promise<void> {
  const range = timeRangeEl.value;
  const data = await fetchJson<CountryInsight>(
    `/country-insight?country=${encodeURIComponent(country)}&time_range=${range}&industry=${currentIndustry}&lang=${currentLanguage}`,
  );
  renderCountryDetail(data);
}

function setActiveCountry(country: string): void {
  activeCountry = country;
  countryFilterEl.value = country;
  activateSidePanel("country");
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
    const isBackgroundJob = result.ok && result.count === 0 && result.message.includes("后台");
    if (isBackgroundJob) {
      showStatus(result.message, "working");
      if (path === "/collect") {
        collectionStatusEl.className = "collection-status running";
        collectionStatusEl.textContent = "后台采集中";
      }
      startJobPolling(path);
      return;
    }
    await refreshCollectionStatus();
    await loadFilters();
    await loadDashboard();
    const countText = typeof result.count === "number" ? ` · ${result.count}` : "";
    showStatus(
      result.ok ? `${doneText}${countText}` : result.message,
      result.ok ? "success" : "error",
    );
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
    void refreshCollectionStatus();
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
  const saved = localStorage.getItem(`worldpulse-keywords-${currentIndustry}`);
  if (!saved) return INDUSTRIES[currentIndustry].keywords;
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
  localStorage.setItem(`worldpulse-keywords-${currentIndustry}`, keywords.join("\n"));
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
  llmSelectEl.options[0].textContent = currentLanguage === "zh" ? "自动选择" : "Auto";
  llmSelectEl.options[1].textContent = "OpenAI";
  llmSelectEl.options[2].textContent = "DeepSeek";
  llmSelectEl.options[3].textContent = currentLanguage === "zh" ? "本地 Ollama" : "Ollama";
  llmSelectEl.value = currentLlm;
  llmConfigBtn.textContent = t("llmConfig");
  llmCheckBtn.textContent = t("llmCheck");
  saveLlmConfigBtn.textContent = t("llmSave");
  profileInputEl.placeholder = t("profilePlaceholder");
  renderMapCount(latestMapTotal);
  renderProfileSummary();
  updateIndustryTabs();
  if (activeAction) {
    showStatus(activeAction === "/collect" ? t("collecting") : t("analyzing"), "working");
  }
}

function updateIndustryTabs(): void {
  industryTabsEl.querySelectorAll<HTMLButtonElement>("button[data-industry]").forEach((button) => {
    button.classList.toggle("active", button.dataset.industry === currentIndustry);
  });
  const mode = INDUSTRIES[currentIndustry];
  document.querySelector(".product-copy")!.textContent = `当前模式：${mode.name}。面向${mode.description}，筛出有时间、有来源、有地理位置的全球事件信号。`;
}

async function switchIndustry(industry: IndustryMode): Promise<void> {
  currentIndustry = industry;
  localStorage.setItem("worldpulse-industry", currentIndustry);
  resetSignalFilters();
  activeCountry = null;
  keywordInputEl.value = loadKeywords().join("\n");
  updateIndustryTabs();
  showStatus(`已切换行业模式：${INDUSTRIES[currentIndustry].name}`, "success");
  await loadFilters();
  await loadDashboard();
  fitMapToEvents();
}

async function loadFilters(): Promise<void> {
  const range = timeRangeEl.value;
  const filters = await fetchJson<FiltersResponse>(`/filters?time_range=${range}&industry=${currentIndustry}`);
  fillSelect(countryFilterEl, filters.countries, t("allCountries"));
  fillSelect(categoryFilterEl, filters.categories, t("allCategories"));
  fillSelect(riskFilterEl, filters.risk_levels, t("allRisks"));
  fillSelect(statusFilterEl, filters.statuses, t("allStatus"));
}

function buildSignalQuery(): string {
  const params = new URLSearchParams();
  params.set("time_range", timeRangeEl.value);
  params.set("industry", currentIndustry);
  if (activeProfile) params.set("profile", profileQueryParam());
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
    const profileParam = activeProfile ? `&profile=${encodeURIComponent(profileQueryParam())}` : "";
    const [metrics, brief, mapEvents] = await Promise.all([
      fetchJson<Metrics>(`/metrics?time_range=${range}&industry=${currentIndustry}`),
      fetchJson<BriefResponse>(`/brief?time_range=${range}&industry=${currentIndustry}${profileParam}&lang=${currentLanguage}`),
      fetchJson<MapEventsResponse>(`/map-events?${buildSignalQuery()}&lang=${currentLanguage}`),
    ]);
    renderMetrics(metrics);
    renderBriefTable(brief.clusters || [], brief.brief);
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

llmSelectEl.addEventListener("change", () => {
  currentLlm = (llmSelectEl.value as LlmChoice) || "auto";
  localStorage.setItem("worldpulse-llm", currentLlm);
  showStatus(`已切换模型：${currentLlm}`, "success");
  void refreshLlmStatus();
});

llmCheckBtn.addEventListener("click", () => {
  void refreshLlmStatus();
});
llmConfigBtn.addEventListener("click", () => {
  llmConfigPanelEl.hidden = !llmConfigPanelEl.hidden;
});
saveLlmConfigBtn.addEventListener("click", () => {
  void saveLlmConfig();
});
sourceHealthBtn.addEventListener("click", () => {
  void showSourceHealthSummary();
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
  activateSidePanel(activeCountry ? "country" : "keywords");
});

sideTabEls.forEach((button) => {
  button.addEventListener("click", () => {
    const panel = button.dataset.sideTab as "brief" | "country" | "keywords" | undefined;
    if (panel) activateSidePanel(panel);
  });
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
  const relevantRow = (ev.target as HTMLElement).closest(".relevant-row") as HTMLButtonElement | null;
  if (relevantRow) {
    const item = [...latestBriefItems, ...latestRenderedEvents].find((event) => event.id === relevantRow.dataset.eventId);
    if (!item) return;
    if (item.country) setActiveCountry(item.country);
    openSignalItem(item);
    return;
  }
  const row = (ev.target as HTMLElement).closest("tr[data-event-id]") as HTMLTableRowElement | null;
  if (!row) return;
  const item = [...latestBriefItems, ...latestRenderedEvents].find((event) => event.id === row.dataset.eventId);
  if (!item) return;
  if (item.country) setActiveCountry(item.country);
  openSignalItem(item);
});

collectBtn.addEventListener("click", () => void runAction("/collect"));
analyzeBtn.addEventListener("click", () => void runAction("/geotag"));
profileBtn.addEventListener("click", () => {
  profilePanelEl.hidden = !profilePanelEl.hidden;
  if (!profilePanelEl.hidden) profileInputEl.focus();
});
saveProfileBtn.addEventListener("click", () => void analyzeAndSaveProfile());
clearProfileBtn.addEventListener("click", () => {
  clearUserProfile();
  showStatus("画像已清除", "success");
  void loadDashboard();
});
cancelBtn.addEventListener("click", () => void cancelActiveAction());
refreshBtn.addEventListener("click", () => void loadDashboard());
saveKeywordsBtn.addEventListener("click", saveKeywords);
industryTabsEl.addEventListener("click", (ev) => {
  const button = (ev.target as HTMLElement).closest("button[data-industry]") as HTMLButtonElement | null;
  if (!button) return;
  const industry = button.dataset.industry as IndustryMode;
  void switchIndustry(industry);
});

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
void refreshLlmStatus();
void refreshCollectionStatus();
window.setInterval(() => void refreshCollectionStatus(), 60000);
void (async () => {
  try {
    await initMap();
  } catch (error) {
    showStatus(`地图初始化失败: ${(error as Error).message}`, "error");
  }
  await loadFilters();
  await loadDashboard();
})();
