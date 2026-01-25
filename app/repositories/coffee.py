"""Coffee repository for Neo4j operations."""

from datetime import datetime, timezone
from typing import LiteralString
from uuid import uuid4

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


# --- Cypher Queries ---

_CREATE_COFFEE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
MATCH (r:Roaster {id: $roaster_id})
WHERE (u)-[:CREATED]->(r)
CREATE (c:Coffee {
    id: $id,
    name: $name,
    origin_country: $origin_country,
    origin_region: $origin_region,
    processing_method: $processing_method,
    variety: $variety,
    roast_level: $roast_level,
    description: $description,
    created_at: datetime($created_at)
})
CREATE (u)-[:CREATED]->(c)
CREATE (r)-[:ROASTS]->(c)
RETURN c.id AS id, c.name AS name, c.origin_country AS origin_country,
       c.origin_region AS origin_region, c.processing_method AS processing_method,
       c.variety AS variety, c.roast_level AS roast_level,
       c.description AS description, c.created_at AS created_at,
       r.id AS roaster_id
"""

_LINK_COFFEE_TO_FLAVOR: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})
MATCH (f:Flavor {id: $flavor_id})
MERGE (c)-[:HAS_FLAVOR]->(f)
"""

_REMOVE_COFFEE_FLAVORS: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})-[r:HAS_FLAVOR]->()
DELETE r
"""

_GET_BY_ID: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee {id: $coffee_id})
MATCH (r:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
RETURN c.id AS id, c.name AS name, c.origin_country AS origin_country,
       c.origin_region AS origin_region, c.processing_method AS processing_method,
       c.variety AS variety, c.roast_level AS roast_level,
       c.description AS description, c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       collect({id: f.id, name: f.name, category: f.category}) AS flavors
"""

_LIST_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
MATCH (r:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
WITH c, r, collect({id: f.id, name: f.name, category: f.category}) AS flavors
RETURN c.id AS id, c.name AS name, c.origin_country AS origin_country,
       c.origin_region AS origin_region, c.processing_method AS processing_method,
       c.variety AS variety, c.roast_level AS roast_level,
       c.description AS description, c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       flavors
ORDER BY c.created_at DESC
SKIP $skip LIMIT $limit
"""

_LIST_BY_ROASTER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
MATCH (r:Roaster {id: $roaster_id})-[:ROASTS]->(c)
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
WITH c, r, collect({id: f.id, name: f.name, category: f.category}) AS flavors
RETURN c.id AS id, c.name AS name, c.origin_country AS origin_country,
       c.origin_region AS origin_region, c.processing_method AS processing_method,
       c.variety AS variety, c.roast_level AS roast_level,
       c.description AS description, c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       flavors
ORDER BY c.created_at DESC
SKIP $skip LIMIT $limit
"""

_COUNT_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
RETURN count(c) AS total
"""

_COUNT_BY_ROASTER: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
MATCH (r:Roaster {id: $roaster_id})-[:ROASTS]->(c)
RETURN count(c) AS total
"""

_UPDATE_COFFEE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee {id: $coffee_id})
SET c.name = COALESCE($name, c.name),
    c.origin_country = COALESCE($origin_country, c.origin_country),
    c.origin_region = COALESCE($origin_region, c.origin_region),
    c.processing_method = COALESCE($processing_method, c.processing_method),
    c.variety = COALESCE($variety, c.variety),
    c.roast_level = COALESCE($roast_level, c.roast_level),
    c.description = COALESCE($description, c.description)
RETURN c.id AS id
"""

_DELETE_COFFEE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee {id: $coffee_id})
DETACH DELETE c
RETURN count(c) AS deleted
"""

_SEARCH_BY_NAME: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
WHERE toLower(c.name) CONTAINS toLower($query)
MATCH (r:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
WITH c, r, collect({id: f.id, name: f.name, category: f.category}) AS flavors
RETURN c.id AS id, c.name AS name, c.origin_country AS origin_country,
       c.origin_region AS origin_region, c.processing_method AS processing_method,
       c.variety AS variety, c.roast_level AS roast_level,
       c.description AS description, c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       flavors
ORDER BY c.name
SKIP $skip LIMIT $limit
"""

_SET_EMBEDDING: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})
SET c.embedding = $embedding
"""

_GET_ROASTER_NAME: LiteralString = """
MATCH (r:Roaster)-[:ROASTS]->(c:Coffee {id: $coffee_id})
RETURN r.name AS name
"""


class CoffeeRepository(GraphRepository):
    """Repository for Coffee CRUD operations in Neo4j."""

    async def _generate_and_store_embedding(
        self,
        session: AsyncSession,
        coffee_id: str,
        coffee_data: dict,
        flavor_names: list[str] | None = None,
    ) -> None:
        """Generate and store embedding for a coffee.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID
            coffee_data: Coffee properties dict
            flavor_names: Optional list of flavor names
        """
        if not embedding_service.is_configured:
            logger.debug("Skipping embedding generation - OpenAI not configured")
            return

        try:
            # Get roaster name if not in coffee_data
            roaster_name = None
            if coffee_data.get("roaster"):
                roaster_name = coffee_data["roaster"].get("name")
            else:
                result = await session.run(_GET_ROASTER_NAME, {"coffee_id": coffee_id})
                record = await result.single()
                if record:
                    roaster_name = record["name"]

            # Build text representation and generate embedding
            text = embedding_service.build_coffee_text(
                coffee_data,
                roaster_name=roaster_name,
                flavor_names=flavor_names,
            )
            embedding = await embedding_service.generate_embedding(text)

            # Store embedding on the coffee node
            await session.run(
                _SET_EMBEDDING,
                {"coffee_id": coffee_id, "embedding": embedding},
            )
            logger.debug("Stored embedding for coffee", coffee_id=coffee_id)

        except Exception as e:
            # Log but don't fail the operation - embedding is enhancement, not critical
            logger.warning(
                "Failed to generate embedding for coffee",
                coffee_id=coffee_id,
                error=str(e),
            )

    def _process_record(self, record: dict) -> dict:
        """Process a Neo4j record into a standardized dict."""
        data = dict(record)

        # Convert datetime
        if data.get("created_at"):
            data["created_at"] = data["created_at"].to_native()

        # Build roaster object
        if data.get("roaster_id"):
            data["roaster"] = {
                "id": data.pop("roaster_id"),
                "name": data.pop("roaster_name", None),
                "location": data.pop("roaster_location", None),
            }
        else:
            data["roaster"] = None

        # Filter out null flavors from the collection
        if "flavors" in data:
            data["flavors"] = [f for f in data["flavors"] if f.get("id") is not None]

        return data

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        roaster_id: str,
        name: str,
        origin_country: str | None = None,
        origin_region: str | None = None,
        processing_method: str | None = None,
        variety: str | None = None,
        roast_level: str | None = None,
        description: str | None = None,
        flavor_ids: list[str] | None = None,
    ) -> dict | None:
        """Create a new coffee with relationships.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            roaster_id: Roaster UUID as string
            name: Coffee name
            origin_country: Optional origin country
            origin_region: Optional origin region
            processing_method: Optional processing method
            variety: Optional variety
            roast_level: Optional roast level
            description: Optional description
            flavor_ids: Optional list of flavor IDs for HAS_FLAVOR relationships

        Returns:
            Created coffee dict or None on error
        """
        try:
            coffee_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            result = await session.run(
                _CREATE_COFFEE,
                {
                    "user_id": user_id,
                    "roaster_id": roaster_id,
                    "id": coffee_id,
                    "name": name,
                    "origin_country": origin_country,
                    "origin_region": origin_region,
                    "processing_method": processing_method,
                    "variety": variety,
                    "roast_level": roast_level,
                    "description": description,
                    "created_at": created_at,
                },
            )
            record = await result.single()

            if not record:
                logger.warning("Failed to create coffee - roaster not found or not owned by user")
                return None

            # Add flavor relationships and collect flavor names for embedding
            flavor_names: list[str] = []
            if flavor_ids:
                for flavor_id in flavor_ids:
                    await session.run(
                        _LINK_COFFEE_TO_FLAVOR,
                        {"coffee_id": coffee_id, "flavor_id": flavor_id},
                    )

            # Fetch the complete coffee with relationships
            coffee = await self.get_by_id(session, user_id, coffee_id)

            # Generate and store embedding
            if coffee:
                if coffee.get("flavors"):
                    flavor_names = [f["name"] for f in coffee["flavors"] if f.get("name")]
                await self._generate_and_store_embedding(
                    session, coffee_id, coffee, flavor_names=flavor_names
                )

            return coffee

        except Exception as e:
            self._handle_graph_error(e, f"create coffee {name}")
            return None

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
    ) -> dict | None:
        """Get a coffee by ID with all relationships.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            coffee_id: Coffee UUID as string

        Returns:
            Coffee dict with roaster and flavors, or None if not found
        """
        try:
            result = await session.run(
                _GET_BY_ID,
                {"user_id": user_id, "coffee_id": coffee_id},
            )
            record = await result.single()

            if record:
                return self._process_record(dict(record))
            return None

        except Exception as e:
            self._handle_graph_error(e, f"get coffee {coffee_id}")
            return None

    async def list_all(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        roaster_id: str | None = None,
    ) -> list[dict]:
        """List all coffees for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            skip: Records to skip
            limit: Max records to return
            roaster_id: Optional roaster filter

        Returns:
            List of coffee dicts
        """
        try:
            if roaster_id:
                result = await session.run(
                    _LIST_BY_ROASTER,
                    {"user_id": user_id, "roaster_id": roaster_id, "skip": skip, "limit": limit},
                )
            else:
                result = await session.run(
                    _LIST_ALL,
                    {"user_id": user_id, "skip": skip, "limit": limit},
                )

            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, "list coffees")
            return []

    async def count(
        self,
        session: AsyncSession,
        user_id: str,
        roaster_id: str | None = None,
    ) -> int:
        """Count coffees for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            roaster_id: Optional roaster filter

        Returns:
            Total count
        """
        try:
            if roaster_id:
                result = await session.run(
                    _COUNT_BY_ROASTER,
                    {"user_id": user_id, "roaster_id": roaster_id},
                )
            else:
                result = await session.run(_COUNT_ALL, {"user_id": user_id})

            record = await result.single()
            return record["total"] if record else 0

        except Exception as e:
            self._handle_graph_error(e, "count coffees")
            return 0

    async def update(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
        name: str | None = None,
        origin_country: str | None = None,
        origin_region: str | None = None,
        processing_method: str | None = None,
        variety: str | None = None,
        roast_level: str | None = None,
        description: str | None = None,
        flavor_ids: list[str] | None = None,
    ) -> dict | None:
        """Update a coffee.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            coffee_id: Coffee UUID as string
            name: Optional new name
            origin_country: Optional new origin country
            origin_region: Optional new origin region
            processing_method: Optional new processing method
            variety: Optional new variety
            roast_level: Optional new roast level
            description: Optional new description
            flavor_ids: Optional new flavor IDs (replaces existing)

        Returns:
            Updated coffee dict or None
        """
        try:
            result = await session.run(
                _UPDATE_COFFEE,
                {
                    "user_id": user_id,
                    "coffee_id": coffee_id,
                    "name": name,
                    "origin_country": origin_country,
                    "origin_region": origin_region,
                    "processing_method": processing_method,
                    "variety": variety,
                    "roast_level": roast_level,
                    "description": description,
                },
            )
            record = await result.single()

            if not record:
                return None

            # Update flavor relationships if provided
            if flavor_ids is not None:
                # Remove existing flavors
                await session.run(_REMOVE_COFFEE_FLAVORS, {"coffee_id": coffee_id})
                # Add new flavors
                for flavor_id in flavor_ids:
                    await session.run(
                        _LINK_COFFEE_TO_FLAVOR,
                        {"coffee_id": coffee_id, "flavor_id": flavor_id},
                    )

            # Fetch updated coffee
            coffee = await self.get_by_id(session, user_id, coffee_id)

            # Regenerate embedding since coffee data changed
            if coffee:
                flavor_names: list[str] = []
                if coffee.get("flavors"):
                    flavor_names = [f["name"] for f in coffee["flavors"] if f.get("name")]
                await self._generate_and_store_embedding(
                    session, coffee_id, coffee, flavor_names=flavor_names
                )

            return coffee

        except Exception as e:
            self._handle_graph_error(e, f"update coffee {coffee_id}")
            return None

    async def delete(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
    ) -> bool:
        """Delete a coffee.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            coffee_id: Coffee UUID as string

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await session.run(
                _DELETE_COFFEE,
                {"user_id": user_id, "coffee_id": coffee_id},
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0
            return deleted > 0

        except Exception as e:
            self._handle_graph_error(e, f"delete coffee {coffee_id}")
            return False

    async def search_by_name(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Search coffees by name.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            query: Search query
            skip: Records to skip
            limit: Max records

        Returns:
            List of matching coffee dicts
        """
        try:
            result = await session.run(
                _SEARCH_BY_NAME,
                {"user_id": user_id, "query": query, "skip": skip, "limit": limit},
            )
            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, f"search coffees {query}")
            return []


# Global instance
coffee_repository = CoffeeRepository()
