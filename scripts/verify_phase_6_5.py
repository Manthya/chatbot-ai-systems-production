import asyncio
import os
import sys
import logging
from chatbot_ai_system.tools.registry import ToolRegistry
from chatbot_ai_system.tools.implementations.web_search import DuckDuckGoSearchTool
from chatbot_ai_system.tools.implementations.python_sandbox import LocalPythonSandbox

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to python path for local execution
sys.path.append(os.path.join(os.getcwd(), "src"))

async def main():
    logger.info("Starting Phase 6.5 Verification (Free Tools)")
    
    registry = ToolRegistry()
    
    # 1. Verify Registration
    tools = registry.get_all_tools()
    tool_names = [t.name for t in tools]
    logger.info(f"Registered Tools: {tool_names}")
    
    if "web_search_duckduckgo" not in tool_names:
        logger.error("❌ web_search_duckduckgo NOT registered")
        return
    if "run_python_script" not in tool_names:
        logger.error("❌ run_python_script NOT registered")
        return
        
    logger.info("✅ Tools successfully registered.")
    
    # 2. Test Web Search
    logger.info("\n--- Testing Web Search ---")
    search_tool = registry.get_tool("web_search_duckduckgo")
    try:
        # Search for something time-sensitive or specific
        result = await search_tool.run(query="current python version", max_results=2)
        logger.info(f"Search Result:\n{result}")
        if "Python" in result or "No results" in result:
             logger.info("✅ Web Search executed successfully.")
        else:
             logger.warning("⚠️ Web Search result unexpected.")
    except Exception as e:
        logger.error(f"❌ Web Search failed: {e}")

    # 3. Test Python Sandbox
    logger.info("\n--- Testing Python Sandbox ---")
    code_tool = registry.get_tool("run_python_script")
    
    # Test 3a: Valid Code
    safe_code = "print(15 * 25)"
    try:
        result = await code_tool.run(code=safe_code)
        logger.info(f"Code Result (15*25): {result.strip()}")
        if "375" in result:
            logger.info("✅ Basic Code Execution passed.")
        else:
            logger.error(f"❌ Basic Code Execution failed. Expected 375, got {result}")
    except Exception as e:
        logger.error(f"❌ Code Execution failed: {e}")
        
    # Test 3b: Timeout
    logger.info("\n--- Testing Timeout (Security) ---")
    timeout_code = "import time; time.sleep(5); print('finished')"
    try:
        # We set tool timeout to 2s for this test via override if possible, 
        # but the tool signature run(code, timeout=10) accepts timeout.
        result = await code_tool.run(code=timeout_code, timeout=2)
        logger.info(f"Timeout Result: {result}")
        if "timed out" in result:
            logger.info("✅ Timeout Enforcement passed.")
        else:
            logger.error("❌ Timeout Enforcement failed.")
    except Exception as e:
         logger.error(f"❌ Timeout test error: {e}")

    logger.info("\nVerification Phase 6.5 Complete.")

if __name__ == "__main__":
    asyncio.run(main())
