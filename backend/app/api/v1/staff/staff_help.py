# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Help Request API

Allows staff to request assistance from on-duty supervisors.
Creates notifications for admins, directors, and managers.
"""
from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.notification import Notification, NotificationStatus, NotificationType
from ....models.user import User, UserRole
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/help", tags=["staff-help"])


class HelpRequest(BaseModel):
    message: Optional[str] = None


class HelpRequestResponse(BaseModel):
    notified_count: int
    message: str


@router.post("/request", response_model=HelpRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_help(
    payload: HelpRequest = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> HelpRequestResponse:
    """Request help from on-duty supervisors."""
    try:
        if payload is None:
            payload = HelpRequest()

        # Find supervisors: admins, directors, super_admins, or staff managers
        stmt = select(User).where(
            or_(
                User.role.in_([UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN]),
                (User.role == UserRole.STAFF) & (User.staff_role == "manager"),
            )
        )
        result = await db.execute(stmt)
        supervisors = result.scalars().all()

        if not supervisors:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No supervisors available to notify.",
            )

        msg = payload.message or "A staff member is requesting assistance."
        subject = f"{current_user.first_name} needs help"

        for supervisor in supervisors:
            notification = Notification(
                user_id=supervisor.id,
                notification_type=NotificationType.STAFF_HELP_REQUESTED,
                status=NotificationStatus.PENDING,
                subject=subject,
                message=msg,
                context_data={
                    "requesting_staff_id": current_user.id,
                    "requesting_staff_name": current_user.first_name,
                },
            )
            db.add(notification)

        await db.flush()

        return HelpRequestResponse(
            notified_count=len(supervisors),
            message=f"Help request sent to {len(supervisors)} supervisor(s).",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create help request notifications")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send help request.",
        ) from None
