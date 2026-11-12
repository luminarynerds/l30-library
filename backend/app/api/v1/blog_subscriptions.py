# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Blog email digest subscription endpoints.

Lives in its own router (NOT in blog.py) to avoid merge conflicts with
in-flight blog UI PRs. Mounted alongside blog.router in registry.py.

Endpoints:
    POST   /api/v1/blog/subscribe         -- public; create or re-confirm a subscription
    GET    /api/v1/blog/confirm           -- public; verify confirmation token
    GET    /api/v1/blog/unsubscribe       -- public; verify unsubscribe token, removes subscription
    GET    /api/v1/blog/subscriptions/me  -- authed; current user's subscriptions

Tokens are random URL-safe strings (existing codebase pattern via
``secrets.token_urlsafe``); no itsdangerous dependency.
"""
from app.core.logging import get_logger
import secrets
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_optional_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.rate_limit import limiter
from app.models.blog_subscription import BlogEmailSubscription
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/blog", tags=["blog-subscriptions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SubscribeRequest(BaseModel):
    email: EmailStr
    frequency: Literal["weekly", "monthly"] = Field(default="weekly")


class SubscribeResponse(BaseModel):
    status: str  # "subscribed" | "already_subscribed" | "pending_confirmation"
    already_subscribed: bool = False
    frequency: str
    email: str


class SubscriptionItem(BaseModel):
    id: int
    email: str
    frequency: str
    confirmed: bool
    last_sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionsListResponse(BaseModel):
    items: list[SubscriptionItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _build_unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/api/v1/blog/unsubscribe?token={token}"


def _build_confirm_url(token: str) -> str:
    settings = get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/api/v1/blog/confirm?token={token}"


async def _send_confirmation_email(email: str, confirm_token: str, unsubscribe_token: str) -> bool:
    confirm_url = _build_confirm_url(confirm_token)
    unsubscribe_url = _build_unsubscribe_url(unsubscribe_token)
    html = f"""\
<!doctype html>
<html><body>
<h2>Confirm your blog digest subscription</h2>
<p>Thanks for subscribing! Click the link below to confirm and start
receiving the digest:</p>
<p><a href="{confirm_url}">Confirm subscription</a></p>
<p>If you didn't request this, you can safely ignore this email or
<a href="{unsubscribe_url}">unsubscribe</a>.</p>
</body></html>
"""
    return await send_email(
        to_email=email,
        subject="Confirm your blog digest subscription",
        html_content=html,
        categories=["blog_digest_confirmation"],
        unsubscribe_url=unsubscribe_url,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("3/minute")
async def subscribe(  # noqa: role-check -- public blog digest subscribe (double opt-in)
    request: Request,
    payload: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> SubscribeResponse:
    """Create or re-confirm a blog digest subscription.

    Idempotent on (email, frequency): existing rows return
    ``already_subscribed=True`` without resending the confirmation email.
    """
    email = payload.email.lower().strip()
    frequency = payload.frequency

    result = await db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.email == email,
            BlogEmailSubscription.frequency == frequency,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        # Link to user if newly authed and the existing row was anon
        if current_user and existing.user_id is None:
            existing.user_id = current_user.id
            await db.commit()
        return SubscribeResponse(
            status="already_subscribed",
            already_subscribed=True,
            frequency=existing.frequency,
            email=existing.email,
        )

    sub = BlogEmailSubscription(
        email=email,
        user_id=current_user.id if current_user else None,
        frequency=frequency,
        confirmation_token=_new_token(),
        unsubscribe_token=_new_token(),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # Fire confirmation email (best-effort; daily-cap can swallow it)
    try:
        sent = await _send_confirmation_email(
            email=sub.email,
            confirm_token=sub.confirmation_token,
            unsubscribe_token=sub.unsubscribe_token,
        )
        if not sent:
            logger.warning(
                "Blog digest confirmation email returned False (cap/dedup/transport)",
                extra={"email": email},
            )
    except Exception:
        logger.exception("Failed to send blog digest confirmation email", extra={"email": email})

    return SubscribeResponse(
        status="pending_confirmation",
        already_subscribed=False,
        frequency=sub.frequency,
        email=sub.email,
    )


@router.get("/confirm", response_class=HTMLResponse)
async def confirm_subscription(  # noqa: role-check -- public confirm via token
    token: str = Query(..., min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Verify a confirmation token and activate the subscription."""
    result = await db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.confirmation_token == token
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token")

    if sub.confirmed_at is None:
        sub.confirmed_at = datetime.now(timezone.utc)
        await db.commit()

    return HTMLResponse(
        """<!doctype html><html><head><meta charset="utf-8"><title>Subscription confirmed</title></head>
<body style="font-family:system-ui;max-width:520px;margin:4rem auto;padding:1rem;">
<h1>Subscription confirmed</h1>
<p>You will now receive the blog digest. You can unsubscribe at any time via the link in any digest email.</p>
</body></html>"""
    )


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(  # noqa: role-check -- public unsubscribe via signed token
    token: str = Query(..., min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Verify an unsubscribe token and remove the subscription row."""
    result = await db.execute(
        select(BlogEmailSubscription).where(
            BlogEmailSubscription.unsubscribe_token == token
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe token")

    await db.delete(sub)
    await db.commit()

    return HTMLResponse(
        """<!doctype html><html><head><meta charset="utf-8"><title>Unsubscribed</title></head>
<body style="font-family:system-ui;max-width:520px;margin:4rem auto;padding:1rem;">
<h1>You have been unsubscribed</h1>
<p>You will no longer receive the blog digest. Sorry to see you go.</p>
</body></html>"""
    )


@router.get("/subscriptions/me", response_model=SubscriptionsListResponse)
async def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionsListResponse:
    """List the current user's blog digest subscriptions."""
    result = await db.execute(
        select(BlogEmailSubscription)
        .where(BlogEmailSubscription.user_id == current_user.id)
        .order_by(BlogEmailSubscription.created_at.desc())
    )
    rows = result.scalars().all()
    items = [
        SubscriptionItem(
            id=r.id,
            email=r.email,
            frequency=r.frequency,
            confirmed=r.confirmed_at is not None,
            last_sent_at=r.last_sent_at,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return SubscriptionsListResponse(items=items)
