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
        
        # Tool call response (Step 1)
        tool_call_msg = MagicMock()
        tool_call_msg.content = ""
        # Mock tool call structure
        tc = MagicMock()
        tc.function.name = "get_current_time"
        tc.function.arguments = {}
        tool_call_msg.tool_calls = [tc]
        
        # Final response (Step 2)
        final_msg = MagicMock()
        final_msg.content = "It is 2026-02-10T14:00:00"
        final_msg.tool_calls = None
        
        # Set side effects
        mock_provider.complete.side_effect = [
            MagicMock(message=tool_call_msg),
            MagicMock(message=final_msg)
        ]
        
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
        data = response.json()
        
        # Verify provider called twice
        self.assertEqual(mock_provider.complete.call_count, 2)
        
        # Verify final response content
        self.assertEqual(data["message"]["content"], "It is 2026-02-10T14:00:00")
        
        # Verify tool was executed (we can infer from the flow, or check if 'tool' role message was passed in 2nd call)
        call_args_list = mock_provider.complete.call_args_list
        second_call_args = call_args_list[1]
        messages_sent = second_call_args.kwargs['messages']
        
        # Should have: User, Assistant (ToolCall), Tool (Result)
        # So length should be 3 (plus history if any, but we started fresh)
        # Wait, routes.py appends to _conversations globally.
        # But we use unique conversation_id for each request usually if not provided?
        # Actually conversation_id is optional in request.
        # Let's check conversation history length passed to second call.
        self.assertTrue(len(messages_sent) >= 3)
        self.assertEqual(messages_sent[-1].role, "tool")

if __name__ == "__main__":
    unittest.main()
