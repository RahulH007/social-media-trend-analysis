"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  STREAM_PROCESSOR.PY — Apache Spark Structured Streaming Consumer          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Reads JSON messages from the Kafka "social_stream" topic, applies:        ║
║    1. Schema parsing (timestamp, text, user_id, location, hashtags)        ║
║    2. Sentiment analysis via PySpark UDFs (VADER / TextBlob)               ║
║    3. Keyword extraction                                                   ║
║    4. Windowed aggregation (5-min tumbling window for trends)              ║
║    5. Writes enriched results to CSV in the output/ directory              ║
║                                                                            ║
║  The dashboard (Streamlit) reads those CSVs for live visualization.        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    FloatType,
    StringType,
    StructField,
    StructType,
)

sys.path.insert(0, ".")
from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    OUTPUT_DIR,
    PROCESSED_POSTS_CSV,
    SENTIMENT_SUMMARY_CSV,
    SPARK_APP_NAME,
    SPARK_BATCH_INTERVAL_SEC,
    SPARK_MASTER,
    SPARK_WATERMARK_DELAY,
    SPARK_WINDOW_DURATION,
    SPARK_SLIDE_DURATION,
    TRENDING_KEYWORDS_CSV,
    GEO_SENTIMENT_CSV,
    SENTIMENT_ENGINE,
)
from nlp_layer.sentiment import SentimentAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SparkProcessor")


# ═══════════════════════════════════════════════════════════════════════
#  JSON schema for incoming Kafka messages
# ═══════════════════════════════════════════════════════════════════════
POST_SCHEMA = StructType([
    StructField("post_id",   StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("user_id",   StringType(), True),
    StructField("text",      StringType(), True),
    StructField("hashtags",  ArrayType(StringType()), True),
    StructField("location",  StructType([
        StructField("city", StringType(), True),
        StructField("lat",  DoubleType(), True),
        StructField("lon",  DoubleType(), True),
    ]), True),
    StructField("platform",  StringType(), True),
])


class SparkStreamProcessor:
    """
    End-to-end Spark Structured Streaming pipeline:
      Kafka → parse → enrich (sentiment + keywords) → aggregate → CSV sink
    """

    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # ── Build Spark session ─────────────────────────────────────────
        self.spark = (
            SparkSession.builder
            .appName(SPARK_APP_NAME)
            .master(SPARK_MASTER)
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints")
            .config("spark.jars.packages",
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1")
            .getOrCreate()
        )
        self.spark.sparkContext.setLogLevel("WARN")

        # ── Register UDFs ───────────────────────────────────────────────
        self._register_udfs()

        logger.info("✅  Spark session created (%s)", SPARK_MASTER)

    # ─────────────────────────────────────────────────────────────────────
    #  UDF Registration
    # ─────────────────────────────────────────────────────────────────────
    def _register_udfs(self):
        """Register sentiment & keyword UDFs for use in DataFrames."""
        analyzer = SentimentAnalyzer(engine=SENTIMENT_ENGINE)

        # Sentiment label UDF
        @F.udf(StringType())
        def sentiment_label_udf(text):
            if text is None:
                return "neutral"
            result = analyzer.analyze(text)
            return result["sentiment_label"]

        # Sentiment score UDF
        @F.udf(FloatType())
        def sentiment_score_udf(text):
            if text is None:
                return 0.0
            result = analyzer.analyze(text)
            return float(result["sentiment_score"])

        # Keyword extraction UDF
        @F.udf(ArrayType(StringType()))
        def keywords_udf(text):
            if text is None:
                return []
            return analyzer.extract_keywords(text, top_n=5)

        self.sentiment_label_udf = sentiment_label_udf
        self.sentiment_score_udf = sentiment_score_udf
        self.keywords_udf = keywords_udf

    # ─────────────────────────────────────────────────────────────────────
    #  Main pipeline
    # ─────────────────────────────────────────────────────────────────────
    def start(self):
        """Build and start all streaming queries."""

        # ── 1. Read from Kafka ──────────────────────────────────────────
        raw_stream = (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
            .option("subscribe", KAFKA_TOPIC)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .load()
        )

        # ── 2. Parse JSON values ───────────────────────────────────────
        parsed = (
            raw_stream
            .selectExpr("CAST(value AS STRING) as json_str")
            .select(F.from_json(F.col("json_str"), POST_SCHEMA).alias("data"))
            .select("data.*")
            .withColumn("event_time", F.to_timestamp("timestamp"))
        )

        # ── 3. Enrich with sentiment + keywords ────────────────────────
        enriched = (
            parsed
            .withColumn("sentiment_label", self.sentiment_label_udf(F.col("text")))
            .withColumn("sentiment_score", self.sentiment_score_udf(F.col("text")))
            .withColumn("keywords",        self.keywords_udf(F.col("text")))
            .withColumn("city",            F.col("location.city"))
            .withColumn("lat",             F.col("location.lat"))
            .withColumn("lon",             F.col("location.lon"))
        )

        # ── 4a. QUERY: Write enriched posts to CSV ─────────────────────
        posts_query = (
            enriched
            .select(
                "post_id", "event_time", "user_id", "text", "platform",
                "sentiment_label", "sentiment_score", "city", "lat", "lon",
                F.concat_ws(",", "hashtags").alias("hashtags_str"),
                F.concat_ws(",", "keywords").alias("keywords_str"),
            )
            .writeStream
            .outputMode("append")
            .format("csv")
            .option("path", PROCESSED_POSTS_CSV)
            .option("checkpointLocation", "/tmp/spark-chk-posts")
            .option("header", "true")
            .trigger(processingTime=f"{SPARK_BATCH_INTERVAL_SEC} seconds")
            .start()
        )
        logger.info("📝  Posts stream → %s", PROCESSED_POSTS_CSV)

        # ── 4b. QUERY: Windowed sentiment summary ──────────────────────
        sentiment_agg = (
            enriched
            .withWatermark("event_time", SPARK_WATERMARK_DELAY)
            .groupBy(
                F.window("event_time", SPARK_WINDOW_DURATION, SPARK_SLIDE_DURATION),
                "sentiment_label",
            )
            .agg(
                F.count("*").alias("count"),
                F.avg("sentiment_score").alias("avg_score"),
            )
            .select(
                F.col("window.start").alias("window_start"),
                F.col("window.end").alias("window_end"),
                "sentiment_label",
                "count",
                "avg_score",
            )
        )

        sentiment_query = (
            sentiment_agg
            .writeStream
            .outputMode("update")
            .format("console")                    # also prints to console
            .trigger(processingTime=f"{SPARK_BATCH_INTERVAL_SEC} seconds")
            .option("checkpointLocation", "/tmp/spark-chk-sentiment")
            .start()
        )
        logger.info("📊  Sentiment aggregation stream started")

        # ── 4c. QUERY: Trending keywords (explode + window) ────────────
        trending = (
            enriched
            .withWatermark("event_time", SPARK_WATERMARK_DELAY)
            .select("event_time", F.explode("keywords").alias("keyword"))
            .groupBy(
                F.window("event_time", SPARK_WINDOW_DURATION, SPARK_SLIDE_DURATION),
                "keyword",
            )
            .count()
            .orderBy(F.desc("count"))
        )

        trending_query = (
            trending
            .writeStream
            .outputMode("complete")
            .format("console")
            .trigger(processingTime=f"{SPARK_BATCH_INTERVAL_SEC} seconds")
            .option("checkpointLocation", "/tmp/spark-chk-trending")
            .option("truncate", "false")
            .start()
        )
        logger.info("🔥  Trending keywords stream started")

        # ── Wait for all queries ────────────────────────────────────────
        logger.info("🚀  All streams running. Ctrl+C to stop.")
        self.spark.streams.awaitAnyTermination()

    def stop(self):
        """Gracefully stop the Spark session."""
        self.spark.stop()
        logger.info("🔒  Spark session stopped.")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    processor = SparkStreamProcessor()
    try:
        processor.start()
    except KeyboardInterrupt:
        logger.info("\n⛔  Shutting down …")
        processor.stop()
