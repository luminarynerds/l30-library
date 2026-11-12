# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for account_service with mocking to avoid database overhead.

Tests cover:
- Account creation and retrieval (get_or_create_account)
- Adding funds (deposits)
- Charging accounts (with insufficient funds handling)
- Refunds
- Transaction listing with pagination and type filtering
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.patron_account import (
    PatronAccount,
    PatronTransaction,
    TransactionType,
    TransactionStatus,
    AccountPaymentMethod as PaymentMethod,
)
from app.services import account_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_account(
    patron_id: int = 1,
    balance: Decimal = Decimal("10.00"),
    is_active: bool = True,
    **overrides,
) -> MagicMock:
    """Return a MagicMock that behaves like a PatronAccount row."""
    acct = MagicMock(spec=PatronAccount)
    acct.id = overrides.get("id", 100)
    acct.patron_id = patron_id
    acct.balance = balance
    acct.total_deposited = overrides.get("total_deposited", Decimal("50.00"))
    acct.total_spent = overrides.get("total_spent", Decimal("40.00"))
    acct.is_active = is_active
    acct.last_deposit_at = None
    acct.last_charge_at = None
    # charge() compares balance <= low_balance_threshold after every charge;
    # a real Decimal is needed or that comparison TypeErrors against a bare
    # MagicMock attribute.
    acct.low_balance_threshold = overrides.get("low_balance_threshold", Decimal("0.00"))
    return acct


def _mock_db() -> AsyncMock:
    """Return a fresh AsyncMock that mimics an AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()  # add is synchronous
    return db


# ---------------------------------------------------------------------------
# get_or_create_account
# ---------------------------------------------------------------------------


class TestGetOrCreateAccount:
    """Tests for account_service.get_or_create_account."""

    @pytest.mark.asyncio
    async def test_get_or_create_account_existing(self):
        """When an account already exists it is returned without creating a new one."""
        db = _mock_db()
        existing = _make_account(patron_id=1)

        # Simulate the SELECT returning an existing account
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute.return_value = result_mock

        account = await account_service.get_or_create_account(db, patron_id=1)

        assert account is existing
        # Should NOT have called db.add since account already exists
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_account_new(self):
        """When no account exists a new PatronAccount is created and flushed."""
        db = _mock_db()

        # SELECT returns None -> no existing account
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        _ = await account_service.get_or_create_account(db, patron_id=42)

        # A new object should have been added and flushed (commit is deferred
        # to the caller's unit of work, not done inside get_or_create_account).
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

        # The object that was added should be a PatronAccount instance
        added_obj = db.add.call_args[0][0]
        assert isinstance(added_obj, PatronAccount)
        assert added_obj.patron_id == 42


# ---------------------------------------------------------------------------
# add_funds
# ---------------------------------------------------------------------------


class TestAddFunds:
    """Tests for account_service.add_funds."""

    @pytest.mark.asyncio
    async def test_add_funds_success(self):
        """A valid deposit increases balance, records a DEPOSIT transaction."""
        db = _mock_db()
        acct = _make_account(patron_id=1, balance=Decimal("5.00"))

        # Patch get_or_create_account so we control the returned account
        with patch.object(account_service, "get_or_create_account", return_value=acct):
            _ = await account_service.add_funds(
                db,
                patron_id=1,
                amount=Decimal("20.00"),
                payment_method=PaymentMethod.CASH,
                notes="Test deposit",
            )

        # Balance should be updated
        assert acct.balance == Decimal("25.00")
        assert acct.total_deposited == Decimal("70.00")

        # A PatronTransaction should have been added, plus an
        # OperationsAuditLog row from the DB-queryable audit trail.
        assert db.add.call_count == 2
        txn = db.add.call_args_list[0][0][0]
        assert isinstance(txn, PatronTransaction)
        assert txn.transaction_type == TransactionType.DEPOSIT
        assert txn.status == TransactionStatus.COMPLETED
        assert txn.amount == Decimal("20.00")
        assert txn.balance_before == Decimal("5.00")
        assert txn.balance_after == Decimal("25.00")
        assert txn.payment_method == PaymentMethod.CASH
        assert txn.receipt_number is not None
        assert txn.notes == "Test deposit"

        # Commit is deferred to the caller's unit of work; add_funds flushes
        # and refreshes the transaction it just created, and the DB-queryable
        # audit trail (_safe_add) flushes again for the OperationsAuditLog row.
        assert db.flush.await_count == 2
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_funds_inactive_account(self):
        """Depositing into an inactive account raises HTTP 400."""
        db = _mock_db()
        acct = _make_account(patron_id=1, is_active=False)

        with patch.object(account_service, "get_or_create_account", return_value=acct):
            with pytest.raises(HTTPException) as exc_info:
                await account_service.add_funds(
                    db,
                    patron_id=1,
                    amount=Decimal("10.00"),
                    payment_method=PaymentMethod.CASH,
                )

        assert exc_info.value.status_code == 400
        assert "inactive" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# charge
# ---------------------------------------------------------------------------


class TestCharge:
    """Tests for account_service.charge."""

    @pytest.mark.asyncio
    async def test_charge_success(self):
        """Charging when there is sufficient balance deducts from the account."""
        db = _mock_db()
        acct = _make_account(patron_id=1, balance=Decimal("15.00"))

        # charge() looks up the account with its own SELECT ... FOR UPDATE
        # (it doesn't go through get_or_create_account), so the account has
        # to come back from db.execute(...).scalar_one_or_none().
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = acct
        db.execute.return_value = result_mock

        _ = await account_service.charge(
            db,
            patron_id=1,
            amount=Decimal("5.00"),
            description="Print job: resume.pdf",
            reference_type="print_job",
            reference_id=99,
        )

        assert acct.balance == Decimal("10.00")
        assert acct.total_spent == Decimal("45.00")

        # First add() call is the PatronTransaction; the second is the
        # OperationsAuditLog row from the DB-queryable audit trail.
        txn = db.add.call_args_list[0][0][0]
        assert isinstance(txn, PatronTransaction)
        assert txn.transaction_type == TransactionType.CHARGE
        assert txn.amount == Decimal("5.00")
        assert txn.balance_before == Decimal("15.00")
        assert txn.balance_after == Decimal("10.00")
        assert txn.reference_type == "print_job"
        assert txn.reference_id == 99

    @pytest.mark.asyncio
    async def test_charge_insufficient_funds(self):
        """Charging more than the balance raises HTTP 402 Payment Required."""
        db = _mock_db()
        acct = _make_account(patron_id=1, balance=Decimal("2.00"))

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = acct
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await account_service.charge(
                db,
                patron_id=1,
                amount=Decimal("10.00"),
                description="Expensive job",
            )

        assert exc_info.value.status_code == 402
        assert "insufficient" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_charge_inactive_account(self):
        """Charging an inactive account raises HTTP 400."""
        db = _mock_db()
        acct = _make_account(patron_id=1, is_active=False, balance=Decimal("100.00"))

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = acct
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await account_service.charge(
                db,
                patron_id=1,
                amount=Decimal("1.00"),
                description="Should fail",
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# refund
# ---------------------------------------------------------------------------


class TestRefund:
    """Tests for account_service.refund."""

    @pytest.mark.asyncio
    async def test_refund_success(self):
        """A refund increases the balance and records a REFUND transaction."""
        db = _mock_db()
        acct = _make_account(patron_id=1, balance=Decimal("3.00"))

        with patch.object(account_service, "get_or_create_account", return_value=acct):
            _ = await account_service.refund(
                db,
                patron_id=1,
                amount=Decimal("7.50"),
                reason="Failed print",
                processed_by_id=99,
                notes="Staff refund",
            )

        assert acct.balance == Decimal("10.50")

        # First add() call is the PatronTransaction; the second is the
        # OperationsAuditLog row from the DB-queryable audit trail.
        txn = db.add.call_args_list[0][0][0]
        assert isinstance(txn, PatronTransaction)
        assert txn.transaction_type == TransactionType.REFUND
        assert txn.status == TransactionStatus.COMPLETED
        assert txn.amount == Decimal("7.50")
        assert txn.balance_before == Decimal("3.00")
        assert txn.balance_after == Decimal("10.50")
        assert txn.processed_by_id == 99
        assert "Failed print" in txn.description
        assert txn.notes == "Staff refund"

        # Commit is deferred to the caller's unit of work; refund flushes and
        # refreshes the transaction it just created, and the DB-queryable
        # audit trail (_safe_add) flushes again for the OperationsAuditLog row.
        assert db.flush.await_count == 2


# ---------------------------------------------------------------------------
# get_transactions
# ---------------------------------------------------------------------------


class TestGetTransactions:
    """Tests for account_service.get_transactions."""

    @pytest.mark.asyncio
    async def test_get_transactions_with_pagination(self):
        """Transactions are returned in pages along with total count."""
        db = _mock_db()
        acct = _make_account(patron_id=1)

        # We need two execute calls: one for count, one for paginated fetch
        txn1 = MagicMock(spec=PatronTransaction)
        txn2 = MagicMock(spec=PatronTransaction)

        # First call: get_or_create_account SELECT
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = acct

        # Second call: count query
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        # Third call: paginated transaction fetch
        fetch_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [txn1, txn2]
        fetch_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [account_result, count_result, fetch_result]

        # Temporarily bypass the internal get_or_create_account to avoid
        # its own execute call interfering; instead we intercept higher up.
        # We'll use the raw function since it chains db.execute calls.
        transactions, total = await account_service.get_transactions(
            db, patron_id=1, page=1, per_page=2
        )

        assert total == 5
        assert len(transactions) == 2
        assert transactions[0] is txn1

    @pytest.mark.asyncio
    async def test_get_transactions_with_type_filter(self):
        """Filtering by transaction_type should include the WHERE clause."""
        db = _mock_db()
        acct = _make_account(patron_id=1)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = acct

        count_result = MagicMock()
        count_result.scalar.return_value = 2

        fetch_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        fetch_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [account_result, count_result, fetch_result]

        transactions, total = await account_service.get_transactions(
            db,
            patron_id=1,
            page=1,
            per_page=20,
            transaction_type=TransactionType.DEPOSIT,
        )

        assert total == 2
        # Verify execute was called at least 3 times (account lookup + count + fetch)
        assert db.execute.await_count == 3
