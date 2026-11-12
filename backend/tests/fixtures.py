# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Advanced test fixtures using factory pattern for complex test scenarios.

Provides composite fixtures combining multiple entities for realistic test scenarios.
Examples: patron with checkouts + holds + fines, catalog with diverse items, etc.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus, ItemType
from app.models.circulation import Checkout, Hold
from app.core.datetime_utils import utc_now


# ==================== Factory Fixtures ====================

class UserFactory:
    """Factory for creating test users with various roles."""

    @staticmethod
    async def create_patron(
        db: AsyncSession,
        email: str = "patron@test.com",
        first_name: str = "Test",
        last_name: str = "Patron",
        **kwargs
    ) -> User:
        """Create a patron user."""
        user = User(
            email=email,
            password_hash=hash_password("TestPassword123!"),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            **kwargs
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def create_admin(
        db: AsyncSession,
        email: str = "admin@test.com",
        first_name: str = "Test",
        last_name: str = "Admin",
        **kwargs
    ) -> User:
        """Create an admin user."""
        user = User(
            email=email,
            password_hash=hash_password("AdminPassword123!"),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
            **kwargs
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def create_staff(
        db: AsyncSession,
        email: str = "staff@test.com",
        first_name: str = "Test",
        last_name: str = "Staff",
        **kwargs
    ) -> User:
        """Create a staff user."""
        user = User(
            email=email,
            password_hash=hash_password("StaffPassword123!"),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.STAFF,
            is_active=True,
            email_verified=True,
            **kwargs
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def create_bulk(
        db: AsyncSession,
        count: int = 5,
        role: UserRole = UserRole.PATRON,
    ) -> list[User]:
        """Create multiple users of the same role."""
        users = []
        for i in range(count):
            user = User(
                email=f"user{i}@test.com",
                password_hash=hash_password("TestPassword123!"),
                first_name=f"Test{i}",
                last_name="User",
                role=role,
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            users.append(user)

        await db.commit()
        for user in users:
            await db.refresh(user)
        return users


class CatalogItemFactory:
    """Factory for creating diverse test catalog items."""

    @staticmethod
    async def create_book(
        db: AsyncSession,
        title: str = "Test Book",
        isbn: str = "9781234567890",
        **kwargs
    ) -> CatalogItem:
        """Create a book."""
        item = CatalogItem(
            title=title,
            item_type=ItemType.BOOK,
            status=ItemStatus.AVAILABLE,
            isbn=isbn,
            author="Test Author",
            publication_year=2024,
            page_count=300,
            **kwargs
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def create_audiobook(
        db: AsyncSession,
        title: str = "Test Audiobook",
        isbn: str = "9789876543210",
        **kwargs
    ) -> CatalogItem:
        """Create an audiobook."""
        item = CatalogItem(
            title=title,
            item_type=ItemType.AUDIOBOOK,
            status=ItemStatus.AVAILABLE,
            isbn=isbn,
            author="Test Author",
            **kwargs
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def create_dvd(
        db: AsyncSession,
        title: str = "Test Movie",
        **kwargs
    ) -> CatalogItem:
        """Create a DVD."""
        item = CatalogItem(
            title=title,
            item_type=ItemType.DVD,
            status=ItemStatus.AVAILABLE,
            **kwargs
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def create_diverse_collection(
        db: AsyncSession,
        count_per_type: int = 5,
    ) -> dict[str, list[CatalogItem]]:
        """Create a diverse collection of different item types."""
        items = {}

        # Create books
        books = []
        for i in range(count_per_type):
            book = await CatalogItemFactory.create_book(
                db,
                title=f"Book {i}",
                isbn=f"978-0-{i:08d}-0"
            )
            books.append(book)
        items["books"] = books

        # Create audiobooks
        audiobooks = []
        for i in range(count_per_type):
            audiobook = await CatalogItemFactory.create_audiobook(
                db,
                title=f"Audiobook {i}",
                isbn=f"978-1-{i:08d}-0"
            )
            audiobooks.append(audiobook)
        items["audiobooks"] = audiobooks

        # Create DVDs
        dvds = []
        for i in range(count_per_type):
            dvd = await CatalogItemFactory.create_dvd(
                db,
                title=f"Movie {i}"
            )
            dvds.append(dvd)
        items["dvds"] = dvds

        return items


class CirculationFactory:
    """Factory for creating circulation records."""

    @staticmethod
    async def create_checkout(
        db: AsyncSession,
        user: User,
        item: CatalogItem,
        status: str = "active",
        due_date: datetime = None,
        **kwargs
    ) -> Checkout:
        """Create a checkout record."""
        if due_date is None:
            due_date = utc_now() + timedelta(days=14)

        checkout = Checkout(
            user_id=user.id,
            catalog_item_id=item.id,
            status=status,
            due_date=due_date,
            checked_out_at=utc_now(),
            **kwargs
        )
        db.add(checkout)
        await db.commit()
        await db.refresh(checkout)

        # Update item status
        item.status = ItemStatus.CHECKED_OUT
        await db.commit()

        return checkout

    @staticmethod
    async def create_overdue_checkout(
        db: AsyncSession,
        user: User,
        item: CatalogItem,
        days_overdue: int = 7,
        **kwargs
    ) -> Checkout:
        """Create an overdue checkout."""
        due_date = utc_now() - timedelta(days=days_overdue)
        return await CirculationFactory.create_checkout(
            db,
            user,
            item,
            due_date=due_date,
            **kwargs
        )

    @staticmethod
    async def create_hold(
        db: AsyncSession,
        user: User,
        item: CatalogItem,
        position: int = 1,
        **kwargs
    ) -> Hold:
        """Create a hold record."""
        hold = Hold(
            user_id=user.id,
            catalog_item_id=item.id,
            position=position,
            placed_at=utc_now(),
            **kwargs
        )
        db.add(hold)
        await db.commit()
        await db.refresh(hold)
        return hold


# ==================== Composite Fixtures ====================

@pytest.fixture
async def patron_with_checkouts(test_db: AsyncSession):
    """Create a patron with multiple active checkouts."""
    # Create patron
    patron = await UserFactory.create_patron(test_db, email="patron_checkouts@test.com")

    # Create catalog items
    items = await CatalogItemFactory.create_diverse_collection(test_db, count_per_type=2)
    all_items = items["books"] + items["audiobooks"] + items["dvds"]

    # Create checkouts
    checkouts = []
    for item in all_items[:5]:  # 5 checkouts
        checkout = await CirculationFactory.create_checkout(test_db, patron, item)
        checkouts.append(checkout)

    return {
        "user": patron,
        "items": all_items[:5],
        "checkouts": checkouts,
    }


@pytest.fixture
async def patron_with_holds(test_db: AsyncSession):
    """Create a patron with multiple holds."""
    patron = await UserFactory.create_patron(test_db, email="patron_holds@test.com")

    # Create catalog items
    items = [
        await CatalogItemFactory.create_book(test_db, title="Hold Book 1"),
        await CatalogItemFactory.create_book(test_db, title="Hold Book 2"),
        await CatalogItemFactory.create_audiobook(test_db, title="Hold Audio 1"),
    ]

    # Create holds
    holds = []
    for i, item in enumerate(items):
        hold = await CirculationFactory.create_hold(test_db, patron, item, position=i + 1)
        holds.append(hold)

    return {
        "user": patron,
        "items": items,
        "holds": holds,
    }


@pytest.fixture
async def patron_with_fines(test_db: AsyncSession):
    """Create a patron with multiple fines."""
    patron = await UserFactory.create_patron(test_db, email="patron_fines@test.com")

    # Create fines
    fines = []
    for i in range(3):
        fine = await CirculationFactory.create_fine(
            test_db,
            patron,
            amount=Decimal(str(10.00 + i * 5)),
            reason=f"overdue_{i}"
        )
        fines.append(fine)

    return {
        "user": patron,
        "fines": fines,
        "total_fines": sum(f.amount for f in fines),
    }


@pytest.fixture
async def patron_with_complete_circulation(test_db: AsyncSession):
    """
    Create a patron with complete circulation data:
    - Multiple checkouts (active + overdue)
    - Multiple holds
    - Multiple fines
    """
    patron = await UserFactory.create_patron(test_db, email="patron_complete@test.com")

    # Create diverse catalog items
    items = await CatalogItemFactory.create_diverse_collection(test_db, count_per_type=3)
    all_items = items["books"] + items["audiobooks"] + items["dvds"]

    # Create active checkouts
    active_checkouts = []
    for item in all_items[:3]:
        checkout = await CirculationFactory.create_checkout(test_db, patron, item)
        active_checkouts.append(checkout)

    # Create overdue checkouts
    overdue_checkouts = []
    for item in all_items[3:5]:
        checkout = await CirculationFactory.create_overdue_checkout(
            test_db, patron, item, days_overdue=10
        )
        overdue_checkouts.append(checkout)

    # Create holds
    holds = []
    for i, item in enumerate(all_items[5:7]):
        hold = await CirculationFactory.create_hold(test_db, patron, item, position=i + 1)
        holds.append(hold)

    # Create fines
    fines = []
    for i in range(2):
        fine = await CirculationFactory.create_fine(
            test_db,
            patron,
            amount=Decimal(str(15.00 + i * 10))
        )
        fines.append(fine)

    return {
        "user": patron,
        "active_checkouts": active_checkouts,
        "overdue_checkouts": overdue_checkouts,
        "holds": holds,
        "fines": fines,
        "all_items": all_items,
    }


@pytest.fixture
async def multiple_patrons_with_data(test_db: AsyncSession):
    """Create multiple patrons with various circulation data."""
    # Create patrons with different roles
    patrons = await UserFactory.create_bulk(test_db, count=5, role=UserRole.PATRON)

    # Create diverse catalog
    items = await CatalogItemFactory.create_diverse_collection(test_db, count_per_type=5)
    all_items = items["books"] + items["audiobooks"] + items["dvds"]

    # Distribute items among patrons
    patron_data = {}
    item_idx = 0

    for patron in patrons:
        checkouts = []
        holds = []

        # Give each patron some checkouts
        for _ in range(3):
            if item_idx < len(all_items):
                checkout = await CirculationFactory.create_checkout(
                    test_db, patron, all_items[item_idx]
                )
                checkouts.append(checkout)
                item_idx += 1

        # Give each patron a hold
        if item_idx < len(all_items):
            hold = await CirculationFactory.create_hold(
                test_db, patron, all_items[item_idx]
            )
            holds.append(hold)
            item_idx += 1

        patron_data[patron.id] = {
            "user": patron,
            "checkouts": checkouts,
            "holds": holds,
        }

    return {
        "patrons": patrons,
        "items": all_items,
        "patron_data": patron_data,
    }


# ==================== Helper Fixtures ====================

@pytest.fixture
async def clean_catalog(test_db: AsyncSession):
    """Get a database session with diverse catalog items ready for testing."""
    items = await CatalogItemFactory.create_diverse_collection(test_db, count_per_type=10)
    return items


@pytest.fixture
async def all_user_roles(test_db: AsyncSession):
    """Create users with all available roles."""
    patron = await UserFactory.create_patron(test_db)
    staff = await UserFactory.create_staff(test_db)
    admin = await UserFactory.create_admin(test_db)

    return {
        "patron": patron,
        "staff": staff,
        "admin": admin,
    }
