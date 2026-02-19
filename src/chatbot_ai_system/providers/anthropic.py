"""Anthropic LLM provider implementation using httpx."""

import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple

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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider using direct HTTP API."""

    provider_name = "anthropic"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.anthropic_api_key
        self.default_model = settings.anthropic_model or "claude-3-haiku-20240307"
        self.base_url = "https://api.anthropic.com/v1"
        
        if not self.api_key:
            logger.warning("Anthropic API key not configured.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _format_messages(self, messages: List[ChatMessage]) -> Tuple[Optional[str], List[Dict]]:
        """Format messages for Anthropic API.
        
        Returns:
            Tuple of (system_prompt, messages_list)
        """
        system_prompt = None
        formatted_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            elif msg.role == MessageRole.TOOL:
                # Anthropic tool use is complex, skipping for this optional implementation
                # or mapping to user role with context
                formatted_messages.append({
                    "role": "user",
                    "content": f"Tool Result [{msg.tool_call_id}]: {msg.content}"
                })
            else:
                formatted_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return system_prompt, formatted_messages

    async def complete(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> ChatResponse:
        """Generate completion via Anthropic REST API."""
        if not self.api_key:
             raise ValueError("Anthropic API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        system, fmt_messages = self._format_messages(messages)
        
        payload = {
            "model": model,
            "messages": fmt_messages,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

            latency_ms = (time.time() - start_time) * 1000
            
            # Metrics
            LLM_REQUESTS_TOTAL.labels(model=model, provider=self.provider_name, status="success").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=model, provider=self.provider_name).observe(time.time() - start_time)
            
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="prompt").inc(input_tokens)
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="completion").inc(output_tokens)

            content_blocks = data.get("content", [])
            text_content = "".join([block["text"] for block in content_blocks if block["type"] == "text"])

            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=text_content,
                ),
                usage=UsageInfo(
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens
                ),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
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
        """Stream completion via Anthropic REST API."""
        if not self.api_key:
             raise ValueError("Anthropic API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        system, fmt_messages = self._format_messages(messages)
        
        payload = {
            "model": model,
            "messages": fmt_messages,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
            "stream": True
        }
        if system:
            payload["system"] = system

        first_token = False
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", 
                f"{self.base_url}/messages",
                json=payload,
                headers=self._get_headers()
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "): continue
                    
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type")
                        
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                if not first_token:
                                    LLM_TTFT_SECONDS.labels(model=model, provider=self.provider_name).observe(time.time() - start_time)
                                    first_token = True
                                    
                                yield StreamChunk(content=delta.get("text", ""))
                                
                        elif event_type == "message_stop":
                            yield StreamChunk(content="", done=True)
                            
                    except json.JSONDecodeError:
                        continue

    async def health_check(self) -> bool:
        # Anthropic doesn't have a simple health/models endpoint without auth
        # We'll just check if we can make a dummy request or simply true if key exists
        return bool(self.api_key)

    def get_available_models(self) -> List[str]:
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
