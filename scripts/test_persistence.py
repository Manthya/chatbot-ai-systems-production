import asyncio
import uuid
import aiohttp
import sys

BASE_URL = "http://localhost:8001"

async def test_persistence():
    async with aiohttp.ClientSession() as session:
        # 1. Health Check
        async with session.get(f"{BASE_URL}/health") as resp:
            print(f"Health Check: {resp.status}")
            if resp.status != 200:
                print(await resp.text())
                return
        
        # 2. Create Conversation & Send Message
        print("\nSending message...")
        payload = {
            "messages": [{"role": "user", "content": "My name is PersistenceTest."}],
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
            
            # Extract conversation_id from response if available?
            # The ChatResponse doesn't return conversation_id currently.
            # We need to list conversations to find it or passing one.
            pass

        # 3. List Conversations to find the new one
        print("\nListing conversations...")
        async with session.get(f"{BASE_URL}/api/conversations") as resp:
            convs = await resp.json()
            print(f"Found {len(convs)} conversations.")
            if not convs:
                print("No conversations found! Persistence failed?")
                return
            
            latest_conv = convs[0] # Assuming ordered by update
            conv_id = latest_conv['id']
            print(f"Latest Conversation ID: {conv_id}")
            print(f"Title: {latest_conv['title']}")

        # 4. Get Conversation History
        print(f"\nFetching history for {conv_id}...")
        async with session.get(f"{BASE_URL}/api/conversations/{conv_id}") as resp:
            history = await resp.json()
            print(f"History length: {len(history)}")
            # Verify user message is there
            user_msgs = [m for m in history if m['role'] == 'user']
            if user_msgs and "PersistenceTest" in user_msgs[-1]['content']:
                print("SUCCESS: Message persisted and retrieved.")
            else:
                print("FAILURE: Message not found in history.")

if __name__ == "__main__":
    try:
        asyncio.run(test_persistence())
    except Exception as e:
        print(f"Test failed: {e}")
