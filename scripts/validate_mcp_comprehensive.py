import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
MODEL = "llama3.2"  # Ensure this model supports tools

# List of test cases
tests = [
    # 1. FILESYSTEM MCP TESTS
    {
        "id": "FS-1",
        "category": "Filesystem",
        "description": "Basic File Read",
        "prompt": "Read the README.md file and summarize the project in 5 bullet points using the read_file tool.",
        "expected_tool": "read_file"
    },
    {
        "id": "FS-2",
        "category": "Filesystem",
        "description": "Config Inspection",
        "prompt": "Open docker-compose.yml using read_file and explain what each service does and how they interact.",
        "expected_tool": "read_file"
    },
    {
        "id": "FS-3",
        "category": "Filesystem",
        "description": "Error Diagnosis",
        "prompt": "Check server.log using read_file and tell me what the main issue is, if any.",
        "expected_tool": "read_file"
    },
    {
        "id": "FS-4",
        "category": "Filesystem",
        "description": "Cross-File Reasoning",
        "prompt": "Look at requirements.txt and src/chatbot_ai_system/server/main.py using read_file and tell me if there are any obvious dependency or startup issues.",
        "expected_tool": "read_file"
    },
    {
        "id": "FS-5",
        "category": "Filesystem",
        "description": "Framework Detection",
        "prompt": "Does this project use FastAPI? Read src/chatbot_ai_system/server/main.py using read_file to check initialization and explain the request flow.",
        "expected_tool": "read_file"
    },

    # 2. GIT MCP TESTS
    {
        "id": "GIT-1",
        "category": "Git",
        "description": "Commit History Summary",
        "prompt": "Summarize the last 5 commits using the git_log tool and explain the main evolution of this project.",
        "expected_tool": "git_log"
    },
    {
        "id": "GIT-2",
        "category": "Git",
        "description": "MCP Introduction Analysis",
        "prompt": "Why was MCPClient introduced? Use git_log to check recent commits involving mcp_client.py.",
        "expected_tool": "git_log"
    },
    {
        "id": "GIT-3",
        "category": "Git",
        "description": "File-Level History",
        "prompt": "Show me the commit history for src/chatbot_ai_system/tools/mcp_client.py using git_log and explain how it evolved.",
        "expected_tool": "git_log"
    },
    {
        "id": "GIT-4",
        "category": "Git",
        "description": "Regression Risk Detection",
        "prompt": "Did any recent commit potentially break backward compatibility? Use git_log to inspect recent changes and explain your reasoning.",
        "expected_tool": "git_log"
    },
    {
        "id": "GIT-5",
        "category": "Git",
        "description": "Attribution / Blame Reasoning",
        "prompt": "Who introduced the registry changes for MCP tools and why? Use git_log on src/chatbot_ai_system/tools/registry.py.",
        "expected_tool": "git_log"
    },

    # 3. FETCH MCP TESTS
    {
        "id": "FETCH-1",
        "category": "Fetch",
        "description": "Simple HTTP Fetch",
        # Use a safe, public URL. GitHub requires auth for some endpoints, but the main repo page is public.
        "prompt": "Fetch the GitHub repository page for https://github.com/Manthya/chatbot-ai-systems-production using fetch_html. Tell me if you can access it.",
        "expected_tool": "fetch_html"
    },
    {
        "id": "FETCH-3",
        "category": "Fetch",
        "description": "Documentation Lookup",
        "prompt": "Fetch the official Model Context Protocol documentation (try https://modelcontextprotocol.io/introduction) using fetch_html and summarize how tool discovery works.",
        "expected_tool": "fetch_html"
    },

    # 4. MULTI-TOOL TESTS
    {
        "id": "MULTI-1",
        "category": "Multi-Tool",
        "description": "Git + Filesystem",
        "prompt": "Check the recent git changes using git_log and then inspect src/chatbot_ai_system/server/main.py using read_file to explain how MCP support was added end-to-end.",
        "expected_tool": "git_log" # Expect at least one tool
    }
]

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

def run_test(test):
    print(f"\n--- Running Test {test['id']}: {test['description']} ---")
    print(f"Prompt: {test['prompt']}")
    
    payload = {
        "messages": [{"role": "user", "content": test['prompt']}],
        "model": MODEL,
        "provider": "ollama",
        "temperature": 0.0 # Strict verification
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        elapsed = time.time() - start_time
        
        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])
        
        print(f"Response Time: {elapsed:.2f}s")
        
        # Determine if expected tool was used
        tool_used = False
        used_tools = [tc['function']['name'] for tc in tool_calls] if tool_calls else []
        
        # Check logs/history for tool usage if not directly in response (some providers handle it differently)
        # But for this system, tool calls are in the response message or previous messages in history.
        # Since this is a single turn, we might need to check if the response indicates tool use or if we can infer it.
        # Ideally, the API returns the assistant's tool call message.
        
        # Let's check constraints
        if test['expected_tool']:
            # We need to rely on the response containing tool calls or the content implying it.
            # In the previous verify_mcp.py output, we saw "Expected to use tool: ..." but verify_mcp.py logic was just printing expected.
            # Here we want to know if it *actually* used it.
            # The current API implementation executes tools and appends results.
            # The final response usually contains the answer based on the tool result.
            # We can't definitively check tool usage from the *final* response content alone without the tool_calls list or intermediate steps.
            # If the API returns the final answer, we look for evidence.
            
            # Simple check: Does the response contain specific info that could only come from the tool?
            print(f"Tools Used (inferred/metadata): {used_tools}") 
            print(f"Response Content:\n{content[:500]}...") # Print first 500 chars
            
            # Pass/Fail Criteria logic
            # This is hard to automate perfectly without inspection of internal logs or a more verbose API response.
            # For now, we will print the result for manual inspection.
            pass

    except Exception as e:
        print(f"Error running test {test['id']}: {e}")

if __name__ == "__main__":
    if not wait_for_server():
        sys.exit(1)
        
    for test in tests:
        run_test(test)
        time.sleep(2) # Pausing between tests to avoid overloading
