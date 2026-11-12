# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dashboard profile endpoints -- GET and PUT for user dashboard preferences."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.dashboard_profile import DashboardProfileResponse, DashboardProfileUpdate
from ..dependencies import require_authenticated

router = APIRouter(prefix="/staff/dashboard", tags=["staff-dashboard-profile"])


@router.get("/profile", response_model=DashboardProfileResponse)
async def get_dashboard_profile(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's dashboard profile."""
    return DashboardProfileResponse(
        dashboard_functions=current_user.dashboard_functions,
        dashboard_tone=current_user.dashboard_tone or "standard",
    )


@router.put("/profile", response_model=DashboardProfileResponse)
async def update_dashboard_profile(
    update: DashboardProfileUpdate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's dashboard profile (onboarding + settings)."""
    current_user.dashboard_functions = update.dashboard_functions
    current_user.dashboard_tone = update.dashboard_tone
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return DashboardProfileResponse(
        dashboard_functions=current_user.dashboard_functions,
        dashboard_tone=current_user.dashboard_tone,
    )
