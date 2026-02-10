import asyncio
import websockets
import json

async def test_query(query, expected_tool_use):
    uri = "ws://127.0.0.1:8000/api/chat/stream"
    print(f"\n--- Testing Query: '{query}' (Expected Tool Use: {expected_tool_use}) ---")
    
    try:
        async with websockets.connect(uri) as websocket:
            request = {
                "messages": [{"role": "user", "content": query}]
            }
            await websocket.send(json.dumps(request))
            
            tool_used = False
            status_seen = False
            full_content = ""
            
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data.get("status"):
                        print(f"STATUS: {data['status']}")
                        status_seen = True
                    
                    if data.get("tool_calls"):
                        print(f"TOOL CALL: {data['tool_calls'][0]['function']['name']}")
                        tool_used = True
                    
                    if data.get("content"):
                        full_content += data["content"]
                        
                    if data.get("done"):
                        break
                        
                except Exception as e:
                    print(f"Error receiving: {e}")
                    break
            
            print(f"Final Content Length: {len(full_content)}")
            
            if expected_tool_use and tool_used:
                print("PASS: Tool was used as expected.")
            elif expected_tool_use and not tool_used:
                print("FAIL: Expected tool use, but none occurred.")
            elif not expected_tool_use and tool_used:
                print("FAIL: Tool used unexpectedly!")
            elif not expected_tool_use and not tool_used:
                print("PASS: No tool used, natural response.")
                
    except Exception as e:
        print(f"Connection failed: {e}")

async def main():
    # Test 1: Tool required
    await test_query("What files are in the current directory?", True)
    
    # Test 2: Conversational (No tool)
    await test_query("hii", False)

if __name__ == "__main__":
    asyncio.run(main())
stone
