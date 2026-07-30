"""
Database initialization and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.env == "development",
    future=True,
    pool_pre_ping=True,
)

# Session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """
    Dependency to get database session
    """
    async with async_session() as session:
        yield session


async def init_db():
    """
    Initialize database tables
    """
    from app.db.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
