# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Circulation domain package -- checkouts, holds, hold-shelf, and jobs."""

from fastapi import APIRouter

from . import checkouts, hold_shelf, holds, jobs
from .helpers import (
    HOLD_EXPIRY_DAYS,
    check_hold_limit,
    get_user_hold_expiry,
    validate_pickup_location,
)

router = APIRouter(prefix="/circulation", tags=["circulation"])
router.include_router(checkouts.router)
router.include_router(holds.router)
router.include_router(hold_shelf.router)
router.include_router(jobs.router)

# Re-export anything other modules might import from circulation
__all__ = [
    "router",
    "checkouts",
    "holds",
    "hold_shelf",
    "jobs",
    # Helper functions (re-exported for backward compatibility)
    "HOLD_EXPIRY_DAYS",
    "check_hold_limit",
    "get_user_hold_expiry",
    "validate_pickup_location",
]
