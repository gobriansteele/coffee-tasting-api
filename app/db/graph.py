"""Neo4j Graph Database connection management."""

from collections.abc import AsyncGenerator

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Neo4j driver (singleton)
_driver: AsyncDriver | None = None


async def create_graph_driver() -> None:
    """Create the Neo4j async driver."""
    global _driver

    if not settings.neo4j_configured:
        logger.warning("Neo4j not configured - graph features will be disabled")
        return

    try:
        # Mask password for logging
        masked_uri = settings.NEO4J_URI
        logger.info("Connecting to Neo4j", uri=masked_uri)

        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=50,
            connection_timeout=30,
        )

        logger.info("Neo4j driver created successfully")
    except Exception as e:
        logger.error("Failed to create Neo4j driver", error=str(e))
        raise


async def close_graph_driver() -> None:
    """Close the Neo4j driver and release resources."""
    global _driver

    if _driver is not None:
        try:
            await _driver.close()
            logger.info("Neo4j driver closed successfully")
        except Exception as e:
            logger.error("Error closing Neo4j driver", error=str(e))
        finally:
            _driver = None


def get_graph_driver() -> AsyncDriver | None:
    """Get the Neo4j driver instance."""
    return _driver


async def get_graph_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async Neo4j session for graph operations.

    Yields:
        AsyncSession: Neo4j async session

    Raises:
        RuntimeError: If Neo4j driver is not initialized
    """
    if _driver is None:
        if not settings.neo4j_configured:
            raise RuntimeError("Neo4j is not configured. Set NEO4J_URI and NEO4J_PASSWORD.")
        raise RuntimeError("Neo4j driver not initialized. Call create_graph_driver() first.")

    async with _driver.session() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Neo4j session error", error=str(e))
            raise


async def check_graph_connection() -> bool:
    """Check if Neo4j connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    if _driver is None:
        if not settings.neo4j_configured:
            logger.info("Neo4j not configured - skipping connection check")
            return True  # Not an error if not configured
        return False

    try:
        async with _driver.session() as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            if record and record["num"] == 1:
                logger.info("Neo4j connection check successful")
                return True
            return False
    except Exception as e:
        logger.error("Neo4j connection check failed", error=str(e))
        return False


