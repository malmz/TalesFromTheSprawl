import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./config/data.sqlite"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionM = sessionmaker(engine)


class Base(MappedAsDataclass, DeclarativeBase):
    pass


def create_tables():
    Base.metadata.create_all(engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: sqlite3.Connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-20000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()
