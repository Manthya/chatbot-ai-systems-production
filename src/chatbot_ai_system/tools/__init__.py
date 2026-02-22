from .base import MCPTool
from .registry import ToolRegistry
from .system_tools import CheckRepoStatusTool, GetCurrentTimeTool

# Global registry instance
registry = ToolRegistry()

# Register default tools
registry.register(GetCurrentTimeTool())
registry.register(CheckRepoStatusTool())
