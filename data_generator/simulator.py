"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SIMULATOR.PY — Realistic Social Media Post Generator                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Generates synthetic tweets/posts with realistic patterns:                 ║
║    • Trending hashtags that spike and decay                                ║
║    • Geo-distributed locations across 15 cities                            ║
║    • Mixed sentiment profiles (positive / neutral / negative)              ║
║    • Burst events simulating viral moments                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════════
#  TOPIC POOLS — each topic has a hashtag + related keyword vocabulary
# ═══════════════════════════════════════════════════════════════════════
TRENDING_TOPICS = [
    {
        "hashtag": "#AI",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "GPT", "LLM", "generative AI",
        ],
    },
    {
        "hashtag": "#ClimateChange",
        "keywords": [
            "global warming", "carbon emissions", "renewable energy",
            "solar power", "sustainability", "net zero", "green energy",
        ],
    },
    {
        "hashtag": "#Elections2026",
        "keywords": [
            "vote", "election", "democracy", "candidate",
            "campaign", "polling", "ballot",
        ],
    },
    {
        "hashtag": "#CryptoMarket",
        "keywords": [
            "bitcoin", "ethereum", "crypto", "blockchain",
            "NFT", "web3", "DeFi", "altcoin",
        ],
    },
    {
        "hashtag": "#WorldCup",
        "keywords": [
            "football", "soccer", "goal", "FIFA",
            "championship", "match", "penalty",
        ],
    },
    {
        "hashtag": "#TechLayoffs",
        "keywords": [
            "layoff", "fired", "unemployment", "hiring freeze",
            "recession", "job cuts", "downsizing",
        ],
    },
    {
        "hashtag": "#SpaceX",
        "keywords": [
            "rocket", "Mars", "launch", "Starship",
            "orbit", "space exploration", "NASA",
        ],
    },
    {
        "hashtag": "#MentalHealth",
        "keywords": [
            "anxiety", "therapy", "mindfulness", "wellness",
            "self-care", "burnout", "meditation",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
#  POST TEMPLATES — sentiment-biased sentence structures
# ═══════════════════════════════════════════════════════════════════════
POSITIVE_TEMPLATES = [
    "Absolutely loving the progress in {keyword}! {hashtag} is the future 🚀",
    "Great news about {keyword} today. {hashtag} gives me so much hope!",
    "Just read an amazing article on {keyword}. So excited! {hashtag}",
    "The innovation happening in {keyword} is incredible {hashtag} 🔥",
    "{keyword} is changing the world for the better. {hashtag}",
    "Can't believe how far {keyword} has come! Truly inspiring {hashtag}",
    "Really impressed by the latest {keyword} developments {hashtag} ✨",
    "Feeling optimistic about {keyword}. {hashtag} — the best is ahead!",
    "What a time to be alive — {keyword} breakthroughs everywhere {hashtag}",
    "Proud to work in {keyword}. {hashtag} community is amazing 💪",
]

NEGATIVE_TEMPLATES = [
    "Seriously concerned about {keyword}. {hashtag} needs urgent attention.",
    "This is terrible — {keyword} is going downhill fast. {hashtag}",
    "{keyword} is a disaster waiting to happen. Wake up people {hashtag}",
    "Lost all faith in {keyword}. {hashtag} is just empty hype.",
    "The {keyword} situation is getting worse every day {hashtag} 😡",
    "Another failure in {keyword}. When will they learn? {hashtag}",
    "Disappointed by the lack of progress on {keyword} {hashtag}",
    "Can't trust anything about {keyword} anymore. {hashtag}",
    "We're heading in the wrong direction with {keyword}. {hashtag} 😔",
    "Stop pretending {keyword} is fine. It's broken. {hashtag}",
]

NEUTRAL_TEMPLATES = [
    "Interesting update on {keyword}. What do you think? {hashtag}",
    "Reading about {keyword} — here's what I found: {hashtag}",
    "What do you all think about {keyword}? {hashtag}",
    "{keyword} is back in the news again. {hashtag}",
    "New report on {keyword} just dropped {hashtag}",
    "Following the {keyword} story closely. {hashtag}",
    "Anyone else tracking {keyword} developments? {hashtag}",
    "Just saw some data on {keyword}. Interesting trends. {hashtag}",
    "Here's a quick summary of {keyword} this week. {hashtag}",
    "Sharing this article on {keyword} for discussion. {hashtag}",
]


# ═══════════════════════════════════════════════════════════════════════
#  GEO LOCATIONS — (city, latitude, longitude)
# ═══════════════════════════════════════════════════════════════════════
LOCATIONS = [
    ("New York, US",        40.7128,  -74.0060),
    ("London, UK",          51.5074,   -0.1278),
    ("Mumbai, India",       19.0760,   72.8777),
    ("Tokyo, Japan",        35.6762,  139.6503),
    ("São Paulo, Brazil",  -23.5505,  -46.6333),
    ("Sydney, Australia",  -33.8688,  151.2093),
    ("Berlin, Germany",     52.5200,   13.4050),
    ("Nairobi, Kenya",      -1.2921,   36.8219),
    ("Toronto, Canada",     43.6532,  -79.3832),
    ("Seoul, South Korea",  37.5665,  126.9780),
    ("Dubai, UAE",          25.2048,   55.2708),
    ("Singapore",            1.3521,  103.8198),
    ("Lagos, Nigeria",       6.5244,    3.3792),
    ("Mexico City, Mexico", 19.4326,  -99.1332),
    ("Bengaluru, India",    12.9716,   77.5946),
]


# ═══════════════════════════════════════════════════════════════════════
#  SIMULATOR CLASS
# ═══════════════════════════════════════════════════════════════════════
class SocialMediaSimulator:
    """
    Generates a continuous stream of realistic social media posts.

    Usage
    -----
        sim = SocialMediaSimulator(rate=20)
        for post in sim.stream():
            print(post)
    """

    def __init__(self, rate: int = 20, burst_prob: float = 0.05):
        """
        Parameters
        ----------
        rate        : Target posts per second.
        burst_prob  : Per-post probability of triggering a burst event
                      (simulates a topic going viral).
        """
        self.rate = rate
        self.burst_prob = burst_prob
        self._burst_topic = None
        self._burst_remaining = 0

    # ── Public API ──────────────────────────────────────────────────────

    def generate_post(self) -> dict:
        """Return a single synthetic social media post as a dictionary."""

        # 1. Pick topic (burst-aware)
        topic = self._pick_topic()
        keyword = random.choice(topic["keywords"])
        hashtag = topic["hashtag"]

        # 2. Pick sentiment bucket → matching template
        roll = random.random()
        if roll < 0.40:
            template = random.choice(POSITIVE_TEMPLATES)
        elif roll < 0.75:
            template = random.choice(NEUTRAL_TEMPLATES)
        else:
            template = random.choice(NEGATIVE_TEMPLATES)

        text = template.format(keyword=keyword, hashtag=hashtag)

        # 3. Optionally append a second hashtag
        if random.random() < 0.30:
            extra = random.choice(
                [t["hashtag"] for t in TRENDING_TOPICS if t["hashtag"] != hashtag]
            )
            text += f" {extra}"

        # 4. Build location (70 % of posts carry geo data)
        location = None
        if random.random() < 0.70:
            city, lat, lon = random.choice(LOCATIONS)
            location = {"city": city, "lat": lat, "lon": lon}

        return {
            "post_id":   str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id":   f"user_{random.randint(1000, 99999)}",
            "text":      text,
            "hashtags":  self._extract_hashtags(text),
            "location":  location,
            "platform":  random.choice(["twitter", "reddit", "mastodon"]),
        }

    def stream(self):
        """Infinite generator yielding posts at the configured rate."""
        interval = 1.0 / self.rate
        while True:
            yield self.generate_post()
            time.sleep(interval)

    def generate_batch(self, n: int) -> list:
        """Generate *n* posts instantly (for sample-data / backfill)."""
        return [self.generate_post() for _ in range(n)]

    # ── Internals ───────────────────────────────────────────────────────

    def _pick_topic(self) -> dict:
        """Select a topic with burst-event logic."""
        if self._burst_remaining > 0:
            self._burst_remaining -= 1
            return self._burst_topic

        if random.random() < self.burst_prob:
            self._burst_topic = random.choice(TRENDING_TOPICS)
            self._burst_remaining = random.randint(15, 50)
            return self._burst_topic

        return random.choice(TRENDING_TOPICS)

    @staticmethod
    def _extract_hashtags(text: str) -> list:
        """Pull all #hashtags from the text."""
        return [w for w in text.split() if w.startswith("#")]


# ── Standalone test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    sim = SocialMediaSimulator(rate=5)
    print("🔄 Generating sample posts (Ctrl+C to stop):\n")
    for post in sim.stream():
        print(json.dumps(post, indent=2))
        print("─" * 60)
