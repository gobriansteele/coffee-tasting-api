from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FlavorTagBase(BaseModel):
    """Base flavor tag schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Flavor tag name")
    category: str | None = Field(None, max_length=50, description="Flavor category (e.g., fruity, nutty)")
    description: str | None = Field(None, description="Description of the flavor")


class FlavorTagCreate(FlavorTagBase):
    """Schema for creating a flavor tag."""
    pass


class FlavorTagUpdate(BaseModel):
    """Schema for updating a flavor tag."""
    name: str | None = Field(None, min_length=1, max_length=100, description="Flavor tag name")
    category: str | None = Field(None, max_length=50, description="Flavor category")
    description: str | None = Field(None, description="Description of the flavor")


class FlavorTagResponse(FlavorTagBase):
    """Schema for flavor tag responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
