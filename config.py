"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CONFIG.PY — Central Configuration for Social Media Trend Analyzer         ║
║  All tunable parameters live here. Adjust for your environment.            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os

# ─── Kafka Settings ──────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_SERVERS", "localhost:9092")
KAFKA_TOPIC             = "social_stream"
KAFKA_PROCESSED_TOPIC   = "processed_stream"
KAFKA_GROUP_ID          = "trend-analyzer-group"

# ─── Spark Settings ──────────────────────────────────────────────────────────
SPARK_APP_NAME              = "SocialMediaTrendAnalyzer"
SPARK_MASTER                = "local[*]"
SPARK_BATCH_INTERVAL_SEC    = 5
SPARK_WATERMARK_DELAY       = "10 seconds"
SPARK_WINDOW_DURATION       = "5 minutes"
SPARK_SLIDE_DURATION        = "1 minute"

# ─── Data Generator ─────────────────────────────────────────────────────────
GENERATOR_RATE_PER_SEC      = 20
GENERATOR_BURST_PROBABILITY = 0.05
TOTAL_SAMPLE_POSTS          = 500

# ─── NLP / Sentiment ────────────────────────────────────────────────────────
SENTIMENT_ENGINE = "vader"            # "textblob" | "vader"

# ─── Storage ────────────────────────────────────────────────────────────────
OUTPUT_DIR               = "output"
PROCESSED_POSTS_CSV      = os.path.join(OUTPUT_DIR, "processed_posts.csv")
TRENDING_KEYWORDS_CSV    = os.path.join(OUTPUT_DIR, "trending_keywords.csv")
SENTIMENT_SUMMARY_CSV    = os.path.join(OUTPUT_DIR, "sentiment_summary.csv")
GEO_SENTIMENT_CSV        = os.path.join(OUTPUT_DIR, "geo_sentiment.csv")
ALERTS_CSV               = os.path.join(OUTPUT_DIR, "alerts.csv")

# ─── Dashboard ──────────────────────────────────────────────────────────────
DASHBOARD_REFRESH_SEC    = 3
DASHBOARD_MAX_ROWS       = 1000
WORDCLOUD_MAX_WORDS      = 80

# ─── Alerting ───────────────────────────────────────────────────────────────
ALERT_SPIKE_THRESHOLD    = 3.0
ALERT_ROLLING_WINDOW     = 10

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE  = "pipeline.log"
