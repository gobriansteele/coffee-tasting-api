from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user_id, require_user_access
from app.api.deps.database import get_db
from app.core.logging import get_logger
from app.repositories.coffee import coffee_repository
from app.repositories.tasting import tasting_repository
from app.schemas.tasting import (
    TastingSessionCreate,
    TastingSessionListResponse,
    TastingSessionResponse,
    TastingSessionUpdate,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=TastingSessionListResponse)
async def list_tasting_sessions(
    skip: int = Query(0, ge=0, description="Number of tastings to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tastings to return"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> TastingSessionListResponse:
    """List all tasting sessions for the authenticated user."""
    try:
        tastings = await tasting_repository.get_by_user_id(
            db,
            current_user_id,
            skip=skip,
            limit=limit
        )
        total = await tasting_repository.count_by_user(db, current_user_id)

        return TastingSessionListResponse(
            tastings=[TastingSessionResponse.model_validate(tasting) for tasting in tastings],
            total=total,
            page=skip // limit + 1,
            size=len(tastings)
        )

    except Exception as e:
        logger.error(
            "Error listing tasting sessions",
            user_id=current_user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/", response_model=TastingSessionResponse, status_code=201)
async def create_tasting_session(
    tasting_data: TastingSessionCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> TastingSessionResponse:
    """Create a new tasting session for the authenticated user."""
    try:
        # Verify coffee exists
        coffee = await coffee_repository.get(db, tasting_data.coffee_id)
        if not coffee:
            raise HTTPException(
                status_code=404,
                detail=f"Coffee with ID '{tasting_data.coffee_id}' not found"
            )

        # Create the tasting session with notes
        tasting = await tasting_repository.create_with_notes(
            db,
            tasting_data=tasting_data,
            user_id=current_user_id
        )

        logger.info(
            "Created tasting session",
            tasting_id=str(tasting.id),
            user_id=current_user_id,
            coffee_id=str(tasting.coffee_id)
        )

        return TastingSessionResponse.model_validate(tasting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating tasting session",
            user_id=current_user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{session_id}", response_model=TastingSessionResponse)
async def get_tasting_session(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> TastingSessionResponse:
    """Get a specific tasting session if it belongs to the authenticated user."""
    try:
        tasting = await tasting_repository.get_with_notes(db, session_id)

        if not tasting:
            raise HTTPException(status_code=404, detail="Tasting session not found")

        # Check if user owns this session
        if tasting.user_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this tasting session"
            )

        return TastingSessionResponse.model_validate(tasting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting tasting session",
            session_id=str(session_id),
            user_id=current_user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put("/{session_id}", response_model=TastingSessionResponse)
async def update_tasting_session(
    session_id: UUID,
    update_data: TastingSessionUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> TastingSessionResponse:
    """Update a tasting session if it belongs to the authenticated user."""
    try:
        # Get existing session
        tasting = await tasting_repository.get(db, session_id)

        if not tasting:
            raise HTTPException(status_code=404, detail="Tasting session not found")

        # Check if user owns this session
        if tasting.user_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this tasting session"
            )

        # If coffee_id is being updated, verify it exists
        if update_data.coffee_id:
            coffee = await coffee_repository.get(db, update_data.coffee_id)
            if not coffee:
                raise HTTPException(
                    status_code=404,
                    detail=f"Coffee with ID '{update_data.coffee_id}' not found"
                )

        # Update the tasting
        await tasting_repository.update(
            db,
            db_obj=tasting,
            obj_in=update_data
        )

        # Get with notes for response
        tasting_with_notes = await tasting_repository.get_with_notes(db, session_id)

        logger.info(
            "Updated tasting session",
            tasting_id=str(session_id),
            user_id=current_user_id
        )

        return TastingSessionResponse.model_validate(tasting_with_notes)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating tasting session",
            session_id=str(session_id),
            user_id=current_user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{session_id}", status_code=204)
async def delete_tasting_session(
    session_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a tasting session."""
    try:
        # Check if tasting session exists and is not already deleted
        tasting = await tasting_repository.get(db, session_id)
        if not tasting:
            raise HTTPException(status_code=404, detail="Tasting session not found")

        # Verify the user owns this tasting session (created by them)
        require_user_access(tasting.created_by, current_user_id)

        # Perform soft delete
        await tasting_repository.delete(db, id=session_id, current_user_id=current_user_id)

        logger.info("Deleted tasting session", session_id=str(session_id), user_id=current_user_id)

    except HTTPException:
        raise
    except ValueError as e:
        # This handles the case where the tasting session was not found in the delete method
        logger.error("Tasting session not found for deletion", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=404, detail="Tasting session not found") from e
    except Exception as e:
        logger.error("Error deleting tasting session", session_id=str(session_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
