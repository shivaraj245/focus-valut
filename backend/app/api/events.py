from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime

from app.db.database import get_db
from app.db.models import BrowserEvent, User
from app.schemas.event import BrowserEventCreate, BrowserEventResponse
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)

router = APIRouter()

# ── In-memory event store for ML-only mode (no DB) ──────────────
_memory_events = []  # list of dicts
_next_id = 1


def get_optional_db():
    """Yields a DB session if available, or None if DB is down."""
    try:
        from sqlalchemy import text
        from app.db.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        try:
            yield db
        finally:
            db.close()
    except Exception:
        yield None


def _url_already_indexed(db: Session, user_id: int, url: str) -> bool:
    return db.query(BrowserEvent.id).filter(
        BrowserEvent.user_id == user_id,
        BrowserEvent.url == url,
        BrowserEvent.is_saved_to_kb.is_(True)
    ).first() is not None


@router.post("/{user_id}")
async def create_event(
    user_id: int,
    event: BrowserEventCreate,
    background_tasks: BackgroundTasks,
    db: Optional[Session] = Depends(get_optional_db)
):
    global _next_id

    # ── ML Classification ────────────────────────────────────────
    prediction = await MLService.predict(event)

    # ── If DB is unavailable, store in memory ────────────────────
    if db is None:
        evt = {
            "id": _next_id,
            "user_id": user_id,
            "url": event.url,
            "title": event.title,
            "domain": event.domain,
            "duration_seconds": event.duration_seconds,
            "hour_of_day": event.hour_of_day,
            "activity_label": prediction.activity_label,
            "activity_probs": prediction.activity_probs,
            "topic_id": prediction.topic_id,
            "topic_name": prediction.topic_name,
            "is_saved_to_kb": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        _memory_events.append(evt)
        _next_id += 1
        return evt

    # ── Ensure user exists ───────────────────────────────────────
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, name=f"User {user_id}", email=f"user{user_id}@focusvault.local")
        db.add(user)
        db.commit()

    # ── Store event ──────────────────────────────────────────────
    db_event = BrowserEvent(
        user_id=user_id,
        url=event.url,
        title=event.title,
        domain=event.domain,
        duration_seconds=event.duration_seconds,
        hour_of_day=event.hour_of_day,
        activity_label=prediction.activity_label,
        activity_probs=prediction.activity_probs,
        topic_id=prediction.topic_id,
        topic_name=prediction.topic_name
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # ── Qdrant indexing (optional — off the request path) ────────
    if prediction.is_learning:
        if _url_already_indexed(db, user_id, event.url):
            db_event.is_saved_to_kb = True
            db.commit()
            db.refresh(db_event)
        else:
            from app.services.indexing_service import IndexingService
            background_tasks.add_task(
                IndexingService.queue_page_for_indexing,
                db_event.id,
                event.url,
                user_id,
                prediction.topic_id,
            )

    return db_event


@router.get("/{user_id}")
async def get_user_events(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Optional[Session] = Depends(get_optional_db)
):
    if db is None:
        # Return from in-memory store
        user_events = [e for e in _memory_events if e["user_id"] == user_id]
        user_events.sort(key=lambda e: e["created_at"], reverse=True)
        return user_events[skip:skip + limit]

    events = db.query(BrowserEvent).filter(
        BrowserEvent.user_id == user_id
    ).order_by(
        BrowserEvent.created_at.desc()
    ).offset(skip).limit(limit).all()
    return events


@router.get("/{user_id}/learning")
async def get_learning_events(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Optional[Session] = Depends(get_optional_db)
):
    if db is None:
        user_events = [
            e for e in _memory_events
            if e["user_id"] == user_id and e["activity_label"] == "learning"
        ]
        user_events.sort(key=lambda e: e["created_at"], reverse=True)
        return user_events[skip:skip + limit]

    events = db.query(BrowserEvent).filter(
        BrowserEvent.user_id == user_id,
        BrowserEvent.activity_label == "learning"
    ).order_by(
        BrowserEvent.created_at.desc()
    ).offset(skip).limit(limit).all()
    return events


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    db: Optional[Session] = Depends(get_optional_db)
):
    if db is None:
        global _memory_events
        before = len(_memory_events)
        _memory_events = [e for e in _memory_events if e["id"] != event_id]
        if len(_memory_events) == before:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}

    event = db.query(BrowserEvent).filter(BrowserEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"message": "Event deleted successfully"}