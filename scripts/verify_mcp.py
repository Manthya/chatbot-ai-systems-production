import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
MODEL = "gemma3:4b"  # Using available model

def wait_for_server():
    print("Waiting for server to be ready...")
    for _ in range(30):
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("Server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    print("Server failed to start.")
    return False

def test_query(query, expected_tool=None):
    print(f"\n--- Testing Query: '{query}' ---")
    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": MODEL,
        "provider": "ollama"
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        elapsed = time.time() - start_time
        
        content = data["message"]["content"]
        print(f"Response ({elapsed:.2f}s): {content}")
        
        # We can't easily check internal logs for tool execution from here without access to server logs,
        # but the content should reflect the tool result (e.g. actual time).
        
        if expected_tool:
            print(f"Expected to use tool: {expected_tool}")
            # In a real verification we'd check logs or trace, but here we judge by output.
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if not wait_for_server():
        sys.exit(1)
        
    # Query 1: Time
    test_query("What time is it now?", expected_tool="get_current_time")
    
    # Query 2: Repo Status
    test_query("Check the git status of this repository.", expected_tool="check_repo_status")
