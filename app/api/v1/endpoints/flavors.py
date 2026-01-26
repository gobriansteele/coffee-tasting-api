"""Flavor endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.deps.auth import ensure_user_exists
from app.api.deps.graph import get_graph_db
from app.core.logging import get_logger
from app.repositories.flavor import flavor_repository
from app.schemas.flavor import FlavorCreate, FlavorListResponse, FlavorResponse

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=FlavorResponse, status_code=201)
async def create_flavor(
    flavor_data: FlavorCreate,
    session: AsyncSession = Depends(get_graph_db),
    _: str = Depends(ensure_user_exists),
) -> FlavorResponse:
    """Create a new flavor or return existing one with same name.

    Flavors are shared across all users. Creating a flavor that already
    exists will return the existing flavor (idempotent).
    """
    try:
        flavor = await flavor_repository.get_or_create(
            session,
            name=flavor_data.name,
            category=flavor_data.category,
        )

        if not flavor:
            raise HTTPException(status_code=500, detail="Failed to create flavor")

        logger.info("Created/retrieved flavor", flavor_id=flavor["id"], name=flavor["name"])

        return FlavorResponse(
            id=UUID(flavor["id"]),
            name=flavor["name"],
            category=flavor.get("category"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating flavor", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/", response_model=FlavorListResponse)
async def list_flavors(
    skip: int = Query(0, ge=0, description="Number of flavors to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of flavors to return"),
    category: str | None = Query(None, description="Filter by category"),
    session: AsyncSession = Depends(get_graph_db),
    _: str = Depends(ensure_user_exists),
) -> FlavorListResponse:
    """List all flavors with optional category filter."""
    try:
        flavors = await flavor_repository.list_all(
            session,
            skip=skip,
            limit=limit,
            category=category,
        )
        total = await flavor_repository.count(session, category=category)

        return FlavorListResponse(
            items=[
                FlavorResponse(
                    id=UUID(f["id"]),
                    name=f["name"],
                    category=f.get("category"),
                )
                for f in flavors
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error("Error listing flavors", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{flavor_id}", response_model=FlavorResponse)
async def get_flavor(
    flavor_id: UUID,
    session: AsyncSession = Depends(get_graph_db),
    _: str = Depends(ensure_user_exists),
) -> FlavorResponse:
    """Get a specific flavor by ID."""
    try:
        flavor = await flavor_repository.get_by_id(session, str(flavor_id))

        if not flavor:
            raise HTTPException(status_code=404, detail="Flavor not found")

        return FlavorResponse(
            id=UUID(flavor["id"]),
            name=flavor["name"],
            category=flavor.get("category"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting flavor", flavor_id=str(flavor_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/search/", response_model=list[FlavorResponse])
async def search_flavors(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    session: AsyncSession = Depends(get_graph_db),
    _: str = Depends(ensure_user_exists),
) -> list[FlavorResponse]:
    """Search flavors by name."""
    try:
        flavors = await flavor_repository.search(session, query=q, limit=limit)

        return [
            FlavorResponse(
                id=UUID(f["id"]),
                name=f["name"],
                category=f.get("category"),
            )
            for f in flavors
        ]

    except Exception as e:
        logger.error("Error searching flavors", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
