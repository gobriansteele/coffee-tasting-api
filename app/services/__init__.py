"""Service layer for external integrations."""

from .embeddings import EmbeddingService, embedding_service

__all__ = [
    "EmbeddingService",
    "embedding_service",
]
