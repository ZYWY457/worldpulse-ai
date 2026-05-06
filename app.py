import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db.database import Database
from collectors.rss_collector import RSSCollector
from ai.analyzer import EventAnalyzer
from ai.social_writer import SocialMediaWriter
from services.risk_score import RiskScorer
from services.correlation import EventCorrelator
import json

# Page Config
st.set_page_config(
    page_title="WorldPulse AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme and World Monitor style
st.markdown("""
<style>
    /* Dark theme base */
    :root {
        --primary-color: #00ff41;
        --danger-color: #ff3333;
        --warning-color: #ffaa00;
        --info-color: #00ccff;
        --bg-dark: #0a0e27;
        --bg-darker: #050812;
        --text-light: #e0e0e0;
        --border-color: #1a2332;
    }
    
    body, .main, .stApp {
        background-color: #0a0e27;
        color: #e0e0e0;
    }
    
    /* Header styling */
    .header-title {
        font-size: 28px;
        font-weight: bold;
        color: #00ff41;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        margin-bottom: 10px;
    }
    
    .header-subtitle {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a2332 0%, #0f1823 100%);
        border: 1px solid #00ff41;
        border-radius: 4px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.1);
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #00ff41;
        text-shadow: 0 0 5px rgba(0, 255, 65, 0.2);
    }
    
    .metric-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }
    
    /* Event list styling */
    .event-item {
        background: linear-gradient(135deg, #1a2332 0%, #0f1823 100%);
        border-left: 3px solid #00ff41;
        border-radius: 4px;
        padding: 12px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    
    .event-item:hover {
        border-left-color: #ffaa00;
        box-shadow: 0 0 15px rgba(255, 170, 0, 0.2);
    }
    
    .event-title {
        font-size: 14px;
        font-weight: bold;
        color: #e0e0e0;
        margin-bottom: 8px;
    }
    
    .event-meta {
        font-size: 11px;
        color: #888;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 8px;
    }
    
    .event-tag {
        background: rgba(0, 255, 65, 0.1);
        border: 1px solid #00ff41;
        color: #00ff41;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        text-transform: uppercase;
    }
    
    .event-tag.critical {
        background: rgba(255, 51, 51, 0.1);
        border-color: #ff3333;
        color: #ff3333;
    }
    
    .event-tag.high {
        background: rgba(255, 170, 0, 0.1);
        border-color: #ffaa00;
        color: #ffaa00;
    }
    
    .event-tag.medium {
        background: rgba(0, 204, 255, 0.1);
        border-color: #00ccff;
        color: #00ccff;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #00ff41 0%, #00cc33 100%);
        color: #000;
        border: none;
        border-radius: 4px;
        font-weight: bold;
        padding: 8px 16px;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
        transform: translateY(-2px);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        border-bottom: 1px solid #1a2332;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #888;
        border-radius: 0;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stTabs [aria-selected="true"] {
        color: #00ff41;
        border-bottom: 2px solid #00ff41;
        box-shadow: 0 2px 8px rgba(0, 255, 65, 0.2);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a2332;
        border: 1px solid #2a3a52;
        border-radius: 4px;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #2a3a52;
    }
    
    /* Divider */
    hr {
        border-color: #1a2332;
        margin: 20px 0;
    }
    
    /* Text area */
    .stTextArea textarea {
        background-color: #0f1823;
        color: #e0e0e0;
        border: 1px solid #1a2332;
        border-radius: 4px;
    }
    
    .stTextArea textarea:focus {
        border-color: #00ff41;
        box-shadow: 0 0 8px rgba(0, 255, 65, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Init DB and Services
db = Database("storage/worldpulse.db")
collector = RSSCollector(db)
analyzer = EventAnalyzer(db)
social_writer = SocialMediaWriter()
risk_scorer = RiskScorer(db)
correlator = EventCorrelator(db)

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown('<div class="header-title">🌍 WORLDPULSE AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-subtitle">Real-time Global Intelligence Dashboard</div>', unsafe_allow_html=True)

with col2:
    st.write("")
    if st.button("🔄 COLLECT", use_container_width=True):
        with st.spinner("Collecting news..."):
            new_count = collector.collect()
            st.success(f"✓ Added {new_count} new events")
            st.rerun()

with col3:
    st.write("")
    if st.button("🤖 ANALYZE", use_container_width=True):
        with st.spinner("Analyzing..."):
            analyzed_count = analyzer.process_unanalyzed()
            st.success(f"✓ Analyzed {analyzed_count} events")
            st.rerun()

st.markdown("---")

# Load Data
def load_data():
    with db.get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM events ORDER BY published_at DESC", conn)
    return df

df = load_data()

# Time filter
time_range = st.radio(
    "TIME RANGE",
    ["1H", "24H", "7D", "ALL"],
    horizontal=True,
    label_visibility="collapsed"
)

if not df.empty:
    df['published_at'] = pd.to_datetime(df['published_at'])
    now = datetime.now()
    if time_range == "1H":
        df = df[df['published_at'] > (now - timedelta(hours=1))]
    elif time_range == "24H":
        df = df[df['published_at'] > (now - timedelta(hours=24))]
    elif time_range == "7D":
        df = df[df['published_at'] > (now - timedelta(days=7))]

# Metrics & Strategic Risk
if not df.empty:
    st.markdown("### GLOBAL SITUATION")
    
    # Calculate Strategic Risk
    analyzed_df = df[df['status'] == 'analyzed']
    strategic_risk = risk_scorer.calculate_strategic_risk(analyzed_df.to_dict('records'))
    
    col_risk, col_metrics = st.columns([1, 3])
    
    with col_risk:
        risk_color = "#00ff41" if strategic_risk < 30 else "#ffaa00" if strategic_risk < 60 else "#ff3333"
        st.markdown(f"""
        <div class="metric-card" style="border-color: {risk_color}; text-align: center;">
            <div class="metric-label">Strategic Risk Index</div>
            <div class="metric-value" style="color: {risk_color}; font-size: 48px;">{int(strategic_risk)}</div>
            <div style="font-size: 10px; color: #888; margin-top: 5px;">COMPOSITE GEOPOLITICAL SCORE</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_metrics:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(df)}</div>
                <div class="metric-label">Total Events</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            critical = len(df[df['risk_level'].isin(['high', 'critical'])])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #ff3333;">{critical}</div>
                <div class="metric-label">High Risk Alerts</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            countries = df['country'].nunique() if 'country' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{countries}</div>
                <div class="metric-label">Active Theaters</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# Intelligence Briefing
st.markdown("### SITUATIONAL AWARENESS")
if not df.empty:
    brief = correlator.get_intelligence_brief(df[df['status'] == 'analyzed'].to_dict('records'))
    st.info(brief)

st.markdown("---")

# Map
st.markdown("### GLOBAL EVENT MAP")
map_df = df[df['lat'].notnull() & df['lon'].notnull()].copy()

if not map_df.empty:
    # Create color mapping for risk levels
    color_map = {
        "low": "#00ff41",
        "medium": "#00ccff",
        "high": "#ffaa00",
        "critical": "#ff3333"
    }
    
    map_df['color'] = map_df['risk_level'].map(color_map).fillna("#00ff41")
    map_df['size'] = map_df['severity'].fillna(1) * 8
    
    fig = go.Figure()
    
    # Add scatter for each risk level to maintain color consistency
    for risk_level, color in color_map.items():
        risk_data = map_df[map_df['risk_level'] == risk_level]
        if not risk_data.empty:
            fig.add_trace(go.Scattergeo(
                lon=risk_data['lon'],
                lat=risk_data['lat'],
                mode='markers',
                marker=dict(
                    size=risk_data['severity'].fillna(1) * 6,
                    color=color,
                    opacity=0.7,
                    line=dict(width=1, color='rgba(255,255,255,0.3)')
                ),
                text=risk_data.apply(lambda x: f"<b>{x['title']}</b><br>Country: {x['country']}<br>Category: {x['category']}<br>Risk: {x['risk_level']}", axis=1),
                hovertemplate='%{text}<extra></extra>',
                name=risk_level.upper(),
                showlegend=True
            ))
    
    fig.update_layout(
        geo=dict(
            projection_type='natural earth',
            bgcolor='rgba(10, 14, 39, 0.8)',
            coastlinecolor='rgba(100, 100, 100, 0.2)',
            landcolor='rgba(20, 30, 50, 0.5)',
            showland=True,
            showocean=True,
            oceancolor='rgba(10, 14, 39, 0.8)',
        ),
        paper_bgcolor='rgba(10, 14, 39, 0)',
        plot_bgcolor='rgba(10, 14, 39, 0)',
        font=dict(color='#e0e0e0', size=10),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        hovermode='closest',
        legend=dict(
            bgcolor='rgba(26, 35, 50, 0.8)',
            bordercolor='#00ff41',
            borderwidth=1,
            font=dict(size=10)
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No geographic data available. Click ANALYZE to process events.")

st.markdown("---")

# Event List
st.markdown("### EVENTS")

# Filter controls
col1, col2, col3 = st.columns(3)
with col1:
    category_filter = st.multiselect("CATEGORY", df['category'].unique() if 'category' in df.columns else [], default=[])
with col2:
    risk_filter = st.multiselect("RISK LEVEL", ["low", "medium", "high", "critical"], default=[])
with col3:
    source_filter = st.multiselect("SOURCE", df['source'].unique() if 'source' in df.columns else [], default=[])

# Apply filters
filtered_df = df.copy()
if category_filter:
    filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
if risk_filter:
    filtered_df = filtered_df[filtered_df['risk_level'].isin(risk_filter)]
if source_filter:
    filtered_df = filtered_df[filtered_df['source'].isin(source_filter)]

# Display events
for idx, row in filtered_df.iterrows():
    risk_color_map = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low"
    }
    # Safe access for risk_level and other fields
    raw_risk = str(row.get('risk_level', 'low')) if pd.notnull(row.get('risk_level')) else 'low'
    risk_tag = risk_color_map.get(raw_risk.lower(), 'low')
    risk_display = raw_risk.upper()
    
    category_display = str(row.get('category', 'other')).upper() if pd.notnull(row.get('category')) else 'OTHER'
    country_display = str(row.get('country', 'Unknown')) if pd.notnull(row.get('country')) else 'Unknown'
    source_display = str(row.get('source', 'Unknown')) if pd.notnull(row.get('source')) else 'Unknown'
    title_display = str(row.get('title', 'No Title')) if pd.notnull(row.get('title')) else 'No Title'
    
    event_html = f"""
    <div class="event-item">
        <div class="event-title">{title_display}</div>
        <div class="event-meta">
            <span style="color: #888;">{source_display}</span>
            <span style="color: #888;">•</span>
            <span style="color: #888;">{pd.to_datetime(row['published_at']).strftime('%Y-%m-%d %H:%M') if pd.notnull(row.get('published_at')) else 'N/A'}</span>
            <span style="color: #888;">•</span>
            <span class="event-tag {risk_tag}">{risk_display}</span>
            <span class="event-tag">{category_display}</span>
            <span style="color: #888;">📍 {country_display}</span>
        </div>
    """
    
    if row['status'] == 'analyzed' and row.get('ai_summary'):
        event_html += f"""
        <div style="font-size: 12px; color: #b0b0b0; margin-bottom: 8px; line-height: 1.5;">
            {row['ai_summary']}
        </div>
        """
    else:
        event_html += f"""
        <div style="font-size: 12px; color: #888; margin-bottom: 8px; line-height: 1.5;">
            {row.get('raw_summary', 'No summary available')[:200]}...
        </div>
        """
    
    event_html += f"""
        <div style="display: flex; gap: 8px; margin-top: 8px;">
            <a href="{row['url']}" target="_blank" style="color: #00ff41; text-decoration: none; font-size: 11px; text-transform: uppercase;">→ VIEW SOURCE</a>
    """
    
    if row['status'] == 'analyzed':
        event_html += f"""
            <span style="color: #888;">•</span>
            <span style="color: #00ccff; cursor: pointer; font-size: 11px; text-transform: uppercase; text-decoration: underline;">✨ SOCIAL</span>
        """
    
    event_html += """
        </div>
    </div>
    """
    
    st.markdown(event_html, unsafe_allow_html=True)
    
    # Social media generation
    if row['status'] == 'analyzed':
        if st.button("Generate Social Content", key=f"btn_{row['id']}", use_container_width=True):
            with st.spinner("Generating..."):
                social_content = social_writer.generate_social_content(
                    title=row['title'],
                    ai_summary=row.get('ai_summary', row['raw_summary']),
                    source=row['source']
                )
                if social_content:
                    st.session_state[f"social_{row['id']}"] = social_content
        
        if f"social_{row['id']}" in st.session_state:
            social = st.session_state[f"social_{row['id']}"]
            
            tab1, tab2, tab3 = st.tabs(["WEIBO", "XIAOHONGSHU", "VIDEO"])
            
            with tab1:
                st.text_area("Weibo Content", social.get('weibo', ''), height=100, key=f"weibo_{row['id']}", disabled=True)
            
            with tab2:
                st.text_area("Xiaohongshu Content", social.get('xiaohongshu', ''), height=150, key=f"xhs_{row['id']}", disabled=True)
            
            with tab3:
                st.text_area("Video Script", social.get('video_script', ''), height=150, key=f"video_{row['id']}", disabled=True)
            
            st.caption("⚠️ Content for information purposes only. Not investment advice.")

st.markdown("---")
st.markdown('<div style="text-align: center; color: #666; font-size: 11px;">WorldPulse AI • Real-time Global Intelligence Dashboard</div>', unsafe_allow_html=True)
