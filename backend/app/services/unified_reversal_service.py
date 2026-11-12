# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog
from ..models.catalog import ItemStatus
from ..models.user import User
from ..models.version_history import EntityType

# Import everything from the reversal package so that external code that
# does `from .unified_reversal_service import ReversalResult` etc. still works.
from .reversal.base import (
    ReversalResult,
    ReversalType,
    CanRevertResult,
    # Time window constants
    UNDO_CHECKOUT_WINDOW_MINUTES,
    UNDO_HOLD_WINDOW_MINUTES,
    UNDO_RENEWAL_WINDOW_DAYS,
    UNDO_FINE_PAYMENT_WINDOW_DAYS,
    # Audit reversal constants
    NON_REVERSIBLE_ACTIONS,
    REVERSIBLE_ACTIONS,
    ACTION_TO_REVERT_ACTION,
    # Shared helpers
    get_user as _get_user_helper,
    get_audit_log as _get_audit_log_helper,
)

from .reversal.audit_strategy import AuditReversalStrategy
from .reversal.circulation_strategy import CirculationReversalStrategy
from .reversal.enhanced_strategy import EnhancedReversalStrategy
from .reversal.fine_strategy import FineReversalStrategy
from .reversal.patron_strategy import PatronRecoveryStrategy

logger = get_logger(__name__)


class UnifiedReversalService:

    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize all strategy instances
        self._audit = AuditReversalStrategy(db)
        self._circulation = CirculationReversalStrategy(db)
        self._enhanced = EnhancedReversalStrategy(db)
        self._fine = FineReversalStrategy(db)
        self._patron = PatronRecoveryStrategy(db)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_user(self, user_id: int) -> Optional[User]:
        return await _get_user_helper(self.db, user_id)

    async def _get_audit_log(self, audit_log_id: int) -> Optional[AuditLog]:
        return await _get_audit_log_helper(self.db, audit_log_id)

    # =========================================================================
    # Circulation Reversals
    # =========================================================================

    async def undo_checkout(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "User error - accidental checkout",
    ) -> ReversalResult:
        return await self._circulation.undo_checkout(checkout_id, performer, reason)

    async def reverse_return(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "User error - mistaken return",
    ) -> ReversalResult:
        return await self._circulation.reverse_return(checkout_id, performer, reason)

    async def revert_item_status_change(
        self,
        item_id: int,
        previous_status: ItemStatus,
        performer: User,
        reason: str = "Staff correction",
    ) -> ReversalResult:
        return await self._circulation.revert_item_status_change(
            item_id, previous_status, performer, reason
        )

    # =========================================================================
    # Enhanced Reversals (holds, renewals, fine payments, suspensions)
    # =========================================================================

    async def undo_hold_placement(
        self,
        hold_id: int,
        performer: User,
        reason: str = "User requested cancellation",
    ) -> ReversalResult:
        return await self._enhanced.undo_hold_placement(hold_id, performer, reason)

    async def undo_renewal(
        self,
        checkout_id: int,
        performer: User,
        reason: str = "Patron requested undo",
    ) -> ReversalResult:
        return await self._enhanced.undo_renewal(checkout_id, performer, reason)

    async def undo_fine_payment(
        self,
        fine_id: int,
        performer: User,
        reason: str = "Payment reversal requested",
    ) -> ReversalResult:
        return await self._enhanced.undo_fine_payment(fine_id, performer, reason)

    async def undo_patron_suspension(
        self,
        user_id: int,
        performer: User,
        reason: str = "Suspension reversed",
    ) -> ReversalResult:
        return await self._enhanced.undo_patron_suspension(user_id, performer, reason)

    async def soft_delete_recovery(
        self,
        entity_type: EntityType,
        entity_id: int,
        performer: User,
        reason: str = "Recovery requested",
    ) -> ReversalResult:
        return await self._enhanced.soft_delete_recovery(
            entity_type, entity_id, performer, reason
        )

    # =========================================================================
    # Fine Reversals
    # =========================================================================

    async def undo_fine_waiver(
        self,
        fine_id: int,
        performer: User,
        reason: str = "Staff correction - waiver undone",
    ) -> ReversalResult:
        return await self._fine.undo_fine_waiver(fine_id, performer, reason)

    async def reverse_fine_payment(
        self,
        fine_id: int,
        amount_to_refund: Decimal,
        performer: User,
        reason: str = "Payment error",
    ) -> ReversalResult:
        return await self._fine.reverse_fine_payment(
            fine_id, amount_to_refund, performer, reason
        )

    # =========================================================================
    # Patron Recovery
    # =========================================================================

    async def restore_deactivated_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Account restoration - error recovery",
    ) -> ReversalResult:
        return await self._patron.restore_deactivated_patron(patron_id, performer, reason)

    async def unblock_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Block removal - error recovery",
    ) -> ReversalResult:
        return await self._patron.unblock_patron(patron_id, performer, reason)

    async def unsuspend_patron(
        self,
        patron_id: int,
        performer: User,
        reason: str = "Suspension removal - error recovery",
    ) -> ReversalResult:
        return await self._patron.unsuspend_patron(patron_id, performer, reason)

    async def list_recoverable_patrons(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._patron.list_recoverable_patrons(limit, offset)

    # =========================================================================
    # Audit Trail Reversals
    # =========================================================================

    async def get_audit_log(self, audit_log_id: int) -> Optional[AuditLog]:
        return await self._get_audit_log(audit_log_id)

    async def check_can_revert(self, audit_log_id: int) -> CanRevertResult:
        return await self._audit.check_can_revert(audit_log_id)

    async def revert(
        self,
        audit_log_id: int,
        admin_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ReversalResult:
        return await self._audit.revert(
            audit_log_id, admin_id, ip_address, user_agent
        )
