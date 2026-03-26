from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
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
from app.api.events import _memory_events, get_optional_db

router = APIRouter()

# ── Topic-based question templates ───────────────────────────────
_TOPIC_QUESTIONS = {
    "dsa": [
        "What is the time complexity of this approach?",
        "Can you explain the algorithm used on this page?",
        "What data structure is most suitable for this problem?",
    ],
    "sql": [
        "What SQL concept was covered on this page?",
        "How would you optimise this query?",
        "What is the difference between JOIN types discussed here?",
    ],
    "ai tools": [
        "How can this AI tool improve your workflow?",
        "What prompt technique was discussed here?",
    ],
    "career": [
        "What career advice was shared on this page?",
        "What skills were highlighted as important?",
    ],
    "web development": [
        "What web technology was covered on this page?",
        "How does this concept improve user experience?",
    ],
    "programming": [
        "What programming concept was discussed here?",
        "How would you apply this in a real project?",
    ],
}

_DEFAULT_QUESTIONS = [
    "What key concept did you learn from this page?",
    "Summarise what this page was about in your own words.",
    "How would you explain this topic to someone else?",
]


def _make_flashcards_from_events(learning_events: list) -> list:
    """Generate flashcard dicts from learning event dicts."""
    cards = []
    card_id = 1
    for evt in learning_events:
        title = evt.get("title", "Unknown")
        domain = evt.get("domain", "")
        topic = evt.get("topic_name", "General Learning")
        url = evt.get("url", "")

        # Pick a topic-specific question or fall back to default
        topic_lower = topic.lower()
        questions = _TOPIC_QUESTIONS.get(topic_lower, _DEFAULT_QUESTIONS)

        for q_template in questions[:2]:  # max 2 cards per event
            cards.append({
                "id": card_id,
                "question": q_template,
                "answer": f"{title} — {topic} (source: {domain})",
                "topic": topic,
                "source_url": url,
                "domain": domain,
                "title": title,
            })
            card_id += 1
    return cards


@router.get("/{user_id}/from-events")
async def get_flashcards_from_events(
    user_id: int,
    db: Optional[Session] = Depends(get_optional_db),
):
    """Generate flashcards on-the-fly from in-memory learning events."""
    if db is not None:
        from app.db.models import BrowserEvent
        events = db.query(BrowserEvent).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.activity_label == "learning",
        ).order_by(BrowserEvent.created_at.desc()).limit(20).all()
        event_dicts = [
            {
                "title": e.title,
                "domain": e.domain,
                "topic_name": e.topic_name,
                "url": e.url,
            }
            for e in events
        ]
    else:
        event_dicts = [
            e for e in _memory_events
            if e.get("user_id") == user_id and e.get("activity_label") == "learning"
        ]

    if not event_dicts:
        return []

    return _make_flashcards_from_events(event_dicts)


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
