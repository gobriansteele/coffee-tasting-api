from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user_id, require_user_access
from app.api.deps.database import get_db
from app.core.logging import get_logger
from app.repositories.sql.coffee import coffee_repository
from app.repositories.sql.flavor_tag import flavor_tag_repository
from app.repositories.sql.roaster import roaster_repository
from app.schemas.coffee import CoffeeCreate, CoffeeListResponse, CoffeeResponse
from app.tasks.graph_sync import delete_coffee_from_graph, sync_coffee_to_graph

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=CoffeeResponse, status_code=201)
async def create_coffee(
    coffee_data: CoffeeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> CoffeeResponse:
    """Create a new coffee."""
    try:
        # Verify roaster exists
        roaster = await roaster_repository.get(db, coffee_data.roaster_id)
        if not roaster:
            raise HTTPException(
                status_code=404, detail=f"Roaster with ID '{coffee_data.roaster_id}' not found"
            )

        # Check if coffee with same name already exists for this roaster
        existing_coffee = await coffee_repository.get_by_name_and_roaster(
            db, coffee_data.name, coffee_data.roaster_id
        )
        if existing_coffee:
            raise HTTPException(
                status_code=400,
                detail=f"Coffee '{coffee_data.name}' already exists for roaster '{roaster.name}'",
            )

        # Handle flavor tags
        flavor_tags = []
        if coffee_data.flavor_tags:
            flavor_tags = await flavor_tag_repository.find_or_create_multiple(
                db, coffee_data.flavor_tags, user_id=current_user_id
            )

        # Create the coffee with flavor tags
        coffee = await coffee_repository.create_with_flavor_tags(
            db, coffee_data=coffee_data, flavor_tags=flavor_tags, current_user_id=current_user_id
        )
        logger.info(
            "Created coffee",
            coffee_id=str(coffee.id),
            name=coffee.name,
            roaster_id=str(coffee.roaster_id),
            flavor_tags=coffee_data.flavor_tags,
        )

        # Queue graph sync
        background_tasks.add_task(sync_coffee_to_graph, coffee.id, current_user_id)

        return CoffeeResponse.model_validate(coffee)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating coffee", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/")
async def list_coffees(
    roaster_id: UUID = Query(None, description="Filter coffees by roaster ID"),
    skip: int = Query(0, ge=0, description="Number of coffees to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of coffees to return"),
    search: str = Query(None, description="Search coffees by name"),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> CoffeeListResponse:
    """List coffees for the current user."""

    try:
        if search:
            # Search by name (user-scoped)
            coffees = await coffee_repository.search_by_name_for_user(
                db, search, current_user_id, skip=skip, limit=limit
            )
        elif roaster_id:
            # Filter by roaster ID (user-scoped)
            roaster = await roaster_repository.get(db, roaster_id)
            if not roaster:
                raise HTTPException(status_code=404, detail=f"Roaster with ID '{roaster_id}' not found")
            coffees = await coffee_repository.get_by_roaster_for_user(
                db, roaster_id, current_user_id, skip=skip, limit=limit
            )
        else:
            coffees = await coffee_repository.get_multi_for_user(db, current_user_id, skip=skip, limit=limit)

        total = await coffee_repository.count_for_user(db, current_user_id)

        return CoffeeListResponse(
            coffees=[CoffeeResponse.model_validate(coffee) for coffee in coffees],
            total=total,
            page=skip // limit + 1,
            size=len(coffees),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing coffees", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{coffee_id}")
async def get_coffee(
    coffee_id: UUID, db: AsyncSession = Depends(get_db), current_user_id: str = Depends(get_current_user_id)
) -> CoffeeResponse:
    """Get a specific coffee owned by the current user."""
    try:
        coffee = await coffee_repository.get_with_flavor_tags(db, coffee_id)
        if not coffee or coffee.created_by != current_user_id:
            raise HTTPException(status_code=404, detail="Coffee not found")

        return CoffeeResponse.model_validate(coffee)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting coffee", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{coffee_id}", status_code=204)
async def delete_coffee(
    coffee_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """Delete a specific coffee."""
    try:
        # Check if coffee exists and is not already deleted
        coffee = await coffee_repository.get(db, coffee_id)
        if not coffee:
            raise HTTPException(status_code=404, detail="Coffee not found")

        # Verify the user owns this coffee (created by them)
        if not coffee.created_by:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resource has no owner")
        require_user_access(coffee.created_by, current_user_id)

        # Perform soft delete
        await coffee_repository.delete(db, id=coffee_id, current_user_id=current_user_id)

        # Queue graph delete
        background_tasks.add_task(delete_coffee_from_graph, coffee_id)

        logger.info("Deleted coffee", coffee_id=str(coffee_id), user_id=current_user_id)

    except HTTPException:
        raise
    except ValueError as e:
        # This handles the case where the coffee was not found in the delete method
        logger.error("Coffee not found for deletion", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=404, detail="Coffee not found") from e
    except Exception as e:
        logger.error("Error deleting coffee", coffee_id=str(coffee_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
