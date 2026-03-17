from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from app.core.config import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.database_url, future=True, echo=settings.app_debug)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

sync_engine = create_engine(settings.sync_database_url, future=True, echo=settings.app_debug)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
