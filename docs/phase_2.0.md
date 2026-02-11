# Phase 2.0: Database Persistence & Scalable Memory

## 1. Overview

**Goal:** Transition the Chatbot AI System from ephemeral in-memory storage to a robust, persistent architecture using PostgreSQL. This phase ensures that user conversations, message history, and long-term memory are preserved across server restarts and provides the foundation for future multi-tenancy and vector search features.

**Status:** ✅ Completed

## 2. Key Changes

### Infrastructure
*   **PostgreSQL**: Integrated a PostgreSQL container via `docker-compose.yml` to serve as the primary data store.
*   **Alembic**: Set up asynchronous database migrations to manage schema evolution safely.
*   **Async Driver**: Switched to `asyncpg` for high-performance, non-blocking database operations.
*   **Query Analysis**: Added detailed SQL logging configuration for deep debugging of database flows.

### Database Schema
We implemented a normalized relational schema designed for extensibility:

*   **`users`**: Base identity table (UUID, email, username).
*   **`conversations`**: Metadata for chat sessions (title, archival status).
*   **`messages`**: The core chat log.
    *   Uses `JSONB` for `tool_calls` to flexibly store complex tool execution data without rigid schema changes.
    *   Uses `JSONB` for `metadata` to allow future expansion (observability metrics).
*   **`memories`**: Dedicated table for long-term user context (facts learned about the user).

### Repository Pattern
We refuted the pattern of direct database access in the application logic. instead, we implemented the **Repository Pattern** to decouple business logic from data access:

*   **`ConversationRepository`**: Handles creating conversations, appending messages, and retrieving history efficiently.
*   **`MemoryRepository`**: Manages storage and retrieval of user-specific facts.
*   **Benefit**: The `ChatOrchestrator` remains clean and focuses on flow logic, oblivious to the underlying SQL implementation.

### Application Logic
*   **Orchestrator**: Updated to load conversation history from the repository at the start of each run.
*   **API Routes**: Refactored to manage database sessions/transactions and inject repositories into the orchestrator.
*   **Persistence**: Ensured atomic commits for user messages (committed *before* LLM inference) and assistant responses (committed *after* generation).

## 3. Observability & Validation

### Database Flow Validation
We performed a "Deep Validation" (`scripts/validate_db_flow.py`) to trace a single user request through the entire stack.

**Verified Flow:**
1.  **Request**: `POST /api/chat` ("Explain quantum physics...")
2.  **DB Check**: `SELECT` user exists.
3.  **DB Write**: `INSERT` conversation -> `INSERT` user message -> `COMMIT`.
4.  **Orchestration**: Fetch memories (`SELECT`), generate LLM response.
5.  **DB Write**: `INSERT` assistant message -> `COMMIT`.
6.  **Retrieval**: `GET /api/conversations` returns the persisted data.

*See `docs/database_flow_analysis.md` for the full report.*

### Persistence Test
Verified that data survives server restarts:
1.  Start Server -> Chat -> Stop Server.
2.  Restart Server -> Chat History is retrieved successfully.

## 4. Future Outlook (Phase 2.5 & 3)

With the database foundation in place, we identified the next steps for scalability:
*   **Observability**: We plan to promote high-value metrics (token usage, latency, model version) from `JSONB` metadata to first-class columns (Phase 2.5).
*   **Vector Search**: The `memories` table is ready to be augmented with `pgvector` embeddings for semantic search (Phase 3).
