# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD tests for account-circulation backend hardening.

Task 1: patron fines endpoint must not leak staff-internal fields
Task 2: active-borrows list must not expose access_token
Task 3: checkout history must paginate at DB level, not load all rows
Task 4: concurrent overdue-fine creation must be idempotent (money path)
Task 5: MetisLib upstream timeout in borrow-history must not 500 the whole response
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


def _make_user(user_id=42):
    from app.models.user import UserRole
    u = MagicMock()
    u.id = user_id
    u.email = "patron{}@test.example".format(user_id)
    u.role = UserRole.PATRON
    u.is_active = True
    u.track_reading_history = True
    u.email_verified = True
    return u


# ===========================================================================
# Task 1: patron fines must not expose staff-internal fields
# ===========================================================================

class TestPatronFinePrivacy:

    @pytest.mark.asyncio
    async def test_patron_fines_excludes_staff_fields(self, test_db, test_patron, test_staff):
        from httpx import AsyncClient, ASGITransport
        from app.core.database import get_db
        from app.api.v1.auth.helpers import get_current_user
        from app.main import app
        from app.models.fine import Fine, FineStatus, FineType

        # balance is a @property on the model (not a column), don't pass it
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("1.50"),
            amount_paid=Decimal("0.00"),
            description="Overdue by 3 day(s)",
            notes="Staff note: patron was out of town",
            waived_by_id=test_staff.id,
        )
        test_db.add(fine)
        await test_db.commit()

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_patron

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.state.setup_complete = True

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/circulation/fines")
            assert resp.status_code == 200, "Expected 200, got {}: {}".format(
                resp.status_code, resp.text
            )
            data = resp.json()
            items = data.get("data", data.get("fines", data.get("items", [])))
            assert len(items) >= 1, "Expected at least 1 fine, got: {}".format(data)
            for item in items:
                assert "notes" not in item, "notes must not be in patron fines response"
                assert "waived_by_id" not in item, "waived_by_id must not be in patron fines response"
                assert "patron_email" not in item, "patron_email must not be in patron fines response"
                assert "patron_name" not in item, "patron_name must not be in patron fines response"
                assert "patron_library_card" not in item, "patron_library_card must not be in patron fines response"
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)


# ===========================================================================
# Task 2: active borrows list must not expose access_token
# ===========================================================================

class TestIndieBorrowsNoTokenInList:

    @pytest.mark.asyncio
    async def test_active_borrows_list_excludes_access_token(self):
        from app.api.v1.indie_lending import get_active_borrows

        user = _make_user()

        fake_borrows = [
            {
                "id": 1,
                "ebook_id": 101,
                "indie_ebook_id": 1,
                "ebook_title": "Test Book",
                "ebook_cover_url": None,
                "author_pen_name": "Author",
                "borrowed_at": datetime.now(timezone.utc).isoformat(),
                "due_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
                "access_token": "SUPERSECRET_TOKEN_abc123",
                "status": "active",
                "download_count": 0,
                "max_downloads": 3,
            }
        ]

        mock_service = MagicMock()
        mock_service.get_active_borrows = AsyncMock(return_value=fake_borrows)
        db = AsyncMock()

        with patch("app.api.v1.indie_lending.get_lending_service", return_value=mock_service):
            result = await get_active_borrows(current_user=user, db=db)

        assert isinstance(result, list) and len(result) == 1
        item = result[0]
        if hasattr(item, "model_dump"):
            item_dict = item.model_dump()
        elif hasattr(item, "dict"):
            item_dict = item.dict()
        else:
            item_dict = item if isinstance(item, dict) else dict(item)

        assert "access_token" not in item_dict, (
            "access_token must not appear in active-borrows list; got keys: {}".format(
                list(item_dict)
            )
        )


# ===========================================================================
# Task 3: checkout history must paginate at DB level
# ===========================================================================

class TestCheckoutHistoryPagination:

    @pytest.mark.asyncio
    async def test_history_returns_paginated_subset(self, test_db, test_patron):
        from httpx import AsyncClient, ASGITransport
        from app.core.database import get_db
        from app.api.v1.auth.helpers import get_current_user
        from app.main import app
        from app.models.catalog import CatalogItem, ItemStatus
        from app.models.circulation import Checkout, CheckoutStatus
        from sqlalchemy import select

        # Enable history tracking for this patron
        test_patron.track_reading_history = True
        await test_db.commit()
        await test_db.refresh(test_patron)
        now = datetime.now()
        for i in range(25):
            item = CatalogItem(title="HBk{}".format(i), status=ItemStatus.available)
            test_db.add(item)
        await test_db.flush()
        items_result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.title.like("HBk%"))
        )
        db_items = items_result.scalars().all()

        for i, it in enumerate(db_items):
            co = Checkout(
                user_id=test_patron.id,
                item_id=it.id,
                status=CheckoutStatus.returned,
                checked_out_at=now - timedelta(days=i + 1),
                due_date=now - timedelta(days=i),
                returned_at=now - timedelta(days=i),
            )
            test_db.add(co)
        await test_db.commit()

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_patron

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.state.setup_complete = True

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/circulation/history",
                    params={"page": 1, "page_size": 10},
                )
            assert resp.status_code == 200, "Expected 200, got {}: {}".format(
                resp.status_code, resp.text
            )
            data = resp.json()
            items_returned = data.get("data", data.get("items", []))
            pagination = data.get("pagination", data)
            total = pagination.get("total", data.get("total", None))

            assert len(items_returned) == 10, (
                "Expected 10 items on page 1 (per_page=10), got {}".format(len(items_returned))
            )
            assert total is not None and total >= 25, (
                "Expected total >= 25, got {}".format(total)
            )
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)


# ===========================================================================
# Task 4: overdue fine creation must be idempotent under repeated calls
# ===========================================================================

class TestOverdueFineIdempotency:
    """
    Calling check_and_create_overdue_fine twice for the same overdue checkout
    must produce at most one Fine row (app-layer guard).

    In production, the Postgres partial unique index ix_fines_idempotent on
    (checkout_id, fine_type, date) provides a second DB-level safety net.
    This test validates the app-layer SELECT-before-INSERT guard works in both
    SQLite (test harness) and Postgres (prod).
    """

    @pytest.mark.asyncio
    async def test_fine_creation_idempotent_on_repeat_call(
        self, test_db, test_patron, test_catalog_item
    ):
        from sqlalchemy import select
        from app.models.circulation import Checkout, CheckoutStatus
        from app.models.fine import Fine
        from app.services.fine_service import check_and_create_overdue_fine

        now = datetime.now(timezone.utc)
        checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=now - timedelta(days=10),
            due_date=now - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)

        await check_and_create_overdue_fine(checkout, test_db, user=test_patron)
        await test_db.commit()

        await check_and_create_overdue_fine(checkout, test_db, user=test_patron)
        await test_db.commit()

        result = await test_db.execute(
            select(Fine).where(Fine.checkout_id == checkout.id)
        )
        all_fines = result.scalars().all()
        assert len(all_fines) <= 1, (
            "Expected at most 1 fine for checkout {}, got {}".format(checkout.id, len(all_fines))
        )


# ===========================================================================
# Task 5: borrow history must not 500 when one MetisLib slot times out
# ===========================================================================

class TestBorrowHistoryResilient:

    @pytest.mark.asyncio
    async def test_borrow_history_degrades_on_upstream_timeout(self):
        import httpx
        from app.api.v1.indie_lending import get_borrow_history

        user = _make_user()
        now = datetime.now(timezone.utc)

        borrow_ok = MagicMock()
        borrow_ok.id = 1
        borrow_ok.ebook_id = 1
        borrow_ok.status = "returned"
        borrow_ok.borrowed_at = now - timedelta(days=30)
        borrow_ok.returned_at = now - timedelta(days=16)
        borrow_ok.due_at = now - timedelta(days=9)
        borrow_ok.rating = None
        ebook_ok = MagicMock()
        ebook_ok.metislib_ebook_id = 101
        borrow_ok.ebook = ebook_ok

        borrow_timeout = MagicMock()
        borrow_timeout.id = 2
        borrow_timeout.ebook_id = 2
        borrow_timeout.status = "returned"
        borrow_timeout.borrowed_at = now - timedelta(days=60)
        borrow_timeout.returned_at = now - timedelta(days=46)
        borrow_timeout.due_at = now - timedelta(days=39)
        borrow_timeout.rating = None
        ebook_timeout = MagicMock()
        ebook_timeout.metislib_ebook_id = 202
        borrow_timeout.ebook = ebook_timeout

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_borrows_result = MagicMock()
        mock_borrows_result.scalars.return_value.all.return_value = [borrow_ok, borrow_timeout]

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[mock_count_result, mock_borrows_result])

        async def _get_ebook_with_timeout(ebook_id, entry_type=None):
            if ebook_id == 202:
                raise httpx.TimeoutException("upstream timeout")
            return {"title": "Good Book", "cover_url": None, "author_name": "Author"}

        mock_client = MagicMock()
        mock_client.get_ebook = _get_ebook_with_timeout

        with patch("app.services.metislib_client.get_metislib_client", return_value=mock_client):
            result = await get_borrow_history(page=1, per_page=20, current_user=user, db=db)

        if hasattr(result, "items"):
            items = result.items
        else:
            items = result.get("items", [])

        assert isinstance(items, list), "history endpoint must return a list of items"
        titles = [
            (i.ebook_title if hasattr(i, "ebook_title") else i.get("ebook_title", ""))
            for i in items
        ]
        assert "Good Book" in titles, (
            "Good Book (non-failing ebook) must appear in response; got: {}".format(titles)
        )
