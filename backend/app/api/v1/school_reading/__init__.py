# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""School reading partnerships package.

Split out of the former 2,887-line ``school_reading_partnerships.py`` into
four cohesive sub-routers.  The parent ``router`` here is what
``registry.py`` includes; it carries the ``/school-partnerships`` prefix and
mounts each sub-router beneath it.

Include order is stable and intentional -- siblings share path prefixes
(e.g. ``/schools/{school_id}/...``) but never collide because each sub-router
owns disjoint sub-paths.
"""

from fastapi import APIRouter

from .lists_and_badges import router as lists_and_badges_router
from .programs import router as programs_router
from .tiers import router as tiers_router
from .family_engagement import router as family_engagement_router

router = APIRouter(prefix="/school-partnerships", tags=["school-partnerships"])

router.include_router(lists_and_badges_router)
router.include_router(programs_router)
router.include_router(tiers_router)
router.include_router(family_engagement_router)

__all__ = ["router"]
