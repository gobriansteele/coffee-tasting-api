
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.coffee import Roaster
from app.repositories.base import BaseRepository
from app.schemas.roaster import RoasterCreate, RoasterUpdate

logger = get_logger(__name__)


class RoasterRepository(BaseRepository[Roaster, RoasterCreate, RoasterUpdate]):
    """Repository for roaster operations."""

    def __init__(self) -> None:
        super().__init__(Roaster)

    async def get_by_name(self, db: AsyncSession, name: str) -> Roaster | None:
        """Get roaster by name."""
        try:
            stmt = select(self.model).where(self.model.name == name)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting roaster by name", name=name, error=str(e))
            raise

    async def search_by_name(
        self,
        db: AsyncSession,
        name_query: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[Roaster]:
        """Search roasters by name (case-insensitive partial match)."""
        try:
            stmt = (
                select(self.model)
                .where(self.model.name.ilike(f"%{name_query}%"))
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Error searching roasters by name", query=name_query, error=str(e))
            raise

    async def get_by_location(
        self,
        db: AsyncSession,
        location: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[Roaster]:
        """Get roasters by location."""
        try:
            stmt = (
                select(self.model)
                .where(self.model.location.ilike(f"%{location}%"))
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Error getting roasters by location", location=location, error=str(e))
            raise


# Global instance
roaster_repository = RoasterRepository()
