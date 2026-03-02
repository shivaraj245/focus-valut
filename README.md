# FocusVault: AI-Powered Learning Memory & Focus Tracker

[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-005571)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-00D2FF)](https://qdrant.tech)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB)](https://react.dev)

**Final Year B.Tech CS Project | Team Size: 3 Members**

Tracks learning activity → builds a **personal knowledge vault** → enables **RAG-based Q&A** strictly from **your own learning pages**.

## 🎯 Quick Demo Flow

```text
1. Chrome Extension tracks GFG reading (20 mins)
2. ML Classifier → Learning (92%), Topic: DSA
3. Page indexed into Qdrant vector store
4. Query: "What is DP?" → Answer from your study history
5. Auto-generated flashcards → ML quality filtering
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Chrome Browser

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd focusvault

# Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and add your Gemini API key (optional)

# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps
```

**Access Points:**
- Backend API: http://localhost:8000/docs
- Frontend Dashboard: http://localhost:3000
- Qdrant Dashboard: http://localhost:6333/dashboard

### Option 2: Local Development

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start PostgreSQL and Qdrant (using Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_USER=focusvault -e POSTGRES_DB=focusvault_db postgres:15-alpine
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Run the backend
uvicorn app.main:app --reload
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

#### 3. Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension` folder
5. Pin the extension to toolbar

## 📁 Project Structure

```
focusvault/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration
│   │   ├── db/             # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI app
│   ├── models/             # ML models (.pkl files)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React Dashboard
│   ├── src/
│   ├── public/
│   └── package.json
├── extension/              # Chrome Extension
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
├── models/                 # Trained ML models
├── docker-compose.yml
└── README.md
```

## 🛠 Tech Stack

| Component  | Technology                          |
|------------|-------------------------------------|
| Extension  | Chrome Manifest V3, JavaScript      |
| Backend    | FastAPI, Python 3.11                |
| Database   | PostgreSQL 15                       |
| Vector DB  | Qdrant                              |
| ML Models  | scikit-learn, LightGBM              |
| Embeddings | sentence-transformers (MiniLM)      |
| LLM        | Google Gemini API                   |
| Frontend   | React, Tailwind CSS                 |

## 🎓 Features

### ✅ Implemented

- **Chrome Extension**: Automatic browsing activity tracking
- **ML Classification**: Activity type (learning/work/entertainment)
- **Topic Clustering**: Auto-categorize learning content
- **Vector Search**: Semantic search over your learning pages
- **RAG Q&A**: Ask questions about what you've learned
- **Flashcard Generation**: AI-powered flashcards with quality filtering
- **Analytics Dashboard**: Learning time, topics, activity breakdown
- **Offline Support**: Extension queues events when backend is down

### 🚧 In Progress

- Spaced repetition algorithm refinement
- Advanced topic modeling
- Multi-user authentication

## 📊 API Endpoints

### Events
- `POST /api/events/{user_id}` - Track browsing event
- `GET /api/events/{user_id}` - Get user events
- `GET /api/events/{user_id}/learning` - Get learning events only

### RAG Query
- `POST /api/query/` - Ask questions about learned content

### Flashcards
- `POST /api/flashcards/generate` - Generate daily flashcards
- `GET /api/flashcards/{user_id}/due` - Get due flashcards
- `POST /api/flashcards/{flashcard_id}/review` - Review flashcard

### Analytics
- `GET /api/analytics/{user_id}/daily` - Daily stats
- `GET /api/analytics/{user_id}/weekly` - Weekly trends
- `GET /api/analytics/{user_id}/topics` - Topic breakdown
- `GET /api/analytics/{user_id}/summary` - Overall summary

## 🤖 ML Models

### Activity Classifier
- **Input**: Title, duration, hour of day
- **Output**: Probabilities for learning/work/entertainment
- **Target Accuracy**: ≥85%

### Topic Clusterer
- **Input**: Page title (vectorized)
- **Output**: Topic ID (DSA, Web Dev, ML, etc.)
- **Method**: K-Means clustering

### Flashcard Quality Scorer
- **Input**: Question-answer pair
- **Output**: Quality score (0-1)
- **Threshold**: 0.7 for inclusion

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Gemini API (Get from: https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_api_key_here

# ML Models
MODELS_PATH=./models
```

### Extension Settings

1. Click extension icon
2. Click "Settings"
3. Set API URL: `http://localhost:8000/api`
4. Set User ID: `1`

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Check API health
curl http://localhost:8000/health

# Test extension
# Load extension in Chrome and visit learning pages
```

## 📝 Development Workflow

### Adding Your Trained ML Models

```bash
# Place your trained models in the models/ directory
models/
├── activity_classifier.pkl    # Your trained classifier
├── topic_clusterer.pkl        # Your trained clusterer
└── vectorizer.pkl             # TF-IDF or similar vectorizer
```

The backend will automatically load these models on startup. If models are not found, it falls back to rule-based classification.

### Training Models (For Your Teammate)

See the separate `ML_TRAINING.md` guide for:
- Data collection format
- Feature engineering
- Model training scripts
- Evaluation metrics

## 🔒 Privacy & Security

- All data stored locally (PostgreSQL + Qdrant)
- No cloud storage of browsing data
- Optional Gemini API for answer generation only
- Domain whitelist/blacklist support
- Manual "Save to KB" option

## 🐛 Troubleshooting

### Extension not tracking
- Check if tracking is enabled (green dot in popup)
- Verify API URL in extension settings
- Check backend is running: `curl http://localhost:8000/health`

### Backend errors
- Check logs: `docker-compose logs backend`
- Verify database connection
- Ensure Qdrant is running

### RAG not working
- Check if pages are indexed: Visit Qdrant dashboard
- Verify Gemini API key (optional)
- Check vector service initialization in logs

## 📚 Documentation

- [Extension README](extension/README.md) - Chrome extension details
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [Architecture](ARCHITECTURE.md) - System design details

## 👥 Team

- **Member 1**: Chrome Extension + Frontend
- **Member 2**: ML Models + Training Pipeline
- **Member 3**: Backend API + RAG System

## 📄 License

Academic Project - B.Tech Final Year

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- Qdrant for vector database
- Google Gemini for LLM capabilities
- Sentence Transformers for embeddings

---

**Load Extension → Study → Ask → Recall → Retain Forever** 🧠
