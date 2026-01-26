"""Recommendation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.coffee import coffee_repository
from app.repositories.recommendation import recommendation_repository
from app.schemas.flavor import FlavorResponse
from app.schemas.recommendation import (
    CoffeeByFlavorResponse,
    CoffeesByFlavorResponse,
    SimilarCoffeeResponse,
    SimilarCoffeesResponse,
)
from app.schemas.roaster import RoasterSummary

logger = get_logger(__name__)
router = APIRouter()


def _build_similar_coffee_response(coffee: dict) -> SimilarCoffeeResponse:
    """Build SimilarCoffeeResponse from repository dict."""
    roaster = None
    if coffee.get("roaster"):
        roaster = RoasterSummary(
            id=UUID(coffee["roaster"]["id"]),
            name=coffee["roaster"]["name"],
            location=coffee["roaster"].get("location"),
        )

    flavors = [
        FlavorResponse(
            id=UUID(f["id"]),
            name=f["name"],
            category=f.get("category"),
        )
        for f in coffee.get("flavors", [])
    ]

    return SimilarCoffeeResponse(
        id=UUID(coffee["id"]),
        name=coffee["name"],
        roaster_id=UUID(coffee["roaster"]["id"]) if coffee.get("roaster") else UUID(coffee.get("roaster_id", "")),
        origin_country=coffee.get("origin_country"),
        origin_region=coffee.get("origin_region"),
        processing_method=coffee.get("processing_method"),
        variety=coffee.get("variety"),
        roast_level=coffee.get("roast_level"),
        description=coffee.get("description"),
        created_at=coffee["created_at"],
        flavors=flavors,
        roaster=roaster,
        shared_flavors=coffee.get("shared_flavors", 0),
    )


def _build_coffee_by_flavor_response(coffee: dict) -> CoffeeByFlavorResponse:
    """Build CoffeeByFlavorResponse from repository dict."""
    roaster = None
    if coffee.get("roaster"):
        roaster = RoasterSummary(
            id=UUID(coffee["roaster"]["id"]),
            name=coffee["roaster"]["name"],
            location=coffee["roaster"].get("location"),
        )

    flavors = [
        FlavorResponse(
            id=UUID(f["id"]),
            name=f["name"],
            category=f.get("category"),
        )
        for f in coffee.get("flavors", [])
    ]

    return CoffeeByFlavorResponse(
        id=UUID(coffee["id"]),
        name=coffee["name"],
        roaster_id=UUID(coffee["roaster"]["id"]) if coffee.get("roaster") else UUID(coffee.get("roaster_id", "")),
        origin_country=coffee.get("origin_country"),
        origin_region=coffee.get("origin_region"),
        processing_method=coffee.get("processing_method"),
        variety=coffee.get("variety"),
        roast_level=coffee.get("roast_level"),
        description=coffee.get("description"),
        created_at=coffee["created_at"],
        flavors=flavors,
        roaster=roaster,
        matching_flavors=coffee.get("matching_flavors", 0),
    )


@router.get("/similar/{coffee_id}", response_model=SimilarCoffeesResponse)
async def get_similar_coffees(
    coffee_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> SimilarCoffeesResponse:
    """Find coffees with similar flavor profiles.

    Returns coffees that share flavors with the specified coffee,
    ordered by number of shared flavors.
    """
    try:
        # Verify coffee exists and belongs to user
        coffee = await coffee_repository.get_by_id(session, user_id, str(coffee_id))
        if not coffee:
            raise HTTPException(
                status_code=404,
                detail=f"Coffee with ID '{coffee_id}' not found",
            )

        similar = await recommendation_repository.similar_coffees(
            session,
            user_id=user_id,
            coffee_id=str(coffee_id),
            limit=limit,
        )

        return SimilarCoffeesResponse(
            items=[_build_similar_coffee_response(c) for c in similar],
            source_coffee_id=str(coffee_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error finding similar coffees", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/by-flavor", response_model=CoffeesByFlavorResponse)
async def get_coffees_by_flavor(
    flavor_ids: str = Query(..., description="Comma-separated list of flavor IDs"),
    exclude_tasted: bool = Query(False, description="Exclude coffees already tasted"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeesByFlavorResponse:
    """Find coffees matching specific flavors.

    Returns coffees that have the specified flavors,
    ordered by number of matching flavors.
    """
    try:
        # Parse flavor IDs
        flavor_id_list = [fid.strip() for fid in flavor_ids.split(",") if fid.strip()]

        if not flavor_id_list:
            raise HTTPException(status_code=400, detail="At least one flavor ID is required")

        # Validate UUIDs
        try:
            for fid in flavor_id_list:
                UUID(fid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid flavor ID format: {e}") from e

        coffees = await recommendation_repository.coffees_by_flavor(
            session,
            user_id=user_id,
            flavor_ids=flavor_id_list,
            exclude_tasted=exclude_tasted,
            limit=limit,
        )

        return CoffeesByFlavorResponse(
            items=[_build_coffee_by_flavor_response(c) for c in coffees],
            flavor_ids=flavor_id_list,
            exclude_tasted=exclude_tasted,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error finding coffees by flavor", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
