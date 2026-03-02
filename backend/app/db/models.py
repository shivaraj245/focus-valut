from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    events = relationship("BrowserEvent", back_populates="user")
    flashcards = relationship("Flashcard", back_populates="user")


class BrowserEvent(Base):
    __tablename__ = "browser_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text)
    domain = Column(String(100), index=True)
    duration_seconds = Column(Integer)
    hour_of_day = Column(Integer)
    activity_label = Column(String(20), index=True)
    activity_probs = Column(JSON)
    topic_id = Column(Integer, index=True)
    topic_name = Column(String(100))
    is_saved_to_kb = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="events")


class Flashcard(Base):
    __tablename__ = "flashcards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    quality_score = Column(Float)
    next_review_at = Column(DateTime)
    difficulty_last = Column(String(10))
    review_count = Column(Integer, default=0)
    source_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="flashcards")


class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
