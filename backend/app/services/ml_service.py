import pickle
import os
from typing import Dict, Any
import numpy as np
from pathlib import Path

from app.core.config import settings
from app.schemas.event import BrowserEventCreate, MLPredictionResponse


class MLService:
    activity_model = None
    topic_model = None
    vectorizer = None
    is_initialized = False
    
    @classmethod
    async def initialize(cls):
        models_path = Path(settings.MODELS_PATH)
        
        if not models_path.exists():
            print(f"⚠️  Models directory not found: {models_path}")
            print("   Using fallback rule-based classification")
            cls.is_initialized = True
            return
        
        try:
            activity_model_path = models_path / "activity_classifier.pkl"
            if activity_model_path.exists():
                with open(activity_model_path, 'rb') as f:
                    cls.activity_model = pickle.load(f)
                print("✅ Activity classifier loaded")
            
            topic_model_path = models_path / "topic_clusterer.pkl"
            if topic_model_path.exists():
                with open(topic_model_path, 'rb') as f:
                    cls.topic_model = pickle.load(f)
                print("✅ Topic clusterer loaded")
            
            vectorizer_path = models_path / "vectorizer.pkl"
            if vectorizer_path.exists():
                with open(vectorizer_path, 'rb') as f:
                    cls.vectorizer = pickle.load(f)
                print("✅ Vectorizer loaded")
            
            cls.is_initialized = True
            
        except Exception as e:
            print(f"⚠️  Error loading ML models: {e}")
            print("   Using fallback rule-based classification")
            cls.is_initialized = True
    
    @classmethod
    def is_ready(cls) -> bool:
        return cls.is_initialized
    
    @classmethod
    async def predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        if cls.activity_model and cls.vectorizer:
            return await cls._ml_predict(event)
        else:
            return await cls._rule_based_predict(event)
    
    @classmethod
    async def _ml_predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        try:
            features = cls._extract_features(event)
            
            activity_probs = cls.activity_model.predict_proba([features])[0]
            activity_classes = cls.activity_model.classes_
            
            activity_probs_dict = {
                cls: float(prob) 
                for cls, prob in zip(activity_classes, activity_probs)
            }
            
            activity_label = activity_classes[np.argmax(activity_probs)]
            
            title_vector = cls.vectorizer.transform([event.title or event.domain])
            topic_id = int(cls.topic_model.predict(title_vector)[0])
            
            topic_names = {
                0: "Data Structures & Algorithms",
                1: "Web Development",
                2: "Machine Learning",
                3: "System Design",
                4: "Programming Languages",
                5: "Other"
            }
            topic_name = topic_names.get(topic_id, "Other")
            
            is_learning = activity_label == "learning" and activity_probs_dict.get("learning", 0) >= settings.LEARNING_THRESHOLD
            
            return MLPredictionResponse(
                activity_label=activity_label,
                activity_probs=activity_probs_dict,
                topic_id=topic_id,
                topic_name=topic_name,
                is_learning=is_learning
            )
            
        except Exception as e:
            print(f"ML prediction error: {e}, falling back to rules")
            return await cls._rule_based_predict(event)
    
    @classmethod
    async def _rule_based_predict(cls, event: BrowserEventCreate) -> MLPredictionResponse:
        title_lower = (event.title or "").lower()
        domain_lower = event.domain.lower()
        
        learning_keywords = [
            'tutorial', 'learn', 'course', 'documentation', 'docs', 'guide',
            'geeksforgeeks', 'stackoverflow', 'medium', 'dev.to', 'leetcode',
            'hackerrank', 'coursera', 'udemy', 'khan', 'w3schools', 'mdn',
            'algorithm', 'data structure', 'programming', 'code', 'developer'
        ]
        
        work_keywords = [
            'jira', 'confluence', 'slack', 'teams', 'zoom', 'meet',
            'github', 'gitlab', 'bitbucket', 'jenkins', 'aws', 'azure'
        ]
        
        entertainment_keywords = [
            'youtube', 'netflix', 'twitter', 'facebook', 'instagram',
            'reddit', 'tiktok', 'twitch', 'spotify', 'game'
        ]
        
        learning_score = sum(1 for kw in learning_keywords if kw in title_lower or kw in domain_lower)
        work_score = sum(1 for kw in work_keywords if kw in title_lower or kw in domain_lower)
        entertainment_score = sum(1 for kw in entertainment_keywords if kw in title_lower or kw in domain_lower)
        
        if learning_score >= work_score and learning_score >= entertainment_score and learning_score > 0:
            activity_label = "learning"
            probs = {"learning": 0.85, "work": 0.10, "entertainment": 0.05}
        elif work_score > entertainment_score:
            activity_label = "work"
            probs = {"learning": 0.10, "work": 0.80, "entertainment": 0.10}
        else:
            activity_label = "entertainment"
            probs = {"learning": 0.05, "work": 0.15, "entertainment": 0.80}
        
        topic_id, topic_name = cls._classify_topic_rule_based(title_lower, domain_lower)
        
        return MLPredictionResponse(
            activity_label=activity_label,
            activity_probs=probs,
            topic_id=topic_id,
            topic_name=topic_name,
            is_learning=activity_label == "learning"
        )
    
    @classmethod
    def _classify_topic_rule_based(cls, title: str, domain: str) -> tuple:
        text = f"{title} {domain}"
        
        if any(kw in text for kw in ['algorithm', 'data structure', 'dsa', 'leetcode', 'sorting', 'tree', 'graph']):
            return 0, "Data Structures & Algorithms"
        elif any(kw in text for kw in ['react', 'vue', 'angular', 'html', 'css', 'javascript', 'frontend', 'backend', 'api']):
            return 1, "Web Development"
        elif any(kw in text for kw in ['machine learning', 'ml', 'ai', 'neural', 'deep learning', 'tensorflow', 'pytorch']):
            return 2, "Machine Learning"
        elif any(kw in text for kw in ['system design', 'architecture', 'scalability', 'microservices', 'database design']):
            return 3, "System Design"
        elif any(kw in text for kw in ['python', 'java', 'c++', 'javascript', 'golang', 'rust', 'programming']):
            return 4, "Programming Languages"
        else:
            return 5, "Other"
    
    @classmethod
    def _extract_features(cls, event: BrowserEventCreate) -> list:
        return [
            event.duration_seconds,
            event.hour_of_day,
            len(event.title or ""),
            len(event.url)
        ]
