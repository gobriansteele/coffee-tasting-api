from datetime import datetime
from typing import Any
from uuid import UUID as PY_UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as SQL_UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model class with common fields."""
    
    # Common fields for all models
    id: Mapped[PY_UUID] = mapped_column(SQL_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    @declared_attr.directive
    def __tablename__(self) -> str:
        """Generate table name from class name."""
        return self.__name__.lower()
    
    def dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns.values()
        }