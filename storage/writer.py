"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  WRITER.PY — Storage Layer                                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Provides a simple, thread-safe writer that:                               ║
║    • Appends enriched posts to a CSV file                                  ║
║    • Maintains rolling aggregation files (sentiment summary, trending)     ║
║    • Detects keyword spikes and logs alerts                                ║
║    • Supports both the Spark pipeline and the standalone demo pipeline     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import logging
import os
import threading
from collections import Counter, deque
from datetime import datetime, timezone

import pandas as pd

import sys
sys.path.insert(0, ".")
from config import (
    ALERT_ROLLING_WINDOW,
    ALERT_SPIKE_THRESHOLD,
    ALERTS_CSV,
    GEO_SENTIMENT_CSV,
    OUTPUT_DIR,
    PROCESSED_POSTS_CSV,
    SENTIMENT_SUMMARY_CSV,
    TRENDING_KEYWORDS_CSV,
)

logger = logging.getLogger("StorageWriter")


class StorageWriter:
    """
    Accumulates enriched post data and periodically flushes
    summary files that the Streamlit dashboard reads.
    """

    POST_COLUMNS = [
        "post_id", "timestamp", "user_id", "text", "platform",
        "sentiment_label", "sentiment_score",
        "city", "lat", "lon",
        "hashtags", "keywords",
    ]

    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._lock = threading.Lock()

        # In-memory buffers
        self._posts_buffer = []
        self._keyword_history = deque(maxlen=5000)   # sliding window for spike detection
        self._keyword_counter = Counter()
        self._alerts = []

        # Initialize CSV files with headers
        self._init_csv(PROCESSED_POSTS_CSV, self.POST_COLUMNS)

    # ─────────────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────────────
    def write_post(self, post: dict, analysis: dict):
        """
        Accept an enriched post (original post + NLP results)
        and buffer it for writing.
        """
        location = post.get("location") or {}
        row = {
            "post_id":         post.get("post_id", ""),
            "timestamp":       post.get("timestamp", ""),
            "user_id":         post.get("user_id", ""),
            "text":            post.get("text", ""),
            "platform":        post.get("platform", ""),
            "sentiment_label": analysis.get("sentiment_label", "neutral"),
            "sentiment_score": analysis.get("sentiment_score", 0.0),
            "city":            location.get("city", ""),
            "lat":             location.get("lat", ""),
            "lon":             location.get("lon", ""),
            "hashtags":        ",".join(analysis.get("hashtags", [])),
            "keywords":        ",".join(analysis.get("keywords", [])),
        }

        with self._lock:
            self._posts_buffer.append(row)

            # Track keywords for spike detection
            for kw in analysis.get("keywords", []):
                self._keyword_counter[kw] += 1
                self._keyword_history.append(kw)

    def flush(self):
        """
        Write buffered posts to disk and update summary files.
        Called periodically by the pipeline.
        """
        with self._lock:
            if not self._posts_buffer:
                return

            # 1. Append posts to CSV
            self._append_csv(PROCESSED_POSTS_CSV, self.POST_COLUMNS, self._posts_buffer)

            # 2. Rebuild summary files from the full CSV
            self._update_summaries()

            # 3. Check for keyword spikes
            self._detect_spikes()

            count = len(self._posts_buffer)
            self._posts_buffer.clear()

        logger.info("💾  Flushed %d posts to disk", count)

    # ─────────────────────────────────────────────────────────────────────
    #  Summary file builders
    # ─────────────────────────────────────────────────────────────────────
    def _update_summaries(self):
        """Rebuild trending-keyword and sentiment-summary CSVs."""
        try:
            df = pd.read_csv(PROCESSED_POSTS_CSV)
        except Exception:
            return

        if df.empty:
            return

        # ── Sentiment summary ───────────────────────────────────────────
        sentiment_counts = (
            df.groupby("sentiment_label")
            .agg(count=("sentiment_label", "size"),
                 avg_score=("sentiment_score", "mean"))
            .reset_index()
        )
        sentiment_counts.to_csv(SENTIMENT_SUMMARY_CSV, index=False)

        # ── Trending keywords ───────────────────────────────────────────
        all_keywords = []
        for kw_str in df["keywords"].dropna():
            all_keywords.extend(kw_str.split(","))

        kw_counts = Counter(all_keywords).most_common(30)
        kw_df = pd.DataFrame(kw_counts, columns=["keyword", "count"])
        kw_df.to_csv(TRENDING_KEYWORDS_CSV, index=False)

        # ── Geo sentiment ───────────────────────────────────────────────
        geo_df = df.dropna(subset=["city"])
        if not geo_df.empty:
            geo_agg = (
                geo_df.groupby("city")
                .agg(
                    avg_score=("sentiment_score", "mean"),
                    post_count=("post_id", "count"),
                    lat=("lat", "first"),
                    lon=("lon", "first"),
                )
                .reset_index()
            )
            geo_agg.to_csv(GEO_SENTIMENT_CSV, index=False)

    # ─────────────────────────────────────────────────────────────────────
    #  Spike detection / alerting
    # ─────────────────────────────────────────────────────────────────────
    def _detect_spikes(self):
        """Flag any keyword whose recent count exceeds THRESHOLD × average."""
        if len(self._keyword_history) < ALERT_ROLLING_WINDOW * 2:
            return   # not enough data yet

        recent = list(self._keyword_history)[-ALERT_ROLLING_WINDOW:]
        recent_counts = Counter(recent)
        avg_per_word = len(recent) / max(len(recent_counts), 1)

        for word, cnt in recent_counts.items():
            if cnt > avg_per_word * ALERT_SPIKE_THRESHOLD:
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "keyword":   word,
                    "count":     cnt,
                    "threshold": round(avg_per_word * ALERT_SPIKE_THRESHOLD, 1),
                }
                self._alerts.append(alert)
                logger.warning("🚨  SPIKE DETECTED: '%s' (%d hits)", word, cnt)

        # Persist alerts
        if self._alerts:
            alert_df = pd.DataFrame(self._alerts)
            alert_df.to_csv(ALERTS_CSV, index=False)

    # ─────────────────────────────────────────────────────────────────────
    #  CSV helpers
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def _init_csv(path: str, columns: list):
        """Write header row if the file doesn't exist yet."""
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()

    @staticmethod
    def _append_csv(path: str, columns: list, rows: list):
        """Append rows to an existing CSV."""
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writerows(rows)
