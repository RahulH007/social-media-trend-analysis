"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RUN_STANDALONE.PY — Demo Pipeline (No Kafka / No Spark Required)          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  This script lets you demonstrate the entire flow on any machine without   ║
║  installing Kafka or Spark.  It uses:                                      ║
║    • SocialMediaSimulator  → generates posts                               ║
║    • SentimentAnalyzer     → enriches with NLP                             ║
║    • StorageWriter         → writes CSVs for the dashboard                 ║
║                                                                            ║
║  Run this in one terminal, then launch the Streamlit dashboard in another. ║
║                                                                            ║
║  Usage:                                                                    ║
║      python run_standalone.py                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import sys
import time

from config import GENERATOR_RATE_PER_SEC, SENTIMENT_ENGINE
from data_generator.simulator import SocialMediaSimulator
from nlp_layer.sentiment import SentimentAnalyzer
from storage.writer import StorageWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("StandalonePipeline")


def main():
    # ── Initialize components ───────────────────────────────────────────
    simulator = SocialMediaSimulator(rate=GENERATOR_RATE_PER_SEC)
    analyzer  = SentimentAnalyzer(engine=SENTIMENT_ENGINE)
    writer    = StorageWriter()

    logger.info("=" * 65)
    logger.info("  STANDALONE PIPELINE — No Kafka / No Spark")
    logger.info("  Generating %d posts/sec → Sentiment → CSV", GENERATOR_RATE_PER_SEC)
    logger.info("  Press Ctrl+C to stop")
    logger.info("=" * 65)

    count = 0
    flush_interval = 2          # flush to disk every 2 seconds
    last_flush = time.time()

    try:
        for post in simulator.stream():
            # ── NLP enrichment ──────────────────────────────────────────
            analysis = analyzer.analyze(post["text"])

            # ── Buffer the enriched post ────────────────────────────────
            writer.write_post(post, analysis)
            count += 1

            # ── Periodic flush ──────────────────────────────────────────
            now = time.time()
            if now - last_flush >= flush_interval:
                writer.flush()
                last_flush = now

            # ── Progress log ────────────────────────────────────────────
            if count % 50 == 0:
                logger.info(
                    "📊  Processed %d posts  |  latest sentiment: %s (%.2f)",
                    count,
                    analysis["sentiment_label"],
                    analysis["sentiment_score"],
                )

    except KeyboardInterrupt:
        logger.info("\n⛔  Interrupted — flushing remaining buffer …")
        writer.flush()
        logger.info("✅  Total posts processed: %d", count)
        logger.info("📁  Output files in: output/")
        logger.info("🖥️   Now run:  streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
