"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GENERATE_SAMPLE.PY — Pre-generate Sample Data for Dashboard Demo          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Creates:                                                                  ║
║    • sample_data/sample_posts.json   (raw simulated posts)                 ║
║    • output/processed_posts.csv      (enriched with sentiment)             ║
║    • output/trending_keywords.csv    (aggregated keyword counts)           ║
║    • output/sentiment_summary.csv    (label distribution)                  ║
║    • output/geo_sentiment.csv        (per-city sentiment averages)         ║
║                                                                            ║
║  Usage:                                                                    ║
║      python sample_data/generate_sample.py                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import TOTAL_SAMPLE_POSTS, SENTIMENT_ENGINE, OUTPUT_DIR
from data_generator.simulator import SocialMediaSimulator
from nlp_layer.sentiment import SentimentAnalyzer
from storage.writer import StorageWriter


def main():
    n = TOTAL_SAMPLE_POSTS
    print(f"🔄  Generating {n} sample posts …")

    simulator = SocialMediaSimulator(rate=100)
    analyzer  = SentimentAnalyzer(engine=SENTIMENT_ENGINE)
    writer    = StorageWriter()

    # ── Generate posts ──────────────────────────────────────────────────
    posts = simulator.generate_batch(n)

    # ── Save raw JSON ───────────────────────────────────────────────────
    sample_dir = os.path.dirname(__file__)
    json_path  = os.path.join(sample_dir, "sample_posts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"📄  Raw posts     → {json_path}")

    # ── Analyze + write to CSV ──────────────────────────────────────────
    for i, post in enumerate(posts):
        analysis = analyzer.analyze(post["text"])
        writer.write_post(post, analysis)
        if (i + 1) % 100 == 0:
            print(f"    … processed {i + 1}/{n}")

    writer.flush()

    print(f"📊  Processed CSV → {OUTPUT_DIR}/")
    print(f"✅  Done! You can now run: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
