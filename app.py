import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from db.database import Database
from collectors.gdelt_collector import GDELTCollector
from collectors.rss_collector import RSSCollector
from ai.analyzer import EventAnalyzer
from ai.ai_client import AIClient
from ai.prompts import SOCIAL_WRITER_PROMPT
from ai.social_writer import SocialMediaWriter
import json

# Page Config
st.set_page_config(page_title="WorldPulse AI Dashboard", layout="wide")

# Init DB and Services
db = Database("storage/worldpulse.db")
collector = RSSCollector(db)
gdelt_collector = GDELTCollector(db)
analyzer = EventAnalyzer(db)
ai_client = AIClient()
social_writer = SocialMediaWriter()

# Sidebar
st.sidebar.title("WorldPulse AI")
st.sidebar.markdown("全球事件监控仪表盘")

# Filters
time_range = st.sidebar.selectbox(
    "时间范围",
    ["今日", "近 24 小时", "近 7 天", "全部"]
)

# Load Data
def load_data():
    with db.get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM events ORDER BY published_at DESC", conn)
    return df

df = load_data()

# Filter Logic
if not df.empty:
    df['published_at'] = pd.to_datetime(df['published_at'])
    now = datetime.now()
    if time_range == "今日":
        df = df[df['published_at'].dt.date == now.date()]
    elif time_range == "近 24 小时":
        df = df[df['published_at'] > (now - timedelta(hours=24))]
    elif time_range == "近 7 天":
        df = df[df['published_at'] > (now - timedelta(days=7))]

# Main UI
st.title("🌍 WorldPulse AI Dashboard")

# Header Buttons
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.write(f"最近更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    if st.button("🔄 采集新闻"):
        with st.spinner("正在采集..."):
            rss_count = collector.collect()
            gdelt_count = gdelt_collector.collect()
            st.success(f"新增 {rss_count + gdelt_count} 条新闻（RSS {rss_count}，GDELT {gdelt_count}）")
            st.rerun()
with col3:
    if st.button("🤖 AI 分析"):
        with st.spinner("正在分析..."):
            analyzed_count = analyzer.process_unanalyzed()
            st.success(f"已分析 {analyzed_count} 条新闻")
            st.rerun()

# Metrics
if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("今日新闻", len(df))
    m2.metric("已分析", len(df[df['status'] == 'analyzed']))
    m3.metric("高风险", len(df[df['risk_level'].isin(['high', 'critical'])]))
    m4.metric("涉及国家", df['country'].nunique() if 'country' in df.columns else 0)

# Map
st.subheader("📍 全球事件地图")
map_df = df[df['lat'].notnull() & df['lon'].notnull()]
if not map_df.empty:
    fig = px.scatter_geo(
        map_df,
        lat="lat",
        lon="lon",
        color="risk_level",
        size="severity",
        hover_name="title",
        hover_data=["country", "category", "risk_level"],
        projection="natural earth",
        color_discrete_map={
            "low": "blue",
            "medium": "yellow",
            "high": "orange",
            "critical": "red"
        }
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无地理位置数据可供展示")

# Briefing
st.subheader("📝 今日 AI 全球简报")
if not df.empty and len(df[df['status'] == 'analyzed']) > 0:
    analyzed_df = df[df['status'] == 'analyzed']
    summary_text = f"今日共监测到 {len(df)} 条事件，其中 {len(analyzed_df)} 条已完成 AI 深度分析。重点关注：\n"
    for _, row in analyzed_df.head(3).iterrows():
        summary_text += f"- **[{row['category']}]** {row['ai_summary']}\n"
    st.info(summary_text)
else:
    st.write("点击 'AI 分析' 按钮生成简报")

# Event List
st.subheader("📰 事件列表")
for _, row in df.iterrows():
    with st.expander(f"{row['title']} ({row['source']})"):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**发布时间:** {row['published_at']}")
            if row['status'] == 'analyzed':
                st.write(f"**AI 摘要:** {row['ai_summary']}")
                st.write(f"**分类:** {row['category']} | **风险:** {row['risk_level']} | **地点:** {row['city']}, {row['country']}")
            else:
                st.write(f"**原始摘要:** {row['raw_summary']}")
            st.write(f"[查看原文]({row['url']})")
        
        with c2:
            if row['status'] == 'analyzed':
                if st.button("✨ 生成社媒文案", key=f"btn_{row['id']}"):
                    content = f"Title: {row['title']}\nSummary: {row['ai_summary']}\nSource: {row['source']}"
                    social_content = social_writer.generate_social_content(
                        title=row["title"],
                        ai_summary=row["ai_summary"],
                        source=row["source"]
                    )
                    if social_content:
                        st.session_state[f"social_{row['id']}"] = social_content
            
            if f"social_{row['id']}" in st.session_state:
                social = st.session_state[f"social_{row['id']}"]
                st.text_area("微博", social.get('weibo', ''), height=100)
                st.text_area("小红书", social.get('xiaohongshu', ''), height=100)
                st.text_area("短视频口播", social.get('video_script', ''), height=100)
                st.caption("内容仅供信息整理，不构成投资建议")
