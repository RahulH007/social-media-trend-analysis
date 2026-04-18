"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SENTIMENT.PY — NLP & Sentiment Analysis Module                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Provides:                                                                 ║
║    1. Sentiment scoring  (positive / negative / neutral + numeric score)   ║
║    2. Keyword extraction (top-N meaningful words per text)                  ║
║    3. Hashtag extraction                                                   ║
║                                                                            ║
║  Engines:                                                                  ║
║    • VADER   — rule-based, fast, great for social media slang / emojis     ║
║    • TextBlob — pattern-based, good general-purpose baseline               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
import string
from collections import Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# ── Download required NLTK data (runs once, cached afterwards) ──────────
for _pkg in ("punkt", "punkt_tab", "stopwords", "averaged_perceptron_tagger"):
    nltk.download(_pkg, quiet=True)

STOP_WORDS = set(stopwords.words("english"))

# ── Extra stop words common in social media but meaningless for trends ──
EXTRA_STOPS = {
    "rt", "like", "just", "im", "get", "got", "one",
    "know", "go", "think", "see", "also", "us", "new",
    "would", "could", "make", "really", "much", "even",
    "still", "back", "way", "want", "need", "let",
    "via", "amp", "https", "http", "co",
}
STOP_WORDS |= EXTRA_STOPS


class SentimentAnalyzer:
    """
    Unified interface for sentiment analysis.

    Parameters
    ----------
    engine : str
        "vader" (default) or "textblob".
    """

    def __init__(self, engine: str = "vader"):
        self.engine = engine.lower()

        if self.engine == "vader":
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()

        elif self.engine == "textblob":
            from textblob import TextBlob          # noqa: F401
            self._textblob_cls = TextBlob

        else:
            raise ValueError(f"Unknown engine '{engine}'. Use 'vader' or 'textblob'.")

    # ─────────────────────────────────────────────────────────────────────
    #  PUBLIC: Analyze a single post
    # ─────────────────────────────────────────────────────────────────────
    def analyze(self, text: str) -> dict:
        """
        Analyze a social media post and return enriched metadata.

        Returns
        -------
        dict with keys:
            sentiment_label : str    — "positive" / "negative" / "neutral"
            sentiment_score : float  — continuous score (-1.0 … +1.0)
            keywords        : list   — top meaningful words
            hashtags        : list   — extracted hashtags
        """
        score = self._compute_score(text)
        label = self._label_from_score(score)
        keywords = self.extract_keywords(text, top_n=5)
        hashtags = self.extract_hashtags(text)

        return {
            "sentiment_label": label,
            "sentiment_score": round(score, 4),
            "keywords":        keywords,
            "hashtags":        hashtags,
        }

    # ─────────────────────────────────────────────────────────────────────
    #  PUBLIC: Batch analysis
    # ─────────────────────────────────────────────────────────────────────
    def analyze_batch(self, texts: list) -> list:
        """Analyze a list of texts, returning a list of result dicts."""
        return [self.analyze(t) for t in texts]

    # ─────────────────────────────────────────────────────────────────────
    #  Keyword extraction
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def extract_keywords(text: str, top_n: int = 5) -> list:
        """
        Tokenize, filter stop-words / punctuation / short tokens,
        and return the top-N most frequent meaningful words.
        """
        # Clean the text
        clean = re.sub(r"http\S+|@\w+|#\w+", "", text)   # strip URLs, mentions, hashtags
        clean = clean.lower().translate(
            str.maketrans("", "", string.punctuation)
        )

        tokens = word_tokenize(clean)
        meaningful = [
            tok for tok in tokens
            if tok not in STOP_WORDS and len(tok) > 2 and tok.isalpha()
        ]

        counts = Counter(meaningful)
        return [word for word, _ in counts.most_common(top_n)]

    # ─────────────────────────────────────────────────────────────────────
    #  Hashtag extraction
    # ─────────────────────────────────────────────────────────────────────
    @staticmethod
    def extract_hashtags(text: str) -> list:
        """Return a list of hashtags found in the text (case-preserved)."""
        return re.findall(r"#\w+", text)

    # ─────────────────────────────────────────────────────────────────────
    #  Internal scoring methods
    # ─────────────────────────────────────────────────────────────────────
    def _compute_score(self, text: str) -> float:
        """Return a float in [-1, +1]."""
        if self.engine == "vader":
            scores = self._vader.polarity_scores(text)
            return scores["compound"]              # compound score: -1…+1

        else:  # textblob
            from textblob import TextBlob
            blob = TextBlob(text)
            return blob.sentiment.polarity          # polarity: -1…+1

    @staticmethod
    def _label_from_score(score: float) -> str:
        """Classify continuous score into a discrete label."""
        if score >= 0.05:
            return "positive"
        elif score <= -0.05:
            return "negative"
        else:
            return "neutral"


# ═══════════════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    analyzer = SentimentAnalyzer(engine="vader")

    samples = [
        "Absolutely loving the progress in machine learning! #AI is the future 🚀",
        "This is terrible — crypto is going downhill fast. #CryptoMarket 😡",
        "New report on climate change just dropped #ClimateChange",
        "Lost all faith in the election process. #Elections2026 is broken.",
        "What a time to be alive — space exploration breakthroughs everywhere #SpaceX ✨",
    ]

    for text in samples:
        result = analyzer.analyze(text)
        print(f"\n📝  {text}")
        print(f"    Label:    {result['sentiment_label']}")
        print(f"    Score:    {result['sentiment_score']}")
        print(f"    Keywords: {result['keywords']}")
        print(f"    Hashtags: {result['hashtags']}")
