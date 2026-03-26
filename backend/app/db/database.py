from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

def _build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine = _build_engine(settings.DATABASE_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    ACTIVE_DATABASE_URL = settings.DATABASE_URL
except Exception as primary_error:
    print(
        "Primary database unavailable; using SQLite fallback. "
        f"Reason: {primary_error.__class__.__name__}: {primary_error}"
    )
    engine = _build_engine(settings.SQLITE_FALLBACK_URL)
    ACTIVE_DATABASE_URL = settings.SQLITE_FALLBACK_URL

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
