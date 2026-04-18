"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  APP.PY — Streamlit Real-Time Dashboard                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Reads the CSV files produced by the pipeline and renders:                 ║
║    • KPI cards (total posts, sentiment breakdown)                          ║
║    • Sentiment distribution (pie + bar charts)                             ║
║    • Top trending keywords (horizontal bar chart)                          ║
║    • Time-series sentiment trend                                           ║
║    • Word cloud                                                            ║
║    • Geo-based sentiment map                                               ║
║    • Keyword spike alerts                                                  ║
║    • Raw data explorer table                                               ║
║                                                                            ║
║  Auto-refreshes every few seconds to simulate real-time updates.           ║
║                                                                            ║
║  Usage:                                                                    ║
║      streamlit run dashboard/app.py                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
from collections import Counter
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Project imports ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    ALERTS_CSV,
    DASHBOARD_MAX_ROWS,
    DASHBOARD_REFRESH_SEC,
    GEO_SENTIMENT_CSV,
    PROCESSED_POSTS_CSV,
    SENTIMENT_SUMMARY_CSV,
    TRENDING_KEYWORDS_CSV,
    WORDCLOUD_MAX_WORDS,
)


# ════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Social Media Trend Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
    }
    /* KPI card styling */
    .kpi-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 4px 0;
    }
    .kpi-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        opacity: 0.7;
    }
    /* Alert styling */
    .alert-box {
        background: rgba(255, 75, 75, 0.12);
        border-left: 4px solid #ff4b4b;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    /* Section header */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        margin-top: 24px;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 2px solid rgba(255,255,255,0.15);
    }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
#  DATA LOADERS (cached with TTL for auto-refresh)
# ════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=DASHBOARD_REFRESH_SEC)
def load_posts():
    if not os.path.exists(PROCESSED_POSTS_CSV):
        return pd.DataFrame()
    try:
        df = pd.read_csv(PROCESSED_POSTS_CSV, nrows=DASHBOARD_MAX_ROWS)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=DASHBOARD_REFRESH_SEC)
def load_trending():
    if not os.path.exists(TRENDING_KEYWORDS_CSV):
        return pd.DataFrame()
    try:
        return pd.read_csv(TRENDING_KEYWORDS_CSV)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=DASHBOARD_REFRESH_SEC)
def load_sentiment_summary():
    if not os.path.exists(SENTIMENT_SUMMARY_CSV):
        return pd.DataFrame()
    try:
        return pd.read_csv(SENTIMENT_SUMMARY_CSV)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=DASHBOARD_REFRESH_SEC)
def load_geo():
    if not os.path.exists(GEO_SENTIMENT_CSV):
        return pd.DataFrame()
    try:
        return pd.read_csv(GEO_SENTIMENT_CSV)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=DASHBOARD_REFRESH_SEC)
def load_alerts():
    if not os.path.exists(ALERTS_CSV):
        return pd.DataFrame()
    try:
        return pd.read_csv(ALERTS_CSV)
    except Exception:
        return pd.DataFrame()


def generate_wordcloud_image(keywords_series):
    """Generate a word cloud PNG from a pandas Series of comma-separated keywords."""
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt

        all_words = []
        for kw_str in keywords_series.dropna():
            all_words.extend(str(kw_str).split(","))

        if not all_words:
            return None

        word_freq = Counter(all_words)
        wc = WordCloud(
            width=800,
            height=400,
            max_words=WORDCLOUD_MAX_WORDS,
            background_color=None,
            mode="RGBA",
            colormap="plasma",
            prefer_horizontal=0.7,
        ).generate_from_frequencies(word_freq)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        fig.patch.set_alpha(0.0)

        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight",
                    transparent=True, dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf
    except ImportError:
        return None


# ════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    auto_refresh = st.toggle("Auto-refresh", value=True)
    if auto_refresh:
        refresh_rate = st.slider("Refresh interval (sec)", 1, 15, DASHBOARD_REFRESH_SEC)
    else:
        refresh_rate = None
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()

    st.markdown("---")
    st.markdown("## 📖 About")
    st.markdown(
        "**Real-Time Social Media Trend Analyzer**\n\n"
        "Pipeline: `Simulator → Kafka → Spark → CSV → Dashboard`\n\n"
        "Built with Python, Kafka, Spark, VADER, and Streamlit."
    )
    st.markdown("---")
    st.markdown("### Pipeline Status")

    posts_df = load_posts()
    if posts_df.empty:
        st.error("No data yet. Run the pipeline first!")
        st.code("python run_standalone.py", language="bash")
        st.code("streamlit run dashboard/app.py", language="bash")
    else:
        st.success(f"✅ {len(posts_df)} posts loaded")


# ════════════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════════════
st.markdown(
    "<h1 style='text-align:center; font-size:2.4rem; margin-bottom:0;'>"
    "📊 Real-Time Social Media Trend Analyzer</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center; opacity:0.6; margin-top:0;'>"
    "Live sentiment · Trending topics · Geo insights · Spike alerts</p>",
    unsafe_allow_html=True,
)

if posts_df.empty:
    st.warning("⏳ Waiting for data … Run the pipeline to start streaming.")
    st.stop()


# ════════════════════════════════════════════════════════════════════════
#  KPI CARDS
# ════════════════════════════════════════════════════════════════════════
total = len(posts_df)
pos = int((posts_df["sentiment_label"] == "positive").sum())
neg = int((posts_df["sentiment_label"] == "negative").sum())
neu = int((posts_df["sentiment_label"] == "neutral").sum())
avg_score = posts_df["sentiment_score"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Posts", f"{total:,}")
c2.metric("Positive 😊", f"{pos:,}", f"{pos/total*100:.1f}%")
c3.metric("Negative 😠", f"{neg:,}", f"{neg/total*100:.1f}%")
c4.metric("Neutral 😐", f"{neu:,}", f"{neu/total*100:.1f}%")
c5.metric("Avg Score", f"{avg_score:+.3f}")


# ════════════════════════════════════════════════════════════════════════
#  ROW 1: SENTIMENT DISTRIBUTION + TRENDING KEYWORDS
# ════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Sentiment & Trending Analysis</div>',
            unsafe_allow_html=True)

col_pie, col_bar = st.columns(2)

# ── Pie Chart ───────────────────────────────────────────────────────────
with col_pie:
    color_map = {"positive": "#00d97e", "neutral": "#f5c542", "negative": "#ff4b4b"}
    fig_pie = px.pie(
        names=["Positive", "Neutral", "Negative"],
        values=[pos, neu, neg],
        color=["positive", "neutral", "negative"],
        color_discrete_map={
            "positive": "#00d97e", "neutral": "#f5c542", "negative": "#ff4b4b"
        },
        title="Sentiment Distribution",
        hole=0.45,
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=50, b=30, l=20, r=20),
    )
    fig_pie.update_traces(
        textinfo="percent+label",
        textfont_size=13,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Trending Keywords Bar ───────────────────────────────────────────────
with col_bar:
    trending_df = load_trending()
    if not trending_df.empty:
        top20 = trending_df.head(20).sort_values("count", ascending=True)
        fig_bar = px.bar(
            top20, x="count", y="keyword",
            orientation="h",
            title="Top 20 Trending Keywords",
            color="count",
            color_continuous_scale="Plasma",
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            yaxis_title="",
            xaxis_title="Frequency",
            coloraxis_showscale=False,
            margin=dict(t=50, b=30, l=20, r=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No trending keywords yet.")


# ════════════════════════════════════════════════════════════════════════
#  ROW 2: TIME-SERIES + WORD CLOUD
# ════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Temporal Trends & Word Cloud</div>',
            unsafe_allow_html=True)

col_ts, col_wc = st.columns(2)

# ── Time-series sentiment ──────────────────────────────────────────────
with col_ts:
    if "timestamp" in posts_df.columns and posts_df["timestamp"].notna().any():
        ts_df = posts_df.dropna(subset=["timestamp"]).copy()
        ts_df["minute"] = ts_df["timestamp"].dt.floor("min")

        ts_agg = (
            ts_df.groupby(["minute", "sentiment_label"])
            .size()
            .reset_index(name="count")
        )

        fig_ts = px.area(
            ts_agg, x="minute", y="count", color="sentiment_label",
            title="Sentiment Over Time (per minute)",
            color_discrete_map={
                "positive": "#00d97e", "neutral": "#f5c542", "negative": "#ff4b4b"
            },
        )
        fig_ts.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis_title="",
            yaxis_title="Post Count",
            legend_title="Sentiment",
            margin=dict(t=50, b=30, l=20, r=20),
        )
        st.plotly_chart(fig_ts, use_container_width=True)
    else:
        st.info("Waiting for timestamped data …")

# ── Word Cloud ─────────────────────────────────────────────────────────
with col_wc:
    st.markdown("#### ☁️ Keyword Word Cloud")
    if "keywords" in posts_df.columns:
        wc_buf = generate_wordcloud_image(posts_df["keywords"])
        if wc_buf:
            st.image(wc_buf, use_container_width=True)
        else:
            st.info("Install `wordcloud` for this feature: `pip install wordcloud`")
    else:
        st.info("No keyword data available.")


# ════════════════════════════════════════════════════════════════════════
#  ROW 3: HASHTAG ANALYSIS + GEO MAP
# ════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Hashtags & Geographic Insights</div>',
            unsafe_allow_html=True)

col_ht, col_geo = st.columns(2)

# ── Hashtag bar chart ──────────────────────────────────────────────────
with col_ht:
    if "hashtags" in posts_df.columns:
        all_tags = []
        for tag_str in posts_df["hashtags"].dropna():
            all_tags.extend(str(tag_str).split(","))
        tag_counts = Counter([t.strip() for t in all_tags if t.strip()])
        if tag_counts:
            ht_df = pd.DataFrame(
                tag_counts.most_common(15), columns=["hashtag", "count"]
            ).sort_values("count", ascending=True)
            fig_ht = px.bar(
                ht_df, x="count", y="hashtag", orientation="h",
                title="Top 15 Hashtags",
                color="count", color_continuous_scale="Viridis",
            )
            fig_ht.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                yaxis_title="", xaxis_title="Frequency",
                coloraxis_showscale=False,
                margin=dict(t=50, b=30, l=20, r=20),
            )
            st.plotly_chart(fig_ht, use_container_width=True)
        else:
            st.info("No hashtag data yet.")
    else:
        st.info("No hashtag column found.")

# ── Geo sentiment map ──────────────────────────────────────────────────
with col_geo:
    geo_df = load_geo()
    if not geo_df.empty and "lat" in geo_df.columns:
        fig_map = px.scatter_geo(
            geo_df,
            lat="lat", lon="lon",
            size="post_count",
            color="avg_score",
            hover_name="city",
            color_continuous_scale="RdYlGn",
            range_color=[-0.5, 0.5],
            title="Sentiment by City",
            projection="natural earth",
            size_max=30,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            geo=dict(
                bgcolor="rgba(0,0,0,0)",
                showframe=False,
                showcoastlines=True,
                coastlinecolor="rgba(255,255,255,0.2)",
                landcolor="rgba(30,30,60,0.6)",
                showland=True,
            ),
            font_color="white",
            margin=dict(t=50, b=10, l=0, r=0),
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No geographic data available yet.")


# ════════════════════════════════════════════════════════════════════════
#  ROW 4: ALERTS + PLATFORM BREAKDOWN
# ════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Alerts & Platform Analysis</div>',
            unsafe_allow_html=True)

col_alert, col_plat = st.columns(2)

# ── Spike Alerts ───────────────────────────────────────────────────────
with col_alert:
    st.markdown("#### 🚨 Keyword Spike Alerts")
    alerts_df = load_alerts()
    if not alerts_df.empty:
        for _, row in alerts_df.tail(10).iterrows():
            st.markdown(
                f'<div class="alert-box">'
                f'<b>{row.get("keyword", "?")}</b> spiked to '
                f'<b>{row.get("count", "?")}</b> hits '
                f'(threshold: {row.get("threshold", "?")})'
                f'<br><small>{row.get("timestamp", "")}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.success("No spikes detected — all keywords within normal range.")

# ── Platform Breakdown ─────────────────────────────────────────────────
with col_plat:
    if "platform" in posts_df.columns:
        plat_counts = posts_df["platform"].value_counts().reset_index()
        plat_counts.columns = ["platform", "count"]
        fig_plat = px.bar(
            plat_counts, x="platform", y="count",
            title="Posts by Platform",
            color="platform",
            color_discrete_sequence=["#636EFA", "#EF553B", "#00CC96"],
        )
        fig_plat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
            margin=dict(t=50, b=30, l=20, r=20),
        )
        st.plotly_chart(fig_plat, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
#  RAW DATA EXPLORER
# ════════════════════════════════════════════════════════════════════════
with st.expander("📋 Raw Data Explorer", expanded=False):
    display_cols = [
        c for c in ["timestamp", "text", "sentiment_label",
                     "sentiment_score", "city", "platform", "hashtags"]
        if c in posts_df.columns
    ]
    st.dataframe(
        posts_df[display_cols].tail(100),
        use_container_width=True,
        height=400,
    )


# ════════════════════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ════════════════════════════════════════════════════════════════════════
if auto_refresh and refresh_rate:
    import time
    time.sleep(refresh_rate)
    st.rerun()
