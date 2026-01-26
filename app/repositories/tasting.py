"""Tasting repository for Neo4j operations."""

from datetime import datetime, timezone
from typing import LiteralString
from uuid import uuid4

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.repositories.graph.base import GraphRepository

logger = get_logger(__name__)


# --- Cypher Queries ---

_CREATE_TASTING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})
MATCH (c:Coffee {id: $coffee_id})
WHERE (u)-[:CREATED]->(c)
CREATE (t:Tasting {
    id: $id,
    brew_method: $brew_method,
    grind_size: $grind_size,
    notes: $notes,
    created_at: datetime($created_at)
})
CREATE (u)-[:LOGGED]->(t)
CREATE (t)-[:OF]->(c)
RETURN t.id AS id
"""

_CREATE_RATING: LiteralString = """
MATCH (t:Tasting {id: $tasting_id})
CREATE (r:Rating {
    id: $id,
    score: $score,
    notes: $notes,
    created_at: datetime($created_at)
})
CREATE (t)-[:HAS]->(r)
RETURN r.id AS id, r.score AS score, r.notes AS notes, r.created_at AS created_at
"""

_LINK_DETECTED_FLAVOR: LiteralString = """
MATCH (t:Tasting {id: $tasting_id})
MATCH (f:Flavor {id: $flavor_id})
MERGE (t)-[d:DETECTED]->(f)
SET d.intensity = $intensity
"""

_REMOVE_DETECTED_FLAVORS: LiteralString = """
MATCH (t:Tasting {id: $tasting_id})-[r:DETECTED]->()
DELETE r
"""

_GET_BY_ID: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
MATCH (t)-[:OF]->(c:Coffee)
MATCH (ro:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (t)-[:HAS]->(r:Rating)
OPTIONAL MATCH (t)-[det:DETECTED]->(f:Flavor)
OPTIONAL MATCH (c)-[:HAS_FLAVOR]->(cf:Flavor)
WITH t, c, ro, r,
     collect(DISTINCT {id: f.id, name: f.name, category: f.category, intensity: det.intensity}) AS detected_flavors,
     collect(DISTINCT {id: cf.id, name: cf.name, category: cf.category}) AS coffee_flavors
RETURN t.id AS id, t.brew_method AS brew_method, t.grind_size AS grind_size,
       t.notes AS notes, t.created_at AS created_at,
       c.id AS coffee_id, c.name AS coffee_name, c.origin_country AS coffee_origin_country,
       c.origin_region AS coffee_origin_region, c.processing_method AS coffee_processing_method,
       c.variety AS coffee_variety, c.roast_level AS coffee_roast_level,
       c.description AS coffee_description, c.created_at AS coffee_created_at,
       ro.id AS roaster_id, ro.name AS roaster_name, ro.location AS roaster_location,
       r.id AS rating_id, r.score AS rating_score, r.notes AS rating_notes, r.created_at AS rating_created_at,
       detected_flavors, coffee_flavors
"""

_LIST_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting)
MATCH (t)-[:OF]->(c:Coffee)
MATCH (ro:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (t)-[:HAS]->(r:Rating)
OPTIONAL MATCH (t)-[det:DETECTED]->(f:Flavor)
WITH t, c, ro, r,
     collect(DISTINCT {id: f.id, name: f.name, category: f.category, intensity: det.intensity}) AS detected_flavors
RETURN t.id AS id, t.brew_method AS brew_method, t.grind_size AS grind_size,
       t.notes AS notes, t.created_at AS created_at,
       c.id AS coffee_id, c.name AS coffee_name,
       ro.id AS roaster_id, ro.name AS roaster_name,
       r.id AS rating_id, r.score AS rating_score, r.notes AS rating_notes, r.created_at AS rating_created_at,
       detected_flavors
ORDER BY t.created_at DESC
SKIP $skip LIMIT $limit
"""

_LIST_BY_COFFEE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting)
MATCH (t)-[:OF]->(c:Coffee {id: $coffee_id})
MATCH (ro:Roaster)-[:ROASTS]->(c)
OPTIONAL MATCH (t)-[:HAS]->(r:Rating)
OPTIONAL MATCH (t)-[det:DETECTED]->(f:Flavor)
WITH t, c, ro, r,
     collect(DISTINCT {id: f.id, name: f.name, category: f.category, intensity: det.intensity}) AS detected_flavors
RETURN t.id AS id, t.brew_method AS brew_method, t.grind_size AS grind_size,
       t.notes AS notes, t.created_at AS created_at,
       c.id AS coffee_id, c.name AS coffee_name,
       ro.id AS roaster_id, ro.name AS roaster_name,
       r.id AS rating_id, r.score AS rating_score, r.notes AS rating_notes, r.created_at AS rating_created_at,
       detected_flavors
ORDER BY t.created_at DESC
SKIP $skip LIMIT $limit
"""

_COUNT_ALL: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting)
RETURN count(t) AS total
"""

_COUNT_BY_COFFEE: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting)
MATCH (t)-[:OF]->(c:Coffee {id: $coffee_id})
RETURN count(t) AS total
"""

_UPDATE_TASTING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
SET t.brew_method = COALESCE($brew_method, t.brew_method),
    t.grind_size = COALESCE($grind_size, t.grind_size),
    t.notes = COALESCE($notes, t.notes)
RETURN t.id AS id
"""

_DELETE_TASTING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
OPTIONAL MATCH (t)-[:HAS]->(r:Rating)
DETACH DELETE t, r
RETURN count(t) AS deleted
"""

_GET_RATING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
MATCH (t)-[:HAS]->(r:Rating)
RETURN r.id AS id, r.score AS score, r.notes AS notes, r.created_at AS created_at
"""

_UPDATE_RATING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
MATCH (t)-[:HAS]->(r:Rating)
SET r.score = COALESCE($score, r.score),
    r.notes = COALESCE($notes, r.notes)
RETURN r.id AS id, r.score AS score, r.notes AS notes, r.created_at AS created_at
"""

_DELETE_RATING: LiteralString = """
MATCH (u:CoffeeDrinker {id: $user_id})-[:LOGGED]->(t:Tasting {id: $tasting_id})
MATCH (t)-[:HAS]->(r:Rating)
DETACH DELETE r
RETURN count(r) AS deleted
"""


class TastingRepository(GraphRepository):
    """Repository for Tasting CRUD operations in Neo4j."""

    def _process_record(self, record: dict, include_full_coffee: bool = False) -> dict:
        """Process a Neo4j record into a standardized dict."""
        data = dict(record)

        # Convert datetimes
        if data.get("created_at"):
            data["created_at"] = data["created_at"].to_native()

        # Build coffee object
        if data.get("coffee_id"):
            coffee = {
                "id": data.pop("coffee_id"),
                "name": data.pop("coffee_name", None),
            }
            if include_full_coffee:
                coffee.update({
                    "origin_country": data.pop("coffee_origin_country", None),
                    "origin_region": data.pop("coffee_origin_region", None),
                    "processing_method": data.pop("coffee_processing_method", None),
                    "variety": data.pop("coffee_variety", None),
                    "roast_level": data.pop("coffee_roast_level", None),
                    "description": data.pop("coffee_description", None),
                    "created_at": data.pop("coffee_created_at", None),
                    "flavors": data.pop("coffee_flavors", []),
                })
                if coffee.get("created_at"):
                    coffee["created_at"] = coffee["created_at"].to_native()
                # Filter null flavors
                coffee["flavors"] = [f for f in coffee.get("flavors", []) if f.get("id")]

            # Add roaster
            if data.get("roaster_id"):
                coffee["roaster"] = {
                    "id": data.pop("roaster_id"),
                    "name": data.pop("roaster_name", None),
                    "location": data.pop("roaster_location", None),
                }
            data["coffee"] = coffee

        # Build rating object
        if data.get("rating_id"):
            data["rating"] = {
                "id": data.pop("rating_id"),
                "score": data.pop("rating_score"),
                "notes": data.pop("rating_notes", None),
                "created_at": data.pop("rating_created_at"),
            }
            if data["rating"]["created_at"]:
                data["rating"]["created_at"] = data["rating"]["created_at"].to_native()
        else:
            data.pop("rating_id", None)
            data.pop("rating_score", None)
            data.pop("rating_notes", None)
            data.pop("rating_created_at", None)
            data["rating"] = None

        # Filter null detected flavors
        if "detected_flavors" in data:
            data["detected_flavors"] = [
                {"flavor": {"id": f["id"], "name": f["name"], "category": f.get("category")}, "intensity": f["intensity"]}
                for f in data["detected_flavors"]
                if f.get("id") is not None
            ]

        return data

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str,
        brew_method: str | None = None,
        grind_size: str | None = None,
        notes: str | None = None,
        detected_flavors: list[dict] | None = None,
        rating: dict | None = None,
    ) -> dict | None:
        """Create a new tasting with optional rating and detected flavors.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            coffee_id: Coffee UUID as string
            brew_method: Optional brewing method
            grind_size: Optional grind size
            notes: Optional tasting notes
            detected_flavors: Optional list of {flavor_id, intensity} dicts
            rating: Optional {score, notes} dict

        Returns:
            Created tasting dict or None on error
        """
        try:
            tasting_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            result = await session.run(
                _CREATE_TASTING,
                {
                    "user_id": user_id,
                    "coffee_id": coffee_id,
                    "id": tasting_id,
                    "brew_method": brew_method,
                    "grind_size": grind_size,
                    "notes": notes,
                    "created_at": created_at,
                },
            )
            record = await result.single()

            if not record:
                logger.warning("Failed to create tasting - coffee not found or not owned by user")
                return None

            # Add detected flavor relationships
            if detected_flavors:
                for df in detected_flavors:
                    await session.run(
                        _LINK_DETECTED_FLAVOR,
                        {
                            "tasting_id": tasting_id,
                            "flavor_id": df["flavor_id"],
                            "intensity": df["intensity"],
                        },
                    )

            # Create rating if provided
            if rating:
                rating_id = str(uuid4())
                await session.run(
                    _CREATE_RATING,
                    {
                        "tasting_id": tasting_id,
                        "id": rating_id,
                        "score": rating["score"],
                        "notes": rating.get("notes"),
                        "created_at": created_at,
                    },
                )

            # Fetch complete tasting
            return await self.get_by_id(session, user_id, tasting_id)

        except Exception as e:
            self._handle_graph_error(e, "create tasting")
            return None

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
    ) -> dict | None:
        """Get a tasting by ID with all relationships.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string

        Returns:
            Tasting dict or None if not found
        """
        try:
            result = await session.run(
                _GET_BY_ID,
                {"user_id": user_id, "tasting_id": tasting_id},
            )
            record = await result.single()

            if record:
                return self._process_record(dict(record), include_full_coffee=True)
            return None

        except Exception as e:
            self._handle_graph_error(e, f"get tasting {tasting_id}")
            return None

    async def list_all(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        coffee_id: str | None = None,
    ) -> list[dict]:
        """List all tastings for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            skip: Records to skip
            limit: Max records to return
            coffee_id: Optional coffee filter

        Returns:
            List of tasting dicts
        """
        try:
            if coffee_id:
                result = await session.run(
                    _LIST_BY_COFFEE,
                    {"user_id": user_id, "coffee_id": coffee_id, "skip": skip, "limit": limit},
                )
            else:
                result = await session.run(
                    _LIST_ALL,
                    {"user_id": user_id, "skip": skip, "limit": limit},
                )

            records = await result.data()
            return [self._process_record(r) for r in records]

        except Exception as e:
            self._handle_graph_error(e, "list tastings")
            return []

    async def count(
        self,
        session: AsyncSession,
        user_id: str,
        coffee_id: str | None = None,
    ) -> int:
        """Count tastings for a user.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            coffee_id: Optional coffee filter

        Returns:
            Total count
        """
        try:
            if coffee_id:
                result = await session.run(
                    _COUNT_BY_COFFEE,
                    {"user_id": user_id, "coffee_id": coffee_id},
                )
            else:
                result = await session.run(_COUNT_ALL, {"user_id": user_id})

            record = await result.single()
            return record["total"] if record else 0

        except Exception as e:
            self._handle_graph_error(e, "count tastings")
            return 0

    async def update(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
        brew_method: str | None = None,
        grind_size: str | None = None,
        notes: str | None = None,
        detected_flavors: list[dict] | None = None,
    ) -> dict | None:
        """Update a tasting.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string
            brew_method: Optional new brew method
            grind_size: Optional new grind size
            notes: Optional new notes
            detected_flavors: Optional new detected flavors (replaces existing)

        Returns:
            Updated tasting dict or None
        """
        try:
            result = await session.run(
                _UPDATE_TASTING,
                {
                    "user_id": user_id,
                    "tasting_id": tasting_id,
                    "brew_method": brew_method,
                    "grind_size": grind_size,
                    "notes": notes,
                },
            )
            record = await result.single()

            if not record:
                return None

            # Update detected flavors if provided
            if detected_flavors is not None:
                await session.run(_REMOVE_DETECTED_FLAVORS, {"tasting_id": tasting_id})
                for df in detected_flavors:
                    await session.run(
                        _LINK_DETECTED_FLAVOR,
                        {
                            "tasting_id": tasting_id,
                            "flavor_id": df["flavor_id"],
                            "intensity": df["intensity"],
                        },
                    )

            return await self.get_by_id(session, user_id, tasting_id)

        except Exception as e:
            self._handle_graph_error(e, f"update tasting {tasting_id}")
            return None

    async def delete(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
    ) -> bool:
        """Delete a tasting and its rating.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await session.run(
                _DELETE_TASTING,
                {"user_id": user_id, "tasting_id": tasting_id},
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0
            return deleted > 0

        except Exception as e:
            self._handle_graph_error(e, f"delete tasting {tasting_id}")
            return False

    # --- Rating Methods ---

    async def create_rating(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
        score: int,
        notes: str | None = None,
    ) -> dict | None:
        """Create a rating for a tasting.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string
            score: Rating score (1-5)
            notes: Optional rating notes

        Returns:
            Rating dict or None on error
        """
        try:
            # Verify tasting exists and belongs to user
            tasting = await self.get_by_id(session, user_id, tasting_id)
            if not tasting:
                return None

            # Check if rating already exists
            if tasting.get("rating"):
                logger.warning("Rating already exists for tasting")
                return None

            rating_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            result = await session.run(
                _CREATE_RATING,
                {
                    "tasting_id": tasting_id,
                    "id": rating_id,
                    "score": score,
                    "notes": notes,
                    "created_at": created_at,
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
            self._handle_graph_error(e, f"create rating for tasting {tasting_id}")
            return None

    async def get_rating(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
    ) -> dict | None:
        """Get a rating for a tasting.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string

        Returns:
            Rating dict or None if not found
        """
        try:
            result = await session.run(
                _GET_RATING,
                {"user_id": user_id, "tasting_id": tasting_id},
            )
            record = await result.single()

            if record:
                data = dict(record)
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].to_native()
                return data
            return None

        except Exception as e:
            self._handle_graph_error(e, f"get rating for tasting {tasting_id}")
            return None

    async def update_rating(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
        score: int | None = None,
        notes: str | None = None,
    ) -> dict | None:
        """Update a rating.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string
            score: Optional new score
            notes: Optional new notes

        Returns:
            Updated rating dict or None
        """
        try:
            result = await session.run(
                _UPDATE_RATING,
                {
                    "user_id": user_id,
                    "tasting_id": tasting_id,
                    "score": score,
                    "notes": notes,
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
            self._handle_graph_error(e, f"update rating for tasting {tasting_id}")
            return None

    async def delete_rating(
        self,
        session: AsyncSession,
        user_id: str,
        tasting_id: str,
    ) -> bool:
        """Delete a rating.

        Args:
            session: Neo4j async session
            user_id: Owner's user ID
            tasting_id: Tasting UUID as string

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await session.run(
                _DELETE_RATING,
                {"user_id": user_id, "tasting_id": tasting_id},
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0
            return deleted > 0

        except Exception as e:
            self._handle_graph_error(e, f"delete rating for tasting {tasting_id}")
            return False


# Global instance
tasting_repository = TastingRepository()
