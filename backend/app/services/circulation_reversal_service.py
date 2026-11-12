# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import ItemStatus
from ..models.user import User
from .unified_reversal_service import (
    UnifiedReversalService,
    ReversalResult as _UnifiedReversalResult,
    UNDO_CHECKOUT_WINDOW_MINUTES,
)


# Backward-compatible alias
CirculationReversalResult = _UnifiedReversalResult

__all__ = [
    "CirculationReversalResult",
    "undo_checkout",
    "reverse_return",
    "revert_item_status_change",
    "UNDO_CHECKOUT_WINDOW_MINUTES",
]


async def undo_checkout(
    checkout_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "User error - accidental checkout",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.undo_checkout(checkout_id, performer, reason)


async def reverse_return(
    checkout_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "User error - mistaken return",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.reverse_return(checkout_id, performer, reason)


async def revert_item_status_change(
    item_id: int,
    previous_status: ItemStatus,
    performer: User,
    db: AsyncSession,
    reason: str = "Staff correction",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.revert_item_status_change(item_id, previous_status, performer, reason)
