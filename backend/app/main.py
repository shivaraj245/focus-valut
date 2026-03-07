from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import events, query, flashcards, analytics
from app.api.ml import router as ml_router
from app.core.config import settings
from app.db.database import engine, Base
from app.services.ml_service import MLService
from app.services.vector_service import VectorService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PostgreSQL — optional, ML endpoints work without it
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database connected")
    except Exception as e:
        print(f"⚠️  Database unavailable (ML-only mode): {e.__class__.__name__}: {e}")

    # ML models — always load
    await MLService.initialize()

    # Qdrant — optional, RAG endpoints need it
    try:
        await VectorService.initialize()
    except Exception as e:
        print(f"⚠️  Qdrant unavailable (RAG disabled): {e.__class__.__name__}: {e}")

    yield

    try:
        await VectorService.close()
    except Exception:
        pass


app = FastAPI(
    title="FocusVault API",
    description="AI-Powered Learning Memory & Focus Tracker",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(query.router, prefix="/api/query", tags=["RAG Query"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ml_router)


@app.get("/")
async def root():
    return {
        "message": "FocusVault API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ml_service": MLService.is_ready(),
        "vector_db": await VectorService.health_check()
    }
