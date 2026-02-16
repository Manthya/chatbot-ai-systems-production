import asyncio
import httpx
import random
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TrafficGenerator")

BASE_URL = "http://localhost:8000"

PROMPTS = [
    "Hello there!",
    "What is the capital of France?",
    "List the files in the current directory.",
    "Show me the git status.",
    "Calculate 15 * 24.", # Might fail or use tool if math tool exists
    "Write a python script to print hello world.",
    "Who won the 1998 World Cup?",
    "Explain quantum computing in simple terms.",
    "fetch https://example.com",
]

async def send_chat_request(client, prompt: str, conversation_id: str):
    logger.info(f"Sending request: {prompt}")
    try:
        start = time.time()
        # Create a new conversation if needed (but API usually handles it or returns new ID)
        # Using a fixed conversation ID for simplicity in this script, or generating new ones.
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "conversation_id": conversation_id,
            "model": "qwen2.5:14b-instruct",
            "stream": False
        }
        
        response = await client.post(f"{BASE_URL}/api/chat", json=payload, timeout=120.0)
        response.raise_for_status()
        
        duration = time.time() - start
        logger.info(f"Request completed in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Request failed: {e}")

async def main():
    logger.info("Starting traffic generation...")
    conversation_id = str(random.randint(1000, 9999)) # Mock ID
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check health first
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                logger.error("Backend not healthy. Exiting.")
                return
        except Exception:
            logger.error("Backend not reachable. Exiting.")
            return

        for i in range(20): # Run for 20 iterations
            prompt = random.choice(PROMPTS)
            await send_chat_request(client, prompt, conversation_id)
            await asyncio.sleep(random.uniform(1, 4))

if __name__ == "__main__":
    asyncio.run(main())
