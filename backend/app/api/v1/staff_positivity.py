# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Positivity Hub API Endpoints

Provides endpoints for:
- Creating positivity entries
- Listing entries (with moderation/source filters)
- Getting positivity digest
- Advocacy flagging
- Moderation queue
"""
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.positivity import PositivityEntry, PositivityEntryType
from ...models.user import User
from ...schemas.positivity import (
    PositivityEntryCreate,
    PositivityEntryResponse,
    PositivityEntryFullResponse,
    PositivityEntriesListResponse,
    PositivityDigestResponse,
    AdvocacyFlagRequest,
    AdvocacyEntriesResponse,
    ModerationActionRequest,
)
from .dependencies import require_staff

router = APIRouter(prefix="/staff/positivity", tags=["staff-positivity"])


def _entry_to_full_response(entry: PositivityEntry) -> PositivityEntryFullResponse:
    return PositivityEntryFullResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        text=entry.text,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        created_by_name=entry.user.full_name if entry.user else None,
        source=entry.source or "staff",
        patron_name=entry.patron_name,
        patron_email=entry.patron_email,
        flagged_for_advocacy=entry.flagged_for_advocacy or False,
        flagged_at=entry.flagged_at,
        flagged_by_name=entry.flagged_by.full_name if entry.flagged_by else None,
        moderation_status=entry.moderation_status or "approved",
        moderated_at=entry.moderated_at,
        moderated_by_name=entry.moderated_by.full_name if entry.moderated_by else None,
        moderation_note=entry.moderation_note,
    )


@router.post("", response_model=PositivityEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_positivity_entry(
    entry_in: PositivityEntryCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new positivity entry (staff only)."""
    # Validate entry type
    try:
        PositivityEntryType(entry_in.entry_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry type. Must be one of: {', '.join([t.value for t in PositivityEntryType])}",
        ) from None

    entry = PositivityEntry(
        organization_id=getattr(staff_user, 'organization_id', None) or 1,
        user_id=staff_user.id,
        entry_type=entry_in.entry_type,
        text=entry_in.text,
        source="staff",
        moderation_status="approved",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return PositivityEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        text=entry.text,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        created_by_name=staff_user.full_name,
    )


@router.get("", response_model=PositivityEntriesListResponse)
async def list_positivity_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    source: Optional[str] = Query(None, description="Filter by source: staff or patron"),
    flagged_only: bool = Query(False, description="Only show advocacy-flagged entries"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List positivity entries for the current organization."""
    org_id = getattr(staff_user, 'organization_id', None) or 1
    base_where = [
        PositivityEntry.organization_id == org_id,
        PositivityEntry.moderation_status == "approved",
    ]
    if entry_type:
        base_where.append(PositivityEntry.entry_type == entry_type)
    if source:
        base_where.append(PositivityEntry.source == source)
    if flagged_only:
        base_where.append(PositivityEntry.flagged_for_advocacy == True)

    count_query = select(func.count(PositivityEntry.id)).where(*base_where)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        select(PositivityEntry)
        .where(*base_where)
        .options(
            selectinload(PositivityEntry.user),
            selectinload(PositivityEntry.flagged_by),
            selectinload(PositivityEntry.moderated_by),
        )
        .offset(offset)
        .limit(per_page)
        .order_by(PositivityEntry.created_at.desc())
    )

    result = await db.execute(query)
    entries = result.scalars().all()

    return PositivityEntriesListResponse(
        entries=[_entry_to_full_response(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/digest", response_model=PositivityDigestResponse)
async def get_positivity_digest(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in digest"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get positivity digest for the current organization."""
    org_id = getattr(staff_user, 'organization_id', None) or 1
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(PositivityEntry).where(
        (PositivityEntry.organization_id == org_id) & (PositivityEntry.created_at >= cutoff_date)
    )

    result = await db.execute(query)
    entries = result.scalars().all()

    # Count by type
    digest = {
        "feedback": 0,
        "win": 0,
        "program": 0,
        "thank_you": 0,
        "compliment": 0,
        "story": 0,
        "appreciation": 0,
    }

    advocacy_flagged = 0
    patron_submissions = 0
    pending_moderation = 0

    for entry in entries:
        key = entry.entry_type.replace("-", "_")
        if key in digest:
            digest[key] += 1
        if getattr(entry, "flagged_for_advocacy", False):
            advocacy_flagged += 1
        if getattr(entry, "source", "staff") == "patron":
            patron_submissions += 1
        if getattr(entry, "moderation_status", "approved") == "pending":
            pending_moderation += 1

    digest["total"] = len(entries)
    digest["advocacy_flagged"] = advocacy_flagged
    digest["patron_submissions"] = patron_submissions
    digest["pending_moderation"] = pending_moderation

    return PositivityDigestResponse(**digest)


# --- Advocacy Endpoints (before /{entry_id} to avoid path conflicts) ---

@router.patch("/{entry_id}/flag", response_model=PositivityEntryFullResponse)
async def toggle_advocacy_flag(
    entry_id: int,
    flag_req: AdvocacyFlagRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Toggle advocacy flag on a positivity entry."""
    entry = await get_or_404(db, PositivityEntry, entry_id, "Entry not found")
    if entry.organization_id != (getattr(staff_user, 'organization_id', None) or 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    entry.flagged_for_advocacy = flag_req.flagged
    if flag_req.flagged:
        entry.flagged_by_id = staff_user.id
        entry.flagged_at = datetime.now(timezone.utc)
    else:
        entry.flagged_by_id = None
        entry.flagged_at = None

    await db.commit()
    # Re-fetch with eager loading for response
    result = await db.execute(
        select(PositivityEntry)
        .where(PositivityEntry.id == entry_id)
        .options(
            selectinload(PositivityEntry.user),
            selectinload(PositivityEntry.flagged_by),
            selectinload(PositivityEntry.moderated_by),
        )
    )
    entry = result.scalar_one()
    return _entry_to_full_response(entry)


@router.get("/advocacy", response_model=AdvocacyEntriesResponse)
async def get_advocacy_entries(
    days: int = Query(90, ge=1, le=365, description="Period in days"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get advocacy-flagged and approved entries for the one-pager tool."""
    org_id = getattr(staff_user, 'organization_id', None) or 1
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(PositivityEntry)
        .where(
            PositivityEntry.organization_id == org_id,
            PositivityEntry.flagged_for_advocacy == True,
            PositivityEntry.moderation_status == "approved",
            PositivityEntry.created_at >= cutoff_date,
        )
        .options(
            selectinload(PositivityEntry.user),
            selectinload(PositivityEntry.flagged_by),
            selectinload(PositivityEntry.moderated_by),
        )
        .order_by(PositivityEntry.created_at.desc())
    )

    result = await db.execute(query)
    entries = result.scalars().all()

    return AdvocacyEntriesResponse(
        entries=[_entry_to_full_response(e) for e in entries],
        count=len(entries),
        period_days=days,
    )


# --- Moderation Endpoints ---

@router.get("/moderation", response_model=PositivityEntriesListResponse)
async def get_moderation_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    moderation_status: Optional[str] = Query(None, description="Filter: pending, approved, rejected"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get patron submissions for moderation review."""
    org_id = getattr(staff_user, 'organization_id', None) or 1
    base_where = [
        PositivityEntry.organization_id == org_id,
        PositivityEntry.source == "patron",
    ]
    if moderation_status:
        base_where.append(PositivityEntry.moderation_status == moderation_status)

    count_query = select(func.count(PositivityEntry.id)).where(*base_where)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        select(PositivityEntry)
        .where(*base_where)
        .options(
            selectinload(PositivityEntry.user),
            selectinload(PositivityEntry.flagged_by),
            selectinload(PositivityEntry.moderated_by),
        )
        .order_by(
            case(
                (PositivityEntry.moderation_status == "pending", 0),
                else_=1,
            ),
            PositivityEntry.created_at.desc(),
        )
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(query)
    entries = result.scalars().all()

    return PositivityEntriesListResponse(
        entries=[_entry_to_full_response(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.patch("/{entry_id}/moderate", response_model=PositivityEntryFullResponse)
async def moderate_entry(
    entry_id: int,
    mod_req: ModerationActionRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a patron submission."""
    if mod_req.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'",
        )

    entry = await get_or_404(db, PositivityEntry, entry_id, "Entry not found")
    if entry.organization_id != (getattr(staff_user, 'organization_id', None) or 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    entry.moderation_status = "approved" if mod_req.action == "approve" else "rejected"
    entry.moderated_by_id = staff_user.id
    entry.moderated_at = datetime.now(timezone.utc)
    entry.moderation_note = mod_req.note

    await db.commit()
    # Re-fetch with eager loading for response
    result = await db.execute(
        select(PositivityEntry)
        .where(PositivityEntry.id == entry_id)
        .options(
            selectinload(PositivityEntry.user),
            selectinload(PositivityEntry.flagged_by),
            selectinload(PositivityEntry.moderated_by),
        )
    )
    entry = result.scalar_one()
    return _entry_to_full_response(entry)


# --- Existing CRUD Endpoints ---

@router.get("/{entry_id}", response_model=PositivityEntryResponse)
async def get_positivity_entry(
    entry_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a positivity entry by ID (staff only)."""
    result = await db.execute(
        select(PositivityEntry)
        .where(PositivityEntry.id == entry_id)
        .options(selectinload(PositivityEntry.user))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    # Check organization access
    if entry.organization_id != (getattr(staff_user, 'organization_id', None) or 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return PositivityEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type,
        text=entry.text,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        created_by_name=entry.user.full_name if entry.user else None,
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_positivity_entry(
    entry_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a positivity entry (staff only - own entries only)."""
    entry = await get_or_404(db, PositivityEntry, entry_id, "Entry not found")

    # Check organization access
    if entry.organization_id != (getattr(staff_user, 'organization_id', None) or 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Only allow deleting own entries or admin can delete any
    if entry.user_id != staff_user.id and not staff_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own entries",
        )

    await db.delete(entry)
    await db.commit()
