import google.generativeai as genai
from typing import List, Dict, Any

from app.core.config import settings
from app.services.vector_service import VectorService
from app.schemas.query import RAGQueryResponse, RAGContext


class RAGService:
    
    @classmethod
    async def answer_question(
        cls,
        question: str,
        user_id: int,
        top_k: int = 5
    ) -> RAGQueryResponse:
        contexts = await VectorService.search(
            query=question,
            user_id=user_id,
            top_k=top_k
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
    async def _generate_answer(cls, question: str, contexts: List[Dict[str, Any]]) -> str:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            return cls._fallback_answer(question, contexts)
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
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
            
            response = model.generate_content(prompt)
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
