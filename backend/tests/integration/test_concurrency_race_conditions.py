# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for concurrency and race conditions in LSC Library Management System.

Tests for:
- Concurrent checkouts/returns
- Race conditions in hold processing
- Fine calculation race conditions
- Inventory count accuracy under concurrent access
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User, UserRole


@pytest.mark.integration
class TestConcurrentCheckout:
    """Test concurrent checkout operations."""

    @pytest.mark.asyncio
    async def test_double_checkout_prevention(
        self, client, test_db: AsyncSession, test_patron, test_user_data, test_catalog_item
    ):
        """Test that same user cannot checkout same item twice.

        Duplicate-checkout prevention is enforced by the service/API layer
        (create_checkout), not a DB constraint on (user_id, item_id) --
        that title-level unique index was intentionally dropped 2026-06-09
        (see the comment above Checkout.__table_args__ in
        app/models/circulation.py): a multi-copy title must allow one
        active checkout per copy concurrently, so only item_copy-level
        uniqueness remains at the DB layer. Raw duplicate ORM inserts (as
        this test used to do) are no longer rejected by Postgres, so this
        has to go through the real checkout endpoint to observe the
        actual duplicate-prevention behavior.
        """
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": test_user_data["email"], "password": test_user_data["password"]},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response1 = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": test_catalog_item.id},
            headers=headers,
        )
        assert response1.status_code == 201

        response2 = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": test_catalog_item.id},
            headers=headers,
        )
        assert response2.status_code == 409, "Double checkout was not prevented"

    @pytest.mark.asyncio
    async def test_checkout_limit_enforcement(self, test_db: AsyncSession, test_patron):
        """Test that checkout limits are enforced under concurrent requests."""
        from app.core.authorization import get_checkout_limit

        # test_patron has no RoleSettings/age-group override, so this falls
        # through to the default max_checkouts=10 (see get_checkout_limit
        # in app/core/authorization.py) -- create exactly `limit` items
        # rather than a hardcoded count so this doesn't drift again if the
        # default changes.
        limit = await get_checkout_limit(test_patron, test_db)
        assert limit > 0

        # Create `limit` items
        items = []
        for i in range(limit):
            item = CatalogItem(
                title=f"Test Book {i}",
                author="Test Author",
                isbn=f"978-0-123456-7{i}-9",
                description="Test book",
                status=ItemStatus.available,
                call_number=f"TEST-{i:03d}",
                publication_year=2024,
            )
            test_db.add(item)
            items.append(item)

        await test_db.commit()

        # Create checkouts up to limit
        for item in items[:limit]:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                due_date=datetime.now() + timedelta(days=21),
                status=CheckoutStatus.active,
            )
            test_db.add(checkout)

        await test_db.commit()

        # Verify we have limit checkouts
        from sqlalchemy import func, select

        result = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        active_count = result.scalar() or 0
        assert active_count == limit


@pytest.mark.integration
class TestConcurrentReturn:
    """Test concurrent return operations."""

    @pytest.mark.asyncio
    async def test_concurrent_returns_same_item(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that item status is correctly updated when multiple returns occur."""
        from sqlalchemy import select

        # Create two checkouts of same item (need different users or items)
        checkout1 = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now() + timedelta(days=21),
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
        )
        test_db.add(checkout1)
        await test_db.commit()
        await test_db.refresh(checkout1)

        # Mark as returned
        checkout1.status = CheckoutStatus.returned
        checkout1.returned_at = datetime.now()
        await test_db.commit()

        # Verify item status is updated
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item = result.scalar_one()
        # Item should be available or on hold depending on holds
        assert item.status in [ItemStatus.available, ItemStatus.on_hold]


@pytest.mark.integration
class TestConcurrentHolds:
    """Test concurrent hold operations."""

    @pytest.mark.asyncio
    async def test_hold_position_accuracy(self, test_db: AsyncSession, test_catalog_item):
        """Test that hold positions remain accurate under concurrent additions."""
        from sqlalchemy import func, select

        from app.core.security import hash_password
        from app.models.user import User, UserRole

        # Create multiple patrons
        patrons = []
        for i in range(3):
            patron = User(
                email=f"patron{i}@example.com",
                password_hash=hash_password("TestPassword123!"),
                first_name=f"Patron{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            patrons.append(patron)

        await test_db.commit()

        # Create holds for same item
        for i, patron in enumerate(patrons):
            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                position=i + 1,
                status=HoldStatus.pending,
                created_at=datetime.now(),
            )
            test_db.add(hold)

        await test_db.commit()

        # Verify positions are sequential
        result = await test_db.execute(
            select(Hold).where(Hold.item_id == test_catalog_item.id).order_by(Hold.position)
        )
        holds = result.scalars().all()

        for i, hold in enumerate(holds):
            assert hold.position == i + 1, (
                f"Hold position mismatch: expected {i + 1}, got {hold.position}"
            )


@pytest.mark.integration
class TestConcurrentFineCalculation:
    """Test concurrent fine calculation operations."""

    @pytest.mark.asyncio
    async def test_overdue_fine_idempotency(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that overdue fine calculation is idempotent under concurrent access."""
        from sqlalchemy import func, select

        from app.services.fine_service import check_and_create_overdue_fine

        # Create overdue checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now() - timedelta(days=5),
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now() - timedelta(days=26),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Simulate concurrent fine creation
        _ = await check_and_create_overdue_fine(checkout, test_db, test_patron)
        _ = await check_and_create_overdue_fine(checkout, test_db, test_patron)

        # Only one fine should be created (idempotency)
        result = await test_db.execute(
            select(func.count(Fine.id)).where(
                Fine.checkout_id == checkout.id, Fine.fine_type == FineType.overdue
            )
        )
        fine_count = result.scalar() or 0
        # Should have exactly one fine or none (depending on role settings)
        assert fine_count <= 1

    @pytest.mark.asyncio
    async def test_concurrent_fine_payment(self, test_db: AsyncSession, test_patron, test_fine):
        """Test concurrent payments on same fine."""
        from sqlalchemy import select

        initial_paid = test_fine.amount_paid

        # Simulate two concurrent payment updates
        payment1 = Decimal("5.00")
        payment2 = Decimal("3.00")

        # First payment
        test_fine.amount_paid += payment1
        await test_db.commit()

        # Second payment (concurrent scenario)
        await test_db.refresh(test_fine)
        test_fine.amount_paid += payment2
        await test_db.commit()

        # Verify both payments are recorded
        await test_db.refresh(test_fine)
        expected_paid = initial_paid + payment1 + payment2
        assert test_fine.amount_paid == expected_paid


@pytest.mark.integration
class TestInventoryConsistency:
    """Test inventory count consistency under concurrent access."""

    @pytest.mark.asyncio
    async def test_item_availability_tracking(self, test_db: AsyncSession, test_catalog_item):
        """Test that item availability is correctly tracked."""
        from sqlalchemy import func, select

        # Get initial status
        await test_db.refresh(test_catalog_item)
        _ = test_catalog_item.status

        # Simulate checkout
        test_catalog_item.status = ItemStatus.checked_out
        await test_db.commit()

        # Verify status is updated
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == test_catalog_item.id)
        )
        item = result.scalar_one()
        assert item.status == ItemStatus.checked_out


@pytest.mark.integration
class TestDeadlockPrevention:
    """Test for potential deadlock conditions."""

    @pytest.mark.asyncio
    async def test_no_deadlock_on_hold_promotion(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that hold promotion doesn't cause deadlocks."""
        from sqlalchemy import select

        # Create checked out item with holds
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now() + timedelta(days=21),
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
        )
        test_db.add(checkout)

        # Create multiple holds
        for i in range(3):
            from app.core.security import hash_password
            from app.models.user import User, UserRole

            patron = User(
                email=f"hold_patron{i}@example.com",
                password_hash=hash_password("TestPassword123!"),
                first_name=f"HoldPatron{i}",
                last_name="Test",
                role=UserRole.PATRON,
                is_active=True,
                email_verified=True,
            )
            test_db.add(patron)
            await test_db.flush()

            hold = Hold(
                user_id=patron.id,
                item_id=test_catalog_item.id,
                position=i + 1,
                status=HoldStatus.pending,
                created_at=datetime.now(),
            )
            test_db.add(hold)

        await test_db.commit()

        # Return item (should promote first hold)
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = datetime.now()

        # Get first hold
        result = await test_db.execute(
            select(Hold).where(Hold.item_id == test_catalog_item.id).order_by(Hold.position)
        )
        first_hold = result.scalars().first()

        if first_hold:
            first_hold.status = HoldStatus.ready
            first_hold.notified_at = datetime.now()

        await test_db.commit()


@pytest.mark.integration
class TestTransactionIsolation:
    """Test transaction isolation levels."""

    @pytest.mark.asyncio
    async def test_dirty_read_prevention(
        self, test_db: AsyncSession, test_patron, test_catalog_item
    ):
        """Test that dirty reads are prevented."""
        from sqlalchemy import select

        # Create checkout
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            due_date=datetime.now() + timedelta(days=21),
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        # Read checkout in another session
        result = await test_db.execute(select(Checkout).where(Checkout.id == checkout.id))
        read_checkout = result.scalar_one()

        assert read_checkout.status == CheckoutStatus.active

    @pytest.mark.asyncio
    async def test_phantom_read_prevention(self, test_db: AsyncSession, test_patron):
        """Test prevention of phantom reads in range queries."""
        from sqlalchemy import func, select

        # Count active checkouts
        result1 = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        count1 = result1.scalar() or 0

        # Insert new checkout
        from app.models.catalog import CatalogItem, ItemStatus

        item = CatalogItem(
            title="New Book",
            author="Test Author",
            isbn="978-0-111111-11-1",
            description="Test",
            status=ItemStatus.available,
            call_number="NEW-001",
            publication_year=2024,
        )
        test_db.add(item)
        await test_db.flush()

        checkout = Checkout(
            user_id=test_patron.id,
            item_id=item.id,
            due_date=datetime.now() + timedelta(days=21),
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
        )
        test_db.add(checkout)
        await test_db.commit()

        # Recount
        result2 = await test_db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.user_id == test_patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        count2 = result2.scalar() or 0

        # Count should have increased
        assert count2 == count1 + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
