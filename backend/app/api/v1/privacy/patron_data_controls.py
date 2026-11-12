# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron data controls: holds history, notification history, AI conversations."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.audit_log import AuditAction
from ....models.catalog import CatalogItem
from ....models.circulation import Hold, HoldStatus
from ....models.notification import NotificationHistory, PatronNotification
from ....models.ai_agents import AgentConversation
from ....models.user import User
from ..auth import get_current_user

from .helpers import create_audit_log
from .schemas import (
    HoldHistoryItem,
    HoldHistoryResponse,
    AIConversationListItem,
    AIConversationListResponse,
    AIConversationDetail,
    NotificationHistoryClearResponse,
)

logger = get_logger(__name__)

router = APIRouter()

# Hold statuses that are considered "historical" (not active)
HISTORICAL_HOLD_STATUSES = [
    HoldStatus.fulfilled,
    HoldStatus.cancelled,
    HoldStatus.expired,
]


# =============================================================================
# Holds History
# =============================================================================


@router.get("/holds-history", response_model=HoldHistoryResponse)
async def get_holds_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the patron's fulfilled, cancelled, and expired holds with item titles."""
    result = await db.execute(
        select(Hold, CatalogItem.title)
        .join(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(
            Hold.user_id == current_user.id,
            Hold.status.in_(HISTORICAL_HOLD_STATUSES),
        )
        .order_by(Hold.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()

    count_result = await db.execute(
        select(func.count())
        .select_from(Hold)
        .where(
            Hold.user_id == current_user.id,
            Hold.status.in_(HISTORICAL_HOLD_STATUSES),
        )
    )
    total = count_result.scalar_one()

    return HoldHistoryResponse(
        items=[
            HoldHistoryItem(
                id=hold.id,
                item_title=title,
                status=hold.status.value if hasattr(hold.status, "value") else str(hold.status),
                created_at=hold.created_at.isoformat() if hold.created_at else None,
                cancelled_at=hold.cancelled_at.isoformat() if hold.cancelled_at else None,
            )
            for hold, title in rows
        ],
        total=total,
    )


@router.delete("/holds-history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_holds_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear patron's hold history by deleting fulfilled/cancelled/expired holds.

    Active holds (pending/ready) are never touched.
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(Hold)
        .where(
            Hold.user_id == current_user.id,
            Hold.status.in_(HISTORICAL_HOLD_STATUSES),
        )
    )
    deleted_count = count_result.scalar_one()

    await db.execute(
        delete(Hold)
        .where(
            Hold.user_id == current_user.id,
            Hold.status.in_(HISTORICAL_HOLD_STATUSES),
        )
    )

    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=current_user.id,
        details={
            "action": "holds_history_cleared",
            "records_deleted": deleted_count,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()


# =============================================================================
# Notification History
# =============================================================================


@router.delete(
    "/notifications/history",
    status_code=status.HTTP_200_OK,
    response_model=NotificationHistoryClearResponse,
)
async def clear_notification_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete dismissed patron notifications and anonymize notification history.

    - Hard-deletes PatronNotification records where is_dismissed=True
    - Anonymizes NotificationHistory records by setting user_id=None
    """
    # Count and delete dismissed patron notifications
    count_dismissed = await db.execute(
        select(func.count())
        .select_from(PatronNotification)
        .where(
            PatronNotification.patron_id == current_user.id,
            PatronNotification.is_dismissed == True,  # noqa: E712
        )
    )
    dismissed_count = count_dismissed.scalar_one()

    await db.execute(
        delete(PatronNotification)
        .where(
            PatronNotification.patron_id == current_user.id,
            PatronNotification.is_dismissed == True,  # noqa: E712
        )
    )

    # Count and anonymize notification history
    count_history = await db.execute(
        select(func.count())
        .select_from(NotificationHistory)
        .where(NotificationHistory.user_id == current_user.id)
    )
    history_count = count_history.scalar_one()

    await db.execute(
        update(NotificationHistory)
        .where(NotificationHistory.user_id == current_user.id)
        .values(user_id=None)
    )

    total_affected = dismissed_count + history_count

    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=current_user.id,
        details={
            "action": "notification_history_cleared",
            "dismissed_notifications_deleted": dismissed_count,
            "history_records_anonymized": history_count,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    return NotificationHistoryClearResponse(deleted_count=total_affected)


# =============================================================================
# AI Conversations
# =============================================================================


@router.get("/ai-conversations", response_model=AIConversationListResponse)
async def list_ai_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the patron's AI conversation history (truncated messages)."""
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.user_id == current_user.id)
        .order_by(AgentConversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()

    count_result = await db.execute(
        select(func.count())
        .select_from(AgentConversation)
        .where(AgentConversation.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    return AIConversationListResponse(
        items=[
            AIConversationListItem(
                id=c.id,
                session_id=c.session_id,
                user_message=c.user_message[:100] if c.user_message else None,
                detected_intent=c.detected_intent,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
            for c in conversations
        ],
        total=total,
    )


@router.get("/ai-conversations/{conversation_id}", response_model=AIConversationDetail)
async def get_ai_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return full detail for a single AI conversation."""
    result = await db.execute(
        select(AgentConversation)
        .where(
            AgentConversation.id == conversation_id,
            AgentConversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return AIConversationDetail(
        id=conversation.id,
        session_id=conversation.session_id,
        user_message=conversation.user_message,
        agent_response=conversation.agent_response,
        conversation_context=conversation.conversation_context,
        detected_intent=conversation.detected_intent,
        helpful=conversation.helpful,
        feedback_note=conversation.feedback_note,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
    )


@router.delete(
    "/ai-conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ai_conversation(
    conversation_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anonymize a single AI conversation."""
    result = await db.execute(
        select(AgentConversation)
        .where(
            AgentConversation.id == conversation_id,
            AgentConversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conversation.user_message = "[deleted]"
    conversation.agent_response = "[deleted]"
    conversation.conversation_context = None
    conversation.user_id = None

    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=current_user.id,
        details={
            "action": "ai_conversation_anonymized",
            "conversation_id": conversation_id,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()


@router.delete("/ai-conversations", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_ai_conversations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anonymize all of the patron's AI conversations."""
    count_result = await db.execute(
        select(func.count())
        .select_from(AgentConversation)
        .where(AgentConversation.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    if total > 0:
        await db.execute(
            update(AgentConversation)
            .where(AgentConversation.user_id == current_user.id)
            .values(
                user_message="[deleted]",
                agent_response="[deleted]",
                conversation_context=None,
                user_id=None,
            )
        )

    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=current_user.id,
        details={
            "action": "all_ai_conversations_anonymized",
            "records_anonymized": total,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()
