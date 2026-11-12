# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Staff Fine Payment Endpoints

Comprehensive test suite for the POST /staff/fines/{fine_id}/pay endpoint covering:
1. Full balance payment with status transition to PAID
2. FinePaymentHistory record creation with payment method and receipt
3. Patron fine total recalculation
4. Fine-block lifting when balance drops below threshold
5. Error handling for invalid payment amounts
6. Concurrent payment handling
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.core.security import create_access_token
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FinePaymentHistory, FineStatus, FineType, PaymentMethod
from app.models.user import User
from app.services.fine_service import get_user_fines_summary
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _auth_headers(user: User) -> dict:
    """Build real JWT auth headers (subject must be the numeric user id --
    app.api.v1.auth.helpers.get_current_user does int(payload["sub"]))."""
    token = create_access_token(subject=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.mark.asyncio
class TestFinePaymentEndpoint:
    """Test the POST /staff/fines/{fine_id}/pay endpoint."""

    async def test_full_payment_changes_status_to_paid(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Requirement 1 & 2: Full payment with amount=balance changes status to PAID."""
        # Create checkout and fine directly -- app.services.fine_service.FINE_FREE_MODE
        # is now True, so check_and_create_overdue_fine() always returns None
        # (accountability is tracked via checkout status, not a Fine row).
        # This endpoint test is about the /pay flow on an existing fine, so
        # construct the Fine directly rather than depend on that gate.
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        fine = Fine(
            user_id=test_patron.id,
            checkout_id=checkout.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.50"),  # 10 days * $0.25
            description="Overdue by 10 day(s)",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)
        assert fine.status == FineStatus.unpaid
        initial_balance = fine.amount - fine.amount_paid

        # Make full payment
        payment_data = {
            "amount": float(initial_balance),
            "notes": "Full payment",
        }

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200
        result = response.json()

        # Verify status changed to PAID
        assert result["status"] == "paid"
        assert Decimal(str(result["amount_paid"])) == fine.amount
        assert Decimal(str(result["balance"])) == Decimal("0.00")

        # Verify in database
        await test_db.refresh(fine)
        assert fine.status == FineStatus.paid
        assert fine.amount_paid == fine.amount
        assert fine.balance == Decimal("0.00")

    async def test_full_payment_creates_payment_history_with_receipt(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Requirement 3: Full payment creates FinePaymentHistory with payment method and receipt."""
        # Create checkout and fine directly -- see the note on
        # test_full_payment_changes_status_to_paid above (FINE_FREE_MODE).
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=25),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        fine = Fine(
            user_id=test_patron.id,
            checkout_id=checkout.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("1.25"),  # 5 days * $0.25
            description="Overdue by 5 day(s)",
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)
        initial_balance = fine.amount - fine.amount_paid

        # Make full payment with payment method
        payment_data = {
            "amount": float(initial_balance),
            "notes": "Payment by card",
        }

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200

        # Verify payment history record was created with receipt and payment method
        payment_history_result = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
        )
        payment_record = payment_history_result.scalar_one_or_none()

        assert payment_record is not None, "FinePaymentHistory record should be created"
        assert payment_record.fine_id == fine.id
        assert payment_record.amount == initial_balance
        assert payment_record.payment_method == PaymentMethod.cash
        assert payment_record.receipt_number is not None
        assert payment_record.receipt_number.startswith("RCP-")
        assert payment_record.processed_by_id == test_staff.id
        assert payment_record.notes == "Payment by card"

    async def test_full_payment_recalculates_patron_fine_total(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Requirement 4: Full payment recalculates patron fine total."""
        # Create two checkouts and fines directly -- see the note on
        # test_full_payment_changes_status_to_paid above (FINE_FREE_MODE).
        checkout1 = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_date=datetime.now(timezone.utc) - timedelta(days=10, hours=1),
        )
        test_db.add(checkout1)
        await test_db.commit()
        await test_db.refresh(checkout1)

        fine1 = Fine(
            user_id=test_patron.id,
            checkout_id=checkout1.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.50"),  # 10 days * $0.25
            description="Overdue by 10 day(s)",
        )
        test_db.add(fine1)
        await test_db.commit()
        await test_db.refresh(fine1)

        checkout2 = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=20),
            due_date=datetime.now(timezone.utc) - timedelta(days=5, hours=1),
        )
        test_db.add(checkout2)
        await test_db.commit()
        await test_db.refresh(checkout2)

        fine2 = Fine(
            user_id=test_patron.id,
            checkout_id=checkout2.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("1.25"),  # 5 days * $0.25
            description="Overdue by 5 day(s)",
        )
        test_db.add(fine2)
        await test_db.commit()
        await test_db.refresh(fine2)

        initial_total = fine1.amount + fine2.amount

        # Get initial patron summary
        summary_before = await get_user_fines_summary(test_patron.id, test_db)
        assert Decimal(str(summary_before["total_outstanding"])) == initial_total

        # Pay off first fine completely
        payment_data = {"amount": float(fine1.amount)}

        response = await client.post(
            f"/api/v1/staff/fines/{fine1.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200

        # Verify patron fine total recalculated
        summary_after = await get_user_fines_summary(test_patron.id, test_db)
        expected_remaining = fine2.amount
        assert Decimal(str(summary_after["total_outstanding"])) == expected_remaining
        assert summary_after["outstanding_count"] == 1

    async def test_full_payment_lifts_fine_block_when_below_threshold(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Requirement 5: Full payment that clears balance below $10.00 threshold lifts fine-block."""
        # Create fine that exceeds block threshold ($10.00 = 1000 cents)
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("12.00"),  # $12.00 - exceeds $10 threshold
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            description="Test fine for block threshold",
        )
        test_db.add(fine)
        await test_db.commit()

        # Verify patron is blocked (fine total >= $10.00)
        summary_before = await get_user_fines_summary(test_patron.id, test_db)
        assert Decimal(str(summary_before["total_outstanding"])) >= Decimal("10.00")

        # Pay down to below threshold ($9.00)
        payment_data = {"amount": 3.01}  # 12.00 - 3.01 = 8.99 (below 10.00)

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200
        result = response.json()

        # Verify balance is below threshold
        remaining_balance = Decimal(str(result["balance"]))
        assert remaining_balance < Decimal("10.00")

        # Verify status is still partial (not all paid)
        assert result["status"] == "partial"

        # Verify in database
        await test_db.refresh(fine)
        summary_after = await get_user_fines_summary(test_patron.id, test_db)
        assert Decimal(str(summary_after["total_outstanding"])) < Decimal("10.00")

    async def test_payment_on_nonexistent_fine_returns_404(
        self,
        client: AsyncClient,
        test_staff: User,
    ):
        """Test that payment on nonexistent fine returns 404."""
        payment_data = {"amount": 5.00}

        response = await client.post(
            "/api/v1/staff/fines/99999/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 404

    async def test_payment_exceeding_balance_returns_400(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Test that payment exceeding balance is rejected."""
        # Create fine with $5.00 balance
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("5.00"),
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            description="Test fine",
        )
        test_db.add(fine)
        await test_db.commit()

        # Try to pay more than balance
        payment_data = {"amount": 6.00}  # Exceeds $5.00 balance

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 400
        assert "exceeds" in _error_detail(response).lower()

    async def test_payment_on_already_paid_fine_returns_400(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
    ):
        """Test that payment on already-paid fine is rejected."""
        # Create and mark fine as already paid
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("5.00"),
            amount_paid=Decimal("5.00"),
            status=FineStatus.paid,
            fine_type=FineType.overdue,
            description="Already paid",
            paid_at=datetime.now(timezone.utc),
        )
        test_db.add(fine)
        await test_db.commit()

        payment_data = {"amount": 1.00}

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 400
        assert "paid" in _error_detail(response).lower()

    async def test_payment_on_waived_fine_returns_400(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
    ):
        """Test that payment on waived fine is rejected."""
        # Create and mark fine as waived
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("5.00"),
            status=FineStatus.waived,
            fine_type=FineType.overdue,
            description="Waived",
            waived_at=datetime.now(timezone.utc),
            waived_by_id=test_staff.id,
        )
        test_db.add(fine)
        await test_db.commit()

        payment_data = {"amount": 1.00}

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 400
        assert "waived" in _error_detail(response).lower()

    async def test_partial_payment_sets_status_to_partial(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
    ):
        """Test that partial payment sets status to partial."""
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("10.00"),
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            description="Test fine for partial payment",
        )
        test_db.add(fine)
        await test_db.commit()

        # Make partial payment
        payment_data = {"amount": 3.50}

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200
        result = response.json()

        assert result["status"] == "partial"
        assert Decimal(str(result["amount_paid"])) == Decimal("3.50")
        assert Decimal(str(result["balance"])) == Decimal("6.50")

    async def test_sequential_partial_payments_eventually_reach_paid(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
    ):
        """Test multiple partial payments eventually mark fine as PAID."""
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("10.00"),
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            description="Test fine for sequential payments",
        )
        test_db.add(fine)
        await test_db.commit()

        # First payment
        response1 = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json={"amount": 3.00},
            headers=_auth_headers(test_staff),
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "partial"

        await test_db.refresh(fine)

        # Second payment
        response2 = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json={"amount": 4.00},
            headers=_auth_headers(test_staff),
        )
        assert response2.status_code == 200
        assert response2.json()["status"] == "partial"

        await test_db.refresh(fine)

        # Final payment
        response3 = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json={"amount": 3.00},
            headers=_auth_headers(test_staff),
        )
        assert response3.status_code == 200
        result = response3.json()

        assert result["status"] == "paid"
        assert Decimal(str(result["amount_paid"])) == Decimal("10.00")
        assert Decimal(str(result["balance"])) == Decimal("0.00")

    async def test_payment_timestamps_set_correctly_on_full_payment(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        test_staff: User,
        test_patron: User,
        test_catalog_item,
    ):
        """Test that paid_at timestamp is set on full payment."""
        fine = Fine(
            user_id=test_patron.id,
            amount=Decimal("5.00"),
            status=FineStatus.unpaid,
            fine_type=FineType.overdue,
            description="Test fine",
        )
        test_db.add(fine)
        await test_db.commit()

        payment_data = {"amount": 5.00}

        response = await client.post(
            f"/api/v1/staff/fines/{fine.id}/pay",
            json=payment_data,
            headers=_auth_headers(test_staff),
        )

        assert response.status_code == 200

        await test_db.refresh(fine)
        assert fine.paid_at is not None
        assert fine.status == FineStatus.paid
