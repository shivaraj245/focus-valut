from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
from datetime import datetime


class BrowserEventCreate(BaseModel):
    url: str
    title: Optional[str] = None
    domain: str
    duration_seconds: int
    hour_of_day: int


class BrowserEventResponse(BaseModel):
    id: int
    user_id: int
    url: str
    title: Optional[str]
    domain: str
    duration_seconds: int
    hour_of_day: int
    activity_label: Optional[str]
    activity_probs: Optional[Dict[str, float]]
    topic_id: Optional[int]
    topic_name: Optional[str]
    is_saved_to_kb: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class MLPredictionResponse(BaseModel):
    activity_label: str
    activity_probs: Dict[str, float]
    topic_id: int
    topic_name: str
    is_learning: bool
