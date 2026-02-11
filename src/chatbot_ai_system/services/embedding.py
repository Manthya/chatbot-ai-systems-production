import logging
from typing import List, Optional
import httpx
from chatbot_ai_system.config import get_settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings using Ollama.
    """
    def __init__(self, base_url: Optional[str] = None, model: str = "nomic-embed-text"):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a given text with caching.
        """
        if not text:
            return None
            
        import hashlib
        from chatbot_ai_system.database.redis import redis_client
        
        # Create hash for text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"embedding:{text_hash}"
        
        # Check cache
        cached_embedding = await redis_client.get(cache_key)
        if cached_embedding:
            logger.info("Using cached embedding")
            return cached_embedding

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    
                    if embedding:
                        # Cache embedding (24 hour TTL)
                        await redis_client.set(cache_key, embedding, ttl=86400)
                        
                    return embedding
                else:
                    logger.error(f"Embedding generation failed: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
