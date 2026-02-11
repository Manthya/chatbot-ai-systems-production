import asyncio
import uuid
import aiohttp
import sys
import json

BASE_URL = "http://localhost:8001"

async def validate_flow():
    print("=== Database Flow Validation Start ===")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Health Check (triggers minor DB check?)
        print("\n[Step 1] Health Check")
        async with session.get(f"{BASE_URL}/health") as resp:
            print(f"Health Status: {resp.status}")
            print(await resp.text())
            
        # Step 2: Create Conversation implicitly via Chat
        print("\n[Step 2] Send Message (Implicit Conversation Creation)")
        payload = {
            "messages": [{"role": "user", "content": "Explain quantum physics in one sentence."}],
            "model": "qwen2.5:14b-instruct",
            "provider": "ollama"
        }
        async with session.post(f"{BASE_URL}/api/chat", json=payload) as resp:
            if resp.status != 200:
                print(f"Chat failed: {resp.status}")
                print(await resp.text())
                return
            data = await resp.json()
            print(f"Chat Response: {data['message']['content'][:50]}...")
            
        # Step 3: List Conversations
        print("\n[Step 3] List Conversations")
        async with session.get(f"{BASE_URL}/api/conversations") as resp:
            convs = await resp.json()
            print(f"Found {len(convs)} conversations.")
            if not convs:
                return
            latest_conv = convs[0]
            conv_id = latest_conv['id']
            print(f"Latest Conv ID: {conv_id}")

        # Step 4: Get History
        print(f"\n[Step 4] Get History for {conv_id}")
        async with session.get(f"{BASE_URL}/api/conversations/{conv_id}") as resp:
            history = await resp.json()
            print(f"History length: {len(history)}")
            for msg in history:
                print(f"- [{msg['role']}]: {msg['content'][:30]}...")

        # Step 5: Delete Conversation
        # print(f"\n[Step 5] Delete Conversation {conv_id}")
        # async with session.delete(f"{BASE_URL}/api/conversations/{conv_id}") as resp:
        #    print(f"Delete Status: {resp.status}")

    print("\n=== Database Flow Validation End ===")

if __name__ == "__main__":
    try:
        asyncio.run(validate_flow())
    except Exception as e:
        print(f"Validation failed: {e}")
