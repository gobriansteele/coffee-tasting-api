from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.database import get_db
from app.repositories.coffee import coffee_repository
from app.repositories.roaster import roaster_repository
from app.schemas.coffee import CoffeeCreate, CoffeeResponse, CoffeeListResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=CoffeeResponse, status_code=201)
async def create_coffee(
    coffee_data: CoffeeCreate,
    db: AsyncSession = Depends(get_db)
) -> CoffeeResponse:
    """Create a new coffee."""
    try:
        # Verify roaster exists
        roaster = await roaster_repository.get(db, coffee_data.roaster_id)
        if not roaster:
            raise HTTPException(
                status_code=404,
                detail=f"Roaster with ID '{coffee_data.roaster_id}' not found"
            )
        
        # Check if coffee with same name already exists for this roaster
        existing_coffee = await coffee_repository.get_by_name_and_roaster(
            db, 
            coffee_data.name, 
            coffee_data.roaster_id
        )
        if existing_coffee:
            raise HTTPException(
                status_code=400,
                detail=f"Coffee '{coffee_data.name}' already exists for roaster '{roaster.name}'"
            )
        
        # Create the coffee
        coffee = await coffee_repository.create(db, obj_in=coffee_data)
        logger.info(
            "Created coffee", 
            coffee_id=str(coffee.id), 
            name=coffee.name,
            roaster_id=str(coffee.roaster_id)
        )
        
        return CoffeeResponse.model_validate(coffee)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating coffee", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/")
async def list_coffees(
    roaster_id: UUID = Query(None, description="Filter coffees by roaster ID"),
    skip: int = Query(0, ge=0, description="Number of coffees to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of coffees to return"),
    search: str = Query(None, description="Search coffees by name"),
    db: AsyncSession = Depends(get_db)
) -> CoffeeListResponse:
    """List all coffees."""

    try:
        if roaster_id:
            # Filter by roaster ID
            roaster = await roaster_repository.get(db, roaster_id)
            if not roaster:
                raise HTTPException(
                    status_code=404,
                    detail=f"Roaster with ID '{roaster_id}' not found"
                )
            coffees = await coffee_repository.get_by_roaster(db, roaster_id, skip=skip, limit=limit)
        else:
            coffees = await coffee_repository.get_multi(db, skip=skip, limit=limit)

        total = await coffee_repository.count(db)

        return CoffeeListResponse(
            coffees=[CoffeeResponse.model_validate(coffee) for coffee in coffees],
            total=total,
            page=skip // limit + 1,
            size=len(coffees)
        )

    except Exception as e:
        logger.error("Error listing coffees", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/{coffee_id}")
async def get_coffee():
    """Get a specific coffee."""
    return {"message": "Get coffee - Coming soon"}