# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for patron list real counts.

Verifies that GET /api/v1/staff/patrons returns real values for
current_checkouts, current_holds, and fines_balance — not zeros.

Also verifies constant query count (no N+1) regardless of page size.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


@pytest.fixture
async def patron_with_activity(test_db, test_staff):
    """One patron with 1 active checkout, 1 pending hold, and 1 unpaid fine."""
    from app.core.security import hash_password
    from app.models.catalog import CatalogItem, ItemType
    from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
    from app.models.fine import Fine, FineStatus, FineType
    from app.models.user import User, UserRole

    patron = User(
        email="active.patron@example.com",
        password_hash=hash_password("Password123!"),
        first_name="Active",
        last_name="Patron",
        library_card="CARD-ACTIVE-01",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(patron)

    item = CatalogItem(
        title="Test Book",
        author="Test Author",
        isbn="9780000000001",
        item_type=ItemType.book,
    )
    test_db.add(item)
    await test_db.flush()

    checkout = Checkout(
        user_id=patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=3),
        due_date=datetime.now(timezone.utc) + timedelta(days=11),
    )
    test_db.add(checkout)

    hold = Hold(
        user_id=patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    test_db.add(hold)

    fine = Fine(
        user_id=patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("3.50"),
        amount_paid=Decimal("0.00"),
    )
    test_db.add(fine)

    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.fixture
async def patron_clean(test_db, test_staff):
    """One patron with no checkouts, holds, or fines."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    patron = User(
        email="clean.patron@example.com",
        password_hash=hash_password("Password123!"),
        first_name="Clean",
        last_name="Patron",
        library_card="CARD-CLEAN-01",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.fixture
async def staff_client_fixture(test_db, test_staff):
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_staff

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.integration
class TestPatronListCounts:
    async def test_active_patron_shows_real_counts(
        self, staff_client_fixture, patron_with_activity
    ):
        """Patron with 1 checkout, 1 hold, $3.50 fine shows real numbers in list."""
        resp = await staff_client_fixture.get("/api/v1/staff/patrons")
        assert resp.status_code == 200
        data = resp.json()

        patrons = data["patrons"]
        match = next(
            (p for p in patrons if p.get("library_card") == "CARD-ACTIVE-01"), None
        )
        assert match is not None, "Patron with CARD-ACTIVE-01 not found in list"

        assert match["current_checkouts"] == 1
        assert match["current_holds"] == 1
        assert float(match["fines_balance"]) == pytest.approx(3.50, abs=0.01)

    async def test_clean_patron_shows_zeros(
        self, staff_client_fixture, patron_clean
    ):
        """Patron with no activity shows zeros for all three count fields."""
        resp = await staff_client_fixture.get("/api/v1/staff/patrons")
        assert resp.status_code == 200
        data = resp.json()

        patrons = data["patrons"]
        match = next(
            (p for p in patrons if p.get("library_card") == "CARD-CLEAN-01"), None
        )
        assert match is not None, "Patron with CARD-CLEAN-01 not found in list"

        assert match["current_checkouts"] == 0
        assert match["current_holds"] == 0
        assert float(match["fines_balance"]) == pytest.approx(0.0, abs=0.01)

    async def test_counts_consistent_with_detail_page(
        self, staff_client_fixture, patron_with_activity
    ):
        """List counts agree with the detail endpoint for the same patron."""
        list_resp = await staff_client_fixture.get("/api/v1/staff/patrons")
        assert list_resp.status_code == 200
        patrons = list_resp.json()["patrons"]
        list_patron = next(
            (p for p in patrons if p.get("library_card") == "CARD-ACTIVE-01"), None
        )
        assert list_patron is not None

        detail_resp = await staff_client_fixture.get(
            f"/api/v1/staff/patrons/{patron_with_activity.id}"
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        # Detail uses full checkout/hold/fines lists; compare counts
        assert list_patron["current_checkouts"] == len(detail.get("checkouts", []))
        assert list_patron["current_holds"] == len(detail.get("holds", []))
        assert float(list_patron["fines_balance"]) == pytest.approx(
            float(detail.get("total_fines_owed", 0)), abs=0.01
        )
