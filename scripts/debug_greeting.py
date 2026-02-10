
import asyncio
import json
import httpx

async def debug_greeting():
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "qwen2.5-coder:7b",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant. You have access to tools, but you should only use them when necessary. For general conversation, greetings, and non-technical questions, respond with natural language in plain text. Do not output JSON unless you are explicitly calling a tool."},
            {"role": "user", "content": "hii"}
        ],
        "stream": False,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files in a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(debug_greeting())
stone
