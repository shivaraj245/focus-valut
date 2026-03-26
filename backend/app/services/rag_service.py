from google import genai
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import BrowserEvent
from app.services.vector_service import VectorService
from app.schemas.query import RAGQueryResponse, RAGContext


class RAGService:

    @classmethod
    def _is_summary_intent(cls, question: str) -> bool:
        q = (question or "").lower()
        summary_phrases = [
            "what did i learn",
            "what i learned",
            "summarize my learning",
            "learning summary",
            "today learning",
            "today's learning",
        ]
        return any(phrase in q for phrase in summary_phrases)

    @classmethod
    def _is_noisy_event(cls, event: BrowserEvent) -> bool:
        url = (event.url or "").lower()
        title = (event.title or "").lower()
        if "/search/?" in url or "swagger" in title or "focusvault" in title:
            return True
        return False

    @classmethod
    def _build_learning_summary(cls, user_id: int, date_from: int, date_to: int):
        if date_from is None or date_to is None:
            return None

        start_dt = datetime.utcfromtimestamp(date_from)
        end_dt = datetime.utcfromtimestamp(date_to)

        db = SessionLocal()
        try:
            events = db.query(BrowserEvent).filter(
                BrowserEvent.user_id == user_id,
                BrowserEvent.activity_label == "learning",
                BrowserEvent.created_at >= start_dt,
                BrowserEvent.created_at < end_dt,
            ).order_by(BrowserEvent.created_at.desc()).all()
        finally:
            db.close()

        clean_events = [event for event in events if not cls._is_noisy_event(event)]
        if not clean_events:
            return None

        total_minutes = sum((event.duration_seconds or 0) for event in clean_events) // 60

        topic_minutes = {}
        for event in clean_events:
            topic = event.topic_name or "General Learning"
            topic_minutes[topic] = topic_minutes.get(topic, 0) + (event.duration_seconds or 0)

        top_topics = sorted(topic_minutes.items(), key=lambda item: item[1], reverse=True)[:3]
        top_topics_text = ", ".join(
            f"{topic} ({seconds // 60}m)" for topic, seconds in top_topics
        )

        unique_titles = []
        seen_titles = set()
        for event in clean_events:
            title = (event.title or "").strip()
            if title and title not in seen_titles:
                unique_titles.append(title)
                seen_titles.add(title)
            if len(unique_titles) >= 5:
                break

        highlights = "\n".join(f"- {title}" for title in unique_titles)

        answer = (
            f"Today you spent about {total_minutes} minutes on learning across {len(clean_events)} tracked study events.\n"
            f"Top topics: {top_topics_text}.\n\n"
            f"Key pages you studied:\n{highlights}"
        )

        contexts = [
            RAGContext(
                text=(event.title or "")[:200],
                url=event.url or "",
                topic_name=event.topic_name or "Other",
                score=1.0,
            )
            for event in clean_events[:5]
        ]

        return RAGQueryResponse(
            question="What did I learn today?",
            answer=answer,
            contexts=contexts,
            confidence=1.0,
        )
    
    @classmethod
    async def answer_question(
        cls,
        question: str,
        user_id: int,
        top_k: int = 5,
        start_date: str = None,
        end_date: str = None,
    ) -> RAGQueryResponse:
        date_from, date_to = cls._resolve_date_window(
            question=question,
            start_date=start_date,
            end_date=end_date,
        )

        if cls._is_summary_intent(question):
            summary_response = cls._build_learning_summary(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
            )
            if summary_response is not None:
                summary_response.question = question
                return summary_response

        contexts = await VectorService.search(
            query=question,
            user_id=user_id,
            top_k=top_k,
            date_from=date_from,
            date_to=date_to,
        )
        
        if not contexts:
            return RAGQueryResponse(
                question=question,
                answer="I couldn't find any relevant information in your learning history. Try studying more pages on this topic!",
                contexts=[],
                confidence=0.0
            )
        
        answer = await cls._generate_answer(question, contexts)
        
        rag_contexts = [
            RAGContext(
                text=ctx["text"][:200] + "...",
                url=ctx["url"],
                topic_name=cls._get_topic_name(ctx.get("topic_id", 5)),
                score=ctx["score"]
            )
            for ctx in contexts
        ]
        
        avg_score = sum(ctx["score"] for ctx in contexts) / len(contexts)
        
        return RAGQueryResponse(
            question=question,
            answer=answer,
            contexts=rag_contexts,
            confidence=round(avg_score, 2)
        )

    @classmethod
    def _resolve_date_window(cls, question: str, start_date: str = None, end_date: str = None):
        if start_date or end_date:
            return cls._parse_explicit_window(start_date, end_date)

        lowered = (question or "").lower()
        now = datetime.utcnow()

        if "today" in lowered:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return int(start.timestamp()), int(end.timestamp())

        if "yesterday" in lowered:
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)
            return int(start.timestamp()), int(end.timestamp())

        if "this week" in lowered:
            start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now + timedelta(seconds=1)
            return int(start.timestamp()), int(end.timestamp())

        if "last week" in lowered:
            this_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            start = this_week_start - timedelta(days=7)
            end = this_week_start
            return int(start.timestamp()), int(end.timestamp())

        return None, None

    @classmethod
    def _parse_explicit_window(cls, start_date: str = None, end_date: str = None):
        def to_datetime(date_str: str):
            if not date_str:
                return None
            text = date_str.strip()
            if len(text) == 10:
                return datetime.fromisoformat(text)
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)

        start_dt = to_datetime(start_date)
        end_dt = to_datetime(end_date)

        if start_dt and not end_dt and len(start_date.strip()) == 10:
            end_dt = start_dt + timedelta(days=1)

        date_from = int(start_dt.timestamp()) if start_dt else None
        date_to = int(end_dt.timestamp()) if end_dt else None
        return date_from, date_to
    
    @classmethod
    async def _generate_answer(cls, question: str, contexts: List[Dict[str, Any]]) -> str:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            return cls._fallback_answer(question, contexts)
        
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            context_text = "\n\n".join([
                f"[Source {i+1}]: {ctx['text']}"
                for i, ctx in enumerate(contexts)
            ])
            
            prompt = f"""You are a helpful AI assistant that answers questions based ONLY on the user's learning history.

Context from user's studied pages:
{context_text}

Question: {question}

Instructions:
- Answer the question using ONLY the information from the context above
- If the context doesn't contain enough information, say so
- Be concise and clear
- Cite which source(s) you used (e.g., "According to Source 1...")

Answer:"""
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
            
        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return cls._fallback_answer(question, contexts)
    
    @classmethod
    def _fallback_answer(cls, question: str, contexts: List[Dict[str, Any]]) -> str:
        best_context = contexts[0] if contexts else None
        
        if not best_context:
            return "No relevant information found in your learning history."
        
        return f"""Based on your learning history, here's what I found:

{best_context['text'][:500]}...

(This is a direct excerpt from: {best_context['url']})

Note: For better AI-generated answers, please configure the Gemini API key in your .env file."""
    
    @classmethod
    def _get_topic_name(cls, topic_id: int) -> str:
        topics = {
            0: "Data Structures & Algorithms",
            1: "Web Development",
            2: "Machine Learning",
            3: "System Design",
            4: "Programming Languages",
            5: "Other"
        }
        return topics.get(topic_id, "Other")
