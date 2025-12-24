"""Graph sync repository for upserting nodes and relationships to Neo4j."""

from typing import LiteralString

from neo4j import AsyncSession

from app.core.logging import get_logger
from app.models.coffee import Coffee, FlavorTag, Roaster
from app.models.tasting import TastingSession

from .base import GraphRepository

logger = get_logger(__name__)

# --- Node Upsert Queries ---

_UPSERT_USER: LiteralString = """
MERGE (u:User {id: $id})
"""

_UPSERT_ROASTER: LiteralString = """
MERGE (r:Roaster {id: $id})
SET r.name = $name,
    r.location = $location,
    r.website = $website,
    r.description = $description
"""

_UPSERT_COFFEE: LiteralString = """
MERGE (c:Coffee {id: $id})
SET c.name = $name,
    c.origin_country = $origin_country,
    c.origin_region = $origin_region,
    c.variety = $variety,
    c.processing_method = $processing_method,
    c.roast_level = $roast_level
"""

_UPSERT_FLAVOR_TAG: LiteralString = """
MERGE (f:FlavorTag {id: $id})
SET f.name = $name,
    f.category = $category
"""

_UPSERT_TASTING_SESSION: LiteralString = """
MERGE (t:TastingSession {id: $id})
SET t.overall_rating = $overall_rating,
    t.brew_method = $brew_method,
    t.would_buy_again = $would_buy_again,
    t.created_at = $created_at
"""

# --- Embedding Upsert Queries ---

_UPSERT_COFFEE_EMBEDDING: LiteralString = """
MATCH (c:Coffee {id: $id})
SET c.embedding = $embedding
"""

_UPSERT_FLAVOR_TAG_EMBEDDING: LiteralString = """
MATCH (f:FlavorTag {id: $id})
SET f.embedding = $embedding
"""

# --- Relationship Queries ---

_LINK_ROASTER_PRODUCES_COFFEE: LiteralString = """
MATCH (r:Roaster {id: $roaster_id})
MATCH (c:Coffee {id: $coffee_id})
MERGE (r)-[:PRODUCES]->(c)
"""

_LINK_COFFEE_HAS_FLAVOR: LiteralString = """
MATCH (c:Coffee {id: $coffee_id})
MATCH (f:FlavorTag {id: $flavor_tag_id})
MERGE (c)-[:HAS_FLAVOR]->(f)
"""

_LINK_USER_CREATED_ROASTER: LiteralString = """
MATCH (u:User {id: $user_id})
MATCH (r:Roaster {id: $roaster_id})
MERGE (u)-[:CREATED]->(r)
"""

_LINK_USER_CREATED_COFFEE: LiteralString = """
MATCH (u:User {id: $user_id})
MATCH (c:Coffee {id: $coffee_id})
MERGE (u)-[:CREATED]->(c)
"""

_LINK_TASTING_FOR_COFFEE: LiteralString = """
MATCH (t:TastingSession {id: $tasting_id})
MATCH (c:Coffee {id: $coffee_id})
MERGE (t)-[:FOR_COFFEE]->(c)
"""

_LINK_TASTING_BY_USER: LiteralString = """
MATCH (t:TastingSession {id: $tasting_id})
MATCH (u:User {id: $user_id})
MERGE (t)-[:BY_USER]->(u)
"""

_LINK_TASTING_DETECTED_FLAVOR: LiteralString = """
MATCH (t:TastingSession {id: $tasting_id})
MATCH (f:FlavorTag {id: $flavor_tag_id})
MERGE (t)-[d:DETECTED]->(f)
SET d.intensity = $intensity
"""

_LINK_USER_TASTED_COFFEE: LiteralString = """
MATCH (u:User {id: $user_id})
MATCH (c:Coffee {id: $coffee_id})
MERGE (u)-[t:TASTED]->(c)
SET t.rating = $rating,
    t.date = $date
"""

# --- Delete Queries ---

_DELETE_USER: LiteralString = """
MATCH (u:User {id: $id}) DETACH DELETE u
"""

_DELETE_ROASTER: LiteralString = """
MATCH (r:Roaster {id: $id}) DETACH DELETE r
"""

_DELETE_COFFEE: LiteralString = """
MATCH (c:Coffee {id: $id}) DETACH DELETE c
"""

_DELETE_FLAVOR_TAG: LiteralString = """
MATCH (f:FlavorTag {id: $id}) DETACH DELETE f
"""

_DELETE_TASTING_SESSION: LiteralString = """
MATCH (t:TastingSession {id: $id}) DETACH DELETE t
"""


class GraphSyncRepository(GraphRepository):
    """Repository for syncing PostgreSQL data to Neo4j graph.

    All operations use MERGE for idempotency - safe to call multiple times.
    Errors are logged but don't raise (graceful degradation).
    """

    async def upsert_user(self, session: AsyncSession, user_id: str) -> None:
        """Upsert a User node.

        Args:
            session: Neo4j async session
            user_id: Supabase auth user ID
        """
        try:
            await session.run(_UPSERT_USER, {"id": user_id})
            logger.debug("Upserted user node", user_id=user_id)
        except Exception as e:
            self._handle_graph_error(e, f"upsert user {user_id}")

    async def upsert_roaster(self, session: AsyncSession, roaster: Roaster) -> None:
        """Upsert a Roaster node.

        Args:
            session: Neo4j async session
            roaster: Roaster model instance
        """
        try:
            await session.run(
                _UPSERT_ROASTER,
                {
                    "id": str(roaster.id),
                    "name": roaster.name,
                    "location": roaster.location,
                    "website": roaster.website,
                    "description": roaster.description,
                },
            )
            logger.debug("Upserted roaster node", roaster_id=str(roaster.id), name=roaster.name)
        except Exception as e:
            self._handle_graph_error(e, f"upsert roaster {roaster.id}")

    async def upsert_coffee(self, session: AsyncSession, coffee: Coffee) -> None:
        """Upsert a Coffee node.

        Args:
            session: Neo4j async session
            coffee: Coffee model instance
        """
        try:
            await session.run(
                _UPSERT_COFFEE,
                {
                    "id": str(coffee.id),
                    "name": coffee.name,
                    "origin_country": coffee.origin_country,
                    "origin_region": coffee.origin_region,
                    "variety": coffee.variety,
                    "processing_method": coffee.processing_method.value if coffee.processing_method else None,
                    "roast_level": coffee.roast_level.value if coffee.roast_level else None,
                },
            )
            logger.debug("Upserted coffee node", coffee_id=str(coffee.id), name=coffee.name)
        except Exception as e:
            self._handle_graph_error(e, f"upsert coffee {coffee.id}")

    async def upsert_flavor_tag(self, session: AsyncSession, tag: FlavorTag) -> None:
        """Upsert a FlavorTag node.

        Args:
            session: Neo4j async session
            tag: FlavorTag model instance
        """
        try:
            await session.run(
                _UPSERT_FLAVOR_TAG,
                {
                    "id": str(tag.id),
                    "name": tag.name,
                    "category": tag.category,
                },
            )
            logger.debug("Upserted flavor tag node", tag_id=str(tag.id), name=tag.name)
        except Exception as e:
            self._handle_graph_error(e, f"upsert flavor tag {tag.id}")

    async def upsert_tasting_session(self, session: AsyncSession, tasting: TastingSession) -> None:
        """Upsert a TastingSession node.

        Args:
            session: Neo4j async session
            tasting: TastingSession model instance
        """
        try:
            await session.run(
                _UPSERT_TASTING_SESSION,
                {
                    "id": str(tasting.id),
                    "overall_rating": tasting.overall_rating,
                    "brew_method": tasting.brew_method.value if tasting.brew_method else None,
                    "would_buy_again": tasting.would_buy_again,
                    "created_at": tasting.created_at.isoformat() if tasting.created_at else None,
                },
            )
            logger.debug("Upserted tasting session node", tasting_id=str(tasting.id))
        except Exception as e:
            self._handle_graph_error(e, f"upsert tasting session {tasting.id}")

    # --- Embedding Methods ---

    async def upsert_coffee_embedding(
        self, session: AsyncSession, coffee_id: str, embedding: list[float]
    ) -> None:
        """Update a Coffee node's embedding vector.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID as string
            embedding: Embedding vector (1536 dimensions for text-embedding-3-small)
        """
        try:
            await session.run(
                _UPSERT_COFFEE_EMBEDDING,
                {"id": coffee_id, "embedding": embedding},
            )
            logger.debug("Upserted coffee embedding", coffee_id=coffee_id)
        except Exception as e:
            self._handle_graph_error(e, f"upsert coffee embedding {coffee_id}")

    async def upsert_flavor_tag_embedding(
        self, session: AsyncSession, flavor_tag_id: str, embedding: list[float]
    ) -> None:
        """Update a FlavorTag node's embedding vector.

        Args:
            session: Neo4j async session
            flavor_tag_id: FlavorTag UUID as string
            embedding: Embedding vector (1536 dimensions for text-embedding-3-small)
        """
        try:
            await session.run(
                _UPSERT_FLAVOR_TAG_EMBEDDING,
                {"id": flavor_tag_id, "embedding": embedding},
            )
            logger.debug("Upserted flavor tag embedding", flavor_tag_id=flavor_tag_id)
        except Exception as e:
            self._handle_graph_error(e, f"upsert flavor tag embedding {flavor_tag_id}")

    # --- Relationship Methods ---

    async def link_coffee_to_roaster(
        self, session: AsyncSession, coffee_id: str, roaster_id: str
    ) -> None:
        """Create PRODUCES relationship between Roaster and Coffee.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID as string
            roaster_id: Roaster UUID as string
        """
        try:
            await session.run(
                _LINK_ROASTER_PRODUCES_COFFEE,
                {"coffee_id": coffee_id, "roaster_id": roaster_id},
            )
            logger.debug("Linked roaster to coffee", roaster_id=roaster_id, coffee_id=coffee_id)
        except Exception as e:
            self._handle_graph_error(e, f"link roaster {roaster_id} to coffee {coffee_id}")

    async def link_coffee_to_flavor(
        self, session: AsyncSession, coffee_id: str, flavor_tag_id: str
    ) -> None:
        """Create HAS_FLAVOR relationship between Coffee and FlavorTag.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID as string
            flavor_tag_id: FlavorTag UUID as string
        """
        try:
            await session.run(
                _LINK_COFFEE_HAS_FLAVOR,
                {"coffee_id": coffee_id, "flavor_tag_id": flavor_tag_id},
            )
            logger.debug("Linked coffee to flavor", coffee_id=coffee_id, flavor_tag_id=flavor_tag_id)
        except Exception as e:
            self._handle_graph_error(e, f"link coffee {coffee_id} to flavor {flavor_tag_id}")

    async def link_coffee_to_flavors(
        self, session: AsyncSession, coffee_id: str, flavor_tag_ids: list[str]
    ) -> None:
        """Create HAS_FLAVOR relationships between Coffee and multiple FlavorTags.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID as string
            flavor_tag_ids: List of FlavorTag UUIDs as strings
        """
        for flavor_tag_id in flavor_tag_ids:
            await self.link_coffee_to_flavor(session, coffee_id, flavor_tag_id)

    async def link_user_created_roaster(
        self, session: AsyncSession, user_id: str, roaster_id: str
    ) -> None:
        """Create CREATED relationship between User and Roaster.

        Args:
            session: Neo4j async session
            user_id: Supabase auth user ID
            roaster_id: Roaster UUID as string
        """
        try:
            await session.run(
                _LINK_USER_CREATED_ROASTER,
                {"user_id": user_id, "roaster_id": roaster_id},
            )
            logger.debug("Linked user created roaster", user_id=user_id, roaster_id=roaster_id)
        except Exception as e:
            self._handle_graph_error(e, f"link user {user_id} created roaster {roaster_id}")

    async def link_user_created_coffee(
        self, session: AsyncSession, user_id: str, coffee_id: str
    ) -> None:
        """Create CREATED relationship between User and Coffee.

        Args:
            session: Neo4j async session
            user_id: Supabase auth user ID
            coffee_id: Coffee UUID as string
        """
        try:
            await session.run(
                _LINK_USER_CREATED_COFFEE,
                {"user_id": user_id, "coffee_id": coffee_id},
            )
            logger.debug("Linked user created coffee", user_id=user_id, coffee_id=coffee_id)
        except Exception as e:
            self._handle_graph_error(e, f"link user {user_id} created coffee {coffee_id}")

    async def link_tasting_to_coffee(
        self, session: AsyncSession, tasting_id: str, coffee_id: str
    ) -> None:
        """Create FOR_COFFEE relationship between TastingSession and Coffee.

        Args:
            session: Neo4j async session
            tasting_id: TastingSession UUID as string
            coffee_id: Coffee UUID as string
        """
        try:
            await session.run(
                _LINK_TASTING_FOR_COFFEE,
                {"tasting_id": tasting_id, "coffee_id": coffee_id},
            )
            logger.debug("Linked tasting to coffee", tasting_id=tasting_id, coffee_id=coffee_id)
        except Exception as e:
            self._handle_graph_error(e, f"link tasting {tasting_id} to coffee {coffee_id}")

    async def link_tasting_to_user(
        self, session: AsyncSession, tasting_id: str, user_id: str
    ) -> None:
        """Create BY_USER relationship between TastingSession and User.

        Args:
            session: Neo4j async session
            tasting_id: TastingSession UUID as string
            user_id: Supabase auth user ID
        """
        try:
            await session.run(
                _LINK_TASTING_BY_USER,
                {"tasting_id": tasting_id, "user_id": user_id},
            )
            logger.debug("Linked tasting to user", tasting_id=tasting_id, user_id=user_id)
        except Exception as e:
            self._handle_graph_error(e, f"link tasting {tasting_id} to user {user_id}")

    async def link_tasting_detected_flavor(
        self, session: AsyncSession, tasting_id: str, flavor_tag_id: str, intensity: int | None
    ) -> None:
        """Create DETECTED relationship between TastingSession and FlavorTag.

        Args:
            session: Neo4j async session
            tasting_id: TastingSession UUID as string
            flavor_tag_id: FlavorTag UUID as string
            intensity: Flavor intensity (1-10 scale), or None
        """
        try:
            await session.run(
                _LINK_TASTING_DETECTED_FLAVOR,
                {"tasting_id": tasting_id, "flavor_tag_id": flavor_tag_id, "intensity": intensity},
            )
            logger.debug(
                "Linked tasting detected flavor",
                tasting_id=tasting_id,
                flavor_tag_id=flavor_tag_id,
                intensity=intensity,
            )
        except Exception as e:
            self._handle_graph_error(e, f"link tasting {tasting_id} detected flavor {flavor_tag_id}")

    async def record_user_tasted_coffee(
        self, session: AsyncSession, user_id: str, coffee_id: str, rating: int | None, date: str | None
    ) -> None:
        """Create or update TASTED relationship between User and Coffee.

        Args:
            session: Neo4j async session
            user_id: Supabase auth user ID
            coffee_id: Coffee UUID as string
            rating: Overall rating (1-10 scale), or None
            date: ISO format date string, or None
        """
        try:
            await session.run(
                _LINK_USER_TASTED_COFFEE,
                {"user_id": user_id, "coffee_id": coffee_id, "rating": rating, "date": date},
            )
            logger.debug(
                "Recorded user tasted coffee",
                user_id=user_id,
                coffee_id=coffee_id,
                rating=rating,
            )
        except Exception as e:
            self._handle_graph_error(e, f"record user {user_id} tasted coffee {coffee_id}")

    # --- Delete Methods ---

    async def delete_user(self, session: AsyncSession, user_id: str) -> None:
        """Delete a User node and all its relationships.

        Args:
            session: Neo4j async session
            user_id: Supabase auth user ID
        """
        try:
            await session.run(_DELETE_USER, {"id": user_id})
            logger.debug("Deleted user node", user_id=user_id)
        except Exception as e:
            self._handle_graph_error(e, f"delete user {user_id}")

    async def delete_roaster(self, session: AsyncSession, roaster_id: str) -> None:
        """Delete a Roaster node and all its relationships.

        Args:
            session: Neo4j async session
            roaster_id: Roaster UUID as string
        """
        try:
            await session.run(_DELETE_ROASTER, {"id": roaster_id})
            logger.debug("Deleted roaster node", roaster_id=roaster_id)
        except Exception as e:
            self._handle_graph_error(e, f"delete roaster {roaster_id}")

    async def delete_coffee(self, session: AsyncSession, coffee_id: str) -> None:
        """Delete a Coffee node and all its relationships.

        Args:
            session: Neo4j async session
            coffee_id: Coffee UUID as string
        """
        try:
            await session.run(_DELETE_COFFEE, {"id": coffee_id})
            logger.debug("Deleted coffee node", coffee_id=coffee_id)
        except Exception as e:
            self._handle_graph_error(e, f"delete coffee {coffee_id}")

    async def delete_flavor_tag(self, session: AsyncSession, flavor_tag_id: str) -> None:
        """Delete a FlavorTag node and all its relationships.

        Args:
            session: Neo4j async session
            flavor_tag_id: FlavorTag UUID as string
        """
        try:
            await session.run(_DELETE_FLAVOR_TAG, {"id": flavor_tag_id})
            logger.debug("Deleted flavor tag node", flavor_tag_id=flavor_tag_id)
        except Exception as e:
            self._handle_graph_error(e, f"delete flavor tag {flavor_tag_id}")

    async def delete_tasting_session(self, session: AsyncSession, tasting_id: str) -> None:
        """Delete a TastingSession node and all its relationships.

        Args:
            session: Neo4j async session
            tasting_id: TastingSession UUID as string
        """
        try:
            await session.run(_DELETE_TASTING_SESSION, {"id": tasting_id})
            logger.debug("Deleted tasting session node", tasting_id=tasting_id)
        except Exception as e:
            self._handle_graph_error(e, f"delete tasting session {tasting_id}")

    # --- Convenience Sync Methods ---

    async def sync_roaster_full(
        self, session: AsyncSession, roaster: Roaster, user_id: str | None = None
    ) -> None:
        """Sync a Roaster with all its relationships.

        Creates/updates:
        - Roaster node
        - User node (if user_id provided)
        - CREATED relationship (if user_id provided)

        Args:
            session: Neo4j async session
            roaster: Roaster model instance
            user_id: Optional user who created the roaster
        """
        await self.upsert_roaster(session, roaster)

        if user_id:
            await self.upsert_user(session, user_id)
            await self.link_user_created_roaster(session, user_id, str(roaster.id))

        logger.debug("Synced roaster full", roaster_id=str(roaster.id))

    async def sync_coffee_full(
        self, session: AsyncSession, coffee: Coffee, user_id: str | None = None
    ) -> None:
        """Sync a Coffee with all its relationships.

        Creates/updates:
        - Coffee node
        - Roaster node (from coffee.roaster)
        - FlavorTag nodes (from coffee.flavor_tags)
        - User node (if user_id provided)
        - PRODUCES relationship
        - HAS_FLAVOR relationships
        - CREATED relationship (if user_id provided)

        Args:
            session: Neo4j async session
            coffee: Coffee model instance (should have roaster and flavor_tags loaded)
            user_id: Optional user who created the coffee
        """
        await self.upsert_coffee(session, coffee)

        # Sync roaster and link
        if coffee.roaster:
            await self.upsert_roaster(session, coffee.roaster)
            await self.link_coffee_to_roaster(session, str(coffee.id), str(coffee.roaster_id))

        # Sync flavor tags and link
        if coffee.flavor_tags:
            for tag in coffee.flavor_tags:
                await self.upsert_flavor_tag(session, tag)
            flavor_tag_ids = [str(tag.id) for tag in coffee.flavor_tags]
            await self.link_coffee_to_flavors(session, str(coffee.id), flavor_tag_ids)

        # Sync user and link
        if user_id:
            await self.upsert_user(session, user_id)
            await self.link_user_created_coffee(session, user_id, str(coffee.id))

        logger.debug("Synced coffee full", coffee_id=str(coffee.id))

    async def sync_tasting_full(self, session: AsyncSession, tasting: TastingSession) -> None:
        """Sync a TastingSession with all its relationships.

        Creates/updates:
        - TastingSession node
        - User node
        - Coffee node (from tasting.coffee)
        - FlavorTag nodes (from tasting.tasting_notes)
        - FOR_COFFEE relationship
        - BY_USER relationship
        - DETECTED relationships (with intensity)
        - TASTED relationship (user -> coffee with rating)

        Args:
            session: Neo4j async session
            tasting: TastingSession model instance (should have coffee and tasting_notes loaded)
        """
        await self.upsert_tasting_session(session, tasting)

        # Sync user and link
        await self.upsert_user(session, tasting.user_id)
        await self.link_tasting_to_user(session, str(tasting.id), tasting.user_id)

        # Sync coffee and link
        if tasting.coffee:
            await self.upsert_coffee(session, tasting.coffee)
            await self.link_tasting_to_coffee(session, str(tasting.id), str(tasting.coffee_id))

            # Record the user tasted this coffee
            await self.record_user_tasted_coffee(
                session,
                tasting.user_id,
                str(tasting.coffee_id),
                tasting.overall_rating,
                tasting.created_at.isoformat() if tasting.created_at else None,
            )

        # Sync detected flavors from tasting notes
        if tasting.tasting_notes:
            for note in tasting.tasting_notes:
                if note.flavor_tag:
                    await self.upsert_flavor_tag(session, note.flavor_tag)
                    await self.link_tasting_detected_flavor(
                        session, str(tasting.id), str(note.flavor_tag_id), note.intensity
                    )

        logger.debug("Synced tasting full", tasting_id=str(tasting.id))


# Global instance
graph_sync_repository = GraphSyncRepository()
