
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
LOG_FILE = "system_test_log.md"

# Add src to PYTHONPATH for the server process
env = os.environ.copy()
env["PYTHONPATH"] = os.path.join(os.getcwd(), "src")
env["OLLAMA_MODEL"] = "qwen2.5:14b-instruct"
env["OLLAMA_BASE_URL"] = "http://localhost:11434"

QUERIES = [
    {"input": "Hi, are you active?", "desc": "Context Check (General/Simple)"},
    {"input": "Start a new conversation", "desc": "Reset"},
    {"input": "List files in the current directory", "desc": "Filesystem Check (Simple Tool)"},
    {"input": "Check git status and list the files in src/", "desc": "Agentic Flow (Complex)"}
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
            f.write("# System Test Log\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            conversation_id = None
            
            for q in QUERIES:
                if q["input"] == "Start a new conversation":
                    conversation_id = None
                    print("Resetting conversation ID.")
                    continue
                    
                print(f"Testing: {q['desc']}")
                f.write(f"## Test: {q['desc']}\n")
                f.write(f"**Query**: \"{q['input']}\"\n\n")
                
                payload = {
                    "messages": [{"role": "user", "content": q["input"]}],
                    "model": env.get("OLLAMA_MODEL", "qwen2.5:14b-instruct"),
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
                                f.write(f"- `{tc.get('function', {}).get('name')}`\n")
                        
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
        print("Done.")

if __name__ == "__main__":
    run_tests()
