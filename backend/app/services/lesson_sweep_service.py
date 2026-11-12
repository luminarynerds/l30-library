# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.email import send_email
from ..core.email_safeguards import email_cap_remaining
from ..models.learning import Course, Lesson, Module
from ..models.user import User

logger = get_logger(__name__)

#: Lessons whose age exceeds this threshold and which still look empty
#: are candidates for deletion. 24h matches the W1-B plan.
SWEEP_TTL_HOURS = 24


@dataclass
class SweepResult:

    status: str  # "ok" | "deferred_email_cap" | "noop"
    deleted_count: int
    deferred_until: Optional[datetime] = None


def _looks_empty(lesson: Lesson) -> bool:
    title = (lesson.title or "").strip()
    if title:
        return False
    content = lesson.content or {}
    if not isinstance(content, dict):
        return False
    body = content.get("body")
    if body is None:
        return True
    if isinstance(body, str) and not body.strip():
        return True
    return False


async def find_sweep_candidates(db: AsyncSession) -> List[Lesson]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SWEEP_TTL_HOURS)
    stmt = select(Lesson).where(
        Lesson.title == "",
        Lesson.created_at < cutoff,
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return [lesson for lesson in rows if _looks_empty(lesson)]


async def _build_recipients(
    db: AsyncSession, lessons: List[Lesson]
) -> list[dict]:
    by_creator: dict[int, list[Lesson]] = {}
    for lesson in lessons:
        module = await db.get(Module, lesson.module_id)
        if module is None:
            continue
        course = await db.get(Course, module.course_id)
        if course is None or course.created_by_id is None:
            continue  # historical / orphaned: skip email, sweep still runs
        by_creator.setdefault(course.created_by_id, []).append(lesson)

    recipients: list[dict] = []
    for user_id, items in by_creator.items():
        user = await db.get(User, user_id)
        if user is None or not user.email:
            # FK set-null fired between course load and now, or no addr.
            continue
        recipients.append(
            {"user_id": user_id, "email": user.email, "lessons": items}
        )
    return recipients


def _render_digest_html(recipient: dict) -> str:
    lesson_lines = "".join(
        f"<li>Module #{lesson.module_id} -- lesson #{lesson.id}"
        f" (created {lesson.created_at.strftime('%Y-%m-%d %H:%M UTC')})</li>"
        for lesson in recipient["lessons"]
    )
    return (
        '<!doctype html><html><body style="font-family:system-ui;'
        'max-width:640px;margin:2rem auto;padding:1rem;">'
        "<h1>Empty course-authoring stubs about to be removed</h1>"
        "<p>The following empty lesson stubs from your courses have been "
        "inactive for over 24 hours and are scheduled for cleanup. If you "
        "still want to keep any of these, open them in the lesson editor "
        "and add a title or content. Otherwise no action is needed.</p>"
        f"<ul>{lesson_lines}</ul>"
        "<p>This message is sent by the course-authoring stub-sweep "
        "(Wave 1 / W1-B). It runs once nightly.</p>"
        "</body></html>"
    )


async def send_pre_sweep_emails(recipients: list[dict]) -> None:
    for recipient in recipients:
        try:
            await send_email(
                to_email=recipient["email"],
                subject="Empty course-authoring stubs about to be removed",
                html_content=_render_digest_html(recipient),
                categories=["course_authoring_stub_sweep"],
                patron_id=recipient["user_id"],
                notification_type="course_authoring_stub_sweep",
            )
        except Exception:
            logger.exception(
                "lesson_sweep: send_email failed for user_id=%s",
                recipient["user_id"],
            )


async def perform_sweep(db: AsyncSession) -> SweepResult:
    candidates = await find_sweep_candidates(db)
    if not candidates:
        return SweepResult(status="noop", deleted_count=0)

    recipients = await _build_recipients(db, candidates)
    needed = len(recipients)
    # Only check the cap if we actually need to send anything. Orphan-only
    # sweeps (all candidates from historical NULL-creator courses) need
    # zero emails and can always proceed.
    if needed > 0:
        try:
            remaining = await email_cap_remaining()
        except Exception:
            # email_cap_remaining is designed to fail open, but belt-and-
            # suspenders: if it raises for any reason, assume the worst
            # and defer rather than risk silent drops.
            logger.exception("lesson_sweep: email_cap_remaining raised; deferring")
            remaining = 0

        if remaining < needed:
            sentry_sdk.add_breadcrumb(
                category="authoring",
                message="stub_sweep_deferred_email_cap",
                level="warning",
                data={
                    "candidates": len(candidates),
                    "recipients_needed": needed,
                    "cap_remaining": remaining,
                },
            )
            logger.warning(
                "lesson_sweep deferred: email cap remaining=%s < needed=%s "
                "(candidates=%s)",
                remaining,
                needed,
                len(candidates),
            )
            return SweepResult(
                status="deferred_email_cap",
                deleted_count=0,
                deferred_until=datetime.now(timezone.utc) + timedelta(days=1),
            )

        await send_pre_sweep_emails(recipients)

    deleted = 0
    for lesson in candidates:
        await db.delete(lesson)
        deleted += 1
    await db.commit()
    logger.info(
        "lesson_sweep ok: deleted=%s recipients=%s",
        deleted,
        needed,
    )
    return SweepResult(status="ok", deleted_count=deleted)
