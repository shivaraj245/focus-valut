from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FlashcardCreate(BaseModel):
    question: str
    answer: str
    source_url: Optional[str] = None


class FlashcardResponse(BaseModel):
    id: int
    user_id: int
    question: str
    answer: str
    quality_score: Optional[float]
    next_review_at: Optional[datetime]
    difficulty_last: Optional[str]
    review_count: int
    source_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FlashcardReview(BaseModel):
    difficulty: str


class FlashcardGenerateRequest(BaseModel):
    user_id: int
    date: Optional[str] = None
