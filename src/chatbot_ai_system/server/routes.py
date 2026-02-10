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
                # Phase 1.2: We don't add a static system prompt here anymore. 
                # We inject dynamic system prompts based on the planning phase.

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
                # --- STEP 1 & 5: PLANNING PHASE ---
                # Decide if tool is needed
                
                logger.info(f"PLANNING: Assessing need for tools for query: '{user_query}'")
                
                planning_messages = [
                    ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=(
                            "You are a routing agent. Your job is to decide if the user's request requires external tools.\n"
                            "Return ONLY 'USE_TOOL' if the request involves: file system access, git operations, fetching URLs, or checking system time.\n"
                            "Return ONLY 'NO_TOOL' if the request is: general knowledge, coding help (without reading files), greetings, or small talk.\n"
                            "Answer with exactly one word."
                        )
                    ),
                    ChatMessage(role=MessageRole.USER, content=user_query)
                ]
                
                planning_response = await provider.complete(
                    messages=planning_messages,
                    model=request.model, # Use same model for planning
                    max_tokens=10,
                    temperature=0.1 # Low temp for determinism
                )
                
                decision = planning_response.message.content.strip().upper()
                # Fallback if model is chatty
                if "USE_TOOL" in decision:
                    decision = "USE_TOOL"
                else:
                    decision = "NO_TOOL"
                    
                logger.info(f"PLANNING DECISION: {decision}")

                # --- STEP 2 & 8: TOOL FILTERING ---
                target_tools = []
                if decision == "USE_TOOL":
                    target_tools = await registry.get_ollama_tools(query=user_query)
                    if not target_tools:
                        logger.info("PLANNING: Decision was USE_TOOL but no relevant tools found. Reverting to NO_TOOL.")
                        decision = "NO_TOOL"
                    else:
                        tool_names = [t['function']['name'] for t in target_tools]
                        logger.info(f"PLANNING: Tools exposed: {tool_names}")

                # --- STEP 3 & 4: EXECUTION / JSON ENFORCEMENT ---
                
                current_turn_messages = list(_conversations[conversation_id])
                
                # Dynamic System Prompt
                if decision == "USE_TOOL":
                    system_instructions = (
                        "You are an AI assistant with access to external tools.\n"
                        "RULES:\n"
                        "1. You MUST call one of the provided tools to answer the question.\n"
                        "2. Return ONLY a valid JSON tool call in the format {\"name\": \"...\", \"arguments\": {...}}.\n"
                        "3. Do NOT explain your thought process or talk. Just output the JSON."
                    )
                else:
                    system_instructions = (
                        "You are a helpful AI assistant.\n"
                        "No external tools are available or needed for this question.\n"
                        "Answer using your internal knowledge only.\n"
                        "Respond in natural language."
                    )

                # Inject strict system prompt for this turn
                # We replace any existing system prompt or append a specific one for this turn
                current_turn_messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_instructions))

                
                full_content = ""
                current_tool_calls = []
                final_answer_source = "MODEL"

                async for chunk in provider.stream(
                    messages=current_turn_messages,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    tools=target_tools if decision == "USE_TOOL" else None,
                ):
                    if not is_connected:
                        break
                    
                    full_content += chunk.content
                    
                    if chunk.tool_calls:
                        current_tool_calls.extend(chunk.tool_calls)
                        
                    chunk.conversation_id = conversation_id
                    
                    if chunk.done:
                        continue

                    # If we are in USE_TOOL mode, we suppress content chunks until we confirm it's not a tool call
                    # ignoring this for now to keep UI responsive, but for strict JSON we might want to buffer?
                    # Qwen usually outputs JSON directly.
                    
                    try:
                        await websocket.send_json(chunk.model_dump())
                    except Exception:
                        is_connected = False
                        break
                
                if not is_connected:
                    break
                
                # --- Fallback Parsing for Qwen ---
                if decision == "USE_TOOL" and not current_tool_calls and full_content:
                     parsed_tool_calls = provider._try_parse_tool_calls(full_content)
                     if parsed_tool_calls:
                        current_tool_calls = parsed_tool_calls
                        logger.info(f"Fallback: Parsed tool calls from content: {len(current_tool_calls)}")
                        # If we parsed tool calls from content, we should probably clear the content displayed to user
                        # implying the previous chunks were "thinking" / JSON raw.
                        # But we already sent them. This is a UI UX nuance. 
                        # For now, we proceed.

                # Update conversation history
                stored_content = full_content if not current_tool_calls else ""
                assistant_msg = ChatMessage(
                    role=MessageRole.ASSISTANT, 
                    content=stored_content,
                    tool_calls=current_tool_calls
                )
                _conversations[conversation_id].append(assistant_msg) # Persist to history

                # --- STEP 6: SYNTHESIS Phase ---
                if current_tool_calls:
                    final_answer_source = "TOOL"
                    
                    for tc in current_tool_calls:
                        tool_name = tc.function.name
                        tool_args = tc.function.arguments
                        
                         # Yield "Thinking" status
                        if is_connected:
                            try:
                                await websocket.send_json(StreamChunk(content="", status=f"Thinking: {tool_name}...", conversation_id=conversation_id).model_dump())
                            except Exception:
                                pass

                        logger.info(f"EXECUTING TOOL: {tool_name}")
                        try:
                            tool = registry.get_tool(tool_name)
                            result = await tool.run(**tool_args)
                        except Exception as e:
                            # Step 7: Tool Failure Fallback
                            result = f"Error: The tool execution failed: {str(e)}"

                        tool_msg = ChatMessage(
                             role=MessageRole.TOOL,
                             content=str(result),
                             tool_call_id=tc.id
                        )
                        _conversations[conversation_id].append(tool_msg)
                        
                        # Append to current context for synthesis
                        current_turn_messages.append(assistant_msg)
                        current_turn_messages.append(tool_msg)

                    # Synthesis call
                    synthesis_system_msg = ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=(
                            "Tool result:\n"
                            f"{str(result)[:2000]}...\n\n" # Truncate for safety/context window?
                            "Using ONLY the tool result above, answer the original question clearly."
                        )
                    )
                    # We might want to just append this instruction as a user message or system message at end
                    # Replacing the strict tool system prompt
                    current_turn_messages = [m for m in current_turn_messages if m.role != MessageRole.SYSTEM]
                    current_turn_messages.insert(0, synthesis_system_msg)

                    async for chunk in provider.stream(
                        messages=current_turn_messages,
                        model=request.model,
                        tools=None # No tools for synthesis
                    ):
                         if not is_connected: break
                         # Send synthesis chunks
                         try:
                            await websocket.send_json(chunk.model_dump())
                         except Exception:
                            is_connected = False
                            break
                            
                    # Start tracking synthesis response (not implementing separate history append for synthesis 
                    # as it usually flows as one turn in UI, but backend stores it as separate assistant msg? 
                    # Standard ollama flow appends synthesis as a new assistant message)
                    full_synthesis = "" # Capture if needed for logs
                    
                # Final Done Chunk
                if is_connected:
                    try:
                        await websocket.send_json(StreamChunk(content="", done=True, conversation_id=conversation_id).model_dump())
                    except Exception:
                        pass
                
                logger.info(f"REQUEST COMPLETE. Source: {final_answer_source}")


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

