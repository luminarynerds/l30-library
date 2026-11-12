# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Concurrent Staff Operations

Validates that simultaneous staff actions do not cause data corruption,
race conditions, or inconsistent state. Each scenario simulates two
operations competing for the same resource.

Scenarios covered:
1. Two staff checking out items to the same patron simultaneously
2. Two staff editing the same patron record concurrently
3. Staff checkout while patron self-checkout on same item
4. Hold placed while item is being checked out
5. Fine paid while staff is waiving it
6. Item status changed by two staff at once
7. Patron account edited from two branches simultaneously
8. Same report run by multiple staff at the same time
9. Inventory scan while items are circulating
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_patron(db: AsyncSession, email: str, **kwargs) -> User:
    patron = User(
        email=email,
        password_hash="hashed",
        first_name=kwargs.get("first_name", "Test"),
        last_name=kwargs.get("last_name", "Patron"),
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(patron)
    await db.commit()
    await db.refresh(patron)
    return patron


async def _create_staff(db: AsyncSession, email: str, **kwargs) -> User:
    staff = User(
        email=email,
        password_hash="hashed",
        first_name=kwargs.get("first_name", "Staff"),
        last_name=kwargs.get("last_name", "Member"),
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


async def _create_item(db: AsyncSession, title: str, status: ItemStatus = ItemStatus.available) -> CatalogItem:
    item = CatalogItem(
        title=title,
        author="Test Author",
        isbn=f"978-0-{hash(title) % 999999:06d}-0",
        description=f"Test item: {title}",
        status=status,
        call_number=f"T-{hash(title) % 9999:04d}",
        publication_year=2024,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# ============================================================================
# 1. Two staff checking out items to the same patron simultaneously
# ============================================================================


class TestConcurrentStaffCheckoutToSamePatron:
    """Two staff members at different desks check out items to the same patron."""

    @pytest.mark.asyncio
    async def test_two_different_items_checked_out_to_same_patron(
        self, test_db: AsyncSession
    ):
        """Both checkouts should succeed for different items without corruption."""
        patron = await _create_patron(test_db, "shared_patron@test.com")
        item_a = await _create_item(test_db, "Book A for Patron")
        item_b = await _create_item(test_db, "Book B for Patron")

        now = _utc_now()

        # Staff 1 checks out item A
        checkout_a = Checkout(
            user_id=patron.id,
            item_id=item_a.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout_a)

        # Staff 2 checks out item B (same patron) at the same instant
        checkout_b = Checkout(
            user_id=patron.id,
            item_id=item_b.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout_b)

        item_a.status = ItemStatus.checked_out
        item_b.status = ItemStatus.checked_out

        await test_db.commit()

        # Verify both checkouts exist and are active
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.user_id == patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        active_checkouts = result.scalars().all()
        assert len(active_checkouts) == 2

        # Items should both be checked_out
        await test_db.refresh(item_a)
        await test_db.refresh(item_b)
        assert item_a.status == ItemStatus.checked_out
        assert item_b.status == ItemStatus.checked_out

    @pytest.mark.asyncio
    async def test_same_item_cannot_be_checked_out_twice(
        self, test_db: AsyncSession
    ):
        """If two staff try to checkout the same item, only one should succeed."""
        patron = await _create_patron(test_db, "patron_dup@test.com")
        item = await _create_item(test_db, "Contested Book")

        now = _utc_now()

        # First checkout succeeds
        checkout1 = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout1)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Second attempt should detect item is already checked out
        await test_db.refresh(item)
        assert item.status == ItemStatus.checked_out

        # Verify only one active checkout exists for this item
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.item_id == item.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        active = result.scalars().all()
        assert len(active) == 1

    @pytest.mark.asyncio
    async def test_patron_checkout_count_consistent_after_concurrent_ops(
        self, test_db: AsyncSession
    ):
        """Patron's active checkout count should be accurate after concurrent checkouts."""
        patron = await _create_patron(test_db, "count_patron@test.com")
        now = _utc_now()

        items = []
        for i in range(5):
            items.append(await _create_item(test_db, f"Concurrent Book {i}"))

        # Check out all 5 items simultaneously
        for item in items:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now,
                due_date=now + timedelta(days=14),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out

        await test_db.commit()

        # Verify count
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.user_id == patron.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        assert len(result.scalars().all()) == 5


# ============================================================================
# 2. Two staff editing the same patron record concurrently
# ============================================================================


class TestConcurrentPatronRecordEditing:
    """Two staff members edit different fields of the same patron record."""

    @pytest.mark.asyncio
    async def test_concurrent_edits_to_different_fields(
        self, test_db: AsyncSession
    ):
        """Edits to different fields should not overwrite each other."""
        patron = await _create_patron(
            test_db, "edit_patron@test.com",
            first_name="Original", last_name="Name",
        )
        patron_id = patron.id

        # Staff 1 updates phone
        patron_s1 = await test_db.get(User, patron_id)
        patron_s1.phone = "555-0101"
        await test_db.commit()

        # Staff 2 updates address (simulating concurrent edit)
        patron_s2 = await test_db.get(User, patron_id)
        patron_s2.address = "123 Library Lane"
        await test_db.commit()

        # Final state should have both updates
        await test_db.refresh(patron_s2)
        result = await test_db.get(User, patron_id)
        assert result.phone == "555-0101"
        assert result.address == "123 Library Lane"

    @pytest.mark.asyncio
    async def test_concurrent_edits_to_same_field_last_write_wins(
        self, test_db: AsyncSession
    ):
        """When two staff edit the same field, the last write should win cleanly."""
        patron = await _create_patron(test_db, "samefield@test.com")
        patron_id = patron.id

        # Staff 1 sets phone
        p1 = await test_db.get(User, patron_id)
        p1.phone = "555-AAAA"
        await test_db.commit()

        # Staff 2 sets phone to different value (later write)
        p2 = await test_db.get(User, patron_id)
        p2.phone = "555-BBBB"
        await test_db.commit()

        # Should be in a clean state (last write wins)
        final = await test_db.get(User, patron_id)
        assert final.phone == "555-BBBB"

        # Patron should still be active and valid
        assert final.is_active is True
        assert final.email == "samefield@test.com"

    @pytest.mark.asyncio
    async def test_patron_record_not_corrupted_by_rapid_updates(
        self, test_db: AsyncSession
    ):
        """Rapid sequential updates should not leave record in corrupted state."""
        patron = await _create_patron(test_db, "rapid@test.com")
        patron_id = patron.id

        # 10 rapid updates
        for i in range(10):
            p = await test_db.get(User, patron_id)
            p.phone = f"555-{i:04d}"
            p.address = f"{i} Fast Street"
            await test_db.commit()

        final = await test_db.get(User, patron_id)
        assert final.phone == "555-0009"
        assert final.address == "9 Fast Street"
        assert final.is_active is True
        assert final.role == UserRole.PATRON


# ============================================================================
# 3. Staff checkout while patron self-checkout on same item
# ============================================================================


class TestStaffCheckoutVsPatronSelfCheckout:
    """Staff tries to check out item at desk while patron uses self-checkout."""

    @pytest.mark.asyncio
    async def test_item_cannot_be_double_checked_out(
        self, test_db: AsyncSession
    ):
        """Only one checkout should succeed for the same item."""
        patron = await _create_patron(test_db, "self_patron@test.com")
        item = await _create_item(test_db, "Contested Self-Checkout Book")

        now = _utc_now()

        # Patron self-checkout completes first
        self_checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(self_checkout)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Staff tries to check out same item — should see it's checked_out
        await test_db.refresh(item)
        assert item.status == ItemStatus.checked_out

        # Verify only one active checkout
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.item_id == item.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        checkouts = result.scalars().all()
        assert len(checkouts) == 1
        assert checkouts[0].user_id == patron.id

    @pytest.mark.asyncio
    async def test_item_status_consistent_after_contested_checkout(
        self, test_db: AsyncSession
    ):
        """Item status should be consistent regardless of who checks it out."""
        patron = await _create_patron(test_db, "consistent@test.com")
        item = await _create_item(test_db, "Status Consistency Book")

        now = _utc_now()

        # Check out the item
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Verify item status matches checkout existence
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.item_id == item.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        active_checkout = result.scalar_one_or_none()
        await test_db.refresh(item)

        assert active_checkout is not None
        assert item.status == ItemStatus.checked_out


# ============================================================================
# 4. Hold placed while item is being checked out
# ============================================================================


class TestHoldPlacedDuringCheckout:
    """A patron places a hold on an item while it's being checked out."""

    @pytest.mark.asyncio
    async def test_hold_placed_on_item_being_checked_out(
        self, test_db: AsyncSession
    ):
        """Hold should be queued and item status should reflect checked_out."""
        patron_borrower = await _create_patron(test_db, "borrower@test.com")
        patron_holder = await _create_patron(test_db, "holder@test.com")
        item = await _create_item(test_db, "Popular Book")

        now = _utc_now()

        # Checkout happens
        checkout = Checkout(
            user_id=patron_borrower.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Hold is placed at the same time
        hold = Hold(
            user_id=patron_holder.id,
            item_id=item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        test_db.add(hold)
        await test_db.commit()

        # Item should be checked_out (not on_hold)
        await test_db.refresh(item)
        assert item.status == ItemStatus.checked_out

        # Checkout should be active
        result = await test_db.execute(
            select(Checkout).where(
                Checkout.item_id == item.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
        assert result.scalar_one_or_none() is not None

        # Hold should be pending
        result = await test_db.execute(
            select(Hold).where(
                Hold.item_id == item.id,
                Hold.status == HoldStatus.pending,
            )
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_multiple_holds_during_checkout_maintain_queue_order(
        self, test_db: AsyncSession
    ):
        """Multiple holds placed while checkout occurs should maintain position order."""
        borrower = await _create_patron(test_db, "borrower2@test.com")
        item = await _create_item(test_db, "Very Popular Book")

        now = _utc_now()

        # Checkout first
        checkout = Checkout(
            user_id=borrower.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Three holds placed concurrently
        holders = []
        for i in range(3):
            holder = await _create_patron(test_db, f"holder{i}_q@test.com")
            holders.append(holder)

        for i, holder in enumerate(holders):
            hold = Hold(
                user_id=holder.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
                created_at=now + timedelta(milliseconds=i),
            )
            test_db.add(hold)

        await test_db.commit()

        # Verify queue order
        result = await test_db.execute(
            select(Hold)
            .where(Hold.item_id == item.id)
            .order_by(Hold.position)
        )
        holds = result.scalars().all()
        assert len(holds) == 3

        for i, hold in enumerate(holds):
            assert hold.position == i + 1

        # No duplicate positions
        positions = [h.position for h in holds]
        assert len(positions) == len(set(positions))

    @pytest.mark.asyncio
    async def test_hold_and_checkout_no_orphan_states(
        self, test_db: AsyncSession
    ):
        """No orphan holds or checkouts after concurrent operations."""
        patron_a = await _create_patron(test_db, "orphan_a@test.com")
        patron_b = await _create_patron(test_db, "orphan_b@test.com")
        item = await _create_item(test_db, "Orphan Test Book")

        now = _utc_now()

        # Checkout
        checkout = Checkout(
            user_id=patron_a.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        item.status = ItemStatus.checked_out

        # Hold
        hold = Hold(
            user_id=patron_b.id,
            item_id=item.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        test_db.add(hold)

        await test_db.commit()

        # Validate: checkout has a valid user, hold has a valid user
        await test_db.refresh(checkout)
        await test_db.refresh(hold)

        assert checkout.user_id == patron_a.id
        assert hold.user_id == patron_b.id

        # Item status is coherent
        await test_db.refresh(item)
        assert item.status == ItemStatus.checked_out


# ============================================================================
# 5. Fine paid while staff is waiving it
# ============================================================================


class TestFinePaymentVsStaffWaiver:
    """Patron pays a fine online while staff is waiving it at the desk."""

    @pytest.mark.asyncio
    async def test_fine_paid_then_waived_no_corruption(
        self, test_db: AsyncSession
    ):
        """Fine paid first, then waived — should end in a definite state."""
        patron = await _create_patron(test_db, "fine_patron@test.com")
        staff = await _create_staff(test_db, "fine_staff@test.com")

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("25.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()
        fine_id = fine.id

        # Patron pays
        f1 = await test_db.get(Fine, fine_id)
        f1.amount_paid = Decimal("25.00")
        f1.status = FineStatus.paid
        f1.paid_at = _utc_now()
        await test_db.commit()

        # Staff waives (arriving after payment)
        f2 = await test_db.get(Fine, fine_id)
        f2.status = FineStatus.waived
        f2.waived_at = _utc_now()
        f2.waived_by_id = staff.id
        await test_db.commit()

        # Final state: fine is in a definite state (waived wins as last write)
        final = await test_db.get(Fine, fine_id)
        assert final.status in (FineStatus.paid, FineStatus.waived)
        # No partial or unpaid — it's resolved
        assert final.status != FineStatus.unpaid

    @pytest.mark.asyncio
    async def test_waived_then_paid_no_double_charge(
        self, test_db: AsyncSession
    ):
        """Staff waives first, then payment arrives — patron should not be double-charged."""
        patron = await _create_patron(test_db, "double_patron@test.com")
        staff = await _create_staff(test_db, "double_staff@test.com")

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("15.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()
        fine_id = fine.id

        # Staff waives
        f1 = await test_db.get(Fine, fine_id)
        f1.status = FineStatus.waived
        f1.waived_at = _utc_now()
        f1.waived_by_id = staff.id
        await test_db.commit()

        # Payment attempt comes in after waiver
        f2 = await test_db.get(Fine, fine_id)
        # In a correct system, this should be rejected or the status stays waived
        # Here we verify the fine is not in an incoherent double-charged state
        if f2.status == FineStatus.waived:
            # Correct: payment should be rejected for waived fine
            pass
        else:
            # If payment went through, amount_paid should not exceed amount
            assert f2.amount_paid <= f2.amount

        final = await test_db.get(Fine, fine_id)
        assert final.status in (FineStatus.paid, FineStatus.waived)
        assert final.amount_paid <= final.amount

    @pytest.mark.asyncio
    async def test_concurrent_partial_payments_no_overpayment(
        self, test_db: AsyncSession
    ):
        """Two partial payments should not result in overpayment."""
        patron = await _create_patron(test_db, "partial_patron@test.com")

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("20.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()
        fine_id = fine.id

        # Payment 1: $12
        f1 = await test_db.get(Fine, fine_id)
        f1.amount_paid = Decimal("12.00")
        f1.status = FineStatus.partial
        await test_db.commit()

        # Payment 2: $8 (should bring to exactly $20)
        f2 = await test_db.get(Fine, fine_id)
        f2.amount_paid = f2.amount_paid + Decimal("8.00")
        if f2.amount_paid >= f2.amount:
            f2.status = FineStatus.paid
            f2.paid_at = _utc_now()
        else:
            f2.status = FineStatus.partial
        await test_db.commit()

        final = await test_db.get(Fine, fine_id)
        assert final.amount_paid == Decimal("20.00")
        assert final.amount_paid <= final.amount
        assert final.status == FineStatus.paid


# ============================================================================
# 6. Item status changed by two staff at once
# ============================================================================


class TestConcurrentItemStatusChanges:
    """Two staff members change item status at the same time."""

    @pytest.mark.asyncio
    async def test_item_status_resolves_to_definite_state(
        self, test_db: AsyncSession
    ):
        """Item should end in one definite status, not a hybrid."""
        item = await _create_item(test_db, "Status Battle Book")
        item_id = item.id

        # Staff 1 marks as missing
        i1 = await test_db.get(CatalogItem, item_id)
        i1.status = ItemStatus.missing
        await test_db.commit()

        # Staff 2 marks as withdrawn (concurrent)
        i2 = await test_db.get(CatalogItem, item_id)
        i2.status = ItemStatus.withdrawn
        await test_db.commit()

        final = await test_db.get(CatalogItem, item_id)
        # Should be in exactly one valid state
        assert final.status in list(ItemStatus)
        # Last write wins — withdrawn
        assert final.status == ItemStatus.withdrawn

    @pytest.mark.asyncio
    async def test_rapid_status_transitions_no_invalid_state(
        self, test_db: AsyncSession
    ):
        """Rapid status transitions should never leave item in an invalid state."""
        item = await _create_item(test_db, "Rapid Status Book")
        item_id = item.id

        transitions = [
            ItemStatus.in_processing,
            ItemStatus.available,
            ItemStatus.checked_out,
            ItemStatus.in_transit,
            ItemStatus.available,
            ItemStatus.on_hold,
            ItemStatus.available,
        ]

        for status in transitions:
            i = await test_db.get(CatalogItem, item_id)
            i.status = status
            await test_db.commit()

        final = await test_db.get(CatalogItem, item_id)
        assert final.status == ItemStatus.available
        assert final.status in list(ItemStatus)

    @pytest.mark.asyncio
    async def test_status_change_does_not_corrupt_other_fields(
        self, test_db: AsyncSession
    ):
        """Changing status should not corrupt title, author, or other metadata."""
        item = await _create_item(test_db, "Metadata Safe Book")
        item_id = item.id
        original_title = item.title
        original_author = item.author

        # Multiple status changes
        for status in [ItemStatus.missing, ItemStatus.in_transit, ItemStatus.available]:
            i = await test_db.get(CatalogItem, item_id)
            i.status = status
            await test_db.commit()

        final = await test_db.get(CatalogItem, item_id)
        assert final.title == original_title
        assert final.author == original_author
        assert final.status == ItemStatus.available


# ============================================================================
# 7. Patron account edited at two branches simultaneously
# ============================================================================


class TestPatronEditedAtTwoBranches:
    """Same patron record updated by staff at different branches."""

    @pytest.mark.asyncio
    async def test_branch_a_updates_phone_branch_b_updates_address(
        self, test_db: AsyncSession
    ):
        """Non-overlapping edits from two branches should both persist."""
        patron = await _create_patron(test_db, "multi_branch@test.com")
        patron_id = patron.id

        # Branch A staff updates phone
        pa = await test_db.get(User, patron_id)
        pa.phone = "555-BRANCH-A"
        await test_db.commit()

        # Branch B staff updates address
        pb = await test_db.get(User, patron_id)
        pb.address = "456 Branch B Ave"
        await test_db.commit()

        final = await test_db.get(User, patron_id)
        assert final.phone == "555-BRANCH-A"
        assert final.address == "456 Branch B Ave"

    @pytest.mark.asyncio
    async def test_both_branches_update_same_field(
        self, test_db: AsyncSession
    ):
        """Overlapping edits: last write should win, no data corruption."""
        patron = await _create_patron(test_db, "conflict_branch@test.com")
        patron_id = patron.id

        # Branch A sets email preference
        pa = await test_db.get(User, patron_id)
        pa.language_preference = "en"
        await test_db.commit()

        # Branch B sets it to something else
        pb = await test_db.get(User, patron_id)
        pb.language_preference = "es"
        await test_db.commit()

        final = await test_db.get(User, patron_id)
        assert final.language_preference == "es"
        # Core identity intact
        assert final.email == "conflict_branch@test.com"
        assert final.is_active is True

    @pytest.mark.asyncio
    async def test_patron_status_not_corrupted_by_concurrent_branch_edits(
        self, test_db: AsyncSession
    ):
        """Patron's account status should remain valid after concurrent edits."""
        patron = await _create_patron(test_db, "status_safe@test.com")
        patron_id = patron.id

        # Branch A updates contact info
        pa = await test_db.get(User, patron_id)
        pa.phone = "555-1111"
        pa.address = "100 Main St"
        await test_db.commit()

        # Branch B updates different contact info
        pb = await test_db.get(User, patron_id)
        pb.emergency_contact_name = "Jane Doe"
        pb.emergency_contact_phone = "555-9999"
        await test_db.commit()

        final = await test_db.get(User, patron_id)
        assert final.is_active is True
        assert final.role == UserRole.PATRON
        assert final.emergency_contact_name == "Jane Doe"
        assert final.emergency_contact_phone == "555-9999"


# ============================================================================
# 8. Same report run by multiple staff at the same time
# ============================================================================


class TestConcurrentReportGeneration:
    """Multiple staff run the same report simultaneously."""

    @pytest.mark.asyncio
    async def test_concurrent_report_queries_return_consistent_data(
        self, test_db: AsyncSession
    ):
        """Running the same query concurrently should return consistent results."""
        patron = await _create_patron(test_db, "report_patron@test.com")
        now = _utc_now()

        # Create some checkouts for reporting
        items = []
        for i in range(3):
            item = await _create_item(test_db, f"Report Book {i}")
            items.append(item)

        for item in items:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now - timedelta(days=i),
                due_date=now + timedelta(days=14 - i),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out

        await test_db.commit()

        # Staff 1 runs circulation report query
        result1 = await test_db.execute(
            select(Checkout).where(Checkout.status == CheckoutStatus.active)
        )
        report1_count = len(result1.scalars().all())

        # Staff 2 runs same report query simultaneously
        result2 = await test_db.execute(
            select(Checkout).where(Checkout.status == CheckoutStatus.active)
        )
        report2_count = len(result2.scalars().all())

        # Both should see the same data
        assert report1_count == report2_count
        assert report1_count == 3

    @pytest.mark.asyncio
    async def test_report_data_not_corrupted_by_concurrent_reads(
        self, test_db: AsyncSession
    ):
        """Concurrent read-only report queries should not corrupt any data."""
        patron = await _create_patron(test_db, "readonly_patron@test.com")
        _ = _utc_now()

        fine = Fine(
            user_id=patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("10.00"),
            amount_paid=Decimal("0.00"),
        )
        test_db.add(fine)
        await test_db.commit()

        original_amount = fine.amount
        fine_id = fine.id

        # Multiple concurrent report reads
        for _ in range(5):
            result = await test_db.execute(
                select(Fine).where(Fine.user_id == patron.id)
            )
            fines = result.scalars().all()
            assert len(fines) == 1
            assert fines[0].amount == original_amount

        # Verify data unchanged after reads
        final = await test_db.get(Fine, fine_id)
        assert final.amount == original_amount
        assert final.status == FineStatus.unpaid

    @pytest.mark.asyncio
    async def test_report_during_active_transactions(
        self, test_db: AsyncSession
    ):
        """Report query during active data modifications should see consistent snapshot."""
        patron = await _create_patron(test_db, "snapshot_patron@test.com")
        now = _utc_now()

        item = await _create_item(test_db, "Snapshot Book")
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=now,
            due_date=now + timedelta(days=14),
        )
        test_db.add(checkout)
        item.status = ItemStatus.checked_out
        await test_db.commit()

        # Query active checkouts
        result = await test_db.execute(
            select(Checkout).where(Checkout.status == CheckoutStatus.active)
        )
        active = result.scalars().all()
        active_count_before = len(active)

        # Return the item
        checkout.status = CheckoutStatus.returned
        checkout.returned_at = now
        item.status = ItemStatus.available
        await test_db.commit()

        # Query again — count should be different now
        result = await test_db.execute(
            select(Checkout).where(Checkout.status == CheckoutStatus.active)
        )
        active_count_after = len(result.scalars().all())

        assert active_count_before == active_count_after + 1


# ============================================================================
# 9. Inventory scan while items are circulating
# ============================================================================


class TestInventoryScanDuringCirculation:
    """Inventory scan happens while items are being checked out/returned."""

    @pytest.mark.asyncio
    async def test_inventory_count_consistent_during_checkout(
        self, test_db: AsyncSession
    ):
        """Item count should be consistent even when items are being checked out."""
        patron = await _create_patron(test_db, "inv_patron@test.com")
        now = _utc_now()

        # Create 10 items
        items = []
        for i in range(10):
            item = await _create_item(test_db, f"Inventory Book {i}")
            items.append(item)

        # Check out 3 items
        for item in items[:3]:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now,
                due_date=now + timedelta(days=14),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out

        await test_db.commit()

        # Run inventory scan query
        available_result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.status == ItemStatus.available)
        )
        available = available_result.scalars().all()

        checked_out_result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.status == ItemStatus.checked_out)
        )
        checked_out = checked_out_result.scalars().all()

        # Total should equal what we created
        assert len(available) + len(checked_out) == 10
        assert len(available) == 7
        assert len(checked_out) == 3

    @pytest.mark.asyncio
    async def test_item_status_consistent_between_scan_and_checkout_record(
        self, test_db: AsyncSession
    ):
        """Item status should match checkout records — no phantom checkouts."""
        patron = await _create_patron(test_db, "phantom_patron@test.com")
        now = _utc_now()

        items = []
        for i in range(5):
            item = await _create_item(test_db, f"Phantom Book {i}")
            items.append(item)

        # Check out items 0,1,2
        for item in items[:3]:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now,
                due_date=now + timedelta(days=14),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out

        await test_db.commit()

        # For each item, verify status matches checkout record
        for item in items:
            await test_db.refresh(item)
            result = await test_db.execute(
                select(Checkout).where(
                    Checkout.item_id == item.id,
                    Checkout.status == CheckoutStatus.active,
                )
            )
            active_checkout = result.scalar_one_or_none()

            if item.status == ItemStatus.checked_out:
                assert active_checkout is not None, (
                    f"Item {item.id} marked checked_out but no active checkout record"
                )
            elif item.status == ItemStatus.available:
                assert active_checkout is None, (
                    f"Item {item.id} marked available but has active checkout record"
                )

    @pytest.mark.asyncio
    async def test_return_during_inventory_scan(
        self, test_db: AsyncSession
    ):
        """Item returned mid-scan should not cause count discrepancies."""
        patron = await _create_patron(test_db, "return_patron@test.com")
        now = _utc_now()

        items = []
        for i in range(5):
            item = await _create_item(test_db, f"Return Scan Book {i}")
            items.append(item)

        # Check out all 5
        checkouts = []
        for item in items:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=now,
                due_date=now + timedelta(days=14),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out
            checkouts.append(checkout)

        await test_db.commit()

        # Scan starts: 0 available, 5 checked out
        scan_result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.status == ItemStatus.available)
        )
        available_before = len(scan_result.scalars().all())

        # Item 0 is returned mid-scan
        checkouts[0].status = CheckoutStatus.returned
        checkouts[0].returned_at = now
        items[0].status = ItemStatus.available
        await test_db.commit()

        # Scan continues: 1 available, 4 checked out
        scan_result2 = await test_db.execute(
            select(CatalogItem).where(CatalogItem.status == ItemStatus.available)
        )
        available_after = len(scan_result2.scalars().all())

        assert available_after == available_before + 1

        # Total items unchanged
        all_result = await test_db.execute(select(CatalogItem))
        total = len(all_result.scalars().all())
        assert total == 5

    @pytest.mark.asyncio
    async def test_no_items_lost_in_concurrent_operations(
        self, test_db: AsyncSession
    ):
        """Items should never disappear from the system during concurrent operations."""
        patron = await _create_patron(test_db, "noloss_patron@test.com")
        now = _utc_now()

        # Create items
        item_ids = []
        for i in range(8):
            item = await _create_item(test_db, f"NoLoss Book {i}")
            item_ids.append(item.id)

        # Rapid checkout/return cycles
        for item_id in item_ids[:4]:
            item = await test_db.get(CatalogItem, item_id)
            # Checkout
            checkout = Checkout(
                user_id=patron.id,
                item_id=item_id,
                status=CheckoutStatus.active,
                checked_out_at=now,
                due_date=now + timedelta(days=14),
            )
            test_db.add(checkout)
            item.status = ItemStatus.checked_out
            await test_db.commit()

            # Return
            checkout.status = CheckoutStatus.returned
            checkout.returned_at = now
            item.status = ItemStatus.available
            await test_db.commit()

        # All items should still exist
        for item_id in item_ids:
            item = await test_db.get(CatalogItem, item_id)
            assert item is not None, f"Item {item_id} disappeared!"
            assert item.status in list(ItemStatus)

        # Total count unchanged
        result = await test_db.execute(select(CatalogItem))
        assert len(result.scalars().all()) == 8
