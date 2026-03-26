"""Tasting and Rating schemas for Neo4j-only architecture."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .coffee import CoffeeResponse
from .enums import BrewMethod, GrindSize
from .flavor import FlavorResponse


# --- Detected Flavor Schemas ---


class DetectedFlavorCreate(BaseModel):
    """Schema for creating a detected flavor in a tasting."""

    flavor_id: UUID = Field(..., description="ID of the flavor detected")
    intensity: int = Field(..., ge=1, le=10, description="Intensity of the flavor (1-10)")


class DetectedFlavorResponse(BaseModel):
    """Schema for detected flavor responses."""

    flavor: FlavorResponse
    intensity: int = Field(..., ge=1, le=10, description="Intensity of the flavor (1-10)")


# --- Rating Schemas ---


class RatingCreate(BaseModel):
    """Schema for creating a rating."""

    score: int = Field(..., ge=1, le=5, description="Rating score (1-5)")
    notes: str | None = Field(None, description="Rating notes")


class RatingUpdate(BaseModel):
    """Schema for updating a rating."""

    score: int | None = Field(None, ge=1, le=5, description="Rating score (1-5)")
    notes: str | None = Field(None, description="Rating notes")


class RatingResponse(BaseModel):
    """Schema for rating responses."""

    id: UUID
    score: int = Field(..., ge=1, le=5, description="Rating score (1-5)")
    notes: str | None = None
    created_at: datetime


# --- Tasting Schemas ---


class TastingCreate(BaseModel):
    """Schema for creating a tasting."""

    coffee_id: UUID = Field(..., description="ID of the coffee being tasted")
    brew_method: BrewMethod | None = Field(None, description="Brewing method used")
    grind_size: GrindSize | None = Field(None, description="Grind size used")
    notes: str | None = Field(None, description="Tasting notes")
    roast_date: str | None = Field(None, description="Roast date as printed on the bag")
    best_by_date: str | None = Field(None, description="Best-by date as printed on the bag")
    lot_number: str | None = Field(None, description="Lot number from the bag")
    detected_flavors: list[DetectedFlavorCreate] | None = Field(
        None, description="Flavors detected during tasting"
    )
    rating: RatingCreate | None = Field(None, description="Optional rating for this tasting")


class TastingUpdate(BaseModel):
    """Schema for updating a tasting."""

    brew_method: BrewMethod | None = Field(None, description="Brewing method used")
    grind_size: GrindSize | None = Field(None, description="Grind size used")
    notes: str | None = Field(None, description="Tasting notes")
    roast_date: str | None = Field(None, description="Roast date as printed on the bag")
    best_by_date: str | None = Field(None, description="Best-by date as printed on the bag")
    lot_number: str | None = Field(None, description="Lot number from the bag")
    detected_flavors: list[DetectedFlavorCreate] | None = Field(
        None, description="Flavors detected (replaces existing)"
    )


class TastingResponse(BaseModel):
    """Schema for tasting responses."""

    id: UUID
    coffee_id: UUID
    brew_method: str | None = None
    grind_size: str | None = None
    notes: str | None = None
    roast_date: str | None = None
    best_by_date: str | None = None
    lot_number: str | None = None
    created_at: datetime
    coffee: CoffeeResponse | None = None
    detected_flavors: list[DetectedFlavorResponse] = Field(default_factory=list)
    rating: RatingResponse | None = None


class TastingListResponse(BaseModel):
    """Schema for tasting list responses."""

    items: list[TastingResponse]
    total: int
    skip: int
    limit: int
