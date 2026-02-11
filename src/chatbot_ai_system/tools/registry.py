from typing import Dict, List, Type, Any, Optional
from .base import MCPTool
try:
    from .mcp_client import MCPClient
except ImportError:
    MCPClient = None

class RemoteMCPTool(MCPTool):
    """Wrapper for a tool provided by a remote MCP server."""
    
    def __init__(self, client: 'MCPClient', name: str, description: str, schema: Dict[str, Any]):
        self.client = client
        self.name = name
        self.description = description
        self.schema = schema
        self.args_schema = None  # Not used for remote tools

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert tool definition to Ollama/OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }

    async def run(self, **kwargs) -> Any:
        """Execute the tool on the remote server."""
        return await self.client.call_tool(self.name, kwargs)


class ToolRegistry:
    """Registry to manage available tools."""

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._mcp_clients: List['MCPClient'] = []
        self._remote_tools_cache: Dict[str, RemoteMCPTool] = {}

    def register(self, tool: MCPTool):
        """Register a new local tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} already registered")
        self._tools[tool.name] = tool

    def register_mcp_client(self, client: 'MCPClient'):
        """Register an MCP client."""
        self._mcp_clients.append(client)

    def get_tool(self, name: str) -> MCPTool:
        """Get a tool by name (checks local first, then cached remote)."""
        if name in self._tools:
            return self._tools[name]
        
        if name in self._remote_tools_cache:
            return self._remote_tools_cache[name]
            
        raise ValueError(f"Tool {name} not found")

    def get_all_tools(self) -> List[MCPTool]:
        """Get all registered tools (local + cached remote)."""
        return list(self._tools.values()) + list(self._remote_tools_cache.values())

    async def refresh_remote_tools(self):
        """Refresh tools from all registered MCP clients."""
        self._remote_tools_cache.clear()
        
        for client in self._mcp_clients:
            try:
                tool_list = await client.list_tools()
                for tool_def in tool_list:
                    # tool_def is {'type': 'function', 'function': {'name': ..., ...}}
                    func = tool_def.get("function", {})
                    name = func.get("name")
                    if name:
                        remote_tool = RemoteMCPTool(
                            client=client,
                            name=name,
                            description=func.get("description", ""),
                            schema=func.get("parameters", {})
                        )
                        self._remote_tools_cache[name] = remote_tool
            except Exception as e:
                # Log error but continue
                print(f"Error fetching tools from client: {e}")

    async def get_ollama_tools(self, query: Optional[str] = None) -> List[Dict]:
        """Get filtered tools in Ollama format based on query."""
        MAX_TOOLS = 5
        
        # Get all available tools
        local_tools = [t for t in self._tools.values()]
        remote_tools = [t for t in self._remote_tools_cache.values()]
        all_tools = local_tools + remote_tools

        if not query:
            # If no query, return an empty list or a default set (we'll prefer empty for "Decision Discipline")
            return []

        # Step 2 & 8: Filter tools based on keywords and enforce MAX_TOOLS
        q = query.lower()
        filtered = []
        
        # Filesystem
        if any(k in q for k in ["file", "read", "directory", "path", "folder", "list", "write", "search"]):
             filtered.extend([t for t in all_tools if t.name in ["read_file", "list_directory", "write_file", "search_files", "get_file_info"]])
        
        # Git
        if any(k in q for k in ["git", "commit", "branch", "log", "diff", "repo", "status", "push"]):
            filtered.extend([t for t in all_tools if t.name.startswith("git_") or t.name == "check_repo_status"])
            
        # Fetch / Web
        if any(k in q for k in ["fetch", "url", "http", "website", "html", "get", "download"]):
            filtered.extend([t for t in all_tools if t.name == "fetch_html"])
            
        # Time
        if any(k in q for k in ["time", "now", "date", "clock"]):
            filtered.extend([t for t in all_tools if t.name == "get_current_time"])

        # Deduplicate and limit
        seen = set()
        final_tools = []
        for t in filtered:
            if t.name not in seen:
                final_tools.append(t.to_ollama_format())
                seen.add(t.name)
        
        return final_tools[:MAX_TOOLS]
