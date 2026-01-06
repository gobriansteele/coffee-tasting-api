"""Graph query repository for reading data from Neo4j."""

from typing import LiteralString

from neo4j import AsyncSession

from app.core.logging import get_logger

from .base import GraphRepository

logger = get_logger(__name__)

# --- Query for entities missing embeddings ---

_GET_COFFEES_WITHOUT_EMBEDDING: LiteralString = """
MATCH (c:Coffee)
WHERE c.embedding IS NULL
RETURN c.id AS id
"""

_GET_FLAVOR_TAGS_WITHOUT_EMBEDDING: LiteralString = """
MATCH (f:FlavorTag)
WHERE f.embedding IS NULL
RETURN f.id AS id
"""

# --- Count queries ---

_COUNT_COFFEES_WITHOUT_EMBEDDING: LiteralString = """
MATCH (c:Coffee)
WHERE c.embedding IS NULL
RETURN count(c) AS count
"""

_COUNT_FLAVOR_TAGS_WITHOUT_EMBEDDING: LiteralString = """
MATCH (f:FlavorTag)
WHERE f.embedding IS NULL
RETURN count(f) AS count
"""

_COUNT_ALL_COFFEES: LiteralString = """
MATCH (c:Coffee)
RETURN count(c) AS count
"""

_COUNT_ALL_FLAVOR_TAGS: LiteralString = """
MATCH (f:FlavorTag)
RETURN count(f) AS count
"""


class GraphQueryRepository(GraphRepository):
    """Repository for querying Neo4j graph data.

    Provides read operations for graph nodes and relationships.
    All operations use graceful degradation - errors are logged but don't raise.
    """

    async def get_coffee_ids_without_embedding(self, session: AsyncSession) -> list[str]:
        """Get IDs of all Coffee nodes that don't have embeddings.

        Args:
            session: Neo4j async session

        Returns:
            List of coffee ID strings
        """
        try:
            result = await session.run(_GET_COFFEES_WITHOUT_EMBEDDING)
            records = await result.data()
            ids = [record["id"] for record in records]
            logger.debug("Found coffees without embedding", count=len(ids))
            return ids
        except Exception as e:
            self._handle_graph_error(e, "get coffees without embedding")
            return []

    async def get_flavor_tag_ids_without_embedding(self, session: AsyncSession) -> list[str]:
        """Get IDs of all FlavorTag nodes that don't have embeddings.

        Args:
            session: Neo4j async session

        Returns:
            List of flavor tag ID strings
        """
        try:
            result = await session.run(_GET_FLAVOR_TAGS_WITHOUT_EMBEDDING)
            records = await result.data()
            ids = [record["id"] for record in records]
            logger.debug("Found flavor tags without embedding", count=len(ids))
            return ids
        except Exception as e:
            self._handle_graph_error(e, "get flavor tags without embedding")
            return []

    async def count_coffees_without_embedding(self, session: AsyncSession) -> int:
        """Count Coffee nodes without embeddings.

        Args:
            session: Neo4j async session

        Returns:
            Count of coffees missing embeddings
        """
        try:
            result = await session.run(_COUNT_COFFEES_WITHOUT_EMBEDDING)
            record = await result.single()
            return record["count"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count coffees without embedding")
            return 0

    async def count_flavor_tags_without_embedding(self, session: AsyncSession) -> int:
        """Count FlavorTag nodes without embeddings.

        Args:
            session: Neo4j async session

        Returns:
            Count of flavor tags missing embeddings
        """
        try:
            result = await session.run(_COUNT_FLAVOR_TAGS_WITHOUT_EMBEDDING)
            record = await result.single()
            return record["count"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count flavor tags without embedding")
            return 0

    async def count_all_coffees(self, session: AsyncSession) -> int:
        """Count all Coffee nodes in the graph.

        Args:
            session: Neo4j async session

        Returns:
            Total count of coffees
        """
        try:
            result = await session.run(_COUNT_ALL_COFFEES)
            record = await result.single()
            return record["count"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count all coffees")
            return 0

    async def count_all_flavor_tags(self, session: AsyncSession) -> int:
        """Count all FlavorTag nodes in the graph.

        Args:
            session: Neo4j async session

        Returns:
            Total count of flavor tags
        """
        try:
            result = await session.run(_COUNT_ALL_FLAVOR_TAGS)
            record = await result.single()
            return record["count"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count all flavor tags")
            return 0


# Global instance
graph_query_repository = GraphQueryRepository()
