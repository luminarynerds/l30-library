# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import AsyncSessionLocal
from ..core.email import send_email
from ..models.blog import BlogPost, BlogPostStatus
from ..models.blog_subscription import BlogEmailSubscription

logger = get_logger(__name__)


_FREQUENCY_WINDOWS = {
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


def _window_for(frequency: str) -> timedelta:
    return _FREQUENCY_WINDOWS.get(frequency, _FREQUENCY_WINDOWS["weekly"])


def _build_unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/api/v1/blog/unsubscribe?token={token}"


def _render_digest_html(posts: Iterable[BlogPost], unsubscribe_url: str) -> str:
    settings = get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    items_html: list[str] = []
    for p in posts:
        url = f"{base}/blog/{p.slug}"
        tldr = (p.tldr or "").strip()
        tldr_html = f"<p>{tldr}</p>" if tldr else ""
        items_html.append(
            f'<article style="margin-bottom:1.5rem;">'
            f'<h3><a href="{url}">{p.title}</a></h3>'
            f"{tldr_html}"
            f'<p><a href="{url}">Read more</a></p>'
            f"</article>"
        )
    body = "\n".join(items_html) or "<p>No new posts this cycle.</p>"
    return (
        "<!doctype html><html><body style=\"font-family:system-ui;max-width:640px;margin:2rem auto;padding:1rem;\">"
        "<h1>Library blog digest</h1>"
        f"{body}"
        f'<hr><p style="font-size:0.85em;color:#666;">'
        f'You are receiving this digest because you subscribed at {base}.'
        f' <a href="{unsubscribe_url}">Unsubscribe</a>.</p>'
        "</body></html>"
    )


async def _gather_new_posts(
    db: AsyncSession, since: datetime
) -> list[BlogPost]:
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.status == BlogPostStatus.published,
            BlogPost.published_at != None,  # noqa: E711 SQL IS NOT NULL
            BlogPost.published_at > since,
        )
        .order_by(BlogPost.published_at.desc())
    )
    return list(result.scalars().all())


async def _process_one(
    db: AsyncSession, sub: BlogEmailSubscription, now: datetime
) -> str:
    window = _window_for(sub.frequency)
    since = sub.last_sent_at or (now - window)

    # Frequency-window guard: if we've sent within the window, skip.
    if sub.last_sent_at is not None and (now - sub.last_sent_at) < window:
        return "skipped_window"

    posts = await _gather_new_posts(db, since)
    if not posts:
        return "skipped_no_posts"

    unsubscribe_url = _build_unsubscribe_url(sub.unsubscribe_token)
    html = _render_digest_html(posts, unsubscribe_url)

    sent = await send_email(
        to_email=sub.email,
        subject=f"Library blog digest -- {len(posts)} new post{'s' if len(posts) != 1 else ''}",
        html_content=html,
        categories=[f"blog_digest_{sub.frequency}"],
        unsubscribe_url=unsubscribe_url,
        patron_id=sub.user_id,
        notification_type=f"blog_digest_{sub.frequency}",
    )
    if not sent:
        # send_email returns False on cap/dedup/transport failure; do NOT
        # update last_sent_at so the next run can retry.
        logger.warning(
            "Blog digest send returned False",
            extra={"subscription_id": sub.id, "email": sub.email},
        )
        return "skipped_window"  # treat as not-sent

    sub.last_sent_at = now
    await db.commit()
    return "sent"


async def send_blog_digests(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.confirmed_at.is_not(None)
        )
    )
    # Snapshot identifiers eagerly so a per-row rollback (which expires all
    # attached objects in SQLAlchemy async sessions) cannot break iteration
    # via lazy-load → MissingGreenlet on the next sub.id access.
    sub_ids: list[tuple[int, str]] = [(s.id, s.email) for s in result.scalars().all()]

    counters = {
        "considered": len(sub_ids),
        "sent": 0,
        "skipped_window": 0,
        "skipped_no_posts": 0,
        "failed": 0,
    }
    for sub_id, sub_email in sub_ids:
        # Re-fetch a fresh, attached row for this iteration. After a prior
        # row's rollback the identity map is expired; loading by PK gives us
        # a clean ORM object we can safely mutate (e.g., set last_sent_at).
        sub = await db.get(BlogEmailSubscription, sub_id)
        if sub is None:
            continue
        try:
            outcome = await _process_one(db, sub, now)
            counters[outcome] = counters.get(outcome, 0) + 1
        except Exception:
            counters["failed"] += 1
            logger.exception(
                "Blog digest send failed for subscription %s", sub_id,
                extra={"subscription_id": sub_id, "email": sub_email},
            )
            # Roll back any partial state from the failure on this row so
            # the next iteration starts clean.
            with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort rollback in batch loop
                await db.rollback()

    logger.info("Blog digest run finished: %s", counters)
    return counters


async def send_blog_digests_job() -> None:
    async with AsyncSessionLocal() as db:
        await send_blog_digests(db)
