from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from pydantic import BaseModel, Field


class MCPTool(ABC):
    """Abstract base class for MCP-style tools."""

    name: str = Field(..., description="Unique name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    args_schema: Type[BaseModel] = Field(..., description="Pydantic model for arguments")

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert tool definition to Ollama/OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool with provided arguments."""
        pass
