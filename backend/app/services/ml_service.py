import re
import json
import numpy as np
import pandas as pd
from pathlib import Path

import joblib

from app.core.config import settings
from app.schemas.event import BrowserEventCreate, MLPredictionResponse

# -- Keyword lists (must match training exactly) --------------------------------
_LEARNING_KEYWORDS = [
    'tutorial', 'course', 'problem', 'leetcode', 'interview',
    'algorithm', 'data structure', 'guide', 'documentation',
    'learn', 'lesson', 'training', 'class', 'education',
    'practice', 'exercise', 'solution', 'code', 'programming',
    'python', 'javascript', 'java', 'database', 'sql',
    'lecture', 'workshop', 'seminar', 'conference', 'webinar',
    'book', 'manual', 'reference', 'academic', 'research',
    'aptitude', 'preparation', 'placement', 'campus', 'quantitative',
    'reasoning', 'ability', 'test', 'exam', 'quiz', 'assessment',
    'skill', 'certification', 'project', 'assignment', 'homework',
    'study', 'notes', 'revision', 'subject', 'chapter',
]

_NON_LEARNING_KEYWORDS = [
    'music', 'song', 'playlist', 'movie', 'film', 'watch',
    'entertainment', 'game', 'gaming', 'streaming', 'social',
    'meme', 'funny', 'comedy', 'news', 'sport', 'cricket',
    'instagram', 'facebook', 'twitter', 'tiktok', 'shorts',
    'viral', 'trending', 'celebrity', 'gossip',
    'drama', 'prank', 'challenge', 'react', 'reaction',
]

_LEARNING_DOMAINS = [
    'geeksforgeeks.org', 'github.com', 'stackoverflow.com',
    'leetcode.com', 'hackerrank.com', 'w3schools.com',
    'mdn.mozilla.org', 'coursera.org', 'udemy.com',
    'edx.org', 'kdnuggets.com', 'dev.to',
    'freecodecamp.org', 'tutorialspoint.com', 'medium.com',
]


# -- Feature helpers (replicate training code exactly) -------------------------

def _clean_title(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _count_keywords_whole_word(text: str, keywords: list) -> int:
    """Whole-word boundary match (prevents 'java' matching 'javascript')."""
    count = 0
    for kw in keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            count += 1
    return count


def _build_feature_df(title: str, domain: str, duration_seconds: int) -> pd.DataFrame:
    """Build the exact DataFrame the trained pipeline expects."""
    cleaned_title = _clean_title(title)
    domain_lower = domain.lower()

    lkc = _count_keywords_whole_word(cleaned_title, _LEARNING_KEYWORDS)
    nlkc = _count_keywords_whole_word(cleaned_title, _NON_LEARNING_KEYWORDS)
    is_learning_domain = int(any(d in domain_lower for d in _LEARNING_DOMAINS))

    return pd.DataFrame([{
        'title': cleaned_title,
        'Domain': domain_lower,
        'duration_seconds': float(duration_seconds),
        'is_very_short_session': int(duration_seconds < 60),
        'learning_keyword_count': lkc,
        'non_learning_keyword_count': nlkc,
        'is_learning_domain': is_learning_domain,
        'keyword_balance': lkc - 3 * nlkc,
        'has_non_learning_marker': int(nlkc > 0),
    }])


def _try_load(path: Path, attr: str, target, msg: str) -> None:
    """Load a joblib file into target.<attr>, warn if missing."""
    if path.exists():
        try:
            setattr(target, attr, joblib.load(path))
            print(msg)
        except Exception as e:
            print(f"Could not load {path.name}: {e}")
    else:
        print(f"  {path.name} not found - rule-based fallback active")


# -- Main service class ---------------------------------------------------------

class MLService:
    # Class-level model holders
    activity_pipeline = None   # sklearn Pipeline: ColumnTransformer + classifier
    activity_label_enc = None  # LabelEncoder -> ['learning', 'not_learning']
    topic_vectorizer = None    # TF-IDF vectorizer for topic clustering
    topic_kmeans = None        # KMeans model
    cluster_map: dict = {}     # {str(cluster_id): topic_name}
    model_metadata: dict = {}  # {test_f1_score, test_accuracy, model_type, ...}
    is_initialized = False

    # -- Lifecycle --------------------------------------------------------------

    @classmethod
    async def initialize(cls):
        configured = Path(settings.MODELS_PATH)
        candidates = [configured, Path("../models"), Path("models"), Path("backend/models")]
        models_path = next((p for p in candidates if p.exists()), configured)

        if not models_path.exists():
            print(f"  Models directory not found. Tried: {', '.join(str(p) for p in candidates)}")
            print("  Using fallback rule-based classification")
            cls.is_initialized = True
            return

        _try_load(models_path / "activity_classifier_pipeline.pkl",
                  "activity_pipeline", cls, "Activity classifier pipeline loaded")
        _try_load(models_path / "activity_label_encoder.pkl",
                  "activity_label_enc", cls, "Activity label encoder loaded")
        _try_load(models_path / "tfidf_vectorizer.pkl",
                  "topic_vectorizer", cls, "TF-IDF topic vectorizer loaded")
        _try_load(models_path / "kmeans_model.pkl",
                  "topic_kmeans", cls, "KMeans topic model loaded")

        cluster_map_path = models_path / "cluster_map.json"
        if cluster_map_path.exists():
            with open(cluster_map_path) as f:
                cls.cluster_map = json.load(f)
            print(f"Cluster map loaded ({len(cls.cluster_map)} topics)")

        meta_path = models_path / "model_metadata.pkl"
        if meta_path.exists():
            cls.model_metadata = joblib.load(meta_path)
            f1 = cls.model_metadata.get('test_f1_score', 'N/A')
            mtype = cls.model_metadata.get('model_type', 'unknown')
            print(f"Model metadata loaded (F1={f1:.3f}, type={mtype})")

        cls.is_initialized = True

    @classmethod
    def is_ready(cls) -> bool:
        return cls.is_initialized

    # -- Primary prediction entry point -----------------------------------------

    @classmethod
    async def predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        if cls.activity_pipeline is not None:
            return await cls._ml_predict(event)
        return await cls._rule_based_predict(event)

    # -- ML-backed prediction ---------------------------------------------------

    @classmethod
    async def _ml_predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        try:
            df = _build_feature_df(
                title=event.title or "",
                domain=event.domain,
                duration_seconds=event.duration_seconds,
            )

            raw_proba = cls.activity_pipeline.predict_proba(df)[0]

            if cls.activity_label_enc is not None:
                class_names = list(cls.activity_label_enc.classes_)
            else:
                class_names = [str(i) for i in range(len(raw_proba))]

            probs_dict = {name: float(p) for name, p in zip(class_names, raw_proba)}
            activity_label = class_names[int(np.argmax(raw_proba))]

            topic_id, topic_name = cls._ml_topic(event.title or event.domain)

            is_learning = (
                activity_label == "learning"
                and probs_dict.get("learning", 0.0) >= settings.LEARNING_THRESHOLD
            )

            return MLPredictionResponse(
                activity_label=activity_label,
                activity_probs=probs_dict,
                topic_id=topic_id,
                topic_name=topic_name,
                is_learning=is_learning,
            )

        except Exception as e:
            print(f"ML prediction error: {e} - falling back to rule-based")
            return await cls._rule_based_predict(event)

    # -- Topic helpers ----------------------------------------------------------

    @classmethod
    def _ml_topic(cls, text: str) -> tuple:
        """Return (topic_id, topic_name) using KMeans + TF-IDF."""
        if cls.topic_vectorizer is None or cls.topic_kmeans is None:
            return cls._rule_based_topic(text)
        try:
            vec = cls.topic_vectorizer.transform([_clean_title(text)])
            cluster_id = int(cls.topic_kmeans.predict(vec)[0])
            topic_name = cls.cluster_map.get(str(cluster_id), f"Topic {cluster_id}")
            return cluster_id, topic_name
        except Exception as e:
            print(f"Topic prediction error: {e}")
            return cls._rule_based_topic(text)

    @classmethod
    def _rule_based_topic(cls, text: str) -> tuple:
        t = text.lower()
        if any(k in t for k in ['algorithm', 'dsa', 'leetcode', 'sorting', 'tree', 'graph', 'data structure']):
            return -1, "DSA"
        if any(k in t for k in ['sql', 'mysql', 'postgres', 'database', 'query', 'schema']):
            return -1, "SQL"
        if any(k in t for k in ['machine learning', 'deep learning', 'neural', 'ai', 'tensorflow', 'pytorch']):
            return -1, "AI/ML"
        if any(k in t for k in ['react', 'vue', 'angular', 'html', 'css', 'javascript', 'frontend']):
            return -1, "Web Development"
        if any(k in t for k in ['python', 'java', 'c++', 'golang', 'rust', 'programming']):
            return -1, "Programming"
        if any(k in t for k in ['resume', 'interview', 'career', 'placement', 'campus']):
            return -1, "Career"
        return -1, "General Learning"

    # -- Rule-based fallback ----------------------------------------------------

    @classmethod
    async def _rule_based_predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        title_lower = (event.title or "").lower()
        domain_lower = event.domain.lower()

        learning_kw = [
            'tutorial', 'learn', 'course', 'documentation', 'docs', 'guide',
            'geeksforgeeks', 'stackoverflow', 'leetcode', 'hackerrank',
            'coursera', 'udemy', 'w3schools', 'mdn', 'algorithm',
            'data structure', 'programming', 'code', 'developer',
        ]
        non_learning_kw = [
            'youtube', 'netflix', 'twitter', 'facebook', 'instagram',
            'reddit', 'tiktok', 'twitch', 'spotify', 'game', 'music', 'movie',
        ]

        ls = sum(1 for kw in learning_kw if kw in title_lower or kw in domain_lower)
        nls = sum(1 for kw in non_learning_kw if kw in title_lower or kw in domain_lower)

        if ls > 0 and ls >= nls:
            activity_label = "learning"
            probs = {"learning": 0.85, "not_learning": 0.15}
        else:
            activity_label = "not_learning"
            probs = {"learning": 0.15, "not_learning": 0.85}

        topic_id, topic_name = cls._rule_based_topic(f"{title_lower} {domain_lower}")

        return MLPredictionResponse(
            activity_label=activity_label,
            activity_probs=probs,
            topic_id=topic_id,
            topic_name=topic_name,
            is_learning=(activity_label == "learning"),
        )

    # -- Status / introspection -------------------------------------------------

    @classmethod
    def get_model_status(cls) -> dict:
        meta = cls.model_metadata
        return {
            "is_initialized": cls.is_initialized,
            "activity_pipeline_loaded": cls.activity_pipeline is not None,
            "activity_label_encoder_loaded": cls.activity_label_enc is not None,
            "topic_vectorizer_loaded": cls.topic_vectorizer is not None,
            "topic_kmeans_loaded": cls.topic_kmeans is not None,
            "cluster_map_topics": len(cls.cluster_map),
            "model_type": meta.get("model_type", "N/A"),
            "test_f1_score": meta.get("test_f1_score", None),
            "test_accuracy": meta.get("test_accuracy", None),
            "using_ml": cls.activity_pipeline is not None,
        }
