# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
from typing import Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.pii_audit import PIIAccessLog
from ..models.user import User, UserRole

logger = get_logger(__name__)

# Must stay in sync with PIIAccessAction in schemas/pii_access_log.py
ALLOWED_ACTIONS = frozenset({"read", "reveal", "export", "print"})


PIIAccessAction = Literal["read", "reveal", "export", "print"]


def _user_role_str(user_role: UserRole | str | None) -> str:
    if user_role is None:
        return "unknown"
    if isinstance(user_role, UserRole):
        return user_role.value
    return str(user_role)


async def log_access(
    db: AsyncSession,
    *,
    user_id: int,
    patron_id: int,
    subject_type: str,
    action: str,
    subject_id: Optional[int] = None,
    reason: Optional[str] = None,
    user_role: UserRole | str | None = None,
    ip_address: Optional[str] = None,
) -> PIIAccessLog:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(
            f"Unsupported PII access action {action!r}; "
            f"expected one of {sorted(ALLOWED_ACTIONS)}"
        )

    record = PIIAccessLog(
        user_id=user_id,
        user_role=_user_role_str(user_role),
        # The granular flow doesn't correspond to a single endpoint URL --
        # the POST that triggered the write is just the transport. Store a
        # stable marker so the existing viewer's endpoint filter still
        # behaves predictably.
        endpoint="granular:pii_access_log",
        fields_accessed=[],
        fields_redacted=[],
        patron_ids_accessed=[patron_id],
        ip_address=ip_address,
        additional_context=None,
        patron_id=patron_id,
        subject_type=subject_type,
        subject_id=subject_id,
        action=action,
        reason=reason,
    )
    db.add(record)
    await db.flush()

    logger.info(
        "pii_access_log granular write: user=%s patron=%s subject=%s/%s action=%s",
        user_id,
        patron_id,
        subject_type,
        subject_id,
        action,
    )

    return record
