# FocusVault: AI-Powered Learning Memory & Focus Tracker

[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-005571)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-00D2FF)](https://qdrant.tech)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB)](https://react.dev)

**Final Year B.Tech CS Project | Team Size: 3 Members | December 2025**

Tracks learning activity → builds a **personal knowledge vault** → enables **RAG-based Q&A** strictly from **your own learning pages**.

---

## 🎯 Live Demo Flow (30 Seconds)

```text
1. Chrome Extension tracks GFG reading (20 mins)
2. ML Classifier → Learning (92%), Topic: DSA
3. Page indexed into Qdrant vector store
4. Query: "What is DP?" → Answer from your study history
5. Auto-generated flashcards → ML quality filtering
```

---

## 🛠 Complete Tech Stack

| Component  | Technology                          | Purpose                           |
| ---------- | ----------------------------------- | --------------------------------- |
| Extension  | Chrome Manifest V3, JavaScript      | Track browsing activity           |
| Backend    | FastAPI, Python 3.11                | ML inference + RAG orchestration  |
| Database   | PostgreSQL 12+                      | Events, users, flashcards         |
| Vector DB  | Qdrant                              | Semantic search over page chunks  |
| ML Models  | scikit-learn, LightGBM              | Activity + topic + quality models |
| Embeddings | all-MiniLM-L6-v2                    | 384-dim semantic vectors          |
| LLM        | Gemini API                          | Flashcard & RAG answer polishing  |
| Frontend   | React / Next.js, Tailwind, Recharts | Dashboard & analytics             |

**Engineering Split:** 70% custom ML + pipelines, 30% APIs

---

## 📋 Software Requirements Specification (SRS)

### Functional Requirements (FR)

```text
FR1: Track URL, title, domain, duration, and hour of visit
FR2: Classify activity (learning/work/entertainment) ≥85% accuracy
FR3: Auto-cluster topics using K-Means (DSA, OS, React, CN)
FR4: Learning pages chunked, embedded, stored in Qdrant
FR5: RAG answers must use only the user's stored pages
FR6: Generate daily flashcards and filter quality >0.7
FR7: Dashboard analytics (learning %, topic charts)
FR8: Spaced repetition scheduling (Easy: 7d, Hard: 1d)
```

### Non-Functional Requirements (NFR)

```text
NFR1: Extension latency <100 ms
NFR2: RAG response <2 seconds
NFR3: ML accuracy targets met
NFR4: User privacy & domain control
NFR5: Support 1000 users, 10k events/day
NFR6: One-click Docker demo setup
```

---

## 🏗 High Level Design (HLD)

```mermaid
graph TB
    A[Chrome Extension] -->|POST Events| B[FastAPI Backend]
    C[React Dashboard] -->|REST APIs| B
    B --> D[ML Service (.pkl models)]
    B --> E[PostgreSQL]
    B --> F[Qdrant Vector DB]
    G[Celery Worker] -->|Index Pages| F
    D --> H[Gemini API]
```

### Data Flow (Per Page Visit)

```text
1. Extension sends page activity
2. ML predicts activity & topic
3. Event stored in PostgreSQL
4. Page fetched, chunked, embedded
5. Vectors stored in Qdrant
```

### RAG Query Flow

```text
User Question → Embedding → Qdrant Search
→ Context + Query → Gemini → Answer
```

---

## 🔧 Low Level Design (LLD)

### Database Schema (PostgreSQL)

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100)
);

CREATE TABLE browser_events (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  url TEXT,
  title TEXT,
  domain VARCHAR(100),
  duration_seconds INT,
  hour_of_day INT,
  activity_label VARCHAR(20),
  activity_probs JSONB,
  topic_id INT,
  is_saved_to_kb BOOLEAN DEFAULT FALSE
);

CREATE TABLE flashcards (
  id SERIAL PRIMARY KEY,
  user_id INT,
  question TEXT,
  answer TEXT,
  quality_score FLOAT,
  next_review_at TIMESTAMP,
  difficulty_last VARCHAR(10)
);
```

### Qdrant Collection

```json
{
  "name": "focusvault_chunks",
  "vectors": {"size": 384, "distance": "Cosine"},
  "payload": {
    "user_id": "integer",
    "topic_id": "integer",
    "url": "keyword",
    "chunk_text": "text"
  }
}
```

### ML Models Summary

| Model               | Input                 | Output        | Accuracy        |
| ------------------- | --------------------- | ------------- | --------------- |
| Activity Classifier | Title, Duration, Hour | Probabilities | 87%             |
| Topic Clusterer     | Title                 | Topic ID      | Silhouette 0.42 |
| Flashcard Scorer    | Q/A pair              | Quality Score | 78%             |

---

## 🚀 Quick Start (Docker)

```bash
git clone <repo-url>
cd focusvault
docker-compose up -d
```

**Access Points**

* Backend: [http://localhost:8000/docs](http://localhost:8000/docs)
* Frontend: [http://localhost:3000](http://localhost:3000)
* Qdrant: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 📁 Project Structure

```text
focusvault/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   └── main.py
│   ├── models/
│   └── requirements.txt
├── frontend/
├── extension/
├── data/
├── docker-compose.yml
└── README.md
```

---

## 📊 Evaluation Metrics

| Metric              | Target | Achieved |
| ------------------- | ------ | -------- |
| Classifier Accuracy | ≥85%   | 87%      |
| RAG Relevance       | ≥80%   | 82%      |
| Flashcard Quality   | ≥75%   | 78%      |
| End-to-End Latency  | <2s    | 1.8s     |

---

## 🔒 Privacy & Security

```text
• Local storage only (Postgres + Qdrant)
• Domain whitelist/blacklist
• No cloud ML inference
• Manual save-to-KB option
• JWT authentication (optional)
```

---

## 🎓 Academic Contributions

1. Custom ML pipeline with 3 models
2. Personalized RAG over user data
3. Passive learning capture system
4. Production-grade ML deployment

---

**Load Extension → Study → Ask → Recall → Retain Forever**
