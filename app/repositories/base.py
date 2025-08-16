from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.base import Base

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: UUID, include_deleted: bool = False) -> ModelType | None:
        """Get a single record by ID."""
        try:
            obj = await db.get(self.model, id)
            if obj and not include_deleted and obj.deleted_at is not None:
                return None
            return obj
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__}", error=str(e))
            raise

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, include_deleted: bool = False
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        try:
            query = select(self.model)
            if not include_deleted:
                query = query.where(self.model.deleted_at.is_(None))
            return list(await db.scalars(query.offset(skip).limit(limit)))
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}", error=str(e))
            raise

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType, current_user_id: str | None = None
    ) -> ModelType:
        """Create a new record."""
        try:
            obj_in_data = obj_in.model_dump()
            if current_user_id:
                obj_in_data["created_by"] = current_user_id
                obj_in_data["updated_by"] = current_user_id
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__}", id=str(db_obj.id))
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating {self.model.__name__}", error=str(e))
            raise

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        current_user_id: str | None = None,
    ) -> ModelType:
        """Update an existing record."""
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            if current_user_id:
                update_data["updated_by"] = current_user_id

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Updated {self.model.__name__}", id=str(db_obj.id))
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__}", error=str(e))
            raise

    async def delete(
        self, db: AsyncSession, *, id: UUID, current_user_id: str | None = None, hard_delete: bool = False
    ) -> ModelType:
        """Soft delete a record by ID."""
        try:
            obj = await self.get(db, id)
            if obj:
                if hard_delete:
                    # Hard delete - permanently remove from database
                    await db.delete(obj)
                    await db.commit()
                    logger.info(f"Hard deleted {self.model.__name__}", id=str(id))
                else:
                    # Soft delete - mark as deleted with audit info
                    obj.deleted_at = datetime.utcnow()
                    if current_user_id:
                        obj.deleted_by = current_user_id
                    db.add(obj)
                    await db.commit()
                    await db.refresh(obj)
                    logger.info(f"Soft deleted {self.model.__name__}", id=str(id))
                return obj
            else:
                raise ValueError(f"{self.model.__name__} with id {id} not found")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__}", error=str(e))
            raise

    async def count(self, db: AsyncSession, include_deleted: bool = False) -> int:
        """Count total records."""
        try:
            query = select(func.count(self.model.id))
            if not include_deleted:
                query = query.where(self.model.deleted_at.is_(None))
            count = await db.scalar(query)
            return count or 0
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}", error=str(e))
            raise

    async def exists(self, db: AsyncSession, id: UUID, include_deleted: bool = False) -> bool:
        """Check if record exists."""
        try:
            obj = await self.get(db, id, include_deleted=include_deleted)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__}", error=str(e))
            raise

    async def restore(self, db: AsyncSession, *, id: UUID, current_user_id: str | None = None) -> ModelType:
        """Restore a soft-deleted record."""
        try:
            obj = await self.get(db, id, include_deleted=True)
            if obj and obj.deleted_at is not None:
                obj.deleted_at = None
                obj.deleted_by = None
                if current_user_id:
                    obj.updated_by = current_user_id
                db.add(obj)
                await db.commit()
                await db.refresh(obj)
                logger.info(f"Restored {self.model.__name__}", id=str(id))
                return obj
            else:
                raise ValueError(f"{self.model.__name__} with id {id} not found or not deleted")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error restoring {self.model.__name__}", error=str(e))
            raise
