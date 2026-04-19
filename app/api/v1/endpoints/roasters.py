"""Roaster endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.roaster import roaster_repository
from app.schemas.roaster import (
    RoasterCreate,
    RoasterListResponse,
    RoasterResponse,
    RoasterUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=RoasterResponse, status_code=201)
async def create_roaster(
    roaster_data: RoasterCreate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RoasterResponse:
    """Create a new roaster."""
    try:
        # Check if roaster with same name already exists for this user
        existing = await roaster_repository.get_by_name(session, user_id, roaster_data.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Roaster with name '{roaster_data.name}' already exists",
            )

        roaster = await roaster_repository.create(
            session,
            user_id=user_id,
            name=roaster_data.name,
            location=roaster_data.location,
            website=roaster_data.website,
            description=roaster_data.description,
        )

        if not roaster:
            raise HTTPException(status_code=500, detail="Failed to create roaster")

        logger.info("Created roaster", roaster_id=roaster["id"], name=roaster["name"])

        return RoasterResponse(
            id=UUID(roaster["id"]),
            name=roaster["name"],
            location=roaster.get("location"),
            website=roaster.get("website"),
            description=roaster.get("description"),
            created_at=roaster["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating roaster", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("", response_model=RoasterListResponse)
async def list_roasters(
    skip: int = Query(0, ge=0, description="Number of roasters to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of roasters to return"),
    search: str | None = Query(None, description="Search roasters by name"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RoasterListResponse:
    """List roasters for the current user with optional search."""
    try:
        if search:
            roasters = await roaster_repository.search_by_name(
                session, user_id, query=search, skip=skip, limit=limit
            )
        else:
            roasters = await roaster_repository.list_all(
                session, user_id, skip=skip, limit=limit
            )

        total = await roaster_repository.count(session, user_id)

        return RoasterListResponse(
            items=[
                RoasterResponse(
                    id=UUID(r["id"]),
                    name=r["name"],
                    location=r.get("location"),
                    website=r.get("website"),
                    description=r.get("description"),
                    created_at=r["created_at"],
                )
                for r in roasters
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error("Error listing roasters", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{roaster_id}", response_model=RoasterResponse)
async def get_roaster(
    roaster_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RoasterResponse:
    """Get a specific roaster owned by the current user."""
    try:
        roaster = await roaster_repository.get_by_id(session, user_id, str(roaster_id))

        if not roaster:
            raise HTTPException(status_code=404, detail="Roaster not found")

        return RoasterResponse(
            id=UUID(roaster["id"]),
            name=roaster["name"],
            location=roaster.get("location"),
            website=roaster.get("website"),
            description=roaster.get("description"),
            created_at=roaster["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting roaster", roaster_id=str(roaster_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{roaster_id}", response_model=RoasterResponse)
async def update_roaster(
    roaster_id: UUID,
    roaster_data: RoasterUpdate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> RoasterResponse:
    """Update a roaster."""
    try:
        # Check roaster exists
        existing = await roaster_repository.get_by_id(session, user_id, str(roaster_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Roaster not found")

        # If name is being changed, check for duplicates
        if roaster_data.name and roaster_data.name != existing["name"]:
            duplicate = await roaster_repository.get_by_name(session, user_id, roaster_data.name)
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Roaster with name '{roaster_data.name}' already exists",
                )

        roaster = await roaster_repository.update(
            session,
            user_id=user_id,
            roaster_id=str(roaster_id),
            name=roaster_data.name,
            location=roaster_data.location,
            website=roaster_data.website,
            description=roaster_data.description,
        )

        if not roaster:
            raise HTTPException(status_code=500, detail="Failed to update roaster")

        logger.info("Updated roaster", roaster_id=str(roaster_id))

        return RoasterResponse(
            id=UUID(roaster["id"]),
            name=roaster["name"],
            location=roaster.get("location"),
            website=roaster.get("website"),
            description=roaster.get("description"),
            created_at=roaster["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating roaster", roaster_id=str(roaster_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{roaster_id}", status_code=204)
async def delete_roaster(
    roaster_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> None:
    """Delete a roaster."""
    try:
        # Check roaster exists
        existing = await roaster_repository.get_by_id(session, user_id, str(roaster_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Roaster not found")

        deleted = await roaster_repository.delete(session, user_id, str(roaster_id))

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete roaster")

        logger.info("Deleted roaster", roaster_id=str(roaster_id), user_id=user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting roaster", roaster_id=str(roaster_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
