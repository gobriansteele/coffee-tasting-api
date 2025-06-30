from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.coffee import ProcessingMethod, RoastLevel
from .flavor_tag import FlavorTagResponse


class CoffeeBase(BaseModel):
    """Base coffee schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Coffee name")
    roaster_id: UUID = Field(..., description="ID of the roaster")

    # Origin info
    origin_country: str | None = Field(None, max_length=100, description="Country of origin")
    origin_region: str | None = Field(None, max_length=255, description="Region of origin")
    farm_name: str | None = Field(None, max_length=255, description="Farm name")
    producer: str | None = Field(None, max_length=255, description="Producer name")
    altitude: str | None = Field(None, max_length=100, description="Altitude range (e.g., '1200-1400m')")

    # Processing
    processing_method: ProcessingMethod | None = Field(None, description="Coffee processing method")
    variety: str | None = Field(None, max_length=255, description="Coffee variety/cultivar")

    # Roasting
    roast_level: RoastLevel | None = Field(None, description="Roast level")
    roast_date: str | None = Field(None, max_length=50, description="Roast date")

    # Additional info
    description: str | None = Field(None, description="Coffee description")
    price: Decimal | None = Field(None, ge=0, decimal_places=2, description="Price")
    bag_size: str | None = Field(None, max_length=50, description="Bag size (e.g., '12oz', '340g')")


class CoffeeCreate(CoffeeBase):
    """Schema for creating a new coffee."""
    flavor_tags: list[str] = Field(default_factory=list, description="List of flavor tag names")


class CoffeeUpdate(BaseModel):
    """Schema for updating an existing coffee."""
    name: str | None = Field(None, min_length=1, max_length=255, description="Coffee name")
    roaster_id: UUID | None = Field(None, description="ID of the roaster")

    # Origin info
    origin_country: str | None = Field(None, max_length=100, description="Country of origin")
    origin_region: str | None = Field(None, max_length=255, description="Region of origin")
    farm_name: str | None = Field(None, max_length=255, description="Farm name")
    producer: str | None = Field(None, max_length=255, description="Producer name")
    altitude: str | None = Field(None, max_length=100, description="Altitude range")

    # Processing
    processing_method: ProcessingMethod | None = Field(None, description="Coffee processing method")
    variety: str | None = Field(None, max_length=255, description="Coffee variety/cultivar")

    # Roasting
    roast_level: RoastLevel | None = Field(None, description="Roast level")
    roast_date: str | None = Field(None, max_length=50, description="Roast date")

    # Additional info
    description: str | None = Field(None, description="Coffee description")
    price: Decimal | None = Field(None, ge=0, decimal_places=2, description="Price")
    bag_size: str | None = Field(None, max_length=50, description="Bag size")


class CoffeeResponse(CoffeeBase):
    """Schema for coffee responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    flavor_tags: list[FlavorTagResponse] = Field(default_factory=list, description="Associated flavor tags")

    class Config:
        from_attributes = True


class CoffeeListResponse(BaseModel):
    """Schema for coffee list responses."""
    coffees: list[CoffeeResponse]
    total: int
    page: int
    size: int
