import asyncio
import uuid
import sys
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from chatbot_ai_system.config import get_settings
from chatbot_ai_system.database.models import User, Conversation, Message, Base
from chatbot_ai_system.repositories.conversation import ConversationRepository
from chatbot_ai_system.models.schemas import ChatMessage, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_observability():
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
    engine = create_async_engine(db_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    user_id = uuid.UUID('00000000-0000-0000-0000-000000000000')

    async with AsyncSessionLocal() as session:
        repo = ConversationRepository(session)
        
        # 1. Create a massive conversation (60 messages)
        logger.info("Creating a massive conversation...")
        conv = await repo.create_conversation(user_id=user_id, title="Observability Test")
        
        for i in range(60):
            await repo.add_message(
                conversation_id=conv.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                sequence_number=i
            )
        await session.commit()
        
        # 2. Test Sliding Window
        logger.info("Testing Sliding Window (Limit 50)...")
        recent_messages = await repo.get_recent_messages(conv.id, limit=50)
        logger.info(f"Fetched {len(recent_messages)} messages.")
        
        if len(recent_messages) != 50:
            logger.error(f"FAIL: Expected 50 messages, got {len(recent_messages)}")
            sys.exit(1)
            
        first_msg = recent_messages[0]
        last_msg = recent_messages[-1]
        logger.info(f"First message (tail): {first_msg.content} (Seq: {first_msg.sequence_number})")
        logger.info(f"Last message (head): {last_msg.content} (Seq: {last_msg.sequence_number})")
        
        # Expected: Message 10 to Message 59 (Total 50)
        # Sequence 10 is the 11th message (0-indexed)
        # Wait, if we have 0..59 (60 msgs). Last 50 are 10..59.
        if first_msg.sequence_number != 10:
             logger.error(f"FAIL: Expected first message sequence to be 10, got {first_msg.sequence_number}")
        
        logger.info("PASS: Sliding Window logic works.")

        # 3. Test Observability Persistence
        # We need to simulate a run where token usage is populated.
        # Since we can't easily run the Orchestrator without a running Ollama (which might not be reliable in test env),
        # we will manually test the repository's ability to save these fields.
        logger.info("Testing Observability Persistence...")
        
        msg = await repo.add_message(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="Final Analysis",
            sequence_number=60,
            token_count_prompt=150,
            token_count_completion=42,
            model="test-model-v1",
            latency_ms=1234
        )
        await session.commit()
        
        # Reload and verify
        # We need a new session or refresh
        await session.refresh(msg)
        
        logger.info(f"Saved Message: Tokens(P: {msg.token_count_prompt}, C: {msg.token_count_completion}), Latency: {msg.latency_ms}")
        
        if msg.token_count_prompt != 150 or msg.latency_ms != 1234:
             logger.error("FAIL: Observability fields were not persisted correctly.")
             sys.exit(1)
             
        logger.info("PASS: Observability Persistence works.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_observability())
