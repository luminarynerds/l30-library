# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.email import send_email
from ..models.parent_onboarding import ParentOnboardingFollowup
from .parent_onboarding import FollowupService

logger = get_logger(__name__)


# Resend tag names. MUST stay distinct across the two passes per
# feedback_resend_tag_name_uniqueness. Keep them stable -- existing Resend
# analytics queries reference these names.
TAG_DUE_TOMORROW = "parent-onboarding-followup-reminder"
TAG_OVERDUE = "parent-onboarding-followup-overdue"


def _group_by_assignee(
    followups: Iterable[ParentOnboardingFollowup],
) -> dict[int, list[ParentOnboardingFollowup]]:
    grouped: dict[int, list[ParentOnboardingFollowup]] = defaultdict(list)
    for f in followups:
        grouped[f.assignee_id].append(f)
    return grouped


def _format_due_tomorrow_html(
    followups: list[ParentOnboardingFollowup],
) -> str:
    rows = "".join(
        f'<tr><td style="padding:6px;border-bottom:1px solid #ddd;">'
        f'<strong>{f.title}</strong><br>'
        f'<span style="color:#666;font-size:12px;">Session #{f.session_id}'
        f'</span></td>'
        f'<td style="padding:6px;border-bottom:1px solid #ddd;">'
        f'{f.due_date.isoformat()}</td></tr>'
        for f in followups
    )
    return f"""
<html><body style="font-family: -apple-system, sans-serif; color: #111;">
<h2 style="font-size:18px;">Follow-up tasks due tomorrow</h2>
<p>You have {len(followups)} follow-up task(s) coming due tomorrow.</p>
<table cellpadding="0" cellspacing="0"
       style="border-collapse:collapse; width:100%; max-width:560px;">
  <thead><tr style="background:#f5f5f5;">
    <th align="left" style="padding:6px;">Task</th>
    <th align="left" style="padding:6px;">Due</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<p style="margin-top:16px; color:#666; font-size:12px;">
  This is an automated reminder from the library's parent-onboarding system.
</p>
</body></html>
"""


def _format_overdue_html(
    followups: list[ParentOnboardingFollowup], today: date,
) -> str:
    rows = "".join(
        f'<tr><td style="padding:6px;border-bottom:1px solid #ddd;">'
        f'<strong>{f.title}</strong><br>'
        f'<span style="color:#666;font-size:12px;">Session #{f.session_id}'
        f'</span></td>'
        f'<td style="padding:6px;border-bottom:1px solid #ddd; color:#c33;">'
        f'{(today - f.due_date).days} day(s) overdue</td></tr>'
        for f in followups
    )
    return f"""
<html><body style="font-family: -apple-system, sans-serif; color: #111;">
<h2 style="font-size:18px; color:#c33;">Overdue follow-up tasks</h2>
<p>You have {len(followups)} follow-up task(s) past their due date.</p>
<table cellpadding="0" cellspacing="0"
       style="border-collapse:collapse; width:100%; max-width:560px;">
  <thead><tr style="background:#f5f5f5;">
    <th align="left" style="padding:6px;">Task</th>
    <th align="left" style="padding:6px;">Status</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<p style="margin-top:16px; color:#666; font-size:12px;">
  This is an automated reminder from the library's parent-onboarding system.
</p>
</body></html>
"""


async def _send_pass(
    db: AsyncSession,
    *,
    target_date: date,
    tag: str,
    subject_template: str,
    html_builder,
) -> dict:
    followups = await FollowupService.list_due_on(db, target_date)
    if not followups:
        return {"assignees": 0, "sent_ok": 0, "sent_failed": 0}

    grouped = _group_by_assignee(followups)
    sent_ok = 0
    sent_failed = 0

    for assignee_id, items in grouped.items():
        assignee = items[0].assignee
        if assignee is None or not assignee.email:
            logger.info(
                "Skipping follow-up reminder: assignee has no email",
                extra={"assignee_id": assignee_id, "count": len(items)},
            )
            continue
        subject = subject_template.format(count=len(items))
        html = html_builder(items)
        try:
            ok = await send_email(
                to_email=assignee.email,
                subject=subject,
                html_content=html,
                categories=[tag],
                notification_type="parent_onboarding_followup",
            )
            if ok:
                sent_ok += 1
            else:
                sent_failed += 1
                logger.warning(
                    "Follow-up reminder email returned False -- daily cap?",
                    extra={
                        "assignee_id": assignee_id,
                        "tag": tag,
                        "count": len(items),
                    },
                )
        except Exception:
            sent_failed += 1
            logger.exception(
                "Follow-up reminder email raised",
                extra={"assignee_id": assignee_id, "tag": tag},
            )

    return {
        "assignees": len(grouped),
        "sent_ok": sent_ok,
        "sent_failed": sent_failed,
    }


async def run_due_tomorrow_pass(
    db: AsyncSession, *, today: date | None = None,
) -> dict:
    if today is None:
        today = date.today()
    summary = await _send_pass(
        db,
        target_date=today + timedelta(days=1),
        tag=TAG_DUE_TOMORROW,
        subject_template="Follow-up due tomorrow: {count} task(s)",
        html_builder=_format_due_tomorrow_html,
    )
    logger.info(
        "Parent-onboarding due-tomorrow reminders dispatched",
        extra={**summary, "target_date": (today + timedelta(days=1)).isoformat()},
    )
    return summary


async def run_overdue_pass(
    db: AsyncSession, *, today: date | None = None,
) -> dict:
    if today is None:
        today = date.today()
    # Closure to bind `today` for the formatter.
    def _builder(items):
        return _format_overdue_html(items, today)
    summary = await _send_pass(
        db,
        target_date=today,
        tag=TAG_OVERDUE,
        subject_template="Follow-ups overdue: {count} task(s)",
        html_builder=_builder,
    )
    logger.info(
        "Parent-onboarding overdue reminders dispatched",
        extra={**summary, "target_date": today.isoformat()},
    )
    return summary
