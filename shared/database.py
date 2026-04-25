import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://leads_user:leads_pass@localhost:5432/leads_db",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — async DB сесія."""
    async with AsyncSessionFactory() as session:
        yield session