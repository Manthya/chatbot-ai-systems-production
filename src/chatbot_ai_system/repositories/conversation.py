from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from chatbot_ai_system.database.models import Conversation, Message, User
from chatbot_ai_system.repositories.base import BaseRepository

class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation-related operations."""

    def __init__(self, session):
        super().__init__(session, Conversation)

    async def get_conversation_with_messages(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation with all messages loaded."""
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_conversation(self, user_id: UUID, title: Optional[str] = None) -> Conversation:
        """Create a new conversation for a user."""
        return await self.create(user_id=user_id, title=title)

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        sequence_number: int,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        # Observability
        token_count_prompt: Optional[int] = None,
        token_count_completion: Optional[int] = None,
        model: Optional[str] = None,
        latency_ms: Optional[int] = None,
        finish_reason: Optional[str] = None
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_number=sequence_number,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            metadata_=metadata,
            token_count_prompt=token_count_prompt,
            token_count_completion=token_count_completion,
            model=model,
            latency_ms=latency_ms,
            finish_reason=finish_reason
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_user_conversations(self, user_id: UUID, limit: int = 50) -> List[Conversation]:
        """Get all conversations for a user, ordered by update time."""
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_recent_messages(self, conversation_id: UUID, limit: int = 50) -> List[Message]:
        """Get the most recent messages for a conversation (Sliding Window)."""
        # Fetch in descending order (newest first) to get the "tail", then reverse.
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        messages = result.scalars().all()
        return list(reversed(messages))
