"""Recommendation schemas."""

from pydantic import BaseModel, Field

from .coffee import CoffeeResponse


class SimilarCoffeeResponse(CoffeeResponse):
    """Coffee response with similarity score."""

    shared_flavors: int = Field(..., description="Number of flavors shared with source coffee")


class SimilarCoffeesResponse(BaseModel):
    """Response for similar coffees query."""

    items: list[SimilarCoffeeResponse]
    source_coffee_id: str


class CoffeeByFlavorResponse(CoffeeResponse):
    """Coffee response with flavor match score."""

    matching_flavors: int = Field(..., description="Number of requested flavors this coffee has")


class CoffeesByFlavorResponse(BaseModel):
    """Response for coffees by flavor query."""

    items: list[CoffeeByFlavorResponse]
    flavor_ids: list[str]
    exclude_tasted: bool
