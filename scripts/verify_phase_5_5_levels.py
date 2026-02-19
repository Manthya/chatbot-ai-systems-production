
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import logging

# Mock dependencies
sys.modules["prometheus_client"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()

from chatbot_ai_system.models.schemas import ChatMessage, MessageRole, StreamChunk, ToolCall, ToolCallFunction
from chatbot_ai_system.orchestrator import ChatOrchestrator
from chatbot_ai_system.providers.ollama import OllamaProvider
from chatbot_ai_system.tools.registry import ToolRegistry

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Phase5.5Test")

class TestPhase5_5_Levels(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        # Patch redis
        self.redis_patcher = patch("chatbot_ai_system.orchestrator.redis_client", new=AsyncMock())
        self.mock_redis = self.redis_patcher.start()
        self.mock_redis.get.return_value = None
        
        # Mocks
        self.mock_provider = AsyncMock(spec=OllamaProvider)
        self.mock_provider.base_url = "http://localhost:11434"
        self.mock_registry = AsyncMock(spec=ToolRegistry)
        self.mock_registry.get_categories.return_value = ["GENERAL", "FILESYSTEM", "GIT", "FETCH"]
        self.mock_registry.get_tools_by_category.side_effect = lambda cat: []
        
        self.mock_conv_repo = AsyncMock()
        self.mock_conv_repo.get_conversation_summary.return_value = None
        self.mock_mem_repo = AsyncMock()
        
        self.orchestrator = ChatOrchestrator(
            provider=self.mock_provider,
            registry=self.mock_registry,
            conversation_repo=self.mock_conv_repo,
            memory_repo=self.mock_mem_repo
        )

    async def asyncTearDown(self):
        self.redis_patcher.stop()

    async def run_query(self, query: str, classification_mock, stream_chunks, description: str):
        """Helper to run a query with specific mocks and log result."""
        print(f"\n🔹 {description}")
        print(f"   Query: \"{query}\"")
        
        # 1. Mock Classification (complete)
        self.mock_provider.complete.reset_mock()
        self.mock_provider.complete.return_value = classification_mock
        
        # 2. Mock Response (stream)
        self.mock_provider.stream.reset_mock()
        
        async def async_gen():
            for chunk in stream_chunks:
                yield chunk
                
        self.mock_provider.stream.return_value = async_gen()
        
        # Capture output
        responses = []
        try:
            async for chunk in self.orchestrator.run(
                conversation_id="123e4567-e89b-12d3-a456-426614174000", user_input=query, conversation_history=[], model="test"
            ):
                if chunk.content: responses.append(chunk.content)
                if chunk.status: print(f"   [Status] {chunk.status}")
                if chunk.tool_calls: print(f"   [ToolCall] {chunk.tool_calls[0].function.name}")
        except Exception as e:
            print(f"   [Error] {e}")
            import traceback
            traceback.print_exc()
            
        final_response = "".join(responses).strip()
        print(f"   [Result] {final_response[:100]}..." if len(final_response) > 100 else f"   [Result] {final_response}")
        return final_response

    # --- LEVEL 1: GENERAL (SIMPLE, MEDIUM, DIFFICULT) ---
    async def test_level1_general(self):
        print("\n=== LEVEL 1: GENERAL (No Tools) ===")
        
        # Simple
        await self.run_query(
            "Hi", 
            MagicMock(message=MagicMock(content="INTENT: GENERAL\nCOMPLEXITY: SIMPLE")),
            [StreamChunk(content="Hello!", done=True)],
            "Simple: Greeting"
        )
        
        # Medium
        await self.run_query(
            "Explain TCP vs UDP", 
            MagicMock(message=MagicMock(content="INTENT: GENERAL\nCOMPLEXITY: SIMPLE")),
            [StreamChunk(content="TCP is connection-oriented...", done=True)],
            "Medium: Technical Concept"
        )

    # --- LEVEL 2: SIMPLE TOOL (ONE-SHOT) ---
    async def test_level2_simple_tool(self):
        print("\n=== LEVEL 2: SIMPLE TOOL (One-Shot) ===")
        
        # Note: One-shot flow calls stream() twice if tool is used.
        # 1. stream() -> tool call
        # 2. stream() -> final answer
        
        # We need side_effect for stream() to yield different generators
        async def gen_tool_call():
             yield StreamChunk(content="", tool_calls=[ToolCall(id="1", function=ToolCallFunction(name="list_files", arguments={}))])
             
        async def gen_final():
             yield StreamChunk(content="Here are the files: file1.txt", done=True)
             
        self.mock_provider.stream.side_effect = [gen_tool_call(), gen_final()]
        
        # Mock tool execution
        tool_mock = AsyncMock()
        tool_mock.run.return_value = "file1.txt"
        self.mock_registry.get_tool.return_value = tool_mock
        self.mock_registry.get_ollama_tools.return_value = [{"function": {"name": "list_files"}}]

        # We must NOT use run_query helper here because we need side_effect on stream
        print(f"\n🔹 Medium: List Files (Simulation)")
        print(f"   Query: \"List files\"")
        
        self.mock_provider.complete.return_value = MagicMock(message=MagicMock(content="INTENT: FILESYSTEM\nCOMPLEXITY: SIMPLE"))
        
        responses = []
        async for chunk in self.orchestrator.run(
             conversation_id="123e4567-e89b-12d3-a456-426614174000", user_input="List files", conversation_history=[], model="test"
        ):
             if chunk.content: responses.append(chunk.content)
             if chunk.status: print(f"   [Status] {chunk.status}")
             if chunk.tool_calls: print(f"   [ToolCall] {chunk.tool_calls[0].function.name}")
             
        final = "".join(responses)
        print(f"   [Result] {final}")

    # --- LEVEL 3: AGENTIC FLOW (COMPLEX) ---
    async def test_level3_agentic(self):
        print("\n=== LEVEL 3: AGENTIC FLOW (Complex) ===")
        
        # For agentic flow, we mock the AgenticEngine.execute method directly 
        # because simulating the entire loop with provider mocks is complex and brittle.
        
        classifier = MagicMock(message=MagicMock(content="INTENT: GIT\nCOMPLEXITY: COMPLEX"))
        planner = MagicMock(message=MagicMock(content="1. Check git status\n2. List src files"))
        
        # Setup provider to return classifier then planner
        self.mock_provider.complete.side_effect = [classifier, planner]
        
        # Ensure tools are present so orchestrator routes to AgenticEngine
        self.mock_registry.get_tools_by_category.side_effect = lambda cat: [{"function": {"name": "git_status"}}] if cat == "GIT" else []
        
        # Use helper but we need to patch execute first
        original_execute = self.orchestrator.agentic_engine.execute
        
        async def mock_execute(*args, **kwargs):
             yield StreamChunk(content="", status="📋 Plan (2 steps):\n1. Check git status\n2. List src files")
             yield StreamChunk(content="", status="📋 Step 1/2: Calling git_status...")
             yield StreamChunk(content="", status="📋 Step 1/2: git_status ✅")
             yield StreamChunk(content="", status="📋 Step 2/2: Calling list_files...")
             yield StreamChunk(content="", status="📋 Step 2/2: list_files ✅")
             yield StreamChunk(content="Git is clean. Src has main.py.", done=True)
        
        self.orchestrator.agentic_engine.execute = mock_execute
        
        # We manually run this to handle the side_effect on complete properly
        print(f"\n🔹 Medium: Git + Filesystem (Agentic)")
        print(f"   Query: \"Check git status and list src files\"")
        
        responses = []
        async for chunk in self.orchestrator.run(
             conversation_id="123e4567-e89b-12d3-a456-426614174000", user_input="Check git status...", conversation_history=[], model="test"
        ):
             if chunk.content: responses.append(chunk.content)
             if chunk.status: print(f"   [Status] {chunk.status}")
             
        final = "".join(responses)
        print(f"   [Result] {final}")
        
        # Restore
        self.orchestrator.agentic_engine.execute = original_execute

    def _async_gen(self, items):
        async def gen():
            for item in items: yield item
        return gen()

if __name__ == "__main__":
    unittest.main()
