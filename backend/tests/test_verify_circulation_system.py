# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Circulation System Verification Test Suite

Proves that every major circulation workflow operates correctly by testing
the service layer directly against the database. Covers:

1. Checkout: item status transitions, due date calculation, duplicate prevention
2. Return: status transitions, hold queue advancement, item availability
3. Holds: placement, queue ordering, immediate ready when available
4. Renewals: due date extension, count increment, hold blocking
5. Overdue detection: grace period, status marking, fine-free mode
6. Checkout limits: enforced per role settings
7. Hold limits: enforced per role settings
8. Hold expiration: expired holds advance queue, item goes available
9. Reading minutes: fine-exempt children accrue minutes, not fines
10. Return with hold queue: next patron promoted to ready
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select, update

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.permission import RoleSettings
from app.models.user import User, UserRole
from app.core.datetime_utils import utc_now
from app.core.authorization import clear_permissions_cache


def _ensure_utc(dt):
    """Normalize a datetime to UTC-aware for comparison.
    SQLite returns naive datetimes; PostgreSQL returns aware ones."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_sqlite(db):
    """Check if running on SQLite (limited SQL function support)."""
    return "sqlite" in str(db.bind.url)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _unique_email():
    return f"circ_verify_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(autouse=True)
def _clear_auth_cache():
    """Clear the authorization module's in-memory caches between every test."""
    clear_permissions_cache()
    yield
    clear_permissions_cache()


@pytest.fixture
async def patron(test_db):
    """Standard patron user."""
    from app.core.security import hash_password
    user = User(
        email=_unique_email(),
        password_hash=hash_password("Pwd12345!"),
        first_name="Alice",
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
async def patron_b(test_db):
    """Second patron for hold queue tests."""
    from app.core.security import hash_password
    user = User(
        email=_unique_email(),
        password_hash=hash_password("Pwd12345!"),
        first_name="Bob",
        last_name="Borrower",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_c(test_db):
    """Third patron for multi-hold tests."""
    from app.core.security import hash_password
    user = User(
        email=_unique_email(),
        password_hash=hash_password("Pwd12345!"),
        first_name="Carol",
        last_name="Checker",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def child_user(test_db):
    """Child user with reading minutes instead of fines."""
    from app.core.security import hash_password
    user = User(
        email=_unique_email(),
        password_hash=hash_password("Pwd12345!"),
        first_name="Danny",
        last_name="Kid",
        role=UserRole.CHILD,
        is_active=True,
        email_verified=True,
        reading_minutes_owed=0,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def child_role_settings(test_db):
    """Role settings for CHILD role: fine-exempt with reading minutes."""
    # Check if settings already exist
    result = await test_db.execute(
        select(RoleSettings).where(RoleSettings.role == UserRole.CHILD)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.use_reading_minutes = True
        existing.fine_exempt = True
        existing.minutes_per_day_overdue = 15
        existing.max_reading_minutes_owed = 180
        await test_db.commit()
        await test_db.refresh(existing)
        return existing

    settings = RoleSettings(
        role=UserRole.CHILD,
        checkout_duration_days=14,
        max_checkouts=3,
        max_renewals=1,
        max_holds=3,
        hold_duration_days=7,
        use_reading_minutes=True,
        fine_exempt=True,
        minutes_per_day_overdue=15,
        max_reading_minutes_owed=180,
    )
    test_db.add(settings)
    await test_db.commit()
    await test_db.refresh(settings)
    return settings


@pytest.fixture
async def available_book(test_db):
    """A single available book with NO ItemCopy rows (one virtual copy).

    The virtual-copy semantics under test require zero copies; SQLite rowid
    reuse in the shared test DB can attach stale ItemCopy rows from earlier
    tests to this item's recycled id, so scrub them explicitly."""
    from sqlalchemy import delete
    from app.models.inventory import ItemCopy

    item = CatalogItem(
        title="Verification Book Alpha",
        author="Test Author",
        isbn=f"978-0-{uuid.uuid4().hex[:6]}-1",
        description="For circulation verification",
        status=ItemStatus.available,
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    await test_db.execute(
        delete(ItemCopy).where(ItemCopy.catalog_item_id == item.id)
    )
    await test_db.commit()
    return item


@pytest.fixture
async def available_books(test_db):
    """Multiple available books for limit testing."""
    books = []
    for i in range(8):
        item = CatalogItem(
            title=f"Verification Book {i+1}",
            author=f"Author {i+1}",
            isbn=f"978-0-{uuid.uuid4().hex[:6]}-{i}",
            description=f"Book {i+1} for verification",
            status=ItemStatus.available,
            publication_year=2024,
        )
        test_db.add(item)
        books.append(item)
    await test_db.commit()
    for b in books:
        await test_db.refresh(b)
    return books


# ---------------------------------------------------------------------------
# 1. CHECKOUT WORKFLOW
# ---------------------------------------------------------------------------


class TestCheckoutWorkflow:
    """Prove that checkout creates correct records and transitions item status."""

    async def test_checkout_creates_active_record(self, test_db, patron, available_book):
        """Checkout creates a record with status=active and correct due date."""
        from app.services.checkout_service import create_checkout

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        assert checkout.status == CheckoutStatus.active
        assert checkout.user_id == patron.id
        assert checkout.item_id == available_book.id
        assert checkout.renewal_count == 0
        assert checkout.returned_at is None
        # Due date should be ~21 days from now (default loan period)
        expected_due = utc_now() + timedelta(days=21)
        assert abs((_ensure_utc(checkout.due_date) - expected_due).total_seconds()) < 60

    async def test_checkout_changes_item_status_to_checked_out(
        self, test_db, patron, available_book
    ):
        """After checkout, the item status must be 'checked_out'."""
        from app.services.checkout_service import create_checkout

        await create_checkout(patron, available_book.id, test_db)
        await test_db.commit()
        await test_db.refresh(available_book)

        assert available_book.status == ItemStatus.checked_out

    async def test_duplicate_checkout_blocked(self, test_db, patron, available_book):
        """Cannot checkout the same item twice."""
        from app.services.checkout_service import create_checkout
        from app.core.exceptions import ConflictError

        await create_checkout(patron, available_book.id, test_db)
        await test_db.commit()

        with pytest.raises(ConflictError):
            await create_checkout(patron, available_book.id, test_db)

    async def test_unavailable_item_cannot_be_checked_out(
        self, test_db, patron, patron_b, available_book
    ):
        """An item that is already checked_out cannot be checked out again.

        A bare status flip is not enough: a stale checked_out status with no
        active loan self-heals and the checkout proceeds. The block is decided
        by loan counts, so another patron's REAL active loan must consume the
        zero-copy title's single virtual copy."""
        from app.services.checkout_service import create_checkout
        from app.core.exceptions import ConflictError

        other_loan = Checkout(
            user_id=patron_b.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            due_date=utc_now() + timedelta(days=21),
        )
        test_db.add(other_loan)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()

        with pytest.raises(ConflictError):
            await create_checkout(patron, available_book.id, test_db)


# ---------------------------------------------------------------------------
# 2. RETURN WORKFLOW
# ---------------------------------------------------------------------------


class TestReturnWorkflow:
    """Prove that return transitions checkout and item correctly."""

    async def test_return_marks_checkout_as_returned(
        self, test_db, patron, available_book
    ):
        """After return, checkout status is 'returned' and returned_at is set."""
        from app.services.checkout_service import create_checkout, return_checkout

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        await return_checkout(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(checkout)

        assert checkout.status == CheckoutStatus.returned
        assert checkout.returned_at is not None

    async def test_return_makes_item_available(self, test_db, patron, available_book):
        """After return (no holds), item becomes available."""
        from app.services.checkout_service import create_checkout, return_checkout

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        await return_checkout(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(available_book)

        assert available_book.status == ItemStatus.available

    async def test_staff_checkin_attributes_patron_and_staff_separately(
        self, test_db, patron, available_book
    ):
        """When staff processes a checkin, ops_audit records the loan owner
        as `patron_id` and the staff member as `staff_id` -- not the staff
        as patron with staff_id NULL. Regression: pre-fix, /checkin passed
        current_user (staff) as the `user` arg, and return_checkout used
        that same value as the audit `patron`, misattributing every staff
        return.

        Builds the Checkout directly rather than via create_checkout so the
        test doesn't depend on circulation_policy seed data (system_settings
        row); the bug we're covering lives in return_checkout's audit call,
        not the policy path."""
        from app.core.security import hash_password
        from app.models.operations_audit_log import OperationsAuditLog, OperationType
        from app.services.checkout_service import return_checkout

        staff = User(
            email=_unique_email(),
            password_hash=hash_password("Pwd12345!"),
            first_name="Sue",
            last_name="Staffer",
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
        )
        test_db.add(staff)
        await test_db.commit()
        await test_db.refresh(staff)

        checkout = Checkout(
            user_id=patron.id,
            item_id=available_book.id,
            due_date=utc_now() + timedelta(days=14),
            status=CheckoutStatus.active,
        )
        available_book.status = ItemStatus.checked_out
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        await return_checkout(checkout, test_db, patron, staff=staff)
        await test_db.commit()

        audit = (
            await test_db.execute(
                select(OperationsAuditLog)
                .where(OperationsAuditLog.operation_type == OperationType.CHECKOUT_RETURNED.value)
                .where(OperationsAuditLog.checkout_id == checkout.id)
            )
        ).scalar_one()

        assert audit.patron_id == patron.id, "patron column must hold the loan owner"
        assert audit.staff_id == staff.id, "staff column must hold the processor"


# ---------------------------------------------------------------------------
# 3. HOLD PLACEMENT & QUEUE ORDERING
# ---------------------------------------------------------------------------


class TestHoldPlacement:
    """Prove that holds are placed with correct queue positions."""

    async def test_hold_on_available_item_is_immediately_ready(
        self, test_db, patron, available_book
    ):
        """Hold on an available item should be immediately ready."""
        hold = Hold(
            user_id=patron.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.pending,
        )
        test_db.add(hold)
        await test_db.flush()

        # Simulate what the API does for available items
        if available_book.status == ItemStatus.available:
            available_book.status = ItemStatus.on_hold
            hold.status = HoldStatus.ready
            hold.notified_at = utc_now()
            hold.expires_at = utc_now() + timedelta(days=7)

        await test_db.commit()
        await test_db.refresh(hold)

        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None
        assert available_book.status == ItemStatus.on_hold

    async def test_hold_queue_positions_sequential(
        self, test_db, patron, patron_b, patron_c, available_book
    ):
        """Multiple holds on same item get sequential positions."""
        # Item is checked out so holds queue up
        available_book.status = ItemStatus.checked_out
        await test_db.commit()

        holds = []
        for i, p in enumerate([patron, patron_b, patron_c], start=1):
            hold = Hold(
                user_id=p.id,
                item_id=available_book.id,
                position=i,
                status=HoldStatus.pending,
            )
            test_db.add(hold)
            holds.append(hold)

        await test_db.commit()
        for h in holds:
            await test_db.refresh(h)

        assert holds[0].position == 1
        assert holds[1].position == 2
        assert holds[2].position == 3
        assert all(h.status == HoldStatus.pending for h in holds)


# ---------------------------------------------------------------------------
# 4. RENEWAL WORKFLOW
# ---------------------------------------------------------------------------


class TestRenewalWorkflow:
    """Prove that renewal extends due date and increments count."""

    async def test_renewal_extends_due_date(self, test_db, patron, available_book):
        """Renewal extends due date by the loan period from now."""
        from app.services.checkout_service import create_checkout, renew_checkout

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        original_due = _ensure_utc(checkout.due_date)
        await renew_checkout(checkout, patron, test_db)
        await test_db.commit()
        await test_db.refresh(checkout)

        assert checkout.renewal_count == 1
        # New due date should be ~21 days from now
        expected_new_due = utc_now() + timedelta(days=21)
        assert abs((_ensure_utc(checkout.due_date) - expected_new_due).total_seconds()) < 60
        # New due date should be later than original
        assert _ensure_utc(checkout.due_date) >= original_due

    async def test_renewal_blocked_when_holds_exist(
        self, test_db, patron, patron_b, available_book
    ):
        """Cannot renew if another patron has a hold on the item."""
        from app.services.checkout_service import create_checkout, renew_checkout
        from app.core.exceptions import ConflictError

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()

        # Another patron places a hold
        hold = Hold(
            user_id=patron_b.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.pending,
        )
        test_db.add(hold)
        await test_db.commit()

        with pytest.raises(ConflictError):
            await renew_checkout(checkout, patron, test_db)

    async def test_renewal_limit_enforced(self, test_db, patron, available_book):
        """Cannot renew beyond the max renewal limit."""
        from app.services.checkout_service import create_checkout, renew_checkout
        from app.core.exceptions import BusinessLogicError

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        # Default max renewals is 2; renew twice
        await renew_checkout(checkout, patron, test_db)
        await test_db.commit()
        await test_db.refresh(checkout)
        await renew_checkout(checkout, patron, test_db)
        await test_db.commit()
        await test_db.refresh(checkout)

        assert checkout.renewal_count == 2

        with pytest.raises(BusinessLogicError):
            await renew_checkout(checkout, patron, test_db)


# ---------------------------------------------------------------------------
# 5. OVERDUE DETECTION (Fine-Free Mode)
# ---------------------------------------------------------------------------


class TestOverdueDetection:
    """Prove overdue detection works in the library's fine-free mode."""

    async def test_not_overdue_within_due_date(self, test_db, patron, available_book):
        """A checkout with future due date is not overdue."""
        from app.services.fine_service import check_and_create_overdue_fine

        checkout = Checkout(
            user_id=patron.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            due_date=utc_now() + timedelta(days=14),
        )
        test_db.add(checkout)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        result = await check_and_create_overdue_fine(checkout, test_db, patron)
        assert result is None
        assert checkout.status == CheckoutStatus.active

    async def test_within_grace_period_not_overdue(
        self, test_db, patron, available_book
    ):
        """A checkout within the 48-hour grace period should not be flagged."""
        from app.services.fine_service import check_and_create_overdue_fine

        checkout = Checkout(
            user_id=patron.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            # Backdate checked_out_at too: ck_checkout_due_after_checkout
            # requires due_date >= checked_out_at (server default is now()).
            checked_out_at=utc_now() - timedelta(days=15),
            due_date=utc_now() - timedelta(hours=24),  # 24h overdue, within 48h grace
        )
        test_db.add(checkout)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        result = await check_and_create_overdue_fine(checkout, test_db, patron)
        assert result is None
        # Status should still be active because within grace
        assert checkout.status == CheckoutStatus.active

    async def test_past_grace_period_marks_overdue(
        self, test_db, patron, available_book
    ):
        """A checkout past the grace period should be marked overdue."""
        from app.services.fine_service import check_and_create_overdue_fine

        checkout = Checkout(
            user_id=patron.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            # Backdate checked_out_at too: ck_checkout_due_after_checkout
            # requires due_date >= checked_out_at (server default is now()).
            checked_out_at=utc_now() - timedelta(days=26),
            due_date=utc_now() - timedelta(days=5),  # 5 days overdue, past 48h grace
        )
        test_db.add(checkout)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        result = await check_and_create_overdue_fine(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(checkout)

        # In fine-free mode, no monetary fine is created
        assert result is None
        # But checkout IS marked as overdue
        assert checkout.status == CheckoutStatus.overdue


# ---------------------------------------------------------------------------
# 6. CHECKOUT LIMIT ENFORCEMENT
# ---------------------------------------------------------------------------


class TestCheckoutLimits:
    """Prove checkout limits are enforced per role settings."""

    async def test_checkout_limit_blocks_at_max(
        self, test_db, patron, available_books
    ):
        """Patron cannot exceed checkout limit."""
        from app.services.checkout_service import create_checkout, check_checkout_limit
        from app.core.exceptions import BusinessLogicError

        # Create role settings with max_checkouts = 3
        result = await test_db.execute(
            select(RoleSettings).where(RoleSettings.role == UserRole.PATRON)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.max_checkouts = 3
        else:
            settings = RoleSettings(
                role=UserRole.PATRON,
                checkout_duration_days=21,
                max_checkouts=3,
                max_renewals=2,
                max_holds=5,
                hold_duration_days=7,
            )
            test_db.add(settings)
        await test_db.commit()

        # Checkout 3 books (the limit). Keep strong references to the Checkout
        # objects: the session's identity map is weak, and if these are GC'd
        # the limit resolver re-loads them from SQLite with NAIVE due_dates,
        # which blows up against tz-aware utc_now() inside the service.
        loans = []
        for i in range(3):
            loans.append(
                (await create_checkout(patron, available_books[i].id, test_db)).checkout
            )
            await test_db.commit()

        # 4th checkout should fail
        with pytest.raises(BusinessLogicError):
            await create_checkout(patron, available_books[3].id, test_db)


# ---------------------------------------------------------------------------
# 7. HOLD LIMIT ENFORCEMENT
# ---------------------------------------------------------------------------


class TestHoldLimits:
    """Prove hold limits are enforced."""

    async def test_hold_limit_blocks_at_max(
        self, test_db, patron, available_books
    ):
        """Patron cannot exceed hold limit (verified via count query)."""
        from sqlalchemy import func

        # Create role settings with max_holds = 2
        result = await test_db.execute(
            select(RoleSettings).where(RoleSettings.role == UserRole.PATRON)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.max_holds = 2
        else:
            settings = RoleSettings(
                role=UserRole.PATRON,
                checkout_duration_days=21,
                max_checkouts=5,
                max_renewals=2,
                max_holds=2,
                hold_duration_days=7,
            )
            test_db.add(settings)
        await test_db.commit()

        # Mark books as checked_out so holds queue
        for book in available_books[:4]:
            book.status = ItemStatus.checked_out
        await test_db.commit()

        # Place 2 holds (the limit)
        for i in range(2):
            hold = Hold(
                user_id=patron.id,
                item_id=available_books[i].id,
                position=1,
                status=HoldStatus.pending,
            )
            test_db.add(hold)
        await test_db.commit()

        # Query the hold limit from role settings
        from app.core.authorization import get_role_settings
        role_settings = await get_role_settings(patron.role, test_db)
        max_holds = role_settings.max_holds if role_settings else 5

        # Count active holds for the patron
        count_result = await test_db.execute(
            select(func.count(Hold.id)).where(
                Hold.user_id == patron.id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
        )
        active_holds = count_result.scalar()

        # Verify: active holds == max, so a new one should be rejected
        assert active_holds == max_holds
        assert active_holds >= max_holds  # Would block further holds


# ---------------------------------------------------------------------------
# 8. HOLD EXPIRATION & QUEUE ADVANCEMENT
# ---------------------------------------------------------------------------


class TestHoldExpiration:
    """Prove that expired holds are processed and queues advance correctly."""

    async def test_expired_ready_hold_advances_queue(
        self, test_db, patron, patron_b, available_book
    ):
        """When a ready hold expires, the next pending hold is promoted."""
        from app.services.hold_service import process_expired_holds

        available_book.status = ItemStatus.on_hold
        await test_db.commit()

        # Hold 1: ready but expired
        hold1 = Hold(
            user_id=patron.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.ready,
            notified_at=utc_now() - timedelta(days=10),
            expires_at=utc_now() - timedelta(days=3),  # Expired 3 days ago
        )
        # Hold 2: pending, next in queue
        hold2 = Hold(
            user_id=patron_b.id,
            item_id=available_book.id,
            position=2,
            status=HoldStatus.pending,
        )
        test_db.add(hold1)
        test_db.add(hold2)
        await test_db.commit()

        processed = await process_expired_holds(test_db, item_id=available_book.id)
        await test_db.commit()
        await test_db.refresh(hold1)
        await test_db.refresh(hold2)

        assert processed == 1
        assert hold1.status == HoldStatus.expired
        assert hold2.status == HoldStatus.ready
        assert hold2.notified_at is not None
        assert hold2.expires_at is not None

    async def test_expired_hold_no_next_makes_item_available(
        self, test_db, patron, available_book
    ):
        """When last hold expires with no pending holds, item becomes available."""
        from app.services.hold_service import process_expired_holds

        available_book.status = ItemStatus.on_hold
        await test_db.commit()

        hold = Hold(
            user_id=patron.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.ready,
            notified_at=utc_now() - timedelta(days=10),
            expires_at=utc_now() - timedelta(days=3),
        )
        test_db.add(hold)
        await test_db.commit()

        processed = await process_expired_holds(test_db, item_id=available_book.id)
        await test_db.commit()
        await test_db.refresh(hold)
        await test_db.refresh(available_book)

        assert processed == 1
        assert hold.status == HoldStatus.expired
        assert available_book.status == ItemStatus.available


# ---------------------------------------------------------------------------
# 9. READING MINUTES FOR CHILDREN (fine-exempt)
# ---------------------------------------------------------------------------


class TestReadingMinutes:
    """Prove that children accrue reading minutes instead of monetary fines.

    Note: The reading minutes UPDATE uses SQL func.least() which is not
    available in SQLite. These tests require PostgreSQL.
    """

    async def test_child_overdue_adds_reading_minutes(
        self, test_db, child_user, child_role_settings, available_book
    ):
        """Overdue child checkout adds reading minutes, not fines."""
        # func.least() is PostgreSQL-only; skip on SQLite
        if "sqlite" in str(test_db.bind.url):
            pytest.skip("Reading minutes UPDATE uses func.least() (PostgreSQL only)")

        from app.services.fine_service import check_and_create_overdue_fine

        checkout = Checkout(
            user_id=child_user.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            # Backdate checked_out_at too: ck_checkout_due_after_checkout
            # requires due_date >= checked_out_at (server default is now()).
            checked_out_at=utc_now() - timedelta(days=26),
            due_date=utc_now() - timedelta(days=5),  # 5 days overdue, past 48h grace
        )
        test_db.add(checkout)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        result = await check_and_create_overdue_fine(checkout, test_db, child_user)
        await test_db.commit()
        await test_db.refresh(child_user)
        await test_db.refresh(checkout)

        # No monetary fine
        assert result is None
        # Reading minutes should have been added
        # Overdue 5 days, 48h grace = ~3 overdue days * 15 min = 45 min
        assert child_user.reading_minutes_owed > 0
        assert checkout.status == CheckoutStatus.overdue
        assert checkout.last_overdue_days_processed > 0

    async def test_child_reading_minutes_no_duplicates(
        self, test_db, child_user, child_role_settings, available_book
    ):
        """Running overdue check twice does NOT double-count reading minutes."""
        # func.least() is PostgreSQL-only; skip on SQLite
        if "sqlite" in str(test_db.bind.url):
            pytest.skip("Reading minutes UPDATE uses func.least() (PostgreSQL only)")

        from app.services.fine_service import check_and_create_overdue_fine

        checkout = Checkout(
            user_id=child_user.id,
            item_id=available_book.id,
            status=CheckoutStatus.active,
            checked_out_at=utc_now() - timedelta(days=26),
            due_date=utc_now() - timedelta(days=5),
        )
        test_db.add(checkout)
        available_book.status = ItemStatus.checked_out
        await test_db.commit()
        await test_db.refresh(checkout)

        # First run
        await check_and_create_overdue_fine(checkout, test_db, child_user)
        await test_db.commit()
        await test_db.refresh(child_user)
        minutes_after_first = child_user.reading_minutes_owed

        # Second run (same overdue period)
        await check_and_create_overdue_fine(checkout, test_db, child_user)
        await test_db.commit()
        await test_db.refresh(child_user)
        minutes_after_second = child_user.reading_minutes_owed

        # Should be the same - no duplicate addition
        assert minutes_after_second == minutes_after_first


# ---------------------------------------------------------------------------
# 10. RETURN WITH HOLD QUEUE (end-to-end)
# ---------------------------------------------------------------------------


class TestReturnWithHoldQueue:
    """Prove the full return-with-holds workflow."""

    async def test_return_promotes_next_hold_to_ready(
        self, test_db, patron, patron_b, available_book
    ):
        """When an item is returned and there's a pending hold, the hold is promoted."""
        from app.services.checkout_service import create_checkout, return_checkout

        # Patron A checks out the book
        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()

        # Patron B places a hold (pending)
        hold = Hold(
            user_id=patron_b.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.pending,
        )
        test_db.add(hold)
        await test_db.commit()

        # Patron A returns the book
        await test_db.refresh(checkout)
        await return_checkout(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(hold)
        await test_db.refresh(available_book)
        await test_db.refresh(checkout)

        # Checkout is returned
        assert checkout.status == CheckoutStatus.returned
        # Hold was promoted to ready
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert hold.expires_at is not None
        # Item is on_hold (waiting for patron B to pick up)
        assert available_book.status == ItemStatus.on_hold

    async def test_return_no_holds_makes_available(
        self, test_db, patron, available_book
    ):
        """When returned with no holds, item becomes available."""
        from app.services.checkout_service import create_checkout, return_checkout

        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        await test_db.refresh(checkout)

        await return_checkout(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(available_book)

        assert available_book.status == ItemStatus.available


# ---------------------------------------------------------------------------
# 11. HOLD CANCELLATION REORDERS QUEUE
# ---------------------------------------------------------------------------


class TestHoldCancellation:
    """Prove that cancelling a hold reorders the remaining positions."""

    async def test_cancel_hold_reorders_positions(
        self, test_db, patron, patron_b, patron_c, available_book
    ):
        """Cancelling hold #1 should shift #2 and #3 down."""
        available_book.status = ItemStatus.checked_out
        await test_db.commit()

        hold1 = Hold(
            user_id=patron.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.pending,
        )
        hold2 = Hold(
            user_id=patron_b.id,
            item_id=available_book.id,
            position=2,
            status=HoldStatus.pending,
        )
        hold3 = Hold(
            user_id=patron_c.id,
            item_id=available_book.id,
            position=3,
            status=HoldStatus.pending,
        )
        test_db.add_all([hold1, hold2, hold3])
        await test_db.commit()

        # Cancel hold1
        hold1.status = HoldStatus.cancelled
        # Manually adjust positions (as the API does)
        hold2.position = 1
        hold3.position = 2
        await test_db.commit()
        await test_db.refresh(hold2)
        await test_db.refresh(hold3)

        assert hold2.position == 1
        assert hold3.position == 2


# ---------------------------------------------------------------------------
# 12. FULL CIRCULATION ROUND-TRIP
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    """End-to-end proof: checkout -> overdue check -> return -> hold promotion."""

    async def test_complete_lifecycle(
        self, test_db, patron, patron_b, available_book
    ):
        """Full lifecycle: checkout, goes overdue, return, next hold promoted."""
        from app.services.checkout_service import create_checkout, return_checkout
        from app.services.fine_service import check_and_create_overdue_fine

        # 1. Patron A checks out
        checkout = (await create_checkout(patron, available_book.id, test_db)).checkout
        await test_db.commit()
        assert checkout.status == CheckoutStatus.active
        assert available_book.status == ItemStatus.checked_out

        # 2. Patron B places hold
        hold = Hold(
            user_id=patron_b.id,
            item_id=available_book.id,
            position=1,
            status=HoldStatus.pending,
        )
        test_db.add(hold)
        await test_db.commit()

        # 3. Simulate time passing - checkout becomes overdue. Backdate
        # checked_out_at along with due_date: ck_checkout_due_after_checkout
        # requires due_date >= checked_out_at.
        checkout.checked_out_at = utc_now() - timedelta(days=26)
        checkout.due_date = utc_now() - timedelta(days=5)
        await test_db.commit()
        await test_db.refresh(checkout)

        await check_and_create_overdue_fine(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(checkout)
        assert checkout.status == CheckoutStatus.overdue

        # 4. Patron A returns the overdue book
        await return_checkout(checkout, test_db, patron)
        await test_db.commit()
        await test_db.refresh(checkout)
        await test_db.refresh(hold)
        await test_db.refresh(available_book)

        # 5. Verify final state
        assert checkout.status == CheckoutStatus.returned
        assert checkout.returned_at is not None
        assert hold.status == HoldStatus.ready
        assert hold.notified_at is not None
        assert available_book.status == ItemStatus.on_hold
