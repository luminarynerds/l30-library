# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Build engine kwargs based on database type
engine_kwargs = {
    "echo": settings.debug,
}

# Only add PostgreSQL-specific parameters if using PostgreSQL
if "postgresql" in settings.database_url.lower():
    engine_kwargs["pool_pre_ping"] = True
    # Connection pool settings - configurable for horizontal scaling
    # Total connections per instance = pool_size + max_overflow
    # When scaling to N instances, ensure N * (pool_size + max_overflow) < PostgreSQL max_connections
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
    engine_kwargs["pool_timeout"] = settings.db_pool_timeout
    engine_kwargs["pool_recycle"] = settings.db_pool_recycle
    # Connection-level timeouts and SSL security
    connect_args = {
        "timeout": 10,  # Connection establishment timeout (asyncpg uses 'timeout' not 'connect_timeout')
        "command_timeout": 60,  # Query execution timeout
    }
    # Enforce SSL in production for data-in-transit encryption
    if settings.environment == "production" and settings.database_require_ssl:
        connect_args["ssl"] = "require"
    engine_kwargs["connect_args"] = connect_args
elif "sqlite" in settings.database_url.lower():
    # SQLite-specific settings
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias for backwards compatibility
async_session_maker = AsyncSessionLocal


class Base(DeclarativeBase):
    pass


# Fix Python 3.11+ str(StrEnum) returning 'ClassName.NAME' instead of value.
# Without this, String(50) columns store garbage when assigned an enum member.
import enum
from sqlalchemy import event as _sa_event

@_sa_event.listens_for(Base, "before_insert", propagate=True)
@_sa_event.listens_for(Base, "before_update", propagate=True)
def _coerce_enum_values(mapper, connection, target):
    for col in mapper.columns:
        if isinstance(col.type, type) or not hasattr(col, 'key'):
            continue
        val = getattr(target, col.key, None)
        if val is not None and isinstance(val, enum.Enum):
            object.__setattr__(target, col.key, val.value)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except sa_exc.SQLAlchemyError as e:
            logger.error(
                "Database error in get_db session",
                extra={"error_type": type(e).__name__, "error": str(e)},
            )
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_async_session() -> AsyncSession:
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except sa_exc.SQLAlchemyError as e:
        logger.error(
            "Database error in get_async_session",
            extra={"error_type": type(e).__name__, "error": str(e)},
        )
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine():
    await engine.dispose()
