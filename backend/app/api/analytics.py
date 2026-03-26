from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_db
from app.db.models import BrowserEvent

router = APIRouter()


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


def _get_memory_events(user_id):
    """Get events from in-memory store when DB is down."""
    from app.api.events import _memory_events
    return [e for e in _memory_events if e["user_id"] == user_id]


@router.get("/{user_id}/daily")
async def get_daily_analytics(
    user_id: int,
    date: Optional[str] = None,
    db: Optional[Session] = Depends(get_optional_db)
):
    if date:
        target_date = datetime.fromisoformat(date)
    else:
        target_date = datetime.utcnow()

    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    if db is None:
        all_events = _get_memory_events(user_id)
        events = []
        for e in all_events:
            ts = datetime.fromisoformat(e["created_at"])
            if start_of_day <= ts < end_of_day:
                events.append(e)
    else:
        events = db.query(BrowserEvent).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.created_at >= start_of_day,
            BrowserEvent.created_at < end_of_day
        ).all()

    total_events = len(events)
    total_time = sum(e["duration_seconds"] if isinstance(e, dict) else e.duration_seconds for e in events)

    learning_events = [
        e for e in events
        if (e["activity_label"] if isinstance(e, dict) else e.activity_label) == "learning"
    ]
    learning_time = sum(e["duration_seconds"] if isinstance(e, dict) else e.duration_seconds for e in learning_events)

    activity_breakdown = {}
    for event in events:
        label = (event["activity_label"] if isinstance(event, dict) else event.activity_label) or "unknown"
        dur = event["duration_seconds"] if isinstance(event, dict) else event.duration_seconds
        activity_breakdown[label] = activity_breakdown.get(label, 0) + dur

    topic_breakdown = {}
    for event in learning_events:
        topic = (event["topic_name"] if isinstance(event, dict) else event.topic_name) or "Other"
        dur = event["duration_seconds"] if isinstance(event, dict) else event.duration_seconds
        topic_breakdown[topic] = topic_breakdown.get(topic, 0) + dur

    return {
        "date": target_date.date().isoformat(),
        "total_events": total_events,
        "total_time_seconds": total_time,
        "total_time_minutes": total_time // 60,
        "learning_events": len(learning_events),
        "learning_time_seconds": learning_time,
        "learning_time_minutes": learning_time // 60,
        "learning_percentage": round((learning_time / total_time * 100) if total_time > 0 else 0, 2),
        "activity_breakdown": activity_breakdown,
        "topic_breakdown": topic_breakdown
    }


@router.get("/{user_id}/weekly")
async def get_weekly_analytics(
    user_id: int,
    db: Optional[Session] = Depends(get_optional_db)
):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    if db is None:
        all_events = _get_memory_events(user_id)
        events = []
        for e in all_events:
            ts = datetime.fromisoformat(e["created_at"])
            if start_date <= ts < end_date:
                events.append(e)
    else:
        events = db.query(BrowserEvent).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.created_at >= start_date,
            BrowserEvent.created_at < end_date
        ).all()

    daily_stats = {}
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_key = day.date().isoformat()
        daily_stats[day_key] = {
            "total_time": 0,
            "learning_time": 0,
            "events": 0
        }

    for event in events:
        if isinstance(event, dict):
            day_key = datetime.fromisoformat(event["created_at"]).date().isoformat()
            dur = event["duration_seconds"]
            label = event["activity_label"]
        else:
            day_key = event.created_at.date().isoformat()
            dur = event.duration_seconds
            label = event.activity_label
        if day_key in daily_stats:
            daily_stats[day_key]["total_time"] += dur
            daily_stats[day_key]["events"] += 1
            if label == "learning":
                daily_stats[day_key]["learning_time"] += dur

    total_time = sum(
        e["duration_seconds"] if isinstance(e, dict) else e.duration_seconds for e in events
    )
    return {
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "daily_stats": daily_stats,
        "total_events": len(events),
        "total_time_hours": total_time // 3600
    }


@router.get("/{user_id}/topics")
async def get_topic_analytics(
    user_id: int,
    db: Optional[Session] = Depends(get_optional_db)
):
    if db is None:
        all_events = _get_memory_events(user_id)
        events = [e for e in all_events if e["activity_label"] == "learning"]
    else:
        events = db.query(BrowserEvent).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.activity_label == "learning"
        ).all()

    topics = {}
    for event in events:
        if isinstance(event, dict):
            topic = event["topic_name"] or "Other"
            dur = event["duration_seconds"]
            title = event["title"]
            url = event["url"]
        else:
            topic = event.topic_name or "Other"
            dur = event.duration_seconds
            title = event.title
            url = event.url

        if topic not in topics:
            topics[topic] = {"name": topic, "count": 0, "total_time": 0, "pages": []}
        topics[topic]["count"] += 1
        topics[topic]["total_time"] += dur
        if len(topics[topic]["pages"]) < 5:
            topics[topic]["pages"].append({"title": title, "url": url, "duration": dur})

    sorted_topics = sorted(topics.values(), key=lambda x: x["total_time"], reverse=True)
    return {"total_topics": len(topics), "topics": sorted_topics}


@router.get("/{user_id}/summary")
async def get_user_summary(
    user_id: int,
    db: Optional[Session] = Depends(get_optional_db)
):
    if db is None:
        all_events = _get_memory_events(user_id)
        total_events = len(all_events)
        learning_events = len([e for e in all_events if e["activity_label"] == "learning"])
        total_time = sum(e["duration_seconds"] for e in all_events)
        learning_time = sum(e["duration_seconds"] for e in all_events if e["activity_label"] == "learning")
    else:
        total_events = db.query(func.count(BrowserEvent.id)).filter(
            BrowserEvent.user_id == user_id
        ).scalar()
        learning_events = db.query(func.count(BrowserEvent.id)).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.activity_label == "learning"
        ).scalar()
        total_time = db.query(func.sum(BrowserEvent.duration_seconds)).filter(
            BrowserEvent.user_id == user_id
        ).scalar() or 0
        learning_time = db.query(func.sum(BrowserEvent.duration_seconds)).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.activity_label == "learning"
        ).scalar() or 0

    return {
        "user_id": user_id,
        "total_events": total_events,
        "learning_events": learning_events,
        "total_time_hours": total_time // 3600,
        "learning_time_hours": learning_time // 3600,
        "learning_percentage": round((learning_time / total_time * 100) if total_time > 0 else 0, 2)
    }
