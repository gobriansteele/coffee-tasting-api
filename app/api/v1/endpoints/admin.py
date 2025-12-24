"""Admin endpoints for system management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user_id, require_admin
from app.api.deps.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.db import get_graph_session
from app.repositories.graph import graph_sync_repository
from app.repositories.sql.coffee import coffee_repository
from app.repositories.sql.roaster import roaster_repository
from app.repositories.sql.tasting import tasting_repository

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/graph/sync",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sync all PostgreSQL data to Neo4j",
    description="Admin-only endpoint to perform a full sync of all data from PostgreSQL to Neo4j graph database.",
)
async def sync_graph_database(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    _: str = Depends(require_admin),
) -> Response:
    """Perform a full sync of PostgreSQL data to Neo4j.

    This endpoint syncs all active roasters, coffees, and tasting sessions
    to the Neo4j graph database. Use this to reconcile any drift between
    the two databases.

    Requires admin role.
    """
    if not settings.neo4j_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is not configured",
        )

    logger.info("Starting full graph sync", initiated_by=current_user_id)

    errors: list[str] = []
    roasters_synced = 0
    coffees_synced = 0
    tastings_synced = 0

    # Keep all work inside the generator scope so the session stays open
    async for graph_session in get_graph_session():
        batch_size = 100

        # Sync all roasters
        skip = 0
        while True:
            roasters = await roaster_repository.get_multi_all(db, skip=skip, limit=batch_size)
            if not roasters:
                break

            for roaster in roasters:
                try:
                    await graph_sync_repository.sync_roaster_full(
                        graph_session, roaster, roaster.created_by
                    )
                    roasters_synced += 1
                except Exception as e:
                    error_msg = f"Failed to sync roaster {roaster.id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            skip += batch_size

        # Sync all coffees
        skip = 0
        while True:
            coffees = await coffee_repository.get_multi_all(db, skip=skip, limit=batch_size)
            if not coffees:
                break

            for coffee in coffees:
                try:
                    # Get coffee with flavor tags for full sync
                    coffee_with_tags = await coffee_repository.get_with_flavor_tags(db, coffee.id)
                    if coffee_with_tags:
                        await graph_sync_repository.sync_coffee_full(
                            graph_session, coffee_with_tags, coffee_with_tags.created_by
                        )
                        coffees_synced += 1
                except Exception as e:
                    error_msg = f"Failed to sync coffee {coffee.id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            skip += batch_size

        # Sync all tastings
        skip = 0
        while True:
            tastings = await tasting_repository.get_multi_all(db, skip=skip, limit=batch_size)
            if not tastings:
                break

            for tasting in tastings:
                try:
                    # Get tasting with notes for full sync
                    tasting_with_notes = await tasting_repository.get_with_notes(db, tasting.id)
                    if tasting_with_notes:
                        await graph_sync_repository.sync_tasting_full(graph_session, tasting_with_notes)
                        tastings_synced += 1
                except Exception as e:
                    error_msg = f"Failed to sync tasting {tasting.id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            skip += batch_size

        # Only iterate once - the generator provides a single session
        break

    logger.info(
        "Completed full graph sync",
        roasters_synced=roasters_synced,
        coffees_synced=coffees_synced,
        tastings_synced=tastings_synced,
        errors_count=len(errors),
        initiated_by=current_user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
