import httpx
from bs4 import BeautifulSoup
from typing import List
import re

from app.core.config import settings
from app.services.vector_service import VectorService


class IndexingService:
    
    @classmethod
    async def queue_page_for_indexing(cls, event_id: int, url: str, user_id: int):
        print(f"📝 Queuing page for indexing: {url}")
        
        try:
            await cls.index_page(url, user_id, topic_id=0)
        except Exception as e:
            print(f"❌ Indexing failed for {url}: {e}")
    
    @classmethod
    async def index_page(cls, url: str, user_id: int, topic_id: int = 0):
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
                metadata={"indexed_at": "now"}
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
                
                soup = BeautifulSoup(response.text, 'lxml')
                
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
