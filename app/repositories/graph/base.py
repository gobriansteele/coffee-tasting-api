"""Base repository for Neo4j graph operations."""
from typing import LiteralString

from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError

from app.core.logging import get_logger

logger = get_logger(__name__)

# Constraint queries as literals
_CONSTRAINT_USER: LiteralString = "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE"
_CONSTRAINT_ROASTER: LiteralString = "CREATE CONSTRAINT roaster_id IF NOT EXISTS FOR (n:Roaster) REQUIRE n.id IS UNIQUE"
_CONSTRAINT_COFFEE: LiteralString = "CREATE CONSTRAINT coffee_id IF NOT EXISTS FOR (n:Coffee) REQUIRE n.id IS UNIQUE"
_CONSTRAINT_FLAVOR_TAG: LiteralString = "CREATE CONSTRAINT flavor_tag_id IF NOT EXISTS FOR (n:FlavorTag) REQUIRE n.id IS UNIQUE"
_CONSTRAINT_TASTING: LiteralString = "CREATE CONSTRAINT tasting_session_id IF NOT EXISTS FOR (n:TastingSession) REQUIRE n.id IS UNIQUE"


class GraphRepository:
    """Base class for Neo4j graph operations.

    Provides error handling with graceful degradation - graph failures
    are logged but don't crash the application.

    Subclasses define their own Cypher queries as module-level constants
    and call session.run() directly with those literals.
    """
    @staticmethod
    def _handle_graph_error(error: Exception, operation: str) -> None:
        """Log graph errors without failing the application.

        Implements graceful degradation - graph operations are supplementary
        to the main PostgreSQL data store, so failures shouldn't break the API.

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
        """Create unique constraints on node IDs if they don't exist.

        Should be called once on application startup after Neo4j connection
        is established. Constraints ensure MERGE operations are performant.

        Args:
            session: Neo4j async session
        """
        try:
            await session.run(_CONSTRAINT_USER)
        except Exception as e:
            self._handle_graph_error(e, "create constraint for User")

        try:
            await session.run(_CONSTRAINT_ROASTER)
        except Exception as e:
            self._handle_graph_error(e, "create constraint for Roaster")

        try:
            await session.run(_CONSTRAINT_COFFEE)
        except Exception as e:
            self._handle_graph_error(e, "create constraint for Coffee")

        try:
            await session.run(_CONSTRAINT_FLAVOR_TAG)
        except Exception as e:
            self._handle_graph_error(e, "create constraint for FlavorTag")

        try:
            await session.run(_CONSTRAINT_TASTING)
        except Exception as e:
            self._handle_graph_error(e, "create constraint for TastingSession")

        logger.info("Graph constraints initialized")
