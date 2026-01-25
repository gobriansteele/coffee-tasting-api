"""Base repository for Neo4j graph operations."""

from typing import LiteralString

from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError

from app.core.logging import get_logger

logger = get_logger(__name__)

# Embedding dimensions for text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536

# Constraint queries as literals (updated for new schema)
_CONSTRAINT_COFFEE_DRINKER: LiteralString = (
    "CREATE CONSTRAINT coffee_drinker_id IF NOT EXISTS FOR (u:CoffeeDrinker) REQUIRE u.id IS UNIQUE"
)
_CONSTRAINT_ROASTER: LiteralString = (
    "CREATE CONSTRAINT roaster_id IF NOT EXISTS FOR (r:Roaster) REQUIRE r.id IS UNIQUE"
)
_CONSTRAINT_COFFEE: LiteralString = (
    "CREATE CONSTRAINT coffee_id IF NOT EXISTS FOR (c:Coffee) REQUIRE c.id IS UNIQUE"
)
_CONSTRAINT_FLAVOR_ID: LiteralString = (
    "CREATE CONSTRAINT flavor_id IF NOT EXISTS FOR (f:Flavor) REQUIRE f.id IS UNIQUE"
)
_CONSTRAINT_FLAVOR_NAME: LiteralString = (
    "CREATE CONSTRAINT flavor_name IF NOT EXISTS FOR (f:Flavor) REQUIRE f.name IS UNIQUE"
)
_CONSTRAINT_TASTING: LiteralString = (
    "CREATE CONSTRAINT tasting_id IF NOT EXISTS FOR (t:Tasting) REQUIRE t.id IS UNIQUE"
)
_CONSTRAINT_RATING: LiteralString = (
    "CREATE CONSTRAINT rating_id IF NOT EXISTS FOR (r:Rating) REQUIRE r.id IS UNIQUE"
)

# Regular indexes for common queries
_INDEX_COFFEE_ORIGIN: LiteralString = (
    "CREATE INDEX coffee_origin IF NOT EXISTS FOR (c:Coffee) ON (c.origin_country)"
)
_INDEX_COFFEE_ROAST: LiteralString = (
    "CREATE INDEX coffee_roast IF NOT EXISTS FOR (c:Coffee) ON (c.roast_level)"
)
_INDEX_FLAVOR_CATEGORY: LiteralString = (
    "CREATE INDEX flavor_category IF NOT EXISTS FOR (f:Flavor) ON (f.category)"
)

# Vector index queries (Neo4j 5.11+)
_VECTOR_INDEX_COFFEE: LiteralString = """
CREATE VECTOR INDEX coffee_embedding IF NOT EXISTS
FOR (c:Coffee) ON c.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
"""

_VECTOR_INDEX_FLAVOR: LiteralString = """
CREATE VECTOR INDEX flavor_embedding IF NOT EXISTS
FOR (f:Flavor) ON f.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
"""


class GraphRepository:
    """Base class for Neo4j graph operations.

    Provides error handling and constraint setup for the Neo4j-only architecture.
    """

    @staticmethod
    def _handle_graph_error(error: Exception, operation: str) -> None:
        """Log graph errors.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        """
        error_type = type(error).__name__
        error_message = str(error)

        if isinstance(error, Neo4jError):
            logger.error(
                "Neo4j operation failed",
                operation=operation,
                error_type=error_type,
                error=error_message,
                code=getattr(error, "code", None),
            )
        else:
            logger.error(
                "Graph operation failed",
                operation=operation,
                error_type=error_type,
                error=error_message,
            )

    async def ensure_constraints(self, session: AsyncSession) -> None:
        """Create unique constraints and indexes if they don't exist.

        Should be called once on application startup after Neo4j connection
        is established. Constraints ensure MERGE operations are performant.

        Args:
            session: Neo4j async session
        """
        # Unique constraints
        constraints = [
            (_CONSTRAINT_COFFEE_DRINKER, "CoffeeDrinker"),
            (_CONSTRAINT_ROASTER, "Roaster"),
            (_CONSTRAINT_COFFEE, "Coffee"),
            (_CONSTRAINT_FLAVOR_ID, "Flavor.id"),
            (_CONSTRAINT_FLAVOR_NAME, "Flavor.name"),
            (_CONSTRAINT_TASTING, "Tasting"),
            (_CONSTRAINT_RATING, "Rating"),
        ]

        for query, name in constraints:
            try:
                await session.run(query)
            except Exception as e:
                self._handle_graph_error(e, f"create constraint for {name}")

        # Regular indexes
        indexes = [
            (_INDEX_COFFEE_ORIGIN, "coffee_origin"),
            (_INDEX_COFFEE_ROAST, "coffee_roast"),
            (_INDEX_FLAVOR_CATEGORY, "flavor_category"),
        ]

        for query, name in indexes:
            try:
                await session.run(query)
            except Exception as e:
                self._handle_graph_error(e, f"create index {name}")

        # Vector indexes for embedding similarity search
        vector_indexes = [
            (_VECTOR_INDEX_COFFEE, "coffee_embedding"),
            (_VECTOR_INDEX_FLAVOR, "flavor_embedding"),
        ]

        for query, name in vector_indexes:
            try:
                await session.run(query)
            except Exception as e:
                self._handle_graph_error(e, f"create vector index {name}")

        logger.info("Graph constraints and indexes initialized")


# Global instance for use in app startup
graph_repository = GraphRepository()
