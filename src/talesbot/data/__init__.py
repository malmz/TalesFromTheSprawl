from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

engine = create_engine("sqlite:///data.sqlite", echo=True)
Session = sessionmaker(engine)


class Base(MappedAsDataclass, DeclarativeBase):
    pass


def create_tables():
    Base.metadata.create_all(engine)


"""database = SqliteDatabase(
    "data.sqlite",
    pragmas={
        "journal_mode": "wal",
        "busy_timeout": 5000,
        "synchronous": "normal",
        "cache_size": -20000,
        "foreign_keys": 1,
        "temp_store": "memory",
    },
)"""
