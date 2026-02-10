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
        all_messages = list(_conversations[conversation_id])
        
        # Add system prompt if not present to guide tool use
        if not any(m.role == MessageRole.SYSTEM for m in all_messages):
            system_prompt = (
                "You are a helpful AI assistant with access to local tools via MCP. "
                "1. If you need information, select a tool and output its call in a JSON block. "
                "2. You will then receive the tool's result in the next message. "
                "3. Use the result to answer the user's question. DO NOT repeat the tool call if you have already received a result.\n"
                "Format tool calls as: ```json\n{\"name\": \"...\", \"arguments\": {...}}\n```"
            )
            all_messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))

        max_turns = 5
        final_response = None

        for _ in range(max_turns):
            response = await provider.complete(
                messages=all_messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=await registry.get_ollama_tools(),
            )

            # If the response contains tool calls, clear the content to avoid
            # confusing the model with its own raw JSON in the next turn's history.
            if response.message.tool_calls:
                response.message.content = ""
            
            # Important: Update all_messages so the LLM sees its own response in next turn
            all_messages.append(response.message)
            _conversations[conversation_id].append(response.message)
            final_response = response

            # Check for tool calls
            if not response.message.tool_calls:
                break

            # Execute tools
            for tool_call in response.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                try:
                    tool = registry.get_tool(tool_name)
                    result = await tool.run(**tool_args)
                except Exception as e:
                    result = f"Error executing tool {tool_name}: {e}"

                # Add tool result to history
                tool_msg = ChatMessage(
                    role=MessageRole.TOOL,
                    content=str(result),
                    tool_call_id=tool_call.id
                )
                all_messages.append(tool_msg)
                _conversations[conversation_id].append(tool_msg)

        if final_response:
            final_response.conversation_id = conversation_id
            return final_response
        else:
             raise HTTPException(status_code=500, detail="No response generated")

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
                # Add default system prompt for context
                _conversations[conversation_id].append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "You are a helpful AI assistant with access to tools. Use tools only when "
                        "the user's request requires them. For greetings and general conversation, "
                        "respond naturally in plain text."
                    )
                ))

            # Add new messages from client
            # We use a combined hash of role and content to deduplicate
            history_fingerprints = [(m.role, m.content) for m in _conversations[conversation_id]]
            for msg in request.messages:
                if (msg.role, msg.content) not in history_fingerprints:
                    _conversations[conversation_id].append(msg)
                    history_fingerprints.append((msg.role, msg.content))

            try:
                # Tool loop for streaming
                max_turns = 5
                
                for _ in range(max_turns):
                    full_content = ""
                    current_tool_calls = []
                    
                    # Stream response
                    async for chunk in provider.stream(
                        messages=_conversations[conversation_id],
                        model=request.model,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        tools=await registry.get_ollama_tools(),
                    ):
                        if not is_connected:
                            break
                        
                        full_content += chunk.content
                        
                        if chunk.tool_calls:
                            current_tool_calls.extend(chunk.tool_calls)
                            
                        chunk.conversation_id = conversation_id
                        
                        # Suppress 'done' if we are in the middle of tool processing
                        # We will send a final 'done' chunk ourselves later if needed
                        if chunk.done:
                            continue

                        try:
                            await websocket.send_json(chunk.model_dump())
                        except Exception as send_error:
                            logger.warning(f"Error sending chunk: {send_error}")
                            is_connected = False
                            break
                    
                    if not is_connected:
                        break
                    
                    # Fallback: support models like Qwen that output raw JSON in content
                    if not current_tool_calls and full_content:
                        parsed_tool_calls = provider._try_parse_tool_calls(full_content)
                        if parsed_tool_calls:
                            current_tool_calls = parsed_tool_calls
                            logger.info(f"Fallback: Parsed {len(current_tool_calls)} tool calls from content text.")

                    # Add assistant message to conversation
                    # Clear content if tool calls are present (consistent with chat_completion fix)
                    stored_content = full_content if not current_tool_calls else ""
                    assistant_msg = ChatMessage(
                        role=MessageRole.ASSISTANT, 
                        content=stored_content,
                        tool_calls=current_tool_calls
                    )
                    _conversations[conversation_id].append(assistant_msg)

                    # If no tool calls, we are done - send a final done chunk
                    if not current_tool_calls:
                        try:
                            final_chunk = StreamChunk(content="", done=True, conversation_id=conversation_id)
                            await websocket.send_json(final_chunk.model_dump())
                        except Exception:
                            pass
                        break
                        
                    # Execute tools
                    for tc in current_tool_calls:
                        tool_name = tc.function.name
                        tool_args = tc.function.arguments
                        
                        # Yield "Thinking" status chunk
                        if is_connected:
                            try:
                                status_chunk = StreamChunk(
                                    content="",
                                    status=f"Thinking: {tool_name}...",
                                    conversation_id=conversation_id
                                )
                                await websocket.send_json(status_chunk.model_dump())
                            except Exception:
                                pass

                        logger.info(f"Streaming turn: Executing tool {tool_name}")
                        try:
                            tool = registry.get_tool(tool_name)
                            result = await tool.run(**tool_args)
                        except Exception as e:
                            result = f"Error executing tool {tool_name}: {e}"
                            
                        _conversations[conversation_id].append(
                            ChatMessage(
                                role=MessageRole.TOOL, 
                                content=str(result),
                                tool_call_id=tc.id
                            )
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

