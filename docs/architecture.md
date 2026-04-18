# 🏗️ System Architecture — Real-Time Social Media Trend Analyzer

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        REAL-TIME SOCIAL MEDIA TREND ANALYZER                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐   │
│   │  DATA SOURCE  │     │    KAFKA     │     │     SPARK STRUCTURED         │   │
│   │    LAYER      │────▶│    LAYER     │────▶│       STREAMING              │   │
│   │              │     │              │     │                              │   │
│   │ • Simulator  │     │ • Producer   │     │ • JSON Parsing               │   │
│   │ • Reddit API │     │ • Topic:     │     │ • Sentiment UDFs             │   │
│   │ • Twitter    │     │   social_    │     │ • Keyword Extraction         │   │
│   │   (optional) │     │   stream     │     │ • Windowed Aggregation       │   │
│   └──────────────┘     └──────────────┘     └──────────┬───────────────────┘   │
│                                                         │                       │
│                                                         ▼                       │
│   ┌──────────────────────────────┐     ┌──────────────────────────────────┐    │
│   │      VISUALIZATION           │     │        NLP LAYER                 │    │
│   │        LAYER                 │◀────│                                  │    │
│   │                              │     │ • VADER Sentiment Analyzer       │    │
│   │ • Streamlit Dashboard        │     │ • TextBlob (alternative)         │    │
│   │ • Plotly Charts              │     │ • NLTK Tokenization              │    │
│   │ • Word Cloud                 │     │ • Stop-word Filtering            │    │
│   │ • Geo Map                    │     │ • Keyword Ranking                │    │
│   │ • Spike Alerts               │     └──────────────────────────────────┘    │
│   └──────────────┬───────────────┘                                             │
│                  │                      ┌──────────────────────────────────┐    │
│                  └─────────reads───────▶│       STORAGE LAYER              │    │
│                                         │                                  │    │
│                                         │ • processed_posts.csv            │    │
│                                         │ • trending_keywords.csv          │    │
│                                         │ • sentiment_summary.csv          │    │
│                                         │ • geo_sentiment.csv              │    │
│                                         │ • alerts.csv                     │    │
│                                         └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Source Layer (`data_generator/simulator.py`)

```
┌─────────────────────────────────────────────────┐
│              SocialMediaSimulator                │
├─────────────────────────────────────────────────┤
│                                                  │
│  8 Trending Topics                               │
│  ├── #AI, #ClimateChange, #Elections2026         │
│  ├── #CryptoMarket, #WorldCup, #TechLayoffs     │
│  └── #SpaceX, #MentalHealth                     │
│                                                  │
│  30 Sentence Templates                           │
│  ├── 10 Positive  (40% probability)              │
│  ├── 10 Neutral   (35% probability)              │
│  └── 10 Negative  (25% probability)              │
│                                                  │
│  15 Geo Locations (city + lat/lon)               │
│  └── 70% of posts carry location data            │
│                                                  │
│  Burst Events                                    │
│  └── 5% chance per post → 15–50 post burst       │
│      (simulates viral moments)                   │
│                                                  │
│  Output: JSON dict per post                      │
│  {                                               │
│    "post_id":   "uuid",                          │
│    "timestamp": "2026-04-14T10:30:00Z",          │
│    "user_id":   "user_12345",                    │
│    "text":      "Great news about AI! #AI 🚀",   │
│    "hashtags":  ["#AI"],                         │
│    "location":  {"city":"NYC", "lat":40, "lon":-74},│
│    "platform":  "twitter"                        │
│  }                                               │
└─────────────────────────────────────────────────┘
```

### 2. Kafka Layer (`kafka_layer/producer.py`)

```
  Simulator.stream()
       │
       │  (generates 20 posts/sec)
       ▼
  ┌─────────────────┐        ┌─────────────────────┐
  │  KafkaPostProducer │─────▶│  Kafka Broker        │
  │                   │       │  Topic: social_stream │
  │ • JSON serializer │       │  Partitions: 3        │
  │ • UTF-8 encoding  │       │  Replication: 1       │
  │ • acks=all        │       │                       │
  │ • retry=3         │       │  Key: post_id         │
  │ • error callbacks │       │  Value: JSON payload   │
  └─────────────────┘        └─────────────────────┘
```

### 3. Spark Processing Layer (`spark_layer/stream_processor.py`)

```
  Kafka Topic                    Spark Structured Streaming
  ─────────────                  ──────────────────────────
  social_stream  ──────────▶  ┌──────────────────────────────┐
                              │  1. readStream (Kafka source) │
                              │  2. Parse JSON → DataFrame    │
                              │  3. Apply UDFs:                │
                              │     • sentiment_label_udf()   │
                              │     • sentiment_score_udf()   │
                              │     • keywords_udf()          │
                              │  4. Windowed Aggregations:     │
                              │     • 5-min tumbling window    │
                              │     • group by sentiment_label │
                              │     • explode keywords + count │
                              │  5. Write to CSV (append mode) │
                              └──────────────────────────────┘
```

### 4. NLP Layer (`nlp_layer/sentiment.py`)

```
  Input Text
      │
      ▼
  ┌────────────────────────┐
  │   SentimentAnalyzer     │
  │                         │
  │   ┌──── VADER ────┐    │     Output:
  │   │ compound score │────│────▶ sentiment_score: -1.0 to +1.0
  │   │  social-media  │    │     sentiment_label: pos/neg/neu
  │   │  aware (emojis │    │
  │   │  slang, caps)  │    │
  │   └────────────────┘    │
  │                         │
  │   ┌── Keyword Extractor─┐    ▶ keywords: ["ai", "future", ...]
  │   │ tokenize → filter   │
  │   │ stopwords → count   │
  │   │ → top-N             │
  │   └─────────────────────┘
  │                         │
  │   ┌── Hashtag Extractor─┐    ▶ hashtags: ["#AI", "#SpaceX"]
  │   │ regex: #\w+         │
  │   └─────────────────────┘
  └────────────────────────┘
```

### 5. Dashboard (`dashboard/app.py`)

```
  ┌─────────────────────────────────────────────────────────┐
  │                STREAMLIT DASHBOARD                       │
  ├──────────┬──────────┬──────────┬──────────┬─────────────┤
  │  Total   │ Positive │ Negative │ Neutral  │  Avg Score  │
  │  Posts   │    😊     │    😠     │    😐    │   +0.123    │
  ├──────────┴──────────┴──────────┴──────────┴─────────────┤
  │                                                          │
  │  ┌─── Sentiment Pie ───┐  ┌─── Trending Keywords ────┐  │
  │  │       ╭───╮          │  │  ██████████ AI            │  │
  │  │     ╭─┤40%├─╮        │  │  ████████   climate       │  │
  │  │    ╭┤  ╰───╯  ├╮     │  │  ██████     bitcoin       │  │
  │  │    │  35%  25% │     │  │  ████       election      │  │
  │  │    ╰───────────╯     │  │  ███        rocket        │  │
  │  └─────────────────────┘  └────────────────────────────┘  │
  │                                                          │
  │  ┌── Time Series ──────┐  ┌──── Word Cloud ───────────┐  │
  │  │  ╱╲   ╱╲            │  │                            │  │
  │  │ ╱  ╲ ╱  ╲  ╱╲       │  │   AI  climate  bitcoin    │  │
  │  │╱    ╳    ╲╱  ╲      │  │  election  rocket  space  │  │
  │  └─────────────────────┘  └────────────────────────────┘  │
  │                                                          │
  │  ┌── Hashtag Analysis ─┐  ┌──── Geo Sentiment Map ────┐  │
  │  │  #AI          ████  │  │     🌍                      │  │
  │  │  #ClimateChange ███ │  │   🟢NYC  🔴London          │  │
  │  │  #CryptoMarket ██  │  │      🟡Mumbai  🟢Tokyo      │  │
  │  └─────────────────────┘  └────────────────────────────┘  │
  │                                                          │
  │  ┌── Spike Alerts ─────┐  ┌──── Platform Breakdown ───┐  │
  │  │  🚨 "bitcoin" spike │  │  twitter  ████████         │  │
  │  │  🚨 "AI" spike      │  │  reddit   ██████           │  │
  │  └─────────────────────┘  │  mastodon ████             │  │
  │                           └────────────────────────────┘  │
  │  ┌── Raw Data Explorer (expandable) ───────────────────┐  │
  │  │  timestamp | text | sentiment | score | city | ...  │  │
  │  └─────────────────────────────────────────────────────┘  │
  └──────────────────────────────────────────────────────────┘

  Auto-refreshes every 3 seconds (configurable)
```

## Two Execution Modes

### Mode A: Full Pipeline (Kafka + Spark)
```
  Terminal 1:  docker-compose up -d          (Kafka infrastructure)
  Terminal 2:  python kafka_layer/producer.py (stream posts → Kafka)
  Terminal 3:  python spark_layer/stream_processor.py  (consume → enrich → CSV)
  Terminal 4:  streamlit run dashboard/app.py (visualize)
```

### Mode B: Standalone Demo (No Kafka, No Spark)
```
  Terminal 1:  python run_standalone.py       (simulate → enrich → CSV)
  Terminal 2:  streamlit run dashboard/app.py (visualize)
```

## Data Flow Summary

```
  POST GENERATED ──▶ KAFKA TOPIC ──▶ SPARK CONSUMER ──▶ SENTIMENT UDF ──▶ CSV FILES ──▶ DASHBOARD
       │                                                                       │
       │              (Mode B skips Kafka + Spark)                             │
       └───────────────────── direct ──────────────────────────────────────────┘
```

## Technology Stack

| Layer           | Technology                  | Purpose                          |
|-----------------|-----------------------------|----------------------------------|
| Data Source     | Python + Faker              | Simulated social media posts     |
| Message Broker  | Apache Kafka 7.6            | Real-time message streaming      |
| Stream Engine   | Apache Spark 3.5            | Structured streaming + UDFs      |
| NLP             | VADER + NLTK                | Sentiment + keyword extraction   |
| Storage         | CSV (Pandas)                | Lightweight persistence          |
| Dashboard       | Streamlit + Plotly          | Interactive real-time charts     |
| Infrastructure  | Docker Compose              | Kafka + Zookeeper containers     |
