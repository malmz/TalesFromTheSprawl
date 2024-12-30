from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from talesbot.config import config

# SQLALCHEMY_DATABASE_URL = "sqlite:///./config/data.sqlite"

engine = create_async_engine(config.SQLALCHEMY_DATABASE_URI)

SessionM = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, MappedAsDataclass, DeclarativeBase):
    pass


async def create_tables():
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


""" @event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: sqlite3.Connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-20000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close() """
