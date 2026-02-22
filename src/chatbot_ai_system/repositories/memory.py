from typing import List
from uuid import UUID

from sqlalchemy import select

from chatbot_ai_system.database.models import Memory
from chatbot_ai_system.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    """Repository for user Long-Term Memory."""

    def __init__(self, session):
        super().__init__(session, Memory)

    async def get_user_memories(self, user_id: UUID) -> List[Memory]:
        """Get all memories for a user."""
        statement = select(Memory).where(Memory.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def add_memory(self, user_id: UUID, content: str, context: dict = None) -> Memory:
        """Add a new memory fact."""
        return await self.create(user_id=user_id, content=content, context=context)
