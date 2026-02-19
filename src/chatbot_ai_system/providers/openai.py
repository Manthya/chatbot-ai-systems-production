"""OpenAI LLM provider implementation using httpx."""

import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional
import uuid

import httpx
from chatbot_ai_system.config import get_settings
from chatbot_ai_system.models.schemas import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    StreamChunk,
    UsageInfo,
    ToolCall,
    ToolCallFunction,
)
from chatbot_ai_system.observability.metrics import (
    LLM_REQUESTS_TOTAL,
    LLM_REQUEST_DURATION_SECONDS,
    LLM_TOKENS_TOTAL,
    LLM_TTFT_SECONDS,
)
from chatbot_ai_system.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using direct HTTP API (no SDK dependency)."""

    provider_name = "openai"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.default_model = settings.openai_model or "gpt-4o-mini"
        self.base_url = "https://api.openai.com/v1"
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured. Provider will fail if used.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict]:
        """Format messages for OpenAI API."""
        formatted = []
        for msg in messages:
            m = {"role": msg.role.value, "content": msg.content}
            
            # Map tool calls
            if msg.tool_calls:
                 m["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": json.dumps(tc.function.arguments) if isinstance(tc.function.arguments, dict) else tc.function.arguments
                        }
                    } for tc in msg.tool_calls
                ]
                 if not m.get("content"):
                     m["content"] = None # OpenAI requires null content if tool_calls present

            # Map tool results
            if msg.role == MessageRole.TOOL:
                m["tool_call_id"] = msg.tool_call_id

            # TODO: Handle images (multimodal) if needed
            formatted.append(m)
        return formatted

    async def complete(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> ChatResponse:
        """Generate completion via OpenAI REST API."""
        if not self.api_key:
             raise ValueError("OpenAI API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

            latency_ms = (time.time() - start_time) * 1000
            
            # Metrics
            LLM_REQUESTS_TOTAL.labels(model=model, provider=self.provider_name, status="success").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=model, provider=self.provider_name).observe(time.time() - start_time)
            
            usage_data = data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="prompt").inc(prompt_tokens)
            LLM_TOKENS_TOTAL.labels(model=model, provider=self.provider_name, type="completion").inc(completion_tokens)

            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content")
            
            tool_calls = None
            if message.get("tool_calls"):
                tool_calls = []
                for tc in message["tool_calls"]:
                    tool_calls.append(ToolCall(
                        id=tc["id"],
                        function=ToolCallFunction(
                            name=tc["function"]["name"],
                            arguments=json.loads(tc["function"]["arguments"])
                        )
                    ))

            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=content,
                    tool_calls=tool_calls
                ),
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=usage_data.get("total_tokens", 0)
                ),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        """Stream completion via OpenAI REST API."""
        if not self.api_key:
             raise ValueError("OpenAI API key not configured")

        model = model or self.default_model
        start_time = time.time()
        
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "stream": True
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        first_token = False
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", 
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._get_headers()
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line or line.strip() == "": continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            
                            if not first_token:
                                LLM_TTFT_SECONDS.labels(model=model, provider=self.provider_name).observe(time.time() - start_time)
                                first_token = True

                            content = delta.get("content")
                            
                            # Streaming tool calls is complex, handling simplified version here
                            # (Accumulating tool calls in the orchestrator is better, 
                            #  but for now we just pass partials if they exist)
                            tool_calls = None
                            if delta.get("tool_calls"):
                                # This logic is tricky for streaming JSON fragments. 
                                # For a robust implementation, we might need a stateful parser.
                                # For this pass, we'll focus on content streaming.
                                pass

                            if content:
                                yield StreamChunk(content=content)
                                
                        except json.JSONDecodeError:
                            continue

    async def health_check(self) -> bool:
        if not self.api_key: return False
        try:
            async with httpx.AsyncClient() as client:
                # Check models endpoint
                resp = await client.get(
                    f"{self.base_url}/models", 
                    headers=self._get_headers()
                )
                return resp.status_code == 200
        except:
            return False

    def get_available_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
