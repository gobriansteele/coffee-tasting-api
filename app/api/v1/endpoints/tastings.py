"""Tasting endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.coffee import coffee_repository
from app.repositories.tasting import tasting_repository
from app.schemas.flavor import FlavorResponse
from app.schemas.roaster import RoasterSummary
from app.schemas.tasting import (
    DetectedFlavorResponse,
    RatingCreate,
    RatingResponse,
    RatingUpdate,
    TastingCreate,
    TastingListResponse,
    TastingResponse,
    TastingUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


def _build_tasting_response(tasting: dict) -> TastingResponse:
    """Build TastingResponse from repository dict."""
    # Build coffee response (simplified for list view)
    coffee = None
    if tasting.get("coffee"):
        c = tasting["coffee"]
        roaster = None
        if c.get("roaster"):
            roaster = RoasterSummary(
                id=UUID(c["roaster"]["id"]),
                name=c["roaster"]["name"],
                location=c["roaster"].get("location"),
            )

        from app.schemas.coffee import CoffeeResponse

        coffee = CoffeeResponse(
            id=UUID(c["id"]),
            name=c["name"],
            roaster_id=UUID(c["roaster"]["id"]) if c.get("roaster") else UUID(c.get("roaster_id", "")),
            origin_country=c.get("origin_country"),
            origin_region=c.get("origin_region"),
            processing_method=c.get("processing_method"),
            variety=c.get("variety"),
            roast_level=c.get("roast_level"),
            description=c.get("description"),
            created_at=c.get("created_at") or tasting["created_at"],
            flavors=[
                FlavorResponse(id=UUID(f["id"]), name=f["name"], category=f.get("category"))
                for f in c.get("flavors", [])
            ],
            roaster=roaster,
        )

    # Build detected flavors
    detected_flavors = [
        DetectedFlavorResponse(
            flavor=FlavorResponse(
                id=UUID(df["flavor"]["id"]),
                name=df["flavor"]["name"],
                category=df["flavor"].get("category"),
            ),
            intensity=df["intensity"],
        )
        for df in tasting.get("detected_flavors", [])
    ]

    # Build rating
    rating = None
    if tasting.get("rating"):
        r = tasting["rating"]
        rating = RatingResponse(
            id=UUID(r["id"]),
            score=r["score"],
            notes=r.get("notes"),
            created_at=r["created_at"],
        )

    return TastingResponse(
        id=UUID(tasting["id"]),
        coffee_id=UUID(tasting["coffee"]["id"]) if tasting.get("coffee") else UUID(tasting.get("coffee_id", "")),
        brew_method=tasting.get("brew_method"),
        grind_size=tasting.get("grind_size"),
        notes=tasting.get("notes"),
        created_at=tasting["created_at"],
        coffee=coffee,
        detected_flavors=detected_flavors,
        rating=rating,
    )


@router.post("/", response_model=TastingResponse, status_code=201)
async def create_tasting(
    tasting_data: TastingCreate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> TastingResponse:
    """Create a new tasting for a coffee."""
    try:
        # Verify coffee exists and belongs to user
        coffee = await coffee_repository.get_by_id(session, user_id, str(tasting_data.coffee_id))
        if not coffee:
            raise HTTPException(
                status_code=404,
                detail=f"Coffee with ID '{tasting_data.coffee_id}' not found",
            )

        tasting = await tasting_repository.create(
            session,
            user_id=user_id,
            coffee_id=str(tasting_data.coffee_id),
            brew_method=tasting_data.brew_method.value if tasting_data.brew_method else None,
            grind_size=tasting_data.grind_size.value if tasting_data.grind_size else None,
            notes=tasting_data.notes,
            detected_flavors=[
                {"flavor_id": str(df.flavor_id), "intensity": df.intensity}
                for df in tasting_data.detected_flavors
            ] if tasting_data.detected_flavors else None,
            rating={
                "score": tasting_data.rating.score,
                "notes": tasting_data.rating.notes,
            } if tasting_data.rating else None,
        )

        if not tasting:
            raise HTTPException(status_code=500, detail="Failed to create tasting")

        logger.info("Created tasting", tasting_id=tasting["id"])

        return _build_tasting_response(tasting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating tasting", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/", response_model=TastingListResponse)
async def list_tastings(
    skip: int = Query(0, ge=0, description="Number of tastings to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of tastings to return"),
    coffee_id: UUID | None = Query(None, description="Filter by coffee ID"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> TastingListResponse:
    """List tastings for the current user."""
    try:
        tastings = await tasting_repository.list_all(
            session,
            user_id,
            skip=skip,
            limit=limit,
            coffee_id=str(coffee_id) if coffee_id else None,
        )
        total = await tasting_repository.count(
            session, user_id, coffee_id=str(coffee_id) if coffee_id else None
        )

        return TastingListResponse(
            items=[_build_tasting_response(t) for t in tastings],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error("Error listing tastings", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{tasting_id}", response_model=TastingResponse)
async def get_tasting(
    tasting_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> TastingResponse:
    """Get a specific tasting with all details."""
    try:
        tasting = await tasting_repository.get_by_id(session, user_id, str(tasting_id))

        if not tasting:
            raise HTTPException(status_code=404, detail="Tasting not found")

        return _build_tasting_response(tasting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting tasting", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{tasting_id}", response_model=TastingResponse)
async def update_tasting(
    tasting_id: UUID,
    tasting_data: TastingUpdate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> TastingResponse:
    """Update a tasting."""
    try:
        existing = await tasting_repository.get_by_id(session, user_id, str(tasting_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Tasting not found")

        tasting = await tasting_repository.update(
            session,
            user_id=user_id,
            tasting_id=str(tasting_id),
            brew_method=tasting_data.brew_method.value if tasting_data.brew_method else None,
            grind_size=tasting_data.grind_size.value if tasting_data.grind_size else None,
            notes=tasting_data.notes,
            detected_flavors=[
                {"flavor_id": str(df.flavor_id), "intensity": df.intensity}
                for df in tasting_data.detected_flavors
            ] if tasting_data.detected_flavors is not None else None,
        )

        if not tasting:
            raise HTTPException(status_code=500, detail="Failed to update tasting")

        logger.info("Updated tasting", tasting_id=str(tasting_id))

        return _build_tasting_response(tasting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating tasting", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{tasting_id}", status_code=204)
async def delete_tasting(
    tasting_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> None:
    """Delete a tasting and its rating."""
    try:
        existing = await tasting_repository.get_by_id(session, user_id, str(tasting_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Tasting not found")

        deleted = await tasting_repository.delete(session, user_id, str(tasting_id))

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete tasting")

        logger.info("Deleted tasting", tasting_id=str(tasting_id), user_id=user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting tasting", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# --- Rating Endpoints ---


@router.post("/{tasting_id}/rating", response_model=RatingResponse, status_code=201)
async def create_rating(
    tasting_id: UUID,
    rating_data: RatingCreate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RatingResponse:
    """Create a rating for a tasting."""
    try:
        existing = await tasting_repository.get_by_id(session, user_id, str(tasting_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Tasting not found")

        if existing.get("rating"):
            raise HTTPException(status_code=400, detail="Rating already exists for this tasting")

        rating = await tasting_repository.create_rating(
            session,
            user_id=user_id,
            tasting_id=str(tasting_id),
            score=rating_data.score,
            notes=rating_data.notes,
        )

        if not rating:
            raise HTTPException(status_code=500, detail="Failed to create rating")

        logger.info("Created rating", tasting_id=str(tasting_id))

        return RatingResponse(
            id=UUID(rating["id"]),
            score=rating["score"],
            notes=rating.get("notes"),
            created_at=rating["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating rating", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{tasting_id}/rating", response_model=RatingResponse)
async def get_rating(
    tasting_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RatingResponse:
    """Get the rating for a tasting."""
    try:
        rating = await tasting_repository.get_rating(session, user_id, str(tasting_id))

        if not rating:
            raise HTTPException(status_code=404, detail="Rating not found")

        return RatingResponse(
            id=UUID(rating["id"]),
            score=rating["score"],
            notes=rating.get("notes"),
            created_at=rating["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting rating", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{tasting_id}/rating", response_model=RatingResponse)
async def update_rating(
    tasting_id: UUID,
    rating_data: RatingUpdate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RatingResponse:
    """Update the rating for a tasting."""
    try:
        existing = await tasting_repository.get_rating(session, user_id, str(tasting_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Rating not found")

        rating = await tasting_repository.update_rating(
            session,
            user_id=user_id,
            tasting_id=str(tasting_id),
            score=rating_data.score,
            notes=rating_data.notes,
        )

        if not rating:
            raise HTTPException(status_code=500, detail="Failed to update rating")

        logger.info("Updated rating", tasting_id=str(tasting_id))

        return RatingResponse(
            id=UUID(rating["id"]),
            score=rating["score"],
            notes=rating.get("notes"),
            created_at=rating["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating rating", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{tasting_id}/rating", status_code=204)
async def delete_rating(
    tasting_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> None:
    """Delete the rating for a tasting."""
    try:
        existing = await tasting_repository.get_rating(session, user_id, str(tasting_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Rating not found")

        deleted = await tasting_repository.delete_rating(session, user_id, str(tasting_id))

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete rating")

        logger.info("Deleted rating", tasting_id=str(tasting_id), user_id=user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting rating", tasting_id=str(tasting_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
