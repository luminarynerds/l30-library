# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import html as html_lib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.email import COLORS, send_email
from app.core.logging import get_logger
from app.models.release_tracker import TrackerBook
from app.services.indie_release_ingestion import INDIE_SOURCES

logger = get_logger(__name__)

DIGEST_CAP = 50
WINDOW_DAYS = 7

_SOURCE_LABELS = {
    "indie_mastodon": "Mastodon (buzz-gated)",
    "indie_itchio": "itch.io books",
}


def _recipient() -> str | None:
    return get_settings().recruitment_digest_email


async def _compute_window(db: AsyncSession) -> list[TrackerBook]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    stmt = (
        select(TrackerBook)
        .where(TrackerBook.source.in_(INDIE_SOURCES), TrackerBook.created_at >= cutoff)
        .options(selectinload(TrackerBook.author))
        .order_by(TrackerBook.created_at.asc())
        .limit(DIGEST_CAP)
    )
    return list((await db.execute(stmt)).scalars().all())


def _render(books: list[TrackerBook], capped: bool) -> str:
    rows = []
    for b in books:
        # title/author/source_url originate from public social posts relayed by the
        # LLM extractor -- escape everything external before it touches email HTML.
        author = html_lib.escape(b.author.name if b.author else "Unknown")
        title = html_lib.escape(str(b.title))
        meta = " -- ".join(
            part
            for part in (
                _SOURCE_LABELS.get(str(b.source), html_lib.escape(str(b.source))),
                html_lib.escape(str(b.blurb_credit or "")),
                f"ISBN {html_lib.escape(str(b.isbn_13))}" if b.isbn_13 else "unresolved (not in Google Books yet)",
                html_lib.escape(str(b.release_date)) if b.release_date else "",
            )
            if part
        )
        evidence = (
            f'<a href="{html_lib.escape(str(b.source_url), quote=True)}">source post</a>'
            if b.source_url
            else "no source link"
        )
        rows.append(
            f'<li style="margin: 10px 0; color: {COLORS["body"]};">'
            f"<strong>{title}</strong> by {author}<br>"
            f'<span style="font-size: 13px;">{meta} -- {evidence}</span></li>'
        )
    cap_note = (
        f'<p style="color: {COLORS["text_light"]};">Capped at {DIGEST_CAP}; more in the staff view.</p>'
        if capped
        else ""
    )
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Indie recruitment digest</h2>
        <p>New indie/self-published titles that cleared the buzz gate this week.
           Candidates for MetisLib author outreach; review and feature the good
           ones in Staff &rarr; Acquisitions &rarr; Releases (source filter: Indie).</p>
        <ul style="padding-left: 20px; list-style: none;">{"".join(rows)}</ul>
        {cap_note}
    </div>
    """


async def send_recruitment_digest(db: AsyncSession, dry_run: bool = False) -> bool:
    """Email the weekly indie recruitment digest. Stateless 7-day window; no-op (False)
    when no recipient is configured or the window is empty."""
    recipient = _recipient()
    if not recipient:
        logger.info("Recruitment digest skipped: RECRUITMENT_DIGEST_EMAIL not set")
        return False
    books = await _compute_window(db)
    if not books:
        logger.info("Recruitment digest skipped: no indie titles in window")
        return False
    capped = len(books) == DIGEST_CAP
    n = len(books)
    subject = f"Indie recruitment digest -- {n} candidate{'s' if n != 1 else ''} this week"
    html = _render(books, capped)
    if dry_run:
        logger.info("Recruitment digest dry-run", extra={"count": n, "capped": capped})
        return True
    sent = await send_email(
        to_email=recipient,
        subject=subject,
        html_content=html,
        categories=["recruitment_digest"],
    )
    if not sent:
        logger.warning("Recruitment digest send refused by email layer")
        return False
    logger.info("Recruitment digest sent", extra={"count": n, "to": recipient})
    return True
