# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD Tests for Circulation Pagination

Tests pagination for circulation endpoints (checkouts, holds, fines).
These tests follow TDD principles - write tests first, implement pagination second.

Contract notes (see app/core/pagination.py + app/schemas/common.py):
  - Query param is ``page_size`` (not ``per_page``); FastAPI silently drops
    unrecognized query params, so passing ``per_page`` is a no-op and the
    endpoint falls back to its default.
  - Default page size is 20 (PaginationDefaults.DEFAULT_PAGE_SIZE); max is
    100 (PaginationDefaults.MAX_PAGE_SIZE).
  - Response envelope is ``{"data": [...], "pagination": {...}}``, and the
    pagination block uses ``per_page``/``total``/``total_pages`` (not a flat
    ``items``/``pages`` at the top level).
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType


class TestCheckoutsPagination:
    """Test checkouts endpoint pagination"""

    @pytest.mark.asyncio
    async def test_get_checkouts_returns_paginated_results(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that GET /checkouts returns paginated results"""
        # Create multiple checkouts
        items = []
        for i in range(15):
            item = CatalogItem(
                title=f"Book {i+1}",
                status=ItemStatus.checked_out,
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        checkouts = []
        for item in items:
            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
            checkouts.append(checkout)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get checkouts with pagination
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        pagination = data["pagination"]
        assert len(data["data"]) == 10
        assert pagination["total"] == 15
        assert pagination["page"] == 1
        assert pagination["total_pages"] == 2

    @pytest.mark.asyncio
    async def test_checkouts_default_page_1_per_page_20(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that checkouts default to page=1, page_size=20"""
        # Create some checkouts
        for i in range(5):
            item = CatalogItem(title=f"Book {i+1}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get checkouts without pagination params
        response = await client.get(
            "/api/v1/circulation/checkouts",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 20
        assert len(data["data"]) == 5

    @pytest.mark.asyncio
    async def test_checkouts_max_per_page_is_100(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that checkouts max page_size is 100"""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Try to request more than 100 per page -- page_size is validated
        # (ge=1, le=100) by PaginationParams, so exceeding it is a 422,
        # not a silent clamp.
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page_size": 200},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_checkouts_handles_page_beyond_total_pages(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that requesting page beyond total returns empty results"""
        # Create 5 checkouts
        for i in range(5):
            item = CatalogItem(title=f"Book {i+1}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Request page 10 when there's only 1 page
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page": 10, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["page"] == 10


class TestHoldsPagination:
    """Test holds endpoint pagination"""

    @pytest.mark.asyncio
    async def test_get_holds_returns_paginated_results(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that GET /holds returns paginated results"""
        # Create multiple holds
        items = []
        for i in range(20):
            item = CatalogItem(
                title=f"Book {i+1}",
                status=ItemStatus.on_hold,
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        holds = []
        for idx, item in enumerate(items):
            hold = Hold(
                user_id=test_patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=idx + 1,
                created_at=datetime.now(),
            )
            test_db.add(hold)
            holds.append(hold)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get first page
        response = await client.get(
            "/api/v1/circulation/holds",
            params={"page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["total"] == 20
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_pages"] == 2

        # Get second page
        response = await client.get(
            "/api/v1/circulation/holds",
            params={"page": 2, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["page"] == 2

    @pytest.mark.asyncio
    async def test_holds_returns_total_count(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that holds endpoint returns correct total count"""
        # Create 7 holds
        for i in range(7):
            item = CatalogItem(title=f"Book {i+1}", status=ItemStatus.on_hold)
            test_db.add(item)
            await test_db.commit()

            hold = Hold(
                user_id=test_patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
            )
            test_db.add(hold)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get holds
        response = await client.get(
            "/api/v1/circulation/holds",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 7


class TestFinesPagination:
    """Test fines endpoint pagination"""

    @pytest.mark.asyncio
    async def test_get_fines_returns_paginated_results(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that GET /fines returns paginated results"""
        # Create multiple fines
        fines = []
        for i in range(12):
            fine = Fine(
                user_id=test_patron.id,
                fine_type=FineType.overdue,
                status=FineStatus.unpaid,
                amount=Decimal("5.00"),
                amount_paid=Decimal("0.00"),
                description=f"Fine {i+1}",
                created_at=datetime.now(),
            )
            test_db.add(fine)
            fines.append(fine)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get fines with pagination
        response = await client.get(
            "/api/v1/circulation/fines",
            params={"page": 1, "page_size": 5},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["total"] == 12
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_fines_default_pagination(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test fines default pagination parameters"""
        # Create some fines
        for i in range(3):
            fine = Fine(
                user_id=test_patron.id,
                fine_type=FineType.lost_item,
                status=FineStatus.unpaid,
                amount=Decimal("25.00"),
                amount_paid=Decimal("0.00"),
                description=f"Lost item fine {i+1}",
            )
            test_db.add(fine)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get fines without pagination params
        response = await client.get(
            "/api/v1/circulation/fines",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 20


class TestPaginationMetadata:
    """Test pagination metadata"""

    @pytest.mark.asyncio
    async def test_returns_correct_page_metadata(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that correct pagination metadata is returned"""
        # Create 25 checkouts
        for i in range(25):
            item = CatalogItem(title=f"Book {i+1}", status=ItemStatus.checked_out)
            test_db.add(item)
            await test_db.commit()

            checkout = Checkout(
                user_id=test_patron.id,
                item_id=item.id,
                status=CheckoutStatus.active,
                checked_out_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=21),
            )
            test_db.add(checkout)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get page 2 with 10 per page
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page": 2, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]

        # Verify metadata
        assert pagination["total"] == 25
        assert pagination["page"] == 2
        assert pagination["per_page"] == 10
        assert pagination["total_pages"] == 3  # ceil(25/10)
        assert len(data["data"]) == 10

    @pytest.mark.asyncio
    async def test_last_page_has_remaining_items(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that last page has correct number of remaining items"""
        # Create 23 holds
        for i in range(23):
            item = CatalogItem(title=f"Book {i+1}", status=ItemStatus.on_hold)
            test_db.add(item)
            await test_db.commit()

            hold = Hold(
                user_id=test_patron.id,
                item_id=item.id,
                status=HoldStatus.pending,
                position=i + 1,
            )
            test_db.add(hold)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Get last page (page 3, 10 per page)
        response = await client.get(
            "/api/v1/circulation/holds",
            params={"page": 3, "page_size": 10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Last page should have 3 items (23 % 10)
        assert len(data["data"]) == 3
        assert data["pagination"]["total"] == 23
        assert data["pagination"]["page"] == 3
        assert data["pagination"]["total_pages"] == 3


class TestPaginationValidation:
    """Test pagination parameter validation"""

    @pytest.mark.asyncio
    async def test_rejects_invalid_page_number(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that invalid page numbers are rejected"""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Try page 0
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page": 0},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422

        # Try negative page
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page": -1},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_invalid_per_page(
        self, test_db: AsyncSession, test_patron: User, client
    ):
        """Test that invalid page_size values are rejected"""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Try page_size 0
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page_size": 0},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422

        # Try negative page_size
        response = await client.get(
            "/api/v1/circulation/checkouts",
            params={"page_size": -10},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422
