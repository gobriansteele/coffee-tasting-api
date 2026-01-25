"""Flavor schemas for API requests and responses."""

from uuid import UUID

from pydantic import BaseModel, Field


class FlavorBase(BaseModel):
    """Base flavor schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Flavor name (unique)")
    category: str | None = Field(None, max_length=50, description="Flavor category (e.g., fruity, nutty)")


class FlavorCreate(FlavorBase):
    """Schema for creating a flavor."""

    pass


class FlavorResponse(FlavorBase):
    """Schema for flavor responses."""

    id: UUID

    class Config:
        from_attributes = True


class FlavorListResponse(BaseModel):
    """Paginated flavor list response."""

    items: list[FlavorResponse]
    total: int
    skip: int
    limit: int
