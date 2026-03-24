"""Schemas for photo-based coffee identification."""

from pydantic import BaseModel

from .enums import ProcessingMethod, RoastLevel


class IdentifiedFlavor(BaseModel):
    """A flavor note extracted from a coffee bag/label photo."""

    name: str
    category: str | None = None


class IdentifiedRoaster(BaseModel):
    """Roaster information extracted from a coffee bag/label photo."""

    name: str
    location: str | None = None


class CoffeeIdentificationResponse(BaseModel):
    """Structured coffee data extracted from a photo via Claude Vision."""

    # Coffee-level fields
    coffee_name: str | None = None
    roaster: IdentifiedRoaster | None = None
    origin_country: str | None = None
    origin_region: str | None = None
    processing_method: ProcessingMethod | None = None
    variety: str | None = None
    roast_level: RoastLevel | None = None
    description: str | None = None
    flavor_notes: list[IdentifiedFlavor] = []
    altitude: str | None = None
    producer: str | None = None

    # Tasting-level fields (roast date, lot, best-by belong on Tasting, not Coffee)
    roast_date: str | None = None
    best_by_date: str | None = None
    lot_number: str | None = None

    # Debug/transparency
    raw_text: str | None = None
