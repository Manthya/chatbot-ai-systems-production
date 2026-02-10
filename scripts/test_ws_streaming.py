import asyncio
import websockets
import json

async def test_ws_status():
    uri = "ws://localhost:8000/api/chat/stream"
    async with websockets.connect(uri) as websocket:
        request = {
            "messages": [
                {"role": "user", "content": "Tell me what files are in the current directory."}
            ],
            "model": "llama3.2"
        }
        await websocket.send(json.dumps(request))
        
        print("Sent request, waiting for chunks...")
        
        status_received = False
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"CHUNK RECEIVED: {data}")
                
                if data.get("status"):
                    print(f"!!! FOUND STATUS: {data['status']} !!!")
                    status_received = True
                
                if data.get("content"):
                    print(f"Content: {data['content']}", end="", flush=True)
                
                if data.get("done"):
                    print("\nStream finished.")
                    break
            except Exception as e:
                print(f"\nError: {e}")
                break
        
        if status_received:
            print("\nSUCCESS: Received 'Thinking' status chunk!")
        else:
            print("\nFAILURE: Did not receive status chunk.")

if __name__ == "__main__":
    asyncio.run(test_ws_status())
