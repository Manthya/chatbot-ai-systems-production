
import asyncio
import logging
import sys
from unittest.mock import MagicMock, AsyncMock
from typing import List, AsyncGenerator

from chatbot_ai_system.models.schemas import (
    ChatMessage,
    MessageRole,
    StreamChunk,
    ToolCall,
    ToolCallFunction,
    ChatResponse
)
from chatbot_ai_system.orchestrator import ChatOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock Classes

class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    def to_ollama_format(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    async def run(self, **kwargs):
        return f"Result from {self.name}: {kwargs}"

class MockRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    async def get_ollama_tools(self, query=None):
        # Return all for simplicity or filter if needed
        return [t.to_ollama_format() for t in self.tools.values()]

    def get_tool(self, name):
        return self.tools[name]

class MockProvider:
    def __init__(self):
        pass

    async def complete(self, messages, **kwargs):
        content = messages[-1].content
        # Mock Intent Classification
        if "intent classifier" in messages[0].content:
            if "git" in content.lower():
                return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="GIT"), model="mock", provider="mock")
            if "file" in content.lower():
                return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="FILESYSTEM"), model="mock", provider="mock")
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="GENERAL"), model="mock", provider="mock")
        return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="Mock Response"), model="mock", provider="mock")

    async def stream(self, messages, tools=None, **kwargs):
        # Mock LLM Logic
        last_msg = messages[-1]
        
        # 1. Planning / First Call
        if tools and messages[0].role == MessageRole.SYSTEM and "tool" in messages[0].content.lower():
            # If asking about git, allow tool call
            content = ""
            for m in messages:
                if m.role == MessageRole.USER:
                    content = m.content
            
            if "git" in content.lower():
                # Simulate tool call
                yield StreamChunk(content="", tool_calls=[
                    ToolCall(function=ToolCallFunction(name="git_status", arguments={}))
                ])
                return

        # 2. Synthesis (After tool result)
        if messages[-1].role == MessageRole.TOOL:
            yield StreamChunk(content="Based on the tool result, here is the answer.")
            return

        # 3. General Chat
        yield StreamChunk(content="This is a general response.")

    def _try_parse_tool_calls(self, content):
        return None

async def run_test():
    # Setup
    registry = MockRegistry()
    registry.register(MockTool("git_status", "Check git status"))
    registry.register(MockTool("read_file", "Read a file"))
    
    provider = MockProvider()
    orchestrator = ChatOrchestrator(provider, registry)

    conversation_history = []

    print("\n--- Test 1: General Query ---")
    query = "Hello, how are you?"
    conversation_history.append(ChatMessage(role=MessageRole.USER, content=query))
    
    logger.info(f"User: {query}")
    async for chunk in orchestrator.run(query, conversation_history, model="mock"):
        if chunk.content:
            print(f"Chunk: {chunk.content}", end="|")
        if chunk.tool_calls:
            print(f"Tool Call: {chunk.tool_calls}")
    print("\nHistory length:", len(conversation_history))
    assert len(conversation_history) == 2 # User + Assistant
    assert conversation_history[-1].role == MessageRole.ASSISTANT

    print("\n--- Test 2: Git Query (Tool Usage) ---")
    query = "Check git status"
    conversation_history.append(ChatMessage(role=MessageRole.USER, content=query))
    
    logger.info(f"User: {query}")
    async for chunk in orchestrator.run(query, conversation_history, model="mock"):
         if chunk.content:
            print(f"Chunk: {chunk.content}", end="|")
         if chunk.status:
             print(f"Status: {chunk.status}")
             
    print("\nHistory length:", len(conversation_history))
    # History: 
    # 0: User (Hello)
    # 1: Asst (General)
    # 2: User (Git)
    # 3: Asst (Tool Call)
    # 4: Tool (Result)
    # 5: Asst (Synthesis)
    assert len(conversation_history) == 6
    assert conversation_history[-3].tool_calls # The assistant msg invoking tool
    assert conversation_history[-2].role == MessageRole.TOOL
    assert conversation_history[-1].role == MessageRole.ASSISTANT

    print("\nAll tests passed!")

if __name__ == "__main__":
    asyncio.run(run_test())
