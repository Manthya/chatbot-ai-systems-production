import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from chatbot_ai_system.server.main import app

class TestToolIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("chatbot_ai_system.server.routes.get_provider")
    def test_tool_calling_flow(self, mock_get_provider):
        # Mock provider
        mock_provider = AsyncMock()
        mock_get_provider.return_value = mock_provider
        
        from chatbot_ai_system.models.schemas import ToolCall, ToolCallFunction
        # Define async generators for the stream responses
        async def stream_1(*args, **kwargs):
            tc = ToolCall(
                id="call_123",
                type="function",
                function=ToolCallFunction(name="get_current_time", arguments={})
            )
            chunk = MagicMock(content="", tool_calls=[tc], done=True)
            yield chunk

        async def stream_2(*args, **kwargs):
            chunk = MagicMock(content="It is 2026-02-10T14:00:00", tool_calls=None, done=True)
            yield chunk

        # Set side effects for stream using a regular MagicMock
        mock_provider.stream = MagicMock(side_effect=[stream_1(), stream_2()])
        
        # Mock complete for intent classification (FETCH intent)
        intent_response = MagicMock()
        intent_response.message.content = "FETCH\nCOMPLEXITY: 1"
        
        # Make the complete() return a coroutine that resolves to intent_response
        async def mock_complete(*args, **kwargs):
            return intent_response
            
        mock_provider.complete.side_effect = mock_complete
        
        # Make request
        response = self.client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "What time is it?"}],
                "provider": "ollama"
            }
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        
        # The response is expected to be a Server-Sent Events stream containing JSON data blocks.
        # But wait, self.client.post returns the full composed response from FastAPI StreamingResponse.
        # The content will be a stream of SSE "data: {...}\n\n". 
        text_response = response.text
        
        # Verify provider called twice
        self.assertEqual(mock_provider.stream.call_count, 2)
        
        # Verify final response content is in the stream
        self.assertIn("It is 2026-02-10T14:00:00", text_response)
        
        # Verify tool was executed
        call_args_list = mock_provider.stream.call_args_list
        second_call_args = call_args_list[1]
        messages_sent = second_call_args.kwargs['messages']
        
        self.assertTrue(len(messages_sent) >= 3)
        self.assertEqual(messages_sent[-1].role, "tool")

if __name__ == "__main__":
    unittest.main()
