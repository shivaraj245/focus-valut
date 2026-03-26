import httpx
from bs4 import BeautifulSoup
from typing import List
import re
from datetime import datetime

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import BrowserEvent
from app.services.vector_service import VectorService


class IndexingService:

    @classmethod
    def _set_url_indexed_state(cls, user_id: int, url: str, is_saved_to_kb: bool):
        db = SessionLocal()
        try:
            db.query(BrowserEvent).filter(
                BrowserEvent.user_id == user_id,
                BrowserEvent.url == url
            ).update({"is_saved_to_kb": is_saved_to_kb}, synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to update KB state for {url}: {e}")
        finally:
            db.close()

    @classmethod
    def _mark_event_indexed(cls, event_id: int):
        db = SessionLocal()
        try:
            event = db.query(BrowserEvent).filter(BrowserEvent.id == event_id).first()
            if not event:
                return

            event.is_saved_to_kb = True

            db.query(BrowserEvent).filter(
                BrowserEvent.user_id == event.user_id,
                BrowserEvent.url == event.url
            ).update({"is_saved_to_kb": True}, synchronize_session=False)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to update indexing state for event {event_id}: {e}")
        finally:
            db.close()

    @classmethod
    async def reindex_learning_events(cls, user_id: int, limit: int = 25):
        db = SessionLocal()
        try:
            events = db.query(BrowserEvent).filter(
                BrowserEvent.user_id == user_id,
                BrowserEvent.activity_label == "learning"
            ).order_by(BrowserEvent.created_at.desc()).all()

            latest_by_url = {}
            for event in events:
                if event.url not in latest_by_url:
                    latest_by_url[event.url] = event

            selected_events = list(latest_by_url.values())[:limit]
        finally:
            db.close()

        indexed = 0
        failed = []

        for event in selected_events:
            try:
                await VectorService.delete_by_url(event.url, user_id)
                cls._set_url_indexed_state(user_id, event.url, False)
                metadata = {
                    "indexed_at": datetime.utcnow().isoformat(),
                    "indexed_at_ts": int(datetime.utcnow().timestamp()),
                    "event_created_at": event.created_at.isoformat() if event.created_at else None,
                    "event_created_at_ts": int(event.created_at.timestamp()) if event.created_at else int(datetime.utcnow().timestamp()),
                }
                await cls.index_page(event.url, user_id, topic_id=event.topic_id or 0, metadata=metadata)
                cls._set_url_indexed_state(user_id, event.url, True)
                indexed += 1
            except Exception as e:
                failed.append({"url": event.url, "reason": str(e)})

        return {
            "indexed_urls": indexed,
            "failed": failed,
            "processed_urls": len(selected_events),
        }

    @classmethod
    def _url_already_indexed(cls, user_id: int, url: str) -> bool:
        db = SessionLocal()
        try:
            return db.query(BrowserEvent.id).filter(
                BrowserEvent.user_id == user_id,
                BrowserEvent.url == url,
                BrowserEvent.is_saved_to_kb.is_(True)
            ).first() is not None
        finally:
            db.close()
    
    @classmethod
    async def queue_page_for_indexing(cls, event_id: int, url: str, user_id: int, topic_id: int = 0):
        print(f"📝 Queuing page for indexing: {url}")

        if cls._url_already_indexed(user_id, url):
            cls._mark_event_indexed(event_id)
            print(f"ℹ️ Skipping duplicate indexing for {url}")
            return
        
        db = SessionLocal()
        event = None
        try:
            event = db.query(BrowserEvent).filter(BrowserEvent.id == event_id).first()
        finally:
            db.close()

        try:
            now = datetime.utcnow()
            metadata = {
                "indexed_at": now.isoformat(),
                "indexed_at_ts": int(now.timestamp()),
                "event_created_at": event.created_at.isoformat() if event and event.created_at else now.isoformat(),
                "event_created_at_ts": int(event.created_at.timestamp()) if event and event.created_at else int(now.timestamp()),
            }
            await cls.index_page(url, user_id, topic_id=topic_id, metadata=metadata)
            cls._mark_event_indexed(event_id)
        except Exception as e:
            print(f"❌ Indexing failed for {url}: {e}")
    
    @classmethod
    async def index_page(cls, url: str, user_id: int, topic_id: int = 0, metadata: dict = None):
        try:
            content = await cls.fetch_page_content(url)
            
            if not content:
                print(f"⚠️  No content extracted from {url}")
                return
            
            chunks = cls.chunk_text(content)
            
            if not chunks:
                print(f"⚠️  No chunks created from {url}")
                return
            
            await VectorService.add_chunks(
                chunks=chunks,
                user_id=user_id,
                topic_id=topic_id,
                url=url,
                metadata=metadata or {
                    "indexed_at": datetime.utcnow().isoformat(),
                    "indexed_at_ts": int(datetime.utcnow().timestamp()),
                }
            )
            
        except Exception as e:
            print(f"❌ Error indexing {url}: {e}")
            raise
    
    @classmethod
    async def fetch_page_content(cls, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                
                article = soup.find('article') or soup.find('main') or soup.find(class_='content')
                
                if article:
                    text = article.get_text(separator=' ', strip=True)
                else:
                    text = soup.get_text(separator=' ', strip=True)
                
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()
                
                return text
                
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return ""
    
    @classmethod
    def chunk_text(cls, text: str) -> List[str]:
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        
        words = text.split()
        
        if len(words) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            
            start = end - overlap
            
            if start >= len(words):
                break
        
        return chunks
