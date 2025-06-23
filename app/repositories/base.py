from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.logging import get_logger
from app.models.base import Base

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID."""
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__}", error=str(e))
            raise
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        try:
            stmt = select(self.model).offset(skip).limit(limit)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}", error=str(e))
            raise
    
    async def create(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """Create a new record."""
        try:
            obj_in_data = obj_in.model_dump()
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
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record."""
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)
            
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
    
    async def delete(self, db: AsyncSession, *, id: UUID) -> ModelType:
        """Delete a record by ID."""
        try:
            obj = await self.get(db, id)
            if obj:
                await db.delete(obj)
                await db.commit()
                logger.info(f"Deleted {self.model.__name__}", id=str(id))
                return obj
            else:
                raise ValueError(f"{self.model.__name__} with id {id} not found")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__}", error=str(e))
            raise
    
    async def count(self, db: AsyncSession) -> int:
        """Count total records."""
        try:
            stmt = select(func.count(self.model.id))
            result = await db.execute(stmt)
            count = result.scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}", error=str(e))
            raise
    
    async def exists(self, db: AsyncSession, id: UUID) -> bool:
        """Check if record exists."""
        try:
            obj = await self.get(db, id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__}", error=str(e))
            raise