
import asyncio
import os
import logging
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to an external MCP server via stdio."""

    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Initialize MCP client.
        
        Args:
            name: Identifier for this server (e.g. 'git', 'filesystem')
            command: Command to run the server
            args: Arguments for the command
            env: Environment variables
        """
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None

    async def connect(self):
        """Connect to the MCP server."""
        logger.info(f"Connecting to MCP server {self.name}...")
        
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env
        )
        
        self._exit_stack = AsyncExitStack()
        
        try:
            read, write = await self._exit_stack.enter_async_context(stdio_client(server_params))
            self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            logger.info(f"Connected to MCP server {self.name}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            if self._exit_stack:
                await self._exit_stack.aclose()
            self._exit_stack = None
            raise

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools in OpenAI/Ollama format."""
        if not self.session:
            # Try to connect if not connected
            try:
                await self.connect()
            except Exception:
                return []
                
        try:
            logger.info(f"Listing tools for {self.name}...")
            result = await self.session.list_tools()
            logger.info(f"Raw list_tools result for {self.name}: {len(result.tools)} tools found")
            tools = []
            for tool in result.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            return tools
        except Exception as e:
            logger.error(f"Error listing tools for {self.name}: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            await self.connect()
            
        try:
            result = await self.session.call_tool(name, arguments)
            # Result usually contains 'content' which is a list of text/image
            # We'll flatten it to a string for simple return, or return structure
            
            output = []
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
                # Handle other types if needed
                
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error calling tool {name} on {self.name}: {e}")
            raise

    async def close(self):
        """Close the connection."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None
