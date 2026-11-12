# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parent-onboarding API router package (assembled from per-subdomain sub-routers)."""
from fastapi import APIRouter
from .sessions import router as sessions_router
from .childcare import router as childcare_router
from .reports import router as reports_router
from .connection_groups import router as connection_groups_router
from .home_visits import router as home_visits_router
from .resource_guide import router as resource_guide_router
from .service_enrollments import router as service_enrollments_router

router = APIRouter(prefix="/parent-onboarding", tags=["parent-onboarding"])
router.include_router(sessions_router)
router.include_router(childcare_router)
router.include_router(reports_router)
router.include_router(connection_groups_router)
router.include_router(home_visits_router)
router.include_router(resource_guide_router)
router.include_router(service_enrollments_router)
