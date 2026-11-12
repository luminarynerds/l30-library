# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff Fines Management API - Package init.

Merges all sub-module routers into a single `router` for backward compatibility
with `from .api.v1 import staff_fines; staff_fines.router`.
"""

from fastapi import APIRouter

from .fines import router as fines_router
from .history import router as history_router
from .partial_payments import router as partial_payments_router
from .payment_plans import router as payment_plans_router
from .receipts import router as receipts_router
from .analytics import router as analytics_router
from .helpers import (
    _track_payment,
    calculate_next_payment_date,
    create_fine_audit_log,
    generate_receipt_number,
)

# Create a top-level router that includes all sub-routers.
# Sub-routers already carry prefix="/staff" and tags=["staff-fines"],
# so we use an empty prefix here to avoid doubling.
router = APIRouter()
router.include_router(fines_router)
router.include_router(history_router)
router.include_router(partial_payments_router)
router.include_router(payment_plans_router)
router.include_router(receipts_router)
router.include_router(analytics_router)

__all__ = [
    "router",
    "_track_payment",
    "calculate_next_payment_date",
    "create_fine_audit_log",
    "generate_receipt_number",
]
