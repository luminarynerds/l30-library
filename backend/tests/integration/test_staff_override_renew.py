# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the staff override-renew endpoint.

POST /api/v1/staff/override-renew/{checkout_id}

Policy (set by the library): staff may renew on behalf of any patron and may
override the per-patron renewal cap and the overdue-grace cutoff. The hold
queue is intentionally NOT overridable: if another patron is waiting, the
renewal is refused so the hold is honored.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient, ASGITransport

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def _reset_redis_client():
    """Reset the lazily-cached global redis client so each test binds it to its
    own event loop (avoids 'attached to a different loop' flakes)."""
    import app.core.cache as cache

    cache.redis_client = None
    yield
    cache.redis_client = None


@pytest.fixture
async def staff_user(test_db):
    from app.core.security import hash_password

    user = User(
        email="override_renew_staff@l30.org",
        password_hash=hash_password("StaffPw123!"),
        first_name="Renew",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron(test_db):
    from app.core.security import hash_password

    user = User(
        email="override_renew_patron@example.test",
        password_hash=hash_password("PatronPw123!"),
        first_name="Renew",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LC10101010",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_client(test_db, staff_user):
    """AsyncClient authenticated as staff via dependency override."""
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return staff_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


async def _make_checkout(
    test_db,
    patron,
    *,
    barcode,
    renewal_count=0,
    status=CheckoutStatus.active,
    overdue=False,
    with_hold=False,
):
    item = CatalogItem(
        title="Override Renew Book",
        author="Test Author",
        isbn=f"978{barcode}",
        barcode=barcode,
        status=ItemStatus.checked_out,
        location="Test Shelf",
    )
    test_db.add(item)
    await test_db.flush()

    now = datetime.now(timezone.utc)
    due = now - timedelta(days=7) if overdue else now + timedelta(days=7)
    checkout = Checkout(
        user_id=patron.id,
        item_id=item.id,
        status=status,
        checked_out_at=now - timedelta(days=21 if overdue else 1),
        due_date=due,
        renewal_count=renewal_count,
    )
    test_db.add(checkout)

    if with_hold:
        from app.core.security import hash_password

        other = User(
            email=f"waiter_{barcode}@example.test",
            password_hash=hash_password("WaiterPw123!"),
            first_name="Other",
            last_name="Waiter",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            library_card=f"LCW{barcode}",
        )
        test_db.add(other)
        await test_db.flush()
        test_db.add(
            Hold(user_id=other.id, item_id=item.id, status=HoldStatus.pending, position=1)
        )

    await test_db.commit()
    await test_db.refresh(checkout)
    return item, checkout


@pytest.mark.integration
class TestStaffOverrideRenew:
    async def test_basic_renew(self, staff_client, test_db, patron):
        _, checkout = await _make_checkout(test_db, patron, barcode="ROR001")
        resp = await staff_client.post(f"/api/v1/staff/override-renew/{checkout.id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["renewal_count"] == 1

    async def test_overdue_renew_reactivates(self, staff_client, test_db, patron):
        _, checkout = await _make_checkout(
            test_db, patron, barcode="ROR002",
            status=CheckoutStatus.overdue, overdue=True,
        )
        resp = await staff_client.post(f"/api/v1/staff/override-renew/{checkout.id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "active"
        assert data["renewal_count"] == 1

    async def test_cap_blocks_without_override(self, staff_client, test_db, patron):
        _, checkout = await _make_checkout(
            test_db, patron, barcode="ROR003", renewal_count=99,
        )
        resp = await staff_client.post(f"/api/v1/staff/override-renew/{checkout.id}")
        # QUOTA_EXCEEDED -> 422
        assert resp.status_code == 422, resp.text

    async def test_cap_renewed_with_override(self, staff_client, test_db, patron):
        _, checkout = await _make_checkout(
            test_db, patron, barcode="ROR004", renewal_count=99,
        )
        resp = await staff_client.post(
            f"/api/v1/staff/override-renew/{checkout.id}?override=true"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["renewal_count"] == 100

    async def test_hold_still_blocks_even_with_override(self, staff_client, test_db, patron):
        _, checkout = await _make_checkout(
            test_db, patron, barcode="ROR005", with_hold=True,
        )
        resp = await staff_client.post(
            f"/api/v1/staff/override-renew/{checkout.id}?override=true"
        )
        # Hold queue is not overridable: another patron is waiting -> 409.
        assert resp.status_code == 409, resp.text
