from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_ai_system.database.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    async def get(self, id: UUID) -> Optional[T]:
        """Get a record by ID."""
        statement = select(self.model_cls).where(self.model_cls.id == id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination."""
        statement = select(self.model_cls).offset(skip).limit(limit)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        """Create a new record."""
        instance = self.model_cls(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # Flush to get ID, but don't commit yet
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs) -> Optional[T]:
        """Update a record by ID."""
        statement = (
            update(self.model_cls)
            .where(self.model_cls.id == id)
            .values(**kwargs)
            .returning(self.model_cls)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        statement = delete(self.model_cls).where(self.model_cls.id == id)
        result = await self.session.execute(statement)
        return result.rowcount > 0
