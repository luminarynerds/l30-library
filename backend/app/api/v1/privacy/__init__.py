# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Privacy and Compliance API package."""

from fastapi import APIRouter

from . import children, data_export, account_deletion, staff_deletion, consent, data_correction, patron_data_controls
from .helpers import check_email_blocked

router = APIRouter(prefix="/privacy", tags=["privacy"])
router.include_router(children.router)
router.include_router(data_export.router)
router.include_router(account_deletion.router)
router.include_router(staff_deletion.router)
router.include_router(consent.router)
router.include_router(data_correction.router)
router.include_router(patron_data_controls.router)

__all__ = [
    "router",
    "check_email_blocked",
    "children",
    "data_export",
    "account_deletion",
    "staff_deletion",
    "consent",
    "data_correction",
    "patron_data_controls",
]
