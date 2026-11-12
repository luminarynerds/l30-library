# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff endpoint: PII Access Log viewer.

Read-only access to the ``pii_access_log`` audit trail for the highest-
privilege roles only (super_admin, director, legal).  Surfaces who has
viewed patron PII and when, with simple filters.

Viewing the log itself is auditable — every request writes an
``AuditAction.VIEWED`` row whose details name the resource so reviewers
can hold reviewers accountable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.authorization import require_role
from ....core.database import get_db
from ....core.pii_audit import PIIAccessLog
from ....models.audit_log import AuditAction, AuditLog
from ....models.user import User, UserRole
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/pii-access-log", tags=["staff-pii-access-log"])


class PIIAccessLogEntry(BaseModel):
    id: int
    user_id: int
    user_name: str | None
    user_role: str
    endpoint: str
    fields_accessed: list[str]
    fields_redacted: list[str]
    patron_ids_accessed: list[int]
    ip_address: str | None
    additional_context: dict[str, Any] | None
    timestamp: datetime

    class Config:
        from_attributes = True


class PIIAccessLogListResponse(BaseModel):
    entries: list[PIIAccessLogEntry]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PIIAccessLogListResponse)
async def list_pii_access_log(
    request: Request,
    patron_id: int | None = Query(None, description="Filter to events that touched this patron"),
    user_id: int | None = Query(None, description="Filter to events by this staff user"),
    endpoint: str | None = Query(None, description="Filter by endpoint substring (case-insensitive)"),
    since: datetime | None = Query(None, description="Default: 90 days ago"),
    until: datetime | None = Query(None, description="Default: now"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL)
    ),
) -> PIIAccessLogListResponse:
    """List PII-access audit events.

    Note: this endpoint deliberately does NOT call ``log_pii_access`` because
    it is reading the audit trail, not patron PII.  It does write an
    ``AuditLog`` row so the reviewers are themselves auditable.
    """
    now = datetime.now(timezone.utc)
    if since is None:
        since = now - timedelta(days=90)
    if until is None:
        until = now

    conditions = [
        PIIAccessLog.timestamp >= since,
        PIIAccessLog.timestamp <= until,
    ]
    if user_id is not None:
        conditions.append(PIIAccessLog.user_id == user_id)
    if endpoint is not None:
        conditions.append(PIIAccessLog.endpoint.ilike(f"%{endpoint}%"))
    if patron_id is not None:
        # patron_ids_accessed is JSON; cast to JSONB to use containment.
        conditions.append(
            cast(PIIAccessLog.patron_ids_accessed, JSONB).contains(
                cast([patron_id], JSONB)
            )
        )

    where = and_(*conditions)

    # Count + fetch.  Wrap both in the table-missing guard so a missing
    # ``pii_access_log`` table returns a clear 503 instead of a generic 500.
    try:
        from sqlalchemy import func

        count_q = select(func.count(PIIAccessLog.id)).where(where)
        total_result = await db.execute(count_q)
        total = int(total_result.scalar_one())

        rows_q = (
            select(PIIAccessLog)
            .where(where)
            .order_by(PIIAccessLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        rows_result = await db.execute(rows_q)
        rows = list(rows_result.scalars().all())
    except ProgrammingError as exc:  # UndefinedTable raises ProgrammingError
        if "pii_access_log" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="pii_access_log table missing; run alembic upgrade head",
            ) from exc
        raise

    # Resolve actor display names with an eager User lookup (no lazy load).
    actor_ids = {r.user_id for r in rows}
    name_map: dict[int, str] = {}
    if actor_ids:
        users_result = await db.execute(
            select(User.id, User.first_name, User.last_name).where(User.id.in_(actor_ids))
        )
        for uid, first, last in users_result.all():
            name_map[uid] = " ".join(filter(None, [first, last])) or None  # type: ignore[assignment]

    entries = [
        PIIAccessLogEntry(
            id=r.id,
            user_id=r.user_id,
            user_name=name_map.get(r.user_id),
            user_role=r.user_role,
            endpoint=r.endpoint or "",
            fields_accessed=list(r.fields_accessed or []),
            fields_redacted=list(r.fields_redacted or []),
            patron_ids_accessed=list(r.patron_ids_accessed or []),
            ip_address=r.ip_address,
            additional_context=r.additional_context,
            timestamp=r.timestamp,
        )
        for r in rows
    ]

    # Audit the auditor.  Use AuditAction.VIEWED so we do not need a new
    # enum value or migration.
    try:
        db.add(
            AuditLog(
                admin_id=current_user.id,
                target_user_id=None,
                action=AuditAction.VIEWED,
                details={
                    "resource": "pii_access_log",
                    "filters": {
                        "patron_id": patron_id,
                        "user_id": user_id,
                        "endpoint": endpoint,
                        "since": since.isoformat(),
                        "until": until.isoformat(),
                        "limit": limit,
                        "offset": offset,
                    },
                    "result_count": len(entries),
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        )
        await db.flush()
    except Exception:
        # Audit-write failure must never break the read.
        logger.exception(
            "Failed to write AuditLog row for pii_access_log view"
        )

    return PIIAccessLogListResponse(
        entries=entries,
        total=total,
        limit=limit,
        offset=offset,
    )
