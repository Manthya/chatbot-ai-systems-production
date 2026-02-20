
import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/api/chat/stream"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            payload = {
                "messages": [
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                "model": "qwen2.5:14b-instruct",
                "provider": "ollama"
            }
            
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            await websocket.send(json.dumps(payload))
            
            print("Waiting for response...")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)
                    print(f"Received: {data}")
                    
                    if data.get("done"):
                        print("Stream finished.")
                        break
                    if data.get("error"):
                        print(f"Error received: {data['error']}")
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response.")
                    break
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
