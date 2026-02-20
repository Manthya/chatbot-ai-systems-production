import requests
import json
import time
import sys

API_URL = "http://localhost:8000/api/chat"

def run_query(query, description):
    print(f"\n--- Test: {description} ---")
    print(f"Query: {query}")
    
    payload = {
        "messages": [{"role": "user", "content": query}],
        "provider": "ollama", 
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        duration = time.time() - start_time
        
        content = data["message"]["content"]
        tool_calls = data["message"].get("tool_calls")
        
        print(f"Status: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        if tool_calls:
            print(f"Tool Calls: {[tc['function']['name'] for tc in tool_calls]}")
        print(f"Response: {content[:500]}..." if len(content) > 500 else f"Response: {content}")
        
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("Waiting for server to be ready...")
    for i in range(10):
        try:
            requests.get("http://localhost:8000/health")
            print("Server is ready!")
            break
        except:
            time.sleep(1)
            print(".", end="", flush=True)
    else:
        print("\nServer failed to start.")
        sys.exit(1)

    # 1. Web Search Test
    run_query(
        "Who is the current CEO of Twitter/X in 2025?", 
        "Web Search (DuckDuckGo)"
    )

    # 2. Python Code Test
    run_query(
        "Write and run a python script to calculate the factorial of 10.", 
        "Code Execution (Python Sandbox)"
    )
    
    # 3. Reasoning + Tool Test
    run_query(
        "Find the release date of Python 3.13 and calculate how many days have passed since then (assume today is Oct 1, 2025).", 
        "Complex Reasoning (Search + Code)"
    )

if __name__ == "__main__":
    main()
