# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Accessibility Preferences API Endpoints.

Provides endpoints for patrons to manage their accessibility preferences
(large print, audio, braille, mobility assistance, etc.) and for staff
to view any patron's preferences.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.patron_communication import PatronPreference
from ...models.user import User, UserRole
from .auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/patron/preferences", tags=["patron-preferences"])

# Staff roles that can view any patron's preferences
STAFF_ROLES = {
    UserRole.STAFF,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
}


# =============================================================================
# Schemas
# =============================================================================


class PatronPreferenceResponse(BaseModel):
    prefers_large_print: bool = False
    prefers_audio_format: bool = False
    prefers_braille: bool = False
    handle_fragile_items_with_care: bool = False
    limited_mobility_assistance_needed: bool = False
    needs_extra_time_checkout: bool = False
    preference_notes: str | None = None

    class Config:
        from_attributes = True


class PatronPreferenceUpdateRequest(BaseModel):
    prefers_large_print: bool | None = None
    prefers_audio_format: bool | None = None
    prefers_braille: bool | None = None
    handle_fragile_items_with_care: bool | None = None
    limited_mobility_assistance_needed: bool | None = None
    needs_extra_time_checkout: bool | None = None
    preference_notes: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PatronPreferenceResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current patron's accessibility preferences.

    Returns default values (all False) if no preferences have been set yet.
    """
    result = await db.execute(
        select(PatronPreference).where(PatronPreference.patron_id == current_user.id)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        return PatronPreferenceResponse()

    return PatronPreferenceResponse.model_validate(pref)


@router.put("", response_model=PatronPreferenceResponse)
async def update_my_preferences(
    update_data: PatronPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current patron's accessibility preferences (upsert).

    Only fields included in the request body are updated; omitted fields
    are left unchanged. If no record exists, one is created.
    """
    changes = update_data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    result = await db.execute(
        select(PatronPreference).where(PatronPreference.patron_id == current_user.id)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        # Create new record
        pref = PatronPreference(
            patron_id=current_user.id,
            set_by_id=current_user.id,
            **changes,
        )
        db.add(pref)
    else:
        # Update existing record
        for field, value in changes.items():
            setattr(pref, field, value)
        pref.set_by_id = current_user.id

    await db.commit()
    await db.refresh(pref)

    return PatronPreferenceResponse.model_validate(pref)


@router.get("/{patron_id}", response_model=PatronPreferenceResponse)
async def get_patron_preferences_staff(
    patron_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Staff-only: View any patron's accessibility preferences.

    Returns default values if the patron has no preferences set.
    """
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )

    # Verify the patron exists
    patron_result = await db.execute(select(User).where(User.id == patron_id))
    patron = patron_result.scalar_one_or_none()
    if patron is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron not found.",
        )

    result = await db.execute(
        select(PatronPreference).where(PatronPreference.patron_id == patron_id)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        return PatronPreferenceResponse()

    return PatronPreferenceResponse.model_validate(pref)
