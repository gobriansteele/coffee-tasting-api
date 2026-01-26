"""Coffee schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import ProcessingMethod, RoastLevel
from .flavor import FlavorResponse
from .roaster import RoasterSummary


class CoffeeBase(BaseModel):
    """Base coffee schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Coffee name")
    roaster_id: UUID = Field(..., description="ID of the roaster")

    # Origin info
    origin_country: str | None = Field(None, max_length=100, description="Country of origin")
    origin_region: str | None = Field(None, max_length=255, description="Region of origin")

    # Processing
    processing_method: ProcessingMethod | None = Field(None, description="Coffee processing method")
    variety: str | None = Field(None, max_length=255, description="Coffee variety (bourbon, gesha, typica, etc.)")

    # Roasting
    roast_level: RoastLevel | None = Field(None, description="Roast level")

    # Additional info
    description: str | None = Field(None, description="Coffee description (for semantic search)")


class CoffeeCreate(CoffeeBase):
    """Schema for creating a new coffee."""

    flavor_ids: list[UUID] = Field(default_factory=list, description="List of expected flavor IDs (HAS_FLAVOR)")


class CoffeeUpdate(BaseModel):
    """Schema for updating an existing coffee."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Coffee name")
    roaster_id: UUID | None = Field(None, description="ID of the roaster")

    # Origin info
    origin_country: str | None = Field(None, max_length=100, description="Country of origin")
    origin_region: str | None = Field(None, max_length=255, description="Region of origin")

    # Processing
    processing_method: ProcessingMethod | None = Field(None, description="Coffee processing method")
    variety: str | None = Field(None, max_length=255, description="Coffee variety")

    # Roasting
    roast_level: RoastLevel | None = Field(None, description="Roast level")

    # Additional info
    description: str | None = Field(None, description="Coffee description")

    # Flavor relationships
    flavor_ids: list[UUID] | None = Field(None, description="Replace expected flavors (HAS_FLAVOR)")


class CoffeeResponse(BaseModel):
    """Schema for coffee responses."""

    id: UUID
    name: str
    roaster_id: UUID
    origin_country: str | None = None
    origin_region: str | None = None
    processing_method: ProcessingMethod | None = None
    variety: str | None = None
    roast_level: RoastLevel | None = None
    description: str | None = None
    created_at: datetime
    flavors: list[FlavorResponse] = Field(default_factory=list, description="Expected flavors")
    roaster: RoasterSummary | None = Field(None, description="Roaster information")

    class Config:
        from_attributes = True


class CoffeeListResponse(BaseModel):
    """Paginated coffee list response."""

    items: list[CoffeeResponse]
    total: int
    skip: int
    limit: int
