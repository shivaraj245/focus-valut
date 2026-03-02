import google.generativeai as genai
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.models import BrowserEvent, Flashcard
from app.schemas.flashcard import FlashcardResponse


class FlashcardService:
    
    @classmethod
    async def generate_daily_flashcards(
        cls,
        user_id: int,
        date: str = None,
        db: Session = None
    ) -> List[FlashcardResponse]:
        if date:
            target_date = datetime.fromisoformat(date)
        else:
            target_date = datetime.utcnow() - timedelta(days=1)
        
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        learning_events = db.query(BrowserEvent).filter(
            BrowserEvent.user_id == user_id,
            BrowserEvent.activity_label == "learning",
            BrowserEvent.created_at >= start_of_day,
            BrowserEvent.created_at < end_of_day
        ).all()
        
        if not learning_events:
            return []
        
        flashcards = []
        
        for event in learning_events[:5]:
            try:
                qa_pairs = await cls._generate_flashcard_from_event(event)
                
                for qa in qa_pairs:
                    quality_score = cls._score_flashcard_quality(qa["question"], qa["answer"])
                    
                    if quality_score >= settings.FLASHCARD_QUALITY_THRESHOLD:
                        flashcard = Flashcard(
                            user_id=user_id,
                            question=qa["question"],
                            answer=qa["answer"],
                            quality_score=quality_score,
                            source_url=event.url,
                            next_review_at=datetime.utcnow() + timedelta(days=1)
                        )
                        
                        db.add(flashcard)
                        flashcards.append(flashcard)
                
            except Exception as e:
                print(f"Error generating flashcard for event {event.id}: {e}")
                continue
        
        if flashcards:
            db.commit()
            for fc in flashcards:
                db.refresh(fc)
        
        return flashcards
    
    @classmethod
    async def _generate_flashcard_from_event(cls, event: BrowserEvent) -> List[dict]:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            return cls._generate_simple_flashcard(event)
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""Generate 2 high-quality flashcards based on this learning page:

Title: {event.title}
Topic: {event.topic_name}
URL: {event.url}

Requirements:
- Create clear, specific questions
- Provide concise, accurate answers
- Focus on key concepts
- Make them useful for spaced repetition

Format your response as:
Q1: [question]
A1: [answer]

Q2: [question]
A2: [answer]"""
            
            response = model.generate_content(prompt)
            text = response.text
            
            qa_pairs = []
            lines = text.strip().split('\n')
            
            current_q = None
            for line in lines:
                line = line.strip()
                if line.startswith('Q'):
                    current_q = line.split(':', 1)[1].strip() if ':' in line else line
                elif line.startswith('A') and current_q:
                    answer = line.split(':', 1)[1].strip() if ':' in line else line
                    qa_pairs.append({"question": current_q, "answer": answer})
                    current_q = None
            
            return qa_pairs if qa_pairs else cls._generate_simple_flashcard(event)
            
        except Exception as e:
            print(f"Gemini flashcard generation error: {e}")
            return cls._generate_simple_flashcard(event)
    
    @classmethod
    def _generate_simple_flashcard(cls, event: BrowserEvent) -> List[dict]:
        return [{
            "question": f"What did you learn about {event.topic_name} from {event.domain}?",
            "answer": f"Review the page: {event.title}"
        }]
    
    @classmethod
    def _score_flashcard_quality(cls, question: str, answer: str) -> float:
        score = 0.5
        
        if len(question) >= 20 and len(question) <= 200:
            score += 0.15
        
        if len(answer) >= 10 and len(answer) <= 500:
            score += 0.15
        
        if '?' in question:
            score += 0.1
        
        if any(word in question.lower() for word in ['what', 'how', 'why', 'explain', 'describe']):
            score += 0.1
        
        return min(score, 1.0)
