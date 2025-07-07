from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.coffee import FlavorTag
from app.repositories.base import BaseRepository
from app.schemas.flavor_tag import FlavorTagCreate, FlavorTagUpdate

logger = get_logger(__name__)


class FlavorTagRepository(BaseRepository[FlavorTag, FlavorTagCreate, FlavorTagUpdate]):
    """Repository for flavor tag operations."""

    def __init__(self) -> None:
        super().__init__(FlavorTag)

    async def find_or_create_by_name(
        self,
        db: AsyncSession,
        name: str,
        category: str | None = None
    ) -> FlavorTag:
        """Find a flavor tag by name or create it if it doesn't exist.

        Name matching is case-insensitive to avoid duplicates.
        """
        try:
            # First try to find existing tag (case-insensitive)
            existing_tag = await db.scalar(
                select(self.model)
                .where(self.model.name.ilike(name))
            )

            if existing_tag:
                logger.debug(f"Found existing flavor tag: {existing_tag.name}")
                return existing_tag

            # Create new tag if not found
            new_tag = self.model(
                name=name,
                category=category
            )
            db.add(new_tag)
            await db.flush()  # Flush to get ID but don't commit yet

            logger.info(f"Created new flavor tag: {name}")
            return new_tag

        except Exception as e:
            logger.error(
                "Error in find_or_create_by_name",
                name=name,
                error=str(e)
            )
            raise

    async def find_or_create_multiple(
        self,
        db: AsyncSession,
        names: list[str]
    ) -> list[FlavorTag]:
        """Find or create multiple flavor tags by name.

        Returns a list of FlavorTag objects in the same order as the input names.
        """
        try:
            tags = []
            for name in names:
                if name:  # Skip empty strings
                    tag = await self.find_or_create_by_name(db, name.strip())
                    tags.append(tag)
            return tags

        except Exception as e:
            logger.error(
                "Error in find_or_create_multiple",
                names=names,
                error=str(e)
            )
            raise

    async def get_by_name(
        self,
        db: AsyncSession,
        name: str
    ) -> FlavorTag | None:
        """Get a flavor tag by name (case-insensitive)."""
        try:
            return await db.scalar(
                select(self.model)
                .where(self.model.name.ilike(name))
            )
        except Exception as e:
            logger.error(
                "Error getting flavor tag by name",
                name=name,
                error=str(e)
            )
            raise

    async def search(
        self,
        db: AsyncSession,
        query: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[FlavorTag]:
        """Search flavor tags by name or category."""
        try:
            return list(await db.scalars(
                select(self.model)
                .where(
                    self.model.name.ilike(f"%{query}%") |
                    self.model.category.ilike(f"%{query}%")
                )
                .offset(skip)
                .limit(limit)
            ))
        except Exception as e:
            logger.error(
                "Error searching flavor tags",
                query=query,
                error=str(e)
            )
            raise


# Global instance
flavor_tag_repository = FlavorTagRepository()
