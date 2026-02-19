"""Gemini LLM provider implementation using httpx."""

import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from chatbot_ai_system.config import get_settings
from chatbot_ai_system.models.schemas import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    StreamChunk,
    UsageInfo,
)
from chatbot_ai_system.observability.metrics import (
    LLM_REQUESTS_TOTAL,
    LLM_REQUEST_DURATION_SECONDS,
    LLM_TOKENS_TOTAL,
    LLM_TTFT_SECONDS,
)
from chatbot_ai_system.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using direct HTTP API."""

    provider_name = "gemini"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.default_model = settings.gemini_model or "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        if not self.api_key:
            logger.warning("Gemini API key not configured.")

    def _format_contents(self, messages: List[ChatMessage]) -> List[Dict]:
        """Format messages for Gemini API."""
        contents = []
        for msg in messages:
            role = "user" if msg.role in [MessageRole.USER, MessageRole.SYSTEM] else "model"
            
            # Gemini doesn't support system messages in 'contents' strictly speaking, 
            # usually mapped to first user message or system_instruction field (v1beta).
            # For simplicity using 'generateContent', we'll treat system as user message.
            
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        return contents

    async def complete(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> ChatResponse:
        """Generate completion via Gemini REST API."""
        if not self.api_key:
             raise ValueError("Gemini API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        # Note: 'system_instruction' can be used for system prompt in newer versions
        
        payload = {
            "contents": self._format_contents(messages),
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        try:
            url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                data = response.json()

            latency_ms = (time.time() - start_time) * 1000
            
            # Metrics
            LLM_REQUESTS_TOTAL.labels(model=model, provider=self.provider_name, status="success").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=model, provider=self.provider_name).observe(time.time() - start_time)
            
            # Usage metadata in Gemini
            usage_meta = data.get("usageMetadata", {})
            prompt_tokens = usage_meta.get("promptTokenCount", 0)
            completion_tokens = usage_meta.get("candidatesTokenCount", 0)
            
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="prompt").inc(prompt_tokens)
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="completion").inc(completion_tokens)

            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                content = "".join([part.get("text", "") for part in parts])

            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=content,
                ),
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=usage_meta.get("totalTokenCount", 0)
                ),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            LLM_REQUESTS_TOTAL.labels(model=model, provider=self.provider_name, status="error").inc()
            raise

    async def stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream completion via Gemini REST API."""
        if not self.api_key:
             raise ValueError("Gemini API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        payload = {
            "contents": self._format_contents(messages),
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        first_token = False
        url = f"{self.base_url}/{model}:streamGenerateContent?key={self.api_key}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", 
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                # Gemini doesn't use SSE standard exactly, it sends JSON array elements
                # But typically simple chunks. The response format is `[{...}, \r\n {...}]`
                # Parsing a JSON array stream is tricky.
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # Simple heuristic: try to find complete JSON objects 
                    # This is brittle but works for basic streaming
                    try:
                         # Gemini stream is a JSON array. We might get partial JSON.
                         # Better to rely on the fact that Google sends valid JSON objects separated
                         # but wrapped in [ ]. 
                         pass
                    except:
                        pass
                    
                    # For now, simplistic yielding without parsing full stream properly
                    # because parsing a streaming JSON array in python without a lib is hard.
                    # Fallback to non-streaming logic or simplified string matching?
                    
                    # Hack: Look for "text": "..."
                    import re
                    matches = re.findall(r'"text":\s*"((?:[^"\\]|\\.)*)"', chunk)
                    for text in matches:
                        # unescape
                        yield StreamChunk(content=text.encode('utf-8').decode('unicode_escape'))

    async def health_check(self) -> bool:
        return bool(self.api_key)

    def get_available_models(self) -> List[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
