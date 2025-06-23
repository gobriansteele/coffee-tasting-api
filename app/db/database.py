from typing import AsyncGenerator, Optional, Callable

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)

# Database engines
engine = None
async_engine = None
SessionLocal: Optional[Callable[[], Session]] = None
AsyncSessionLocal: Optional[Callable[[], AsyncSession]] = None


def create_database_engines() -> None:
    """Create database engines for sync and async operations."""
    global engine, async_engine, SessionLocal, AsyncSessionLocal
    
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL not configured")
        raise ValueError("DATABASE_URL must be set")
    
    # Convert postgres:// to postgresql:// if needed
    database_url = str(settings.DATABASE_URL)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Async engine (primary)
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
    )
    
    # Sync engine (for migrations and admin tasks)
    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
    )
    
    # Session factories
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    
    logger.info("Database engines created successfully")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call create_database_engines() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get sync database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call create_database_engines() first.")
    
    return SessionLocal()


async def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        if async_engine is None:
            return False
            
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False