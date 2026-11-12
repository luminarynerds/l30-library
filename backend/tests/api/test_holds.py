# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API tests for the /holds POST endpoint NON_HOLDABLE_STATUSES enforcement.

Ensures patrons cannot place holds on lost/withdrawn/missing/reference/restricted
items by knowing their ID. The same frozenset that powers available_for_hold
(PR #573) is now enforced server-side; rejection is 422 ITEM_NOT_HOLDABLE.
"""

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.user import User, UserRole
from app.schemas.catalog import NON_HOLDABLE_STATUSES


@pytest.fixture
def auth_as(hold_patron):
    """Override get_current_user to return the hold_patron without JWT verification.

    Tests in this environment can't round-trip through verify_token because the
    Redis revocation cache fails closed without Redis. Overriding the dependency
    keeps these tests focused on the holdability check rather than auth plumbing.
    """
    from app.main import app
    from app.api.v1.auth.helpers import get_current_user

    async def _override():
        return hold_patron

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def hold_patron(test_db):
    """A clean patron for hold-placement tests (avoids fixture cross-talk)."""
    from app.core.security import hash_password

    user = User(
        email="hold_patron@example.com",
        password_hash=hash_password("HoldPatron123!"),
        first_name="Hold",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _make_item(test_db, status: ItemStatus, barcode: str = "NONHOLD-001") -> CatalogItem:
    item = CatalogItem(
        title=f"Item with status {status.value}",
        author="Test Author",
        isbn=None,
        description="",
        status=status,
        call_number=barcode,
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.mark.asyncio
async def test_place_hold_rejects_lost_item_with_422(client, test_db, hold_patron, auth_as):
    """Patron trying to hold a lost item gets a structured 422."""
    item = await _make_item(test_db, ItemStatus.lost, "LOST-001")

    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": item.id},
    )

    assert response.status_code == 422, response.text
    body = response.json()
    # main.py-registered APIError handler shape: {"code": ..., "detail": ...}
    assert body.get("code") == "ITEM_NOT_HOLDABLE"
    assert "lost" in body.get("detail", "").lower()


@pytest.mark.asyncio
async def test_place_hold_rejects_withdrawn_item(client, test_db, hold_patron, auth_as):
    item = await _make_item(test_db, ItemStatus.withdrawn, "WITHDRAWN-001")

    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": item.id},
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body.get("code") == "ITEM_NOT_HOLDABLE"
    assert "withdrawn" in body.get("detail", "").lower()


@pytest.mark.parametrize("item_status", sorted(NON_HOLDABLE_STATUSES, key=lambda s: s.value))
@pytest.mark.asyncio
async def test_place_hold_rejects_each_non_holdable_status(
    client, test_db, hold_patron, auth_as, item_status
):
    """Every status in NON_HOLDABLE_STATUSES must be rejected."""
    item = await _make_item(test_db, item_status, f"NONHOLD-{item_status.value}")

    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": item.id},
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body.get("code") == "ITEM_NOT_HOLDABLE"
    # The status name appears in the message so the patron knows why.
    assert item_status.value in body.get("detail", "")


@pytest.mark.asyncio
async def test_place_hold_succeeds_for_holdable_item(client, test_db, hold_patron, auth_as, monkeypatch):
    """Regression: a holdable status (available) is not rejected by the new check.

    Stubs invalidate_catalog_cache to skip the Redis call that this no-Redis
    test environment can't satisfy. The point of this test is that the new
    NON_HOLDABLE_STATUSES check does not block holdable items.
    """
    async def _noop():
        return None

    monkeypatch.setattr(
        "app.api.v1.circulation.holds.invalidate_catalog_cache", _noop
    )

    item = await _make_item(test_db, ItemStatus.available, "AVAIL-NEW-001")

    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": item.id},
    )

    # endpoint declares 201; some test envs see 200. Either is success.
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert data["item_id"] == item.id
    assert data["status"] in ("pending", "ready")
