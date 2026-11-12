# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for the partial payment endpoint.

Tests the complete workflow for making partial payments on fines:
1. Make a partial payment on a fine
2. Verify the remaining balance is correct
3. Verify FinePaymentHistory records the payment
4. Make multiple partial payments until the fine is fully paid
5. Verify the fine status changes to PAID
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select

from app.models.fine import Fine, FineStatus, FineType, FinePaymentHistory, PaymentMethod


def _money(value) -> Decimal:
    """MoneyDecimal fields serialize as JSON floats (see
    app/schemas/_base.py: PlainSerializer(float, when_used="json")), not
    strings -- go through str() to avoid binary-float comparison surprises."""
    return Decimal(str(value))


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def test_fine_12_dollars(test_db, test_patron):
    """Create a $12.00 fine for testing."""
    fine = Fine(
        user_id=test_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("12.00"),
        amount_paid=Decimal("0.00"),
        description="Test fine for partial payment testing",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


async def get_auth_headers(client, email: str, password: str) -> dict:
    """Get authentication headers for a user."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestPartialPaymentEndpoint:
    """Test the /staff/fines/{fine_id}/partial-payment endpoint."""

    async def test_make_partial_payment_5_dollars(
        self, client, test_db, test_staff, test_staff_data, test_fine_12_dollars
    ):
        """
        Test 1: Make a $5.00 partial payment on a $12.00 fine.

        Expected:
        - Response status 200
        - Fine balance should be $7.00
        - FinePaymentHistory should record the $5.00 payment
        - Fine status should be 'partial'
        """
        # Get staff authentication
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Make partial payment of $5.00
        response = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
                "notes": "First partial payment",
            },
            headers=headers,
        )

        # Verify response
        assert response.status_code == 200, f"Unexpected status: {response.text}"
        data = response.json()

        # Verify fine in response
        assert data["fine"]["id"] == test_fine_12_dollars.id
        assert _money(data["fine"]["amount"]) == Decimal("12.00")
        assert _money(data["fine"]["amount_paid"]) == Decimal("5.00")
        assert _money(data["fine"]["balance"]) == Decimal("7.00")
        assert data["fine"]["status"] == "partial"

        # Verify payment record in response
        assert _money(data["payment"]["amount"]) == Decimal("5.00")
        assert data["payment"]["payment_method"] == "cash"
        assert data["receipt_number"] is not None

        # Verify in database
        await test_db.refresh(test_fine_12_dollars)
        assert test_fine_12_dollars.amount_paid == Decimal("5.00")
        assert test_fine_12_dollars.balance == Decimal("7.00")
        assert test_fine_12_dollars.status == FineStatus.partial

        # Verify payment history record
        payment_history = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == test_fine_12_dollars.id)
        )
        payments = payment_history.scalars().all()
        assert len(payments) == 1
        assert payments[0].amount == Decimal("5.00")
        assert payments[0].payment_method == PaymentMethod.cash
        assert payments[0].receipt_number == data["receipt_number"]

    async def test_make_second_partial_payment_7_dollars(
        self, client, test_db, test_staff, test_staff_data, test_fine_12_dollars
    ):
        """
        Test 2-5: Make multiple partial payments ($5.00, then $7.00) to pay off a $12.00 fine.

        Expected:
        - After first payment: balance = $7.00, status = 'partial'
        - After second payment: balance = $0.00, status = 'paid'
        - FinePaymentHistory should have 2 records
        - Fine should be marked as paid
        """
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # First partial payment of $5.00
        response1 = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
                "notes": "First partial payment",
            },
            headers=headers,
        )
        assert response1.status_code == 200
        data1 = response1.json()
        receipt1 = data1["receipt_number"]

        # Verify first payment
        await test_db.refresh(test_fine_12_dollars)
        assert test_fine_12_dollars.amount_paid == Decimal("5.00")
        assert test_fine_12_dollars.balance == Decimal("7.00")
        assert test_fine_12_dollars.status == FineStatus.partial

        # Second partial payment of $7.00 (remaining balance)
        response2 = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 7.00,
                "payment_method": "card",
                "notes": "Final payment to complete the fine",
            },
            headers=headers,
        )
        assert response2.status_code == 200
        data2 = response2.json()
        receipt2 = data2["receipt_number"]

        # Verify second payment response
        assert _money(data2["fine"]["amount_paid"]) == Decimal("12.00")
        assert _money(data2["fine"]["balance"]) == Decimal("0.00")
        assert data2["fine"]["status"] == "paid"
        assert data2["fine"]["paid_at"] is not None
        assert _money(data2["payment"]["amount"]) == Decimal("7.00")
        assert data2["payment"]["payment_method"] == "card"

        # Verify in database
        await test_db.refresh(test_fine_12_dollars)
        assert test_fine_12_dollars.amount_paid == Decimal("12.00")
        assert test_fine_12_dollars.balance == Decimal("0.00")
        assert test_fine_12_dollars.status == FineStatus.paid
        assert test_fine_12_dollars.paid_at is not None

        # Verify both payments in payment history
        payment_history = await test_db.execute(
            select(FinePaymentHistory).where(FinePaymentHistory.fine_id == test_fine_12_dollars.id)
        )
        payments = payment_history.scalars().all()
        assert len(payments) == 2

        # First payment
        assert payments[0].amount == Decimal("5.00")
        assert payments[0].payment_method == PaymentMethod.cash
        assert payments[0].receipt_number == receipt1

        # Second payment
        assert payments[1].amount == Decimal("7.00")
        assert payments[1].payment_method == PaymentMethod.card
        assert payments[1].receipt_number == receipt2

    async def test_payment_exceeding_balance_rejected(
        self, client, test_staff, test_staff_data, test_fine_12_dollars
    ):
        """Test that a payment exceeding the remaining balance is rejected."""
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Try to pay more than the balance
        response = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 15.00,
                "payment_method": "cash",
            },
            headers=headers,
        )

        assert response.status_code == 400
        assert "exceeds remaining balance" in _error_detail(response)

    async def test_payment_on_already_paid_fine_rejected(
        self, client, test_db, test_staff, test_staff_data, test_fine_12_dollars
    ):
        """Test that a payment on an already-paid fine is rejected."""
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Mark fine as paid
        test_fine_12_dollars.status = FineStatus.paid
        test_fine_12_dollars.amount_paid = Decimal("12.00")
        await test_db.commit()

        # Try to make another payment
        response = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
            },
            headers=headers,
        )

        assert response.status_code == 400
        assert "already paid in full" in _error_detail(response)

    async def test_payment_on_waived_fine_rejected(
        self, client, test_db, test_staff, test_staff_data, test_fine_12_dollars
    ):
        """Test that a payment on a waived fine is rejected."""
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Mark fine as waived
        test_fine_12_dollars.status = FineStatus.waived
        await test_db.commit()

        # Try to make a payment
        response = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
            },
            headers=headers,
        )

        assert response.status_code == 400
        assert "waived" in _error_detail(response)

    async def test_payment_on_nonexistent_fine_returns_404(
        self, client, test_staff, test_staff_data
    ):
        """Test that payment on a nonexistent fine returns 404."""
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        response = await client.post(
            "/api/v1/staff/fines/99999/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
            },
            headers=headers,
        )

        assert response.status_code == 404

    async def test_payment_requires_staff_role(
        self, client, test_patron, test_user_data, test_fine_12_dollars
    ):
        """Test that payment endpoint requires staff role."""
        headers = await get_auth_headers(
            client, test_user_data["email"], test_user_data["password"]
        )

        response = await client.post(
            f"/api/v1/staff/fines/{test_fine_12_dollars.id}/partial-payment",
            json={
                "amount": 5.00,
                "payment_method": "cash",
            },
            headers=headers,
        )

        assert response.status_code == 403 or response.status_code == 401

    async def test_multiple_payment_methods(
        self, client, test_db, test_staff, test_staff_data, test_patron
    ):
        """Test that different payment methods are correctly recorded."""
        headers = await get_auth_headers(
            client, test_staff_data["email"], test_staff_data["password"]
        )

        # Create multiple fines
        payment_methods_to_test = [
            ("cash", PaymentMethod.cash),
            ("card", PaymentMethod.card),
            ("check", PaymentMethod.check),
            ("online", PaymentMethod.online),
        ]

        for method_str, method_enum in payment_methods_to_test:
            # Create a fine
            fine = Fine(
                user_id=test_patron.id,
                fine_type=FineType.overdue,
                status=FineStatus.unpaid,
                amount=Decimal("10.00"),
                amount_paid=Decimal("0.00"),
                description=f"Test fine for {method_str} payment",
            )
            test_db.add(fine)
            await test_db.commit()
            await test_db.refresh(fine)

            # Make payment
            response = await client.post(
                f"/api/v1/staff/fines/{fine.id}/partial-payment",
                json={
                    "amount": 5.00,
                    "payment_method": method_str,
                    "notes": f"Payment via {method_str}",
                },
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["payment"]["payment_method"] == method_str

            # Verify in database
            payment_history = await test_db.execute(
                select(FinePaymentHistory).where(FinePaymentHistory.fine_id == fine.id)
            )
            payment = payment_history.scalars().first()
            assert payment.payment_method == method_enum
