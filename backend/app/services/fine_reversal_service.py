# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from .unified_reversal_service import (
    UnifiedReversalService,
    ReversalResult as _UnifiedReversalResult,
)

# Backward-compatible alias
FineReversalResult = _UnifiedReversalResult

__all__ = [
    "FineReversalResult",
    "undo_fine_waiver",
    "reverse_fine_payment",
]


async def undo_fine_waiver(
    fine_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "Staff correction - waiver undone",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.undo_fine_waiver(fine_id, performer, reason)


async def reverse_fine_payment(
    fine_id: int,
    amount_to_refund: Decimal,
    performer: User,
    db: AsyncSession,
    reason: str = "Payment error",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.reverse_fine_payment(fine_id, amount_to_refund, performer, reason)
