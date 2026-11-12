# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public patron waiting-list signup.

Patron self-serve registration is currently invite-only; the public
``/register`` page posts emails here instead of creating accounts, so we can
onboard patrons in manageable batches. Write-only, no email send.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.waitlist import WaitlistSignup

router = APIRouter(prefix="/waitlist", tags=["waitlist"])
logger = get_logger("l30.waitlist")


class WaitlistSignupRequest(BaseModel):
    email: EmailStr
    source: Optional[str] = Field(None, max_length=50)


@router.post("", status_code=201)
async def join_waitlist(  # noqa: role-check (public form)
    body: WaitlistSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add an email to the patron waiting list. Anonymous, idempotent."""
    email_lower = body.email.lower().strip()
    source = (body.source.strip()[:50] if body.source else None) or "register"

    existing = (
        await db.execute(
            select(WaitlistSignup).where(func.lower(WaitlistSignup.email) == email_lower)
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(WaitlistSignup(email=email_lower, source=source))
        await db.commit()
        logger.info("waitlist_signup email=%s source=%s", email_lower, source)
        message = "You're on the list."
    else:
        message = "You're already on the list."

    count = (await db.execute(select(func.count(WaitlistSignup.id)))).scalar()
    return {"success": True, "count": count, "message": message}
