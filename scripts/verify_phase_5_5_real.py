
import subprocess
import time
import json
import os
import sys
import urllib.request
import urllib.error

# Configuration
API_URL = "http://localhost:8000/api/chat"
HEALTH_URL = "http://localhost:8000/health"
SERVER_CMD = [sys.executable, "-m", "uvicorn", "chatbot_ai_system.server.main:app", "--port", "8000", "--host", "0.0.0.0"]
LOG_FILE = "phase_5_5_verification_report.md"

# Add src to PYTHONPATH for the server process
env = os.environ.copy()
env["PYTHONPATH"] = os.path.join(os.getcwd(), "src")
env["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b-instruct")
env["OLLAMA_BASE_URL"] = "http://localhost:11434"

QUERIES = [
    # LEVEL 1: EASY (Simple Flow - General Knowledge)
    {"input": "Hi, how are you?", "desc": "Easy 1: Greeting"},
    {"input": "What is the capital of France?", "desc": "Easy 2: Fact Retrieval"},
    {"input": "Who wrote Romeo and Juliet?", "desc": "Easy 3: Fact Retrieval"},
    {"input": "Explain the concept of recursion briefly.", "desc": "Easy 4: Explanation"},
    {"input": "What is the boiling point of water?", "desc": "Easy 5: Common Knowledge"},

    # LEVEL 2: MEDIUM (Simple Tool Usage - One-Shot)
    {"input": "List the files in the current directory.", "desc": "Medium 1: List Files (Filesystem)"},
    {"input": "Read the contents of requirements.txt.", "desc": "Medium 2: Read File (Filesystem)"},
    {"input": "What files are in the 'docs' folder?", "desc": "Medium 3: List Dir (Filesystem)"},
    {"input": "Check the size of README.md.", "desc": "Medium 4: File metadata (Filesystem/General)"},
    {"input": "Show me the first 5 lines of pyproject.toml.", "desc": "Medium 5: Read Partial File (Filesystem)"},

    # LEVEL 3: DIFFICULT (Agentic Flow - Multi-step / Complex)
    {"input": "Check git status and then list the files in src/.", "desc": "Hard 1: Git + Filesystem Sequence"},
    {"input": "Read docs/phase_5.0.md and docs/phase_4.1.md and summarize the key differences.", "desc": "Hard 2: Multi-file Read + Synthesis"},
    {"input": "Find all python files in scripts/ and tell me which one is the largest.", "desc": "Hard 3: Search + Analysis"},
    {"input": "Analyze the imports in src/chatbot_ai_system/orchestrator.py and list the external dependencies.", "desc": "Hard 4: Code Analysis"},
    {"input": "Look for error messages in server.log and summarize what happened.", "desc": "Hard 5: Log Analysis"}
]

def wait_for_server(timeout=60):
    print("Waiting for server...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(HEALTH_URL) as response:
                if response.status == 200:
                    return True
        except:
            time.sleep(1)
    return False

def run_tests():
    # Start Server
    print(f"Starting server with command: {' '.join(SERVER_CMD)}")
    with open("server.log", "w") as server_log:
        process = subprocess.Popen(SERVER_CMD, stdout=server_log, stderr=subprocess.STDOUT, env=env)
    
    try:
        # Wait for ready
        if not wait_for_server():
            print("Server failed to start. Check server.log for details.")
            return

        print("Server is ready. Running tests...")
        
        with open(LOG_FILE, "w") as f:
            f.write("# Phase 5.5 Verification Report\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            conversation_id = None
            
            for i, q in enumerate(QUERIES):
                # Reset conversation to ensure clean slate for each query type if needed
                # But typically we want to test continuity. However, for precise flow testing,
                # we might want to reset or keep same. Let's keep same for now.
                # Actually, some might get confused by context using previous tool outputs.
                # Let's start a new conversation for each distinct level to be safe?
                # Or just one long one. Let's try one long one to test memory too.
                # Just kidding, let's reset for each level block? No, let's keep it simple.
                # Just one conversation.
                
                print(f"[{i+1}/{len(QUERIES)}] Testing: {q['desc']}")
                f.write(f"## Test {i+1}: {q['desc']}\n")
                f.write(f"**Query**: \"{q['input']}\"\n\n")
                
                payload = {
                    "messages": [{"role": "user", "content": q["input"]}],
                    "model": env.get("OLLAMA_MODEL"),
                    "provider": "ollama"
                }
                
                if conversation_id:
                    payload["conversation_id"] = conversation_id
                
                try:
                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json'})
                    
                    start_req = time.time()
                    with urllib.request.urlopen(req) as response:
                        duration = time.time() - start_req
                        body = response.read().decode('utf-8')
                        resp_data = json.loads(body)
                        
                        # Extract response
                        msg = resp_data.get("message", {})
                        content = msg.get("content", "")
                        tool_calls = msg.get("tool_calls", [])
                        
                        f.write(f"**Response** ({duration:.2f}s):\n")
                        f.write(f"{content}\n\n")
                        
                        if tool_calls:
                            f.write("**Tool Calls**:\n")
                            for tc in tool_calls:
                                args = tc.get('function', {}).get('arguments')
                                f.write(f"- `{tc.get('function', {}).get('name')}`: {args}\n")
                        else:
                             f.write("**Tool Calls**: None\n")
                        
                        if "conversation_id" in resp_data:
                            conversation_id = resp_data["conversation_id"]
                        
                        print(f"  Success ({duration:.2f}s)")
                        
                except urllib.error.HTTPError as e:
                    error_msg = f"HTTP {e.code}: {e.reason}"
                    try:
                        err_body = e.read().decode('utf-8')
                        error_msg += f"\nBody: {err_body}"
                    except: pass
                    
                    f.write(f"**Error**: {error_msg}\n\n")
                    print(f"  Failed: {error_msg}")
                    
                except Exception as e:
                    f.write(f"**Error**: {e}\n\n")
                    print(f"  Exception: {e}")
                    import traceback
                    traceback.print_exc()

                f.write("---\n")

    finally:
        print("Stopping server...")
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
             try: process.kill()
             except: pass
        print(f"Done. Report written to {LOG_FILE}.")

if __name__ == "__main__":
    run_tests()
