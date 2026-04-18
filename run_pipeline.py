"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RUN_PIPELINE.PY — Full Pipeline (Kafka + Spark)                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Launches the Kafka Producer and Spark Stream Processor as sub-processes.  ║
║                                                                            ║
║  Prerequisites:                                                            ║
║    1. Kafka + Zookeeper running (see docker-compose.yml)                   ║
║    2. Kafka topic created (auto-creates if server allows)                  ║
║    3. pip install -r requirements.txt                                      ║
║                                                                            ║
║  Usage:                                                                    ║
║      python run_pipeline.py                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Pipeline")


def main():
    logger.info("=" * 65)
    logger.info("  FULL PIPELINE — Kafka Producer + Spark Consumer")
    logger.info("=" * 65)

    processes = []

    try:
        # ── 1. Start Kafka Producer ─────────────────────────────────────
        logger.info("🚀  Starting Kafka Producer …")
        producer_proc = subprocess.Popen(
            [sys.executable, "kafka_layer/producer.py"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(("Kafka Producer", producer_proc))
        time.sleep(2)

        # ── 2. Start Spark Consumer ─────────────────────────────────────
        logger.info("🚀  Starting Spark Stream Processor …")
        spark_proc = subprocess.Popen(
            [sys.executable, "spark_layer/stream_processor.py"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        processes.append(("Spark Consumer", spark_proc))

        # ── Wait ────────────────────────────────────────────────────────
        logger.info("✅  Pipeline running. Press Ctrl+C to stop all.")
        for name, proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        logger.info("\n⛔  Shutting down all processes …")
        for name, proc in processes:
            proc.terminate()
            logger.info("    Terminated %s (pid=%d)", name, proc.pid)

        # Give them a moment, then force-kill
        time.sleep(2)
        for name, proc in processes:
            if proc.poll() is None:
                proc.kill()

        logger.info("✅  All processes stopped.")


if __name__ == "__main__":
    main()
