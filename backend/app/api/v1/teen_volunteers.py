# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Teen volunteer management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .dependencies import require_authenticated, require_staff
from app.models.user import User
from app.models.teen_volunteer import TeenVolunteer, TeenAdvisoryBoardMember

router = APIRouter(prefix="/teen-volunteers", tags=["teen-volunteers"])


@router.get("")
async def list_teen_volunteers(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all teen volunteers with user names."""
    result = await db.execute(
        select(
            TeenVolunteer,
            # Names encrypted; select columns (auto-decrypted) and concat app-side.
            User.first_name,
            User.last_name,
        )
        .join(User, TeenVolunteer.user_id == User.id)
        .order_by(TeenVolunteer.id)
    )
    rows = result.all()
    items = []
    for tv, first_name, last_name in rows:
        d = {c.name: getattr(tv, c.name) for c in tv.__table__.columns}
        d["user_name"] = f"{first_name or ''} {last_name or ''}".strip()
        # Convert date/datetime to string for JSON
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        items.append(d)
    return items


@router.get("/advisory-board")
async def list_advisory_board(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List teen advisory board members."""
    result = await db.execute(
        select(
            TeenAdvisoryBoardMember,
            User.first_name,
            User.last_name,
        )
        .join(TeenVolunteer, TeenAdvisoryBoardMember.volunteer_id == TeenVolunteer.id)
        .join(User, TeenVolunteer.user_id == User.id)
        .order_by(TeenAdvisoryBoardMember.id)
    )
    rows = result.all()
    items = []
    for member, first_name, last_name in rows:
        d = {c.name: getattr(member, c.name) for c in member.__table__.columns}
        d["volunteer_name"] = f"{first_name or ''} {last_name or ''}".strip()
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        items.append(d)
    return items


@router.get("/{volunteer_id}")
async def get_teen_volunteer(
    volunteer_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a single teen volunteer."""
    result = await db.execute(
        select(TeenVolunteer).where(TeenVolunteer.id == volunteer_id)
    )
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail="Teen volunteer not found")
    d = {c.name: getattr(tv, c.name) for c in tv.__table__.columns}
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


@router.post("/{volunteer_id}/approve")
async def approve_teen_volunteer(
    volunteer_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending teen volunteer."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(TeenVolunteer).where(TeenVolunteer.id == volunteer_id)
    )
    tv = result.scalar_one_or_none()
    if not tv:
        raise HTTPException(status_code=404, detail="Teen volunteer not found")
    if tv.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Volunteer is not pending approval")

    tv.status = "active"
    tv.training_completed = True
    tv.safety_acknowledgment = True
    tv.background_check_completed = True
    tv.approved_at = datetime.now(timezone.utc)
    tv.approved_by_id = current_user.id
    await db.flush()

    return {"message": "Teen volunteer approved", "id": tv.id}
