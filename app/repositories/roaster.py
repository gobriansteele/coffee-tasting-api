"""Roaster repository for Neo4j operations."""

from datetime import datetime, timezone
from typing import LiteralString
from uuid import uuid4

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository

logger = get_logger(__name__)


# --- Cypher Queries ---

_CREATE_ROASTER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
CREATE (r:Roaster {
    id: $id,
    name: $name,
    location: $location,
    website: $website,
    description: $description,
    created_at: datetime($created_at)
})
CREATE (u)-[:CREATED]->(r)
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
"""

_GET_BY_ID: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster {id: $roaster_id})
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
"""

_GET_BY_NAME: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster {name: $name})
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
"""

_LIST_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster)
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
ORDER BY r.created_at DESC
SKIP $skip LIMIT $limit
"""

_COUNT_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster)
RETURN count(r) AS total
"""

_UPDATE_ROASTER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster {id: $roaster_id})
SET r.name = COALESCE($name, r.name),
    r.location = COALESCE($location, r.location),
    r.website = COALESCE($website, r.website),
    r.description = COALESCE($description, r.description)
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
"""

_DELETE_ROASTER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster {id: $roaster_id})
DETACH DELETE r
RETURN count(r) AS deleted
"""

_SEARCH_BY_NAME: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(r:Roaster)
WHERE toLower(r.name) CONTAINS toLower($query)
RETURN r.id AS id, r.name AS name, r.location AS location,
       r.website AS website, r.description AS description,
       r.created_at AS created_at
ORDER BY r.name
SKIP $skip LIMIT $limit
"""


class RoasterRepository(GraphRepository):
    """Repository for Roaster CRUD operations in Neo4j."""

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        name: str,
        location: str | None = None,
        website: str | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Create a new roaster.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            name: Roaster name
            location: Optional location
            website: Optional website URL
            description: Optional description

        Returns:
            Created roaster dict or None on error
        """
        try:
            roaster_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            result = await session.run(
                _CREATE_ROASTER,
                {
                    "user_id": user_id,
                    "id": roaster_id,
                    "name": name,
                    "location": location,
                    "website": website,
                    "description": description,
                    "created_at": created_at,
                },
            )
            record = await result.single()
            if record:
                data = dict(record)
                # Convert Neo4j datetime to Python datetime if needed
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].to_native()
                return data
            return None
        except Exception as e:
            self._handle_graph_error(e, f"create roaster {name}")
            return None

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: str,
        roaster_id: str,
    ) -> dict | None:
        """Get a roaster by ID (owned by user).

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            roaster_id: Roaster UUID as string

        Returns:
            Roaster dict or None if not found
        """
        try:
            result = await session.run(
                _GET_BY_ID,
                {"user_id": user_id, "roaster_id": roaster_id},
            )
            record = await result.single()
            if record:
                data = dict(record)
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].to_native()
                return data
            return None
        except Exception as e:
            self._handle_graph_error(e, f"get roaster {roaster_id}")
            return None

    async def get_by_name(
        self,
        session: AsyncSession,
        user_id: str,
        name: str,
    ) -> dict | None:
        """Get a roaster by name (owned by user).

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            name: Roaster name

        Returns:
            Roaster dict or None if not found
        """
        try:
            result = await session.run(
                _GET_BY_NAME,
                {"user_id": user_id, "name": name},
            )
            record = await result.single()
            if record:
                data = dict(record)
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].to_native()
                return data
            return None
        except Exception as e:
            self._handle_graph_error(e, f"get roaster by name {name}")
            return None

    async def list_all(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """List all roasters for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            skip: Records to skip
            limit: Max records to return

        Returns:
            List of roaster dicts
        """
        try:
            result = await session.run(
                _LIST_ALL,
                {"user_id": user_id, "skip": skip, "limit": limit},
            )
            records = await result.data()
            # Convert datetimes
            for record in records:
                if record.get("created_at"):
                    record["created_at"] = record["created_at"].to_native()
            return records
        except Exception as e:
            self._handle_graph_error(e, "list roasters")
            return []

    async def count(self, session: AsyncSession, user_id: str) -> int:
        """Count roasters for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID

        Returns:
            Total count
        """
        try:
            result = await session.run(_COUNT_ALL, {"user_id": user_id})
            record = await result.single()
            return record["total"] if record else 0
        except Exception as e:
            self._handle_graph_error(e, "count roasters")
            return 0

    async def update(
        self,
        session: AsyncSession,
        user_id: str,
        roaster_id: str,
        name: str | None = None,
        location: str | None = None,
        website: str | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Update a roaster.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            roaster_id: Roaster UUID as string
            name: Optional new name
            location: Optional new location
            website: Optional new website
            description: Optional new description

        Returns:
            Updated roaster dict or None
        """
        try:
            result = await session.run(
                _UPDATE_ROASTER,
                {
                    "user_id": user_id,
                    "roaster_id": roaster_id,
                    "name": name,
                    "location": location,
                    "website": website,
                    "description": description,
                },
            )
            record = await result.single()
            if record:
                data = dict(record)
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].to_native()
                return data
            return None
        except Exception as e:
            self._handle_graph_error(e, f"update roaster {roaster_id}")
            return None

    async def delete(
        self,
        session: AsyncSession,
        user_id: str,
        roaster_id: str,
    ) -> bool:
        """Delete a roaster.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            roaster_id: Roaster UUID as string

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await session.run(
                _DELETE_ROASTER,
                {"user_id": user_id, "roaster_id": roaster_id},
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0
            return deleted > 0
        except Exception as e:
            self._handle_graph_error(e, f"delete roaster {roaster_id}")
            return False

    async def search_by_name(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Search roasters by name.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            query: Search query
            skip: Records to skip
            limit: Max records

        Returns:
            List of matching roaster dicts
        """
        try:
            result = await session.run(
                _SEARCH_BY_NAME,
                {"user_id": user_id, "query": query, "skip": skip, "limit": limit},
            )
            records = await result.data()
            for record in records:
                if record.get("created_at"):
                    record["created_at"] = record["created_at"].to_native()
            return records
        except Exception as e:
            self._handle_graph_error(e, f"search roasters {query}")
            return []


# Global instance
roaster_repository = RoasterRepository()
