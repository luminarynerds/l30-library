# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Staff Pull List feature.

The pull list allows library staff to generate a list of items to retrieve
from shelves for ready holds, grouped by shelf location for efficient picking.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Hold, HoldStatus


class TestPullListAccess:
    """Test access control for the pull list endpoint."""

    @pytest.mark.asyncio
    async def test_patron_cannot_access_pull_list(
        self, test_db: AsyncSession, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that regular patrons cannot access the pull list endpoint."""
        # Create a ready hold
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()

        # Import here to ensure test fixtures are set up first
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        # Override dependencies
        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_patron

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        # Bypass FirstBootMiddleware (app/core/first_boot.py): the per-test
        # DB has no admin user, which would otherwise trip the
        # setup-required check and return 503 before auth is even checked.
        # Same workaround as the `client` fixture in tests/conftest.py.
        app.state.setup_complete = True

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 403
                # Global HTTPException handler (app/core/exception_handlers.py)
                # wraps errors as {"error": {"message": ...}}, not {"detail": ...}.
                assert "Staff or admin role required" in response.json()["error"]["message"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_staff_can_access_pull_list(
        self, test_db: AsyncSession, test_staff: User, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that staff members can access the pull list endpoint."""
        # Create a ready hold
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        # Bypass FirstBootMiddleware -- see comment in
        # test_patron_cannot_access_pull_list above.
        app.state.setup_complete = True

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()
                assert "locations" in data
                assert "total_items" in data
                assert "generated_at" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_can_access_pull_list(
        self, test_db: AsyncSession, test_admin: User, test_patron: User, test_catalog_item: CatalogItem
    ):
        """Test that admin users can access the pull list endpoint."""
        # Create a ready hold
        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_admin

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        # Bypass FirstBootMiddleware -- see comment in
        # test_patron_cannot_access_pull_list above.
        app.state.setup_complete = True

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestPullListFiltering:
    """Test location filtering for the pull list."""

    @pytest.mark.asyncio
    async def test_filter_by_location(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that pull list can be filtered by location."""
        from app.core.security import hash_password

        # Create patron
        patron = User(
            email="pulllist_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Pull",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create items in different locations
        item_fiction = CatalogItem(
            title="Fiction Book",
            author="Fiction Author",
            status=ItemStatus.on_hold,
            location="Fiction A-1",
            call_number="FIC AUT",
        )
        item_nonfiction = CatalogItem(
            title="Nonfiction Book",
            author="Nonfiction Author",
            status=ItemStatus.on_hold,
            location="Nonfiction B-2",
            call_number="629.1 AUT",
        )
        test_db.add_all([item_fiction, item_nonfiction])
        await test_db.commit()
        await test_db.refresh(item_fiction)
        await test_db.refresh(item_nonfiction)

        # Create ready holds for both items
        now = datetime.now(timezone.utc)
        hold_fiction = Hold(
            user_id=patron.id,
            item_id=item_fiction.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        hold_nonfiction = Hold(
            user_id=patron.id,
            item_id=item_nonfiction.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add_all([hold_fiction, hold_nonfiction])
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with TestClient(app) as client:
                # Filter by Fiction location
                response = client.get(
                    "/api/v1/circulation/holds/pull-list",
                    params={"location": "Fiction A-1"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["total_items"] == 1
                assert len(data["locations"]) == 1
                assert data["locations"][0]["location"] == "Fiction A-1"
                assert data["locations"][0]["items"][0]["item_title"] == "Fiction Book"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_locations(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that pull list without filter returns items from all locations."""
        from app.core.security import hash_password

        # Create patron
        patron = User(
            email="pulllist_all_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="All",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create items in different locations
        item1 = CatalogItem(
            title="Location A Book",
            author="Author A",
            status=ItemStatus.on_hold,
            location="Location A",
            call_number="LOC A",
        )
        item2 = CatalogItem(
            title="Location B Book",
            author="Author B",
            status=ItemStatus.on_hold,
            location="Location B",
            call_number="LOC B",
        )
        test_db.add_all([item1, item2])
        await test_db.commit()
        await test_db.refresh(item1)
        await test_db.refresh(item2)

        # Create ready holds for both items
        now = datetime.now(timezone.utc)
        hold1 = Hold(
            user_id=patron.id,
            item_id=item1.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        hold2 = Hold(
            user_id=patron.id,
            item_id=item2.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add_all([hold1, hold2])
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with TestClient(app) as client:
                # No filter
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()
                assert data["total_items"] == 2
                assert len(data["locations"]) == 2
                location_names = [loc["location"] for loc in data["locations"]]
                assert "Location A" in location_names
                assert "Location B" in location_names
        finally:
            app.dependency_overrides.clear()


class TestPullListSorting:
    """Test sorting of items in the pull list."""

    @pytest.mark.asyncio
    async def test_items_sorted_by_location_then_expiration(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that items are sorted by shelf location, then by pickup
        urgency (soonest-expiring hold first).

        app/api/v1/circulation/hold_shelf.py:get_holds_pull_list groups by
        CatalogItem.location, then orders by Hold.expires_at (most urgent
        first) -- not by call_number. This was previously asserted as a
        call-number sort, which the endpoint has never implemented; the
        docstring and order_by() have always documented "most urgent first".
        """
        from app.core.security import hash_password

        # Create patron
        patron = User(
            email="pulllist_sort_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Sort",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create items with different call numbers in same location
        item_z = CatalogItem(
            title="Z Book",
            author="Z Author",
            status=ItemStatus.on_hold,
            location="Fiction",
            call_number="FIC ZZZ",
        )
        item_a = CatalogItem(
            title="A Book",
            author="A Author",
            status=ItemStatus.on_hold,
            location="Fiction",
            call_number="FIC AAA",
        )
        item_m = CatalogItem(
            title="M Book",
            author="M Author",
            status=ItemStatus.on_hold,
            location="Fiction",
            call_number="FIC MMM",
        )
        test_db.add_all([item_z, item_a, item_m])
        await test_db.commit()
        await test_db.refresh(item_z)
        await test_db.refresh(item_a)
        await test_db.refresh(item_m)

        # Create ready holds with distinct expiration dates, most urgent
        # first: item_z expires soonest, item_m latest. created_at is
        # deliberately given the OPPOSITE order (m earliest, z latest) so a
        # regression that sorts by created_at instead of expires_at would
        # fail this test.
        now = datetime.now(timezone.utc)
        holds = [
            Hold(
                user_id=patron.id,
                item_id=item.id,
                status=HoldStatus.ready,
                position=1,
                created_at=now - timedelta(minutes=i),
                notified_at=now,
                expires_at=now + timedelta(days=expires_in_days),
            )
            for i, (item, expires_in_days) in enumerate(
                [(item_z, 1), (item_a, 5), (item_m, 10)]
            )
        ]
        test_db.add_all(holds)
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        # Bypass FirstBootMiddleware -- see comment in
        # TestPullListAccess.test_patron_cannot_access_pull_list.
        app.state.setup_complete = True

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()

                # Find the Fiction location
                fiction_loc = None
                for loc in data["locations"]:
                    if loc["location"] == "Fiction":
                        fiction_loc = loc
                        break

                assert fiction_loc is not None
                items = fiction_loc["items"]

                # Items should be sorted by pickup urgency (soonest-expiring
                # hold first), matching get_holds_pull_list's order_by.
                call_numbers = [item["call_number"] for item in items]
                assert call_numbers == ["FIC ZZZ", "FIC AAA", "FIC MMM"]
        finally:
            app.dependency_overrides.clear()


class TestPullListContent:
    """Test content of pull list items."""

    @pytest.mark.asyncio
    async def test_pull_list_includes_required_fields(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that pull list items include all required fields."""
        from app.core.security import hash_password

        # Create patron with library card
        patron = User(
            email="pulllist_fields_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Fields",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            library_card="LIB-12345",
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create item with all details
        item = CatalogItem(
            title="Complete Details Book",
            author="Complete Author",
            status=ItemStatus.on_hold,
            location="Reference R-3",
            call_number="REF 100.5 COM",
            barcode="BARCODE-98765",
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        # Create ready hold
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=7)
        hold = Hold(
            user_id=patron.id,
            item_id=item.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=expires_at,
        )
        test_db.add(hold)
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()

                assert data["total_items"] == 1
                pull_item = data["locations"][0]["items"][0]

                # Verify all required fields are present
                assert pull_item["item_title"] == "Complete Details Book"
                assert pull_item["item_author"] == "Complete Author"
                assert pull_item["call_number"] == "REF 100.5 COM"
                assert pull_item["shelf_location"] == "Reference R-3"
                assert pull_item["barcode"] == "BARCODE-98765"
                assert pull_item["patron_name"] == "Fields Patron"
                assert pull_item["patron_library_card"] == "LIB-12345"
                assert pull_item["hold_expires_at"] is not None
                assert pull_item["hold_created_at"] is not None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_only_ready_holds_included(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that only holds with 'ready' status are included in pull list."""
        from app.core.security import hash_password

        # Create patron
        patron = User(
            email="pulllist_ready_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Ready",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create items for different hold statuses
        item_ready = CatalogItem(
            title="Ready Item",
            author="Ready Author",
            status=ItemStatus.on_hold,
            location="Shelf A",
        )
        item_pending = CatalogItem(
            title="Pending Item",
            author="Pending Author",
            status=ItemStatus.checked_out,
            location="Shelf B",
        )
        item_fulfilled = CatalogItem(
            title="Fulfilled Item",
            author="Fulfilled Author",
            status=ItemStatus.checked_out,
            location="Shelf C",
        )
        test_db.add_all([item_ready, item_pending, item_fulfilled])
        await test_db.commit()
        await test_db.refresh(item_ready)
        await test_db.refresh(item_pending)
        await test_db.refresh(item_fulfilled)

        now = datetime.now(timezone.utc)

        # Create holds with different statuses
        hold_ready = Hold(
            user_id=patron.id,
            item_id=item_ready.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        hold_pending = Hold(
            user_id=patron.id,
            item_id=item_pending.id,
            status=HoldStatus.pending,
            position=1,
            created_at=now,
        )
        hold_fulfilled = Hold(
            user_id=patron.id,
            item_id=item_fulfilled.id,
            status=HoldStatus.fulfilled,
            position=1,
            created_at=now - timedelta(days=1),
        )
        test_db.add_all([hold_ready, hold_pending, hold_fulfilled])
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()

                # Only the ready hold should be included
                assert data["total_items"] == 1
                assert data["locations"][0]["items"][0]["item_title"] == "Ready Item"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_items_without_location_grouped_as_unassigned(
        self, test_db: AsyncSession, test_staff: User
    ):
        """Test that items without location are grouped under 'Unassigned'."""
        from app.core.security import hash_password

        # Create patron
        patron = User(
            email="pulllist_unassigned_patron@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Unassigned",
            last_name="Patron",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)

        # Create item without location
        item_no_loc = CatalogItem(
            title="No Location Book",
            author="No Loc Author",
            status=ItemStatus.on_hold,
            location=None,  # No location set
            call_number="NO LOC",
        )
        test_db.add(item_no_loc)
        await test_db.commit()
        await test_db.refresh(item_no_loc)

        now = datetime.now(timezone.utc)
        hold = Hold(
            user_id=patron.id,
            item_id=item_no_loc.id,
            status=HoldStatus.ready,
            position=1,
            created_at=now,
            notified_at=now,
            expires_at=now + timedelta(days=7),
        )
        test_db.add(hold)
        await test_db.commit()

        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.api.v1.auth import get_current_user

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/circulation/holds/pull-list")
                assert response.status_code == 200
                data = response.json()

                assert data["total_items"] == 1
                assert data["locations"][0]["location"] == "Unassigned"
                assert data["locations"][0]["items"][0]["shelf_location"] is None
        finally:
            app.dependency_overrides.clear()
