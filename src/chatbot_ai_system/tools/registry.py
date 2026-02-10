from typing import Dict, List, Type
from .base import MCPTool

class ToolRegistry:
    """Registry to manage available tools."""

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}

    def register(self, tool: MCPTool):
        """Register a new tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} already registered")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> MCPTool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        return self._tools[name]

    def get_all_tools(self) -> List[MCPTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_ollama_tools(self) -> List[Dict]:
        """Get all tools in Ollama format."""
        return [tool.to_ollama_format() for tool in self._tools.values()]
