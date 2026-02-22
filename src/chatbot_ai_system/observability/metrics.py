"""
Prometheus metrics definition for the Chatbot AI System.
"""

from prometheus_client import Counter, Histogram

# --- LLM Metrics ---

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total", "Total number of LLM requests", ["model", "provider", "status"]
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "Time taken for LLM requests to complete",
    ["model", "provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total number of tokens processed",
    ["model", "provider", "type"],  # type: prompt, completion
)

LLM_TTFT_SECONDS = Histogram(
    "llm_ttft_seconds",
    "Time to First Token (TTFT) for streaming responses",
    ["model", "provider"],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

# --- Tool Execution Metrics ---

TOOL_EXECUTION_TOTAL = Counter(
    "tool_execution_total", "Total number of tool executions", ["tool_name", "status"]
)

TOOL_EXECUTION_DURATION_SECONDS = Histogram(
    "tool_execution_duration_seconds",
    "Time taken for tool execution",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# --- Orchestrator/Business Logic ---

INTENT_CLASSIFICATION_TOTAL = Counter(
    "intent_classification_total", "Total number of intent classifications", ["intent"]
)

ORCHESTRATOR_REQUEST_DURATION_SECONDS = Histogram(
    "orchestrator_request_duration_seconds",
    "Total time taken for full orchestration flow",
    ["intent"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0],
)
