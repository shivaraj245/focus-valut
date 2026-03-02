# FocusVault — Low Level Design (LLD)

**B.Tech Final Year Project | AI-Powered Learning Memory & Focus Tracker**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Chrome Extension — Internal Design](#3-chrome-extension--internal-design)
4. [Backend — Module Design](#4-backend--module-design)
   - 4.1 [Configuration Module](#41-configuration-module)
   - 4.2 [Database Layer](#42-database-layer)
   - 4.3 [Schema Layer (Pydantic)](#43-schema-layer-pydantic)
   - 4.4 [API Layer](#44-api-layer)
   - 4.5 [Service Layer](#45-service-layer)
5. [ML Pipeline Design](#5-ml-pipeline-design)
6. [Vector Indexing & Search Design](#6-vector-indexing--search-design)
7. [RAG (Retrieval-Augmented Generation) Pipeline](#7-rag-retrieval-augmented-generation-pipeline)
8. [Flashcard Service Design](#8-flashcard-service-design)
9. [Database Schema](#9-database-schema)
10. [REST API Contract](#10-rest-api-contract)
11. [Sequence Diagrams](#11-sequence-diagrams)
12. [Frontend — Component Design](#12-frontend--component-design)
13. [Configuration & Environment Design](#13-configuration--environment-design)
14. [Error Handling Strategy](#14-error-handling-strategy)
15. [Deployment Architecture](#15-deployment-architecture)

---

## 1. Introduction

This document describes the **Low Level Design** of FocusVault — an AI-powered learning memory and focus tracker. It specifies the internal design of every module, class interfaces, database schema, API contracts, sequence flows, and algorithms used throughout the system.

### Scope

| Layer | Description |
|-------|-------------|
| Chrome Extension | Manifest V3 extension for browsing activity capture |
| FastAPI Backend | REST API server, orchestration, business logic |
| ML Service | Activity classification + topic clustering |
| Indexing Service | Web scraping, chunking, embedding ingestion |
| Vector Service | Qdrant-based semantic storage and retrieval |
| RAG Service | Gemini-based answer generation over personal knowledge |
| Flashcard Service | AI-powered flashcard generation + spaced repetition |
| Analytics Service | Daily/weekly/topic usage aggregation |
| React Frontend | SPA dashboard for user interaction |

---

## 2. System Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                  Chrome Extension                    │
│  background.js  │  content.js  │  popup.html/js/css  │
└────────────┬─────────────────────────────────────────┘
             │ POST /api/events/{user_id}
             ▼
┌──────────────────────────────────────────────────────┐
│                   FastAPI Backend                    │
│                                                      │
│  ┌──────────┐ ┌─────────┐ ┌────────────┐ ┌────────┐ │
│  │  Events  │ │  Query  │ │ Flashcards │ │Analytics│ │
│  │  Router  │ │  Router │ │   Router   │ │ Router │ │
│  └────┬─────┘ └────┬────┘ └─────┬──────┘ └───┬────┘ │
│       │            │            │             │      │
│  ┌────▼─────┐ ┌────▼────┐ ┌────▼──────┐      │      │
│  │MLService │ │RAGService│ │Flashcard  │      │      │
│  │          │ │         │ │Service    │      │      │
│  └────┬─────┘ └────┬────┘ └─────┬─────┘      │      │
│       │            │            │             │      │
│  ┌────▼─────────────▼────────────▼─────────────▼───┐ │
│  │              Service Layer                       │ │
│  │   IndexingService   │   VectorService            │ │
│  └──────────────┬──────┴──────────┬────────────────┘ │
└─────────────────│─────────────────│──────────────────┘
                  │                 │
         ┌────────▼──────┐  ┌───────▼───────┐  ┌────────────┐
         │  PostgreSQL   │  │    Qdrant     │  │ Gemini API │
         │  (metadata)   │  │  (vectors)    │  │  (LLM)     │
         └───────────────┘  └───────────────┘  └────────────┘
                  ▲
         ┌────────┴──────────────────────────────────┐
         │              React Frontend               │
         │  Dashboard │ Events │ Query │ Flashcards  │
         └───────────────────────────────────────────┘
```

---

## 3. Chrome Extension — Internal Design

### 3.1 Module Breakdown

| File | Responsibility |
|------|---------------|
| `manifest.json` | Declares permissions, background service worker, content scripts |
| `background.js` | Core tracking logic, offline queue, alarm-based sync |
| `content.js` | Page content extraction (text, metadata) |
| `popup.html/js/css` | UI for status, stats, settings |

### 3.2 `background.js` — State Variables

```
currentTab     : { id, url, title, domain, startTime }   // active tab metadata
tabStartTime   : number (ms epoch)                        // when current tab became active
isTracking     : boolean                                  // global on/off switch
userId         : number                                   // configured user identity
activeTabData  : Map<tabId, tabData>                      // per-tab accumulated data
```

### 3.3 Background Service Worker — Event Handlers

| Chrome Event | Handler | Action |
|---|---|---|
| `chrome.runtime.onInstalled` | Init handler | Set defaults in `chrome.storage.local`; create periodic alarm |
| `chrome.tabs.onActivated` | `handleTabChange(tabId)` | Save previous tab data; start timing new tab |
| `chrome.tabs.onUpdated` (status=complete) | `handleTabChange(tabId)` | Re-initialise timing on page navigation |
| `chrome.windows.onFocusChanged` | Focus handler | Save data on window blur; re-detect active tab on window focus |
| `chrome.alarms.onAlarm` (trackingAlarm) | Alarm handler | Flush offline queue; heartbeat log |
| `chrome.runtime.onSuspend` | Suspend handler | Emergency flush of current tab data |
| `chrome.runtime.onMessage` | Message switch | Handle `GET_STATUS`, `TOGGLE_TRACKING`, `UPDATE_SETTINGS` |

### 3.4 `handleTabChange(tabId)` — Flow

```
handleTabChange(tabId)
  │
  ├─ Read isTracking from storage → if false, return
  ├─ saveCurrentTabData()         → flush previous tab event to backend
  ├─ chrome.tabs.get(tabId)       → get URL/title
  ├─ Filter chrome:// URLs        → skip internal pages
  └─ Set currentTab = { id, url, title, domain, startTime=now }
```

### 3.5 `saveCurrentTabData()` — Flow

```
saveCurrentTabData()
  │
  ├─ duration = (now - tabStartTime) / 1000 seconds
  ├─ duration < 5 → discard (too short to be meaningful)
  └─ Build eventData = { url, title, domain, duration_seconds, hour_of_day }
       └─ sendEventToBackend(eventData)
            ├─ Success → update lastSync in storage; broadcast EVENT_TRACKED message
            └─ Failure → queueOfflineEvent(eventData) → append to offlineQueue (cap=100)
```

### 3.6 Offline Queue

```
offlineQueue : Array<{ url, title, domain, duration_seconds, hour_of_day, timestamp }>
Max size     : 100 entries (FIFO eviction)
Sync trigger : Periodic alarm (every 30 s) → syncOfflineEvents()
```

### 3.7 `content.js` — Page Extraction

Injected into every page. On `DOMContentLoaded`, extracts:
- `document.title`
- `meta[name=description]` content
- Main content text (from `<article>`, `<main>`, or `<body>`)

Sends extracted content to `background.js` via `chrome.runtime.sendMessage`.

---

## 4. Backend — Module Design

### 4.1 Configuration Module

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str          # PostgreSQL connection string

    # Qdrant
    QDRANT_HOST: str           # default "localhost"
    QDRANT_PORT: int           # default 6333
    QDRANT_COLLECTION: str     # default "focusvault_chunks"

    # LLM
    GEMINI_API_KEY: str        # Google Gemini API key

    # Auth (future)
    SECRET_KEY: str
    ALGORITHM: str             # "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # ML
    MODELS_PATH: str           # path to .pkl files directory
    LEARNING_THRESHOLD: float  # default 0.7
    FLASHCARD_QUALITY_THRESHOLD: float  # default 0.7

    # Embeddings
    EMBEDDING_MODEL: str       # "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_DIM: int            # 384

    # Chunking
    CHUNK_SIZE: int            # 512 words
    CHUNK_OVERLAP: int         # 50 words
```

### 4.2 Database Layer

**File:** `app/db/database.py`

```
engine        = create_engine(DATABASE_URL)
SessionLocal  = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base          = declarative_base()

get_db()      → yields a SQLAlchemy Session; always closes on exit (used as FastAPI dependency)
```

**File:** `app/db/models.py`

Four SQLAlchemy ORM classes map to PostgreSQL tables. See [Section 9](#9-database-schema) for full schema.

### 4.3 Schema Layer (Pydantic)

Pydantic models used for request validation and response serialization.

#### `app/schemas/event.py`

| Class | Direction | Fields |
|-------|-----------|--------|
| `BrowserEventCreate` | Request (POST body) | `url`, `title?`, `domain`, `duration_seconds`, `hour_of_day` |
| `BrowserEventResponse` | Response | all above + `id`, `user_id`, `activity_label`, `activity_probs`, `topic_id`, `topic_name`, `is_saved_to_kb`, `created_at` |
| `MLPredictionResponse` | Internal | `activity_label`, `activity_probs`, `topic_id`, `topic_name`, `is_learning` |

#### `app/schemas/flashcard.py`

| Class | Direction | Fields |
|-------|-----------|--------|
| `FlashcardCreate` | Request | `question`, `answer`, `source_url?` |
| `FlashcardResponse` | Response | `id`, `user_id`, `question`, `answer`, `quality_score`, `next_review_at`, `difficulty_last`, `review_count`, `source_url`, `created_at` |
| `FlashcardReview` | Request (POST body) | `difficulty` (`"easy"` \| `"medium"` \| `"hard"`) |
| `FlashcardGenerateRequest` | Request | `user_id`, `date?` |

#### `app/schemas/query.py`

| Class | Direction | Fields |
|-------|-----------|--------|
| `RAGQueryRequest` | Request | `question`, `user_id`, `top_k` (default 5) |
| `RAGContext` | Nested response | `text`, `url`, `topic_name`, `score` |
| `RAGQueryResponse` | Response | `question`, `answer`, `contexts: List[RAGContext]`, `confidence` |

### 4.4 API Layer

All routers registered in `app/main.py` with `/api/<resource>` prefix.

#### `app/api/events.py` — `EventRouter`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/{user_id}` | `create_event` | Accept event; run ML; persist; queue indexing |
| GET | `/{user_id}` | `get_user_events` | Paginated list of all events |
| GET | `/{user_id}/learning` | `get_learning_events` | Filter learning events only |
| DELETE | `/{event_id}` | `delete_event` | Hard-delete a single event |

#### `app/api/query.py` — `QueryRouter`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/` | `query_knowledge_base` | RAG Q&A over user's knowledge base |

#### `app/api/flashcards.py` — `FlashcardRouter`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/generate` | `generate_flashcards` | Trigger AI flashcard generation for a date |
| GET | `/{user_id}/due` | `get_due_flashcards` | Cards due for review (`next_review_at <= now`) |
| GET | `/{user_id}` | `get_user_flashcards` | All user flashcards (paginated) |
| POST | `/{flashcard_id}/review` | `review_flashcard` | Submit review difficulty; update schedule |
| POST | `/` | `create_flashcard` | Manual flashcard creation |
| DELETE | `/{flashcard_id}` | `delete_flashcard` | Hard-delete a flashcard |

#### `app/api/analytics.py` — `AnalyticsRouter`

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/{user_id}/daily` | `get_daily_analytics` | Stats for a single day |
| GET | `/{user_id}/weekly` | `get_weekly_analytics` | 7-day rolling stats |
| GET | `/{user_id}/topics` | `get_topic_analytics` | Per-topic time breakdown |
| GET | `/{user_id}/summary` | `get_user_summary` | Lifetime aggregate summary |

### 4.5 Service Layer

| Class | File | Responsibility |
|-------|------|---------------|
| `MLService` | `services/ml_service.py` | Load/run activity & topic ML models |
| `IndexingService` | `services/indexing_service.py` | Fetch, parse, chunk and index page content |
| `VectorService` | `services/vector_service.py` | Qdrant client wrapper (upsert, search, delete) |
| `RAGService` | `services/rag_service.py` | Orchestrate vector search + LLM answer generation |
| `FlashcardService` | `services/flashcard_service.py` | Generate, score, and persist flashcards |

---

## 5. ML Pipeline Design

### 5.1 `MLService` — Class Design

```
MLService (static/class methods only)
│
├── activity_model  : sklearn / LightGBM classifier  (loaded from .pkl)
├── topic_model     : KMeans clusterer                (loaded from .pkl)
├── vectorizer      : TF-IDF or CountVectorizer       (loaded from .pkl)
└── is_initialized  : bool
```

### 5.2 Initialization Flow

```
MLService.initialize()
  │
  ├─ Check MODELS_PATH directory exists
  ├─ Load activity_classifier.pkl  → cls.activity_model
  ├─ Load topic_clusterer.pkl      → cls.topic_model
  ├─ Load vectorizer.pkl           → cls.vectorizer
  └─ If any file missing → log warning, use rule-based fallback
```

### 5.3 Prediction Flow

```
MLService.predict(BrowserEventCreate) → MLPredictionResponse
  │
  ├─ If activity_model AND vectorizer loaded:
  │    └─ _ml_predict(event)
  └─ Else:
       └─ _rule_based_predict(event)
```

### 5.4 ML Prediction (`_ml_predict`)

```
Input features vector = [
    duration_seconds,   # numeric
    hour_of_day,        # numeric (0-23)
    len(title),         # numeric
    len(url)            # numeric
]

activity_probs   = activity_model.predict_proba([features])[0]
activity_label   = class with highest probability
title_vector     = vectorizer.transform([title or domain])
topic_id         = topic_model.predict(title_vector)[0]
topic_name       = TOPIC_MAP[topic_id]
is_learning      = activity_label == "learning"
                   AND activity_probs["learning"] >= LEARNING_THRESHOLD (0.7)
```

### 5.5 Topic ID to Name Mapping

| topic_id | topic_name |
|----------|-----------|
| 0 | Data Structures & Algorithms |
| 1 | Web Development |
| 2 | Machine Learning |
| 3 | System Design |
| 4 | Programming Languages |
| 5 | Other |

### 5.6 Rule-Based Fallback (`_rule_based_predict`)

**Activity classification:**

```
learning_score     = count of learning keywords in (title + domain)
work_score         = count of work keywords in (title + domain)
entertainment_score= count of entertainment keywords in (title + domain)

if learning_score >= work_score AND learning_score >= entertainment_score AND > 0:
    label = "learning",      probs = {learning:0.85, work:0.10, entertainment:0.05}
elif work_score > entertainment_score:
    label = "work",          probs = {learning:0.10, work:0.80, entertainment:0.10}
else:
    label = "entertainment", probs = {learning:0.05, work:0.15, entertainment:0.80}
```

**Keyword lists (abbreviated):**

| Category | Sample Keywords |
|----------|----------------|
| Learning | `tutorial`, `learn`, `docs`, `leetcode`, `algorithm`, `geeksforgeeks`, `stackoverflow` |
| Work | `jira`, `github`, `gitlab`, `jenkins`, `aws`, `slack`, `zoom` |
| Entertainment | `youtube`, `netflix`, `twitter`, `reddit`, `tiktok`, `spotify` |

**Topic classification (rule-based):**

| Condition (keyword in title+domain) | topic_id |
|-------------------------------------|----------|
| `algorithm`, `dsa`, `leetcode`, `tree`, `graph` | 0 — DSA |
| `react`, `html`, `css`, `javascript`, `api`, `frontend` | 1 — Web Dev |
| `machine learning`, `neural`, `tensorflow`, `pytorch` | 2 — ML |
| `system design`, `architecture`, `microservices` | 3 — System Design |
| `python`, `java`, `c++`, `golang`, `rust` | 4 — Programming |
| *(default)* | 5 — Other |

---

## 6. Vector Indexing & Search Design

### 6.1 `VectorService` — Class Design

```
VectorService (static/class methods)
│
├── client          : QdrantClient
├── encoder         : SentenceTransformer("all-MiniLM-L6-v2")
└── is_initialized  : bool
```

### 6.2 Qdrant Collection Configuration

```
Collection name : "focusvault_chunks" (configurable)
Vector size     : 384  (MiniLM-L6-v2 output dimension)
Distance metric : COSINE
```

### 6.3 `IndexingService` — Pipeline

```
IndexingService.index_page(url, user_id, topic_id)
  │
  ├─ fetch_page_content(url)
  │    ├─ HTTP GET (httpx, timeout=10s, follow_redirects=True)
  │    ├─ Parse HTML with BeautifulSoup (lxml)
  │    ├─ Remove: <script>, <style>, <nav>, <footer>, <header>, <aside>
  │    ├─ Extract: <article> > <main> > .content > body (priority order)
  │    └─ Normalize whitespace → return plain text string
  │
  ├─ chunk_text(content)
  │    ├─ Split text into words
  │    ├─ If word count ≤ CHUNK_SIZE (512) → return [full_text]
  │    └─ Sliding window:
  │         start = 0
  │         end   = start + CHUNK_SIZE (512)
  │         chunk = words[start:end]
  │         next start = end - CHUNK_OVERLAP (50)   ← overlap ensures context continuity
  │         repeat until start ≥ len(words)
  │
  └─ VectorService.add_chunks(chunks, user_id, topic_id, url)
       ├─ encoder.encode(chunks) → embeddings (N × 384 float32)
       └─ For each (chunk, embedding):
            point = PointStruct(
                id      = uuid4(),
                vector  = embedding.tolist(),
                payload = {
                    user_id    : int,
                    topic_id   : int,
                    url        : str,
                    chunk_text : str,
                    chunk_index: int
                }
            )
       └─ client.upsert(collection, points)
```

### 6.4 Semantic Search

```
VectorService.search(query, user_id, top_k=5, topic_id=None)
  │
  ├─ query_vector = encoder.encode(query).tolist()          # 384-dim
  ├─ filter = { must: [ {user_id == user_id} ] }
  │            + optional {topic_id == topic_id}
  └─ results = client.search(collection, query_vector, filter, limit=top_k)
       └─ Return list of { text, url, topic_id, score, metadata }
```

---

## 7. RAG (Retrieval-Augmented Generation) Pipeline

### 7.1 `RAGService` — Flow

```
RAGService.answer_question(question, user_id, top_k=5)
  │
  ├─ VectorService.search(question, user_id, top_k)    → contexts[]
  │
  ├─ If contexts empty:
  │    └─ Return "No relevant information found" response (confidence=0.0)
  │
  ├─ _generate_answer(question, contexts)
  │    ├─ If GEMINI_API_KEY configured:
  │    │    ├─ Construct prompt:
  │    │    │    "You are a helpful AI assistant..."
  │    │    │    "Context: [Source 1] ... [Source N]"
  │    │    │    "Question: ..."
  │    │    │    "Answer ONLY from context; cite sources"
  │    │    ├─ model.generate_content(prompt)
  │    │    └─ Return response.text
  │    └─ Else (no API key):
  │         └─ _fallback_answer(): return first context's text[:500] + URL
  │
  ├─ Build RAGContext list:
  │    context.text = ctx["text"][:200] + "..."   (truncated for display)
  │    context.score = cosine similarity score
  │
  └─ confidence = mean(scores)
     Return RAGQueryResponse { question, answer, contexts, confidence }
```

### 7.2 Gemini Prompt Template

```
You are a helpful AI assistant that answers questions based ONLY on the user's learning history.

Context from user's studied pages:
[Source 1]: <chunk_text>
[Source 2]: <chunk_text>
...

Question: <user_question>

Instructions:
- Answer the question using ONLY the information from the context above
- If the context doesn't contain enough information, say so
- Be concise and clear
- Cite which source(s) you used (e.g., "According to Source 1...")

Answer:
```

---

## 8. Flashcard Service Design

### 8.1 `FlashcardService` — Daily Generation Flow

```
FlashcardService.generate_daily_flashcards(user_id, date, db)
  │
  ├─ Resolve target date (default: yesterday)
  ├─ Query BrowserEvent WHERE user_id=X AND activity_label="learning"
  │         AND created_at IN [start_of_day, end_of_day)
  ├─ Take top 5 learning events
  │
  └─ For each event:
       ├─ _generate_flashcard_from_event(event)
       │    ├─ If GEMINI_API_KEY:
       │    │    ├─ Prompt Gemini: generate 2 Q&A pairs from title/topic/url
       │    │    └─ Parse response: lines starting with Q/A
       │    └─ Else: _generate_simple_flashcard(event)
       │         └─ { question: "What did you learn about {topic}?",
       │               answer: "Review: {title}" }
       │
       ├─ For each Q&A pair:
       │    ├─ quality_score = _score_flashcard_quality(question, answer)
       │    └─ If quality_score >= FLASHCARD_QUALITY_THRESHOLD (0.7):
       │         └─ Persist Flashcard to DB; schedule next_review_at = now + 1 day
       │
       └─ db.commit() after all flashcards for the batch
```

### 8.2 Flashcard Quality Scoring Algorithm

```
_score_flashcard_quality(question, answer) → float [0.0, 1.0]

Base score = 0.5

+0.15  if 20 ≤ len(question) ≤ 200     (appropriate question length)
+0.15  if 10 ≤ len(answer) ≤ 500       (appropriate answer length)
+0.10  if '?' in question               (proper question format)
+0.10  if question contains any of:
         ['what', 'how', 'why', 'explain', 'describe']

Max = min(sum, 1.0)
Threshold for inclusion = 0.7
```

### 8.3 Spaced Repetition Schedule

```
review_flashcard(flashcard_id, difficulty)
  │
  ├─ "easy"   → next_review_at = now + 7 days
  ├─ "medium" → next_review_at = now + 3 days
  └─ "hard"   → next_review_at = now + 1 day

Also increments: review_count += 1
Sets: difficulty_last = difficulty
```

---

## 9. Database Schema

### 9.1 `users` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, INDEX | Auto-increment user ID |
| `name` | VARCHAR(100) | NOT NULL | Display name |
| `email` | VARCHAR(255) | UNIQUE, INDEX | User email |
| `created_at` | TIMESTAMP | DEFAULT NOW | Account creation time |

**Relationships:**
- One-to-many → `browser_events` (via `user_id`)
- One-to-many → `flashcards` (via `user_id`)

---

### 9.2 `browser_events` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Auto-increment event ID |
| `user_id` | INTEGER | FK → users.id, NOT NULL | Owning user |
| `url` | TEXT | NOT NULL | Full page URL |
| `title` | TEXT | | Page title |
| `domain` | VARCHAR(100) | INDEX | Hostname |
| `duration_seconds` | INTEGER | | Time spent on page |
| `hour_of_day` | INTEGER | | Hour when event occurred (0-23) |
| `activity_label` | VARCHAR(20) | INDEX | `"learning"` / `"work"` / `"entertainment"` |
| `activity_probs` | JSON | | `{learning: 0.85, work: 0.10, entertainment: 0.05}` |
| `topic_id` | INTEGER | INDEX | Topic cluster ID (0-5) |
| `topic_name` | VARCHAR(100) | | Human-readable topic name |
| `is_saved_to_kb` | BOOLEAN | DEFAULT FALSE | Whether page was indexed to Qdrant |
| `created_at` | TIMESTAMP | DEFAULT NOW, INDEX | Event timestamp |

---

### 9.3 `flashcards` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Auto-increment card ID |
| `user_id` | INTEGER | FK → users.id, NOT NULL | Owning user |
| `question` | TEXT | NOT NULL | Flashcard question |
| `answer` | TEXT | NOT NULL | Flashcard answer |
| `quality_score` | FLOAT | | ML quality score (0.0–1.0) |
| `next_review_at` | TIMESTAMP | | Scheduled next review time |
| `difficulty_last` | VARCHAR(10) | | Last review difficulty (`easy`/`medium`/`hard`) |
| `review_count` | INTEGER | DEFAULT 0 | Times reviewed |
| `source_url` | TEXT | | Origin page URL |
| `created_at` | TIMESTAMP | DEFAULT NOW | Card creation time |

---

### 9.4 `topics` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Topic cluster ID |
| `name` | VARCHAR(100) | UNIQUE, NOT NULL | Topic display name |
| `description` | TEXT | | Topic description |
| `created_at` | TIMESTAMP | DEFAULT NOW | Record creation time |

---

### 9.5 Qdrant Point Schema (Vector Store)

Each point stored in the `focusvault_chunks` collection:

```json
{
  "id": "<uuid4>",
  "vector": [0.12, -0.05, ..., 0.34],
  "payload": {
    "user_id":     1,
    "topic_id":    0,
    "url":         "https://example.com/page",
    "chunk_text":  "...250-512 word text chunk...",
    "chunk_index": 0
  }
}
```

---

### 9.6 Entity Relationship Diagram

```
┌──────────┐         ┌──────────────────┐         ┌─────────────┐
│  users   │ 1     N │  browser_events  │         │   topics    │
├──────────┤◄────────├──────────────────┤         ├─────────────┤
│ id  (PK) │         │ id         (PK)  │         │ id     (PK) │
│ name     │         │ user_id    (FK)  │         │ name        │
│ email    │         │ url              │         │ description │
│ created  │         │ title            │         │ created_at  │
└──────────┘         │ domain           │         └─────────────┘
     │               │ duration_seconds │
     │               │ hour_of_day      │
     │               │ activity_label   │
     │               │ activity_probs   │
     │               │ topic_id   ──────┼──► topics.id (logical)
     │               │ topic_name       │
     │               │ is_saved_to_kb   │
     │               │ created_at       │
     │               └──────────────────┘
     │
     │         ┌───────────────┐
     │ 1     N │  flashcards   │
     └────────►├───────────────┤
               │ id       (PK) │
               │ user_id  (FK) │
               │ question      │
               │ answer        │
               │ quality_score │
               │ next_review_at│
               │ difficulty_   │
               │ review_count  │
               │ source_url    │
               │ created_at    │
               └───────────────┘
```

---

## 10. REST API Contract

### 10.1 Events API

#### `POST /api/events/{user_id}` — Track Browsing Event

**Request Body:**
```json
{
  "url": "https://geeksforgeeks.org/binary-search",
  "title": "Binary Search - GeeksforGeeks",
  "domain": "geeksforgeeks.org",
  "duration_seconds": 180,
  "hour_of_day": 14
}
```

**Response `200 OK`:**
```json
{
  "id": 42,
  "user_id": 1,
  "url": "https://geeksforgeeks.org/binary-search",
  "title": "Binary Search - GeeksforGeeks",
  "domain": "geeksforgeeks.org",
  "duration_seconds": 180,
  "hour_of_day": 14,
  "activity_label": "learning",
  "activity_probs": { "learning": 0.85, "work": 0.10, "entertainment": 0.05 },
  "topic_id": 0,
  "topic_name": "Data Structures & Algorithms",
  "is_saved_to_kb": false,
  "created_at": "2025-01-01T14:00:00"
}
```

---

#### `GET /api/events/{user_id}?skip=0&limit=100`

**Response:** Array of `BrowserEventResponse` objects (ordered by `created_at DESC`)

---

#### `GET /api/events/{user_id}/learning?skip=0&limit=50`

**Response:** Filtered array where `activity_label = "learning"`

---

#### `DELETE /api/events/{event_id}`

**Response `200`:**
```json
{ "message": "Event deleted successfully" }
```
**Response `404`:** Event not found

---

### 10.2 Query API

#### `POST /api/query/`

**Request Body:**
```json
{
  "question": "What is dynamic programming?",
  "user_id": 1,
  "top_k": 5
}
```

**Response `200 OK`:**
```json
{
  "question": "What is dynamic programming?",
  "answer": "Based on your study history, dynamic programming is...",
  "contexts": [
    {
      "text": "Dynamic programming is an algorithmic technique...",
      "url": "https://geeksforgeeks.org/dynamic-programming",
      "topic_name": "Data Structures & Algorithms",
      "score": 0.92
    }
  ],
  "confidence": 0.87
}
```

---

### 10.3 Flashcards API

#### `POST /api/flashcards/generate`

**Request Body:**
```json
{
  "user_id": 1,
  "date": "2025-01-01"
}
```

**Response `200 OK`:**
```json
{
  "message": "Generated 3 flashcards",
  "flashcards": [ /* FlashcardResponse[] */ ]
}
```

---

#### `GET /api/flashcards/{user_id}/due`

**Response:** Array of flashcards where `next_review_at <= now`

---

#### `POST /api/flashcards/{flashcard_id}/review`

**Request Body:**
```json
{ "difficulty": "medium" }
```

**Response `200 OK`:** Updated `FlashcardResponse` with new `next_review_at`

---

#### `DELETE /api/flashcards/{flashcard_id}`

**Response `200`:**
```json
{ "message": "Flashcard deleted successfully" }
```

---

### 10.4 Analytics API

#### `GET /api/analytics/{user_id}/daily?date=2025-01-01`

**Response:**
```json
{
  "date": "2025-01-01",
  "total_events": 25,
  "total_time_seconds": 7200,
  "total_time_minutes": 120,
  "learning_events": 12,
  "learning_time_seconds": 3600,
  "learning_time_minutes": 60,
  "learning_percentage": 50.0,
  "activity_breakdown": {
    "learning": 3600,
    "work": 2400,
    "entertainment": 1200
  },
  "topic_breakdown": {
    "Data Structures & Algorithms": 1800,
    "Web Development": 1200,
    "Machine Learning": 600
  }
}
```

---

#### `GET /api/analytics/{user_id}/weekly`

**Response:**
```json
{
  "start_date": "2024-12-26",
  "end_date": "2025-01-02",
  "daily_stats": {
    "2024-12-26": { "total_time": 3600, "learning_time": 1800, "events": 10 },
    "...": {}
  },
  "total_events": 70,
  "total_time_hours": 14
}
```

---

#### `GET /api/analytics/{user_id}/topics`

**Response:**
```json
{
  "total_topics": 3,
  "topics": [
    {
      "name": "Data Structures & Algorithms",
      "count": 20,
      "total_time": 7200,
      "pages": [
        { "title": "...", "url": "...", "duration": 300 }
      ]
    }
  ]
}
```

---

#### `GET /api/analytics/{user_id}/summary`

**Response:**
```json
{
  "user_id": 1,
  "total_events": 200,
  "learning_events": 80,
  "total_time_hours": 40,
  "learning_time_hours": 16,
  "learning_percentage": 40.0
}
```

---

## 11. Sequence Diagrams

### 11.1 Browsing Event Tracking

```
Extension         Backend              MLService         IndexingService     VectorService
   │                  │                    │                   │                  │
   │──POST /events/1──►│                   │                   │                  │
   │                  │──predict(event)───►│                   │                  │
   │                  │                   │──[if model loaded]─►                  │
   │                  │                   │   feature extract  │                  │
   │                  │                   │   predict_proba()  │                  │
   │                  │◄──MLPrediction─────│                   │                  │
   │                  │                   │                   │                  │
   │                  │──persist BrowserEvent to PostgreSQL    │                  │
   │                  │                   │                   │                  │
   │                  │──[if is_learning]──────────────────────►                  │
   │                  │                   │  queue_page_for_indexing(url)         │
   │                  │                   │                   │──fetch_page()─────►
   │                  │                   │                   │  parse HTML       │
   │                  │                   │                   │  chunk_text()     │
   │                  │                   │                   │──add_chunks()─────►
   │                  │                   │                   │              encode + upsert
   │◄──200 BrowserEventResponse──────────│                   │                  │
```

### 11.2 RAG Query Flow

```
User (Frontend)        Backend (QueryRouter)    RAGService       VectorService     Gemini API
      │                        │                    │                 │                │
      │──POST /api/query/──────►│                   │                 │                │
      │                        │──answer_question───►                 │                │
      │                        │                    │──search(query)──►               │
      │                        │                    │   encode query   │               │
      │                        │                    │   qdrant.search()│               │
      │                        │                    │◄─ top-K chunks ──│               │
      │                        │                    │                  │               │
      │                        │                    │──[GEMINI_KEY set]────────────────►
      │                        │                    │  build prompt    │               │
      │                        │                    │  generate_content│               │
      │                        │                    │◄─ answer text ───────────────────│
      │                        │◄── RAGQueryResponse─│                 │               │
      │◄──200 JSON─────────────│                    │                 │               │
```

### 11.3 Flashcard Generation Flow

```
Frontend/Scheduler     Backend              FlashcardService     Gemini API    PostgreSQL
       │                   │                      │                  │              │
       │──POST /generate───►│                     │                  │              │
       │                   │──generate_daily──────►                  │              │
       │                   │                      │──query learning events──────────►
       │                   │                      │◄─ events[] ──────────────────────│
       │                   │                      │                  │              │
       │                   │                      │──[for each event]│              │
       │                   │                      │──generate prompt─►              │
       │                   │                      │◄─ Q&A pairs ─────│              │
       │                   │                      │                  │              │
       │                   │                      │──score_quality() │              │
       │                   │                      │──[score >= 0.7]──────────────────►
       │                   │                      │  INSERT Flashcard│              │
       │                   │                      │◄─ saved flashcard────────────────│
       │                   │◄── response ──────────│                 │              │
       │◄──200 JSON────────│                      │                  │              │
```

### 11.4 Flashcard Review (Spaced Repetition)

```
User (Frontend)        Backend (FlashcardRouter)        PostgreSQL
      │                          │                           │
      │──POST /{id}/review───────►│                          │
      │   { difficulty: "hard" }  │                          │
      │                          │──look up Flashcard by id──►
      │                          │◄─ flashcard object ────────│
      │                          │                           │
      │                          │  intervals = {easy:7, medium:3, hard:1}
      │                          │  next_review_at = now + 1 day
      │                          │  difficulty_last = "hard"
      │                          │  review_count += 1
      │                          │──UPDATE flashcard──────────►
      │◄──200 FlashcardResponse──│◄─ updated record───────────│
```

---

## 12. Frontend — Component Design

### 12.1 Application Structure

```
App.jsx  (React Router)
│
├── /             → Dashboard.jsx
├── /events       → Events.jsx
├── /query        → Query.jsx
└── /flashcards   → Flashcards.jsx

src/api/           → Axios/fetch API client functions
src/index.css      → Tailwind CSS entry
```

### 12.2 Page Components

| Page | File | Key State | API Calls |
|------|------|-----------|-----------|
| Dashboard | `Dashboard.jsx` | `summary`, `dailyStats`, `topics`, `weeklyData` | `GET /analytics/summary`, `GET /analytics/daily`, `GET /analytics/topics`, `GET /analytics/weekly` |
| Events | `Events.jsx` | `events[]`, `filter` (all/learning) | `GET /events/{userId}`, `GET /events/{userId}/learning` |
| Query | `Query.jsx` | `question`, `answer`, `contexts[]`, `loading` | `POST /query/` |
| Flashcards | `Flashcards.jsx` | `dueCards[]`, `currentCard`, `showAnswer` | `GET /flashcards/{userId}/due`, `POST /flashcards/{id}/review`, `POST /flashcards/generate` |

### 12.3 API Client (`src/api/`)

Thin wrapper around `fetch`/Axios:
- Base URL read from `import.meta.env.VITE_API_URL` (default `http://localhost:8000/api`)
- All functions are `async` / return JSON
- Error responses re-thrown as Error objects for component error boundaries

---

## 13. Configuration & Environment Design

### 13.1 Backend `.env` Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://focusvault:password@localhost:5432/focusvault_db` | PostgreSQL DSN |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `focusvault_chunks` | Qdrant collection name |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |
| `MODELS_PATH` | `./models` | Directory for `.pkl` ML model files |
| `LEARNING_THRESHOLD` | `0.7` | Min probability to classify as learning |
| `FLASHCARD_QUALITY_THRESHOLD` | `0.7` | Min quality score to save a flashcard |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace model ID |
| `VECTOR_DIM` | `384` | Embedding vector dimension |
| `CHUNK_SIZE` | `512` | Words per text chunk |
| `CHUNK_OVERLAP` | `50` | Words of overlap between chunks |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `DEBUG` | `true` | Enable FastAPI debug mode |

### 13.2 Frontend `.env` Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000/api` | Backend API base URL |

### 13.3 Chrome Extension Storage Keys

| Key | Type | Description |
|-----|------|-------------|
| `isTracking` | boolean | Global tracking on/off |
| `userId` | number | Configured user ID |
| `apiUrl` | string | Backend base URL |
| `lastSync` | number (ms) | Timestamp of last successful event sync |
| `lastEvent` | object | Last successfully tracked event |
| `offlineQueue` | array | Buffered events pending sync |

---

## 14. Error Handling Strategy

### 14.1 Backend

| Layer | Strategy |
|-------|----------|
| ML Service | Catch-all → fall back to rule-based classification; log warning |
| Indexing Service | Catch per-URL → log error; do not fail event creation |
| Vector Service | Catch per-operation → return 0 chunks / empty search results |
| RAG Service | Catch Gemini API errors → fallback to context excerpt |
| Flashcard Service | Catch per-event → continue to next event; partial success |
| API Routes | `HTTPException(404)` for missing resources; `HTTPException(500)` with detail for service errors |

### 14.2 Chrome Extension

| Scenario | Strategy |
|----------|----------|
| Backend unreachable | Queue event in `offlineQueue`; retry on next alarm |
| Queue overflow (>100) | FIFO eviction of oldest event |
| Extension suspended | `onSuspend` listener saves current tab data |
| Chrome internal URL | Skip tracking for `chrome://` and `chrome-extension://` URLs |

### 14.3 Frontend

| Scenario | Strategy |
|----------|----------|
| API failure | Show error message in component; no global crash |
| Empty data | Render empty-state UI (no data available messages) |

---

## 15. Deployment Architecture

### 15.1 Docker Compose Services

```
docker-compose.yml
│
├── backend
│    ├── Image: python:3.11-slim (Dockerfile)
│    ├── Port: 8000
│    ├── Volumes: ./models → /app/models
│    └── Depends: postgres, qdrant
│
├── frontend
│    ├── Image: node:18 (Dockerfile)
│    ├── Port: 3000
│    └── Depends: backend
│
├── postgres
│    ├── Image: postgres:15-alpine
│    ├── Port: 5432
│    └── Volume: postgres_data
│
└── qdrant
     ├── Image: qdrant/qdrant
     ├── Ports: 6333 (HTTP), 6334 (gRPC)
     └── Volume: qdrant_storage
```

### 15.2 Backend Startup Sequence

```
FastAPI lifespan (startup)
  │
  ├─ Base.metadata.create_all(engine)   → auto-create all SQL tables
  ├─ MLService.initialize()             → load .pkl models
  └─ VectorService.initialize()         → connect Qdrant; create collection; load encoder

FastAPI lifespan (shutdown)
  └─ VectorService.close()             → close Qdrant connection
```

### 15.3 Port Map

| Service | Internal Port | External Port |
|---------|--------------|---------------|
| Backend (FastAPI) | 8000 | 8000 |
| Frontend (React) | 3000 | 3000 |
| PostgreSQL | 5432 | 5432 |
| Qdrant HTTP | 6333 | 6333 |
| Qdrant gRPC | 6334 | 6334 |

---

*Document generated for FocusVault v1.0.0 — B.Tech Final Year Project*
