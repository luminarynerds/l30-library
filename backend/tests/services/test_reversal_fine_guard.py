# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests: fine-reversal staleness guard (H3).

_check_can_revert_fine_action must refuse when the fine's current status
has moved past what the audited action left it in.

Bug: reverting a FEE_WAIVED audit entry on a subsequently-paid fine would
blindly set fine.status = previous_status (unpaid), clobbering the payment.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.audit_log import AuditAction, AuditLog
from app.models.fine import Fine, FineStatus
from app.services.reversal.audit_strategy import AuditReversalStrategy


def _strategy_with_fine(fine):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fine
    db.execute.return_value = mock_result
    return AuditReversalStrategy(db)


def _audit_log(action, fine_id, previous_status):
    log = MagicMock(spec=AuditLog)
    log.action = action
    log.details = {"fine_id": fine_id, "previous_status": previous_status}
    return log


@pytest.mark.asyncio
async def test_check_can_revert_waive_refuses_when_fine_since_paid():
    """
    Sequence: fine waived (audit W, previous_status=unpaid) → fine paid.
    Reverting audit W must be refused — setting status back to unpaid
    would clobber the payment.
    """
    fine = MagicMock(spec=Fine)
    fine.id = 42
    fine.status = FineStatus.paid  # progressed past waived

    strategy = _strategy_with_fine(fine)
    audit_log = _audit_log(AuditAction.FEE_WAIVED, 42, "unpaid")

    result = await strategy._check_can_revert_fine_action(audit_log)

    assert not result.can_revert, (
        "Must refuse: fine is paid; reverting the waive entry would clobber the payment"
    )


@pytest.mark.asyncio
async def test_check_can_revert_waive_allows_when_fine_still_waived():
    """Happy path: fine is still waived — safe to revert the waive action."""
    fine = MagicMock(spec=Fine)
    fine.id = 7
    fine.status = FineStatus.waived  # still in expected state

    strategy = _strategy_with_fine(fine)
    audit_log = _audit_log(AuditAction.FEE_WAIVED, 7, "unpaid")

    result = await strategy._check_can_revert_fine_action(audit_log)

    assert result.can_revert, "Should allow: fine is still waived"


@pytest.mark.asyncio
async def test_check_can_revert_payment_refuses_when_fine_since_waived():
    """
    Sequence: fine paid (audit P, previous_status=unpaid) → fine waived.
    Reverting audit P must be refused.
    """
    fine = MagicMock(spec=Fine)
    fine.id = 99
    fine.status = FineStatus.waived  # progressed past paid

    strategy = _strategy_with_fine(fine)
    audit_log = _audit_log(AuditAction.FEE_PAID, 99, "unpaid")

    result = await strategy._check_can_revert_fine_action(audit_log)

    assert not result.can_revert, (
        "Must refuse: fine is now waived; reverting the payment entry would be inconsistent"
    )


@pytest.mark.asyncio
async def test_check_can_revert_payment_allows_when_fine_still_paid():
    """Happy path: fine is still paid — safe to revert the payment action."""
    fine = MagicMock(spec=Fine)
    fine.id = 5
    fine.status = FineStatus.paid  # still in expected state

    strategy = _strategy_with_fine(fine)
    audit_log = _audit_log(AuditAction.FEE_PAID, 5, "unpaid")

    result = await strategy._check_can_revert_fine_action(audit_log)

    assert result.can_revert, "Should allow: fine is still paid"
