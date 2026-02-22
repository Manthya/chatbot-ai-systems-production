# Phase 6.5: Free Tool Integration

This phase adds powerful agentic capabilities to the chatbot without requiring any paid API subscriptions.

## 🎯 Objectives
- **Web Search**: Enable the chatbot to find real-time information using DuckDuckGo (Free).
- **Code Execution**: Enable the chatbot to write and run Python code locally to solve math problems, process data, or generate text.

---

## 🛠️ New Tools

### 1. `web_search_duckduckgo`
- **Description**: Performs a web search and returns the top 5 results with titles, URLs, and snippets.
- **Backend**: Uses the `duckduckgo-search` (or `ddgs`) Python library.
- **Auth**: None required.
- **Privacy**: DuckDuckGo does not track search history.

### 2. `run_python_script`
- **Description**: Executes arbitrary Python code in a temporary file on the host machine.
- **Backend**: Python `subprocess` module.
- **Security**:
    - **Timeout**: 10 seconds execution limit by default.
    - **Isolation**: Runs in a temp file, but **has access to the host network and filesystem**. 
    - *Warning*: This is a "Local Sandbox" for personal use. Do not expose this tool to untrusted public users without further sandboxing (e.g., Docker).

---

## 🚀 Usage

These tools are automatically registered in the `ToolRegistry` and available to the `AgenticEngine`.

**Example User Queries:**
- "Search for the latest release date of iPhone 16." -> `web_search_duckduckgo(query="iPhone 16 release date")`
- "Calculate the 50th Fibonacci number." -> `run_python_script(code="...")`
- "Find the stock price of NVDA and tell me if it's higher than last week." -> `web_search_duckduckgo` -> `Agentic Loop`

---

## ✅ Verification

Run the verification script to test both tools:

```bash
python scripts/verify_phase_6_5.py
```

**Sample Output:**
```
INFO:__main__:Started Phase 6.5 Verification
INFO:__main__:✅ Tools successfully registered.
INFO:__main__:--- Testing Web Search ---
INFO:__main__:Search Result: 1. [Title](url)...
INFO:__main__:--- Testing Python Sandbox ---
INFO:__main__:Code Result (15*25): 375
INFO:__main__:✅ Basic Code Execution passed.
INFO:__main__:✅ Timeout Enforcement passed.
```
