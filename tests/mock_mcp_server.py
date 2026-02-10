
from mcp.server.fastmcp import FastMCP

# Create a FastMCP server
mcp = FastMCP("demo_server")

@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.tool()
async def echo(message: str) -> str:
    """Echo the message back."""
    return f"Echo: {message}"

if __name__ == "__main__":
    mcp.run()
