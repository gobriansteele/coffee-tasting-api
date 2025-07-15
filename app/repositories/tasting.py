from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.coffee import Coffee
from app.models.tasting import TastingNote, TastingSession
from app.repositories.base import BaseRepository
from app.repositories.flavor_tag import flavor_tag_repository
from app.schemas.tasting import TastingSessionCreate, TastingSessionUpdate

logger = get_logger(__name__)


class TastingRepository(BaseRepository[TastingSession, TastingSessionCreate, TastingSessionUpdate]):
    """Repository for tasting session operations."""

    def __init__(self) -> None:
        super().__init__(TastingSession)

    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[TastingSession]:
        """Get all tasting sessions by user ID."""
        try:
            return list(await db.scalars(
                select(self.model)
                .options(
                    selectinload(self.model.tasting_notes)
                    .selectinload(TastingNote.flavor_tag),
                    selectinload(self.model.coffee)
                    .selectinload(Coffee.roaster)
                )
                .where(self.model.user_id == user_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            ))
        except Exception as e:
            logger.error(
                "Error getting tastings by user",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def create_with_notes(
        self,
        db: AsyncSession,
        *,
        tasting_data: TastingSessionCreate,
        user_id: str
    ) -> TastingSession:
        """Create a tasting session with associated notes."""
        try:
            # Create the tasting session directly
            db_session = self.model(
                **tasting_data.model_dump(exclude={'tasting_notes'}),
                user_id=user_id,
                created_by=user_id
            )
            db.add(db_session)
            await db.flush()  # Flush to get the session ID

            # Handle flavor tags and create tasting notes
            if tasting_data.tasting_notes:
                # Get all unique flavor names
                flavor_names = [note.flavor_name for note in tasting_data.tasting_notes]

                # Find or create flavor tags
                flavor_tags = await flavor_tag_repository.find_or_create_multiple(db, flavor_names, user_id=user_id)

                # Create mapping of flavor name to flavor tag
                flavor_map = {tag.name.lower(): tag for tag in flavor_tags}

                # Create tasting notes
                for note_data in tasting_data.tasting_notes:
                    flavor_tag = flavor_map.get(note_data.flavor_name.lower())
                    if flavor_tag:
                        note = TastingNote(
                            tasting_session_id=db_session.id,
                            flavor_tag_id=flavor_tag.id,
                            created_by=user_id,
                            **note_data.model_dump(exclude={'flavor_name'})
                        )
                        db.add(note)

            await db.commit()
            # Refresh with eager loading of tasting notes and their flavor tags
            await db.refresh(
                db_session,
                ['tasting_notes']
            )

            # Re-fetch with proper eager loading for response serialization
            result = await db.scalar(
                select(self.model)
                .options(
                    selectinload(self.model.tasting_notes)
                    .selectinload(TastingNote.flavor_tag),
                    selectinload(self.model.coffee)
                    .selectinload(Coffee.roaster)
                )
                .where(self.model.id == db_session.id)
            )
            if not result:
                raise ValueError("Failed to re-fetch created tasting session")
            db_session = result

            logger.info(
                "Created tasting session with notes",
                id=str(db_session.id),
                user_id=user_id,
                notes_count=len(tasting_data.tasting_notes or [])
            )
            return db_session
        except Exception as e:
            await db.rollback()
            logger.error(
                "Error creating tasting session",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_with_notes(
        self,
        db: AsyncSession,
        id: UUID
    ) -> TastingSession | None:
        """Get a tasting session with all its notes."""
        try:
            result = await db.scalar(
                select(self.model)
                .options(
                    selectinload(self.model.tasting_notes)
                    .selectinload(TastingNote.flavor_tag),
                    selectinload(self.model.coffee)
                    .selectinload(Coffee.roaster)
                )
                .where(self.model.id == id)
            )
            return result if result else None
        except Exception as e:
            logger.error(
                "Error getting tasting with notes",
                id=str(id),
                error=str(e)
            )
            raise

    async def delete_by_id(
        self,
        db: AsyncSession,
        *,
        id: UUID,
        user_id: str
    ) -> TastingSession:
        """Delete a tasting session by ID, ensuring it belongs to the user."""
        try:
            # Get the tasting if it belongs to the user
            tasting = await db.scalar(
                select(self.model).where(
                    self.model.id == id,
                    self.model.user_id == user_id
                )
            )

            if not tasting:
                raise ValueError(f"Tasting session {id} not found or doesn't belong to user {user_id}")

            # Delete the tasting (notes will cascade)
            await db.delete(tasting)
            await db.commit()

            logger.info(
                "Deleted tasting session",
                id=str(id),
                user_id=user_id
            )
            return tasting
        except Exception as e:
            await db.rollback()
            logger.error(
                "Error deleting tasting session",
                id=str(id),
                user_id=user_id,
                error=str(e)
            )
            raise

    async def count_by_user(
        self,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """Count total tasting sessions for a user."""
        try:
            count = await db.scalar(
                select(func.count(self.model.id))
                .where(self.model.user_id == user_id)
            )
            return count or 0
        except Exception as e:
            logger.error(
                "Error counting tastings for user",
                user_id=user_id,
                error=str(e)
            )
            raise


# Global instance
tasting_repository = TastingRepository()
