
import httpx
import logging
import asyncio
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("TestScenarios")

BASE_URL = "http://localhost:8001"

async def ran_chat(messages, description):
    logger.info(f"\n--- Scenario: {description} ---")
    payload = {
        "messages": messages,
        "model": "qwen2.5:14b-instruct",
        "provider": "ollama"
    }
    
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            latency = (time.time() - start_time)
            
            content = data['message']['content']
            logger.info(f"Lat: {latency:.2f}s | Response: {content.strip()}")
            return content
    except Exception as e:
        logger.error(f"Failed: {e}")
        return None

async def main():
    logger.info("Starting Extended Scenarios...")

    # Scenario 1: Multi-turn Context
    # Turn 1
    messages = [{"role": "user", "content": "My name is Alice."}]
    resp1 = await ran_chat(messages, "Memory Test - Turn 1")
    
    # Turn 2
    if resp1:
        messages.append({"role": "assistant", "content": resp1})
        messages.append({"role": "user", "content": "What is my name?"})
        await ran_chat(messages, "Memory Test - Turn 2 (Context Retrieval)")

    # Scenario 2: Filesystem Access
    messages = [{"role": "user", "content": "List the files in the current directory."}]
    await ran_chat(messages, "Tool Test - List Files")

    # Scenario 3: Specific File Read
    messages = [{"role": "user", "content": "Read the first 5 lines of requirements.txt"}]
    await ran_chat(messages, "Tool Test - Read File")

    # Scenario 4: Complex/Ambiguous
    messages = [{"role": "user", "content": "Is there a README.md file? If so, what does it happen to say about the project title?"}]
    await ran_chat(messages, "Tool Test - Complex (Check existence + Read)")

if __name__ == "__main__":
    asyncio.run(main())
