"""Admin endpoints for system management."""

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user_id, require_admin, require_api_key
from app.api.deps.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.db import get_graph_session
from app.repositories.graph import graph_query_repository, graph_sync_repository
from app.repositories.sql.coffee import coffee_repository
from app.repositories.sql.roaster import roaster_repository
from app.repositories.sql.tasting import tasting_repository
from app.services import embedding_service

logger = get_logger(__name__)

router = APIRouter()


# --- Embedding Trueup Schemas ---


class EntityType(str, Enum):
    """Entity types that support embeddings."""

    COFFEE = "coffee"
    FLAVOR_TAG = "flavor_tag"


class EmbeddingTrueupRequest(BaseModel):
    """Request body for embedding trueup."""

    entity_types: list[EntityType] = Field(
        default=[EntityType.COFFEE, EntityType.FLAVOR_TAG],
        description="Entity types to process. Defaults to all.",
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of entities to process in parallel per batch.",
    )


class EmbeddingTrueupResponse(BaseModel):
    """Response from embedding trueup operation."""

    coffees_found: int = Field(description="Number of coffees found without embeddings")
    coffees_processed: int = Field(description="Number of coffees successfully processed")
    coffees_failed: int = Field(description="Number of coffees that failed processing")
    flavor_tags_found: int = Field(description="Number of flavor tags found without embeddings")
    flavor_tags_processed: int = Field(description="Number of flavor tags successfully processed")
    flavor_tags_failed: int = Field(description="Number of flavor tags that failed processing")
    errors: list[str] = Field(default_factory=list, description="Error messages for failed entities")


class EmbeddingStatusResponse(BaseModel):
    """Response showing current embedding status."""

    coffees_total: int = Field(description="Total coffees in graph")
    coffees_without_embedding: int = Field(description="Coffees missing embeddings")
    flavor_tags_total: int = Field(description="Total flavor tags in graph")
    flavor_tags_without_embedding: int = Field(description="Flavor tags missing embeddings")


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


@router.get(
    "/embeddings/status",
    response_model=EmbeddingStatusResponse,
    summary="Get embedding status",
    description="Get counts of entities with and without embeddings. Protected by x-api-key header.",
)
async def get_embedding_status(
    _: str = Depends(require_api_key),
) -> EmbeddingStatusResponse:
    """Get current embedding status for all entity types.

    Shows how many entities have embeddings and how many are missing.
    Use this to check before running a trueup operation.

    Requires x-api-key header.
    """
    if not settings.neo4j_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is not configured",
        )

    async for graph_session in get_graph_session():
        coffees_total = await graph_query_repository.count_all_coffees(graph_session)
        coffees_without = await graph_query_repository.count_coffees_without_embedding(graph_session)
        tags_total = await graph_query_repository.count_all_flavor_tags(graph_session)
        tags_without = await graph_query_repository.count_flavor_tags_without_embedding(graph_session)

        return EmbeddingStatusResponse(
            coffees_total=coffees_total,
            coffees_without_embedding=coffees_without,
            flavor_tags_total=tags_total,
            flavor_tags_without_embedding=tags_without,
        )

    # Should not reach here
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Failed to connect to Neo4j",
    )


@router.post(
    "/embeddings/trueup",
    response_model=EmbeddingTrueupResponse,
    summary="True up embeddings for entities",
    description="Generate embeddings for entities that are missing them. Protected by x-api-key header.",
)
async def trueup_embeddings(
    request: EmbeddingTrueupRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
) -> EmbeddingTrueupResponse:
    """True up embeddings for entities missing them.

    Queries the Neo4j graph for entities without embeddings, fetches their
    data from PostgreSQL, generates embeddings via OpenAI, and stores them
    back in the graph.

    Processing is done in parallel batches for efficiency while respecting
    OpenAI rate limits.

    Requires x-api-key header.
    """
    if not settings.neo4j_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j is not configured",
        )

    if not embedding_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI is not configured - cannot generate embeddings",
        )

    # Create a service instance with the requested batch size
    from app.services.embedding_trueup import EmbeddingTrueupService, TrueupResult

    service = EmbeddingTrueupService(batch_size=request.batch_size)
    result = TrueupResult()

    logger.info(
        "Starting embedding trueup",
        entity_types=[et.value for et in request.entity_types],
        batch_size=request.batch_size,
    )

    async for graph_session in get_graph_session():
        # Process requested entity types
        if EntityType.COFFEE in request.entity_types:
            await service.trueup_coffees(db, graph_session, result)

        if EntityType.FLAVOR_TAG in request.entity_types:
            await service.trueup_flavor_tags(db, graph_session, result)

        break

    logger.info(
        "Completed embedding trueup",
        coffees_found=result.coffees_found,
        coffees_processed=result.coffees_processed,
        coffees_failed=result.coffees_failed,
        flavor_tags_found=result.flavor_tags_found,
        flavor_tags_processed=result.flavor_tags_processed,
        flavor_tags_failed=result.flavor_tags_failed,
        errors_count=len(result.errors),
    )

    return EmbeddingTrueupResponse(
        coffees_found=result.coffees_found,
        coffees_processed=result.coffees_processed,
        coffees_failed=result.coffees_failed,
        flavor_tags_found=result.flavor_tags_found,
        flavor_tags_processed=result.flavor_tags_processed,
        flavor_tags_failed=result.flavor_tags_failed,
        errors=result.errors,
    )
