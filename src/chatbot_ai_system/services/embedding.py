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
        Generate embedding for a given text.
        """
        if not text:
            return None
            
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
                    return data.get("embedding")
                else:
                    logger.error(f"Embedding generation failed: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
