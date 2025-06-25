from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from ..models.coffee import ProcessingMethod, RoastLevel


class CoffeeBase(BaseModel):
    """Base coffee schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Coffee name")
    roaster_id: UUID = Field(..., description="ID of the roaster")
    
    # Origin info
    origin_country: Optional[str] = Field(None, max_length=100, description="Country of origin")
    origin_region: Optional[str] = Field(None, max_length=255, description="Region of origin")
    farm_name: Optional[str] = Field(None, max_length=255, description="Farm name")
    producer: Optional[str] = Field(None, max_length=255, description="Producer name")
    altitude: Optional[str] = Field(None, max_length=100, description="Altitude range (e.g., '1200-1400m')")
    
    # Processing
    processing_method: Optional[ProcessingMethod] = Field(None, description="Coffee processing method")
    variety: Optional[str] = Field(None, max_length=255, description="Coffee variety/cultivar")
    
    # Roasting
    roast_level: Optional[RoastLevel] = Field(None, description="Roast level")
    roast_date: Optional[str] = Field(None, max_length=50, description="Roast date")
    
    # Additional info
    description: Optional[str] = Field(None, description="Coffee description")
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Price")
    bag_size: Optional[str] = Field(None, max_length=50, description="Bag size (e.g., '12oz', '340g')")


class CoffeeCreate(CoffeeBase):
    """Schema for creating a new coffee."""
    pass


class CoffeeUpdate(BaseModel):
    """Schema for updating an existing coffee."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Coffee name")
    roaster_id: Optional[UUID] = Field(None, description="ID of the roaster")
    
    # Origin info
    origin_country: Optional[str] = Field(None, max_length=100, description="Country of origin")
    origin_region: Optional[str] = Field(None, max_length=255, description="Region of origin")
    farm_name: Optional[str] = Field(None, max_length=255, description="Farm name")
    producer: Optional[str] = Field(None, max_length=255, description="Producer name")
    altitude: Optional[str] = Field(None, max_length=100, description="Altitude range")
    
    # Processing
    processing_method: Optional[ProcessingMethod] = Field(None, description="Coffee processing method")
    variety: Optional[str] = Field(None, max_length=255, description="Coffee variety/cultivar")
    
    # Roasting
    roast_level: Optional[RoastLevel] = Field(None, description="Roast level")
    roast_date: Optional[str] = Field(None, max_length=50, description="Roast date")
    
    # Additional info
    description: Optional[str] = Field(None, description="Coffee description")
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Price")
    bag_size: Optional[str] = Field(None, max_length=50, description="Bag size")


class CoffeeResponse(CoffeeBase):
    """Schema for coffee responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoffeeListResponse(BaseModel):
    """Schema for coffee list responses."""
    coffees: List[CoffeeResponse]
    total: int
    page: int
    size: int