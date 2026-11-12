# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Lost and Damaged Item Management API Package

Comprehensive API for managing:
- Lost items (mark lost, process found, write off)
- Damaged items (report, assess, mending queue, withdraw)
- Claims returned disputes
- Financial and inventory reports
- Workflow settings

This package splits the endpoints into focused sub-routers:
- lost_items: mark lost, found, writeoff, bulk operations
- damaged_items: report, assess, mending, withdraw, bulk operations
- claims_returned: file, review, search, resolve disputes
- reports: financial and inventory analytics
"""

from fastapi import APIRouter

from .lost_items import router as lost_items_router
from .damaged_items import router as damaged_items_router
from .claims_returned import router as claims_returned_router
from .reports import router as reports_router
from .item_issues_unified import router as item_issues_unified_router

router = APIRouter(prefix="/staff/lost-damaged", tags=["staff-lost-damaged"])

router.include_router(item_issues_unified_router)
router.include_router(lost_items_router)
router.include_router(damaged_items_router)
router.include_router(claims_returned_router)
router.include_router(reports_router)
