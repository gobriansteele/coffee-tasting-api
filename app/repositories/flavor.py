"""Flavor repository for Neo4j operations."""

from typing import LiteralString
from uuid import uuid4

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


# --- Cypher Queries ---

_CREATE_FLAVOR: LiteralString = """
MERGE (f:Flavor {name: $name})
ON CREATE SET
    f.id = $id,
    f.category = $category
ON MATCH SET
    f.category = COALESCE($category, f.category)
RETURN f.id AS id, f.name AS name, f.category AS category
"""

_GET_BY_ID: LiteralString = """
MATCH (f:Flavor {id: $id})
RETURN f.id AS id, f.name AS name, f.category AS category
"""

_GET_BY_NAME: LiteralString = """
MATCH (f:Flavor {name: $name})
RETURN f.id AS id, f.name AS name, f.category AS category
"""

_LIST_ALL: LiteralString = """
MATCH (f:Flavor)
RETURN f.id AS id, f.name AS name, f.category AS category
ORDER BY f.name
SKIP $skip LIMIT $limit
"""

_LIST_BY_CATEGORY: LiteralString = """
MATCH (f:Flavor {category: $category})
RETURN f.id AS id, f.name AS name, f.category AS category
ORDER BY f.name
SKIP $skip LIMIT $limit
"""

_COUNT_ALL: LiteralString = """
MATCH (f:Flavor)
RETURN count(f) AS total
"""

_COUNT_BY_CATEGORY: LiteralString = """
MATCH (f:Flavor {category: $category})
RETURN count(f) AS total
"""

_SEARCH_BY_NAME: LiteralString = """
MATCH (f:Flavor)
WHERE toLower(f.name) CONTAINS toLower($query)
RETURN f.id AS id, f.name AS name, f.category AS category
ORDER BY f.name
LIMIT $limit
"""

_SET_EMBEDDING: LiteralString = """
MATCH (f:Flavor {id: $flavor_id})
SET f.embedding = $embedding
"""

_CHECK_EMBEDDING_EXISTS: LiteralString = """
MATCH (f:Flavor {id: $flavor_id})
RETURN f.embedding IS NOT NULL AS has_embedding
"""


class FlavorRepository(GraphRepository):
    """Repository for Flavor CRUD operations in Neo4j."""

    async def _generate_and_store_embedding(
        self,
        session: AsyncSession,
        flavor_id: str,
        flavor_data: dict,
    ) -> None:
        """Generate and store embedding for a flavor.

        Args:
            session: Neo4j async session
            flavor_id: Flavor UUID
            flavor_data: Flavor dict with name and category
        """
        if not embedding_service.is_configured:
            logger.debug("Skipping embedding generation - OpenAI not configured")
            return

        try:
            # Check if embedding already exists
            result = await session.run(_CHECK_EMBEDDING_EXISTS, {"flavor_id": flavor_id})
            record = await result.single()
            if record and record["has_embedding"]:
                logger.debug("Flavor already has embedding", flavor_id=flavor_id)
                return

            # Build text representation and generate embedding
            text = embedding_service.build_flavor_text(flavor_data)
            embedding = await embedding_service.generate_embedding(text)

            # Store embedding on the flavor node
            await session.run(
                _SET_EMBEDDING,
                {"flavor_id": flavor_id, "embedding": embedding},
            )
            logger.debug("Stored embedding for flavor", flavor_id=flavor_id)

        except Exception as e:
            # Log but don't fail the operation - embedding is enhancement, not critical
            logger.warning(
                "Failed to generate embedding for flavor",
                flavor_id=flavor_id,
                error=str(e),
            )

    async def get_or_create(
        self,
        session: AsyncSession,
        name: str,
        category: str | None = None,
    ) -> dict | None:
        """Get existing flavor by name or create new one.

        Uses MERGE for idempotent creation.

        Args:
            session: Neo4j async session
            name: Flavor name (unique)
            category: Optional flavor category

        Returns:
            Flavor dict with id, name, category or None on error
        """
        try:
            result = await session.run(
                _CREATE_FLAVOR,
                {
                    "id": str(uuid4()),
                    "name": name,
                    "category": category,
                },
            )
            record = await result.single()
            if record:
                flavor = dict(record)
                # Generate embedding (will skip if already exists)
                await self._generate_and_store_embedding(session, flavor["id"], flavor)
                return flavor
            return None
        except Exception as e:
            self._handle_graph_error(e, f"get_or_create flavor {name}")
            return None

    async def get_by_id(self, session: AsyncSession, flavor_id: str) -> dict | None:
        """Get a flavor by ID.

        Args:
            session: Neo4j async session
            flavor_id: Flavor UUID as string

        Returns:
            Flavor dict or None if not found
        """
        try:
            result = await session.run(_GET_BY_ID, {"id": flavor_id})
            record = await result.single()
            if record:
                return dict(record)
            return None
        except Exception as e:
            self._handle_graph_error(e, f"get flavor {flavor_id}")
            return None

    async def get_by_name(self, session: AsyncSession, name: str) -> dict | None:
        """Get a flavor by name.

        Args:
            session: Neo4j async session
            name: Flavor name

        Returns:
            Flavor dict or None if not found
        """
        try:
            result = await session.run(_GET_BY_NAME, {"name": name})
            record = await result.single()
            if record:
                return dict(record)
            return None
        except Exception as e:
            self._handle_graph_error(e, f"get flavor by name {name}")
            return None

    async def list_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
    ) -> list[dict]:
        """List all flavors with pagination.

        Args:
            session: Neo4j async session
            skip: Number of records to skip
            limit: Max records to return
            category: Optional category filter

        Returns:
            List of flavor dicts
        """
        try:
            if category:
                result = await session.run(
                    _LIST_BY_CATEGORY,
                    {"category": category, "skip": skip, "limit": limit},
                )
            else:
                result = await session.run(
                    _LIST_ALL,
                    {"skip": skip, "limit": limit},
                )
            records = await result.data()
            return records
        except Exception as e:
            self._handle_graph_error(e, "list flavors")
            return []

    async def count(self, session: AsyncSession, category: str | None = None) -> int:
        """Count total flavors.

        Args:
            session: Neo4j async session
            category: Optional category filter

        Returns:
            Total count
        """
        try:
            if category:
                result = await session.run(_COUNT_BY_CATEGORY, {"category": category})
            else:
                result = await session.run(_COUNT_ALL)
            record = await result.single()
            return record["total"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count flavors")
            return 0

    async def search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Search flavors by name.

        Args:
            session: Neo4j async session
            query: Search query
            limit: Max results

        Returns:
            List of matching flavor dicts
        """
        try:
            result = await session.run(
                _SEARCH_BY_NAME,
                {"query": query, "limit": limit},
            )
            records = await result.data()
            return records
        except Exception as e:
            self._handle_graph_error(e, f"search flavors {query}")
            return []


# Global instance
flavor_repository = FlavorRepository()
