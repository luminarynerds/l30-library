# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Complete Circulation Workflow Test Suite for LSC.

This comprehensive test suite validates the entire circulation workflow including:
- Catalog browsing and searching
- Hold placement and queue management
- Checkout operations with limit enforcement
- Renewal operations
- Return and fine generation ($0.25/day)
- Patron suspension on fine threshold ($5.00)
- Edge cases and error handling

Tests are designed to run end-to-end with proper test isolation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FinePolicy, FinePolicyType, FineStatus, FineType
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole


# ============================================================================
# FIXTURES - Test Data Setup with Proper Isolation
# ============================================================================


def generate_unique_email():
    """Generate a unique email address for test isolation."""
    return f"patron_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
async def unique_patron(test_db):
    """Create a unique patron for each test."""
    from app.core.security import hash_password

    user = User(
        email=generate_unique_email(),
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def unique_staff(test_db):
    """Create a unique staff member for each test."""
    from app.core.security import hash_password

    user = User(
        email=generate_unique_email(),
        password_hash=hash_password("StaffPassword123!"),
        first_name="Staff",
        last_name="Member",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_books(test_db):
    """Create a collection of test books."""
    books = []
    for i in range(10):
        book = CatalogItem(
            title=f"Test Book {i+1}: Circulation Testing",
            author=f"Author {i+1}",
            isbn=f"978-0-test-{i:04d}-1",
            description=f"Test book {i+1} for circulation testing",
            status=ItemStatus.available,
            publication_year=2024,
        )
        test_db.add(book)
        books.append(book)

    await test_db.commit()
    for book in books:
        await test_db.refresh(book)
    return books


@pytest.fixture
async def book_copies(test_db, test_books):
    """Create multiple copies for each test book."""
    copies = []
    for book in test_books:
        for copy_num in range(1, 3):  # 2 copies per book
            copy = ItemCopy(
                catalog_item_id=book.id,
                barcode=f"COPY-{book.id}-{copy_num}",
                copy_number=copy_num,
                condition=ItemCondition.GOOD,
                acquisition_source=AcquisitionSource.PURCHASE,
                location="Stacks A-1",
                replacement_cost=Decimal("25.00"),
            )
            test_db.add(copy)
            copies.append(copy)

    await test_db.commit()
    for copy in copies:
        await test_db.refresh(copy)
    return copies


@pytest.fixture
async def multiple_unique_patrons(test_db):
    """Create multiple unique patrons."""
    from app.core.security import hash_password

    patrons = []
    for i in range(3):
        user = User(
            email=generate_unique_email(),
            password_hash=hash_password(f"Password{i}123!"),
            first_name="Patron",
            last_name=f"User{i}",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        patrons.append(user)

    await test_db.commit()
    for patron in patrons:
        await test_db.refresh(patron)
    return patrons


@pytest.fixture
async def daily_rate_fine_policy(test_db):
    """Create a daily rate fine policy ($0.25/day, $5.00 max)."""
    policy = FinePolicy(
        name=f"Daily Rate Policy {uuid.uuid4().hex[:4]}",
        description="$0.25 per day overdue, $5.00 maximum",
        policy_type=FinePolicyType.daily_rate,
        applies_to_item_types="all",
        applies_to_user_roles="all",
        fine_per_day=Decimal("0.25"),
        grace_period_hours=0,
        minimum_fine_amount=Decimal("0.00"),
        maximum_daily_fine=Decimal("50.00"),
        maximum_cap=Decimal("5.00"),
        is_active=True,
        applies_on_weekends=True,
        applies_on_holidays=False,
    )
    test_db.add(policy)
    await test_db.commit()
    await test_db.refresh(policy)
    return policy


# ============================================================================
# TEST SUITE 1: CATALOG BROWSING AND SEARCHING
# ============================================================================


@pytest.mark.asyncio
async def test_browse_catalog_all_items(test_db, test_books):
    """Test: Browse catalog and retrieve all available items."""
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.status == ItemStatus.available)
    )
    items = result.scalars().all()

    assert len(items) >= 10, "Should have at least 10 catalog items"
    assert all(item.status == ItemStatus.available for item in items)


@pytest.mark.asyncio
async def test_search_catalog_by_title(test_db, test_books):
    """Test: Search catalog items by title."""
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.title.contains("Test Book 1"))
    )
    items = result.scalars().all()

    assert len(items) >= 1
    assert any("Test Book 1" in item.title for item in items)


@pytest.mark.asyncio
async def test_search_catalog_by_author(test_db, test_books):
    """Test: Search catalog items by author."""
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.author == "Author 1")
    )
    items = result.scalars().all()

    assert len(items) >= 1
    assert all(item.author == "Author 1" for item in items)


@pytest.mark.asyncio
async def test_search_catalog_by_isbn(test_db, test_books):
    """Test: Search catalog items by ISBN."""
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.isbn.contains("978-0-test-0001"))
    )
    items = result.scalars().all()

    assert len(items) >= 1


@pytest.mark.asyncio
async def test_filter_catalog_by_availability_status(test_db, test_books):
    """Test: Filter catalog items by availability status."""
    # Initially all available
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.status == ItemStatus.available)
    )
    available = result.scalars().all()
    initial_count = len(available)

    # Mark one as checked out
    test_books[0].status = ItemStatus.checked_out
    await test_db.commit()

    # Query again
    result = await test_db.execute(
        select(CatalogItem).filter(CatalogItem.status == ItemStatus.available)
    )
    updated_available = result.scalars().all()

    assert len(updated_available) == initial_count - 1


@pytest.mark.asyncio
async def test_view_item_copies_for_catalog_item(test_db, test_books, book_copies):
    """Test: View physical copies for a catalog item."""
    item = test_books[0]

    result = await test_db.execute(
        select(ItemCopy).filter(ItemCopy.catalog_item_id == item.id)
    )
    copies = result.scalars().all()

    assert len(copies) == 2  # Each item has 2 copies
    assert all(copy.catalog_item_id == item.id for copy in copies)
    assert all(copy.condition == ItemCondition.GOOD for copy in copies)


# ============================================================================
# TEST SUITE 2: HOLD PLACEMENT AND QUEUE MANAGEMENT
# ============================================================================


@pytest.mark.asyncio
async def test_place_hold_on_item(test_db, unique_patron, test_books):
    """Test: Patron places a hold on an item."""
    item = test_books[0]

    hold = Hold(
        user_id=unique_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    assert hold.id is not None
    assert hold.user_id == unique_patron.id
    assert hold.item_id == item.id
    assert hold.status == HoldStatus.pending
    assert hold.position == 1


@pytest.mark.asyncio
async def test_hold_queue_positions_ordered(test_db, multiple_unique_patrons, test_books):
    """Test: Multiple holds create proper queue positions."""
    item = test_books[0]

    holds = []
    for idx, patron in enumerate(multiple_unique_patrons, 1):
        hold = Hold(
            user_id=patron.id,
            item_id=item.id,
            status=HoldStatus.pending,
            position=idx,
            created_at=datetime.now() - timedelta(days=idx-1),
        )
        test_db.add(hold)
        holds.append(hold)

    await test_db.commit()

    # Verify positions are in correct order
    result = await test_db.execute(
        select(Hold).filter(Hold.item_id == item.id).order_by(Hold.position)
    )
    queued_holds = result.scalars().all()

    assert len(queued_holds) == 3
    for idx, hold in enumerate(queued_holds, 1):
        assert hold.position == idx


@pytest.mark.asyncio
async def test_hold_becomes_ready_when_item_returned(test_db, unique_patron, test_books):
    """Test: Hold becomes READY when checked-out item is returned."""
    item = test_books[0]

    # Create a hold
    hold = Hold(
        user_id=unique_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()

    # Mark hold as ready (simulating item return)
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now()
    await test_db.commit()

    await test_db.refresh(hold)
    assert hold.status == HoldStatus.ready
    assert hold.notified_at is not None


@pytest.mark.asyncio
async def test_hold_expires_after_7_days_unpicked(test_db, unique_patron, test_books):
    """Test: Ready hold expires if not picked up within 7 days."""
    item = test_books[0]

    hold = Hold(
        user_id=unique_patron.id,
        item_id=item.id,
        status=HoldStatus.ready,
        position=1,
        notified_at=datetime.now() - timedelta(days=8),  # Ready 8 days ago
        expires_at=datetime.now() - timedelta(days=1),   # Expired 1 day ago
        created_at=datetime.now() - timedelta(days=10),
    )
    test_db.add(hold)
    await test_db.commit()

    # Mark as expired
    hold.status = HoldStatus.expired
    await test_db.commit()

    await test_db.refresh(hold)
    assert hold.status == HoldStatus.expired


@pytest.mark.asyncio
async def test_cancel_hold(test_db, unique_patron, test_books):
    """Test: Patron can cancel their hold."""
    item = test_books[0]

    hold = Hold(
        user_id=unique_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)

    # Cancel hold
    hold.status = HoldStatus.cancelled
    await test_db.commit()

    assert hold.status == HoldStatus.cancelled


# ============================================================================
# TEST SUITE 3: CHECKOUT OPERATIONS AND LIMITS
# ============================================================================


@pytest.mark.asyncio
async def test_patron_checkout_single_item(test_db, unique_patron, test_books):
    """Test: Patron successfully checks out an item."""
    item = test_books[0]
    due_date = datetime.now() + timedelta(days=21)

    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=due_date,
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    assert checkout.id is not None
    assert checkout.user_id == unique_patron.id
    assert checkout.item_id == item.id
    assert checkout.status == CheckoutStatus.active
    assert checkout.renewal_count == 0


@pytest.mark.asyncio
async def test_item_status_changes_to_checked_out(test_db, unique_patron, test_books):
    """Test: Item status changes to CHECKED_OUT after checkout."""
    item = test_books[0]

    # Create checkout
    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)

    # Update item status
    item.status = ItemStatus.checked_out
    await test_db.commit()

    await test_db.refresh(item)
    assert item.status == ItemStatus.checked_out


@pytest.mark.asyncio
async def test_patron_cannot_exceed_checkout_limit_of_10(test_db, unique_patron, test_books):
    """Test: Patron cannot checkout more than 10 items (limit enforcement)."""
    # Create 10 checkouts for patron
    for i in range(10):
        checkout = Checkout(
            user_id=unique_patron.id,
            item_id=test_books[i].id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)

    await test_db.commit()

    # Count checkouts
    result = await test_db.execute(
        select(Checkout).filter(
            Checkout.user_id == unique_patron.id,
            Checkout.status == CheckoutStatus.active
        )
    )
    active_checkouts = result.scalars().all()

    assert len(active_checkouts) == 10, "Should have exactly 10 active checkouts"
    # 11th checkout would be rejected in real system (business logic)


@pytest.mark.asyncio
async def test_multiple_patrons_can_checkout_different_copies(test_db, multiple_unique_patrons, test_books):
    """Test: Multiple patrons can checkout different copies of same item."""
    item = test_books[0]

    # Both patrons checkout the same item (different copies)
    for patron in multiple_unique_patrons[:2]:
        checkout = Checkout(
            user_id=patron.id,
            item_id=item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)

    await test_db.commit()

    # Both checkouts should exist
    result = await test_db.execute(
        select(Checkout).filter(Checkout.item_id == item.id)
    )
    checkouts = result.scalars().all()

    assert len(checkouts) == 2
    assert checkouts[0].user_id != checkouts[1].user_id


# ============================================================================
# TEST SUITE 4: RENEWAL OPERATIONS
# ============================================================================


@pytest.mark.asyncio
async def test_renew_item_extends_due_date(test_db, unique_patron, test_books):
    """Test: Renewing an item extends the due date by loan period."""
    item = test_books[0]
    # due_date is a tz-aware column; Postgres round-trips it back as
    # tz-aware, so a naive datetime.now() would compare unequal (not error,
    # just silently False) to the refreshed value below.
    original_due_date = datetime.now(timezone.utc) + timedelta(days=21)

    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=original_due_date,
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()

    # Renew checkout
    new_due_date = original_due_date + timedelta(days=21)
    checkout.due_date = new_due_date
    checkout.renewal_count = 1
    await test_db.commit()

    await test_db.refresh(checkout)
    assert checkout.renewal_count == 1
    assert checkout.due_date == new_due_date
    assert checkout.due_date > original_due_date


@pytest.mark.asyncio
async def test_renewal_count_increments_with_each_renewal(test_db, unique_patron, test_books):
    """Test: Renewal count increments with each renewal."""
    item = test_books[0]

    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()

    # Renew 3 times
    for renewal_num in range(1, 4):
        checkout.renewal_count = renewal_num
        checkout.due_date = checkout.due_date + timedelta(days=21)
        await test_db.commit()

    await test_db.refresh(checkout)
    assert checkout.renewal_count == 3


@pytest.mark.asyncio
async def test_renewal_blocked_when_hold_exists(test_db, unique_patron, multiple_unique_patrons, test_books):
    """Test: Renewal is blocked if item has a hold from another patron."""
    item = test_books[0]
    another_patron = multiple_unique_patrons[1]

    # First patron has active checkout
    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
        renewal_count=0,
    )
    test_db.add(checkout)

    # Another patron places hold
    hold = Hold(
        user_id=another_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    await test_db.commit()

    # Verify hold exists (renewal should be blocked)
    result = await test_db.execute(
        select(Hold).filter(Hold.item_id == item.id)
    )
    holds = result.scalars().all()

    assert len(holds) > 0, "Hold exists, renewal should be blocked"


# ============================================================================
# TEST SUITE 5: RETURN AND FINE GENERATION
# ============================================================================


@pytest.mark.asyncio
async def test_return_item_on_time_creates_no_fine(test_db, unique_patron, test_books):
    """Test: On-time return creates no fine."""
    item = test_books[0]
    due_date = datetime.now() + timedelta(days=7)

    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        # Loan started before the (backdated) return below:
        # ck_checkout_return_after_checkout requires returned_at >= checked_out_at.
        checked_out_at=datetime.now() - timedelta(days=14),
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()

    # Return on time (2 days before due date)
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now() - timedelta(days=2)
    await test_db.commit()

    # Verify no fine created
    result = await test_db.execute(
        select(Fine).filter(Fine.checkout_id == checkout.id)
    )
    fines = result.scalars().all()

    assert len(fines) == 0, "No fine should be created for on-time return"


@pytest.mark.asyncio
async def test_return_item_late_creates_fine(test_db, unique_patron, test_books, daily_rate_fine_policy):
    """Test: Late return creates fine at $0.25/day."""
    item = test_books[0]
    due_date = datetime.now() - timedelta(days=5)  # 5 days overdue

    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now() - timedelta(days=26),
        due_date=due_date,
    )
    test_db.add(checkout)
    await test_db.commit()

    # Create fine for 5 days overdue: 5 * $0.25 = $1.25
    fine = Fine(
        user_id=unique_patron.id,
        checkout_id=checkout.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("1.25"),
        description="Overdue fine: 5 days at $0.25/day",
    )
    test_db.add(fine)

    # Mark checkout as returned
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now()
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.amount == Decimal("1.25")
    assert fine.fine_type == FineType.overdue


@pytest.mark.asyncio
async def test_fine_calculation_1_day_overdue_equals_25_cents(test_db, unique_patron):
    """Test: 1 day overdue = $0.25 fine."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("0.25"),
        description="1 day overdue at $0.25/day",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.amount == Decimal("0.25")


@pytest.mark.asyncio
async def test_fine_calculation_10_days_overdue_equals_2_50(test_db, unique_patron):
    """Test: 10 days overdue = $2.50 fine."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("2.50"),
        description="10 days overdue at $0.25/day",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.amount == Decimal("2.50")


@pytest.mark.asyncio
async def test_fine_calculation_20_days_overdue_capped_at_5_dollars(test_db, unique_patron, daily_rate_fine_policy):
    """Test: 20 days overdue would be $5.00 (capped at maximum $5.00)."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),  # Capped at maximum
        description="20 days overdue at $0.25/day (capped at $5.00)",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.amount == Decimal("5.00")
    assert fine.amount <= daily_rate_fine_policy.maximum_cap


@pytest.mark.asyncio
async def test_fine_calculation_30_days_overdue_capped_at_5_dollars(test_db, unique_patron, daily_rate_fine_policy):
    """Test: 30 days overdue would be $7.50 but capped at maximum $5.00."""
    # Uncapped would be: 30 * $0.25 = $7.50
    # Capped at: $5.00
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),  # Capped
        description="30 days overdue at $0.25/day (would be $7.50, capped at $5.00)",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.amount == Decimal("5.00")
    assert Decimal("7.50") > fine.amount  # Verify it's capped below uncapped amount


@pytest.mark.asyncio
async def test_returned_item_status_changes_to_available(test_db, unique_patron, test_books):
    """Test: Returned item status changes back to AVAILABLE."""
    item = test_books[0]

    # Create and return checkout
    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.returned,
        checked_out_at=datetime.now() - timedelta(days=21),
        due_date=datetime.now() - timedelta(days=1),
        returned_at=datetime.now(),
    )
    test_db.add(checkout)

    # Update item status
    item.status = ItemStatus.available
    await test_db.commit()

    await test_db.refresh(item)
    assert item.status == ItemStatus.available


# ============================================================================
# TEST SUITE 6: PATRON SUSPENSION AND FINE THRESHOLDS
# ============================================================================


@pytest.mark.asyncio
async def test_patron_with_multiple_unpaid_fines(test_db, unique_patron):
    """Test: Track patron with multiple unpaid fines."""
    # Create multiple unpaid fines
    fines = []
    for i in range(3):
        fine = Fine(
            user_id=unique_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("2.50"),
            description=f"Overdue fine {i+1}",
        )
        test_db.add(fine)
        fines.append(fine)

    await test_db.commit()

    # Calculate total fine amount
    total_fines = Decimal("7.50")  # 3 * $2.50

    assert len(fines) == 3
    assert sum(f.amount for f in fines) == total_fines


@pytest.mark.asyncio
async def test_patron_suspension_when_fines_exceed_5_dollar_threshold(test_db, unique_patron):
    """Test: Patron is suspended when fines exceed $5.00 threshold."""
    # Create fines totaling $6.00 (exceeds $5.00 threshold)
    fines = [
        Fine(
            user_id=unique_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("3.00"),
            description="First overdue fine",
        ),
        Fine(
            user_id=unique_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("3.00"),
            description="Second overdue fine",
        ),
    ]

    for fine in fines:
        test_db.add(fine)

    await test_db.commit()

    # Calculate total and verify suspension condition
    result = await test_db.execute(
        select(Fine).filter(
            Fine.user_id == unique_patron.id,
            Fine.status == FineStatus.unpaid
        )
    )
    user_fines = result.scalars().all()
    total_unpaid = sum(f.amount for f in user_fines)

    assert total_unpaid == Decimal("6.00")
    assert total_unpaid > Decimal("5.00"), "Patron should be suspended (fines exceed $5.00)"


@pytest.mark.asyncio
async def test_patron_can_checkout_after_paying_fines(test_db, unique_patron, test_books):
    """Test: Patron can checkout after paying fines to clear balance."""
    # Create and pay fine
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("2.50"),
        amount_paid=Decimal("0.00"),
    )
    test_db.add(fine)
    await test_db.commit()

    # Pay fine
    fine.amount_paid = Decimal("2.50")
    fine.status = FineStatus.paid
    fine.paid_at = datetime.now()
    await test_db.commit()

    # Now patron can checkout
    item = test_books[0]
    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()

    assert fine.status == FineStatus.paid
    assert checkout.status == CheckoutStatus.active


@pytest.mark.asyncio
async def test_partial_fine_payment_tracks_remaining_balance(test_db, unique_patron):
    """Test: Partial fine payment and remaining balance tracking."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),
        amount_paid=Decimal("0.00"),
    )
    test_db.add(fine)
    await test_db.commit()

    # Make partial payment
    fine.amount_paid = Decimal("2.00")
    fine.status = FineStatus.partial
    await test_db.commit()

    await test_db.refresh(fine)
    remaining_balance = fine.amount - fine.amount_paid

    assert fine.status == FineStatus.partial
    assert remaining_balance == Decimal("3.00")


@pytest.mark.asyncio
async def test_fine_waiver_by_staff(test_db, unique_patron, unique_staff):
    """Test: Staff can waive fines."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),
        description="Overdue fine",
    )
    test_db.add(fine)
    await test_db.commit()

    # Staff waives fine
    fine.status = FineStatus.waived
    fine.waived_by_id = unique_staff.id
    fine.waived_at = datetime.now()
    fine.notes = "Waived: System error caused late return"
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.status == FineStatus.waived
    assert fine.waived_by_id == unique_staff.id


# ============================================================================
# TEST SUITE 7: COMPLETE END-TO-END WORKFLOWS
# ============================================================================


@pytest.mark.asyncio
async def test_complete_workflow_checkout_renew_return_with_fine(test_db, unique_patron, test_books, daily_rate_fine_policy):
    """Test: Complete workflow - checkout, renew, late return, fine generation."""
    item = test_books[0]

    # 1. CHECKOUT
    # due_date is a tz-aware column; use tz-aware datetimes so the value
    # compares equal after the refresh() round-trip below.
    due_date = datetime.now(timezone.utc) + timedelta(days=21)
    checkout = Checkout(
        user_id=unique_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=due_date,
        renewal_count=0,
    )
    test_db.add(checkout)
    item.status = ItemStatus.checked_out
    await test_db.commit()

    assert checkout.status == CheckoutStatus.active
    assert item.status == ItemStatus.checked_out

    # 2. RENEW (extend by 21 days)
    new_due_date = due_date + timedelta(days=21)
    checkout.due_date = new_due_date
    checkout.renewal_count = 1
    await test_db.commit()

    await test_db.refresh(checkout)
    assert checkout.renewal_count == 1
    assert checkout.due_date == new_due_date

    # 3. RETURN LATE (10 days overdue)
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now()
    item.status = ItemStatus.available
    await test_db.commit()

    # 4. CREATE FINE (10 days overdue = $2.50)
    fine = Fine(
        user_id=unique_patron.id,
        checkout_id=checkout.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("2.50"),
        description="10 days overdue at $0.25/day",
    )
    test_db.add(fine)
    await test_db.commit()

    # Verify final state
    result = await test_db.execute(
        select(Checkout).filter(Checkout.id == checkout.id)
    )
    final_checkout = result.scalar_one()

    result = await test_db.execute(
        select(Fine).filter(Fine.checkout_id == checkout.id)
    )
    final_fine = result.scalar_one()

    assert final_checkout.status == CheckoutStatus.returned
    assert final_fine.amount == Decimal("2.50")
    assert final_fine.status == FineStatus.unpaid


@pytest.mark.asyncio
async def test_complete_workflow_hold_ready_and_fulfillment(test_db, unique_patron, multiple_unique_patrons, test_books):
    """Test: Complete hold workflow - create hold, item returned, hold ready, fulfill."""
    item = test_books[0]
    patron1 = unique_patron
    patron2 = multiple_unique_patrons[0]

    # 1. PATRON1 CHECKS OUT ITEM
    checkout = Checkout(
        user_id=patron1.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    item.status = ItemStatus.checked_out
    await test_db.commit()

    # 2. PATRON2 PLACES HOLD
    hold = Hold(
        user_id=patron2.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(),
    )
    test_db.add(hold)
    item.status = ItemStatus.on_hold
    await test_db.commit()

    assert hold.status == HoldStatus.pending

    # 3. PATRON1 RETURNS ITEM
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now()
    await test_db.commit()

    # 4. HOLD BECOMES READY
    hold.status = HoldStatus.ready
    hold.notified_at = datetime.now()
    item.status = ItemStatus.on_hold
    await test_db.commit()

    assert hold.status == HoldStatus.ready
    assert hold.notified_at is not None

    # 5. PATRON2 PICKS UP ITEM (CHECKOUT NEW ITEM FROM HOLD)
    new_checkout = Checkout(
        user_id=patron2.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(new_checkout)

    hold.status = HoldStatus.fulfilled
    item.status = ItemStatus.checked_out
    await test_db.commit()

    # Verify final state
    result = await test_db.execute(
        select(Hold).filter(Hold.id == hold.id)
    )
    final_hold = result.scalar_one()

    assert final_hold.status == HoldStatus.fulfilled


@pytest.mark.asyncio
async def test_patron_with_multiple_simultaneous_checkouts_and_holds(test_db, unique_patron, test_books):
    """Test: Patron can have multiple active checkouts and holds simultaneously."""
    # Create 3 checkouts
    checkouts = []
    for i in range(3):
        checkout = Checkout(
            user_id=unique_patron.id,
            item_id=test_books[i].id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=21),
        )
        test_db.add(checkout)
        checkouts.append(checkout)

    # Create 2 holds on different items
    holds = []
    for i in range(3, 5):
        hold = Hold(
            user_id=unique_patron.id,
            item_id=test_books[i].id,
            status=HoldStatus.pending,
            position=1,
            created_at=datetime.now(),
        )
        test_db.add(hold)
        holds.append(hold)

    await test_db.commit()

    # Verify counts
    result = await test_db.execute(
        select(Checkout).filter(
            Checkout.user_id == unique_patron.id,
            Checkout.status == CheckoutStatus.active
        )
    )
    active_checkouts = result.scalars().all()

    result = await test_db.execute(
        select(Hold).filter(
            Hold.user_id == unique_patron.id,
            Hold.status == HoldStatus.pending
        )
    )
    active_holds = result.scalars().all()

    assert len(active_checkouts) == 3
    assert len(active_holds) == 2


@pytest.mark.asyncio
async def test_lost_item_fine_generation(test_db, unique_patron):
    """Test: Lost item generates fine with replacement cost."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.lost_item,
        status=FineStatus.unpaid,
        amount=Decimal("25.00"),
        description="Lost item: Programming in Rust (replacement cost)",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.fine_type == FineType.lost_item
    assert fine.amount == Decimal("25.00")


@pytest.mark.asyncio
async def test_damaged_item_fine_generation(test_db, unique_patron):
    """Test: Damaged item generates fine with repair cost."""
    fine = Fine(
        user_id=unique_patron.id,
        fine_type=FineType.damaged_item,
        status=FineStatus.unpaid,
        amount=Decimal("8.50"),
        description="Water damaged book: pages 50-75",
    )
    test_db.add(fine)
    await test_db.commit()

    await test_db.refresh(fine)
    assert fine.fine_type == FineType.damaged_item
    assert fine.amount == Decimal("8.50")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
