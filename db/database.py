from typing import Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from config import settings
async_engine = create_async_engine(settings.database.url, echo=True)

async_session = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine)

# Создание всех таблиц в базе данных
# Base.metadata.create_all(engine)

async def get_db() -> AsyncSession:
    db = async_session()
    try:
        yield db
    finally:
        await db.close()


def connection(func: Callable):
    # @functools.wraps
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)

    return wrapper