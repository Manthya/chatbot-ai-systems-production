"""Ollama LLM provider for local model inference."""

import logging
import time
from typing import AsyncGenerator, List, Optional

import httpx

from chatbot_ai_system.config import get_settings
from chatbot_ai_system.models.schemas import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    StreamChunk,
    UsageInfo,
)

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM models.

    Ollama allows running open source models locally including:
    - Llama 2
    - Mistral
    - CodeLlama
    - And many more
    """

    provider_name = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            default_model: Default model to use (default: llama2)
        """
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = default_model or settings.ollama_model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _format_messages(self, messages: List[ChatMessage]) -> List[dict]:
        """Format messages for Ollama API."""
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    async def complete(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """Generate a completion using Ollama.

        Args:
            messages: List of chat messages
            model: Model to use (default: llama2)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            ChatResponse with the generated message
        """
        start_time = time.time()
        client = await self._get_client()
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=data.get("message", {}).get("content", ""),
                ),
                usage=UsageInfo(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0)
                    + data.get("eval_count", 0),
                ),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"Failed to get completion from Ollama: {e}")

    async def stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a completion using Ollama.

        Args:
            messages: List of chat messages
            model: Model to use (default: llama2)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            StreamChunk objects with partial content
        """
        model = model or self.default_model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            # Use a fresh client for streaming to avoid connection issues
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json

                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            done = data.get("done", False)

                            if content or done:
                                yield StreamChunk(content=content, done=done)

        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming error: {e}")
            raise RuntimeError(f"Failed to stream from Ollama: {e}")

    async def health_check(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """Get list of commonly available Ollama models."""
        # This returns common models; actual availability depends on what's pulled
        return [
            "llama2",
            "llama2:13b",
            "mistral",
            "codellama",
            "phi",
            "neural-chat",
            "starling-lm",
        ]

    async def list_local_models(self) -> List[str]:
        """Get list of models actually available locally."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []
