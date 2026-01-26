"""User/CoffeeDrinker schemas."""

from pydantic import BaseModel, Field

from .flavor import FlavorResponse


class UserProfile(BaseModel):
    """User profile response."""

    id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    email: str | None = Field(None, description="Email address")
    first_name: str | None = Field(None, max_length=100, description="First name")
    last_name: str | None = Field(None, max_length=100, description="Last name")
    display_name: str | None = Field(None, max_length=100, description="Display name")


class UserStats(BaseModel):
    """User statistics."""

    roaster_count: int
    coffee_count: int
    tasting_count: int


class FlavorProfileEntry(BaseModel):
    """A flavor in the user's profile with detection statistics."""

    flavor: FlavorResponse
    detection_count: int = Field(..., description="Number of times this flavor was detected")
    avg_intensity: float = Field(..., description="Average intensity when detected (1-10)")


class FlavorProfileResponse(BaseModel):
    """User's flavor profile based on tasting history."""

    items: list[FlavorProfileEntry]
    total: int
