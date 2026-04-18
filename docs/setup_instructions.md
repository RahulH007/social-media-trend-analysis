# 📋 Step-by-Step Setup Instructions

## Prerequisites

| Software       | Version  | Required For        | Install Link                          |
|----------------|----------|---------------------|---------------------------------------|
| Python         | 3.9+     | Everything          | https://python.org/downloads          |
| pip            | 21+      | Python packages     | Comes with Python                     |
| Docker Desktop | 4.0+     | Kafka (Mode A only) | https://docker.com/products/docker-desktop |
| Java JDK       | 11 or 17 | Spark (Mode A only) | https://adoptium.net                  |

---

## Quick Start (Mode B — Standalone, No Kafka/Spark)

This is the easiest way to run the project. No Docker, no Java, no Kafka needed.

### Step 1: Clone / Extract the Project

```bash
cd social-media-trend-analyzer
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first run will also download NLTK data files (punkt, stopwords).
> This happens automatically and requires an internet connection.

### Step 4: Generate Sample Data (Optional Quick Test)

```bash
python sample_data/generate_sample.py
```

This creates 500 pre-analyzed posts so the dashboard has data immediately.

### Step 5: Run the Standalone Pipeline

**Terminal 1** — Start the data pipeline:
```bash
python run_standalone.py
```

You'll see output like:
```
10:30:01 │ INFO    │ ══════════════════════════════════════════
10:30:01 │ INFO    │   STANDALONE PIPELINE — No Kafka / No Spark
10:30:01 │ INFO    │   Generating 20 posts/sec → Sentiment → CSV
10:30:03 │ INFO    │ 📊  Processed 50 posts  |  latest sentiment: positive (0.67)
10:30:05 │ INFO    │ 💾  Flushed 40 posts to disk
```

### Step 6: Launch the Dashboard

**Terminal 2** — Start Streamlit:
```bash
streamlit run dashboard/app.py
```

Your browser will open at `http://localhost:8501` with the live dashboard.

---

## Full Pipeline Setup (Mode A — Kafka + Spark)

### Step 1–3: Same as above

### Step 4: Start Kafka Infrastructure

```bash
docker-compose up -d
```

Wait ~30 seconds for Kafka to be ready. Verify:
```bash
docker-compose ps
# All services should show "Up (healthy)"
```

(Optional) Open Kafka UI at `http://localhost:8080` to monitor topics.

### Step 5: Create the Kafka Topic (Optional — Auto-creates)

```bash
docker exec -it kafka kafka-topics \
    --create \
    --topic social_stream \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1
```

### Step 6: Start the Kafka Producer

**Terminal 2:**
```bash
python kafka_layer/producer.py
```

### Step 7: Start the Spark Consumer

**Terminal 3:**
```bash
python spark_layer/stream_processor.py
```

> **Note:** The first run downloads the Spark-Kafka connector JAR (~30 MB).

### Step 8: Launch the Dashboard

**Terminal 4:**
```bash
streamlit run dashboard/app.py
```

---

## Verifying the Pipeline

### Check 1: Output Files Exist

```bash
ls -la output/
# Expected files:
#   processed_posts.csv
#   trending_keywords.csv
#   sentiment_summary.csv
#   geo_sentiment.csv
#   alerts.csv (if spikes detected)
```

### Check 2: Data is Flowing

```bash
wc -l output/processed_posts.csv
# Should show increasing line count over time
```

### Check 3: Dashboard is Live

Open `http://localhost:8501` — charts should update every 3 seconds.

---

## Troubleshooting

### "No data yet" on the dashboard
- Ensure `run_standalone.py` or the Kafka pipeline is running
- Check that `output/processed_posts.csv` exists and has data

### Kafka connection errors
- Verify Docker containers are running: `docker-compose ps`
- Check Kafka logs: `docker-compose logs kafka`
- Ensure port 9092 is not in use by another application

### Spark JAR download fails
- Check internet connection
- Manually download the Kafka connector:
  ```bash
  pip install pyspark[sql]
  ```

### NLTK download errors
- Run manually:
  ```python
  import nltk
  nltk.download('punkt')
  nltk.download('punkt_tab')
  nltk.download('stopwords')
  nltk.download('averaged_perceptron_tagger')
  ```

### ModuleNotFoundError
- Ensure you're in the project root directory
- Ensure the virtual environment is activated
- Re-run: `pip install -r requirements.txt`

---

## Stopping the Pipeline

### Standalone Mode
- Press `Ctrl+C` in the pipeline terminal
- Press `Ctrl+C` in the Streamlit terminal

### Full Pipeline Mode
- Press `Ctrl+C` in each terminal (producer, Spark, Streamlit)
- Stop Kafka: `docker-compose down`

---

## Cleaning Up

```bash
# Remove generated output files
rm -rf output/

# Remove Spark checkpoints
rm -rf /tmp/spark-checkpoints /tmp/spark-chk-*

# Remove Docker volumes (Kafka data)
docker-compose down -v
```
