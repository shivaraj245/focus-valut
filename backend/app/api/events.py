from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import BrowserEvent, User
from app.schemas.event import BrowserEventCreate, BrowserEventResponse, MLPredictionResponse
from app.services.ml_service import MLService
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.post("/{user_id}", response_model=BrowserEventResponse)
async def create_event(
    user_id: int,
    event: BrowserEventCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, name=f"User {user_id}", email=f"user{user_id}@focusvault.local")
        db.add(user)
        db.commit()
    
    prediction = await MLService.predict(event)
    
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
    
    if prediction.is_learning:
        await IndexingService.queue_page_for_indexing(db_event.id, event.url, user_id)
    
    return db_event


@router.get("/{user_id}", response_model=List[BrowserEventResponse])
async def get_user_events(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    events = db.query(BrowserEvent).filter(
        BrowserEvent.user_id == user_id
    ).order_by(
        BrowserEvent.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return events


@router.get("/{user_id}/learning", response_model=List[BrowserEventResponse])
async def get_learning_events(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
    event = db.query(BrowserEvent).filter(BrowserEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    
    return {"message": "Event deleted successfully"}
