"""Roaster schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RoasterBase(BaseModel):
    """Base roaster schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Roaster name")
    location: str | None = Field(None, max_length=255, description="Roaster location (city, state, country)")
    website: str | None = Field(None, max_length=500, description="Roaster website URL")
    description: str | None = Field(None, description="Roaster description")

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str | None) -> str | None:
        """Auto-add https:// prefix if missing."""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class RoasterCreate(RoasterBase):
    """Schema for creating a new roaster."""

    pass


class RoasterUpdate(BaseModel):
    """Schema for updating an existing roaster."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Roaster name")
    location: str | None = Field(None, max_length=255, description="Roaster location")
    website: str | None = Field(None, max_length=500, description="Roaster website URL")
    description: str | None = Field(None, description="Roaster description")

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str | None) -> str | None:
        """Auto-add https:// prefix if missing."""
        if v and not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v


class RoasterSummary(BaseModel):
    """Slim roaster schema for embedding in other responses."""

    id: UUID
    name: str
    location: str | None = None

    class Config:
        from_attributes = True


class RoasterResponse(RoasterBase):
    """Schema for roaster responses."""

    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RoasterListResponse(BaseModel):
    """Paginated roaster list response."""

    items: list[RoasterResponse]
    total: int
    skip: int
    limit: int
