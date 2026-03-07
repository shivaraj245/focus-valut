from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.ml_service import MLService

router = APIRouter(prefix="/api/ml", tags=["ML"])


# ── Request / Response schemas ─────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    title: str
    domain: str = ""
    duration_seconds: int = 120
    hour_of_day: int = 12


class ClassifyResponse(BaseModel):
    activity_label: str          # "learning" | "not_learning"
    activity_probs: dict         # {"learning": 0.87, "not_learning": 0.13}
    is_learning: bool
    source: str                  # "ml_model" | "rule_based"


class TopicResponse(BaseModel):
    topic_id: int
    topic_name: str
    source: str


class FullPredictionResponse(BaseModel):
    activity_label: str
    activity_probs: dict
    topic_id: int
    topic_name: str
    is_learning: bool


class BatchItem(BaseModel):
    title: str
    domain: str = ""
    duration_seconds: int = 120
    hour_of_day: int = 12


class BatchRequest(BaseModel):
    items: List[BatchItem]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/status", summary="Check which models are loaded")
def model_status():
    """
    Returns load status of each model file and training metadata.
    Useful to verify the backend picked up the .pkl files correctly.
    """
    return MLService.get_model_status()


@router.post("/classify", response_model=ClassifyResponse, summary="Classify a page visit")
async def classify_activity(req: ClassifyRequest):
    """
    Classify a browsing event as **learning** or **not_learning**.

    - Uses the trained `activity_classifier_pipeline.pkl` when loaded.
    - Falls back to keyword-based rules if models are not found.
    """
    from app.schemas.event import BrowserEventCreate

    event = BrowserEventCreate(
        url=f"https://{req.domain}/",
        title=req.title,
        domain=req.domain or req.title[:30],
        duration_seconds=req.duration_seconds,
        hour_of_day=req.hour_of_day,
    )
    try:
        result = await MLService.predict(event)
        source = "ml_model" if MLService.activity_pipeline is not None else "rule_based"
        return ClassifyResponse(
            activity_label=result.activity_label,
            activity_probs=result.activity_probs,
            is_learning=result.is_learning,
            source=source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topic", response_model=TopicResponse, summary="Predict topic cluster")
def predict_topic(req: ClassifyRequest):
    """
    Predict the topic cluster for a page title using KMeans + TF-IDF.
    Falls back to rule-based topic mapping if `kmeans_model.pkl` is not loaded.
    """
    try:
        if MLService.topic_kmeans is not None and MLService.topic_vectorizer is not None:
            topic_id, topic_name = MLService._ml_topic(req.title)
            source = "ml_model"
        else:
            topic_id, topic_name = MLService._rule_based_topic(req.title)
            source = "rule_based"

        return TopicResponse(topic_id=topic_id, topic_name=topic_name, source=source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=FullPredictionResponse,
             summary="Full prediction: activity + topic in one call")
async def full_predict(req: ClassifyRequest):
    """
    Single endpoint that returns both activity classification and topic prediction.
    This is what the Chrome extension calls when indexing a new page.
    """
    from app.schemas.event import BrowserEventCreate

    event = BrowserEventCreate(
        url=f"https://{req.domain}/",
        title=req.title,
        domain=req.domain or req.title[:30],
        duration_seconds=req.duration_seconds,
        hour_of_day=req.hour_of_day,
    )
    try:
        result = await MLService.predict(event)
        return FullPredictionResponse(
            activity_label=result.activity_label,
            activity_probs=result.activity_probs,
            topic_id=result.topic_id,
            topic_name=result.topic_name,
            is_learning=result.is_learning,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", summary="Classify up to 100 events in one request")
async def batch_predict(req: BatchRequest):
    """
    Batch classification — useful for re-classifying historical events
    or bulk imports from the extension.
    """
    if len(req.items) > 100:
        raise HTTPException(status_code=400, detail="Max 100 items per batch request")

    from app.schemas.event import BrowserEventCreate

    results = []
    for item in req.items:
        event = BrowserEventCreate(
            url=f"https://{item.domain}/",
            title=item.title,
            domain=item.domain or item.title[:30],
            duration_seconds=item.duration_seconds,
            hour_of_day=item.hour_of_day,
        )
        try:
            prediction = await MLService.predict(event)
            results.append({
                "title": item.title,
                "domain": item.domain,
                "activity_label": prediction.activity_label,
                "activity_probs": prediction.activity_probs,
                "topic_id": prediction.topic_id,
                "topic_name": prediction.topic_name,
                "is_learning": prediction.is_learning,
            })
        except Exception as e:
            results.append({"title": item.title, "error": str(e)})

    source = "ml_model" if MLService.activity_pipeline is not None else "rule_based"
    return {"count": len(results), "source": source, "results": results}
