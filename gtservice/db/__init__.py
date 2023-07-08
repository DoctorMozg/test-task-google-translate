from contextlib import asynccontextmanager

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, \
    async_sessionmaker
from gtservice.db.common import Base

from gtservice import settings

engine = create_async_engine(
    settings.DB_CONNECTION_STRING,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)


class Database:

    def __init__(self, eng: AsyncEngine):
        self._engine = eng
        self._metadata = Base.metadata
        self._session_factory = async_sessionmaker(eng)

    def metadata(self) -> MetaData:
        return self._metadata

    def async_session_generator(self):
        return self._session_factory

    async def create_all(self):
        async with engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def drop_all(self):
        async with engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)


database: Database = Database(engine)


@asynccontextmanager
async def database_session_context():
    try:
        async_session = database.async_session_generator()
        async with async_session() as session:
            yield session
    except:
        await session.rollback()
        raise
    finally:
        await session.close()


async def database_session():
    async with database_session_context() as session:
        yield session
