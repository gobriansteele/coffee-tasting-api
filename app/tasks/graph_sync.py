"""Background tasks for syncing PostgreSQL data to Neo4j."""

from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.db import get_graph_session
from app.db.database import AsyncSessionLocal
from app.repositories.graph import graph_sync_repository
from app.repositories.sql.coffee import coffee_repository
from app.repositories.sql.flavor_tag import flavor_tag_repository
from app.repositories.sql.roaster import roaster_repository
from app.repositories.sql.tasting import tasting_repository
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


async def sync_roaster_to_graph(roaster_id: UUID, user_id: str | None = None) -> None:
    """Background task to sync a roaster to the graph.

    Args:
        roaster_id: The UUID of the roaster to sync
        user_id: Optional user ID to create CREATED relationship
    """
    if not settings.neo4j_configured:
        return

    try:
        # Get roaster from PostgreSQL
        async with AsyncSessionLocal() as db:
            roaster = await roaster_repository.get(db, roaster_id)
            if not roaster:
                logger.warning("Roaster not found for graph sync", roaster_id=str(roaster_id))
                return

        # Sync to graph
        async for graph_session in get_graph_session():
            await graph_sync_repository.sync_roaster_full(graph_session, roaster, user_id)
            logger.info(
                "Synced roaster to graph",
                roaster_id=str(roaster_id),
                roaster_name=roaster.name,
            )
            break

    except Exception as e:
        logger.error(
            "Failed to sync roaster to graph",
            roaster_id=str(roaster_id),
            error=str(e),
        )


async def delete_roaster_from_graph(roaster_id: UUID) -> None:
    """Background task to delete a roaster from the graph.

    Args:
        roaster_id: The UUID of the roaster to delete
    """
    if not settings.neo4j_configured:
        return

    try:
        async for graph_session in get_graph_session():
            await graph_sync_repository.delete_roaster(graph_session, str(roaster_id))
            logger.info("Deleted roaster from graph", roaster_id=str(roaster_id))
            break

    except Exception as e:
        logger.error(
            "Failed to delete roaster from graph",
            roaster_id=str(roaster_id),
            error=str(e),
        )


async def sync_coffee_to_graph(coffee_id: UUID, user_id: str | None = None) -> None:
    """Background task to sync a coffee to the graph.

    Args:
        coffee_id: The UUID of the coffee to sync
        user_id: Optional user ID to create CREATED relationship
    """
    if not settings.neo4j_configured:
        return

    try:
        # Get coffee with relationships from PostgreSQL
        async with AsyncSessionLocal() as db:
            coffee = await coffee_repository.get_with_flavor_tags(db, coffee_id)
            if not coffee:
                logger.warning("Coffee not found for graph sync", coffee_id=str(coffee_id))
                return

        # Sync to graph
        async for graph_session in get_graph_session():
            await graph_sync_repository.sync_coffee_full(graph_session, coffee, user_id)
            logger.info(
                "Synced coffee to graph",
                coffee_id=str(coffee_id),
                coffee_name=coffee.name,
            )

            # Generate and store embedding if OpenAI is configured
            if embedding_service.is_configured:
                try:
                    text = embedding_service.build_coffee_text(coffee)
                    embedding = await embedding_service.generate_embedding(text)
                    await graph_sync_repository.upsert_coffee_embedding(
                        graph_session, str(coffee_id), embedding
                    )
                    logger.info(
                        "Generated coffee embedding",
                        coffee_id=str(coffee_id),
                        text_length=len(text),
                    )
                except Exception as e:
                    logger.error(
                        "Failed to generate coffee embedding",
                        coffee_id=str(coffee_id),
                        error=str(e),
                    )
            break

    except Exception as e:
        logger.error(
            "Failed to sync coffee to graph",
            coffee_id=str(coffee_id),
            error=str(e),
        )


async def delete_coffee_from_graph(coffee_id: UUID) -> None:
    """Background task to delete a coffee from the graph.

    Args:
        coffee_id: The UUID of the coffee to delete
    """
    if not settings.neo4j_configured:
        return

    try:
        async for graph_session in get_graph_session():
            await graph_sync_repository.delete_coffee(graph_session, str(coffee_id))
            logger.info("Deleted coffee from graph", coffee_id=str(coffee_id))
            break

    except Exception as e:
        logger.error(
            "Failed to delete coffee from graph",
            coffee_id=str(coffee_id),
            error=str(e),
        )


async def sync_flavor_tag_to_graph(flavor_tag_id: UUID) -> None:
    """Background task to sync a flavor tag to the graph with embedding.

    Args:
        flavor_tag_id: The UUID of the flavor tag to sync
    """
    if not settings.neo4j_configured:
        return

    try:
        # Get flavor tag from PostgreSQL
        async with AsyncSessionLocal() as db:
            tag = await flavor_tag_repository.get(db, flavor_tag_id)
            if not tag:
                logger.warning("Flavor tag not found for graph sync", flavor_tag_id=str(flavor_tag_id))
                return

        # Sync to graph
        async for graph_session in get_graph_session():
            await graph_sync_repository.upsert_flavor_tag(graph_session, tag)
            logger.info(
                "Synced flavor tag to graph",
                flavor_tag_id=str(flavor_tag_id),
                tag_name=tag.name,
            )

            # Generate and store embedding if OpenAI is configured
            if embedding_service.is_configured:
                try:
                    text = embedding_service.build_flavor_tag_text(tag)
                    embedding = await embedding_service.generate_embedding(text)
                    await graph_sync_repository.upsert_flavor_tag_embedding(
                        graph_session, str(flavor_tag_id), embedding
                    )
                    logger.info(
                        "Generated flavor tag embedding",
                        flavor_tag_id=str(flavor_tag_id),
                        tag_name=tag.name,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to generate flavor tag embedding",
                        flavor_tag_id=str(flavor_tag_id),
                        error=str(e),
                    )
            break

    except Exception as e:
        logger.error(
            "Failed to sync flavor tag to graph",
            flavor_tag_id=str(flavor_tag_id),
            error=str(e),
        )


async def delete_flavor_tag_from_graph(flavor_tag_id: UUID) -> None:
    """Background task to delete a flavor tag from the graph.

    Args:
        flavor_tag_id: The UUID of the flavor tag to delete
    """
    if not settings.neo4j_configured:
        return

    try:
        async for graph_session in get_graph_session():
            await graph_sync_repository.delete_flavor_tag(graph_session, str(flavor_tag_id))
            logger.info("Deleted flavor tag from graph", flavor_tag_id=str(flavor_tag_id))
            break

    except Exception as e:
        logger.error(
            "Failed to delete flavor tag from graph",
            flavor_tag_id=str(flavor_tag_id),
            error=str(e),
        )


async def sync_tasting_to_graph(tasting_id: UUID) -> None:
    """Background task to sync a tasting session to the graph.

    Args:
        tasting_id: The UUID of the tasting session to sync
    """
    if not settings.neo4j_configured:
        return

    try:
        # Get tasting with relationships from PostgreSQL
        async with AsyncSessionLocal() as db:
            tasting = await tasting_repository.get_with_notes(db, tasting_id)
            if not tasting:
                logger.warning("Tasting not found for graph sync", tasting_id=str(tasting_id))
                return

        # Sync to graph
        async for graph_session in get_graph_session():
            await graph_sync_repository.sync_tasting_full(graph_session, tasting)
            logger.info(
                "Synced tasting to graph",
                tasting_id=str(tasting_id),
                coffee_id=str(tasting.coffee_id),
            )
            break

    except Exception as e:
        logger.error(
            "Failed to sync tasting to graph",
            tasting_id=str(tasting_id),
            error=str(e),
        )


async def delete_tasting_from_graph(tasting_id: UUID) -> None:
    """Background task to delete a tasting session from the graph.

    Args:
        tasting_id: The UUID of the tasting session to delete
    """
    if not settings.neo4j_configured:
        return

    try:
        async for graph_session in get_graph_session():
            await graph_sync_repository.delete_tasting_session(graph_session, str(tasting_id))
            logger.info("Deleted tasting from graph", tasting_id=str(tasting_id))
            break

    except Exception as e:
        logger.error(
            "Failed to delete tasting from graph",
            tasting_id=str(tasting_id),
            error=str(e),
        )
