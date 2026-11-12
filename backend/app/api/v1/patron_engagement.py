# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Engagement API - Celebrations and Recognition Endpoints

Handles checkout milestones, anniversary recognition, and event thank yous.
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...services.patron_engagement_service import PatronEngagementService
from ...schemas.common import MessageResponse
from .auth import get_current_user
from .dependencies import is_staff_or_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/patron-engagement", tags=["patron-engagement"])


async def require_staff_or_self(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.post(
    "/celebrate-100th-checkout/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def celebrate_100th_checkout(
    user_id: int,
    current_user: User = Depends(require_staff_or_self),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if patron has reached their 100th checkout and send celebration.

    Staff can check any patron. Patrons can only check their own.
    Returns notification status.
    """
    # Authorization: staff or the user themselves
    if not is_staff_or_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own milestones",
        )

    try:
        service = PatronEngagementService(db)
        notification = await service.check_and_celebrate_100th_checkout(user_id)

        if not notification:
            return MessageResponse(
                message="Patron has not reached 100 checkouts yet or notification already sent",
            )

        return MessageResponse(
            message="100th checkout celebration notification queued successfully",
        )
    except Exception as e:
        logger.error(f"Error celebrating 100th checkout for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process celebration",
        ) from e


@router.post(
    "/celebrate-card-anniversary/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def celebrate_card_anniversary(
    user_id: int,
    current_user: User = Depends(require_staff_or_self),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if today is patron's library card anniversary and send recognition.

    Staff can check any patron. Patrons can only check their own.
    Returns notification status.
    """
    # Authorization: staff or the user themselves
    if not is_staff_or_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check your own milestones",
        )

    try:
        service = PatronEngagementService(db)
        notification = await service.check_and_celebrate_card_anniversary(user_id)

        if not notification:
            return MessageResponse(
                message="Today is not the patron's library card anniversary",
            )

        return MessageResponse(
            message="Card anniversary celebration notification queued successfully",
        )
    except Exception as e:
        logger.error(f"Error celebrating card anniversary for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process celebration",
        ) from e


@router.post(
    "/send-event-thank-you/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def send_event_thank_you(
    user_id: int,
    event_id: int,
    event_title: str,
    attendee_name: Optional[str] = None,
    current_user: User = Depends(require_staff_or_self),
    db: AsyncSession = Depends(get_db),
):
    """
    Send thank you message after event attendance.

    Staff can send on behalf of any patron. Patrons can send for themselves.
    Query parameters:
    - event_id: ID of the event
    - event_title: Title of the event
    - attendee_name (optional): Attendee name for personalization
    """
    # Authorization: staff or the user themselves
    if not is_staff_or_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only send thank you on your own behalf",
        )

    if not event_title or not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id and event_title are required",
        )

    try:
        service = PatronEngagementService(db)
        await service.send_event_thank_you(
            user_id=user_id,
            event_id=event_id,
            event_title=event_title,
            attendee_name=attendee_name,
        )

        return MessageResponse(
            message="Event thank you notification queued successfully",
        )
    except Exception as e:
        logger.error(f"Error sending event thank you for user {user_id}, event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send thank you message",
        ) from e
