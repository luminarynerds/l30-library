# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bulk staff actions for patron accounts."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.user import User
from ....services.bulk_operations_service import (
    bulk_block_patrons as svc_bulk_block,
    bulk_send_notification as svc_bulk_notify,
    bulk_waive_fines as svc_bulk_waive,
    validate_bulk_request,
)
from ..dependencies import require_staff
from .patrons_schemas import (
    BulkBlockRequest,
    BulkBlockResponse,
    BulkNotificationRequest,
    BulkNotificationResponse,
    BulkWaiveFinesRequest,
    BulkWaiveFinesResponse,
)

router = APIRouter()

@router.post("/bulk-block", response_model=BulkBlockResponse)
@limiter.limit("10/minute")
async def bulk_block_patrons(
    request: Request,
    block_data: BulkBlockRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Block or unblock multiple patron accounts at once. Rate limited to 10 req/min."""
    try:
        validate_bulk_request(block_data.patron_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    result = await svc_bulk_block(
        db=db,
        patron_ids=block_data.patron_ids,
        blocked=block_data.blocked,
        reason=block_data.reason,
    )
    return BulkBlockResponse(**result)


@router.post("/bulk-waive-fines", response_model=BulkWaiveFinesResponse)
@limiter.limit("10/minute")
async def bulk_waive_fines(
    request: Request,
    waive_data: BulkWaiveFinesRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Waive all outstanding fines for multiple patrons (e.g., amnesty day)."""
    try:
        validate_bulk_request(waive_data.patron_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    result = await svc_bulk_waive(
        db=db,
        patron_ids=waive_data.patron_ids,
        staff_user_id=staff_user.id,
        reason=waive_data.reason,
    )
    return BulkWaiveFinesResponse(**result)


@router.post("/bulk-notify", response_model=BulkNotificationResponse)
@limiter.limit("5/minute")
async def bulk_send_notification(
    request: Request,
    notify_data: BulkNotificationRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Send a notification/email to multiple patrons. Rate limited to 5 req/min."""
    try:
        validate_bulk_request(notify_data.patron_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if not notify_data.subject or not notify_data.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Subject and message are required"
        )

    result = await svc_bulk_notify(
        db=db,
        patron_ids=notify_data.patron_ids,
        subject=notify_data.subject,
        message=notify_data.message,
        notification_type=notify_data.notification_type,
    )
    return BulkNotificationResponse(**result)


