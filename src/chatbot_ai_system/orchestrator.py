"""
Chat Orchestrator Module.

This module implements the 9-phase architecture for handling chat requests,
including intent classification, tool scope reduction, and orchestrating
the interaction between the LLM and MCP tools.
"""

import logging
import json
from typing import List, Optional, Dict, Any, AsyncGenerator

from chatbot_ai_system.models.schemas import (
    ChatMessage,
    MessageRole,
    StreamChunk,
    ToolCall,
)
from chatbot_ai_system.providers.ollama import OllamaProvider
from chatbot_ai_system.tools.registry import ToolRegistry
from chatbot_ai_system.tools import registry

logger = logging.getLogger(__name__)

class ChatOrchestrator:
    """
    Orchestrates the chat flow, handling intent classification,
    tool selection, and LLM interaction.
    """

    def __init__(
        self, 
        provider: OllamaProvider, 
        registry: ToolRegistry,
        conversation_repo: Any, # Avoid circular import type hint issues or use TYPE_CHECKING
        memory_repo: Any
    ):
        self.provider = provider
        self.registry = registry
        self.conversation_repo = conversation_repo
        self.memory_repo = memory_repo

    async def run(
        self,
        conversation_id: str,
        user_input: str,
        conversation_history: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Main entry point for the orchestrator (Phase 3).
        """
        import uuid
        conv_uuid = uuid.UUID(conversation_id)

        # Fetch Long-Term Memory (Phase 2 Addition)
        if user_id:
            try:
                memories = await self.memory_repo.get_user_memories(uuid.UUID(user_id))
                user_context = "\nUser Profile:\n" + "\n".join([f"- {m.content}" for m in memories])
            except Exception as e:
                logger.error(f"Failed to fetch memories: {e}")
                user_context = ""
        else:
            user_context = ""

        # --- Phase 4: Intent Classification ---
        intent = await self._classify_intent(user_input, model)
        logger.info(f"Phase 4: Classified intent as '{intent}'")

        # --- Phase 5: Tool Scope Reduction ---
        tools = await self._filter_tools(intent, user_input)
        logger.info(f"Phase 5: Selected tools: {[t['function']['name'] for t in tools]}")

        # Prepare messages
        messages = list(conversation_history)
        current_seq = len(conversation_history) # Start sequence number
        
        # Inject Dynamic System Prompt
        system_prompt = self._get_system_prompt(intent, bool(tools))
        if user_context:
            system_prompt += user_context

        if messages and messages[0].role == MessageRole.SYSTEM:
            messages[0] = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
        else:
            messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
            
        # --- Phase 6: First LLM Call (Planning) ---
        current_tool_calls: List[ToolCall] = []
        full_content = ""
        
        # Streaming loop
        async for chunk in self.provider.stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools if tools else None
        ):
            full_content += chunk.content
            if chunk.tool_calls:
                current_tool_calls.extend(chunk.tool_calls)
            
            if not current_tool_calls:
                yield chunk
            else:
                 pass

        # Check for fallback parsing (Phase 6b)
        if not current_tool_calls and tools:
             parsed = self.provider._try_parse_tool_calls(full_content)
             if parsed:
                 current_tool_calls = parsed

        # --- Phase 7: Tool Execution ---
        if current_tool_calls:
            # Append assistant message with tool calls
            assistant_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=full_content,
                tool_calls=current_tool_calls
            )
            messages.append(assistant_msg)
            
            # Persist to DB
            current_seq += 1
            await self.conversation_repo.add_message(
                conversation_id=conv_uuid,
                role=MessageRole.ASSISTANT,
                content=full_content,
                sequence_number=current_seq,
                tool_calls=[t.model_dump() for t in current_tool_calls],
                metadata={"model": model}
            )
            
            # Execute tools
            for tool_call in current_tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                
                yield StreamChunk(content="", status=f"Executing {tool_name}...", done=False)
                
                try:
                    tool = self.registry.get_tool(tool_name)
                    result = await tool.run(**tool_args)
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result = f"Error executing tool {tool_name}: {e}"

                # Persist result
                current_seq += 1
                tool_msg = ChatMessage(role=MessageRole.TOOL, content=str(result), tool_call_id=tool_call.id)
                messages.append(tool_msg)
                
                await self.conversation_repo.add_message(
                    conversation_id=conv_uuid,
                    role=MessageRole.TOOL,
                    content=str(result),
                    sequence_number=current_seq,
                    tool_call_id=tool_call.id
                )

            # --- Phase 8: Tool Result Feedback Loop ---
            synthesis_content = ""
            async for chunk in self.provider.stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=None
            ):
                synthesis_content += chunk.content
                yield chunk
            
            # Persist synthesis
            current_seq += 1
            await self.conversation_repo.add_message(
                conversation_id=conv_uuid,
                role=MessageRole.ASSISTANT,
                content=synthesis_content,
                sequence_number=current_seq,
                metadata={"model": model, "type": "synthesis"}
            )
            
        else:
             # Persist final response
             current_seq += 1
             await self.conversation_repo.add_message(
                conversation_id=conv_uuid,
                role=MessageRole.ASSISTANT,
                content=full_content,
                sequence_number=current_seq,
                metadata={"model": model}
             )

    async def _classify_intent(self, user_input: str, model: str) -> str:
        """
        Phase 4: Classify user intent to determine tool needs.
        """
        # Simple zero-shot classifier
        classifier_messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "You are an intent classifier. Analyze the user's request.\n"
                    "Categories:\n"
                    "1. GIT: Version control, commits, branches, diffs.\n"
                    "2. FILESYSTEM: Reading/writing files, listing directories, searching.\n"
                    "3. FETCH: Web requests, extracting content from URLs.\n"
                    "4. GENERAL: General knowledge, coding advice (without file access), greetings.\n"
                    "Output ONLY the category name (e.g., 'GIT')."
                )
            ),
            ChatMessage(role=MessageRole.USER, content=user_input)
        ]
        
        response = await self.provider.complete(
            messages=classifier_messages,
            model=model,
            max_tokens=10,
            temperature=0.1
        )
        
        intent = response.message.content.strip().upper()
        # Fallback normalization
        if "GIT" in intent: return "GIT"
        if "FILE" in intent: return "FILESYSTEM"
        if "FETCH" in intent: return "FETCH"
        return "GENERAL"

    async def _filter_tools(self, intent: str, user_input: str) -> List[Dict[str, Any]]:
        """
        Phase 5: Reduce tool scope based on intent.
        """
        if intent == "GENERAL":
            return []
            
        all_tools = await self.registry.get_ollama_tools(query=user_input)
        
        filtered = []
        for tool in all_tools:
            name = tool['function']['name']
            if intent == "GIT" and ("git" in name or "repo" in name):
                filtered.append(tool)
            elif intent == "FILESYSTEM" and any(x in name for x in ["file", "dir", "list", "read", "write", "search"]):
                filtered.append(tool)
            elif intent == "FETCH" and "fetch" in name:
                filtered.append(tool)
                
        return filtered

    def _get_system_prompt(self, intent: str, has_tools: bool) -> str:
        """
        Get the appropriate system prompt based on intent and tool availability.
        """
        base_prompt = "You are a helpful AI assistant."
        
        if not has_tools:
           return base_prompt + "\nAnswer using your internal knowledge. Do notHALLUCINATE tools."
           
        tool_instructions = (
            "\nYou have access to external tools via MCP.\n"
            "1. If the user's request requires it, call the appropriate tool.\n"
            "2. Output a valid JSON tool call.\n"
            "3. Use the tool result to answer the question."
        )
        
        return base_prompt + tool_instructions
