# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for concurrent checkout protection.

Validates that the distributed lock (Redis) and partial unique index
(ix_active_item_copy_checkout) prevent two concurrent checkouts of the
same physical item copy from both succeeding.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.inventory import ItemCopy, AcquisitionSource, ItemCondition
from app.models.user import User, UserRole


@pytest.fixture
async def catalog_item(test_db):
    """Create a single catalog item for concurrent checkout tests."""
    item = CatalogItem(
        title="Concurrent Checkout Test Item",
        author="Test Author",
        isbn="9780000012349",  # isbn column is varchar(20); must fit
        description="Single copy item for concurrency testing",
        status=ItemStatus.available,
        call_number="CC-001",
        barcode="CC001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def item_copy(test_db, catalog_item):
    """Create a single physical copy for the catalog item."""
    copy = ItemCopy(
        catalog_item_id=catalog_item.id,
        barcode="COPY-CC-001",
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
async def two_patrons(test_db):
    """Create two patron users for concurrent checkout attempts."""
    from app.core.security import hash_password

    patrons = []
    for i in range(2):
        user = User(
            email=f"patron-cc-{i}@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name=f"Patron{i}",
            last_name="ConcurrentCheckout",
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
async def test_concurrent_item_copy_checkout_only_one_succeeds(
    test_db, catalog_item, item_copy, two_patrons
):
    """Two concurrent checkouts of the same item copy: exactly one succeeds, one fails.

    This tests the database-level partial unique index
    (ix_active_item_copy_checkout) that prevents two active checkouts
    from referencing the same item_copy_id.

    Each attempt needs its OWN AsyncSession/connection: a single
    AsyncSession is not safe for concurrent use from two coroutines at
    once (SQLAlchemy's async Session serializes internally -- flushing
    from two tasks against the same session races on session-internal
    state, raising "Session is already flushing" / "another operation is
    in progress" rather than exercising the real DB-level constraint).
    """
    from tests.conftest import get_session_factory

    patron_a, patron_b = two_patrons
    catalog_item_id = catalog_item.id
    item_copy_id = item_copy.id

    async def attempt_checkout(patron_id):
        """Try to create an active checkout for the shared item copy, using
        its own session so this genuinely races at the DB level."""
        session = get_session_factory()()
        try:
            checkout = Checkout(
                user_id=patron_id,
                item_id=catalog_item_id,
                item_copy_id=item_copy_id,
                status=CheckoutStatus.active,
                due_date=datetime.utcnow() + timedelta(days=21),
            )
            session.add(checkout)
            await session.flush()
            await session.commit()
            return {"success": True, "checkout_id": checkout.id}
        except IntegrityError:
            await session.rollback()
            return {"success": False, "error": "integrity_error"}
        except Exception as e:  # noqa: BLE001 - race test reports any failure mode
            await session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            await session.close()

    results = await asyncio.gather(
        attempt_checkout(patron_a.id),
        attempt_checkout(patron_b.id),
    )

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    assert len(successful) == 1, (
        f"Exactly one checkout should succeed, but {len(successful)} did: {results}"
    )
    assert len(failed) == 1, f"Exactly one checkout should fail, but {len(failed)} did: {results}"


@pytest.mark.asyncio
async def test_returned_checkout_allows_new_checkout(test_db, catalog_item, item_copy, two_patrons):
    """After a checkout is returned, a new active checkout on the same copy is allowed.

    Validates that the partial unique index only applies to status='active'.
    """
    patron_a, patron_b = two_patrons

    # Patron A checks out the item copy
    checkout_a = Checkout(
        user_id=patron_a.id,
        item_id=catalog_item.id,
        item_copy_id=item_copy.id,
        status=CheckoutStatus.active,
        due_date=datetime.utcnow() + timedelta(days=21),
    )
    test_db.add(checkout_a)
    await test_db.commit()
    await test_db.refresh(checkout_a)

    # Patron A returns the item
    checkout_a.status = CheckoutStatus.returned
    checkout_a.returned_at = datetime.utcnow()
    await test_db.commit()

    # Patron B should now be able to checkout the same copy
    checkout_b = Checkout(
        user_id=patron_b.id,
        item_id=catalog_item.id,
        item_copy_id=item_copy.id,
        status=CheckoutStatus.active,
        due_date=datetime.utcnow() + timedelta(days=21),
    )
    test_db.add(checkout_b)
    await test_db.commit()
    await test_db.refresh(checkout_b)

    assert checkout_b.id is not None
    assert checkout_b.status == CheckoutStatus.active
    assert checkout_b.item_copy_id == item_copy.id

    # Verify both checkouts exist in the database
    result = await test_db.execute(select(Checkout).where(Checkout.item_copy_id == item_copy.id))
    all_checkouts = result.scalars().all()
    assert len(all_checkouts) == 2

    active_checkouts = [c for c in all_checkouts if c.status == CheckoutStatus.active]
    assert len(active_checkouts) == 1
    assert active_checkouts[0].id == checkout_b.id
