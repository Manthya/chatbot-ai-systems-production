"""DuckDuckGo Web Search tool implementation."""

import logging

# Try importing, but fail gracefully if not installed so app doesn't crash
try:
    from duckduckgo_search import DDGS

    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

from pydantic import BaseModel, Field

from chatbot_ai_system.tools.base import MCPTool

logger = logging.getLogger(__name__)


class DuckDuckGoSearchArgs(BaseModel):
    query: str = Field(..., description="The search query.")
    max_results: int = Field(
        default=5, description="Maximum number of results to return (default: 5)."
    )


class DuckDuckGoSearchTool(MCPTool):
    """Tool for performing web searches using DuckDuckGo."""

    name = "web_search_duckduckgo"
    description = (
        "Perform a web search using DuckDuckGo. "
        "Use this for finding up-to-date information, news, or specific facts."
    )

    args_schema = DuckDuckGoSearchArgs

    async def run(self, query: str, max_results: int = 5) -> str:
        """Execute the search."""
        if not HAS_DDGS:
            return "Error: duckduckgo-search library is not installed."

        try:
            results = []
            with DDGS() as ddgs:
                # 'text' method replaces 'answers' in newer versions
                # ddgs.text() returns an iterator
                ddgs_gen = ddgs.text(query, max_results=max_results)
                for r in ddgs_gen:
                    results.append(r)

            if not results:
                return "No results found."

            # Format results
            formatted = []
            for i, res in enumerate(results, 1):
                title = res.get("title", "No Title")
                href = res.get("href", "No URL")
                body = res.get("body", "No Description")
                formatted.append(f"{i}. [{title}]({href})\n   {body}")

            return "\n\n".join(formatted)

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return f"Search failed: {str(e)}"
