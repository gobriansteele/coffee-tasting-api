"""User repository for Neo4j operations."""

from typing import LiteralString

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository

logger = get_logger(__name__)


# --- Cypher Queries ---

_GET_USER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
RETURN u.id AS id, u.email AS email, u.first_name AS first_name,
       u.last_name AS last_name, u.display_name AS display_name
"""

_UPDATE_USER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
SET u.email = COALESCE($email, u.email),
    u.first_name = COALESCE($first_name, u.first_name),
    u.last_name = COALESCE($last_name, u.last_name),
    u.display_name = COALESCE($display_name, u.display_name)
RETURN u.id AS id, u.email AS email, u.first_name AS first_name,
       u.last_name AS last_name, u.display_name AS display_name
"""

_GET_FLAVOR_PROFILE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting)-[d:DETECTED]->(f:Flavor)
WITH f, count(d) AS detection_count, avg(d.intensity) AS avg_intensity
RETURN f.id AS id, f.name AS name, f.category AS category,
       detection_count, avg_intensity
ORDER BY detection_count DESC, avg_intensity DESC
LIMIT $limit
"""

_GET_USER_STATS: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
OPTIONAL MATCH (u)-[:CREATED]->(r:Roaster)
OPTIONAL MATCH (u)-[:CREATED]->(c:Coffee)
OPTIONAL MATCH (u)-[:LOGGED]->(t:Tasting)
RETURN count(DISTINCT r) AS roaster_count,
       count(DISTINCT c) AS coffee_count,
       count(DISTINCT t) AS tasting_count
"""


class UserRepository(GraphRepository):
    """Repository for User/CoffeeDrinker operations in Neo4j."""

    async def get_profile(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> dict | None:
        """Get user profile.

        Args:
            session: Neo4j async session
            user_id: User ID

        Returns:
            User profile dict or None if not found
        """
        try:
            result = await session.run(_GET_USER, {"user_id": user_id})
            record = await result.single()

            if record:
                return dict(record)
            return None

        except Exception as e:
            self._handle_graph_error(e, f"get user {user_id}")
            return None

    async def update_profile(
        self,
        session: AsyncSession,
        user_id: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
    ) -> dict | None:
        """Update user profile.

        Args:
            session: Neo4j async session
            user_id: User ID
            email: Optional email
            first_name: Optional first name
            last_name: Optional last name
            display_name: Optional display name

        Returns:
            Updated user profile dict or None
        """
        try:
            result = await session.run(
                _UPDATE_USER,
                {
                    "user_id": user_id,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": display_name,
                },
            )
            record = await result.single()

            if record:
                return dict(record)
            return None

        except Exception as e:
            self._handle_graph_error(e, f"update user {user_id}")
            return None

    async def get_flavor_profile(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Get user's flavor profile based on detected flavors.

        Aggregates all flavors the user has detected across tastings,
        returning the most frequently detected flavors with average intensity.

        Args:
            session: Neo4j async session
            user_id: User ID
            limit: Max flavors to return

        Returns:
            List of flavor dicts with detection_count and avg_intensity
        """
        try:
            result = await session.run(
                _GET_FLAVOR_PROFILE,
                {"user_id": user_id, "limit": limit},
            )
            records = await result.data()
            return records

        except Exception as e:
            self._handle_graph_error(e, f"get flavor profile for {user_id}")
            return []

    async def get_stats(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> dict:
        """Get user statistics.

        Args:
            session: Neo4j async session
            user_id: User ID

        Returns:
            Dict with roaster_count, coffee_count, tasting_count
        """
        try:
            result = await session.run(_GET_USER_STATS, {"user_id": user_id})
            record = await result.single()

            if record:
                return dict(record)
            return {"roaster_count": 0, "coffee_count": 0, "tasting_count": 0}

        except Exception as e:
            self._handle_graph_error(e, f"get stats for {user_id}")
            return {"roaster_count": 0, "coffee_count": 0, "tasting_count": 0}


# Global instance
user_repository = UserRepository()
