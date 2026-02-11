import asyncio
import os
import sys
from chatbot_ai_system.tools.mcp_client import MCPClient

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

async def inspect_server(name, command, args):
    print(f"\n--- Inspecting {name} ---")
    client = MCPClient(name, command, args, env=os.environ.copy())
    try:
        await client.connect()
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"- {tool['function']['name']}: {tool['function']['description'][:50]}...")
            print(f"  Args: {tool['function']['parameters']['properties'].keys()}")
        await client.close()
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Filesystem
    await inspect_server(
        "filesystem",
        "npx",
        ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()]
    )

    # Git
    await inspect_server(
        "git",
        "npx",
        ["-y", "@mseep/git-mcp-server"]
    )
    
    # Fetch
    await inspect_server(
        "fetch",
        "npx",
        ["-y", "zcaceres/fetch-mcp"]
    )

if __name__ == "__main__":
    asyncio.run(main())
