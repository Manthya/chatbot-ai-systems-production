"""FastAPI server routes for the chatbot API."""

import logging
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from chatbot_ai_system.config import get_settings
from chatbot_ai_system.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationInfo,
    ErrorResponse,
    HealthResponse,
    MessageRole,
    StreamChunk,
)
from chatbot_ai_system.providers import OllamaProvider

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Provider instances
_providers: Dict[str, OllamaProvider] = {}

# In-memory conversation storage (will be replaced with DB in Phase 2)
_conversations: Dict[str, List[ChatMessage]] = {}


def get_provider(name: str = "ollama") -> OllamaProvider:
    """Get or create a provider instance."""
    if name not in _providers:
        if name == "ollama":
            _providers[name] = OllamaProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")
    return _providers[name]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from chatbot_ai_system import __version__

    provider_status = {}

    # Check Ollama
    try:
        ollama = get_provider("ollama")
        provider_status["ollama"] = await ollama.health_check()
    except Exception:
        provider_status["ollama"] = False

    return HealthResponse(
        status="healthy" if any(provider_status.values()) else "degraded",
        version=__version__,
        providers=provider_status,
    )


@router.post("/api/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """Generate a chat completion.

    Args:
        request: Chat request with messages and options

    Returns:
        ChatResponse with the generated message
    """
    settings = get_settings()
    provider_name = request.provider or settings.default_llm_provider

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []

    # Add user messages to conversation history
    for msg in request.messages:
        if msg not in _conversations[conversation_id]:
            _conversations[conversation_id].append(msg)

    try:
        # Get all messages for context
        all_messages = _conversations[conversation_id]

        response = await provider.complete(
            messages=all_messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Add assistant response to conversation history
        _conversations[conversation_id].append(response.message)

        response.conversation_id = conversation_id
        return response

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {e}")


@router.get("/api/conversations", response_model=List[ConversationInfo])
async def list_conversations():
    """List all conversations."""
    conversations = []
    for conv_id, messages in _conversations.items():
        if messages:
            conversations.append(
                ConversationInfo(
                    id=conv_id,
                    title=messages[0].content[:50] if messages else "New Conversation",
                    message_count=len(messages),
                    created_at=messages[0].timestamp if messages else datetime.utcnow(),
                    updated_at=messages[-1].timestamp if messages else datetime.utcnow(),
                )
            )
    return conversations


@router.get("/api/conversations/{conversation_id}", response_model=List[ChatMessage])
async def get_conversation(conversation_id: str):
    """Get messages for a specific conversation."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversations[conversation_id]


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del _conversations[conversation_id]
    return {"status": "deleted", "conversation_id": conversation_id}


@router.websocket("/api/chat/stream")
async def websocket_chat_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses.

    Protocol:
    1. Client connects to WebSocket
    2. Client sends JSON message with ChatRequest format
    3. Server streams back StreamChunk objects
    4. Final chunk has done=True
    """
    await websocket.accept()
    settings = get_settings()
    is_connected = True

    try:
        while is_connected:
            # Receive message from client
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                is_connected = False
                break
            except Exception as e:
                logger.warning(f"Error receiving message: {e}")
                is_connected = False
                break

            try:
                request = ChatRequest(**data)
            except Exception as e:
                if is_connected:
                    try:
                        await websocket.send_json(
                            ErrorResponse(error="Invalid request", detail=str(e)).model_dump()
                        )
                    except Exception:
                        is_connected = False
                continue

            provider_name = request.provider or settings.default_llm_provider

            try:
                provider = get_provider(provider_name)
            except ValueError as e:
                if is_connected:
                    try:
                        await websocket.send_json(
                            ErrorResponse(error="Invalid provider", detail=str(e)).model_dump()
                        )
                    except Exception:
                        is_connected = False
                continue

            # Get or create conversation
            conversation_id = request.conversation_id or str(uuid.uuid4())
            if conversation_id not in _conversations:
                _conversations[conversation_id] = []

            # Add messages to conversation
            for msg in request.messages:
                if msg not in _conversations[conversation_id]:
                    _conversations[conversation_id].append(msg)

            try:
                # Stream response
                full_content = ""
                async for chunk in provider.stream(
                    messages=_conversations[conversation_id],
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                ):
                    if not is_connected:
                        break
                    full_content += chunk.content
                    chunk.conversation_id = conversation_id
                    try:
                        await websocket.send_json(chunk.model_dump())
                    except Exception as send_error:
                        logger.warning(f"Error sending chunk: {send_error}")
                        is_connected = False
                        break

                if is_connected and full_content:
                    # Add assistant message to conversation
                    _conversations[conversation_id].append(
                        ChatMessage(role=MessageRole.ASSISTANT, content=full_content)
                    )

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                if is_connected:
                    try:
                        await websocket.send_json(
                            ErrorResponse(error="Streaming failed", detail=str(e)).model_dump()
                        )
                    except Exception:
                        is_connected = False

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket connection closed")

