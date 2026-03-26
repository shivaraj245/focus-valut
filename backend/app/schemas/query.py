from pydantic import BaseModel
from typing import List, Optional


class RAGQueryRequest(BaseModel):
    question: str
    user_id: int
    top_k: int = 5
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class RAGContext(BaseModel):
    text: str
    url: str
    topic_name: str
    score: float


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    contexts: List[RAGContext]
    confidence: float
