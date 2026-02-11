# Phase 1.2: Decision Discipline & Intelligence Upgrade

## Objective
Implement a robust **Decision Discipline** framework to ensure the chatbot intelligently distinguishes between conversational queries (which should be answered directly) and technical queries (which require tool execution).

## Key Implementation Details

### 1. The Decision Pipeline
We introduced a multi-step pipeline in the WebSocket handler (`routes.py`) to enforce strict logic:

1.  **Planning Phase**: Before generating a response, the system queries the model with a specialized prompt: *"Decide if this query requires external tools. Answer USE_TOOL or NO_TOOL."*
2.  **Tool Filtering**:
    *   If **NO_TOOL**: The system hides all tools and forces a natural language response.
    *   If **USE_TOOL**: The system filters the available tools based on keywords (e.g., "file" -> `filesystem` tools only) to reduce noise.
3.  **Strict JSON Enforcement**: When tools are active, a rigorous system prompt is injected to ensure the model outputs *only* valid JSON, preventing "chatty" tool calls.
4.  **Execution & Synthesis**: The tool is executed, and the result is fed back to the model for a final synthesized answer.

### 2. Model Upgrade
*   **Old Model**: `llama3.2` (Struggled with instruction following and tool formats).
*   **New Model**: **`qwen2.5:14b-instruct`** (Superior reasoning, strict adherence to JSON formats, and better conversational nuances).

### 3. Verification
*   Added `scripts/verify_decision_discipline.py` to automatically test the routing logic.
    *   *Test 1*: "hii" -> Confirms **NO_TOOL** path.
    *   *Test 2*: "List files" -> Confirms **USE_TOOL** path.

## Outcome
The chatbot now feels significantly "smarter." It no longer attempts to use file system tools for simple greetings, and it reliably executes tools when actual data is needed.

## Usage
*   Ensure `OLLAMA_MODEL=qwen2.5:14b-instruct` is set in `.env`.
*   Run the backend: `uvicorn chatbot_ai_system.server.main:app --reload`
*   Run the frontend: `npm run dev`
stone
