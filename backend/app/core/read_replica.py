# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import exc as sa_exc, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

logger = logging.getLogger("app.read_replica")

settings = get_settings()

# ---------------------------------------------------------------------------
# Replica Engine Configuration
# ---------------------------------------------------------------------------

# Replica URL: falls back to primary if not configured
_replica_url: Optional[str] = None
_replica_engine = None
_ReplicaSessionLocal: Optional[async_sessionmaker] = None


def _get_replica_url() -> str:
    import os
    return os.getenv("REPLICA_DATABASE_URL", settings.database_url)


def _init_replica_engine():
    global _replica_engine, _ReplicaSessionLocal, _replica_url
    import os

    _replica_url = _get_replica_url()
    is_separate_replica = _replica_url != settings.database_url

    if is_separate_replica:
        logger.info("Read replica configured - analytics queries will be routed to replica")
    else:
        logger.info("No REPLICA_DATABASE_URL set - using primary for all queries")

    # Only create a separate engine if the replica URL differs from primary
    if not is_separate_replica:
        # In single-server mode, reuse the primary engine
        from .database import engine as primary_engine, AsyncSessionLocal
        _replica_engine = primary_engine
        _ReplicaSessionLocal = AsyncSessionLocal
        return

    engine_kwargs = {
        "echo": settings.debug,
    }

    if "postgresql" in _replica_url.lower():
        engine_kwargs["pool_pre_ping"] = True
        # Replica can have a larger pool since it only handles reads
        engine_kwargs["pool_size"] = settings.db_pool_size + 10
        engine_kwargs["max_overflow"] = settings.db_max_overflow + 10
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout
        engine_kwargs["pool_recycle"] = settings.db_pool_recycle

        connect_args = {
            "timeout": 10,
            "command_timeout": 120,  # Reports can take longer
        }

        if settings.environment == "production" and settings.database_require_ssl:
            connect_args["ssl"] = "require"

        # Set replica-specific options
        connect_args["options"] = "-c default_transaction_read_only=on"

        engine_kwargs["connect_args"] = connect_args

    _replica_engine = create_async_engine(_replica_url, **engine_kwargs)

    _ReplicaSessionLocal = async_sessionmaker(
        _replica_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info(
        "Read replica engine initialized",
        extra={
            "pool_size": engine_kwargs.get("pool_size"),
            "command_timeout": 120,
        },
    )


# ---------------------------------------------------------------------------
# Session Providers (FastAPI Dependencies)
# ---------------------------------------------------------------------------

async def get_replica_db() -> AsyncGenerator[AsyncSession, None]:
    if _ReplicaSessionLocal is None:
        _init_replica_engine()

    async with _ReplicaSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except sa_exc.SQLAlchemyError as e:
            replica_url = _replica_url or "primary"
            logger.error(
                "Database error in replica session",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "replica_url": replica_url,
                },
            )
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_primary_db() -> AsyncGenerator[AsyncSession, None]:
    from .database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Query Routing Helper
# ---------------------------------------------------------------------------

class QueryRouter:

    def __init__(
        self,
        primary: AsyncSession,
        replica: Optional[AsyncSession] = None,
    ):
        self.primary = primary
        self.replica = replica or primary

    async def execute_read(self, statement):
        return await self.replica.execute(statement)

    async def execute_write(self, statement):
        return await self.primary.execute(statement)

    async def add(self, instance):
        self.primary.add(instance)

    async def flush(self):
        await self.primary.flush()

    async def commit(self):
        await self.primary.commit()


# ---------------------------------------------------------------------------
# Recommended Endpoint Routing
# ---------------------------------------------------------------------------

# Map of API route prefixes to their recommended database session type.
# Use this as a reference when adding Depends() to new endpoints.

ROUTE_DB_MAPPING = {
    # === REPLICA (read-only, analytics-heavy) ===
    "/api/v1/reports": "replica",
    "/api/v1/annual-reports": "replica",
    "/api/v1/financial-reports": "replica",
    "/api/v1/usage-statistics": "replica",
    "/api/v1/staff/dashboard": "replica",
    "/api/v1/catalog/search": "replica",
    "/api/v1/catalog/browse": "replica",
    "/api/v1/indie/discovery": "replica",
    "/api/v1/indie/trending": "replica",
    "/api/v1/reading-programs/leaderboard": "replica",
    "/api/v1/analytics": "replica",
    "/api/v1/monitoring/performance": "replica",

    # === PRIMARY (write operations, transactional) ===
    "/api/v1/circulation/checkout": "primary",
    "/api/v1/circulation/return": "primary",
    "/api/v1/circulation/renew": "primary",
    "/api/v1/holds": "primary",
    "/api/v1/fines": "primary",
    "/api/v1/auth": "primary",
    "/api/v1/users": "primary",
    "/api/v1/catalog/create": "primary",
    "/api/v1/catalog/update": "primary",
}


# ---------------------------------------------------------------------------
# Replica Health Check
# ---------------------------------------------------------------------------

async def check_replica_lag() -> dict:
    if _replica_engine is None:
        _init_replica_engine()

    if _replica_url == settings.database_url:
        return {
            "status": "single_server",
            "lag_seconds": 0,
            "message": "No replica configured - using primary for all queries",
        }

    try:
        async with _ReplicaSessionLocal() as session:
            # PostgreSQL replication lag query
            result = await session.execute(
                text("""
                    SELECT
                        CASE WHEN pg_is_in_recovery()
                        THEN EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))
                        ELSE 0
                        END AS lag_seconds
                """)
            )
            row = result.fetchone()
            lag = float(row[0]) if row else 0

            status = "healthy"
            if lag > 30:
                status = "critical"
            elif lag > 5:
                status = "warning"

            return {
                "status": status,
                "lag_seconds": round(lag, 2),
                "message": f"Replication lag: {lag:.2f}s",
            }
    except sa_exc.SQLAlchemyError as e:
        logger.warning("Failed to check replica lag: %s", e)
        return {
            "status": "error",
            "lag_seconds": -1,
            "message": f"Failed to check replica: {str(e)}",
        }


async def dispose_replica_engine():
    if _replica_engine is not None:
        from .database import engine as primary_engine
        # Only dispose if it's a separate engine
        if _replica_engine is not primary_engine:
            await _replica_engine.dispose()
            logger.info("Read replica engine disposed")
