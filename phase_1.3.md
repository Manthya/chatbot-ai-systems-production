# Phase 1.3: Chat Orchestrator

## Overview
Phase 1.3 introduces the **Chat Orchestrator**, a central component responsible for managing the conversational flow, intent classification, and tool execution. This implementation follows a robust 9-phase architecture to ensure reliable and context-aware interactions.

## Architecture
The system is designed around a 9-phase processing pipeline:

1.  **System Startup**: FastAPI initialization and MCP client registration.
2.  **User Message**: Incoming request handling via WebSocket or REST API.
3.  **Orchestrator Entry**: The `ChatOrchestrator` takes control of the flow.
4.  **Intent Classification**: A lightweight LLM call categorizes user intent (GIT, FILESYSTEM, FETCH, GENERAL).
5.  **Tool Scope Reduction**: Available tools are filtered based on the classified intent to optimize context usage.
6.  **First LLM Call (Planning)**: The LLM generates a response or a tool call plan.
7.  **Tool Execution**: Validated tool calls are executed against MCP servers.
8.  **Tool Result Feedback**: Results are fed back to the LLM for synthesis.
9.  **Response Return**: The final response is streamed back to the user.

## Components

### `src/chatbot_ai_system/orchestrator.py`
The core class `ChatOrchestrator` implements the pipeline.
-   **`_classify_intent`**: Determines the nature of the user's request.
-   **`_filter_tools`**: Selects relevant tools from the `ToolRegistry`.
-   **`run`**: Async generator that orchestrates the entire loop and streams results.

### `src/chatbot_ai_system/server/routes.py`
Updated endpoints to utilize the Orchestrator.
-   **WebSocket**: `/api/chat/stream` - Full streaming support with tool status updates.
-   **REST**: `/api/chat` - Synchronous wrapper around the orchestrator.

## Verification
The implementation has been verified with both automated scripts and manual scenarios.
-   **Memory**: Multi-turn conversations persist context correctly.
-   **Tools**: Filesystem and Git tools are correctly identified and executed.
-   **Efficiency**: General queries bypass tool processing for lower latency.

## Usage
The Orchestrator is active by default for all chat endpoints. No special configuration is required beyond ensuring the MCP servers and Ollama are running.
