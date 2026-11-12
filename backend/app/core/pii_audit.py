# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import json
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Sequence

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..core.database import Base

# Deferred: app.models.__init__ imports app.models.pii_access_log, which
# re-exports PIIAccessLog from this module. Importing app.models at module
# scope here closes that loop and breaks collection whenever this module is
# imported first (a test chunk starting with test_pii_access_log_service.py).
if TYPE_CHECKING:
    from ..models.user import UserRole

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Database model
# ---------------------------------------------------------------------------


class PIIAccessLog(Base):
    __tablename__ = "pii_access_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, nullable=False, index=True)
    user_role = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False)
    fields_accessed = Column(JSON, nullable=False, default=list)
    fields_redacted = Column(JSON, nullable=False, default=list)
    patron_ids_accessed = Column(JSON, nullable=True, default=list)
    ip_address = Column(String(45), nullable=True)
    additional_context = Column(JSON, nullable=True)

    # Granular per-record fields (added by pii_access_log_002).
    # Nullable so the existing batched flow keeps writing rows without them.
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject_type = Column(String(64), nullable=True)
    subject_id = Column(Integer, nullable=True)
    action = Column(String(32), nullable=True)
    reason = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


async def log_pii_access(
    *,
    db: AsyncSession | None = None,
    user_id: int,
    user_role: UserRole | str,
    endpoint: str,
    fields_accessed: Sequence[str],
    fields_redacted: Sequence[str],
    patron_ids_accessed: Sequence[int] | None = None,
    ip_address: str | None = None,
    additional_context: dict[str, Any] | None = None,
) -> None:
    from ..models.user import UserRole  # runtime import, deferred per the guard above

    role_str = user_role.value if isinstance(user_role, UserRole) else str(user_role)

    log_entry = {
        "event": "pii_access",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user_role": role_str,
        "endpoint": endpoint,
        "fields_accessed": list(fields_accessed),
        "fields_redacted": list(fields_redacted),
        "patron_ids_accessed": list(patron_ids_accessed) if patron_ids_accessed else [],
        "ip_address": ip_address,
    }
    if additional_context:
        log_entry["additional_context"] = additional_context

    # Always emit a structured log line
    logger.info("PII access: %s", json.dumps(log_entry))

    # Persist to database when a session is available
    if db is not None:
        try:
            record = PIIAccessLog(
                user_id=user_id,
                user_role=role_str,
                endpoint=endpoint,
                fields_accessed=list(fields_accessed),
                fields_redacted=list(fields_redacted),
                patron_ids_accessed=list(patron_ids_accessed) if patron_ids_accessed else [],
                ip_address=ip_address,
                additional_context=additional_context,
            )
            db.add(record)
            await db.flush()
        except Exception:
            # Audit failures must never break the actual request
            logger.exception("Failed to persist PII access log to database")
