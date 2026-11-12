# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Patron Profile Edit & Reading Minutes Management API Endpoints.

Provides endpoints for staff to:
- Edit patron profile fields (name, email, phone, address) with audit logging
- View and adjust patron reading minutes (for Read-for-Fines program)
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.shortcuts import get_or_404
from ...models.audit_log import AuditAction, AuditLog
from ...models.reading import ReadingLog, ReadingLogStatus
from ...models.user import User, UserRole, email_blind_hash
from .dependencies import require_staff

logger = get_logger(__name__)
router = APIRouter(prefix="/staff/patrons", tags=["staff-patron-profile-edit"])


# =============================================================================
# Schemas
# =============================================================================


class StaffPatronProfileEditRequest(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=500)
    preferred_contact_method: str | None = Field(None, max_length=20)
    language_preference: str | None = Field(None, max_length=50)
    accessibility_needs: str | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)


class StaffPatronProfileEditResponse(BaseModel):
    message: str
    patron_id: int
    changes: dict


class ReadingMinutesStatusResponse(BaseModel):
    patron_id: int
    patron_name: str
    minutes_owed: int
    minutes_logged: int
    minutes_remaining: int
    is_clear: bool


class StaffAddReadingMinutesRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=500, description="Reading minutes to add (1-500)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for adding minutes")


class StaffLogReadingMinutesRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=120, description="Minutes to log (1-120)")
    note: str | None = Field(None, max_length=200, description="Optional note about the reading session")


class StaffReadingMinutesResponse(BaseModel):
    message: str
    patron_id: int
    minutes_owed: int
    minutes_logged: int
    minutes_remaining: int
    is_clear: bool


# =============================================================================
# Staff Patron Profile Edit Endpoints
# =============================================================================


@router.put("/{patron_id}/profile", response_model=StaffPatronProfileEditResponse)
@limiter.limit("30/minute")
async def staff_edit_patron_profile(
    request: Request,
    patron_id: int,
    edit_request: StaffPatronProfileEditRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff: Edit a patron's profile information.

    Supports updating name, email, phone, address, and other profile fields.
    All changes are audit-logged with before/after values and staff attribution.
    Email changes take effect immediately when done by staff (no re-verification needed).
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    update_data = edit_request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    # If email is being changed, check for duplicates
    if "email" in update_data:
        new_email = update_data["email"].lower()
        if new_email != patron.email.lower():
            existing = await db.execute(
                select(User).where(User.email_hash == email_blind_hash(new_email), User.id != patron_id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already associated with another account.",
                )
            update_data["email"] = new_email
        else:
            # Same email, skip the update
            del update_data["email"]

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes detected.",
        )

    # Capture old values for audit trail
    changes = {}
    for field, new_value in update_data.items():
        old_value = getattr(patron, field)
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None
        if old_str != new_str:
            changes[field] = {"old": old_str, "new": new_str}

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes detected.",
        )

    # Apply changes
    for field, value in update_data.items():
        setattr(patron, field, value)
    patron.updated_at = datetime.now(timezone.utc)

    # Create audit log
    audit_log = AuditLog(
        admin_id=staff_user.id,
        target_user_id=patron.id,
        action=AuditAction.UPDATE_USER,
        details={"changes": changes, "edited_by": staff_user.email},
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(patron)

    logger.info(
        "Staff %s (id=%d) updated patron %d profile: %s",
        staff_user.email,
        staff_user.id,
        patron_id,
        list(changes.keys()),
    )

    return StaffPatronProfileEditResponse(
        message=f"Patron profile updated successfully. Changed: {', '.join(changes.keys())}",
        patron_id=patron_id,
        changes=changes,
    )


# =============================================================================
# Staff Reading Minutes Management Endpoints
# =============================================================================


@router.get("/{patron_id}/reading-minutes", response_model=ReadingMinutesStatusResponse)
async def staff_get_reading_minutes(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff: View a patron's reading minutes status."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    remaining = max(0, patron.reading_minutes_owed - patron.reading_minutes_logged)

    return ReadingMinutesStatusResponse(
        patron_id=patron.id,
        patron_name=f"{patron.first_name} {patron.last_name}",
        minutes_owed=patron.reading_minutes_owed,
        minutes_logged=patron.reading_minutes_logged,
        minutes_remaining=remaining,
        is_clear=remaining == 0,
    )


@router.post("/{patron_id}/reading-minutes/add", response_model=StaffReadingMinutesResponse)
@limiter.limit("30/minute")
async def staff_add_reading_minutes_owed(
    request: Request,
    patron_id: int,
    add_request: StaffAddReadingMinutesRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff: Add reading minutes owed to a patron.

    Used when converting an overdue fine to reading minutes for the
    Read-for-Fines program. The patron must then log reading time
    to pay off the minutes.
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    old_owed = patron.reading_minutes_owed

    # Use atomic increment to prevent race conditions
    await db.execute(
        update(User)
        .where(User.id == patron_id)
        .values(reading_minutes_owed=User.reading_minutes_owed + add_request.minutes)
    )

    # Audit log
    audit_log = AuditLog(
        admin_id=staff_user.id,
        target_user_id=patron.id,
        action=AuditAction.UPDATE_USER,
        details={
            "action": "add_reading_minutes_owed",
            "minutes_added": add_request.minutes,
            "old_owed": old_owed,
            "new_owed": old_owed + add_request.minutes,
            "reason": add_request.reason,
        },
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(patron)

    remaining = max(0, patron.reading_minutes_owed - patron.reading_minutes_logged)

    logger.info(
        "Staff %s added %d reading minutes owed to patron %d (reason: %s)",
        staff_user.email,
        add_request.minutes,
        patron_id,
        add_request.reason,
    )

    return StaffReadingMinutesResponse(
        message=f"Added {add_request.minutes} reading minutes owed to {patron.first_name} {patron.last_name}.",
        patron_id=patron.id,
        minutes_owed=patron.reading_minutes_owed,
        minutes_logged=patron.reading_minutes_logged,
        minutes_remaining=remaining,
        is_clear=remaining == 0,
    )


@router.post("/{patron_id}/reading-minutes/log", response_model=StaffReadingMinutesResponse)
@limiter.limit("30/minute")
async def staff_log_reading_minutes(
    request: Request,
    patron_id: int,
    log_request: StaffLogReadingMinutesRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff: Log reading minutes on behalf of a patron.

    Used when a staff member observes a child reading in the library
    or when a patron reports reading and staff verifies it at the desk.
    Creates an audit trail with staff attribution.
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    remaining = patron.reading_minutes_owed - patron.reading_minutes_logged
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{patron.first_name} doesn't have any reading minutes to pay off.",
        )

    # Cap minutes to what's actually owed
    minutes_to_log = min(log_request.minutes, remaining)

    # Use atomic increment to prevent race conditions
    await db.execute(
        update(User)
        .where(User.id == patron_id)
        .values(reading_minutes_logged=User.reading_minutes_logged + minutes_to_log)
    )

    # Create reading log entry with staff attribution
    reading_log = ReadingLog(
        user_id=patron.id,
        minutes=minutes_to_log,
        notes=f"[Staff-logged by {staff_user.first_name} {staff_user.last_name}] {log_request.note or ''}".strip(),
        reading_date=datetime.now(timezone.utc),
        status=ReadingLogStatus.approved,
        reviewed_by_id=staff_user.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(reading_log)

    # Audit log
    audit_log = AuditLog(
        admin_id=staff_user.id,
        target_user_id=patron.id,
        action=AuditAction.UPDATE_USER,
        details={
            "action": "staff_log_reading_minutes",
            "minutes_logged": minutes_to_log,
            "note": log_request.note,
        },
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(patron)

    remaining = max(0, patron.reading_minutes_owed - patron.reading_minutes_logged)
    is_clear = remaining == 0

    if is_clear:
        msg = f"Logged {minutes_to_log} minutes for {patron.first_name}. All reading minutes are now paid off!"
    else:
        msg = f"Logged {minutes_to_log} minutes for {patron.first_name}. {remaining} minutes remaining."

    logger.info(
        "Staff %s logged %d reading minutes for patron %d",
        staff_user.email,
        minutes_to_log,
        patron_id,
    )

    return StaffReadingMinutesResponse(
        message=msg,
        patron_id=patron.id,
        minutes_owed=patron.reading_minutes_owed,
        minutes_logged=patron.reading_minutes_logged,
        minutes_remaining=remaining,
        is_clear=is_clear,
    )
