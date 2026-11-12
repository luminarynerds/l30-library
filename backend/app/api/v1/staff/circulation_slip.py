# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Circulation Slip Endpoint

Email a checkout slip to the patron on file. Print path lives client-side
(window.print()); this endpoint only handles the email delivery. Gated by
the ``circulation_print_slip_enabled`` org feature flag.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.email import send_email
from ....core.rate_limit import limiter
from ....models.circulation import Checkout
from ....models.user import User
from ..dependencies import require_staff
from ..feature_guards import require_circulation_print_slip_enabled

router = APIRouter(prefix="/staff/circulation", tags=["staff-circulation-slip"])


class EmailSlipRequest(BaseModel):
    checkout_id: int = Field(..., description="ID of the checkout to email a slip for")


class EmailSlipResponse(BaseModel):
    message: str
    sent: bool


def _render_slip_html(
    *,
    patron_name: str,
    item_title: str,
    item_author: Optional[str],
    checked_out_at: datetime,
    due_date: datetime,
    library_name: str,
) -> str:
    co = checked_out_at.strftime("%b %d, %Y %I:%M %p")
    due = due_date.strftime("%b %d, %Y")
    author_line = f"<div>by {item_author}</div>" if item_author else ""
    return f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, system-ui, sans-serif; color:#2C1810; margin:0; padding:24px;">
  <div style="max-width:480px;margin:0 auto;">
    <h2 style="margin:0 0 4px 0;">Checkout slip</h2>
    <div style="color:#8B7B6A;font-size:13px;margin-bottom:16px;">{library_name}</div>
    <div style="margin-bottom:12px;">Hi {patron_name},</div>
    <div style="border:1px solid #E5E0D8;border-radius:6px;padding:16px;">
      <div style="font-weight:600;font-size:16px;">{item_title}</div>
      {author_line}
      <div style="margin-top:12px;color:#5C4F3D;font-size:14px;">
        <div>Checked out: {co}</div>
        <div>Due: <strong>{due}</strong></div>
      </div>
    </div>
    <div style="margin-top:16px;color:#8B7B6A;font-size:12px;">
      Bring your card if you'd like to renew or ask about a hold.
    </div>
  </div>
</body></html>"""


@router.post("/email-slip", response_model=EmailSlipResponse)
@limiter.limit("30/minute")
async def email_checkout_slip(
    request: Request,
    payload: EmailSlipRequest,
    _staff_user: User = Depends(require_staff),
    _flag: None = Depends(require_circulation_print_slip_enabled),
    db: AsyncSession = Depends(get_db),
) -> EmailSlipResponse:
    """Email a checkout slip to the patron on file."""
    result = await db.execute(
        select(Checkout)
        .where(Checkout.id == payload.checkout_id)
        .options(selectinload(Checkout.user), selectinload(Checkout.item))
    )
    checkout = result.scalar_one_or_none()
    if checkout is None:
        raise HTTPException(status_code=404, detail="Checkout not found")

    user = checkout.user
    if user is None or not user.email:
        raise HTTPException(
            status_code=422,
            detail="Patron has no email address on file",
        )

    item = checkout.item
    item_title = (getattr(item, "title", None) or "Library item").strip() or "Library item"
    item_author = getattr(item, "author", None)
    patron_name = (
        f"{user.first_name or ''} {user.last_name or ''}".strip()
        or user.email.split("@")[0]
    )

    # Defensive: branding import is best-effort; if the runtime branding
    # snapshot is missing in tests, fall back to a neutral label.
    try:
        from ....core.branding import branding
        library_name = branding.library_name
    except Exception:  # noqa: BLE001  # branding lookup fallback — neutral label
        library_name = "Library"

    co_at = checkout.checked_out_at or datetime.now(timezone.utc)
    due = checkout.due_date

    html = _render_slip_html(
        patron_name=patron_name,
        item_title=item_title,
        item_author=item_author,
        checked_out_at=co_at,
        due_date=due,
        library_name=library_name,
    )

    sent = await send_email(
        to_email=user.email,
        subject=f"Checkout slip - {item_title}",
        html_content=html,
        categories=["checkout_slip"],
        patron_id=user.id,
        notification_type="checkout_slip",
    )

    if sent:
        return EmailSlipResponse(message="Slip emailed.", sent=True)
    # send_email returns False on daily-cap or dedup hit. Surface as 200 so
    # the client can show a soft warning; the print path still works.
    return EmailSlipResponse(
        message="Email could not be delivered right now (daily cap or duplicate). The slip can still be printed.",
        sent=False,
    )
