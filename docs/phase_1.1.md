# Phase 1.1: MCP Tool Optimization & Reliability Report

This document outlines the evolutionary steps taken during Phase 1 to integrate Model Context Protocol (MCP) servers and optimize tool usage for local LLMs via Ollama.

## 1. What We Did
*   **MCP Integration**: Successfully integrated three Model Context Protocol servers:
    *   **Filesystem**: Direct project file read/write access.
    *   **Git**: Version control history and status management.
    *   **Fetch**: Real-time web content retrieval.
*   **Tool Filtering Architecture**: Implemented an allowlist mechanism in `ToolRegistry` to reduce the tool surface from 44+ tools to 15 essential "Swiss Army Knife" tools.
*   **Default Model Alignment**: Configured **Llama 3.2 (3B)** as the default model for superior tool-calling compliance and multi-turn reliability.
*   **JSON Parsing Fallback**: Added a manual regex-based JSON parser to `OllamaProvider` to handle models that output tool calls in plain text content rather than using the native API.
*   **Streaming Tool Execution**: Enabled real-time "Thinking" status updates by yielding intermediate chunks before tool execution over WebSocket.

## 2. Challenges & Solutions

### A. The "Infinite Tool Loop" (What didn't work)
*   **Problem**: The LLM would repeat the same tool call infinitely without moving to a natural language response.
*   **Root Causes**: 
    1.  The message history loop in `routes.py` was not updating the `all_messages` list sent to the LLM, so the model never saw its own previous calls or the results.
    2.  Missing IDs in `ToolCall` and `ChatMessage` made it impossible for the LLM to correlate Results with Calls.
*   **Solution**: 
    1.  Updated `routes.py` to correctly append assistant and tool messages to the context list in every turn.
    2.  Implemented UUID-based `tool_call_id` correlation across the entire stack.

### B. Tool Overload (Context Bloat)
*   **Problem**: Loading all 44 Git/FS tools exceeded the small local models' capabilities, leading to hallucinations and "Refusals".
*   **Solution**: Implemented the `ESSENTIAL_TOOLS` allowlist in `registry.py` to prioritize general-purpose discovery and action tools.

### C. Streaming Termination (WebSocket)
*   **Problem**: The LLM would yield a `done=True` chunk at the end of its first turn, causing the client to close the WebSocket before the tool-execution loop could complete.
*   **Solution**: Modified `routes.py` to suppress standard `done` signals if tool calls are pending, yielding a custom final `done` chunk only after all tool turns are exhausted.

## 3. Current System State
The system is currently a **Multi-Turn Reactive Chatbot**.
*   **Logic**: It can execute up to 5 consecutive tool-use turns per request.
*   **Context Management**: It clears raw JSON content from assistant messages in subsequent turns to keep the LLM focused on the natural language conversation flow.
*   **Reliability**: Using Llama 3.2, the system successfully completes complex tasks (e.g., "Read logs and summarize status").

## 4. Current Drawbacks
*   **Static Filtering**: If a user needs a specific tool not in the "Essential 15" (like `git_blame`), they cannot access it without a code change.
*   **Turn Latency**: Multi-turn tool usage with local models (7B+) can take 30-45s depending on hardware.
*   **Model Sensitivity**: The system relies heavily on specific prompt formatting for tool-call detection.

## 5. Future Production Solutions
*   **Dynamic Tool Selection (RAG for Tools)**: Instead of a static list, use semantic search to inject only the relevant tools into the prompt based on the user's query.
*   **Speculative Decoding / Smaller Drafters**: Use a tiny model to "decide" if a tool is needed before calling the larger model, reducing inference time.
*   **Agentic Supervision**: Implement a separate "Validator" turn where the system checks if the tool result actually answered the user's question before returning.
*   **Streaming Tool Execution**: Allow the frontend to show the "Thinking" state (e.g., "Reading README.md...") in real-time while tools are executing.
