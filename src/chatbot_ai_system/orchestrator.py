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

    def __init__(self, provider: OllamaProvider, registry: ToolRegistry):
        self.provider = provider
        self.registry = registry

    async def run(
        self,
        user_input: str,
        conversation_history: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Main entry point for the orchestrator (Phase 3).
        
        Executes the following phases:
        Phase 4: Intent Classification
        Phase 5: Tool Scope Reduction
        Phase 6: First LLM Call (Planning)
        Phase 7: Tool Execution
        Phase 8: Tool Result Feedback Loop
        Phase 9: Response Return
        """
        
        # --- Phase 4: Intent Classification ---
        intent = await self._classify_intent(user_input, model)
        logger.info(f"Phase 4: Classified intent as '{intent}'")

        # --- Phase 5: Tool Scope Reduction ---
        tools = await self._filter_tools(intent, user_input)
        logger.info(f"Phase 5: Selected tools: {[t['function']['name'] for t in tools]}")

        # --- Phase 5: Tool Scope Reduction ---
        tools = await self._filter_tools(intent, user_input)
        logger.info(f"Phase 5: Selected tools: {[t['function']['name'] for t in tools]}")

        # Prepare messages
        # We work directly with conversation_history to persist changes?
        # A safer approach for list modification:
        # We use a working copy for the LLM context (to inject system prompt without messing up history permanently if needed)
        # BUT we must append new messages (Assistant, Tool) to the persistent history.
        
        messages = list(conversation_history)
        
        # Inject Dynamic System Prompt for this turn
        # We replace any existing system prompt in the WORKING COPY only, 
        # or we update the history? 
        # Let's update the working copy.
        system_prompt = self._get_system_prompt(intent, bool(tools))
        
        if messages and messages[0].role == MessageRole.SYSTEM:
            messages[0] = ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
        else:
            messages.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
            
        # Ensure user message is at the end (should be handling in routes, but let's be safe)
        # routes.py appends the user message before calling run.
        
        # --- Phase 6: First LLM Call (Planning) ---
        
        # --- Phase 6: First LLM Call (Planning) ---
        # We need to stream the response.
        
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
            
            # Yield content to user immediately if it's text
            # If we are strictly expecting JSON for tools, we might want to suppress
            # but for better UX we often stream.
            if not current_tool_calls:
                yield chunk
            else:
                 # If we have tool calls, we might stop yielding text if the model is just outputting JSON
                 # But if it's "I will check that for you...", we want to show it.
                 # Qwen often outputs strictly JSON if asked.
                 pass

        # Check for fallback parsing (Phase 6b)
        if not current_tool_calls and tools:
             parsed = self.provider._try_parse_tool_calls(full_content)
             if parsed:
                 current_tool_calls = parsed
                 logger.info(f"Fallback: Parsed tool calls from content: {len(current_tool_calls)}")

        # --- Phase 7: Tool Execution ---
        if current_tool_calls:
            # Append assistant message with tool calls to history
            assistant_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=full_content,
                tool_calls=current_tool_calls
            )
            messages.append(assistant_msg)
            conversation_history.append(assistant_msg) # Persist to history
            
            # Execute tools
            for tool_call in current_tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                
                # Notify user of execution (optional, can be a specific event type)
                yield StreamChunk(
                    content="", 
                    status=f"Executing {tool_name}...",
                    done=False
                )
                
                logger.info(f"Phase 7: Executing tool {tool_name}")
                try:
                    # Get tool (Phase 7a)
                    # We need to handle the case where the tool might not be in the reduced scope
                    # but was hallucinated. The registry check ensures safety.
                    tool = self.registry.get_tool(tool_name)
                    result = await tool.run(**tool_args)
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result = f"Error executing tool {tool_name}: {e}"

                # Append result to history
                tool_msg = ChatMessage(
                    role=MessageRole.TOOL,
                    content=str(result),
                    tool_call_id=tool_call.id
                )
                messages.append(tool_msg)
                conversation_history.append(tool_msg) # Persist to history

            # --- Phase 8: Tool Result Feedback Loop ---
            # Call LLM again with tool results
            logger.info("Phase 8: Calling LLM with tool results")
            
            # We need to capture the synthesis response to append to history too!
            synthesis_content = ""
            
            async for chunk in self.provider.stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=None # No tools for synthesis Phase
            ):
                synthesis_content += chunk.content
                yield chunk
            
            # Append synthesis result to history
            synthesis_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=synthesis_content
            )
            conversation_history.append(synthesis_msg)
            
        else:
             # If no tools were called, the initial loop's content is the final answer
             # We need to append it to history
             assistant_msg = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=full_content
            )
             conversation_history.append(assistant_msg)


        # Final cleanup / done signal is handled by the caller or the last yield

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
            
        # We can implement specific filtering logic here
        # For now, we leverage the registry's query-based filtering
        # but we can make it more explicit based on intent categories
        
        all_tools = await self.registry.get_ollama_tools(query=user_input)
        
        # Refine based on intent using a mapping if needed
        # Or blindly trust the registry's keyword matching which is already good
        # But let's enforce based on intent to be stricter as per "Decision Discipline"
        
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
