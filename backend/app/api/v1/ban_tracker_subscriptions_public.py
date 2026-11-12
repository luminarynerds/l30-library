# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public (no-auth) ban-tracker subscription endpoints.

This router exists separately from ``ban_tracker_subscriptions.py``
specifically because every other route there is auth-required (the
patron CRUD surface). The unsubscribe link in a digest email needs
to work for an un-authenticated recipient -- the URL token itself
is the credential -- so it must not pick up the auth dependency that
the CRUD router applies.

Mounted at ``/ban-tracker`` so the URL ends up at
``/api/v1/ban-tracker/unsubscribe?token=...`` per the spec.
"""
from __future__ import annotations

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.ban_tracker import BanTrackerSubscription

logger = get_logger(__name__)

router = APIRouter(
    prefix="/ban-tracker",
    tags=["ban-tracker-subscriptions"],
)


# Generic page body. Returned for both valid + invalid tokens so the
# endpoint never confirms whether a token existed -- token guesses
# are indistinguishable from real unsubscribes from the caller's view.
_UNSUB_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unsubscribed</title>
<meta name="robots" content="noindex">
<style>
body { font-family: Georgia, serif; background: #FAF7F2; color: #2C1810; margin: 0; padding: 0; }
.wrap { max-width: 520px; margin: 8vh auto; padding: 40px 32px; background: #fff;
         border: 1px solid #E5E0D8; border-radius: 6px; text-align: center; }
h1 { margin: 0 0 12px 0; font-size: 24px; }
p { margin: 0 0 16px 0; line-height: 1.5; color: #5C4F3D; }
a { color: #B85C2E; text-decoration: underline; }
</style>
</head>
<body>
<div class="wrap">
<h1>You've been unsubscribed.</h1>
<p>If that was a valid ban-tracker unsubscribe link, the matching subscription
has been turned off. You won't receive further digest emails for it.</p>
<p>Changed your mind? You can re-subscribe any time from your account on
<a href="/account">account</a>.</p>
</div>
</body>
</html>
"""


@router.api_route(
    "/unsubscribe",
    methods=["GET", "POST"],
    response_class=HTMLResponse,
)
async def unsubscribe_via_token(
    token: str = Query(..., min_length=1, max_length=128),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    result = await db.execute(
        select(BanTrackerSubscription).where(
            BanTrackerSubscription.unsubscribe_token == token
        )
    )
    sub = result.scalar_one_or_none()
    if sub is not None and sub.is_active:
        sub.is_active = False
        await db.commit()
        logger.info(
            "ban_tracker subscription unsubscribed via token",
            extra={"subscription_id": sub.id, "user_id": sub.user_id},
        )

    return HTMLResponse(content=_UNSUB_PAGE_HTML, status_code=200)
