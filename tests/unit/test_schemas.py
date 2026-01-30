"""Unit tests for schema business logic.

Note: We don't test Pydantic validation (min_length, ge/le constraints, enum validation)
as that's testing library functionality, not our business logic.
"""

from uuid import uuid4

from app.schemas.tasting import (
    DetectedFlavorCreate,
    RatingCreate,
    TastingCreate,
)
from app.schemas.enums import BrewMethod, GrindSize


class TestTastingSchemaComposition:
    """Tests for tasting schema composition - our business logic for how tastings are structured."""

    def test_tasting_with_nested_rating(self) -> None:
        """Test that a tasting can include an inline rating."""
        tasting = TastingCreate(
            coffee_id=uuid4(),
            rating=RatingCreate(score=4, notes="Good coffee"),
        )
        assert tasting.rating is not None
        assert tasting.rating.score == 4

    def test_tasting_with_detected_flavors(self) -> None:
        """Test that a tasting can include multiple detected flavors."""
        flavor_ids = [uuid4(), uuid4(), uuid4()]
        tasting = TastingCreate(
            coffee_id=uuid4(),
            detected_flavors=[
                DetectedFlavorCreate(flavor_id=fid, intensity=5)
                for fid in flavor_ids
            ],
        )
        assert tasting.detected_flavors is not None
        assert len(tasting.detected_flavors) == 3

    def test_tasting_complete_flow(self) -> None:
        """Test creating a complete tasting with all optional fields.

        This represents the full business flow: user tastes a coffee,
        records brew parameters, detects flavors, and rates it.
        """
        coffee_id = uuid4()
        flavor_id = uuid4()

        tasting = TastingCreate(
            coffee_id=coffee_id,
            brew_method=BrewMethod.POUROVER,
            grind_size=GrindSize.MEDIUM,
            notes="Bright acidity with berry notes",
            detected_flavors=[
                DetectedFlavorCreate(flavor_id=flavor_id, intensity=8)
            ],
            rating=RatingCreate(score=5, notes="One of my favorites"),
        )

        # Verify the complete structure
        assert tasting.coffee_id == coffee_id
        assert tasting.brew_method == BrewMethod.POUROVER
        assert tasting.grind_size == GrindSize.MEDIUM
        assert tasting.notes is not None
        assert tasting.detected_flavors is not None
        assert len(tasting.detected_flavors) == 1
        assert tasting.detected_flavors[0].intensity == 8
        assert tasting.rating is not None
        assert tasting.rating.score == 5
