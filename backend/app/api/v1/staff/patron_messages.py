# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Patron Message Print Queue + Bulk Messaging Endpoints

Two routers in this module:

* ``router`` (prefix ``/staff/messages``) backs the librarian-agent
  print_only / email_or_print delivery modes. Messages written with
  channel=PRINT land here in status=QUEUED; staff fetch the queue, run
  print, then POST mark-printed to flip status to PRINTED.

* ``bulk_router`` (prefix ``/staff/patrons/messages``) backs the bulk-
  message action on the staff Patrons page: one request, many recipients,
  per-recipient status array so partial failure is never silently 200.
"""
from app.core.logging import get_logger
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.database import get_db
from ....core.email import send_email
from ....core.email_safeguards import check_daily_cap
from ....core.pii_audit import log_pii_access
from ....core.shortcuts import get_or_404
from ....models.patron_communication import (
    MessageChannel,
    MessageStatus,
    MessageType,
    PatronMessage,
)
from ....models.user import User
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/messages", tags=["staff-patron-messages"])


class PrintQueueMessage(BaseModel):
    id: int
    patron_id: int
    patron_name: str
    patron_card: Optional[str] = None
    patron_address_line1: Optional[str] = None
    patron_address_line2: Optional[str] = None
    patron_city: Optional[str] = None
    patron_state: Optional[str] = None
    patron_zip_code: Optional[str] = None
    message_type: str
    subject: str
    body: str
    sent_at: datetime
    status: str


class PrintQueueResponse(BaseModel):
    items: list[PrintQueueMessage]
    total: int


@router.get("/print-queue", response_model=PrintQueueResponse)
async def list_print_queue(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Patron messages queued for print delivery (channel=print, status=queued)."""
    count_q = await db.execute(
        select(func.count(PatronMessage.id)).where(
            PatronMessage.channel == MessageChannel.PRINT,
            PatronMessage.status == MessageStatus.QUEUED,
        )
    )
    total = count_q.scalar() or 0

    rows_q = await db.execute(
        select(PatronMessage, User)
        .join(User, User.id == PatronMessage.patron_id)
        .where(
            PatronMessage.channel == MessageChannel.PRINT,
            PatronMessage.status == MessageStatus.QUEUED,
        )
        .order_by(PatronMessage.sent_at.asc())
        .limit(limit)
        .offset(offset)
    )

    items = [
        PrintQueueMessage(
            id=msg.id,
            patron_id=patron.id,
            patron_name=f"{patron.first_name} {patron.last_name}".strip(),
            patron_card=patron.library_card,
            patron_address_line1=patron.address_line1,
            patron_address_line2=patron.address_line2,
            patron_city=patron.city,
            patron_state=patron.state,
            patron_zip_code=patron.zip_code,
            message_type=msg.message_type.value,
            subject=msg.subject,
            body=msg.body,
            sent_at=msg.sent_at,
            status=msg.status.value,
        )
        for msg, patron in rows_q.all()
    ]
    return PrintQueueResponse(items=items, total=total)


@router.post("/{message_id}/mark-printed")
async def mark_message_printed(
    message_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a queued print message as printed. No-op if already printed."""
    msg = await get_or_404(db, PatronMessage, message_id, "Message not found")

    if msg.channel != MessageChannel.PRINT:
        raise HTTPException(
            status_code=400,
            detail=f"Message {message_id} is not on the print channel "
                   f"(channel={msg.channel.value})",
        )

    if msg.status == MessageStatus.PRINTED:
        return {"id": msg.id, "status": msg.status.value, "already_printed": True}

    if msg.status != MessageStatus.QUEUED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark printed from status={msg.status.value}; "
                   f"must be queued",
        )

    msg.status = MessageStatus.PRINTED
    await db.flush()
    return {"id": msg.id, "status": msg.status.value, "already_printed": False}


# ---------------------------------------------------------------------------
# Bulk patron messaging
# ---------------------------------------------------------------------------

bulk_router = APIRouter(
    prefix="/staff/patrons/messages", tags=["staff-patron-bulk-messages"]
)

BulkChannel = Literal["email", "in_app", "sms"]


class BulkMessageRequest(BaseModel):

    patron_ids: list[int] = Field(..., min_length=1, max_length=500)
    template_id: Optional[int] = None
    subject: Optional[str] = Field(None, max_length=500)
    body: str = Field(..., min_length=1, max_length=10000)
    channels: list[BulkChannel] = Field(default_factory=lambda: ["email", "in_app"])


class BulkMessageRecipientResult(BaseModel):

    patron_id: int
    status: Literal["sent", "capped", "failed", "skipped"]
    channels_sent: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class BulkMessageResponse(BaseModel):

    sent: int
    failed: int
    capped: int
    skipped: int
    per_recipient: list[BulkMessageRecipientResult]


def _personalize(text: str, patron: User) -> str:
    full_name = f"{patron.first_name or ''} {patron.last_name or ''}".strip()
    return (
        text.replace("{patron_name}", full_name)
            .replace("{first_name}", patron.first_name or "")
            .replace("{last_name}", patron.last_name or "")
    )


@bulk_router.post("/bulk", response_model=BulkMessageResponse)
async def bulk_send_patron_message(
    payload: BulkMessageRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> BulkMessageResponse:
    settings = get_settings()

    if not payload.channels:
        raise HTTPException(status_code=400, detail="At least one channel is required")

    # Dedup patron_ids preserving order for stable per-recipient ordering.
    seen: set[int] = set()
    ordered_ids = [pid for pid in payload.patron_ids if not (pid in seen or seen.add(pid))]

    # We only read scalar columns (id/email/phone/name) per patron, so no
    # eager-load is required. If the response ever grows to include a
    # relationship field, add selectinload here to dodge MissingGreenlet
    # (feedback_l30_async_property_landmine).
    rows = await db.execute(select(User).where(User.id.in_(ordered_ids)))
    patrons_by_id = {p.id: p for p in rows.scalars().all()}

    subject = payload.subject or f"Message from {settings.app_name}"
    per_recipient: list[BulkMessageRecipientResult] = []
    sent_count = 0
    failed_count = 0
    capped_count = 0
    skipped_count = 0

    # Generate a batch id for Resend tag uniqueness
    # (feedback_resend_tag_name_uniqueness).
    batch_id = int(datetime.utcnow().timestamp())

    for pid in ordered_ids:
        patron = patrons_by_id.get(pid)
        if patron is None:
            per_recipient.append(
                BulkMessageRecipientResult(
                    patron_id=pid, status="failed", reason="patron_not_found"
                )
            )
            failed_count += 1
            continue

        personalized_subject = _personalize(subject, patron)
        personalized_body = _personalize(payload.body, patron)

        channels_sent: list[str] = []
        last_reason: Optional[str] = None
        channel_failed = False
        channel_capped = False

        for channel in payload.channels:
            if channel == "email":
                if not patron.email:
                    last_reason = "no_email_on_file"
                    continue
                # Pre-check the daily cap so we can distinguish "capped"
                # from generic delivery failure in the response.
                try:
                    cap_ok = await check_daily_cap()
                except Exception:  # noqa: BLE001  # safeguards fail-open — proceed if cap check unavailable
                    cap_ok = True  # Safeguards fail-open
                if not cap_ok:
                    logger.warning(
                        "Bulk message hit daily cap mid-batch",
                        extra={
                            "patron_id": patron.id,
                            "staff_user_id": staff_user.id,
                            "batch_id": batch_id,
                        },
                    )
                    channel_capped = True
                    last_reason = "daily_cap_reached"
                    continue

                html_body = (
                    "<div style=\"font-family: Arial, sans-serif; max-width: 600px; "
                    "margin: 0 auto;\">"
                    f"<h2>{personalized_subject}</h2>"
                    f"<div style=\"white-space: pre-wrap;\">{personalized_body}</div>"
                    f"<hr><p style=\"color:#888;font-size:12px;\">"
                    f"{settings.app_name} -- this message was sent by a staff member."
                    "</p></div>"
                )
                try:
                    ok = await send_email(
                        to_email=patron.email,
                        subject=personalized_subject,
                        html_content=html_body,
                        patron_id=patron.id,
                        notification_type="staff_bulk_message",
                        categories=[f"bulk-msg-{batch_id}-{patron.id}"],
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        "Bulk message email send raised",
                        extra={"patron_id": patron.id, "batch_id": batch_id},
                    )
                    last_reason = f"email_error: {str(exc)[:120]}"
                    channel_failed = True
                    continue

                msg_row = PatronMessage(
                    patron_id=patron.id,
                    sender_id=staff_user.id,
                    message_type=MessageType.CUSTOM,
                    channel=MessageChannel.EMAIL,
                    subject=personalized_subject,
                    body=personalized_body,
                    recipient_email=patron.email,
                    delivered=bool(ok),
                    status=MessageStatus.SENT if ok else MessageStatus.FAILED,
                    delivery_error=None if ok else "email send returned False",
                )
                db.add(msg_row)
                if ok:
                    channels_sent.append("email")
                else:
                    channel_failed = True
                    last_reason = "email_delivery_failed"

            elif channel == "in_app":
                # In-app delivery requires a STAFF_MESSAGE entry in the
                # PatronNotificationCategory enum (DB-side). Adding it is a
                # follow-up migration; for now surface as skipped with a
                # clear reason so the UI can explain.
                last_reason = "in_app_pending_enum_migration"

            elif channel == "sms":
                # Mirror the single-patron send path: SMS provider is not yet
                # configured. Record and report rather than failing the whole
                # recipient.
                if not patron.phone:
                    last_reason = "no_phone_on_file"
                    continue
                last_reason = "sms_provider_not_configured"
                # Surface as skipped (not failed) so the caller can distinguish
                # "we tried but the platform doesn't support SMS yet" from a
                # genuine delivery error.

        if channels_sent:
            per_recipient.append(
                BulkMessageRecipientResult(
                    patron_id=pid,
                    status="sent",
                    channels_sent=channels_sent,
                    reason=last_reason,
                )
            )
            sent_count += 1
        elif channel_capped:
            per_recipient.append(
                BulkMessageRecipientResult(
                    patron_id=pid, status="capped", reason=last_reason or "daily_cap_reached"
                )
            )
            capped_count += 1
        elif channel_failed:
            per_recipient.append(
                BulkMessageRecipientResult(
                    patron_id=pid, status="failed", reason=last_reason or "delivery_failed"
                )
            )
            failed_count += 1
        else:
            per_recipient.append(
                BulkMessageRecipientResult(
                    patron_id=pid,
                    status="skipped",
                    reason=last_reason or "no_deliverable_channel",
                )
            )
            skipped_count += 1

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Bulk message persistence failed", extra={"batch_id": batch_id})
        raise HTTPException(status_code=500, detail="Failed to persist message history") from None

    # One audit log per request with the full recipient list. Reading patron
    # email/phone/name for personalization counts as PII access.
    try:
        await log_pii_access(
            db=db,
            user_id=staff_user.id,
            user_role=staff_user.role,
            endpoint="/api/v1/staff/patrons/messages/bulk",
            fields_accessed=["email", "phone", "first_name", "last_name"],
            fields_redacted=[],
            patron_ids_accessed=ordered_ids,
            additional_context={
                "batch_id": batch_id,
                "channels": list(payload.channels),
                "sent": sent_count,
                "failed": failed_count,
                "capped": capped_count,
                "skipped": skipped_count,
            },
        )
        await db.commit()
    except Exception:
        # Audit failure must not break the user-visible response.
        logger.exception("PII audit log for bulk message failed")

    return BulkMessageResponse(
        sent=sent_count,
        failed=failed_count,
        capped=capped_count,
        skipped=skipped_count,
        per_recipient=per_recipient,
    )
