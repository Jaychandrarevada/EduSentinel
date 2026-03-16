"""
SQLAlchemy async engine, session factory, and declarative Base.
Supports PostgreSQL (asyncpg) and SQLite (aiosqlite) based on DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from app.config import settings

_url = settings.DATABASE_URL
_is_sqlite = _url.startswith("sqlite")

def _to_async_url(url: str) -> str:
    """
    Convert any PostgreSQL URL variant to the asyncpg async scheme.

    Handles all formats Render, Railway, Supabase, and local envs may provide:
      postgres://...           → postgresql+asyncpg://...
      postgresql://...         → postgresql+asyncpg://...
      postgresql+psycopg2://.. → postgresql+asyncpg://...
      postgresql+asyncpg://..  → unchanged
    """
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url

if _is_sqlite:
    # SQLite: use aiosqlite driver, no connection pool settings
    _async_url = _url.replace("sqlite://", "sqlite+aiosqlite://")
    engine = create_async_engine(
        _async_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL: use asyncpg driver with connection pooling
    _async_url = _to_async_url(_url)
    engine = create_async_engine(
        _async_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Shared naming convention for Alembic migrations
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)
