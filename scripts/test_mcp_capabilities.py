import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Mock Redis (required by mcp_client.py)
mock_redis = MagicMock()
mock_redis.get = AsyncMock(return_value=None)
mock_redis.set = AsyncMock()

async def run_tests():
    print("Initializing MCP Tool Registry (Mocked Redis)...")
    
    with patch('chatbot_ai_system.database.redis.redis_client', mock_redis):
        from chatbot_ai_system.tools import registry
        from chatbot_ai_system.tools.mcp_client import MCPClient
        from chatbot_ai_system.config.mcp_server_config import get_mcp_servers
        
        # Load servers
        servers = get_mcp_servers()
        print(f"Found {len(servers)} configured MCP servers.")
        
        results = {}

        for server_config in servers:
            print(f"\n--- Testing Server: {server_config.name} ---")
            
            # Check env vars
            missing = [v for v in server_config.required_env_vars if v not in os.environ and v not in server_config.env_vars]
            if missing:
                print(f"⚠️  Skipping {server_config.name}: Missing {missing}")
                results[server_config.name] = "SKIPPED (Missing Env)"
                continue

            client = None
            try:
                print(f"Connecting to {server_config.name}...")
                client = MCPClient(
                    name=server_config.name,
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env_vars or os.environ.copy()
                )
                
                # Connect directly to test
                await client.connect()
                print(f"✅ Connected to {server_config.name}")
                
                # List tools
                tools = await client.list_tools()
                print(f"✅ Found {len(tools)} tools")
                if tools:
                    print(f"   Sample: {tools[0]['function']['name']}")
                
                results[server_config.name] = f"PASSED ({len(tools)} tools)"
                
                # Close connection
                await client.close()
                
            except Exception as e:
                print(f"❌ Failed {server_config.name}: {e}")
                results[server_config.name] = f"FAILED: {e}"
                if client:
                    try:
                        await client.close()
                    except:
                        pass
        
        print("\n--- Summary ---")
        for name, result in results.items():
            print(f"{name}: {result}")

if __name__ == "__main__":
    asyncio.run(run_tests())
