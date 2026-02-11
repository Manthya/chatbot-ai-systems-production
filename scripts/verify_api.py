import httpx
import logging
import asyncio
import json
import time
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/api/chat/stream"

# ...

async def test_rest_api():
    logger.info("--- Testing REST API ---")
    
    # Test 1: General Query
    logger.info("Test 1: General Query ('Hello')")
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "qwen2.5:14b-instruct",
        "provider": "ollama"
    }
    try:
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/api/chat", json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            latency = (time.time() - start_time)
            logger.info(f"Response: {data['message']['content'][:100]}... (Latency: {latency:.2f}s)")
            if data['message'].get('tool_calls'):
                logger.warning("Unexpected tool call in general query!")
            else:
                logger.info("✅ No tool calls (Correct)")
                
    except Exception as e:
        logger.error(f"REST API failed: {e}")

    # Test 2: Tool Query
    logger.info("\nTest 2: Tool Query ('What time is it?')")
    payload = {
        "messages": [{"role": "user", "content": "What time is it now?"}],
        "model": "qwen2.5:14b-instruct",
        "provider": "ollama"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Response: {data['message']['content'][:100]}...")
            
            if "202" in data['message']['content'] or "AM" in data['message']['content'] or "PM" in data['message']['content']:
                 logger.info("✅ Time/Date found in response (Tool likely used)")
            else:
                 logger.warning("Maybe tool wasn't used? Check logs.")

    except Exception as e:
        logger.error(f"REST API failed: {e}")

async def test_websocket_api():
    logger.info("\n--- Testing WebSocket API ---")
    try:
        async with websockets.connect(WS_URL) as websocket:
            logger.info("Connected to WebSocket")
            
            # Test 3: Git Status Query
            query = "Check git status of the current repo"
            logger.info(f"Test 3: Git Query ('{query}')")
            
            request = {
                "messages": [{"role": "user", "content": query}],
                "model": "qwen2.5:14b-instruct",
                "provider": "ollama"
            }
            await websocket.send(json.dumps(request))
            
            tool_detected = False
            response_text = ""
            
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data.get("done"):
                        break
                        
                    if data.get("status"):
                        logger.info(f"Status Update: {data['status']}")
                        if "Thinking" in data['status'] or "Executing" in data['status']:
                            tool_detected = True
                            
                    if data.get("content"):
                        response_text += data["content"]
                        print(data["content"], end="", flush=True)
                        
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break
            
            print("\n")
            if tool_detected:
                logger.info("✅ Tool execution detected via status update")
            else:
                logger.warning("Tool execution NOT detected via status update (might be fast or missing)")

    except Exception as e:
        logger.error(f"WebSocket verification failed: {e}")

async def main():
    # Wait for server to be ready
    logger.info("Waiting for server...")
    for _ in range(5):
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{BASE_URL}/health")
            break
        except:
            await asyncio.sleep(1)
            
    await test_rest_api()
    await test_websocket_api()

if __name__ == "__main__":
    asyncio.run(main())
