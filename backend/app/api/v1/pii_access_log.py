# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Granular PII access log API: write path.

POST /api/v1/pii-access-log/

The staff frontend hook calls this endpoint to record a single PII
access event. The read path (filtered list of events for auditors)
lives at /api/v1/staff/pii-access-log and serves the highest-privilege
roles only.
"""

from __future__ import annotations

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.pii_access_log import PIIAccessLogCreate, PIIAccessLogRead
from ...services import pii_access_log_service
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/pii-access-log", tags=["pii-access-log"])


@router.post(
    "/",
    response_model=PIIAccessLogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a PII access event",
)
async def create_pii_access_log_entry(
    payload: PIIAccessLogCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> PIIAccessLogRead:
    """Write one granular PII access event.

    The endpoint is staff-only because patron-facing surfaces should not
    be claiming "I just accessed patron PII" -- the actor is always the
    authenticated staff session.
    """
    ip = request.client.host if request.client else None

    try:
        record = await pii_access_log_service.log_access(
            db,
            user_id=current_user.id,
            patron_id=payload.patron_id,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            action=payload.action,
            reason=payload.reason,
            user_role=current_user.role,
            ip_address=ip,
        )
        await db.commit()
        await db.refresh(record)
    except ValueError as exc:
        # Service rejected the action enum. Should be unreachable because
        # the Pydantic Literal catches the same case, but defend the
        # boundary in case the schema and service drift.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception:
        # Audit-log writes must never break the calling flow, but the
        # client API is fire-and-forget on its end -- here on the server
        # we still surface failures so monitoring picks them up.
        await db.rollback()
        logger.exception(
            "Failed to persist granular pii_access_log row for user=%s patron=%s",
            current_user.id,
            payload.patron_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record PII access event",
        ) from None

    return PIIAccessLogRead.model_validate(record)
