# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Branch-aware closure handling in check_and_create_overdue_fine.

Bug: count_closure_days() was always called without branch_id, so only
system-wide closures reduced overdue-fine days. A branch closed for
renovation still accrued fines for its own patrons. These tests pin the
fix: the checked-out copy's own branch (resolved via BranchItemCopy) is
now passed through, with a system-wide-only fallback when it can't be
resolved.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.fine_service as fine_service
from app.core.circulation_config import OVERDUE_GRACE_HOURS
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus
from app.models.inventory import ItemCopy
from app.models.multi_branch import BranchClosure, BranchItemCopy
from app.models.user import User
from app.services.fine_service import check_and_create_overdue_fine

ITEM_BRANCH_ID = 42
OTHER_BRANCH_ID = 99
BASE_OVERDUE_DAYS = 10


@pytest.fixture(autouse=True)
def _enable_fining(monkeypatch):
    # FINE_FREE_MODE defaults True in fine_service, so the monetary-fine
    # branch never runs and OVERDUE_FINE_PER_DAY is $0.00; override both
    # so a real Fine lands and its amount encodes the day count.
    monkeypatch.setattr(fine_service, "FINE_FREE_MODE", False)
    monkeypatch.setattr(fine_service, "OVERDUE_FINE_PER_DAY", Decimal("1.00"))


def _due_date_for_overdue_days(now: datetime, days: int) -> datetime:
    """due_date yielding exactly `days` post-grace overdue days, with a
    1-hour margin so real elapsed test-run time can't tip it into day+1."""
    return now - timedelta(hours=OVERDUE_GRACE_HOURS + 24 * (days - 1) + 1)


async def _make_checkout(
    db: AsyncSession,
    patron: User,
    item: CatalogItem,
    item_copy: ItemCopy | None,
    due_date: datetime,
) -> Checkout:
    checkout = Checkout(
        user_id=patron.id,
        item_id=item.id,
        item_copy_id=item_copy.id if item_copy else None,
        status=CheckoutStatus.active,
        checked_out_at=due_date - timedelta(days=30),
        due_date=due_date,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)
    return checkout


async def _assign_branch(db: AsyncSession, item_copy_id: int, branch_id: int) -> None:
    db.add(
        BranchItemCopy(
            item_copy_id=item_copy_id,
            home_branch_id=branch_id,
            current_branch_id=branch_id,
        )
    )
    await db.commit()


async def _add_closure(
    db: AsyncSession,
    branch_id: int,
    start: date,
    end: date,
    *,
    is_system_wide: bool = False,
) -> None:
    db.add(
        BranchClosure(
            branch_id=branch_id,
            start_date=start,
            end_date=end,
            reason="Test closure",
            is_system_wide=is_system_wide,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_branch_closure_at_items_own_branch_reduces_fine_days(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, test_item_copy: ItemCopy,
):
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    await _assign_branch(test_db, test_item_copy.id, ITEM_BRANCH_ID)
    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() + timedelta(days=3), due_date.date() + timedelta(days=5),
    )  # 3-day closure at the item's own branch

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, test_item_copy, due_date)

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is not None
    expected_days = BASE_OVERDUE_DAYS - 3
    assert fine.description == f"Overdue by {expected_days} day(s)"
    assert fine.amount == Decimal(expected_days)


@pytest.mark.asyncio
async def test_branch_closure_covering_full_window_zeroes_the_fine(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, test_item_copy: ItemCopy,
):
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    await _assign_branch(test_db, test_item_copy.id, ITEM_BRANCH_ID)
    # Over-cover the window on both ends; count_closure_days clips to the
    # actual [due_date+1, today] range, so this reliably zeroes it out
    # regardless of exact hour-of-day when the test runs.
    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() - timedelta(days=2), now.date() + timedelta(days=2),
    )

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, test_item_copy, due_date)

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is None


@pytest.mark.asyncio
async def test_other_branch_closure_does_not_reduce_fine_days(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, test_item_copy: ItemCopy,
):
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    await _assign_branch(test_db, test_item_copy.id, ITEM_BRANCH_ID)
    # Closure at a DIFFERENT branch than the item's -- must not count.
    await _add_closure(
        test_db, OTHER_BRANCH_ID,
        due_date.date() + timedelta(days=3), due_date.date() + timedelta(days=5),
    )

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, test_item_copy, due_date)

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is not None
    assert fine.description == f"Overdue by {BASE_OVERDUE_DAYS} day(s)"
    assert fine.amount == Decimal(BASE_OVERDUE_DAYS)


@pytest.mark.asyncio
async def test_system_wide_closure_still_reduces_fine_days(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, test_item_copy: ItemCopy,
):
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    await _assign_branch(test_db, test_item_copy.id, ITEM_BRANCH_ID)
    await _add_closure(
        test_db, OTHER_BRANCH_ID,
        due_date.date() + timedelta(days=3), due_date.date() + timedelta(days=5),
        is_system_wide=True,
    )

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, test_item_copy, due_date)

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is not None
    expected_days = BASE_OVERDUE_DAYS - 3
    assert fine.description == f"Overdue by {expected_days} day(s)"
    assert fine.amount == Decimal(expected_days)


@pytest.mark.asyncio
async def test_unresolvable_branch_no_item_copy_falls_back_to_system_wide_only(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem,
):
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    # System-wide closure (2 days) -- should count.
    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() + timedelta(days=2), due_date.date() + timedelta(days=3),
        is_system_wide=True,
    )
    # Branch-specific closure (3 days) -- irrelevant since the checkout
    # has no item_copy_id to resolve a branch from; must NOT count.
    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() + timedelta(days=5), due_date.date() + timedelta(days=7),
    )

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, None, due_date)
    assert checkout.item_copy_id is None

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is not None
    expected_days = BASE_OVERDUE_DAYS - 2
    assert fine.description == f"Overdue by {expected_days} day(s)"
    assert fine.amount == Decimal(expected_days)


@pytest.mark.asyncio
async def test_item_copy_without_branch_assignment_falls_back_to_system_wide_only(
    test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem, test_item_copy: ItemCopy,
):
    """item_copy_id is set, but no BranchItemCopy row exists for it (e.g. a
    single-branch library that never assigns copies to branches) -- the
    resolver must return None rather than raise, same fallback as above."""
    now = datetime.now(timezone.utc)
    due_date = _due_date_for_overdue_days(now, BASE_OVERDUE_DAYS)

    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() + timedelta(days=2), due_date.date() + timedelta(days=3),
        is_system_wide=True,
    )
    await _add_closure(
        test_db, ITEM_BRANCH_ID,
        due_date.date() + timedelta(days=5), due_date.date() + timedelta(days=7),
    )

    checkout = await _make_checkout(test_db, test_patron, test_catalog_item, test_item_copy, due_date)

    fine = await check_and_create_overdue_fine(checkout, test_db, test_patron)

    assert fine is not None
    expected_days = BASE_OVERDUE_DAYS - 2
    assert fine.description == f"Overdue by {expected_days} day(s)"
    assert fine.amount == Decimal(expected_days)
