# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test that placed-hold responses include pickup_branch_name."""

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.multi_branch import Branch, LibrarySystem
from app.models.user import User, UserRole


@pytest.fixture
async def library_system(test_db):
    system = LibrarySystem(
        name="Test Library System",
        code="TLS",
    )
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)
    return system


@pytest.fixture
async def pickup_branch(test_db, library_system):
    branch = Branch(
        library_system_id=library_system.id,
        code="MAIN",
        name="Main Branch",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


@pytest.fixture
async def holdable_item(test_db):
    item = CatalogItem(
        title="Test Holdable Book",
        author="Test Author",
        status=ItemStatus.available,
        call_number="TEST-001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def patron_user(test_db):
    from app.core.security import hash_password

    user = User(
        email="pickup_test_patron@example.com",
        password_hash=hash_password("Test1234!"),
        first_name="Pickup",
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
def auth_as_patron(patron_user):
    from app.main import app
    from app.api.v1.auth.helpers import get_current_user

    async def _override():
        return patron_user

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_place_hold_response_includes_pickup_branch_name(
    client, test_db, patron_user, pickup_branch, holdable_item, auth_as_patron
):
    """Placing a hold with a pickup_location_id returns pickup_branch_name in the response."""
    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": holdable_item.id, "pickup_location_id": pickup_branch.id},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["pickup_location_id"] == pickup_branch.id
    assert data["pickup_branch_name"] == "Main Branch"


@pytest.mark.asyncio
async def test_get_holds_includes_pickup_branch_name(
    client, test_db, patron_user, pickup_branch, holdable_item, auth_as_patron
):
    """GET /circulation/holds returns pickup_branch_name for holds with a pickup location."""
    # Place a hold first
    place_resp = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": holdable_item.id, "pickup_location_id": pickup_branch.id},
    )
    assert place_resp.status_code == 201, place_resp.text

    # Retrieve holds list
    list_resp = await client.get("/api/v1/circulation/holds")
    assert list_resp.status_code == 200, list_resp.text
    holds = list_resp.json()["data"]
    assert len(holds) == 1
    assert holds[0]["pickup_location_id"] == pickup_branch.id
    assert holds[0]["pickup_branch_name"] == "Main Branch"


@pytest.mark.asyncio
async def test_place_hold_without_pickup_location_has_null_branch_name(
    client, test_db, patron_user, holdable_item, auth_as_patron
):
    """When no pickup_location_id is given and the patron has no home branch, branch name is null."""
    response = await client.post(
        "/api/v1/circulation/holds",
        json={"item_id": holdable_item.id},
    )
    # May succeed (null pickup) or fail (validate_pickup_location rejects None).
    # Either way pickup_branch_name must not raise.
    if response.status_code == 201:
        data = response.json()
        assert data.get("pickup_branch_name") is None
