# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.email import send_email
from ..models.parent_onboarding import ParentHomeVisit
from ..models.user import User, UserRole
from .organization_features_service import OrganizationFeaturesService
from .parent_onboarding import HomeVisitSafetyService

logger = get_logger(__name__)

SUPERVISOR_ROLES = {UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN}


async def _load_supervisor_emails(db: AsyncSession) -> list[tuple[int, str]]:
    result = await db.execute(
        select(User.id, User.email).where(
            User.role.in_([r.value for r in SUPERVISOR_ROLES]),
            User.email.isnot(None),
        )
    )
    return [(row[0], row[1]) for row in result.all() if row[1]]


def _render_overdue_email_html(
    visit: ParentHomeVisit,
    minutes_overdue: int,
) -> str:
    visitor_name = (
        f"{visit.visitor.first_name} {visit.visitor.last_name}"
        if getattr(visit, "visitor", None) is not None
        else f"User #{visit.visitor_id}"
    )
    return f"""
<html><body style="font-family: -apple-system, sans-serif; color: #111;">
<p style="background:#fee; border:1px solid #c33; padding:12px;
   font-size:16px; color:#900;">
  <strong>SAFETY ALERT:</strong> home visit safety check-out is overdue.
</p>
<table cellpadding="6" style="border-collapse:collapse;">
  <tr><td><strong>Visitor</strong></td><td>{visitor_name}</td></tr>
  <tr><td><strong>Visit ID</strong></td><td>#{visit.id}</td></tr>
  <tr><td><strong>Scheduled date</strong></td><td>{visit.scheduled_date}</td></tr>
  <tr><td><strong>Address</strong></td><td>{visit.address or '(not recorded)'}</td></tr>
  <tr><td><strong>Checked in at</strong></td><td>{visit.safety_checkin_at.isoformat()}</td></tr>
  <tr><td><strong>Check-out due</strong></td><td>{visit.safety_checkout_due_at.isoformat()}</td></tr>
  <tr><td><strong>Minutes overdue</strong></td><td>{minutes_overdue}</td></tr>
</table>
<p>Please attempt to reach the visitor by phone immediately. If you cannot
reach them within 5 minutes, contact local emergency services.</p>
<p style="color:#666; font-size:12px;">This is an automated alert from the
library's lone-worker safety system. You are receiving it because you are
listed as the safety buddy for this visit or hold a supervisor role.</p>
</body></html>
""".strip()


def _coerce_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _dispatch_overdue_alerts(
    db: AsyncSession,
    visit: ParentHomeVisit,
    now: datetime,
) -> dict:
    due = _coerce_aware(visit.safety_checkout_due_at)
    minutes_overdue = int(
        max(0, (now - due).total_seconds() // 60)
    )
    html = _render_overdue_email_html(visit, minutes_overdue)
    subject = f"[SAFETY] Home visit #{visit.id} check-out overdue ({minutes_overdue}m)"

    sent: list[str] = []
    failed: list[str] = []

    # Resend tag names must be unique within a send -- one tag per send
    # keyed to the visit id is safest. See feedback_resend_tag_name_uniqueness.
    tag = f"safety-overdue-visit-{visit.id}"

    async def _send_one(addr: str) -> None:
        if not addr:
            return
        try:
            ok = await send_email(
                to_email=addr,
                subject=subject,
                html_content=html,
                categories=[tag],
                notification_type="home_visit_safety_overdue",
            )
            if ok:
                sent.append(addr)
            else:
                failed.append(addr)
                logger.error(
                    "Safety overdue email returned False",
                    extra={"visit_id": visit.id, "to": addr},
                )
        except Exception:
            failed.append(addr)
            logger.exception(
                "Safety overdue email raised",
                extra={"visit_id": visit.id, "to": addr},
            )

    # Buddy first -- their phone is the staff member's primary fallback.
    if visit.safety_buddy is not None and visit.safety_buddy.email:
        await _send_one(visit.safety_buddy.email)

    # Then every supervisor. Done sequentially because send_email has
    # per-worker Resend pacing baked in (5 req/s cap).
    for _uid, addr in await _load_supervisor_emails(db):
        # Skip the buddy if they're also a supervisor (dedup).
        if visit.safety_buddy is not None and addr == visit.safety_buddy.email:
            continue
        await _send_one(addr)

    return {"sent": sent, "failed": failed, "minutes_overdue": minutes_overdue}


async def scan_and_notify_overdue_visits(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> dict:
    enabled = await OrganizationFeaturesService.is_feature_enabled(
        db, "home_visit_safety_enabled"
    )
    if not enabled:
        return {"scanned": 0, "flagged": 0, "notified_ok": 0, "notified_failed": 0}

    if now is None:
        now = datetime.now(timezone.utc)

    # Only NOT-YET-FLAGGED overdue visits: we never want to double-notify.
    pending = await HomeVisitSafetyService.list_overdue(
        db, include_flagged=False, now=now,
    )
    if not pending:
        return {"scanned": 0, "flagged": 0, "notified_ok": 0, "notified_failed": 0}

    notified_ok = 0
    notified_failed = 0

    for visit in pending:
        # Stamp flag first. If the alert dispatch hangs past the next
        # scheduler tick, the row won't be re-picked.
        await HomeVisitSafetyService.flag_overdue(db, visit, now=now)
        try:
            summary = await _dispatch_overdue_alerts(db, visit, now)
            notified_ok += len(summary["sent"])
            notified_failed += len(summary["failed"])
            logger.warning(
                "Overdue home visit safety alert dispatched",
                extra={
                    "visit_id": visit.id,
                    "sent_to": summary["sent"],
                    "failed_to": summary["failed"],
                    "minutes_overdue": summary["minutes_overdue"],
                },
            )
        except Exception:
            notified_failed += 1
            logger.exception(
                "Overdue alert dispatch raised", extra={"visit_id": visit.id},
            )

    await db.commit()
    return {
        "scanned": len(pending),
        "flagged": len(pending),
        "notified_ok": notified_ok,
        "notified_failed": notified_failed,
    }
