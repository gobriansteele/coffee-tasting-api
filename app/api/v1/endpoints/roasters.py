from typing import List
from uuid import UUID

import supabase
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.api.deps.database import get_db
from app.repositories.roaster import roaster_repository
from app.schemas.roaster import RoasterCreate, RoasterResponse, RoasterListResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=RoasterResponse, status_code=201)
async def create_roaster(
    roaster_data: RoasterCreate,
    db: AsyncSession = Depends(get_db)
) -> RoasterResponse:
    """Create a new roaster."""
    try:
        # Check if roaster with same name already exists
        existing_roaster = await roaster_repository.get_by_name(db, roaster_data.name)
        if existing_roaster:
            raise HTTPException(
                status_code=400,
                detail=f"Roaster with name '{roaster_data.name}' already exists"
            )
        
        # Create the roaster
        roaster = await roaster_repository.create(db, obj_in=roaster_data)
        logger.info("Created roaster", roaster_id=str(roaster.id), name=roaster.name)
        
        return RoasterResponse.from_orm(roaster)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating roaster", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=RoasterListResponse)
async def list_roasters(
    skip: int = Query(0, ge=0, description="Number of roasters to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of roasters to return"),
    search: str = Query(None, description="Search roasters by name"),
    location: str = Query(None, description="Filter roasters by location"),
    db: AsyncSession = Depends(get_db)
) -> RoasterListResponse:
    """List roasters with optional filtering and pagination."""
    try:
        if search:
            roasters = await roaster_repository.search_by_name(db, search, skip=skip, limit=limit)
        elif location:
            roasters = await roaster_repository.get_by_location(db, location, skip=skip, limit=limit)
        else:
            roasters = await roaster_repository.get_multi(db, skip=skip, limit=limit)
        
        total = await roaster_repository.count(db)
        
        return RoasterListResponse(
            roasters=[RoasterResponse.from_orm(roaster) for roaster in roasters],
            total=total,
            page=skip // limit + 1,
            size=len(roasters)
        )
    
    except Exception as e:
        logger.error("Error listing roasters", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{roaster_id}", response_model=RoasterResponse)
async def get_roaster(
    roaster_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> RoasterResponse:
    """Get a specific roaster by ID."""

    try:
        roaster = await roaster_repository.get(db, roaster_id)
        if not roaster:
            raise HTTPException(status_code=404, detail="Roaster not found")
        
        return RoasterResponse.from_orm(roaster)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting roaster", roaster_id=str(roaster_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")