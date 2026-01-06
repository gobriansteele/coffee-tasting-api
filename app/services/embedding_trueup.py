"""Service for truing up embeddings for existing entities in the graph."""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from neo4j import AsyncSession as Neo4jSession
from sqlalchemy.ext.asyncio import AsyncSession as SQLSession

from app.core.logging import get_logger
from app.models.coffee import Coffee, FlavorTag
from app.repositories.graph import graph_query_repository, graph_sync_repository
from app.repositories.sql.coffee import coffee_repository
from app.repositories.sql.flavor_tag import flavor_tag_repository
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


@dataclass
class TrueupResult:
    """Result of an embedding trueup operation."""

    coffees_found: int = 0
    coffees_processed: int = 0
    coffees_failed: int = 0
    flavor_tags_found: int = 0
    flavor_tags_processed: int = 0
    flavor_tags_failed: int = 0
    errors: list[str] = field(default_factory=list)


class EmbeddingTrueupService:
    """Service for backfilling embeddings for entities missing them."""

    def __init__(self, batch_size: int = 10) -> None:
        """Initialize the trueup service.

        Args:
            batch_size: Number of entities to process in parallel per batch
        """
        self.batch_size = batch_size

    async def _generate_and_store_coffee_embedding(
        self,
        coffee: Coffee,
        graph_session: Neo4jSession,
    ) -> None:
        """Generate and store embedding for a single coffee.

        Args:
            coffee: Coffee model instance with relationships loaded
            graph_session: Neo4j session for storing the embedding

        Raises:
            Exception: If embedding generation or storage fails
        """
        text = embedding_service.build_coffee_text(coffee)
        embedding = await embedding_service.generate_embedding(text)
        await graph_sync_repository.upsert_coffee_embedding(
            graph_session, str(coffee.id), embedding
        )
        logger.debug(
            "Generated coffee embedding",
            coffee_id=str(coffee.id),
            coffee_name=coffee.name,
        )

    async def _generate_and_store_flavor_tag_embedding(
        self,
        tag: FlavorTag,
        graph_session: Neo4jSession,
    ) -> None:
        """Generate and store embedding for a single flavor tag.

        Args:
            tag: FlavorTag model instance
            graph_session: Neo4j session for storing the embedding

        Raises:
            Exception: If embedding generation or storage fails
        """
        text = embedding_service.build_flavor_tag_text(tag)
        embedding = await embedding_service.generate_embedding(text)
        await graph_sync_repository.upsert_flavor_tag_embedding(
            graph_session, str(tag.id), embedding
        )
        logger.debug(
            "Generated flavor tag embedding",
            flavor_tag_id=str(tag.id),
            tag_name=tag.name,
        )

    async def _process_single_coffee(
        self,
        coffee_id: str,
        db: SQLSession,
        graph_session: Neo4jSession,
    ) -> tuple[bool, str | None]:
        """Process a single coffee embedding.

        Args:
            coffee_id: Coffee ID string to process
            db: SQLAlchemy session for fetching coffee data
            graph_session: Neo4j session for storing embeddings

        Returns:
            Tuple of (success, error_message). error_message is None on success.
        """
        try:
            uuid = UUID(coffee_id)
            coffee = await coffee_repository.get_with_flavor_tags(db, uuid)
            if not coffee:
                error_msg = f"Coffee {coffee_id}: not found in PostgreSQL"
                logger.warning(error_msg)
                return False, error_msg

            await self._generate_and_store_coffee_embedding(coffee, graph_session)
            return True, None

        except Exception as e:
            error_msg = f"Coffee {coffee_id}: {e}"
            logger.error("Failed to process coffee embedding", coffee_id=coffee_id, error=str(e))
            return False, error_msg

    async def _process_single_flavor_tag(
        self,
        tag_id: str,
        db: SQLSession,
        graph_session: Neo4jSession,
    ) -> tuple[bool, str | None]:
        """Process a single flavor tag embedding.

        Args:
            tag_id: Flavor tag ID string to process
            db: SQLAlchemy session for fetching tag data
            graph_session: Neo4j session for storing embeddings

        Returns:
            Tuple of (success, error_message). error_message is None on success.
        """
        try:
            uuid = UUID(tag_id)
            tag = await flavor_tag_repository.get(db, uuid)
            if not tag:
                error_msg = f"FlavorTag {tag_id}: not found in PostgreSQL"
                logger.warning(error_msg)
                return False, error_msg

            await self._generate_and_store_flavor_tag_embedding(tag, graph_session)
            return True, None

        except Exception as e:
            error_msg = f"FlavorTag {tag_id}: {e}"
            logger.error("Failed to process flavor tag embedding", tag_id=tag_id, error=str(e))
            return False, error_msg

    async def _process_coffee_batch(
        self,
        coffee_ids: list[str],
        db: SQLSession,
        graph_session: Neo4jSession,
        result: TrueupResult,
    ) -> None:
        """Process a batch of coffees in parallel.

        Args:
            coffee_ids: List of coffee ID strings to process
            db: SQLAlchemy session for fetching coffee data
            graph_session: Neo4j session for storing embeddings
            result: TrueupResult to accumulate results
        """
        # Fetch all coffees sequentially first (AsyncSession doesn't support concurrent ops)
        coffees: list[tuple[str, Coffee | None]] = []
        for cid in coffee_ids:
            try:
                uuid = UUID(cid)
                coffee = await coffee_repository.get_with_flavor_tags(db, uuid)
                coffees.append((cid, coffee))
            except Exception as e:
                error_msg = f"Coffee {cid}: {e}"
                logger.error("Failed to fetch coffee", coffee_id=cid, error=str(e))
                result.coffees_failed += 1
                result.errors.append(error_msg)

        # Filter out missing coffees
        valid_coffees: list[tuple[str, Coffee]] = []
        for cid, coffee in coffees:
            if coffee is None:
                error_msg = f"Coffee {cid}: not found in PostgreSQL"
                logger.warning(error_msg)
                result.coffees_failed += 1
                result.errors.append(error_msg)
            else:
                valid_coffees.append((cid, coffee))

        if not valid_coffees:
            return

        # Parallelize embedding generation (the slow OpenAI API calls)
        async def generate_embedding_for_coffee(
            coffee: Coffee,
        ) -> tuple[str, list[float] | None, str | None]:
            """Returns (coffee_id, embedding, error_msg)."""
            try:
                text = embedding_service.build_coffee_text(coffee)
                embedding = await embedding_service.generate_embedding(text)
                return str(coffee.id), embedding, None
            except Exception as e:
                error_msg = f"Coffee {coffee.id}: {e}"
                logger.error(
                    "Failed to generate coffee embedding",
                    coffee_id=str(coffee.id),
                    error=str(e),
                )
                return str(coffee.id), None, error_msg

        tasks = [generate_embedding_for_coffee(coffee) for _, coffee in valid_coffees]
        embedding_results = await asyncio.gather(*tasks)

        # Store embeddings sequentially (Neo4j session doesn't support concurrent ops)
        for coffee_id, embedding, error_msg in embedding_results:
            if embedding is None:
                result.coffees_failed += 1
                if error_msg:
                    result.errors.append(error_msg)
            else:
                try:
                    await graph_sync_repository.upsert_coffee_embedding(
                        graph_session, coffee_id, embedding
                    )
                    result.coffees_processed += 1
                    logger.debug(
                        "Generated coffee embedding",
                        coffee_id=coffee_id,
                    )
                except Exception as e:
                    error_msg = f"Coffee {coffee_id}: failed to store embedding: {e}"
                    logger.error(error_msg)
                    result.coffees_failed += 1
                    result.errors.append(error_msg)

    async def _process_flavor_tag_batch(
        self,
        tag_ids: list[str],
        db: SQLSession,
        graph_session: Neo4jSession,
        result: TrueupResult,
    ) -> None:
        """Process a batch of flavor tags in parallel.

        Args:
            tag_ids: List of flavor tag ID strings to process
            db: SQLAlchemy session for fetching tag data
            graph_session: Neo4j session for storing embeddings
            result: TrueupResult to accumulate results
        """
        # Fetch all tags sequentially first (AsyncSession doesn't support concurrent ops)
        tags: list[tuple[str, FlavorTag | None]] = []
        for tid in tag_ids:
            try:
                uuid = UUID(tid)
                tag = await flavor_tag_repository.get(db, uuid)
                tags.append((tid, tag))
            except Exception as e:
                error_msg = f"FlavorTag {tid}: {e}"
                logger.error("Failed to fetch flavor tag", tag_id=tid, error=str(e))
                result.flavor_tags_failed += 1
                result.errors.append(error_msg)

        # Filter out missing tags
        valid_tags: list[tuple[str, FlavorTag]] = []
        for tid, tag in tags:
            if tag is None:
                error_msg = f"FlavorTag {tid}: not found in PostgreSQL"
                logger.warning(error_msg)
                result.flavor_tags_failed += 1
                result.errors.append(error_msg)
            else:
                valid_tags.append((tid, tag))

        if not valid_tags:
            return

        # Parallelize embedding generation (the slow OpenAI API calls)
        async def generate_embedding_for_tag(
            tag: FlavorTag,
        ) -> tuple[str, list[float] | None, str | None]:
            """Returns (tag_id, embedding, error_msg)."""
            try:
                text = embedding_service.build_flavor_tag_text(tag)
                embedding = await embedding_service.generate_embedding(text)
                return str(tag.id), embedding, None
            except Exception as e:
                error_msg = f"FlavorTag {tag.id}: {e}"
                logger.error(
                    "Failed to generate flavor tag embedding",
                    tag_id=str(tag.id),
                    error=str(e),
                )
                return str(tag.id), None, error_msg

        tasks = [generate_embedding_for_tag(tag) for _, tag in valid_tags]
        embedding_results = await asyncio.gather(*tasks)

        # Store embeddings sequentially (Neo4j session doesn't support concurrent ops)
        for tag_id, embedding, error_msg in embedding_results:
            if embedding is None:
                result.flavor_tags_failed += 1
                if error_msg:
                    result.errors.append(error_msg)
            else:
                try:
                    await graph_sync_repository.upsert_flavor_tag_embedding(
                        graph_session, tag_id, embedding
                    )
                    result.flavor_tags_processed += 1
                    logger.debug(
                        "Generated flavor tag embedding",
                        flavor_tag_id=tag_id,
                    )
                except Exception as e:
                    error_msg = f"FlavorTag {tag_id}: failed to store embedding: {e}"
                    logger.error(error_msg)
                    result.flavor_tags_failed += 1
                    result.errors.append(error_msg)

    async def trueup_coffees(
        self,
        db: SQLSession,
        graph_session: Neo4jSession,
        result: TrueupResult,
    ) -> None:
        """True up embeddings for all coffees missing them.

        Args:
            db: SQLAlchemy session for fetching data
            graph_session: Neo4j session for querying and storing
            result: TrueupResult to accumulate results
        """
        # Get all coffee IDs without embeddings from the graph
        coffee_ids = await graph_query_repository.get_coffee_ids_without_embedding(graph_session)
        result.coffees_found = len(coffee_ids)

        if not coffee_ids:
            logger.info("No coffees found without embeddings")
            return

        logger.info("Found coffees without embeddings", count=len(coffee_ids))

        # Process in batches
        for i in range(0, len(coffee_ids), self.batch_size):
            batch = coffee_ids[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(coffee_ids) + self.batch_size - 1) // self.batch_size

            logger.info(
                "Processing coffee batch",
                batch=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            await self._process_coffee_batch(batch, db, graph_session, result)

    async def trueup_flavor_tags(
        self,
        db: SQLSession,
        graph_session: Neo4jSession,
        result: TrueupResult,
    ) -> None:
        """True up embeddings for all flavor tags missing them.

        Args:
            db: SQLAlchemy session for fetching data
            graph_session: Neo4j session for querying and storing
            result: TrueupResult to accumulate results
        """
        # Get all flavor tag IDs without embeddings from the graph
        tag_ids = await graph_query_repository.get_flavor_tag_ids_without_embedding(graph_session)
        result.flavor_tags_found = len(tag_ids)

        if not tag_ids:
            logger.info("No flavor tags found without embeddings")
            return

        logger.info("Found flavor tags without embeddings", count=len(tag_ids))

        # Process in batches
        for i in range(0, len(tag_ids), self.batch_size):
            batch = tag_ids[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(tag_ids) + self.batch_size - 1) // self.batch_size

            logger.info(
                "Processing flavor tag batch",
                batch=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            await self._process_flavor_tag_batch(batch, db, graph_session, result)

    async def trueup_all(
        self,
        db: SQLSession,
        graph_session: Neo4jSession,
    ) -> TrueupResult:
        """True up embeddings for all entity types.

        Args:
            db: SQLAlchemy session for fetching data
            graph_session: Neo4j session for querying and storing

        Returns:
            TrueupResult with counts and any errors
        """
        result = TrueupResult()

        # Process coffees
        await self.trueup_coffees(db, graph_session, result)

        # Process flavor tags
        await self.trueup_flavor_tags(db, graph_session, result)

        return result


# Global instance with default batch size
embedding_trueup_service = EmbeddingTrueupService(batch_size=10)
