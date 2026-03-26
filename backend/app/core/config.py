from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://focusvault:password@localhost:5432/focusvault_db"
    SQLITE_FALLBACK_URL: str = "sqlite:///./focusvault_local.db"
    
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "focusvault_chunks"
    QDRANT_LOCAL_PATH: str = "./qdrant_local"
    
    GEMINI_API_KEY: str = ""
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    MODELS_PATH: str = "./models"
    
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_DIM: int = 384
    
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    
    LEARNING_THRESHOLD: float = 0.7
    FLASHCARD_QUALITY_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
