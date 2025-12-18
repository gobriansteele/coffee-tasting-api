"""Repository layer for data access."""

# Re-export SQL repositories for backward compatibility
from .sql import (
    BaseRepository,
    CoffeeRepository,
    FlavorTagRepository,
    RoasterRepository,
    TastingRepository,
    coffee_repository,
    flavor_tag_repository,
    roaster_repository,
    tasting_repository,
)

__all__ = [
    # SQL repositories
    "BaseRepository",
    "CoffeeRepository",
    "coffee_repository",
    "FlavorTagRepository",
    "flavor_tag_repository",
    "RoasterRepository",
    "roaster_repository",
    "TastingRepository",
    "tasting_repository",
]
