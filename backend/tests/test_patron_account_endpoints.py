# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for patron account API endpoints (patron_account.py).

Tests the FastAPI route handlers using mocked service layer dependencies.
Covers:
- GET  /patron/account (get balance)
- GET  /patron/account/transactions
- POST /patron/account/deposit
- POST /staff/patron/{id}/deposit
- POST /staff/patron/{id}/refund
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.models.patron_account import (
    PatronAccount,
    PatronTransaction,
    TransactionType,
    TransactionStatus,
    AccountPaymentMethod as PaymentMethod,
)
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(user_id: int = 1, role: UserRole = UserRole.PATRON) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"user{user_id}@example.com"
    user.role = role
    user.is_active = True
    return user


def _make_account(patron_id: int = 1, balance: Decimal = Decimal("25.00")) -> MagicMock:
    now = datetime.now(timezone.utc)
    acct = MagicMock(spec=PatronAccount)
    acct.id = 100
    acct.patron_id = patron_id
    acct.balance = balance
    acct.total_deposited = Decimal("100.00")
    acct.total_spent = Decimal("75.00")
    acct.is_active = True
    acct.low_balance_threshold = Decimal("2.00")
    acct.auto_reload_enabled = False
    acct.last_deposit_at = now
    acct.last_charge_at = now
    acct.created_at = now
    return acct


def _make_transaction(
    txn_id: int = 1,
    account_id: int = 100,
    txn_type: TransactionType = TransactionType.DEPOSIT,
    amount: Decimal = Decimal("20.00"),
) -> MagicMock:
    now = datetime.now(timezone.utc)
    txn = MagicMock(spec=PatronTransaction)
    txn.id = txn_id
    txn.account_id = account_id
    txn.transaction_type = txn_type
    txn.status = TransactionStatus.COMPLETED
    txn.amount = amount
    txn.balance_before = Decimal("5.00")
    txn.balance_after = Decimal("25.00")
    txn.payment_method = PaymentMethod.CASH
    txn.description = "Test transaction"
    txn.reference_type = None
    txn.reference_id = None
    txn.receipt_number = "RCP-ABCDEF123456"
    txn.notes = None
    txn.created_at = now
    txn.processed_by_id = None
    return txn


# ===========================================================================
# GET /patron/account  (get_account_balance)
# ===========================================================================


class TestGetBalance:
    """Tests for the get_account_balance endpoint."""

    @pytest.mark.asyncio
    async def test_get_balance(self):
        """Returns the patron's account balance information."""
        from app.api.v1.patron_account import get_account_balance

        user = _make_user(user_id=1)
        db = AsyncMock()
        account = _make_account(patron_id=1, balance=Decimal("42.50"))

        with patch(
            "app.api.v1.patron_account.account_service.get_balance",
            new_callable=AsyncMock,
            return_value=account,
        ):
            response = await get_account_balance(current_user=user, db=db)

        # The endpoint calls AccountBalanceResponse.model_validate(account)
        # which requires from_attributes=True; the result should contain balance info.
        assert response.balance == Decimal("42.50")
        assert response.patron_id == 1
        assert response.is_active is True


# ===========================================================================
# GET /patron/account/transactions
# ===========================================================================


class TestGetTransactions:
    """Tests for the get_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_get_transactions(self):
        """Returns paginated transaction list."""
        from app.api.v1.patron_account import get_transactions

        user = _make_user(user_id=1)
        db = AsyncMock()
        txn1 = _make_transaction(txn_id=1, amount=Decimal("10.00"))
        txn2 = _make_transaction(txn_id=2, amount=Decimal("5.00"))

        with patch(
            "app.api.v1.patron_account.account_service.get_transactions",
            new_callable=AsyncMock,
            return_value=([txn1, txn2], 2),
        ):
            response = await get_transactions(
                page=1,
                per_page=20,
                transaction_type=None,
                current_user=user,
                db=db,
            )

        assert response.total == 2
        assert response.page == 1
        assert response.per_page == 20
        assert len(response.items) == 2


# ===========================================================================
# POST /patron/account/deposit
# ===========================================================================


class TestDepositFunds:
    """Tests for the deposit_funds endpoint."""

    @pytest.mark.asyncio
    async def test_deposit_funds(self):
        """A patron can deposit funds into their own account."""
        from app.api.v1.patron_account import deposit_funds
        from app.schemas.patron_account import DepositRequest

        user = _make_user(user_id=1)
        db = AsyncMock()
        txn = _make_transaction(
            txn_id=10,
            txn_type=TransactionType.DEPOSIT,
            amount=Decimal("50.00"),
        )

        request = DepositRequest(
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.ONLINE,
            notes="Self-service deposit",
        )

        with patch(
            "app.api.v1.patron_account.account_service.add_funds",
            new_callable=AsyncMock,
            return_value=txn,
        ) as mock_add:
            response = await deposit_funds(
                request=request, current_user=user, db=db
            )

        mock_add.assert_awaited_once_with(
            db,
            1,
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.ONLINE,
            notes="Self-service deposit",
        )

        assert response.amount == Decimal("50.00")
        assert response.transaction_type == TransactionType.DEPOSIT


# ===========================================================================
# POST /staff/patron/{patron_id}/deposit
# ===========================================================================


class TestStaffDeposit:
    """Tests for the staff_deposit endpoint."""

    @pytest.mark.asyncio
    async def test_staff_deposit(self):
        """Staff can deposit funds for any patron, recording processed_by_id."""
        from app.api.v1.patron_account import staff_deposit
        from app.schemas.patron_account import StaffDepositRequest

        staff = _make_user(user_id=99, role=UserRole.STAFF)
        db = AsyncMock()
        txn = _make_transaction(
            txn_id=20,
            txn_type=TransactionType.DEPOSIT,
            amount=Decimal("100.00"),
        )

        request = StaffDepositRequest(
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
            notes="Cash at desk",
        )

        with patch(
            "app.api.v1.patron_account.account_service.add_funds",
            new_callable=AsyncMock,
            return_value=txn,
        ) as mock_add:
            response = await staff_deposit(
                patron_id=42, request=request, current_user=staff, db=db
            )

        mock_add.assert_awaited_once_with(
            db,
            42,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
            processed_by_id=99,
            notes="Cash at desk",
        )

        assert response.amount == Decimal("100.00")


# ===========================================================================
# POST /staff/patron/{patron_id}/refund
# ===========================================================================


class TestStaffRefund:
    """Tests for the staff_refund endpoint."""

    @pytest.mark.asyncio
    async def test_staff_refund(self):
        """Staff can issue a refund to a patron's account."""
        from app.api.v1.patron_account import staff_refund
        from app.schemas.patron_account import RefundRequest

        staff = _make_user(user_id=99, role=UserRole.STAFF)
        db = AsyncMock()
        txn = _make_transaction(
            txn_id=30,
            txn_type=TransactionType.REFUND,
            amount=Decimal("15.00"),
        )

        request = RefundRequest(
            amount=Decimal("15.00"),
            reason="Printer jam",
            notes="Refunded due to paper jam",
        )

        with patch(
            "app.api.v1.patron_account.account_service.refund",
            new_callable=AsyncMock,
            return_value=txn,
        ) as mock_refund:
            response = await staff_refund(
                patron_id=42, request=request, current_user=staff, db=db
            )

        mock_refund.assert_awaited_once_with(
            db,
            42,
            amount=Decimal("15.00"),
            reason="Printer jam",
            processed_by_id=99,
            notes="Refunded due to paper jam",
        )

        assert response.amount == Decimal("15.00")
        assert response.transaction_type == TransactionType.REFUND
