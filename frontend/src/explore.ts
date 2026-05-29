// WorldPulse Explore - Low-noise information discovery interface

import type { EventItem } from "./main";

export type ExploreTimeRange = "24h" | "7d" | "30d";
export type ExploreIndustry = "overview" | "tech" | "finance" | "trade" | "supply_chain" | "geopolitics" | "content";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "http://localhost:8000";

/**
 * Get source quality label based on source_weight or source_count
 */
export function getSourceQualityLabel(event: EventItem, lang: "zh" | "en"): string {
  const weight = (event as any).source_weight ?? 0;
  if (weight >= 0.9) return lang === "zh" ? "高" : "High";
  if (weight >= 0.75) return lang === "zh" ? "中高" : "Medium-High";
  if (weight >= 0.6) return lang === "zh" ? "中" : "Medium";
  return lang === "zh" ? "待验证" : "Needs verification";
}

/**
 * Get noise hint based on heuristics
 */
export function getNoiseHint(event: EventItem, lang: "zh" | "en"): string {
  const weight = (event as any).source_weight ?? 0;
  const source = (event.source || "").toLowerCase();
  const hasSummary = !!(event.ai_summary || event.summary_zh || event.raw_summary);
  const summaryLen = (event.ai_summary?.length || 0) + (event.summary_zh?.length || 0) + (event.raw_summary?.length || 0);
  
  // Official/institutional sources with high weight = low noise
  if (weight >= 0.85 && (source.includes("gov") || source.includes("reuters") || source.includes("bloomberg"))) {
    return lang === "zh" ? "低噪声" : "Low noise";
  }
  
  // Google News aggregator or low weight = needs verification
  if (source.includes("google") || weight < 0.6) {
    return lang === "zh" ? "需核验" : "Needs verification";
  }
  
  // No summary or very short = insufficient info
  if (!hasSummary || summaryLen < 50) {
    return lang === "zh" ? "信息不足" : "Insufficient information";
  }
  
  return "";
}

/**
 * Get "why it matters" text
 */
export function getWhyMatters(event: EventItem, lang: "zh" | "en"): string {
  // Priority order: business_impact, market_impact, opportunity_signal, content_angle
  if (event.business_impact) return event.business_impact;
  if (event.market_impact) return event.market_impact;
  if (event.opportunity_signal) return event.opportunity_signal;
  if (event.content_angle) return event.content_angle;
  
  // Fallback
  return lang === "zh" 
    ? "该事件可能影响相关行业、市场或地区，需要继续观察来源确认。"
    : "This event may affect related industries, markets, or regions. Continue monitoring sources for confirmation.";
}

/**
 * Get one-sentence summary
 */
export function getOneSentence(event: EventItem, lang: "zh" | "en"): string {
  if (lang === "zh" && event.summary_zh) return event.summary_zh;
  if (event.ai_summary) return event.ai_summary;
  if (event.raw_summary) return event.raw_summary;
  if (event.summary) return event.summary;
  return lang === "zh" ? "暂无摘要。" : "No summary available.";
}

/**
 * Render a single Worth Knowing card
 */
export function renderWorthCard(event: EventItem, lang: "zh" | "en"): string {
  const quality = getSourceQualityLabel(event, lang);
  const noise = getNoiseHint(event, lang);
  const whyMatters = getWhyMatters(event, lang);
  const summary = getOneSentence(event, lang);
  
  const riskLevel = event.risk_level || "low";
  const riskClass = riskLevel === "critical" ? "risk-critical" 
    : riskLevel === "high" ? "risk-high"
    : riskLevel === "medium" ? "risk-medium" : "risk-low";
  
  const riskText = lang === "zh" 
    ? (riskLevel === "critical" ? "严重" : riskLevel === "high" ? "高" : riskLevel === "medium" ? "中" : "低")
    : (riskLevel === "critical" ? "Critical" : riskLevel === "high" ? "High" : riskLevel === "medium" ? "Medium" : "Low");
  
  const location = event.country || event.city || (lang === "zh" ? "未知地区" : "Unknown");
  const timeAgo = formatTimeAgo(event.published_at || event.created_at, lang);
  
  const hasMultiSource = (event.source_count || 0) > 1 || (event.rss_count || 0) + (event.gdelt_count || 0) > 1;
  const sourceNote = hasMultiSource 
    ? (lang === "zh" ? "多来源交叉出现" : "Cross-verified by multiple sources")
    : "";

  return `
    <article class="worth-card" data-event-id="${event.id}">
      <div class="card-header">
        <span class="risk-chip ${riskClass}">${riskText}</span>
        <span class="source-quality-chip">${lang === "zh" ? "来源质量" : "Source"}: ${quality}</span>
        ${noise ? `<span class="noise-chip">${noise}</span>` : ""}
      </div>
      
      <h3 class="card-title">${escapeHtml(event.title_zh || event.title)}</h3>
      
      <p class="card-summary">${escapeHtml(summary)}</p>
      
      <div class="why-matters">
        <strong>${lang === "zh" ? "为什么值得知道" : "Why it matters"}:</strong>
        <span>${escapeHtml(whyMatters)}</span>
      </div>
      
      <div class="card-meta">
        <span class="meta-item">📍 ${escapeHtml(location)}</span>
        <span class="meta-item">🕐 ${timeAgo}</span>
        ${sourceNote ? `<span class="meta-item source-note">${sourceNote}</span>` : ""}
      </div>
      
      <div class="card-actions">
        <button class="btn-detail" data-action="detail" data-event-id="${event.id}">
          ${lang === "zh" ? "查看详情" : "View details"}
        </button>
        <a href="${escapeHtml(event.url)}" target="_blank" rel="noopener noreferrer" class="btn-original">
          ${lang === "zh" ? "打开原文" : "Open original"}
        </a>
        ${event.lat && event.lon ? `
          <button class="btn-map" data-action="map" data-lat="${event.lat}" data-lon="${event.lon}">
            ${lang === "zh" ? "去地图看" : "View on map"}
          </button>
        ` : ""}
      </div>
    </article>
  `;
}

/**
 * Format time ago
 */
function formatTimeAgo(timestamp: string | null | undefined, lang: "zh" | "en"): string {
  if (!timestamp) return lang === "zh" ? "未知时间" : "Unknown time";
  
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return lang === "zh" ? "时间无效" : "Invalid time";
  
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMinutes < 60) {
    return lang === "zh" ? `${diffMinutes || 1}分钟前` : `${diffMinutes || 1}m ago`;
  }
  if (diffHours < 48) {
    return lang === "zh" ? `${diffHours}小时前` : `${diffHours}h ago`;
  }
  return lang === "zh" ? `${diffDays}天前` : `${diffDays}d ago`;
}

/**
 * Escape HTML
 */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Load explore data from backend
 */
export async function loadExploreData(
  timeRange: ExploreTimeRange,
  industry: ExploreIndustry,
  lang: "zh" | "en"
): Promise<EventItem[]> {
  try {
    // First try /brief endpoint
    const briefUrl = `${API_BASE}/brief?time_range=${timeRange}&industry=${industry}&lang=${lang}`;
    const briefRes = await fetch(briefUrl);
    if (briefRes.ok) {
      const data = await briefRes.json();
      if (data.clusters && data.clusters.length > 0) {
        return data.clusters;
      }
    }
  } catch (e) {
    console.warn("Brief endpoint failed, trying events:", e);
  }
  
  // Fallback to /events
  try {
    const eventsUrl = `${API_BASE}/events?time_range=${timeRange}&page_size=20&lang=${lang}`;
    const eventsRes = await fetch(eventsUrl);
    if (eventsRes.ok) {
      const data = await eventsRes.json();
      return data.items || data;
    }
  } catch (e) {
    console.warn("Events endpoint failed:", e);
  }
  
  return [];
}

/**
 * Render the worth knowing grid
 */
export function renderWorthGrid(container: HTMLElement, events: EventItem[], lang: "zh" | "en"): void {
  if (!events || events.length === 0) {
    container.innerHTML = "";
    return;
  }
  
  container.innerHTML = events.map(e => renderWorthCard(e, lang)).join("");
}

/**
 * Show empty state
 */
export function showEmptyState(container: HTMLElement, emptyEl: HTMLElement): void {
  container.innerHTML = "";
  emptyEl.hidden = false;
}

/**
 * Hide empty state
 */
export function hideEmptyState(emptyEl: HTMLElement): void {
  emptyEl.hidden = true;
}
