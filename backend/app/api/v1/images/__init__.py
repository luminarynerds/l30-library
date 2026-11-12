# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter

from . import cover

router = APIRouter()
router.include_router(cover.router)

__all__ = ["router", "cover"]
