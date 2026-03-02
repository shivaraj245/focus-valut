# FocusVault Setup Guide

Complete setup instructions for your B.Tech final year project.

## 📋 Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Chrome Browser** - For the extension
- **Git** - For version control

## 🚀 Quick Start (Recommended)

### Option 1: Docker (Easiest)

```bash
# 1. Navigate to project directory
cd d:\Projects\antigravity-focus

# 2. Start all services
docker-compose up -d

# 3. Check if everything is running
docker-compose ps

# 4. View logs
docker-compose logs -f backend
```

**Access URLs:**
- Backend API: http://localhost:8000/docs
- Frontend Dashboard: http://localhost:3000
- Qdrant Dashboard: http://localhost:6333/dashboard
- PostgreSQL: localhost:5432

### Option 2: Local Development

#### Step 1: Database Setup

```bash
# Start PostgreSQL
docker run -d \
  --name focusvault_postgres \
  -e POSTGRES_USER=focusvault \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=focusvault_db \
  -p 5432:5432 \
  postgres:15-alpine

# Start Qdrant
docker run -d \
  --name focusvault_qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant
```

#### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# Edit .env and configure (optional: add Gemini API key)

# Run backend
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000

#### Step 3: Frontend Setup

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Copy environment file
copy .env.example .env

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3000

#### Step 4: Chrome Extension Setup

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `extension` folder from your project
5. Pin the extension to your toolbar
6. Click the extension icon and go to Settings
7. Set API URL: `http://localhost:8000/api`
8. Set User ID: `1`

## 🔧 Configuration

### Backend Configuration (.env)

```bash
# Database
DATABASE_URL=postgresql://focusvault:password@localhost:5432/focusvault_db

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Gemini API (Get from: https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_api_key_here

# ML Models
MODELS_PATH=./models
```

### Getting Gemini API Key (Optional but Recommended)

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key and paste it in `.env` file

**Note:** Without Gemini API, RAG will work but use simpler text extraction instead of AI-generated answers.

## 🤖 Adding ML Models

Your teammate training the models should:

1. Train the models using collected data
2. Export as `.pkl` files:
   - `activity_classifier.pkl`
   - `topic_clusterer.pkl`
   - `vectorizer.pkl`
3. Place them in the `models/` directory
4. Restart the backend

**Fallback:** If models are not present, the system uses rule-based classification (works but less accurate).

## ✅ Verification Steps

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "ml_service": true,
  "vector_db": true
}
```

### 2. Test Extension

1. Visit any learning website (e.g., GeeksforGeeks, MDN)
2. Stay on the page for 10+ seconds
3. Click the extension icon
4. Check if the page is being tracked

### 3. Test API

Open http://localhost:8000/docs and try:
- GET `/health` - Check system health
- GET `/api/analytics/1/summary` - Get user summary

### 4. Test Frontend

1. Open http://localhost:3000
2. Navigate through Dashboard, Events, Query, Flashcards
3. Check if data appears (after using extension)

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check if port 8000 is free
netstat -ano | findstr :8000

# View backend logs
docker-compose logs backend
```

### Extension not tracking

1. Check extension popup - is tracking enabled (green dot)?
2. Verify API URL in extension settings
3. Check browser console for errors (F12)
4. Check background script console:
   - Go to `chrome://extensions/`
   - Click "service worker" under FocusVault

### Frontend not loading data

1. Check if backend is running: http://localhost:8000/health
2. Check browser console for CORS errors
3. Verify API URL in frontend/.env

### Qdrant connection issues

```bash
# Check if Qdrant is running
curl http://localhost:6333/health

# Restart Qdrant
docker restart focusvault_qdrant
```

### Database connection issues

```bash
# Check PostgreSQL logs
docker logs focusvault_postgres

# Connect to database
docker exec -it focusvault_postgres psql -U focusvault -d focusvault_db

# List tables
\dt
```

## 📊 Testing the Full Flow

### Complete End-to-End Test

1. **Start Extension Tracking**
   - Load extension in Chrome
   - Verify tracking is enabled (green dot)

2. **Browse Learning Content**
   - Visit GeeksforGeeks article on DSA
   - Stay for 2+ minutes
   - Visit MDN docs on JavaScript
   - Stay for 2+ minutes

3. **Check Dashboard**
   - Open http://localhost:3000
   - Verify events appear in Dashboard
   - Check activity breakdown
   - View learning time

4. **Test RAG Query**
   - Go to "Ask AI" page
   - Ask: "What is a binary search tree?"
   - Check if answer uses your browsing history

5. **Generate Flashcards**
   - Go to "Flashcards" page
   - Click "Generate Flashcards"
   - Review generated cards

## 🔄 Daily Development Workflow

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend
```

## 📦 Production Deployment

### Build for Production

```bash
# Build Docker images
docker-compose build

# Start in production mode
docker-compose up -d

# Check status
docker-compose ps
```

### Environment Variables for Production

Update `.env` with:
- Strong `SECRET_KEY`
- Production database credentials
- Set `DEBUG=False`
- Set `ENVIRONMENT=production`

## 🎓 Project Structure Overview

```
focusvault/
├── extension/          # Chrome Extension (Member 1)
│   ├── manifest.json
│   ├── background.js   # Tracking logic
│   ├── popup.html/js   # Extension UI
│   └── content.js      # Page content extraction
│
├── backend/            # FastAPI Backend (Member 3)
│   ├── app/
│   │   ├── api/        # REST endpoints
│   │   ├── services/   # ML, RAG, Vector services
│   │   ├── db/         # Database models
│   │   └── main.py     # FastAPI app
│   └── requirements.txt
│
├── frontend/           # React Dashboard (Member 1)
│   ├── src/
│   │   ├── pages/      # Dashboard, Events, Query, Flashcards
│   │   └── api/        # API client
│   └── package.json
│
├── models/             # ML Models (Member 2)
│   ├── activity_classifier.pkl
│   ├── topic_clusterer.pkl
│   └── vectorizer.pkl
│
└── docker-compose.yml  # All services orchestration
```

## 👥 Team Member Responsibilities

### Member 1: Extension + Frontend
- Chrome extension development
- React dashboard
- UI/UX design
- Extension testing

### Member 2: ML Models
- Data collection and labeling
- Feature engineering
- Model training (activity, topic)
- Model evaluation and tuning

### Member 3: Backend + RAG
- FastAPI development
- Database design
- RAG pipeline implementation
- Vector database integration
- API documentation

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Chrome Extension Docs](https://developer.chrome.com/docs/extensions/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [React Documentation](https://react.dev/)
- [Gemini API Docs](https://ai.google.dev/docs)

## 🆘 Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review logs: `docker-compose logs`
3. Check GitHub issues (if using version control)
4. Ask your team members
5. Review API documentation: http://localhost:8000/docs

## ✨ Next Steps

After setup:

1. Test the complete flow
2. Collect training data with the extension
3. Train ML models (Member 2)
4. Integrate trained models
5. Test RAG with real queries
6. Generate flashcards
7. Prepare demo for presentation

Good luck with your project! 🚀
