# 📘 Rahul's Helper Guide: Social Media Trend Analyzer

Welcome to the **Social Media Trend Analyzer**! This document is designed to give you an end-to-end understanding of what this project is, how it works, and what each part of the code does. Think of it as your beginner-friendly compass to navigate the codebase.

---

## 🎯 1. What is this project?

The **Social Media Trend Analyzer** is a real-time data engineering and analytics pipeline. 
Imagine Twitter, Reddit, or Instagram: thousands of posts are created every second. This project simulates that kind of traffic, reads it in real-time, figures out if the posts are positive or negative (Sentiment Analysis), identifies trending keywords, and visualizes everything on a live dashboard.

**Key Features:**
- **Real-time Data Streaming:** Handles incoming data continuously, not just in static batches.
- **Natural Language Processing (NLP):** Understands the emotional tone of text.
- **Interactive Dashboard:** Live-updating charts and word clouds.
- **Two Modes of Operation:**
  1. **Standalone Mode:** Easy to run on a local machine without complex setups.
  2. **Big Data Mode:** Uses industry-standard tools (Kafka & Apache Spark) capable of handling millions of records.

---

## 🏗️ 2. High-Level Architecture

Data flows through the system in a straight line:
1. **Generation:** Fake posts are created.
2. **Ingestion (Pipeline Mode):** Posts are sent to a waiting room (Kafka).
3. **Processing:** Posts are analyzed for sentiment and keywords.
4. **Storage:** Processed data is saved to `.csv` files.
5. **Visualization:** The dashboard reads the `.csv` files and draws charts.

---

## 🧩 3. Module Breakdown (What does what?)

Here is how the project folders are organized and what exactly they do:

### ⚙️ Core Configuration
- **`config.py`**: The central brain for settings. It stores variables like how many posts to generate per second, file paths, and Kafka server addresses. Change things here once, and it updates everywhere.
- **`docker-compose.yml`**: A blueprint file used by Docker to spin up Kafka and Zookeeper (required for the Big Data mode). 
- **`requirements.txt`**: A list of all Python libraries (like `pandas`, `streamlit`, `nltk`) needed to run the project.

### 🏭 1. `data_generator/`
*The Fake Data Factory*
- **`simulator.py`**: Uses a library called `Faker` to generate highly realistic, random social media posts. It creates fake usernames, locations, timestamps, and randomized text.

### 📡 2. `kafka_layer/` 
*The Delivery System (Used in Full Pipeline Mode)*
- **`producer.py`**: Acts like a mailman. It grabs the fake posts from the `simulator.py` and publishes them to an Apache Kafka topic (a real-time data queue) so the next system can read them at its own pace.

### 🧠 3. `spark_layer/`
*The Heavy Lifter (Used in Full Pipeline Mode)*
- **`stream_processor.py`**: Connects to Kafka using Apache Spark. It pulls the massive stream of posts, organizes them into structured tables (DataFrames), and routes them to the NLP layer in real-time. 

### 💬 4. `nlp_layer/`
*The Brains / Artificial Intelligence*
- **`sentiment.py`**: Uses NLP libraries like `VADER` and `TextBlob`. It reads a tweet (e.g., *"I love this new phone!"*) and assigns it a mathematical score (e.g., `+0.85` for Positive). It also extracts trending words (e.g., ignoring words like "the" or "and").

### 💾 5. `storage/`
*The Filing Cabinet*
- **`writer.py`**: Takes the processed, scored data and writes it out to CSV files inside the `output/` folder so the dashboard can access it.

### 📊 6. `dashboard/`
*The User Interface*
- **`app.py`**: A web application built with Streamlit. It constantly reads the CSV files from the `storage/` folder and updates graphs, metrics, and word clouds on your screen.

### 🏃 7. Runner Scripts
*The "Start Buttons"*
- **`run_standalone.py`**: Bypasses Kafka and Spark. It runs the generator, NLP, and storage all in one simple Python script. Perfect for testing and beginners.
- **`run_pipeline.py`** / **Kafka+Spark scripts**: The complex way to run it using the Big Data tools.

### 📂 Other Folders
- **`sample_data/`**: Contains scripts to just dump 500 fake posts immediately so you can test the dashboard without running a live stream.
- **`docs/`**: Where this guide and other setup instructions live.

---

## 🚀 4. How to run it right now (The Easy Way)

1. Open a terminal and run the backend:
   ```bash
   python run_standalone.py
   ```
2. Open a **second** terminal and run the frontend:
   ```bash
   streamlit run dashboard/app.py
   ```
3. Open the link provided in the terminal (usually `http://localhost:8501`) in your web browser.

---

## 💡 Note on PDF Conversion
*This document is written in Markdown format. To save it as a PDF, right-click this file in VS Code and select "Markdown PDF: Export (pdf)" if you have the Markdown PDF extension installed, or open it in a browser and "Print to PDF".*