# 📊 Real-Time Social Media Trend Analyzer

> A complete Big Data pipeline that ingests social media posts, processes them in real time with Apache Kafka and Apache Spark, performs AI-based sentiment analysis, and visualizes insights on a live Streamlit dashboard.

---

## 🎯 Project Overview

This project demonstrates a production-style real-time analytics pipeline suitable for a **Big Data Analytics** course assignment. It covers all layers of a modern streaming architecture:

| Layer | Technology | Role |
|-------|-----------|------|
| **Data Source** | Python Simulator | Generates realistic social media posts at 20+ msgs/sec |
| **Message Broker** | Apache Kafka | Decouples ingestion from processing; enables replay |
| **Stream Processing** | Apache Spark Structured Streaming | Real-time transformation, aggregation, windowing |
| **NLP Engine** | VADER (NLTK) / TextBlob | Sentiment scoring + keyword extraction |
| **Storage** | CSV (Pandas) | Lightweight, human-readable persistence |
| **Visualization** | Streamlit + Plotly | Auto-refreshing interactive dashboard |

---

## 🚀 Quick Start (2 Minutes)

No Kafka or Spark installation needed for the standalone demo:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate sample data (500 posts, instant)
python sample_data/generate_sample.py

# 3. Start the live pipeline (Terminal 1)
python run_standalone.py

# 4. Launch the dashboard (Terminal 2)
streamlit run dashboard/app.py
```

Open `http://localhost:8501` — the dashboard auto-refreshes with live data.

---

## 🏗️ System Architecture

```
┌──────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌───────────┐    ┌───────────┐
│   Simulator   │───▶│    Kafka     │───▶│   Spark Streaming  │───▶│  CSV/     │───▶│ Streamlit │
│  (20 msg/s)  │    │  (Topic:     │    │  • Sentiment UDFs  │    │  Parquet  │    │ Dashboard │
│              │    │  social_     │    │  • Keyword Extract  │    │           │    │           │
│  Burst events│    │  stream)     │    │  • Window Agg      │    │  Alerts   │    │  Charts   │
│  Geo data    │    │  Partitions:3│    │  • Geo grouping    │    │  Trends   │    │  Maps     │
└──────────────┘    └──────────────┘    └───────────────────┘    └───────────┘    └───────────┘
```

> **Standalone mode** skips Kafka + Spark and pipes data directly: Simulator → NLP → CSV → Dashboard

See [`docs/architecture.md`](docs/architecture.md) for detailed diagrams of every component.

---

## 📂 Project Structure

```
social-media-trend-analyzer/
│
├── config.py                      # All tunable parameters (one place)
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Kafka + Zookeeper containers
├── run_standalone.py              # Demo mode (no Kafka/Spark)
├── run_pipeline.py                # Full mode (Kafka + Spark)
│
├── data_generator/
│   ├── __init__.py
│   └── simulator.py               # Realistic post generator with bursts
│
├── kafka_layer/
│   ├── __init__.py
│   └── producer.py                # Kafka producer with retry logic
│
├── spark_layer/
│   ├── __init__.py
│   └── stream_processor.py        # Spark Structured Streaming consumer
│
├── nlp_layer/
│   ├── __init__.py
│   └── sentiment.py               # VADER/TextBlob sentiment + keywords
│
├── storage/
│   ├── __init__.py
│   └── writer.py                  # CSV writer + spike detection
│
├── dashboard/
│   └── app.py                     # Streamlit dashboard (10 visualizations)
│
├── sample_data/
│   └── generate_sample.py         # Pre-generate sample dataset
│
├── docs/
│   ├── architecture.md            # Full architecture diagrams
│   └── setup_instructions.md      # Step-by-step setup guide
│
└── output/                        # Generated at runtime
    ├── processed_posts.csv
    ├── trending_keywords.csv
    ├── sentiment_summary.csv
    ├── geo_sentiment.csv
    └── alerts.csv
```

---

## ⚙️ Two Execution Modes

### Mode A: Standalone Demo (Recommended for Quick Testing)

```
Terminal 1:  python run_standalone.py         # Simulate → Analyze → CSV
Terminal 2:  streamlit run dashboard/app.py   # Live dashboard
```

**Requirements:** Python 3.9+ only.

### Mode B: Full Pipeline (Kafka + Spark)

```
Terminal 1:  docker-compose up -d                    # Start Kafka
Terminal 2:  python kafka_layer/producer.py           # Stream to Kafka
Terminal 3:  python spark_layer/stream_processor.py   # Spark consumer
Terminal 4:  streamlit run dashboard/app.py            # Dashboard
```

**Requirements:** Python 3.9+, Docker, Java 11/17.

---

## 📊 Dashboard Features

The Streamlit dashboard provides **10 interactive visualizations**:

| # | Visualization | Description |
|---|---------------|-------------|
| 1 | **KPI Cards** | Total posts, positive/negative/neutral counts, average score |
| 2 | **Sentiment Pie Chart** | Donut chart with percentage breakdown |
| 3 | **Trending Keywords** | Top 20 keywords (horizontal bar, Plasma colorscale) |
| 4 | **Time-Series Trend** | Stacked area chart — sentiment count per minute |
| 5 | **Word Cloud** | Visual word frequency map of extracted keywords |
| 6 | **Hashtag Analysis** | Top 15 hashtags ranked by frequency |
| 7 | **Geo Sentiment Map** | World map — bubble size = post count, color = avg sentiment |
| 8 | **Spike Alerts** | Real-time alerts when a keyword exceeds 3× rolling average |
| 9 | **Platform Breakdown** | Posts per platform (Twitter / Reddit / Mastodon) |
| 10 | **Raw Data Explorer** | Expandable table with full post details |

Auto-refreshes every 3 seconds (configurable via sidebar).

---

## 🧪 Bonus Features Implemented

| Feature | Status | Details |
|---------|--------|---------|
| Trending topics over time windows | ✅ | 5-minute tumbling window with 1-min slide |
| Geo-based sentiment analysis | ✅ | 15 cities, scatter map with avg sentiment color |
| Alert system for keyword spikes | ✅ | Rolling average comparison, alerts persisted to CSV |
| Word cloud generation | ✅ | Matplotlib + wordcloud library, Plasma colormap |
| Burst event simulation | ✅ | 5% chance of viral topic burst (15–50 posts) |
| Fault-tolerant Kafka producer | ✅ | Exponential backoff, delivery callbacks, retry=3 |
| Multiple NLP engines | ✅ | VADER (default) + TextBlob (configurable) |
| Platform diversity | ✅ | Twitter / Reddit / Mastodon simulation |

---

## 🔧 Configuration

All parameters are centralized in `config.py`:

```python
# Key settings you might want to change:
GENERATOR_RATE_PER_SEC  = 20        # Posts per second
SENTIMENT_ENGINE        = "vader"   # "vader" or "textblob"
DASHBOARD_REFRESH_SEC   = 3         # Dashboard auto-refresh interval
ALERT_SPIKE_THRESHOLD   = 3.0       # Spike = 3× rolling average
SPARK_WINDOW_DURATION   = "5 minutes"
```

---

## 📝 Sample Data Format

Each generated post follows this JSON schema:

```json
{
  "post_id":   "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-04-14T10:30:15.123456+00:00",
  "user_id":   "user_42567",
  "text":      "Absolutely loving the progress in machine learning! #AI is the future 🚀 #SpaceX",
  "hashtags":  ["#AI", "#SpaceX"],
  "location":  {"city": "Bengaluru, India", "lat": 12.9716, "lon": 77.5946},
  "platform":  "twitter"
}
```

After NLP enrichment, the CSV adds:
- `sentiment_label` — positive / negative / neutral
- `sentiment_score` — continuous float from -1.0 to +1.0
- `keywords` — comma-separated top-5 meaningful words

---

## 🧠 How Sentiment Analysis Works

The project uses **VADER** (Valence Aware Dictionary and sEntiment Reasoner) by default:

1. **Tokenization** — NLTK `word_tokenize` splits text into words
2. **Sentiment Scoring** — VADER returns a compound score from -1.0 to +1.0
   - Handles emojis (🚀 = positive), caps ("AMAZING" = intensifier), slang
3. **Classification** — Score mapped to label:
   - `score >= 0.05` → **positive**
   - `score <= -0.05` → **negative**
   - otherwise → **neutral**
4. **Keyword Extraction** — Stop-word filtered, frequency-ranked top-5
5. **Hashtag Extraction** — Regex `#\w+` pattern matching

---

## 📚 Technologies Used

- **Apache Kafka** — Distributed message streaming platform
- **Apache Spark** — Unified analytics engine for large-scale data processing
- **PySpark** — Python API for Apache Spark
- **VADER Sentiment** — Rule-based sentiment analysis tuned for social media
- **NLTK** — Natural Language Toolkit for tokenization and stop-words
- **TextBlob** — Simplified text processing (alternative engine)
- **Streamlit** — Python framework for data dashboards
- **Plotly** — Interactive charting library
- **Pandas** — Data manipulation and CSV I/O
- **Docker Compose** — Container orchestration for Kafka infrastructure
- **WordCloud** — Word frequency visualization

---

## 🤝 Contributing

This is an academic project. Feel free to extend it with:
- Real Twitter/Reddit API integration (replace the simulator)
- MongoDB or PostgreSQL storage backend
- Apache Flink as an alternative stream processor
- Transformer-based sentiment (HuggingFace `distilbert`)
- Kubernetes deployment manifests

---

## 📜 License

This project is for educational purposes. All code is provided as-is for learning Big Data concepts.
