"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  PRODUCER.PY — Kafka Producer for Social Media Stream                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Reads posts from the SocialMediaSimulator and publishes them as JSON      ║
║  messages to a Kafka topic.                                                ║
║                                                                            ║
║  Features:                                                                 ║
║    • JSON serialization with UTF-8 encoding                                ║
║    • Configurable throughput (posts/sec)                                    ║
║    • Delivery callbacks with error logging                                 ║
║    • Graceful shutdown on Ctrl+C                                           ║
║    • Retry logic with fault-tolerance                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
import time

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

# ── Add project root to path so we can import sibling packages ──────────
sys.path.insert(0, ".")
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, GENERATOR_RATE_PER_SEC
from data_generator.simulator import SocialMediaSimulator

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("KafkaProducer")


class KafkaPostProducer:
    """
    Wraps kafka-python's KafkaProducer with:
      • automatic JSON serialization
      • delivery success / error callbacks
      • retry on broker unavailability
    """

    MAX_RETRIES = 5
    RETRY_BACKOFF_SEC = 3

    def __init__(self, servers: str = KAFKA_BOOTSTRAP_SERVERS, topic: str = KAFKA_TOPIC):
        self.topic = topic
        self.servers = servers
        self.producer = None
        self._connect()

    # ── Connection with retry ───────────────────────────────────────────

    def _connect(self):
        """Attempt to connect to Kafka brokers with exponential back-off."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks="all",                   # wait for all replicas
                    retries=3,                    # per-message retries
                    max_block_ms=5000,
                )
                logger.info(
                    "✅  Connected to Kafka broker(s): %s", self.servers
                )
                return
            except NoBrokersAvailable:
                wait = self.RETRY_BACKOFF_SEC * attempt
                logger.warning(
                    "⏳  Broker unavailable (attempt %d/%d). Retrying in %ds …",
                    attempt, self.MAX_RETRIES, wait,
                )
                time.sleep(wait)

        logger.error("❌  Could not connect after %d attempts. Exiting.", self.MAX_RETRIES)
        sys.exit(1)

    # ── Publishing ──────────────────────────────────────────────────────

    def send(self, post: dict):
        """
        Publish a single post to the Kafka topic.
        Uses post_id as the message key for partitioning.
        """
        try:
            future = self.producer.send(
                self.topic,
                key=post.get("post_id", ""),
                value=post,
            )
            future.add_callback(self._on_success)
            future.add_errback(self._on_error)
        except KafkaError as exc:
            logger.error("🔴  Kafka send error: %s", exc)

    def flush(self):
        """Block until all buffered messages are delivered."""
        if self.producer:
            self.producer.flush()

    def close(self):
        """Flush remaining messages and close the producer."""
        self.flush()
        if self.producer:
            self.producer.close()
            logger.info("🔒  Producer closed.")

    # ── Callbacks ───────────────────────────────────────────────────────

    @staticmethod
    def _on_success(metadata):
        logger.debug(
            "📨  Delivered → topic=%s  partition=%d  offset=%d",
            metadata.topic, metadata.partition, metadata.offset,
        )

    @staticmethod
    def _on_error(exc):
        logger.error("🔴  Delivery failed: %s", exc)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN — run the producer as a standalone script
# ═══════════════════════════════════════════════════════════════════════
def main():
    """
    Entrypoint: creates a simulator + producer and streams posts
    into Kafka indefinitely until Ctrl+C.
    """
    simulator = SocialMediaSimulator(rate=GENERATOR_RATE_PER_SEC)
    producer  = KafkaPostProducer()
    count     = 0

    logger.info(
        "🚀  Streaming posts to topic '%s' at ~%d msgs/sec  (Ctrl+C to stop)",
        KAFKA_TOPIC, GENERATOR_RATE_PER_SEC,
    )

    try:
        for post in simulator.stream():
            producer.send(post)
            count += 1
            if count % 100 == 0:
                logger.info("📊  Published %d messages so far", count)
    except KeyboardInterrupt:
        logger.info("\n⛔  Interrupted — flushing remaining messages …")
    finally:
        producer.close()
        logger.info("✅  Total messages published: %d", count)


if __name__ == "__main__":
    main()
