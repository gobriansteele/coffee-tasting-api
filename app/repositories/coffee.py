from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coffee import Coffee
from app.schemas.coffee import CoffeeCreate, CoffeeUpdate
from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoffeeRepository(BaseRepository[Coffee, CoffeeCreate, CoffeeUpdate]):
    """Repository for coffee operations."""

    def __init__(self) -> None:
        super().__init__(Coffee)

    async def get_by_name_and_roaster(
        self, 
        db: AsyncSession, 
        name: str, 
        roaster_id: UUID
    ) -> Optional[Coffee]:
        """Get coffee by name and roaster ID."""
        try:
            stmt = select(self.model).where(
                self.model.name == name,
                self.model.roaster_id == roaster_id
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "Error getting coffee by name and roaster", 
                name=name, 
                roaster_id=str(roaster_id), 
                error=str(e)
            )
            raise

    async def get_by_roaster(
        self, 
        db: AsyncSession, 
        roaster_id: UUID, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Coffee]:
        """Get all coffees by roaster."""
        try:
            stmt = (
                select(self.model)
                .where(self.model.roaster_id == roaster_id)
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                "Error getting coffees by roaster", 
                roaster_id=str(roaster_id), 
                error=str(e)
            )
            raise

    async def search_by_name(
        self, 
        db: AsyncSession, 
        name_query: str, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Coffee]:
        """Search coffees by name (case-insensitive partial match)."""
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
            logger.error(
                "Error searching coffees by name", 
                query=name_query, 
                error=str(e)
            )
            raise

    async def get_by_origin_country(
        self, 
        db: AsyncSession, 
        country: str, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Coffee]:
        """Get coffees by origin country."""
        try:
            stmt = (
                select(self.model)
                .where(self.model.origin_country.ilike(f"%{country}%"))
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                "Error getting coffees by origin country", 
                country=country, 
                error=str(e)
            )
            raise


# Global instance
coffee_repository = CoffeeRepository()