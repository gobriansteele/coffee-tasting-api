"""Coffee endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.coffee import coffee_repository
from app.repositories.roaster import roaster_repository
from app.schemas.coffee import (
    CoffeeCreate,
    CoffeeListResponse,
    CoffeeResponse,
    CoffeeUpdate,
)
from app.schemas.flavor import FlavorResponse
from app.schemas.roaster import RoasterSummary

logger = get_logger(__name__)
router = APIRouter()


def _build_coffee_response(coffee: dict) -> CoffeeResponse:
    """Build CoffeeResponse from repository dict."""
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

    return CoffeeResponse(
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
    )


@router.post("/", response_model=CoffeeResponse, status_code=201)
async def create_coffee(
    coffee_data: CoffeeCreate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeeResponse:
    """Create a new coffee linked to a roaster."""
    try:
        # Verify roaster exists and belongs to user
        roaster = await roaster_repository.get_by_id(session, user_id, str(coffee_data.roaster_id))
        if not roaster:
            raise HTTPException(
                status_code=404,
                detail=f"Roaster with ID '{coffee_data.roaster_id}' not found",
            )

        coffee = await coffee_repository.create(
            session,
            user_id=user_id,
            roaster_id=str(coffee_data.roaster_id),
            name=coffee_data.name,
            origin_country=coffee_data.origin_country,
            origin_region=coffee_data.origin_region,
            processing_method=coffee_data.processing_method.value if coffee_data.processing_method else None,
            variety=coffee_data.variety,
            roast_level=coffee_data.roast_level.value if coffee_data.roast_level else None,
            description=coffee_data.description,
            flavor_ids=[str(fid) for fid in coffee_data.flavor_ids] if coffee_data.flavor_ids else None,
        )

        if not coffee:
            raise HTTPException(status_code=500, detail="Failed to create coffee")

        logger.info("Created coffee", coffee_id=coffee["id"], name=coffee["name"])

        return _build_coffee_response(coffee)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating coffee", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/", response_model=CoffeeListResponse)
async def list_coffees(
    skip: int = Query(0, ge=0, description="Number of coffees to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of coffees to return"),
    roaster_id: UUID | None = Query(None, description="Filter by roaster ID"),
    search: str | None = Query(None, description="Search coffees by name"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeeListResponse:
    """List coffees for the current user with optional filters."""
    try:
        if search:
            coffees = await coffee_repository.search_by_name(
                session, user_id, query=search, skip=skip, limit=limit
            )
            total = len(coffees)  # Search doesn't have a separate count
        else:
            coffees = await coffee_repository.list_all(
                session,
                user_id,
                skip=skip,
                limit=limit,
                roaster_id=str(roaster_id) if roaster_id else None,
            )
            total = await coffee_repository.count(
                session, user_id, roaster_id=str(roaster_id) if roaster_id else None
            )

        return CoffeeListResponse(
            items=[_build_coffee_response(c) for c in coffees],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error("Error listing coffees", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{coffee_id}", response_model=CoffeeResponse)
async def get_coffee(
    coffee_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeeResponse:
    """Get a specific coffee with roaster and flavors."""
    try:
        coffee = await coffee_repository.get_by_id(session, user_id, str(coffee_id))

        if not coffee:
            raise HTTPException(status_code=404, detail="Coffee not found")

        return _build_coffee_response(coffee)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting coffee", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{coffee_id}", response_model=CoffeeResponse)
async def update_coffee(
    coffee_id: UUID,
    coffee_data: CoffeeUpdate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> CoffeeResponse:
    """Update a coffee."""
    try:
        # Check coffee exists
        existing = await coffee_repository.get_by_id(session, user_id, str(coffee_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Coffee not found")

        # If changing roaster, verify it exists
        if coffee_data.roaster_id:
            roaster = await roaster_repository.get_by_id(session, user_id, str(coffee_data.roaster_id))
            if not roaster:
                raise HTTPException(
                    status_code=404,
                    detail=f"Roaster with ID '{coffee_data.roaster_id}' not found",
                )

        coffee = await coffee_repository.update(
            session,
            user_id=user_id,
            coffee_id=str(coffee_id),
            name=coffee_data.name,
            origin_country=coffee_data.origin_country,
            origin_region=coffee_data.origin_region,
            processing_method=coffee_data.processing_method.value if coffee_data.processing_method else None,
            variety=coffee_data.variety,
            roast_level=coffee_data.roast_level.value if coffee_data.roast_level else None,
            description=coffee_data.description,
            flavor_ids=[str(fid) for fid in coffee_data.flavor_ids] if coffee_data.flavor_ids is not None else None,
        )

        if not coffee:
            raise HTTPException(status_code=500, detail="Failed to update coffee")

        logger.info("Updated coffee", coffee_id=str(coffee_id))

        return _build_coffee_response(coffee)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating coffee", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{coffee_id}", status_code=204)
async def delete_coffee(
    coffee_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> None:
    """Delete a coffee."""
    try:
        # Check coffee exists
        existing = await coffee_repository.get_by_id(session, user_id, str(coffee_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Coffee not found")

        deleted = await coffee_repository.delete(session, user_id, str(coffee_id))

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete coffee")

        logger.info("Deleted coffee", coffee_id=str(coffee_id), user_id=user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting coffee", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
