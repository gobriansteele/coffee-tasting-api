"""User profile endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.user import user_repository
from app.schemas.flavor import FlavorResponse
from app.schemas.user import (
    FlavorProfileEntry,
    FlavorProfileResponse,
    UserProfile,
    UserProfileUpdate,
    UserStats,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=UserProfile)
async def get_current_user_profile(
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> UserProfile:
    """Get the current user's profile."""
    try:
        profile = await user_repository.get_profile(session, user_id)

        if not profile:
            # User should exist via ensure_user_exists, but just in case
            return UserProfile(id=user_id)

        return UserProfile(
            id=profile["id"],
            email=profile.get("email"),
            first_name=profile.get("first_name"),
            last_name=profile.get("last_name"),
            display_name=profile.get("display_name"),
        )

    except Exception as e:
        logger.error("Error getting user profile", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/", response_model=UserProfile)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> UserProfile:
    """Update the current user's profile."""
    try:
        profile = await user_repository.update_profile(
            session,
            user_id=user_id,
            email=profile_data.email,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            display_name=profile_data.display_name,
        )

        if not profile:
            raise HTTPException(status_code=500, detail="Failed to update profile")

        logger.info("Updated user profile", user_id=user_id)

        return UserProfile(
            id=profile["id"],
            email=profile.get("email"),
            first_name=profile.get("first_name"),
            last_name=profile.get("last_name"),
            display_name=profile.get("display_name"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user profile", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/stats", response_model=UserStats)
async def get_current_user_stats(
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> UserStats:
    """Get statistics for the current user."""
    try:
        stats = await user_repository.get_stats(session, user_id)

        return UserStats(
            roaster_count=stats["roaster_count"],
            coffee_count=stats["coffee_count"],
            tasting_count=stats["tasting_count"],
        )

    except Exception as e:
        logger.error("Error getting user stats", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/flavor-profile", response_model=FlavorProfileResponse)
async def get_flavor_profile(
    limit: int = Query(20, ge=1, le=100, description="Max flavors to return"),
    session: AsyncSession = Depends(get_graph_db),
    user_id: str = Depends(ensure_user_exists),
) -> FlavorProfileResponse:
    """Get the current user's flavor profile.

    Returns the flavors most frequently detected by this user across all tastings,
    along with average intensity for each flavor.
    """
    try:
        flavors = await user_repository.get_flavor_profile(session, user_id, limit=limit)

        items = [
            FlavorProfileEntry(
                flavor=FlavorResponse(
                    id=UUID(f["id"]),
                    name=f["name"],
                    category=f.get("category"),
                ),
                detection_count=f["detection_count"],
                avg_intensity=f["avg_intensity"],
            )
            for f in flavors
        ]

        return FlavorProfileResponse(items=items, total=len(items))

    except Exception as e:
        logger.error("Error getting flavor profile", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
