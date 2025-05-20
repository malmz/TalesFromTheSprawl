from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from talesbot.config import config

engine = create_async_engine(config.SQLALCHEMY_DATABASE_URI)

SessionM = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, MappedAsDataclass, DeclarativeBase):
    pass


async def create_tables():
    # Import models so they are registerd
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
