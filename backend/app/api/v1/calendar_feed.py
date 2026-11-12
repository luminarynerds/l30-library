# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Per-patron iCal feed of due dates and ready holds.

Two endpoints:

* ``POST /api/v1/me/calendar/token`` (auth required) -- mints a stable
  signed subscription URL for the calling patron. Token has no expiry;
  it is bound to ``user_id`` via an HMAC-SHA256 signature using the app
  JWT secret. Future revoke surface would invalidate by rotating
  ``JWT_SECRET_KEY`` or adding a per-user revocation marker (separate PR).

* ``GET /api/v1/me/calendar.ics?token=...`` -- public, unauthenticated;
  the signed token is the bearer of identity. Returns an RFC 5545
  VCALENDAR body with one VEVENT per active checkout (due date) and one
  per ready hold (pickup window).

The iCal body is hand-rolled to match the pattern in
``book_clubs_patron.py`` -- the ``icalendar`` library is not a backend
dep. All-day VEVENTs use ``VALUE=DATE`` with the local-date form
``YYYYMMDD`` (RFC 5545 section 3.3.4).
"""

from __future__ import annotations

import hashlib
import hmac
from app.core.logging import get_logger
from app.core.branding import branding
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.config import get_settings
from ...core.database import get_db
from ...models.circulation import (
    Checkout,
    CheckoutStatus,
    Hold,
    HoldStatus,
)
from ...models.user import User
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/me", tags=["account"])


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

_TOKEN_PURPOSE = "calendar"


def _signing_key() -> bytes:
    s = get_settings()
    key = (s.jwt_secret_key or s.secret_key or "").encode("utf-8")
    if not key:
        # Defensive: should never happen with a real config.
        raise RuntimeError("No signing key configured (JWT_SECRET_KEY/SECRET_KEY)")
    return key


def _sign(user_id: int) -> str:
    msg = f"{user_id}|{_TOKEN_PURPOSE}".encode("utf-8")
    return hmac.new(_signing_key(), msg, hashlib.sha256).hexdigest()


def mint_calendar_token(user_id: int) -> str:
    return f"{user_id}.{_sign(user_id)}"


def verify_calendar_token(token: str) -> int:
    if not token or "." not in token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_part, sig = token.split(".", 1)
    try:
        user_id = int(user_part)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    expected = _sign(user_id)
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


# ---------------------------------------------------------------------------
# iCal helpers
# ---------------------------------------------------------------------------

# Hand-rolled per RFC 5545. CRLF line endings, no line folding (our values
# are short). Backslash MUST be escaped before the other special chars to
# avoid double-escaping.

def _ical_escape(value: str | None) -> str:
    if not value:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _fmt_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fmt_date(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%d")


def _item_title(item) -> str:
    if item is None:
        return "Library item"
    return getattr(item, "title", None) or "Library item"


async def _fetch_checkouts(db: AsyncSession, user_id: int) -> list[Checkout]:
    q = (
        select(Checkout)
        .where(Checkout.user_id == user_id)
        .where(Checkout.status == CheckoutStatus.active)
        .options(selectinload(Checkout.item))
        .order_by(Checkout.due_date.asc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def _fetch_ready_holds(db: AsyncSession, user_id: int) -> list[Hold]:
    q = (
        select(Hold)
        .where(Hold.user_id == user_id)
        .where(Hold.status == HoldStatus.ready)
        .options(selectinload(Hold.item), selectinload(Hold.pickup_location))
        .order_by(Hold.expires_at.asc().nulls_last())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


def _build_ics(
    checkouts: list[Checkout],
    holds: list[Hold],
    now: datetime,
) -> str:
    dtstamp = _fmt_utc(now)
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{branding.library_name}//Patron Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Library: due dates & holds",
    ]

    for co in checkouts:
        if not co.due_date:
            continue
        date = _fmt_date(co.due_date)
        title = _item_title(co.item)
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:l30-checkout-{co.id}@example.com",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{date}",
            f"SUMMARY:Library item due: {_ical_escape(title)}",
            "END:VEVENT",
        ])

    for h in holds:
        ready_at = h.notified_at or h.updated_at or h.created_at
        if not ready_at:
            continue
        start_date = _fmt_date(ready_at)
        title = _item_title(h.item)
        branch_name = (
            getattr(h.pickup_location, "name", None)
            if h.pickup_location is not None
            else None
        )
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:l30-hold-{h.id}@example.com",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{start_date}",
        ])
        if h.expires_at:
            lines.append(f"DTEND;VALUE=DATE:{_fmt_date(h.expires_at)}")
        lines.append(f"SUMMARY:Hold ready for pickup: {_ical_escape(title)}")
        if branch_name:
            lines.append(f"LOCATION:{_ical_escape(branch_name)}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/calendar/token")
async def mint_calendar_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Mint a stable webcal:// subscription URL for the calling patron.

    The token is HMAC-signed over ``{user_id}|calendar`` and has no expiry.
    Future revoke surface would either rotate ``JWT_SECRET_KEY`` (invalidates
    all subscriptions) or add a per-user revocation column (separate PR).
    """
    token = mint_calendar_token(current_user.id)
    # Build the webcal:// URL off the request host so the URL points back at
    # whichever host the SPA is talking to (prod, staging, dev). The webcal
    # scheme is mandatory for "Add to Apple Calendar" subscribe flows.
    host = request.url.netloc or "l30.org"
    webcal_url = f"webcal://{host}/api/v1/me/calendar.ics?token={token}"
    return {"url": webcal_url}


@router.get("/calendar.ics")
async def patron_calendar_feed(
    token: str = Query(..., description="Signed subscription token"),
    db: AsyncSession = Depends(get_db),
):
    """Return the patron's personal iCal feed.

    Authentication is via the signed token in the query string -- this is
    the only way Calendar clients (Apple Calendar, Google Calendar, Outlook)
    can fetch a personalised feed, since webcal:// subscriptions cannot
    send Authorization headers.
    """
    user_id = verify_calendar_token(token)
    checkouts = await _fetch_checkouts(db, user_id)
    holds = await _fetch_ready_holds(db, user_id)
    body = _build_ics(checkouts, holds, datetime.now(timezone.utc))
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="l30-calendar.ics"',
            "Cache-Control": "private, max-age=300",
        },
    )
