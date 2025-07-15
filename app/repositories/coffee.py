from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.coffee import Coffee, FlavorTag
from app.repositories.base import BaseRepository
from app.schemas.coffee import CoffeeCreate, CoffeeUpdate

logger = get_logger(__name__)


class CoffeeRepository(BaseRepository[Coffee, CoffeeCreate, CoffeeUpdate]):
    """Repository for coffee operations."""

    def __init__(self) -> None:
        super().__init__(Coffee)

    async def get(self, db: AsyncSession, id: UUID, include_delete: bool = False) -> Coffee | None:
        """Get a single coffee by ID with eager loaded flavor_tags."""
        try:
            result = await db.scalar(
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
                .where(self.model.id == id)
            )
            return result if result else None
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__}", error=str(e))
            raise

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> list[Coffee]:
        """Get multiple records with pagination and eager load flavor_tags."""
        try:
            return list(await db.scalars(
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
                .offset(skip)
                .limit(limit)
            ))
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}", error=str(e))
            raise

    async def create_with_flavor_tags(
        self,
        db: AsyncSession,
        *,
        coffee_data: CoffeeCreate,
        flavor_tags: list[FlavorTag],
        current_user_id: str | None = None
    ) -> Coffee:
        """Create a coffee with associated flavor tags."""
        try:
            # Create coffee data without flavor_tags field
            coffee_dict = coffee_data.model_dump(exclude={'flavor_tags'})
            if current_user_id:
                coffee_dict['created_by'] = current_user_id
                coffee_dict['updated_by'] = current_user_id
            db_coffee = self.model(**coffee_dict)

            # Associate flavor tags
            db_coffee.flavor_tags = flavor_tags

            db.add(db_coffee)
            await db.commit()
            await db.refresh(db_coffee, ['flavor_tags'])

            logger.info(
                "Created coffee with flavor tags",
                coffee_id=str(db_coffee.id),
                name=db_coffee.name,
                flavor_count=len(flavor_tags)
            )
            return db_coffee

        except Exception as e:
            await db.rollback()
            logger.error(
                "Error creating coffee with flavor tags",
                error=str(e)
            )
            raise

    async def get_with_flavor_tags(
        self,
        db: AsyncSession,
        id: UUID
    ) -> Coffee | None:
        """Get a coffee with its flavor tags."""
        try:
            result = await db.scalar(
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
                .where(self.model.id == id)
            )
            return result if result else None
        except Exception as e:
            logger.error(
                "Error getting coffee with flavor tags",
                id=str(id),
                error=str(e)
            )
            raise

    async def get_by_name_and_roaster(
        self,
        db: AsyncSession,
        name: str,
        roaster_id: UUID
    ) -> Coffee | None:
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
    ) -> list[Coffee]:
        """Get all coffees by roaster."""
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
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
    ) -> list[Coffee]:
        """Search coffees by name (case-insensitive partial match)."""
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
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
    ) -> list[Coffee]:
        """Get coffees by origin country."""
        try:
            stmt = (
                select(self.model)
                .options(selectinload(self.model.flavor_tags))
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
