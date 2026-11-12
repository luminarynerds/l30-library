# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bookmobile routes and stops API — stub endpoints."""

from fastapi import APIRouter, Depends
from ...models.user import User
from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/bookmobile", tags=["bookmobile"])


@router.get("")
async def list_bookmobile_routes(current_user: User = Depends(require_staff)):
    """List bookmobile routes and schedules."""
    return {"routes": [], "total": 0, "message": "Bookmobile module is being configured."}


@router.get("/stops")
async def list_bookmobile_stops(current_user: User = Depends(require_staff)):
    """List bookmobile stops."""
    return {"stops": [], "total": 0}


@router.get("/schedule")
async def get_bookmobile_schedule(current_user: User = Depends(require_staff)):
    """Get bookmobile schedule."""
    return {"schedule": [], "total": 0}
