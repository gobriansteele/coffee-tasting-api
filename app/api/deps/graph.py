"""Neo4j graph database dependencies for FastAPI."""

from collections.abc import AsyncGenerator

from neo4j import AsyncSession

from app.core.config import settings
from app.db.graph import get_graph_session as _get_graph_session


async def get_graph_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get Neo4j graph session.

    Yields:
        AsyncSession: Neo4j async session for graph operations

    Raises:
        RuntimeError: If Neo4j is not configured or driver not initialized
    """
    async for session in _get_graph_session():
        yield session


async def get_graph_db_optional() -> AsyncGenerator[AsyncSession | None, None]:
    """Dependency to optionally get Neo4j graph session.

    This dependency returns None if Neo4j is not configured, allowing
    endpoints to gracefully degrade when graph features are unavailable.

    Yields:
        AsyncSession | None: Neo4j session if available, None otherwise
    """
    if not settings.neo4j_configured:
        yield None
        return

    try:
        async for session in _get_graph_session():
            yield session
    except RuntimeError:
        yield None
