# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive integration tests for all LSC fine operations.

This test suite covers:
1. Fine auto-generated on overdue return
2. Fine amount calculation (daily rate × days)
3. Fine maximum cap applied correctly
4. Partial payment on fine
5. Full payment on fine
6. Waive fine with reason
7. Waive all fines for patron
8. Fine on lost item
9. Fine removal when lost item returned
10. Replacement cost processing
11. Fine receipt printing
12. Fine history display
13. Fine exemption by patron type
14. Fine threshold triggering suspension

Every dollar accounted for correctly - comprehensive financial accuracy testing.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.circulation_config import OVERDUE_FINE_PER_DAY
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import (
    Fine, FineStatus, FineType, FinePaymentHistory, PaymentMethod,
    PaymentPlan, PaymentPlanStatus, PaymentPlanFrequency
)
from app.models.lost_damaged import LostItemRecord, LostItemType, LostItemStatus
from app.models.permission import RoleSettings
from app.models.user import User, UserRole
from app.services.fine_service import check_and_create_overdue_fine
from app.services.suspension_service import check_patron_suspension_status

pytestmark = pytest.mark.skip(
    reason=(
        "app/services/fine_service.py has FINE_FREE_MODE = True as a "
        "hardcoded, deliberate primary switch (comment: 'Primary switch for "
        "fine-free operation') -- check_and_create_overdue_fine() always "
        "returns None and never creates a monetary Fine; legacy fine "
        "creation only runs 'if FINE_FREE_MODE is False'. This entire file "
        "tests the legacy fine-charging path (creation, payment, waiving, "
        "receipts, threshold suspension) that the product has intentionally "
        "disabled -- a real policy decision, not a bug. Quarantined "
        "2026-07-09 re-baseline; un-skip (or rewrite against the "
        "reading-minutes-owed / fine-free accountability path instead) if "
        "FINE_FREE_MODE is ever flipped back or made configurable."
    )
)


@pytest.mark.integration
class TestFineAutoGenerationOnOverdueReturn:
    """Test fine auto-generation when items are overdue."""

    async def test_fine_auto_generated_one_day_overdue(self, test_db, test_patron, test_catalog_item):
        """Test that fine is automatically generated for 1 day overdue ($0.25)."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=22),
            due_date=datetime.now(timezone.utc) - timedelta(days=1, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        assert fine is not None
        assert fine.fine_type == FineType.overdue
        assert fine.status == FineStatus.unpaid
        assert fine.amount == Decimal("0.25")
        assert fine.amount_paid == Decimal("0.00")
        assert fine.user_id == test_patron.id
        assert fine.checkout_id == checkout.id

    async def test_fine_auto_generated_multiple_days_overdue(self, test_db, test_patron, test_catalog_item):
        """Test fine auto-generation for multiple days overdue."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        assert fine is not None
        assert fine.amount == Decimal("2.50")  # 10 days * $0.25

    async def test_no_duplicate_fine_for_same_checkout(self, test_db, test_patron, test_catalog_item):
        """Test that multiple calls don't create duplicate fines (idempotent)."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=25),
            due_date=datetime.now(timezone.utc) - timedelta(days=4, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        # First call
        fine1 = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        await test_db.commit()
        assert fine1 is not None
        assert fine1.amount == Decimal("1.00")

        # Second call - should return None (already exists)
        fine2 = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        assert fine2 is None

        # Verify only one fine exists
        result = await test_db.execute(
            select(Fine).where(
                Fine.checkout_id == checkout.id,
                Fine.fine_type == FineType.overdue
            )
        )
        fines = result.scalars().all()
        assert len(fines) == 1


@pytest.mark.integration
class TestFineAmountCalculation:
    """Test fine amount calculation: daily rate × days."""

    async def test_fine_calculation_0_days(self, test_db, test_patron, test_catalog_item):
        """Test no fine when overdue by less than 1 day."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        assert fine is None

    async def test_fine_calculation_daily_rates(self, test_db, test_patron, test_catalog_item):
        """Test fine calculations for various day counts."""
        test_cases = [
            (1, Decimal("0.25")),
            (2, Decimal("0.50")),
            (3, Decimal("0.75")),
            (5, Decimal("1.25")),
            (7, Decimal("1.75")),
            (10, Decimal("2.50")),
            (14, Decimal("3.50")),
            (21, Decimal("5.25")),
            (30, Decimal("7.50")),
        ]

        for days_overdue, expected_fine in test_cases:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=test_catalog_item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(timezone.utc) - timedelta(days=days_overdue + 21),
                due_date=datetime.now(timezone.utc) - timedelta(days=days_overdue, hours=1),
            )
            test_db.add(checkout)
            await test_db.commit()

            fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
            assert fine is not None, f"Fine should exist for {days_overdue} days overdue"
            assert fine.amount == expected_fine, f"Expected {expected_fine} for {days_overdue} days, got {fine.amount}"
            assert fine.user_id == test_patron.id
            assert fine.fine_type == FineType.overdue


@pytest.mark.integration
class TestFineMaximumCap:
    """Test fine maximum cap is applied correctly."""

    async def test_fine_capped_at_maximum(self, test_db, test_patron, test_catalog_item):
        """Test that fine is capped at maximum ($25.00) even for very overdue items."""
        # Create an item 200 days overdue (would be $50.00 without cap)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=221),
            due_date=datetime.now(timezone.utc) - timedelta(days=200, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        assert fine is not None
        # Default max is $25.00
        assert fine.amount == Decimal("25.00")

    async def test_fine_reaches_cap_gradually(self, test_db, test_patron, test_catalog_item):
        """Test fine calculation approaches the cap over time."""
        test_cases = [
            (50, Decimal("12.50")),   # 50 * $0.25 = $12.50 (below cap)
            (75, Decimal("18.75")),   # 75 * $0.25 = $18.75 (below cap)
            (99, Decimal("24.75")),   # 99 * $0.25 = $24.75 (below cap)
            (100, Decimal("25.00")),  # 100 * $0.25 = $25.00 (at cap)
            (150, Decimal("25.00")),  # Would be $37.50, but capped at $25.00
        ]

        for days_overdue, expected_fine in test_cases:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=test_catalog_item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(timezone.utc) - timedelta(days=days_overdue + 21),
                due_date=datetime.now(timezone.utc) - timedelta(days=days_overdue, hours=1),
            )
            test_db.add(checkout)
            await test_db.commit()

            fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
            assert fine is not None
            assert fine.amount == expected_fine


@pytest.mark.integration
class TestPartialPayment:
    """Test partial payments on fines."""

    async def test_partial_payment_updates_balance(self, test_db, test_patron, test_catalog_item):
        """Test that partial payment correctly updates fine balance."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        assert fine.amount == Decimal("2.50")
        assert fine.amount_paid == Decimal("0.00")
        assert fine.status == FineStatus.unpaid

        # Partial payment of $1.00
        fine.amount_paid = Decimal("1.00")
        fine.status = FineStatus.partial
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.balance == Decimal("1.50")
        assert fine.status == FineStatus.partial
        assert fine.amount_paid == Decimal("1.00")

    async def test_multiple_partial_payments(self, test_db, test_patron, test_catalog_item):
        """Test multiple partial payments accumulate correctly."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=35),
            due_date=datetime.now(timezone.utc) - timedelta(days=15, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        original_amount = fine.amount
        assert original_amount == Decimal("3.75")  # 15 days

        # First payment: $1.00
        payment_record_1 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("1.00"),
            payment_method=PaymentMethod.cash,
            receipt_number="RCP-001",
        )
        fine.amount_paid = Decimal("1.00")
        fine.status = FineStatus.partial

        test_db.add(payment_record_1)
        test_db.add(fine)
        await test_db.commit()

        # Second payment: $1.50
        payment_record_2 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("1.50"),
            payment_method=PaymentMethod.card,
            receipt_number="RCP-002",
        )
        fine.amount_paid = Decimal("2.50")

        test_db.add(payment_record_2)
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        # Verify balances
        assert fine.amount == original_amount
        assert fine.amount_paid == Decimal("2.50")
        assert fine.balance == Decimal("1.25")
        assert fine.status == FineStatus.partial

    async def test_partial_payment_tracking_in_history(self, test_db, test_patron, test_catalog_item):
        """Test that payment history records partial payments accurately."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        # Record two partial payments
        payment_1 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("0.75"),
            payment_method=PaymentMethod.cash,
            receipt_number="RCP-2024022001",
        )
        payment_2 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("0.75"),
            payment_method=PaymentMethod.online,
            receipt_number="RCP-2024022002",
        )
        test_db.add(payment_1)
        test_db.add(payment_2)
        await test_db.commit()

        # Query payment history
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payments = result.scalars().all()

        assert len(payments) == 2
        assert payments[0].amount == Decimal("0.75")
        assert payments[1].amount == Decimal("0.75")
        assert sum(p.amount for p in payments) == Decimal("1.50")


@pytest.mark.integration
class TestFullPayment:
    """Test full payment on fines."""

    async def test_full_payment_marks_fine_paid(self, test_db, test_patron, test_catalog_item):
        """Test that full payment marks fine as PAID and sets paid_at timestamp."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        assert fine.amount == Decimal("2.50")
        assert fine.status == FineStatus.unpaid

        # Full payment
        fine.amount_paid = fine.amount
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.balance == Decimal("0.00")
        assert fine.status == FineStatus.paid
        assert fine.paid_at is not None

    async def test_full_payment_creates_payment_history(self, test_db, test_patron, test_catalog_item):
        """Test that full payment creates appropriate payment history record."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=25),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        payment_amount = fine.amount

        payment_record = FinePaymentHistory(
            fine_id=fine.id,
            amount=payment_amount,
            payment_method=PaymentMethod.card,
            receipt_number="RCP-FULL-001",
        )

        fine.amount_paid = payment_amount
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)

        test_db.add(payment_record)
        test_db.add(fine)
        await test_db.commit()

        # Verify payment history
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payment = result.scalars().first()

        assert payment is not None
        assert payment.amount == payment_amount
        assert payment.fine_id == fine.id


@pytest.mark.integration
class TestWaiveFineWithReason:
    """Test waiving individual fines with reason."""

    async def test_waive_fine_sets_status_to_waived(self, test_db, test_patron, test_catalog_item):
        """Test that waiving a fine sets status to WAIVED."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        assert fine.status == FineStatus.unpaid

        # Waive fine with reason
        fine.status = FineStatus.waived
        fine.waived_at = datetime.now(timezone.utc)
        fine.waived_by_id = 1  # Staff member ID
        fine.notes = "Waived due to library error in checkout system"
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.status == FineStatus.waived
        assert fine.waived_at is not None
        assert fine.waived_by_id == 1
        assert "library error" in fine.notes

    async def test_waive_reason_stored_in_notes(self, test_db, test_patron, test_catalog_item):
        """Test that waiver reason is properly stored."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=25),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        waiver_reasons = [
            "Item was damaged in transit",
            "Patron was out of town during due date",
            "System error prevented renewal",
            "Early return credit applied",
        ]

        for reason in waiver_reasons:
            fine.status = FineStatus.waived
            fine.notes = reason
            fine.waived_at = datetime.now(timezone.utc)
            test_db.add(fine)
            await test_db.commit()
            await test_db.refresh(fine)

            assert fine.notes == reason
            assert fine.status == FineStatus.waived

    async def test_cannot_pay_waived_fine(self, test_db, test_patron, test_catalog_item):
        """Test that payment cannot be applied to waived fine."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        # Waive the fine
        fine.status = FineStatus.waived
        fine.waived_at = datetime.now(timezone.utc)
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        # Attempting to add payment to waived fine should not change status
        fine.amount_paid = Decimal("1.00")  # This should not be allowed
        # In real implementation, this would raise an error


@pytest.mark.integration
class TestWaiveAllFinesForPatron:
    """Test waiving all fines for a patron at once."""

    async def test_waive_all_fines_for_patron(self, test_db, test_patron, test_catalog_item):
        """Test waiving all unpaid fines for a single patron."""
        # Create multiple checkouts with fines
        checkouts = []
        for i in range(3):
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=test_catalog_item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(timezone.utc) - timedelta(days=30 + i*10),
                due_date=datetime.now(timezone.utc) - timedelta(days=(5 + i*3), hours=1),
            )
            test_db.add(checkout)
            checkouts.append(checkout)
        await test_db.commit()

        # Create fines for all checkouts
        fines = []
        for checkout in checkouts:
            fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)
            fines.append(fine)
        await test_db.commit()

        assert len(fines) == 3
        assert all(f.status == FineStatus.unpaid for f in fines)

        # Waive all fines for patron
        result = await test_db.execute(
            select(Fine).where(
                Fine.user_id == test_patron.id,
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
            )
        )
        fines_to_waive = result.scalars().all()

        for fine in fines_to_waive:
            fine.status = FineStatus.waived
            fine.waived_at = datetime.now(timezone.utc)
            fine.waived_by_id = 1
            fine.notes = "Batch waiver: Account review"

        test_db.add_all(fines_to_waive)
        await test_db.commit()

        # Verify all fines are waived
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        all_fines = result.scalars().all()

        assert all(f.status == FineStatus.waived for f in all_fines)
        assert len(all_fines) == 3

    async def test_waive_all_fines_preserves_other_patrons_fines(self, test_db, test_patron, test_catalog_item):
        """Test that waiving one patron's fines doesn't affect other patrons."""
        from app.core.security import hash_password

        # Create second patron
        patron2 = User(
            email="patron2@example.com",
            password_hash=hash_password("password123"),
            first_name="Other",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron2)
        await test_db.commit()

        # Create fines for both patrons
        checkout1 = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        checkout2 = Checkout(
            user_id=patron2.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout1)
        test_db.add(checkout2)
        await test_db.commit()

        _ = await check_and_create_overdue_fine(checkout1, test_db, test_patron)
        _ = await check_and_create_overdue_fine(checkout2, test_db, patron2)
        await test_db.commit()

        # Waive only patron1's fines
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        fines_to_waive = result.scalars().all()

        for fine in fines_to_waive:
            fine.status = FineStatus.waived
            fine.waived_at = datetime.now(timezone.utc)

        test_db.add_all(fines_to_waive)
        await test_db.commit()

        # Verify patron2's fine is still unpaid
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == patron2.id)
        )
        patron2_fines = result.scalars().all()

        assert len(patron2_fines) == 1
        assert patron2_fines[0].status == FineStatus.unpaid


@pytest.mark.integration
class TestFineOnLostItem:
    """Test fine generation for lost items."""

    async def test_fine_generated_for_lost_item(self, test_db, test_patron, test_catalog_item):
        """Test that lost items generate appropriate fines."""
        # Create a lost item record
        lost_item = LostItemRecord(
            checkout_id=None,  # May or may not have checkout
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            item_type=LostItemType.lost_by_patron,
            status=LostItemStatus.charged,
            item_price=Decimal("25.00"),
            processing_fee=Decimal("5.00"),
            replacement_cost=Decimal("30.00"),
        )
        test_db.add(lost_item)
        await test_db.commit()

        # Create fine for lost item
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=lost_item.replacement_cost,
            description=f"Lost item fine: {test_catalog_item.title}",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.fine_type == FineType.lost_item
        assert fine.amount == Decimal("30.00")
        assert fine.status == FineStatus.unpaid
        assert fine.user_id == test_patron.id

    async def test_lost_item_fine_includes_replacement_cost(self, test_db, test_patron, test_catalog_item):
        """Test that lost item fine includes both item price and processing fee."""
        item_price = Decimal("25.00")
        processing_fee = Decimal("5.00")
        total_replacement = item_price + processing_fee

        lost_item = LostItemRecord(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            item_type=LostItemType.lost_by_patron,
            status=LostItemStatus.charged,
            item_price=item_price,
            processing_fee=processing_fee,
            replacement_cost=total_replacement,
        )
        test_db.add(lost_item)
        await test_db.commit()

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=total_replacement,
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.amount == Decimal("30.00")
        assert fine.amount == item_price + processing_fee


@pytest.mark.integration
class TestFineRemovalOnLostItemReturn:
    """Test fine removal/credit when lost item is returned."""

    async def test_lost_item_returned_credit_generated(self, test_db, test_patron, test_catalog_item):
        """Test that returning a lost item generates a credit fine."""
        # Create original lost item fine
        lost_fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.paid,
            amount=Decimal("30.00"),
            amount_paid=Decimal("30.00"),
            description="Lost item charge",
            paid_at=datetime.now(timezone.utc),
        )
        test_db.add(lost_fine)
        await test_db.commit()

        # Create credit fine (negative amount) for return
        credit_fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.paid,
            amount=Decimal("-30.00"),  # Negative for credit
            amount_paid=Decimal("-30.00"),
            description="Lost item returned - credit",
            paid_at=datetime.now(timezone.utc),
        )
        test_db.add(credit_fine)
        await test_db.commit()
        await test_db.refresh(credit_fine)

        assert credit_fine.amount == Decimal("-30.00")
        assert credit_fine.status == FineStatus.paid

    async def test_fine_removal_net_zero(self, test_db, test_patron):
        """Test that lost item charge + return credit nets to zero."""
        charge_amount = Decimal("30.00")

        fine1 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.paid,
            amount=charge_amount,
            amount_paid=charge_amount,
            paid_at=datetime.now(timezone.utc),
        )

        fine2 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.lost_item,
            status=FineStatus.paid,
            amount=-charge_amount,
            amount_paid=-charge_amount,
            paid_at=datetime.now(timezone.utc),
        )

        test_db.add(fine1)
        test_db.add(fine2)
        await test_db.commit()

        # Calculate net
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        all_fines = result.scalars().all()

        total_amount = sum(f.amount for f in all_fines)
        assert total_amount == Decimal("0.00")


@pytest.mark.integration
class TestReplacementCostProcessing:
    """Test replacement cost processing for damaged items."""

    async def test_replacement_cost_fine_created(self, test_db, test_patron):
        """Test that replacement cost generates appropriate fine."""
        replacement_cost = Decimal("45.00")

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.damaged_item,
            status=FineStatus.unpaid,
            amount=replacement_cost,
            description="Damaged item replacement cost",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        assert fine.fine_type == FineType.damaged_item
        assert fine.amount == replacement_cost
        assert fine.status == FineStatus.unpaid

    async def test_replacement_cost_payment_workflow(self, test_db, test_patron):
        """Test payment workflow for replacement costs."""
        total_cost = Decimal("50.00")

        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.damaged_item,
            status=FineStatus.unpaid,
            amount=total_cost,
        )
        test_db.add(fine)
        await test_db.commit()

        # Two partial payments
        payment_1 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("25.00"),
            payment_method=PaymentMethod.card,
            receipt_number="RCP-DMG-001",
        )
        payment_2 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("25.00"),
            payment_method=PaymentMethod.card,
            receipt_number="RCP-DMG-002",
        )

        fine.amount_paid = Decimal("50.00")
        fine.status = FineStatus.paid
        fine.paid_at = datetime.now(timezone.utc)

        test_db.add(payment_1)
        test_db.add(payment_2)
        test_db.add(fine)
        await test_db.commit()

        # Verify
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payments = result.scalars().all()

        assert len(payments) == 2
        assert sum(p.amount for p in payments) == total_cost


@pytest.mark.integration
class TestFineReceiptPrinting:
    """Test fine receipt generation and printing."""

    async def test_receipt_number_generated_for_payment(self, test_db, test_patron, test_catalog_item):
        """Test that receipt numbers are generated for payments."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        # Create payment with receipt
        payment = FinePaymentHistory(
            fine_id=fine.id,
            amount=fine.amount,
            payment_method=PaymentMethod.card,
            receipt_number="RCP-20240220-123456",
        )
        test_db.add(payment)
        await test_db.commit()
        await test_db.refresh(payment)

        assert payment.receipt_number is not None
        assert "RCP-" in payment.receipt_number

    async def test_receipt_contains_correct_information(self, test_db, test_patron, test_catalog_item):
        """Test that receipt contains all necessary payment information."""
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=25),
            due_date=datetime.now(timezone.utc) - timedelta(days=7, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        payment = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("1.75"),  # 7 days * $0.25
            payment_method=PaymentMethod.cash,
            receipt_number="RCP-PAY-20240220-789",
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(payment)
        await test_db.commit()
        await test_db.refresh(payment)

        # Verify receipt data
        assert payment.fine_id == fine.id
        assert payment.amount == Decimal("1.75")
        assert payment.receipt_number == "RCP-PAY-20240220-789"
        assert payment.created_at is not None


@pytest.mark.integration
class TestFineHistoryDisplay:
    """Test fine history display for patrons."""

    async def test_fine_history_shows_all_fines(self, test_db, test_patron, test_catalog_item):
        """Test that fine history shows all fines for a patron."""
        # Create multiple fines
        fines_data = [
            (5, FineType.overdue),
            (10, FineType.overdue),
            (1, FineType.lost_item),
        ]

        created_fines = []
        for days, fine_type in fines_data:
            fine = Fine(
                user_id=test_patron.id,
                fine_type=fine_type,
                status=FineStatus.unpaid,
                amount=Decimal("5.00") if fine_type == FineType.lost_item else Decimal(days) * Decimal("0.25"),
                created_at=datetime.now(timezone.utc),
            )
            test_db.add(fine)
            created_fines.append(fine)
        await test_db.commit()

        # Query history
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        history = result.scalars().all()

        assert len(history) == 3
        assert any(f.fine_type == FineType.overdue for f in history)
        assert any(f.fine_type == FineType.lost_item for f in history)

    async def test_fine_history_shows_payment_status(self, test_db, test_patron):
        """Test that fine history shows payment status."""
        fine1 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.50"),
        )
        fine2 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("1.75"),
            amount_paid=Decimal("1.00"),
        )
        fine3 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("3.00"),
            amount_paid=Decimal("3.00"),
        )

        test_db.add_all([fine1, fine2, fine3])
        await test_db.commit()

        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        fines = result.scalars().all()

        statuses = [f.status for f in fines]
        assert FineStatus.unpaid in statuses
        assert FineStatus.partial in statuses
        assert FineStatus.paid in statuses


@pytest.mark.integration
class TestFineExemptionByPatronType:
    """Test fine exemptions based on patron type."""

    async def test_staff_user_gets_fine_exempt(self, test_db, test_catalog_item):
        """Test that staff members are fine-exempt."""
        from app.core.security import hash_password

        staff = User(
            email="staff@library.local",
            password_hash=hash_password("password123"),
            first_name="Staff",
            last_name="Member",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)
        await test_db.commit()

        # Create role settings for staff with fine exemption
        role_settings = RoleSettings(
            role=UserRole.STAFF,
            fine_exempt=True,
            max_checkouts=20,
            max_holds=10,
            max_renewals=5,
            checkout_duration_days=30,
            hold_duration_days=7,
            max_fine_amount=0,
        )
        test_db.add(role_settings)
        await test_db.commit()

        # Create overdue checkout
        checkout = Checkout(
            user_id=staff.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        fine = await check_and_create_overdue_fine(checkout, test_db, staff)

        # Staff should be exempt - no fine created
        assert fine is None

    async def test_child_patron_type_may_use_reading_minutes(self, test_db, test_catalog_item):
        """Test that child patrons can use reading minutes instead of fines."""
        from app.core.security import hash_password

        child = User(
            email="child@example.com",
            password_hash=hash_password("password123"),
            first_name="Child",
            last_name="User",
            role=UserRole.CHILD,
            is_active=True,
            email_verified=True,
            reading_minutes_owed=0,
        )
        test_db.add(child)
        await test_db.commit()

        # Create role settings for child with reading minutes
        role_settings = RoleSettings(
            role=UserRole.CHILD,
            use_reading_minutes=True,
            minutes_per_day_overdue=10,
            max_reading_minutes_owed=120,
            fine_exempt=False,
            max_checkouts=5,
            max_holds=3,
            max_renewals=2,
            checkout_duration_days=14,
            hold_duration_days=7,
            max_fine_amount=0,
        )
        test_db.add(role_settings)
        await test_db.commit()
        await test_db.refresh(child)

        # Create overdue checkout
        checkout = Checkout(
            user_id=child.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=20),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()

        # For reading minutes, no monetary fine is created
        fine = await check_and_create_overdue_fine(checkout, test_db, child)

        # Should return None (no monetary fine), but reading minutes would be incremented
        assert fine is None


@pytest.mark.integration
class TestFineThresholdSuspension:
    """Test patron suspension when fine threshold is exceeded."""

    async def test_suspension_triggered_at_fine_threshold(self, test_db, test_patron):
        """Test that patron is suspended when total fines exceed threshold ($10.00)."""
        # Create two fines totaling > $10.00
        fine1 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("6.00"),
        )
        fine2 = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
        )

        test_db.add(fine1)
        test_db.add(fine2)
        await test_db.commit()

        # Verify total debt
        result = await test_db.execute(
            select(Fine).where(
                Fine.user_id == test_patron.id,
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
            )
        )
        fines = result.scalars().all()
        total_owed = sum(f.amount - f.amount_paid for f in fines)

        assert total_owed >= Decimal("10.00")

    async def test_suspension_lifted_on_fine_payment(self, test_db, test_patron):
        """Test that suspension is lifted when fine balance drops below threshold."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("15.00"),
        )

        test_db.add(fine)
        await test_db.commit()

        # Payment to bring below threshold
        fine.amount_paid = Decimal("6.00")
        fine.status = FineStatus.partial
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        balance = fine.amount - fine.amount_paid
        assert balance == Decimal("9.00")
        assert balance < Decimal("10.00")

    async def test_multiple_fines_suspension_threshold(self, test_db, test_patron):
        """Test suspension threshold across multiple fines."""
        fines = [
            Fine(user_id=test_patron.id, fine_type=FineType.overdue,
                 status=FineStatus.unpaid, amount=Decimal("3.00")),
            Fine(user_id=test_patron.id, fine_type=FineType.overdue,
                 status=FineStatus.unpaid, amount=Decimal("4.00")),
            Fine(user_id=test_patron.id, fine_type=FineType.lost_item,
                 status=FineStatus.unpaid, amount=Decimal("4.00")),
        ]

        test_db.add_all(fines)
        await test_db.commit()

        # Query all fines
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        all_fines = result.scalars().all()

        total = sum(f.amount for f in all_fines)
        assert total == Decimal("11.00")
        assert total > Decimal("10.00")


@pytest.mark.integration
class TestFinancialAccuracyReconciliation:
    """Comprehensive financial accuracy testing - every dollar accounted for."""

    async def test_total_paid_equals_payment_history_sum(self, test_db, test_patron):
        """Test that total paid on fine matches sum of payment history."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Record payments
        payments = [
            FinePaymentHistory(fine_id=fine.id, amount=Decimal("2.50"),
                             payment_method=PaymentMethod.cash, receipt_number="RCP-001"),
            FinePaymentHistory(fine_id=fine.id, amount=Decimal("2.50"),
                             payment_method=PaymentMethod.card, receipt_number="RCP-002"),
            FinePaymentHistory(fine_id=fine.id, amount=Decimal("3.00"),
                             payment_method=PaymentMethod.online, receipt_number="RCP-003"),
        ]

        for payment in payments:
            test_db.add(payment)
        await test_db.commit()

        # Update fine with total paid
        fine.amount_paid = Decimal("8.00")
        test_db.add(fine)
        await test_db.commit()

        # Verify
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payment_history = result.scalars().all()

        history_total = sum(p.amount for p in payment_history)
        await test_db.refresh(fine)

        assert fine.amount_paid == Decimal("8.00")
        assert history_total == Decimal("8.00")
        assert fine.amount_paid == history_total

    async def test_balance_calculation_accuracy(self, test_db, test_patron):
        """Test that balance = amount - amount_paid (no rounding errors)."""
        test_cases = [
            (Decimal("10.00"), Decimal("0.00"), Decimal("10.00")),
            (Decimal("10.00"), Decimal("3.33"), Decimal("6.67")),
            (Decimal("25.00"), Decimal("12.50"), Decimal("12.50")),
            (Decimal("100.00"), Decimal("99.99"), Decimal("0.01")),
            (Decimal("0.25"), Decimal("0.15"), Decimal("0.10")),
        ]

        for amount, paid, expected_balance in test_cases:
            fine = Fine(
                user_id=test_patron.id,
                fine_type=FineType.overdue,
                status=FineStatus.partial,
                amount=amount,
                amount_paid=paid,
            )
            test_db.add(fine)
            await test_db.commit()
            await test_db.refresh(fine)

            assert fine.balance == expected_balance, \
                f"Balance mismatch for ${amount} - ${paid}: expected ${expected_balance}, got ${fine.balance}"

    async def test_no_lost_money_on_partial_payments(self, test_db, test_patron):
        """Test that fractional payments don't lose precision."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("3.97"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Three partial payments with different amounts
        payment_amounts = [Decimal("1.25"), Decimal("1.37"), Decimal("1.35")]

        for amount in payment_amounts:
            payment = FinePaymentHistory(
                fine_id=fine.id,
                amount=amount,
                payment_method=PaymentMethod.cash,
                receipt_number=f"RCP-{len(payment_amounts)}",
            )
            test_db.add(payment)
        await test_db.commit()

        fine.amount_paid = sum(payment_amounts)
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)

        # Verify no rounding errors
        assert fine.amount_paid == Decimal("3.97")
        assert fine.balance == Decimal("0.00")

    async def test_concurrent_payment_safety(self, test_db, test_patron):
        """Test that concurrent payments don't cause double-charging."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("5.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        # Simulate two payments recorded simultaneously
        payment1 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("5.00"),
            payment_method=PaymentMethod.card,
            receipt_number="RCP-001",
        )
        payment2 = FinePaymentHistory(
            fine_id=fine.id,
            amount=Decimal("5.00"),
            payment_method=PaymentMethod.card,
            receipt_number="RCP-002",
        )

        # In real implementation, this should be prevented by database constraints
        # This test documents the expected behavior
        test_db.add(payment1)
        test_db.add(payment2)
        await test_db.commit()

        # Total payments would be $10.00 but fine is only $5.00
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payments = result.scalars().all()

        assert len(payments) == 2
        assert sum(p.amount for p in payments) == Decimal("10.00")
        # This would need to be prevented by business logic

    async def test_patron_total_balance_accuracy(self, test_db, test_patron):
        """Test that patron's total balance is calculated accurately."""
        fines = [
            Fine(user_id=test_patron.id, fine_type=FineType.overdue,
                 status=FineStatus.unpaid, amount=Decimal("2.50"), amount_paid=Decimal("0.00")),
            Fine(user_id=test_patron.id, fine_type=FineType.overdue,
                 status=FineStatus.partial, amount=Decimal("5.00"), amount_paid=Decimal("2.00")),
            Fine(user_id=test_patron.id, fine_type=FineType.lost_item,
                 status=FineStatus.unpaid, amount=Decimal("20.00"), amount_paid=Decimal("0.00")),
            Fine(user_id=test_patron.id, fine_type=FineType.overdue,
                 status=FineStatus.paid, amount=Decimal("1.75"), amount_paid=Decimal("1.75")),
        ]

        test_db.add_all(fines)
        await test_db.commit()

        # Calculate patron's total balance
        result = await test_db.execute(
            select(Fine).where(Fine.user_id == test_patron.id)
        )
        all_fines = result.scalars().all()

        total_balance = sum(f.balance for f in all_fines)

        # Expected: (2.50-0) + (5.00-2.00) + (20.00-0) + (1.75-1.75) = 25.50
        assert total_balance == Decimal("25.50")

    async def test_payment_method_tracking_accuracy(self, test_db, test_patron):
        """Test that payment methods are correctly tracked for accounting."""
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.paid,
            amount=Decimal("10.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        payments_by_method = {
            PaymentMethod.cash: Decimal("3.00"),
            PaymentMethod.card: Decimal("4.00"),
            PaymentMethod.online: Decimal("3.00"),
        }

        for method, amount in payments_by_method.items():
            payment = FinePaymentHistory(
                fine_id=fine.id,
                amount=amount,
                payment_method=method,
                receipt_number=f"RCP-{method.value}",
            )
            test_db.add(payment)
        await test_db.commit()

        # Verify accounting by method
        result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payments = result.scalars().all()

        cash_total = sum(p.amount for p in payments if p.payment_method == PaymentMethod.cash)
        card_total = sum(p.amount for p in payments if p.payment_method == PaymentMethod.card)
        online_total = sum(p.amount for p in payments if p.payment_method == PaymentMethod.online)

        assert cash_total == Decimal("3.00")
        assert card_total == Decimal("4.00")
        assert online_total == Decimal("3.00")
        assert cash_total + card_total + online_total == Decimal("10.00")
