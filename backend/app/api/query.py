from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.indexing_service import IndexingService
from app.schemas.query import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/", response_model=RAGQueryResponse)
async def query_knowledge_base(
    query: RAGQueryRequest,
    db: Session = Depends(get_db)
):
    try:
        result = await RAGService.answer_question(
            question=query.question,
            user_id=query.user_id,
            top_k=query.top_k,
            start_date=query.start_date,
            end_date=query.end_date,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/test")
async def test_rag():
    return {
        "message": "RAG service is ready",
        "status": "ok"
    }


@router.post("/reindex/{user_id}")
async def reindex_user_knowledge_base(
    user_id: int,
    limit: int = 25,
    db: Session = Depends(get_db)
):
    try:
        return await IndexingService.reindex_learning_events(user_id=user_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")
