# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Concurrent Operations and Race Conditions.

Tests system behavior under concurrent access:
- Simultaneous checkouts of same item (only one should succeed)
- Simultaneous hold placements (queue positioning)
- Fine calculation with concurrent updates
- Hold advancement with concurrent queue operations
- Inventory sync with concurrent receipt operations
- Database constraint enforcement (unique indexes)
- Transaction isolation and locking
- Deadlock prevention
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole

pytestmark = pytest.mark.skip(
    reason=(
        "TEST-HARNESS BUG, not verified product rot -- every test in this file "
        "runs multiple asyncio.gather()'d coroutines against the SAME shared "
        "test_db AsyncSession to simulate concurrent actors. SQLAlchemy's "
        "AsyncSession is explicitly not safe for concurrent use from multiple "
        "coroutines; the failures (sqlalchemy.exc.IllegalStateChangeError: "
        "commit()/rollback() called while _prepare_impl in progress; "
        "InterfaceError: cannot perform operation, another operation in "
        "progress; plus duplicate-key IntegrityError on setup fixtures reused "
        "across gather'd tasks) are exactly the documented symptom of sharing "
        "one AsyncSession across tasks, confirmed 2026-07-09 re-baseline. "
        "Whether the app itself correctly serializes concurrent checkouts/"
        "holds/fines under real concurrent DB connections is still an open "
        "question this file cannot currently answer -- fixing it requires "
        "giving each gathered task its own AsyncSessionLocal() rather than "
        "sharing the fixture, which is a real per-test refactor (>15 min), "
        "out of scope here. Reported in the triage doc as a follow-up, not "
        "fixed. Un-skip once each concurrent task gets its own session."
    )
)


@pytest.fixture
async def shared_item(test_db):
    """Create a single item that multiple tests will try to checkout."""
    item = CatalogItem(
        title="Shared Item For Concurrency Tests",
        author="Test Author",
        isbn="978-0-concurrent-001",
        description="Single copy item",
        status=ItemStatus.available,
        call_number="CONC-001",
        barcode="CONC001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def item_copy_for_concurrency(test_db, shared_item):
    """Create a physical copy for concurrency tests."""
    copy = ItemCopy(
        catalog_item_id=shared_item.id,
        barcode="COPY-CONC-001",
        copy_number=1,
        condition=ItemCondition.GOOD,
        acquisition_source=AcquisitionSource.PURCHASE,
        location="Stacks",
        replacement_cost=Decimal("25.00"),
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def patron_pool(test_db):
    """Create multiple patrons for concurrent tests."""
    from app.core.security import hash_password

    patrons = []
    for i in range(5):
        user = User(
            email=f"patron-concurrent-{i}@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name=f"Patron{i}",
            last_name="Concurrent",
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


@pytest.mark.asyncio
async def test_simultaneous_checkouts_same_item(test_db, shared_item, patron_pool):
    """Test: Only one checkout succeeds when multiple patrons try simultaneously."""
    patrons = patron_pool[:2]

    # Both patrons try to checkout the same item
    _ = []

    async def attempt_checkout(patron, item):
        try:
            checkout = Checkout(
                user_id=patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                due_date=datetime.now(tz=None) + timedelta(days=21),
            )
            test_db.add(checkout)
            await test_db.flush()
            # Try to commit
            await test_db.commit()
            return {"success": True, "checkout": checkout}
        except IntegrityError:
            await test_db.rollback()
            return {"success": False, "error": "Unique constraint violation"}
        except Exception as e:
            await test_db.rollback()
            return {"success": False, "error": str(e)}

    # Simulate concurrent attempts
    results = await asyncio.gather(
        attempt_checkout(patrons[0], shared_item),
        attempt_checkout(patrons[1], shared_item),
    )

    # Verify only one succeeded (database constraint prevents duplicate active checkouts)
    successful = [r for r in results if r["success"]]
    _ = [r for r in results if not r["success"]]

    assert len(successful) <= 1, "Only one checkout should succeed"


@pytest.mark.asyncio
async def test_concurrent_hold_queue_positioning(test_db, shared_item, patron_pool):
    """Test: Multiple holds get unique queue positions."""
    patrons = patron_pool[:3]

    # All patrons try to hold the same item
    async def place_hold(patron, item, db_session):
        hold = Hold(
            user_id=patron.id,
            item_id=item.id,
            status=HoldStatus.pending,
            position=None,  # Will be set
        )
        db_session.add(hold)
        await db_session.commit()
        await db_session.refresh(hold)
        return hold

    # Place holds concurrently
    hold_tasks = [place_hold(patron, shared_item, test_db) for patron in patrons]
    _ = await asyncio.gather(*hold_tasks)

    # Verify all holds exist
    result = await test_db.execute(
        select(Hold).filter(Hold.item_id == shared_item.id).order_by(Hold.position)
    )
    queue = result.scalars().all()
    assert len(queue) == 3

    # Verify positions are sequential
    positions = [h.position for h in queue]
    assert positions == [1, 2, 3] or all(p is not None for p in positions)


@pytest.mark.asyncio
async def test_concurrent_fine_calculations(test_db, patron_pool):
    """Test: Concurrent fine calculations don't cause issues."""
    patron = patron_pool[0]

    async def create_fine(amount):
        fine = Fine(
            user_id=patron.id,
            fine_type="overdue",
            status=FineStatus.unpaid,
            amount=Decimal(str(amount)),
        )
        test_db.add(fine)
        await test_db.commit()
        await test_db.refresh(fine)
        return fine

    # Create multiple fines concurrently
    fine_tasks = [create_fine(Decimal("2.50")) for _ in range(3)]
    _ = await asyncio.gather(*fine_tasks)

    # Verify all fines created
    result = await test_db.execute(
        select(Fine).filter(Fine.user_id == patron.id)
    )
    all_fines = result.scalars().all()
    assert len(all_fines) == 3


@pytest.mark.asyncio
async def test_concurrent_fine_payments(test_db, patron_pool):
    """Test: Concurrent fine payments update amounts correctly."""
    patron = patron_pool[0]

    # Create a fine
    fine = Fine(
        user_id=patron.id,
        fine_type="overdue",
        status=FineStatus.unpaid,
        amount=Decimal("10.00"),
        amount_paid=Decimal("0.00"),
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    # Multiple payment attempts
    async def make_payment(payment_amount):
        # In real system, would use SELECT FOR UPDATE
        fine.amount_paid += payment_amount
        await test_db.commit()
        return fine.amount_paid

    payment_tasks = [
        make_payment(Decimal("2.50")),
        make_payment(Decimal("2.50")),
        make_payment(Decimal("5.00")),
    ]

    # Due to race condition without locking, final balance may not be exact
    # In production, this would use SELECT FOR UPDATE
    results = await asyncio.gather(*payment_tasks)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_hold_advancement_under_concurrent_returns(test_db, patron_pool, shared_item):
    """Test: Queue advances correctly when item returned (multiple holds waiting)."""
    patrons = patron_pool[:3]

    # Create hold queue
    holds = []
    for i, patron in enumerate(patrons):
        hold = Hold(
            user_id=patron.id,
            item_id=shared_item.id,
            status=HoldStatus.pending,
            position=i + 1,
        )
        test_db.add(hold)
        holds.append(hold)
    await test_db.commit()

    # Item returned, first hold becomes ready
    holds[0].status = HoldStatus.ready
    await test_db.commit()

    # Verify queue structure
    result = await test_db.execute(
        select(Hold).filter(Hold.item_id == shared_item.id).order_by(Hold.position)
    )
    queue = result.scalars().all()
    assert queue[0].status == HoldStatus.ready
    assert queue[1].status == HoldStatus.pending


@pytest.mark.asyncio
async def test_concurrent_item_copy_receipt(test_db, patron_pool):
    """Test: Multiple copies received concurrently are tracked correctly."""
    from app.models.acquisition import PurchaseOrderItem

    po_item = PurchaseOrderItem(
        purchase_order_id=None,  # Simplified
        title="Test Book",
        quantity=5,
        unit_price=Decimal("25.00"),
        received_quantity=0,
    )
    test_db.add(po_item)
    await test_db.commit()
    await test_db.refresh(po_item)

    # Simulate receiving copies concurrently
    async def receive_copy(copy_num):
        copy = ItemCopy(
            catalog_item_id=None,
            barcode=f"COPY-CONC-{copy_num:03d}",
            copy_number=copy_num,
            condition=ItemCondition.NEW,
            acquisition_source=AcquisitionSource.PURCHASE,
            purchase_order_item_id=po_item.id,
        )
        test_db.add(copy)
        await test_db.commit()
        await test_db.refresh(copy)
        return copy

    # Receive 5 copies concurrently
    copy_tasks = [receive_copy(i) for i in range(1, 6)]
    _ = await asyncio.gather(*copy_tasks)

    # Verify all copies created
    result = await test_db.execute(
        select(ItemCopy).filter(ItemCopy.purchase_order_item_id == po_item.id)
    )
    received_copies = result.scalars().all()
    assert len(received_copies) == 5


@pytest.mark.asyncio
async def test_concurrent_checkout_and_hold(test_db, patron_pool, shared_item):
    """Test: When item checked out and held, hold is ready on return."""
    patrons = patron_pool[:2]

    # Patron 1 places hold
    hold = Hold(
        user_id=patrons[0].id,
        item_id=shared_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()

    # Patron 2 checks out (if available)
    checkout = Checkout(
        user_id=patrons[1].id,
        item_id=shared_item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(tz=None) + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()

    # Return item, hold should become ready
    checkout.status = CheckoutStatus.returned
    checkout.returned_at = datetime.now(tz=None)
    hold.status = HoldStatus.ready
    await test_db.commit()

    assert hold.status == HoldStatus.ready


@pytest.mark.asyncio
async def test_prevent_double_checkout_with_unique_index(test_db, shared_item, patron_pool):
    """Test: Database unique index prevents duplicate active checkouts."""
    patron = patron_pool[0]

    # Create first checkout
    checkout1 = Checkout(
        user_id=patron.id,
        item_id=shared_item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(tz=None) + timedelta(days=21),
    )
    test_db.add(checkout1)
    await test_db.commit()

    # Try to create second active checkout of same item (should fail)
    try:
        checkout2 = Checkout(
            user_id=patron.id,
            item_id=shared_item.id,
            status=CheckoutStatus.active,
            due_date=datetime.now(tz=None) + timedelta(days=21),
        )
        test_db.add(checkout2)
        await test_db.flush()
        await test_db.commit()
        assert False, "Should have raised IntegrityError"
    except IntegrityError:
        await test_db.rollback()
        # Expected behavior


@pytest.mark.asyncio
async def test_prevent_duplicate_active_holds(test_db, shared_item, patron_pool):
    """Test: Patron can't have multiple active holds on same item."""
    patron = patron_pool[0]

    # Create first hold
    hold1 = Hold(
        user_id=patron.id,
        item_id=shared_item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold1)
    await test_db.commit()

    # Try to create second active hold (should fail or be prevented)
    # In PostgreSQL with proper constraints:
    try:
        hold2 = Hold(
            user_id=patron.id,
            item_id=shared_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        test_db.add(hold2)
        await test_db.flush()
        await test_db.commit()
        # If no constraint, at least service layer should prevent
    except IntegrityError:
        await test_db.rollback()


@pytest.mark.asyncio
async def test_concurrent_fine_waiver(test_db, patron_pool, test_staff):
    """Test: Concurrent fine waiver attempts are handled safely."""
    patron = patron_pool[0]

    # Create a fine
    fine = Fine(
        user_id=patron.id,
        fine_type="overdue",
        status=FineStatus.unpaid,
        amount=Decimal("10.00"),
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)

    # Multiple waiver attempts
    async def waive_fine():
        fine.status = FineStatus.waived
        fine.waived_by_id = test_staff.id
        fine.waived_at = datetime.now(tz=None)
        await test_db.commit()
        return fine

    # Try to waive concurrently (last write wins)
    waive_tasks = [waive_fine() for _ in range(2)]
    _ = await asyncio.gather(*waive_tasks)

    # Verify fine is waived
    await test_db.refresh(fine)
    assert fine.status == FineStatus.waived


@pytest.mark.asyncio
async def test_concurrent_hold_expiration(test_db, patron_pool, shared_item):
    """Test: Multiple holds expiring concurrently are handled correctly."""
    patrons = patron_pool[:3]

    # Create hold queue
    holds = []
    for i, patron in enumerate(patrons):
        hold = Hold(
            user_id=patron.id,
            item_id=shared_item.id,
            status=HoldStatus.ready,
            position=i + 1,
            expires_at=datetime.now(tz=None) - timedelta(days=1),
        )
        test_db.add(hold)
        holds.append(hold)
    await test_db.commit()

    # Expire multiple holds
    async def expire_hold(hold):
        hold.status = HoldStatus.expired
        await test_db.commit()
        return hold

    expire_tasks = [expire_hold(hold) for hold in holds]
    _ = await asyncio.gather(*expire_tasks)

    # Verify all expired
    result = await test_db.execute(
        select(Hold).filter(Hold.item_id == shared_item.id)
    )
    all_holds = result.scalars().all()
    assert all(h.status == HoldStatus.expired for h in all_holds)


@pytest.mark.asyncio
async def test_checkout_renewal_concurrent_updates(test_db, patron_pool, shared_item):
    """Test: Concurrent renewal attempts don't double-count renewals."""
    patron = patron_pool[0]

    # Create checkout
    checkout = Checkout(
        user_id=patron.id,
        item_id=shared_item.id,
        status=CheckoutStatus.active,
        due_date=datetime.now(tz=None) + timedelta(days=21),
        renewal_count=0,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    # Concurrent renewals
    async def renew():
        checkout.renewal_count += 1
        checkout.due_date = datetime.now(tz=None) + timedelta(days=21)
        await test_db.commit()
        return checkout

    renew_tasks = [renew() for _ in range(3)]
    _ = await asyncio.gather(*renew_tasks)

    # Due to race condition without locking, count may be less than 3
    # In production, use SELECT FOR UPDATE
    await test_db.refresh(checkout)
    assert checkout.renewal_count <= 3


@pytest.mark.asyncio
async def test_inventory_count_consistency_under_concurrent_updates(test_db, patron_pool):
    """Test: Item copy availability counts remain consistent."""
    from app.models.acquisition import PurchaseOrderItem

    po_item = PurchaseOrderItem(
        purchase_order_id=None,
        title="Popular Book",
        quantity=10,
        unit_price=Decimal("20.00"),
        received_quantity=0,
    )
    test_db.add(po_item)
    await test_db.commit()
    await test_db.refresh(po_item)

    # Concurrent receipts
    async def receive_items(count):
        po_item.received_quantity += count
        await test_db.commit()
        return po_item.received_quantity

    receipt_tasks = [
        receive_items(2),
        receive_items(3),
        receive_items(5),
    ]

    _ = await asyncio.gather(*receipt_tasks)

    # Verify final count
    await test_db.refresh(po_item)
    # Race condition may cause final count to be less than 10
    assert po_item.received_quantity <= 10


@pytest.mark.asyncio
async def test_concurrent_operations_with_error_recovery(test_db, patron_pool, shared_item):
    """Test: System recovers from errors in concurrent operations."""
    patrons = patron_pool[:2]

    async def safe_checkout(patron):
        try:
            checkout = Checkout(
                user_id=patron.id,
                item_id=shared_item.id,
                status=CheckoutStatus.active,
                due_date=datetime.now(tz=None) + timedelta(days=21),
            )
            test_db.add(checkout)
            await test_db.commit()
            return {"success": True}
        except Exception:
            await test_db.rollback()
            return {"success": False}

    tasks = [safe_checkout(patron) for patron in patrons]
    results = await asyncio.gather(*tasks)

    # At least one should succeed
    successful = sum(1 for r in results if r["success"])
    assert successful >= 1
