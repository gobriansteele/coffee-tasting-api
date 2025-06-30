from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.tasting import BrewMethod, GrindSize
from .flavor_tag import FlavorTagResponse


class TastingNoteBase(BaseModel):
    """Base tasting note schema."""
    intensity: int | None = Field(None, ge=1, le=10, description="Intensity (1-10)")
    notes: str | None = Field(None, description="Additional notes about this flavor")
    aroma: bool = Field(False, description="Detected in aroma")
    flavor: bool = Field(False, description="Detected in flavor")
    aftertaste: bool = Field(False, description="Detected in aftertaste")


class TastingNoteCreate(TastingNoteBase):
    """Schema for creating a tasting note."""
    flavor_name: str = Field(..., min_length=1, description="Name of the flavor detected")


class TastingNoteResponse(TastingNoteBase):
    """Schema for tasting note responses."""
    id: UUID
    tasting_session_id: UUID
    flavor_tag: FlavorTagResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TastingSessionBase(BaseModel):
    """Base tasting session schema."""
    coffee_id: UUID = Field(..., description="ID of the coffee")

    # Brewing parameters
    brew_method: BrewMethod = Field(..., description="Brewing method used")
    grind_size: GrindSize | None = Field(None, description="Grind size")

    # Measurements
    coffee_dose: Decimal | None = Field(None, ge=0, decimal_places=1, description="Coffee dose (grams)")
    water_amount: Decimal | None = Field(None, ge=0, decimal_places=1, description="Water amount (grams/ml)")
    water_temperature: int | None = Field(None, ge=0, le=100, description="Water temperature (celsius)")
    brew_time: str | None = Field(None, max_length=20, description="Brew time (e.g., '4:30')")

    # Equipment
    grinder: str | None = Field(None, max_length=255, description="Grinder used")
    brewing_device: str | None = Field(None, max_length=255, description="Brewing device")
    filter_type: str | None = Field(None, max_length=100, description="Filter type")

    # Session notes
    session_notes: str | None = Field(None, description="Session notes")
    overall_rating: int | None = Field(None, ge=1, le=10, description="Overall rating (1-10)")
    would_buy_again: bool | None = Field(None, description="Would buy again")


class TastingSessionCreate(TastingSessionBase):
    """Schema for creating a tasting session."""
    tasting_notes: list[TastingNoteCreate] | None = Field(default_factory=list, description="Tasting notes")


class TastingSessionUpdate(BaseModel):
    """Schema for updating a tasting session."""
    coffee_id: UUID | None = Field(None, description="ID of the coffee")

    # Brewing parameters
    brew_method: BrewMethod | None = Field(None, description="Brewing method used")
    grind_size: GrindSize | None = Field(None, description="Grind size")

    # Measurements
    coffee_dose: Decimal | None = Field(None, ge=0, decimal_places=1, description="Coffee dose (grams)")
    water_amount: Decimal | None = Field(None, ge=0, decimal_places=1, description="Water amount (grams/ml)")
    water_temperature: int | None = Field(None, ge=0, le=100, description="Water temperature (celsius)")
    brew_time: str | None = Field(None, max_length=20, description="Brew time")

    # Equipment
    grinder: str | None = Field(None, max_length=255, description="Grinder used")
    brewing_device: str | None = Field(None, max_length=255, description="Brewing device")
    filter_type: str | None = Field(None, max_length=100, description="Filter type")

    # Session notes
    session_notes: str | None = Field(None, description="Session notes")
    overall_rating: int | None = Field(None, ge=1, le=10, description="Overall rating (1-10)")
    would_buy_again: bool | None = Field(None, description="Would buy again")


class TastingSessionResponse(TastingSessionBase):
    """Schema for tasting session responses."""
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: datetime
    tasting_notes: list[TastingNoteResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TastingSessionListResponse(BaseModel):
    """Schema for tasting session list responses."""
    tastings: list[TastingSessionResponse]
    total: int
    page: int
    size: int
