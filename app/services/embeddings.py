"""Embedding service for generating vector embeddings via OpenAI."""

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.models.coffee import Coffee, FlavorTag

logger = get_logger(__name__)

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured")
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    @property
    def is_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(settings.OPENAI_API_KEY)

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If OpenAI is not configured
            Exception: If embedding generation fails
        """
        if not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        response = await self.client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
        )

        embedding = response.data[0].embedding
        logger.debug(
            "Generated embedding",
            text_length=len(text),
            embedding_dimensions=len(embedding),
        )
        return embedding

    def build_coffee_text(
        self,
        coffee: Coffee,
        roaster_name: str | None = None,
        flavor_tag_names: list[str] | None = None,
    ) -> str:
        """Build text representation of a coffee for embedding.

        Combines coffee attributes into a single text string that captures
        the semantic meaning of the coffee for similarity search.

        Args:
            coffee: Coffee model instance
            roaster_name: Optional roaster name (if not loaded on coffee)
            flavor_tag_names: Optional list of flavor tag names (if not loaded)

        Returns:
            Text representation suitable for embedding
        """
        parts: list[str] = []

        # Coffee name
        if coffee.name:
            parts.append(coffee.name)

        # Roaster
        roaster = roaster_name or (coffee.roaster.name if coffee.roaster else None)
        if roaster:
            parts.append(f"from {roaster}")

        # Origin
        origin_parts = []
        if coffee.origin_region:
            origin_parts.append(coffee.origin_region)
        if coffee.origin_country:
            origin_parts.append(coffee.origin_country)
        if origin_parts:
            parts.append(f"origin: {', '.join(origin_parts)}")

        # Processing and roast
        if coffee.processing_method:
            parts.append(f"{coffee.processing_method.value} process")
        if coffee.roast_level:
            parts.append(f"{coffee.roast_level.value} roast")

        # Variety
        if coffee.variety:
            parts.append(f"variety: {coffee.variety}")

        # Flavor tags
        flavors = flavor_tag_names or (
            [tag.name for tag in coffee.flavor_tags] if coffee.flavor_tags else None
        )
        if flavors:
            parts.append(f"flavors: {', '.join(flavors)}")

        # Description (truncate if very long)
        if coffee.description:
            desc = coffee.description[:500] if len(coffee.description) > 500 else coffee.description
            parts.append(desc)

        return ". ".join(parts)

    def build_flavor_tag_text(self, tag: FlavorTag) -> str:
        """Build text representation of a flavor tag for embedding.

        Adds context to help the embedding model understand this is a
        coffee flavor descriptor.

        Args:
            tag: FlavorTag model instance

        Returns:
            Text representation suitable for embedding
        """
        parts = [f"coffee flavor note: {tag.name}"]

        if tag.category:
            parts.append(f"category: {tag.category}")

        return ". ".join(parts)


# Global instance
embedding_service = EmbeddingService()
