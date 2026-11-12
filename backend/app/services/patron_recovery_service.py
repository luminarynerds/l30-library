# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from .unified_reversal_service import (
    UnifiedReversalService,
    ReversalResult as _UnifiedReversalResult,
)

# Backward-compatible alias
PatronRecoveryResult = _UnifiedReversalResult

__all__ = [
    "PatronRecoveryResult",
    "restore_deactivated_patron",
    "unblock_patron",
    "unsuspend_patron",
    "list_recoverable_patrons",
]


async def restore_deactivated_patron(
    patron_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "Account restoration - error recovery",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.restore_deactivated_patron(patron_id, performer, reason)


async def unblock_patron(
    patron_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "Block removal - error recovery",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.unblock_patron(patron_id, performer, reason)


async def unsuspend_patron(
    patron_id: int,
    performer: User,
    db: AsyncSession,
    reason: str = "Suspension removal - error recovery",
) -> _UnifiedReversalResult:
    service = UnifiedReversalService(db)
    return await service.unsuspend_patron(patron_id, performer, reason)


async def list_recoverable_patrons(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    service = UnifiedReversalService(db)
    return await service.list_recoverable_patrons(limit, offset)
