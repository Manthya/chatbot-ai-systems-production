import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
MODEL = "llama3.2"  # Using known tool-supporting model

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
    try:
        test_query("What time is it now? Use the get_current_time tool.", expected_tool="get_current_time")
    except Exception as e:
        print(f"Skipping Time test due to error: {e}")
    
    # Query 2: Repo Status
    try:
        test_query("Check the git status of this repository using the check_repo_status tool.", expected_tool="check_repo_status")
    except Exception as e:
        print(f"Skipping Repo Status test due to error: {e}")

    # Query 3: Filesystem (Read README.md)
    test_query("Read the README.md file in the current directory using the read_file tool.", expected_tool="read_file")

    # Query 4: Git (Last 3 commits)
    test_query("Show me the last 3 commits using the git_log tool.", expected_tool="git_log")

    # Query 5: Fetch (Example.com)
    # The tool is named 'fetch_html' in zcaceres/fetch-mcp
    test_query("Fetch the content of https://example.com using the fetch_html tool.", expected_tool="fetch_html")
