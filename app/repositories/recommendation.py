"""Recommendation repository for Neo4j operations."""

from typing import LiteralString

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


# --- Cypher Queries ---

_SIMILAR_COFFEES: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})-[:HAS_FLAVOR]->(f:Flavor)<-[:HAS_FLAVOR]-(similar:Coffee)
WHERE c <> similar
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(similar)
MATCH (r:Roaster)-[:ROASTS]->(similar)
WITH similar, r, count(DISTINCT f) AS shared_flavors
ORDER BY shared_flavors DESC
LIMIT $limit
OPTIONAL MATCH (similar)-[:HAS_FLAVOR]->(sf:Flavor)
RETURN similar.id AS id, similar.name AS name,
       similar.origin_country AS origin_country,
       similar.origin_region AS origin_region,
       similar.processing_method AS processing_method,
       similar.variety AS variety,
       similar.roast_level AS roast_level,
       similar.description AS description,
       similar.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       shared_flavors,
       collect({id: sf.id, name: sf.name, category: sf.category}) AS flavors
"""

_COFFEES_BY_FLAVOR: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
WHERE f.id IN $flavor_ids
MATCH (r:Roaster)-[:ROASTS]->(c)
WITH c, r, count(DISTINCT f) AS matching_flavors
ORDER BY matching_flavors DESC
LIMIT $limit
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(cf:Flavor)
RETURN c.id AS id, c.name AS name,
       c.origin_country AS origin_country,
       c.origin_region AS origin_region,
       c.processing_method AS processing_method,
       c.variety AS variety,
       c.roast_level AS roast_level,
       c.description AS description,
       c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       matching_flavors,
       collect({id: cf.id, name: cf.name, category: cf.category}) AS flavors
"""

_COFFEES_BY_FLAVOR_EXCLUDE_TASTED: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c:Coffee)
MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
WHERE f.id IN $flavor_ids
  AND NOT EXISTS((u)-[:LOGGED]->(:Tasting)-[:OF]->(c))
MATCH (r:Roaster)-[:ROASTS]->(c)
WITH c, r, count(DISTINCT f) AS matching_flavors
ORDER BY matching_flavors DESC
LIMIT $limit
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(cf:Flavor)
RETURN c.id AS id, c.name AS name,
       c.origin_country AS origin_country,
       c.origin_region AS origin_region,
       c.processing_method AS processing_method,
       c.variety AS variety,
       c.roast_level AS roast_level,
       c.description AS description,
       c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       matching_flavors,
       collect({id: cf.id, name: cf.name, category: cf.category}) AS flavors
"""

# Vector similarity search queries
_GET_COFFEE_EMBEDDING: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})
RETURN c.embedding AS embedding
"""

# Semantic search - all coffees (cross-user discovery)
_SIMILAR_COFFEES_SEMANTIC_ALL: LiteralString = """
CALL db.index.vector.queryNodes('coffee_embedding', $top_k, $embedding)
YIELD node AS similar, score
WHERE similar.id <> $source_coffee_id
MATCH (r:Roaster)-[:ROASTS]->(similar)
WITH similar, r, score
ORDER BY score DESC
LIMIT $limit
OPTIONAL MATCH (similar)-[:HAS_FLAVOR]->(f:Flavor)
OPTIONAL MATCH (creator:CoffeeDrinker)-[:CREATED]->(similar)
RETURN similar.id AS id, similar.name AS name,
       similar.origin_country AS origin_country,
       similar.origin_region AS origin_region,
       similar.processing_method AS processing_method,
       similar.variety AS variety,
       similar.roast_level AS roast_level,
       similar.description AS description,
       similar.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       score AS similarity_score,
       creator.id AS created_by,
       collect({id: f.id, name: f.name, category: f.category}) AS flavors
"""

# Semantic search - user's coffees only
_SIMILAR_COFFEES_SEMANTIC_USER: LiteralString = """
CALL db.index.vector.queryNodes('coffee_embedding', $top_k, $embedding)
YIELD node AS similar, score
WHERE similar.id <> $source_coffee_id
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(similar)
MATCH (r:Roaster)-[:ROASTS]->(similar)
WITH similar, r, score
ORDER BY score DESC
LIMIT $limit
OPTIONAL MATCH (similar)-[:HAS_FLAVOR]->(f:Flavor)
RETURN similar.id AS id, similar.name AS name,
       similar.origin_country AS origin_country,
       similar.origin_region AS origin_region,
       similar.processing_method AS processing_method,
       similar.variety AS variety,
       similar.roast_level AS roast_level,
       similar.description AS description,
       similar.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       score AS similarity_score,
       collect({id: f.id, name: f.name, category: f.category}) AS flavors
"""

_SIMILAR_FLAVORS_SEMANTIC: LiteralString = """
CALL db.index.vector.queryNodes('flavor_embedding', $top_k, $embedding)
YIELD node AS f, score
WHERE f.id <> $source_flavor_id
RETURN f.id AS id, f.name AS name, f.category AS category, score AS similarity_score
ORDER BY score DESC
LIMIT $limit
"""

_GET_FLAVOR_EMBEDDING: LiteralString = """
MATCH (f:Flavor {id: $flavor_id})
RETURN f.embedding AS embedding
"""

# Text-based semantic search (search by description/query text)
_SEARCH_COFFEES_BY_TEXT_ALL: LiteralString = """
CALL db.index.vector.queryNodes('coffee_embedding', $top_k, $embedding)
YIELD node AS c, score
MATCH (r:Roaster)-[:ROASTS]->(c)
WITH c, r, score
ORDER BY score DESC
LIMIT $limit
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
OPTIONAL MATCH (creator:CoffeeDrinker)-[:CREATED]->(c)
RETURN c.id AS id, c.name AS name,
       c.origin_country AS origin_country,
       c.origin_region AS origin_region,
       c.processing_method AS processing_method,
       c.variety AS variety,
       c.roast_level AS roast_level,
       c.description AS description,
       c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       score AS similarity_score,
       creator.id AS created_by,
       collect({id: f.id, name: f.name, category: f.category}) AS flavors
"""

_SEARCH_COFFEES_BY_TEXT_USER: LiteralString = """
CALL db.index.vector.queryNodes('coffee_embedding', $top_k, $embedding)
YIELD node AS c, score
MATCH (u:CoffeeDrinker {id: $user_id})-[:CREATED]->(c)
MATCH (r:Roaster)-[:ROASTS]->(c)
WITH c, r, score
ORDER BY score DESC
LIMIT $limit
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(f:Flavor)
RETURN c.id AS id, c.name AS name,
       c.origin_country AS origin_country,
       c.origin_region AS origin_region,
       c.processing_method AS processing_method,
       c.variety AS variety,
       c.roast_level AS roast_level,
       c.description AS description,
       c.created_at AS created_at,
       r.id AS roaster_id, r.name AS roaster_name, r.location AS roaster_location,
       score AS similarity_score,
       collect({id: f.id, name: f.name, category: f.category}) AS flavors
"""


class RecommendationRepository(GraphRepository):
    """Repository for recommendation queries in Neo4j."""

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

    async def similar_coffees(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Find coffees with similar flavor profiles.

        Args:
            session: Neo4j async session
            user_id: User ID (to scope to user's coffees)
            coffee_id: Source coffee ID
            limit: Max results to return

        Returns:
            List of coffee dicts with shared_flavors count
        """
        try:
            result = await session.run(
                _SIMILAR_COFFEES,
                {"user_id": user_id, "coffee_id": coffee_id, "limit": limit},
            )
            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, f"find similar coffees to {coffee_id}")
            return []

    async def coffees_by_flavor(
        self,
        session: AsyncSession,
        user_id: str,
        flavor_ids: list[str],
        exclude_tasted: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Find coffees matching given flavors.

        Args:
            session: Neo4j async session
            user_id: User ID
            flavor_ids: List of flavor IDs to match
            exclude_tasted: If True, exclude coffees the user has tasted
            limit: Max results to return

        Returns:
            List of coffee dicts with matching_flavors count
        """
        try:
            query = _COFFEES_BY_FLAVOR_EXCLUDE_TASTED if exclude_tasted else _COFFEES_BY_FLAVOR
            result = await session.run(
                query,
                {"user_id": user_id, "flavor_ids": flavor_ids, "limit": limit},
            )
            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, "find coffees by flavor")
            return []

    async def similar_coffees_semantic(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
        limit: int = 10,
        user_only: bool = False,
    ) -> list[dict]:
        """Find semantically similar coffees using vector embeddings.

        Uses the coffee's embedding to find coffees with similar semantic
        profiles (description, origin, flavors, etc.).

        Args:
            session: Neo4j async session
            user_id: User ID (used when user_only=True)
            coffee_id: Source coffee ID
            limit: Max results to return
            user_only: If True, only search user's coffees. Default False (all coffees).

        Returns:
            List of coffee dicts with similarity_score (0-1, higher is more similar)
        """
        try:
            # Get the source coffee's embedding
            result = await session.run(_GET_COFFEE_EMBEDDING, {"coffee_id": coffee_id})
            record = await result.single()

            if not record or not record["embedding"]:
                logger.warning("Coffee has no embedding for semantic search", coffee_id=coffee_id)
                return []

            embedding = record["embedding"]

            # Query for similar coffees
            # top_k should be higher than limit to account for filtering
            top_k = limit * 3

            if user_only:
                result = await session.run(
                    _SIMILAR_COFFEES_SEMANTIC_USER,
                    {
                        "embedding": embedding,
                        "source_coffee_id": coffee_id,
                        "user_id": user_id,
                        "top_k": top_k,
                        "limit": limit,
                    },
                )
            else:
                result = await session.run(
                    _SIMILAR_COFFEES_SEMANTIC_ALL,
                    {
                        "embedding": embedding,
                        "source_coffee_id": coffee_id,
                        "top_k": top_k,
                        "limit": limit,
                    },
                )

            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, f"find semantically similar coffees to {coffee_id}")
            return []

    async def search_coffees_by_text(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 20,
        user_only: bool = False,
    ) -> list[dict]:
        """Search coffees using natural language text.

        Converts the query text to an embedding and finds coffees with
        similar semantic profiles.

        Args:
            session: Neo4j async session
            user_id: User ID (used when user_only=True)
            query: Natural language search query (e.g., "fruity Ethiopian light roast")
            limit: Max results to return
            user_only: If True, only search user's coffees. Default False (all coffees).

        Returns:
            List of coffee dicts with similarity_score
        """
        if not embedding_service.is_configured:
            logger.warning("Cannot search by text - OpenAI not configured")
            return []

        try:
            # Generate embedding for the search query
            embedding = await embedding_service.generate_embedding(query)

            # top_k should be higher than limit to account for filtering
            top_k = limit * 3

            if user_only:
                result = await session.run(
                    _SEARCH_COFFEES_BY_TEXT_USER,
                    {
                        "embedding": embedding,
                        "user_id": user_id,
                        "top_k": top_k,
                        "limit": limit,
                    },
                )
            else:
                result = await session.run(
                    _SEARCH_COFFEES_BY_TEXT_ALL,
                    {
                        "embedding": embedding,
                        "top_k": top_k,
                        "limit": limit,
                    },
                )

            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, f"search coffees by text: {query}")
            return []

    async def similar_flavors(
        self,
        session: AsyncSession,
        flavor_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Find semantically similar flavors.

        Useful for suggesting related flavor notes (e.g., "blueberry" -> "blackberry", "raspberry").

        Args:
            session: Neo4j async session
            flavor_id: Source flavor ID
            limit: Max results to return

        Returns:
            List of flavor dicts with similarity_score
        """
        try:
            # Get the source flavor's embedding
            result = await session.run(_GET_FLAVOR_EMBEDDING, {"flavor_id": flavor_id})
            record = await result.single()

            if not record or not record["embedding"]:
                logger.warning("Flavor has no embedding for semantic search", flavor_id=flavor_id)
                return []

            embedding = record["embedding"]

            # Query for similar flavors
            top_k = limit * 2

            result = await session.run(
                _SIMILAR_FLAVORS_SEMANTIC,
                {
                    "embedding": embedding,
                    "source_flavor_id": flavor_id,
                    "top_k": top_k,
                    "limit": limit,
                },
            )

            records = await result.data()
            return records

        except Exception as e:
            self._handle_graph_error(e, f"find similar flavors to {flavor_id}")
            return []


# Global instance
recommendation_repository = RecommendationRepository()
