from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db import (
    check_graph_connection,
    check_postgresql_connection,
    close_graph_driver,
    create_graph_driver,
    create_postgresql_engine,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting up Coffee Tasting API")

    # Configure logging
    configure_logging()

    # Initialize PostgreSQL database
    create_postgresql_engine()

    # Check PostgreSQL connection
    if not await check_postgresql_connection():
        logger.error("Failed to connect to PostgreSQL")
        raise RuntimeError("PostgreSQL connection failed")

    # Initialize Neo4j graph database (optional - won't fail if not configured)
    if settings.neo4j_configured:
        await create_graph_driver()
        if not await check_graph_connection():
            logger.warning("Failed to connect to Neo4j - graph features will be unavailable")
        else:
            logger.info("Neo4j graph database connected")
    else:
        logger.info("Neo4j not configured - graph features disabled")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Coffee Tasting API")

    # Close Neo4j driver
    await close_graph_driver()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Include API routes
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Register exception handlers
    register_exception_handlers(app)

    return app


# Create the application instance
app = create_application()
