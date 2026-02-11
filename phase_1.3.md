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

## Deep Dive: MCP Tool Lifecycle

To understand how the system interacts with external tools, here is the detailed lifecycle of an MCP tool from startup to execution.

### 1. Startup & Discovery
When the backend starts (`src/chatbot_ai_system/server/main.py`), it initializes the MCP clients and discovers available tools.

1.  **Initialization**: `startup_event` creates `MCPClient` instances for Filesystem, Git, and Fetch.
2.  **Connection**: Each client spawns the corresponding Node.js MCP server process (e.g., `npx @modelcontextprotocol/server-filesystem`) and establishes a standard input/output (stdio) connection.
3.  **Registration**: Clients are registered with the `ToolRegistry` (`src/chatbot_ai_system/tools/registry.py`).
4.  **Discovery (List Tools)**:
    -   The registry calls `refresh_remote_tools()`.
    -   It iterates through each client and sends a `tools/list` JSON-RPC request.
    -   The MCP server returns a list of available tools and their JSON schemas.
    -   These tool definitions are **cached in memory** within the `ToolRegistry`.

### 2. Runtime Execution
When a user sends a request that requires a tool, the specific flow is:

1.  **Filter**: The Orchestrator asks `registry.get_ollama_tools(query)`.
2.  **Select**: The registry filters cached tools based on the query keywords (e.g., "git" keywords -> Git tools).
3.  **Plan**: The LLM receives the filtered tool definitions in the system prompt.
4.  **Call**: The LLM decides to use a tool and outputs a JSON tool call (e.g., `git_status`).
5.  **Retrieve**: The Orchestrator requests the tool object from the registry via `registry.get_tool("git_status")`.
6.  **Execute**:
    -   The registry returns a `RemoteMCPTool` wrapper.
    -   The Orchestrator calls `tool.run(**args)`.
    -   The wrapper delegates to its `MCPClient`.
    -   The client sends a `tools/call` JSON-RPC request to the persistent Node.js process.
7.  **Result**: The MCP server executes the command and returns the result, which is passed back to the LLM.
