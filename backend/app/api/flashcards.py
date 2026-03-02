from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import Flashcard
from app.schemas.flashcard import (
    FlashcardCreate, 
    FlashcardResponse, 
    FlashcardReview,
    FlashcardGenerateRequest
)
from app.services.flashcard_service import FlashcardService

router = APIRouter()


@router.post("/generate")
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    db: Session = Depends(get_db)
):
    try:
        flashcards = await FlashcardService.generate_daily_flashcards(
            user_id=request.user_id,
            date=request.date,
            db=db
        )
        
        return {
            "message": f"Generated {len(flashcards)} flashcards",
            "flashcards": flashcards
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/{user_id}/due", response_model=List[FlashcardResponse])
async def get_due_flashcards(
    user_id: int,
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    
    flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.next_review_at <= now
    ).order_by(Flashcard.next_review_at).all()
    
    return flashcards


@router.get("/{user_id}", response_model=List[FlashcardResponse])
async def get_user_flashcards(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id
    ).order_by(
        Flashcard.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return flashcards


@router.post("/{flashcard_id}/review")
async def review_flashcard(
    flashcard_id: int,
    review: FlashcardReview,
    db: Session = Depends(get_db)
):
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    intervals = {
        "easy": 7,
        "medium": 3,
        "hard": 1
    }
    
    days = intervals.get(review.difficulty.lower(), 3)
    flashcard.next_review_at = datetime.utcnow() + timedelta(days=days)
    flashcard.difficulty_last = review.difficulty
    flashcard.review_count += 1
    
    db.commit()
    db.refresh(flashcard)
    
    return flashcard


@router.post("/", response_model=FlashcardResponse)
async def create_flashcard(
    user_id: int,
    flashcard: FlashcardCreate,
    db: Session = Depends(get_db)
):
    db_flashcard = Flashcard(
        user_id=user_id,
        question=flashcard.question,
        answer=flashcard.answer,
        source_url=flashcard.source_url,
        next_review_at=datetime.utcnow() + timedelta(days=1)
    )
    
    db.add(db_flashcard)
    db.commit()
    db.refresh(db_flashcard)
    
    return db_flashcard


@router.delete("/{flashcard_id}")
async def delete_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db)
):
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db.delete(flashcard)
    db.commit()
    
    return {"message": "Flashcard deleted successfully"}
