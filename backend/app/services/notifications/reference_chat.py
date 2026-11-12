# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.email import send_email
from ...models.ai_agents import AgentConversation
from ...models.notification import (
    PatronNotification,
    PatronNotificationCategory,
)
from ...models.user import User

from .templates import render_staff_reply_email

logger = get_logger(__name__)
settings = get_settings()


async def send_staff_reply_notification(
    db: AsyncSession,
    staff_reply: AgentConversation,
) -> None:
    context = staff_reply.conversation_context or {}
    if not context.get("staff_reply"):
        logger.warning(
            "send_staff_reply_notification called on non-staff-reply row %s",
            staff_reply.id,
        )
        return

    # 1. Resolve patron + recipient email
    patron: Optional[User] = None
    if staff_reply.user_id:
        patron = (
            await db.execute(select(User).where(User.id == staff_reply.user_id))
        ).scalar_one_or_none()

    recipient_email: Optional[str] = (
        patron.email if patron and patron.email else None
    )
    if not recipient_email:
        followup = await db.execute(
            select(AgentConversation.patron_followup_email)
            .where(
                AgentConversation.session_id == staff_reply.session_id,
                AgentConversation.patron_followup_email.is_not(None),
            )
            .limit(1)
        )
        recipient_email = followup.scalar_one_or_none()

    # 2. Find the patron's original question for email context (the most
    # recent prior turn on the same session).
    q_result = await db.execute(
        select(AgentConversation)
        .where(
            AgentConversation.session_id == staff_reply.session_id,
            AgentConversation.id < staff_reply.id,
        )
        .order_by(AgentConversation.id.desc())
        .limit(1)
    )
    prior = q_result.scalar_one_or_none()
    patron_question = prior.user_message if prior else "(no question recorded)"

    staff_name = context.get("staff_name") or "A librarian"
    patron_display = (patron.first_name if patron and patron.first_name else "Patron")

    library_name = getattr(settings, "library_name", None) or "your library"
    public_base = (getattr(settings, "frontend_url", None) or "").rstrip("/")
    chat_url = f"{public_base}/account/conversations/{staff_reply.session_id}"

    # 3. In-app notification (logged-in patrons only) — idempotent.
    if patron:
        source_event_id = f"staff_reply:{staff_reply.id}"
        existing = await db.execute(
            select(PatronNotification.id).where(
                PatronNotification.source_event_id == source_event_id
            )
        )
        if existing.scalar_one_or_none() is None:
            notif = PatronNotification(
                patron_id=patron.id,
                category=PatronNotificationCategory.REFERENCE_CHAT_REPLY,
                title=f"{staff_name} answered your question",
                # Truncate to 500 chars for in-app notification preview; full reply lives in the chat.
                message=(staff_reply.agent_response or "")[:500],
                source_event_type="staff_reply",
                source_event_id=source_event_id,
                action_url=f"/account/conversations/{staff_reply.session_id}",
                action_label="View reply",
            )
            db.add(notif)
            try:
                await db.commit()
            except IntegrityError:
                # Another concurrent dispatcher won the race; the unique
                # constraint on source_event_id confirms the notification
                # already exists, so this is a safe no-op.
                await db.rollback()

    # 4. Email — only when we have a recipient address.
    if recipient_email:
        subject, html_body = render_staff_reply_email(
            patron_name=patron_display,
            staff_name=staff_name,
            patron_question=patron_question,
            staff_response=staff_reply.agent_response or "",
            chat_url=chat_url,
            library_name=library_name,
        )
        try:
            ok = await send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=html_body,
            )
        except Exception:
            logger.exception(
                "Failed to send staff-reply email for conv %s to %s",
                staff_reply.id,
                recipient_email,
            )
            ok = False
        if not ok:
            logger.warning(
                "send_email returned False for staff-reply conv %s to %s",
                staff_reply.id,
                recipient_email,
            )
    else:
        logger.info(
            "Staff reply %s on session %s has no patron contact (anon, no followup_email); skipping email",
            staff_reply.id,
            staff_reply.session_id,
        )
