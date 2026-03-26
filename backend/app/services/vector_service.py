from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, Range, VectorParams
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import uuid

from app.core.config import settings


class VectorService:
    client: QdrantClient = None
    encoder: SentenceTransformer = None
    is_initialized = False

    @classmethod
    def _ensure_collection(cls):
        collections = cls.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.QDRANT_COLLECTION not in collection_names:
            cls.client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=settings.VECTOR_DIM,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Created Qdrant collection: {settings.QDRANT_COLLECTION}")
        else:
            print(f"✅ Qdrant collection exists: {settings.QDRANT_COLLECTION}")

    @classmethod
    def _load_encoder(cls):
        if cls.encoder is None:
            cls.encoder = SentenceTransformer(settings.EMBEDDING_MODEL)
            print(f"✅ Loaded embedding model: {settings.EMBEDDING_MODEL}")
    
    @classmethod
    async def initialize(cls):
        try:
            cls.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )

            cls._ensure_collection()
            cls._load_encoder()
            cls.is_initialized = True
            print("✅ Connected to remote Qdrant server")

        except Exception as remote_error:
            print(f"⚠️  Remote Qdrant initialization error: {remote_error}")
            print("   Falling back to local embedded Qdrant storage")

            try:
                cls.client = QdrantClient(path=settings.QDRANT_LOCAL_PATH)
                cls._ensure_collection()
                cls._load_encoder()
                cls.is_initialized = True
                print(f"✅ Local Qdrant initialized at: {settings.QDRANT_LOCAL_PATH}")
            except Exception as local_error:
                print(f"⚠️  Local Qdrant fallback error: {local_error}")
                print("   Vector search will be unavailable")
                cls.is_initialized = False
            

    
    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
    
    @classmethod
    async def health_check(cls) -> bool:
        try:
            if cls.client:
                cls.client.get_collections()
                return True
        except:
            pass
        return False
    
    @classmethod
    async def add_chunks(
        cls,
        chunks: List[str],
        user_id: int,
        topic_id: int,
        url: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        if not cls.is_initialized:
            print("⚠️  Vector service not initialized")
            return 0
        
        try:
            embeddings = cls.encoder.encode(chunks, show_progress_bar=False)
            
            points = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid.uuid4())
                
                payload = {
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "url": url,
                    "chunk_text": chunk,
                    "chunk_index": idx
                }
                
                if metadata:
                    payload.update(metadata)
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload=payload
                    )
                )
            
            cls.client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=points
            )
            
            print(f"✅ Indexed {len(points)} chunks for {url}")
            return len(points)
            
        except Exception as e:
            print(f"❌ Error adding chunks: {e}")
            return 0
    
    @classmethod
    async def search(
        cls,
        query: str,
        user_id: int,
        top_k: int = 5,
        topic_id: int = None,
        date_from: int = None,
        date_to: int = None,
    ) -> List[Dict[str, Any]]:
        if not cls.is_initialized:
            return []
        
        try:
            query_vector = cls.encoder.encode(query, show_progress_bar=False).tolist()

            must_conditions = [
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]

            if topic_id is not None:
                must_conditions.append(
                    FieldCondition(
                        key="topic_id",
                        match=MatchValue(value=topic_id)
                    )
                )

            if date_from is not None or date_to is not None:
                must_conditions.append(
                    FieldCondition(
                        key="event_created_at_ts",
                        range=Range(
                            gte=date_from,
                            lt=date_to,
                        )
                    )
                )

            query_filter = Filter(must=must_conditions)
            
            results = cls.client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k
            )
            
            return [
                {
                    "text": hit.payload.get("chunk_text", ""),
                    "url": hit.payload.get("url", ""),
                    "topic_id": hit.payload.get("topic_id"),
                    "score": hit.score,
                    "metadata": hit.payload
                }
                for hit in results
            ]
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    @classmethod
    async def delete_by_url(cls, url: str, user_id: int):
        if not cls.is_initialized:
            return
        
        try:
            cls.client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector={
                    "filter": {
                        "must": [
                            {"key": "user_id", "match": {"value": user_id}},
                            {"key": "url", "match": {"value": url}}
                        ]
                    }
                }
            )
            print(f"✅ Deleted vectors for {url}")
        except Exception as e:
            print(f"❌ Error deleting vectors: {e}")
