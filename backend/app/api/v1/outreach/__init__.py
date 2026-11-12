# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Outreach Program Tracking API endpoints.
Manages school/organization partnerships, visits, deposits,
institutional cards, and bulk checkouts.

Split into domain-focused sub-modules:
- partners: Partner CRUD + contacts
- deposits: Deposit collection, refund, apply
- visits: Visit scheduling, completion, cancellation
- institutional: Institutional cards + bulk checkouts
- statistics: Dashboard, reports, monthly statistics
"""

from fastapi import APIRouter

from .partners import router as partners_router
from .deposits import router as deposits_router
from .visits import router as visits_router
from .institutional import router as institutional_router
from .statistics import router as statistics_router
from .helpers import require_staff

router = APIRouter(prefix="/outreach", tags=["outreach"])

router.include_router(partners_router)
router.include_router(deposits_router)
router.include_router(visits_router)
router.include_router(institutional_router)
router.include_router(statistics_router)

__all__ = ["router", "require_staff"]
