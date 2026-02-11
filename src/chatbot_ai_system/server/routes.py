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
    ToolCall,
)
from chatbot_ai_system.providers import OllamaProvider
from chatbot_ai_system.tools import registry
from chatbot_ai_system.orchestrator import ChatOrchestrator

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
        # Orchestrator expects the new messages to be in history or passed as input?
        # Orchestrator.run takes (user_input, conversation_history).
        # We need to ensure the user message is added to history first (which it is, lines 91-95).
        
        # We need to find the user query from the request
        user_msg = request.messages[-1] # content-wise, or iterate
        # logic at lines 92-94 adds them.
        # But we need the query string for orchestrator.
        if request.messages:
             user_query = request.messages[-1].content
             if request.messages[-1].role != MessageRole.USER:
                 # fallback if last message isn't user (rare)
                 user_query = "Process the conversation context."
        else:
             raise HTTPException(status_code=400, detail="No messages provided")

        # Initialize Orchestrator
        orchestrator = ChatOrchestrator(provider=provider, registry=registry)
        
        full_content = ""
        tool_calls = []
        
        # Run Orchestrator and consume stream
        async for chunk in orchestrator.run(
            user_input=user_query,
            conversation_history=_conversations[conversation_id], # Pass mutable list
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 1000
        ):
             full_content += chunk.content
             if chunk.tool_calls:
                 tool_calls.extend(chunk.tool_calls)
        
        # Construct final response
        # The orchestrator should have updated `_conversations[conversation_id]` with the final response
        # so we can just return the last message from history?
        # BUT `ChatResponse` expects the generated message.
        # And we need usage info (which orchestrator streaming doesn't provide easily yet... oops).
        # We'll mock usage for now or improve Orchestrator later.
        
        # We'll return the aggregated content.
        
        response_msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=full_content,
            tool_calls=tool_calls if tool_calls else None
        )
        
        return ChatResponse(
            message=response_msg,
            usage=None, # Orchestrator stream doesn't bubble usage yet
            model=request.model or settings.default_llm_provider,
            provider=provider_name
        )

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        # Log stack trace
        import traceback
        traceback.print_exc()
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

            # Add new messages from client
            # We use a combined hash of role and content to deduplicate
            history_fingerprints = [(m.role, m.content) for m in _conversations[conversation_id]]
            new_user_message = None
            for msg in request.messages:
                if (msg.role, msg.content) not in history_fingerprints:
                    _conversations[conversation_id].append(msg)
                    history_fingerprints.append((msg.role, msg.content))
                    if msg.role == MessageRole.USER:
                        new_user_message = msg

            # If no new user message (e.g. just connecting), find the last one
            if not new_user_message:
                for m in reversed(_conversations[conversation_id]):
                    if m.role == MessageRole.USER:
                        new_user_message = m
                        break
            
            if not new_user_message:
                 continue # Should not happen in normal flow

            user_query = new_user_message.content

            try:
                # Initialize Orchestrator
                orchestrator = ChatOrchestrator(provider=provider, registry=registry)
                
                # Run Orchestrator
                # We pass the conversion_id mostly for tracking, but here we pass the HISTORY list
                # _conversations[conversation_id] is the list we want to update.
                
                async for chunk in orchestrator.run(
                    user_input=user_query,
                    conversation_history=_conversations[conversation_id],
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens or 1000
                ):
                    if not is_connected:
                        break
                    
                    chunk.conversation_id = conversation_id
                    
                    try:
                        await websocket.send_json(chunk.model_dump())
                    except Exception:
                        is_connected = False
                        break
                
                # Final Done Chunk
                if is_connected:
                    try:
                        await websocket.send_json(StreamChunk(content="", done=True, conversation_id=conversation_id).model_dump())
                    except Exception:
                        pass

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


