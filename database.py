"""
database.py – Ask-Your-Payments PostgreSQL Engine & Session Factory
===================================================================
Team CrackerX · PayPal AI Hackathon 2026

Responsibilities:
  1. Async engine creation bound to the validated DATABASE_URL from config.py.
  2. Session factory for transactional request scoping (FastAPI dependency).
  3. Startup DDL routine that:
     a) Enables the pg_trgm extension (required for fuzzy candidate matching).
     b) Creates all Medallion-architecture tables (Bronze → Silver → Gold).
  4. Health-check helper for readiness probes.

Design decisions:
  • asyncpg is the async driver; the URL is rewritten to postgresql+asyncpg://.
  • Pool limits are conservative defaults suitable for a hackathon Supabase instance;
    production would tune via env vars.
  • The engine echoes SQL only when a DEBUG flag is set (defaults to off).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from config import settings

logger = logging.getLogger("ask_your_payments.database")

# ---------------------------------------------------------------------------
# 1. Asynchronous Database Engine Construction (asyncpg)
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv("DATABASE_URL") or (
    settings.DATABASE_URL.get_secret_value()
    if hasattr(settings.DATABASE_URL, "get_secret_value")
    else str(settings.DATABASE_URL)
)

# Normalise the scheme for asyncpg:
#   postgresql://  →  postgresql+asyncpg://
#   postgres://    →  postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# 2. Session Factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
async_session_factory = AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields a transactional async session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_standalone_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context-manager for use outside of FastAPI request scope
    (workers, migrations, CLI scripts).
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# 3. Startup DDL: extensions + table creation
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """
    Idempotent database initialisation executed once at application startup.

    Steps:
      1. CREATE EXTENSION IF NOT EXISTS pg_trgm
         → Required for GIN-indexed trigram similarity searches used by
           the fuzzy candidate matching engine (NOT vector embeddings).
      2. CREATE ALL tables declared via SQLModel.metadata.
    """
    async with engine.begin() as conn:
        # ── Enable pg_trgm for fuzzy matching ──────────────────────────
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        logger.info("pg_trgm extension enabled.")

        # ── Materialise the full Medallion schema ──────────────────────
        # Import models so SQLModel.metadata is populated before create_all.
        import models as _models  # noqa: F401

        await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("All Medallion-architecture tables created.")

        try:
            await conn.execute(text("ALTER TABLE silver_transactions ADD COLUMN IF NOT EXISTS failure_reason TEXT"))
        except Exception as exc:
            logger.debug("Optional column migration for failure_reason: %s", exc)


# ---------------------------------------------------------------------------
# 4. Shutdown
# ---------------------------------------------------------------------------

async def close_db() -> None:
    """Dispose connection pool on graceful shutdown."""
    await engine.dispose()
    logger.info("Database connection pool disposed.")


# ---------------------------------------------------------------------------
# 5. Health check
# ---------------------------------------------------------------------------

async def check_db_health() -> bool:
    """Returns True when the database is reachable. Used by /healthz."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed.")
        return False
