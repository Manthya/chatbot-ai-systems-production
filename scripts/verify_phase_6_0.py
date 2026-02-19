import asyncio
import os
import sys
import logging
from chatbot_ai_system.config import get_settings
from chatbot_ai_system.providers.factory import ProviderFactory
from chatbot_ai_system.models.schemas import ChatMessage, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to python path for local execution
sys.path.append(os.path.join(os.getcwd(), "src"))

async def test_provider(name: str):
    logger.info(f"--- Testing Provider: {name} ---")
    try:
        provider = ProviderFactory.get_provider(name)
        logger.info(f"Successfully initialized {name}")
        
        # Check health
        is_healthy = await provider.health_check()
        logger.info(f"Health check: {is_healthy}")
        
        if is_healthy:
            # Test completion
            messages = [ChatMessage(role=MessageRole.USER, content="Hello, say 'Test Successful' if you can hear me.")]
            response = await provider.complete(messages=messages, max_tokens=10)
            logger.info(f"Response: {response.message.content}")
        else:
            logger.warning(f"Provider {name} is not healthy (likely missing API key). Skipping completion test.")
            
    except Exception as e:
        logger.error(f"Failed to test {name}: {e}")

async def main():
    logger.info("Starting Phase 6.0 Verification")
    
    # 1. Test Default (Ollama) - Should always work if Ollama is running
    await test_provider("ollama")
    
    # 2. Test OpenAI (Optional)
    if os.environ.get("OPENAI_API_KEY"):
        await test_provider("openai")
    else:
        logger.info("Skipping OpenAI test (No API Key)")
        
    # 3. Test Anthropic (Optional)
    if os.environ.get("ANTHROPIC_API_KEY"):
        await test_provider("anthropic")
    else:
        logger.info("Skipping Anthropic test (No API Key)")

    # 4. Test Gemini (Optional)
    if os.environ.get("GEMINI_API_KEY"):
        await test_provider("gemini")
    else:
        logger.info("Skipping Gemini test (No API Key)")

    logger.info("Verification Complete")

if __name__ == "__main__":
    asyncio.run(main())
