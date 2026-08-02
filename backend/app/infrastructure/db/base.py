from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the app.

    Alembic's env.py imports this (and every models module, to make sure
    they've registered themselves on Base.metadata) to drive autogenerate.
    """
