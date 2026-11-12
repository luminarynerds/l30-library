# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Librarian notifications for teacher-driven school_reading actions.

Wraps the in-app ``Notification`` row write + Resend email fan-out so that
the seven teacher-facing routes in ``family_engagement.py`` can call one
function. Notify failures NEVER bubble: the user action is the source of
truth, the helper just logs.

Why a separate module (not ``_shared.py``):
- ``_shared.py`` is auth/scope helpers, intentionally narrow + already
  imported by every sub-router. Putting model + email imports there
  thickens the import graph for routes that don't notify.

Recipient resolution (see CLAUDE memo
``feedback_l30_navconfig_patron_only``-style ``role`` thinking):
- An admin-level FLOOR (LIBRARY_ADMIN / ADMIN / SUPER_ADMIN / DIRECTOR) is
  always notified. Among line STAFF, only those whose ``staff_role`` is in
  ``_CHILDRENS_STAFF_ROLES`` are notified -- so front-desk / circ / pages /
  reference don't get pinged on every teacher action. (Recipients are
  library-wide, not per-school: ``User.school_id`` is teacher-only.)
- ``target_user_id`` still overrides everything (e.g. the slot's
  ``librarian_id``) -- targeted notifications are unaffected.

In-app notification type:
- We reuse ``NotificationType.EVENT_UPDATED`` -- a pre-existing PG enum
  value -- exactly as ``claims_returned_service.py`` does. Adding a new
  enum value requires alembic, which is out of scope.

Skip-noise (cancel within grace window):
- ``NOTIFY_CANCEL_GRACE_SECONDS`` is the module-level config constant.
  When a teacher cancels a booking they made <60s ago, we skip the email
  so librarians aren't pinged for fat-finger fixes. The in-app notification
  is also skipped in this window -- both channels are about awareness, and
  a noisy in-app feed is just as bad as a noisy inbox.
"""

from __future__ import annotations

import asyncio
import contextlib
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....models.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
)
from ....models.outreach import OutreachPartner
from ....models.user import User, UserRole

logger = get_logger(__name__)

# Grace window for cancel-noise suppression. If a teacher cancels a booking
# within this window of having made it, we skip notifying librarians.
NOTIFY_CANCEL_GRACE_SECONDS: int = 60

# Admin-level floor: always notified on teacher/school actions regardless of
# staff_role. (STAFF is intentionally NOT here -- line staff are filtered by
# staff_role below.)
_FLOOR_ROLES = (
    UserRole.LIBRARY_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
)

# staff_role values (for role == STAFF) that also receive notifications.
# Hardcoded default for now; a future admin UI will make this configurable via
# organization_features -- see spec
# 2026-06-07-l30-teacher-notification-recipients-design-PINNED.md.
_CHILDRENS_STAFF_ROLES = ("childrens_librarian", "teen_librarian")


def _staff_outreach_link(frontend_url: str, school_id: int) -> str:
    base = (frontend_url or "").rstrip("/")
    return f"{base}/staff/outreach?schoolId={school_id}"


def _action_verb(action_type: str) -> str:
    return {
        "reading_list_request": "requested",
        "consultation_book": "booked",
        "consultation_cancel": "cancelled",
        "library_visit_request": "requested",
        "library_visit_cancel": "cancelled",
        "family_challenge_join": "joined",
        "training_module_complete": "completed",
    }.get(action_type, "submitted")


def _action_noun(action_type: str) -> str:
    return {
        "reading_list_request": "a reading-list request",
        "consultation_book": "a librarian consultation",
        "consultation_cancel": "a librarian consultation",
        "library_visit_request": "a library visit",
        "library_visit_cancel": "a library visit request",
        "family_challenge_join": "a family reading challenge",
        "training_module_complete": "a training module",
    }.get(action_type, "a teacher action")


def is_within_cancel_grace(created_at: Optional[datetime]) -> bool:
    if created_at is None:
        return False
    # Models use timezone-aware DateTime(timezone=True); coerce naive safely.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - created_at
    return delta.total_seconds() < NOTIFY_CANCEL_GRACE_SECONDS


async def _resolve_recipients(
    db: AsyncSession,
    *,
    target_user_id: Optional[int],
) -> list[User]:
    if target_user_id is not None:
        result = await db.execute(
            select(User).where(User.id == target_user_id, User.is_active == True)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        return [user] if user else []

    result = await db.execute(
        select(User).where(
            User.is_active == True,  # noqa: E712
            or_(
                User.role.in_([r.value for r in _FLOOR_ROLES]),
                and_(
                    User.role == UserRole.STAFF.value,
                    User.staff_role.in_(_CHILDRENS_STAFF_ROLES),
                ),
            ),
        )
    )
    return list(result.scalars().all())


async def _resolve_school(
    db: AsyncSession,
    school_id: Optional[int],
) -> Optional[OutreachPartner]:
    if school_id is None:
        return None
    result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.id == school_id)
    )
    return result.scalar_one_or_none()


def _render_email_html(
    *,
    teacher_name: str,
    school_name: str,
    verb: str,
    noun: str,
    extra_details: Optional[str],
    deep_link: str,
) -> str:
    detail_block = (
        f'<p style="color:#5C4F3D;">{extra_details}</p>' if extra_details else ""
    )
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color:#2C1810;">Teacher action: {verb} {noun}</h2>
        <p>
            <strong>{teacher_name}</strong> at <strong>{school_name}</strong>
            {verb} {noun}.
        </p>
        {detail_block}
        <p>
            <a href="{deep_link}"
               style="display:inline-block; background-color:#D68533; color:#fff;
                      padding:10px 18px; border-radius:6px; text-decoration:none;">
                Open in staff outreach
            </a>
        </p>
        <hr style="border:none; border-top:1px solid #E5E0D8; margin:30px 0;">
        <p style="color:#8B7B6A; font-size:12px;">
            This is an automated staff notification. Reply to the teacher
            directly, or open the link above to manage the request.
        </p>
    </div>
    """


# Strong refs to in-flight background email tasks. asyncio only holds weak
# references to tasks, so without this the fan-out could be garbage-collected
# mid-send once the request handler returns.
_background_email_tasks: set[asyncio.Task] = set()


def _schedule_email_fanout(
    send_email,
    email_jobs: list[tuple[str, str]],
    subject: str,
    html: str,
    action_type: str,
) -> None:
    """Dispatch the Resend fan-out on a background task.

    The teacher's action is already committed by the time we get here; the
    emails are best-effort awareness pings. Running them inline made the
    request wait on one network round-trip per recipient (~18 staff in prod),
    so the teacher saw a multi-second hang. We send them after the response
    instead. ``email_jobs`` carries only plain strings -- no DB session crosses
    into the task (the request-scoped session closes once the response returns).
    """

    async def _runner() -> None:
        for to_email, tag in email_jobs:
            try:
                await send_email(
                    to_email,
                    subject,
                    html,
                    categories=[tag],
                    notification_type=f"teacher_action_{action_type}",
                )
            except Exception:  # noqa: BLE001 - one bad send must not stop the rest
                logger.exception(
                    "Failed to send librarian email for teacher action",
                    extra={"action_type": action_type, "to_email": to_email},
                )

    try:
        task = asyncio.create_task(_runner())
    except RuntimeError:
        # No running loop (e.g. invoked from a sync context). Skip rather than
        # block -- emails are best-effort and the in-app rows already landed.
        logger.warning(
            "No event loop for email fan-out; skipping",
            extra={"action_type": action_type},
        )
        return
    _background_email_tasks.add(task)
    task.add_done_callback(_background_email_tasks.discard)


async def _notify_librarian_of_teacher_action(
    db: AsyncSession,
    *,
    teacher: User,
    school_id: Optional[int],
    action_type: str,
    payload: Optional[dict] = None,
    target_user_id: Optional[int] = None,
    booked_at: Optional[datetime] = None,
) -> None:
    try:
        is_cancel = action_type.endswith("_cancel")
        if is_cancel and is_within_cancel_grace(booked_at):
            logger.info(
                "Skipping librarian notification: cancel within grace window",
                extra={
                    "action_type": action_type,
                    "teacher_user_id": teacher.id,
                    "booked_at": booked_at.isoformat() if booked_at else None,
                },
            )
            return

        recipients = await _resolve_recipients(db, target_user_id=target_user_id)
        if not recipients:
            logger.info(
                "No librarian recipients for teacher action",
                extra={"action_type": action_type, "school_id": school_id},
            )
            return

        school = await _resolve_school(db, school_id)
        school_name = school.name if school else "your school"
        teacher_name = getattr(teacher, "full_name", None) or teacher.email or "A teacher"
        verb = _action_verb(action_type)
        noun = _action_noun(action_type)

        # Defer settings import to runtime so test environments that stub
        # core.config don't need to provide it.
        try:
            from ....core.config import get_settings

            frontend_url = get_settings().frontend_url or ""
        except Exception:  # pragma: no cover - defensive  # noqa: BLE001  # defensive settings import — fall back to empty URL
            frontend_url = ""
        deep_link = _staff_outreach_link(frontend_url, school_id or 0)

        subject = f"{teacher_name} {verb} {noun} at {school_name}"
        context_data = {
            "action_type": action_type,
            "teacher_user_id": teacher.id,
            "teacher_name": teacher_name,
            "school_id": school_id,
            "school_name": school_name,
            "deep_link": deep_link,
            "payload": payload or {},
        }
        extra_details = None
        if payload:
            # One line per payload field, compactly. Keep PII surface low --
            # callers should pass only action metadata (counts, dates, ids).
            extra_details = "<br>".join(
                f"<strong>{k}:</strong> {v}" for k, v in payload.items()
            )

        # --- In-app rows (one per recipient) ------------------------------
        for recipient in recipients:
            try:
                db.add(
                    Notification(
                        user_id=recipient.id,
                        notification_type=NotificationType.EVENT_UPDATED,
                        status=NotificationStatus.SENT,
                        subject=subject,
                        message=(
                            f"{teacher_name} {verb} {noun} at {school_name}."
                        ),
                        context_data=context_data,
                        sent_at=datetime.now(timezone.utc),
                    )
                )
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to enqueue in-app notification",
                    extra={
                        "action_type": action_type,
                        "recipient_user_id": recipient.id,
                    },
                )

        # Flush the in-app rows alongside the caller's commit. The caller
        # already did `await db.commit()` before we got here, so we issue
        # a follow-up commit just for our rows.
        try:
            await db.commit()
        except Exception:
            logger.exception(
                "Failed to commit in-app librarian notification rows",
                extra={"action_type": action_type},
            )
            with contextlib.suppress(Exception):  # noqa: BLE001 - defensive rollback after failed commit
                await db.rollback()

        # --- Email fan-out ------------------------------------------------
        # Lazy import to keep this module importable in test environments
        # that stub email/Resend.
        try:
            from ....core.email import send_email
        except Exception:  # pragma: no cover - defensive  # noqa: BLE001  # defensive lazy import — disable email if unavailable
            send_email = None  # type: ignore

        if send_email is not None:
            html = _render_email_html(
                teacher_name=teacher_name,
                school_name=school_name,
                verb=verb,
                noun=noun,
                extra_details=extra_details,
                deep_link=deep_link,
            )
            # Build plain-data jobs in-path, then dispatch the actual Resend
            # calls on a background task so the teacher's request does not block
            # on N sequential network round-trips (one per recipient). Unique
            # Resend tag per (action, recipient) -- Resend rejects duplicate tag
            # names within a single send, and we want per-recipient analytics.
            email_jobs = [
                (
                    recipient.email,
                    f"teacher_action_{action_type}_u{recipient.id}",
                )
                for recipient in recipients
                if getattr(recipient, "email", None)
            ]
            if email_jobs:
                _schedule_email_fanout(
                    send_email, email_jobs, subject, html, action_type
                )
    except Exception:
        # Top-level safety net: notify failures must not 500 the caller.
        logger.exception(
            "Unhandled error in librarian notification helper",
            extra={"action_type": action_type},
        )
