# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for browse.py handler fixes (2026-05-17).

Covers:
- Bug 2: GET /api/v1/catalog/barcode/{bc} 500'd on every item
  (missing selectinload on .images + undefined item_id var).
- Bug 3: visibility check rejected super_admin/director on uncataloged items.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.auth.helpers import get_optional_user
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.inventory import ItemCopy
from app.models.user import User, UserRole


async def _client_as(test_db, user):
    """Yield an AsyncClient with get_optional_user overridden to return `user`."""
    async def override_get_db():
        yield test_db

    async def override_get_optional_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_user] = override_get_optional_user
    app.state.setup_complete = True

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _make_user(test_db, role: UserRole, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name=role.value,
        role=role,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def cataloged_book(test_db):
    item = CatalogItem(
        title="Barcode Handler Fix - Cataloged",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        barcode="TEST-BARCODE-CATALOGED-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def uncataloged_book(test_db):
    item = CatalogItem(
        title="Barcode Handler Fix - Uncataloged",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.UNCATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        barcode="TEST-BARCODE-UNCATALOGED-002",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def in_progress_book(test_db):
    item = CatalogItem(
        title="Browse Handler - In Progress",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.IN_PROGRESS,
        sensitivity_level=SensitivityLevel.PUBLIC,
        barcode="TEST-BARCODE-INPROGRESS-003",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


# ------------------- Bug 2: barcode handler regression -------------------


@pytest.mark.asyncio
async def test_barcode_lookup_cataloged_returns_200_with_images(test_db, cataloged_book):
    """Public hit on /catalog/barcode/{bc} for a cataloged item returns full response."""
    ac = await _client_as(test_db, None)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{cataloged_book.barcode}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["title"] == cataloged_book.title
        # .images must serialize without MissingGreenlet
        assert "images" in data
        assert data["images"] == []
    finally:
        app.dependency_overrides.clear()


# ------------- Bug 3: super_admin/director visibility -------------


@pytest.mark.asyncio
async def test_barcode_lookup_uncataloged_404_for_anonymous(test_db, uncataloged_book):
    ac = await _client_as(test_db, None)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{uncataloged_book.barcode}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,email",
    [
        (UserRole.STAFF, "staff@browse-fix.test"),
        (UserRole.ADMIN, "admin@browse-fix.test"),
        (UserRole.SUPER_ADMIN, "super@browse-fix.test"),
        (UserRole.DIRECTOR, "director@browse-fix.test"),
    ],
)
async def test_barcode_lookup_uncataloged_200_for_staff_or_above(
    test_db, uncataloged_book, role, email
):
    """staff/admin/super_admin/director can all see uncataloged items by barcode."""
    user = await _make_user(test_db, role, email)
    ac = await _client_as(test_db, user)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{uncataloged_book.barcode}")
        assert response.status_code == 200, f"role={role.value}: {response.text}"
        assert response.json()["title"] == uncataloged_book.title
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("path_template", ["/api/v1/catalog/items/{id}", "/api/v1/catalog/{id}"])
async def test_get_by_id_uncataloged_200_for_super_admin(test_db, uncataloged_book, path_template):
    """GET /catalog/items/{id} AND legacy /catalog/{id} both 200 for super_admin."""
    user = await _make_user(
        test_db, UserRole.SUPER_ADMIN, f"super-{path_template.count('items')}@browse-fix.test"
    )
    ac = await _client_as(test_db, user)
    try:
        async with ac as client:
            response = await client.get(path_template.format(id=uncataloged_book.id))
        assert response.status_code == 200, f"path={path_template}: {response.text}"
        assert response.json()["title"] == uncataloged_book.title
    finally:
        app.dependency_overrides.clear()


# ------------- Follow-up: in_progress also hidden from public -------------


@pytest.mark.asyncio
async def test_barcode_lookup_in_progress_404_for_anonymous(test_db, in_progress_book):
    """in_progress items must not be visible to anonymous users (consistency with /catalog list)."""
    ac = await _client_as(test_db, None)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{in_progress_book.barcode}")
        assert response.status_code == 404, response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,email",
    [
        (UserRole.STAFF, "staff-ip@browse-fix.test"),
        (UserRole.ADMIN, "admin-ip@browse-fix.test"),
        (UserRole.SUPER_ADMIN, "super-ip@browse-fix.test"),
        (UserRole.DIRECTOR, "director-ip@browse-fix.test"),
    ],
)
async def test_barcode_lookup_in_progress_200_for_staff_or_above(
    test_db, in_progress_book, role, email
):
    user = await _make_user(test_db, role, email)
    ac = await _client_as(test_db, user)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{in_progress_book.barcode}")
        assert response.status_code == 200, f"role={role.value}: {response.text}"
        assert response.json()["title"] == in_progress_book.title
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("path_template", ["/api/v1/catalog/items/{id}", "/api/v1/catalog/{id}"])
async def test_get_by_id_in_progress_404_for_anonymous(test_db, in_progress_book, path_template):
    ac = await _client_as(test_db, None)
    try:
        async with ac as client:
            response = await client.get(path_template.format(id=in_progress_book.id))
        assert response.status_code == 404, f"path={path_template}: {response.text}"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("path_template", ["/api/v1/catalog/items/{id}", "/api/v1/catalog/{id}"])
async def test_get_by_id_in_progress_200_for_super_admin(test_db, in_progress_book, path_template):
    user = await _make_user(
        test_db, UserRole.SUPER_ADMIN, f"super-ip-{path_template.count(chr(0x69)+chr(0x74)+chr(0x65)+chr(0x6d)+chr(0x73))}@browse-fix.test"
    )
    ac = await _client_as(test_db, user)
    try:
        async with ac as client:
            response = await client.get(path_template.format(id=in_progress_book.id))
        assert response.status_code == 200, f"path={path_template}: {response.text}"
        assert response.json()["title"] == in_progress_book.title
    finally:
        app.dependency_overrides.clear()


# ----- Item-copy barcode fallback (2026-05-19) -----
# CatalogItem.barcode is only populated for equipment/kits; per-copy physical
# barcodes (which is what gets scanned) live on ItemCopy.barcode. Before this
# fix, /catalog/barcode/{copy_barcode} 404'd for every regular book.


@pytest.fixture
async def cataloged_book_with_copy_barcode(test_db):
    """A cataloged book whose CatalogItem.barcode is NULL but has an
    ItemCopy with a barcode -- the common shape for shelved books."""
    item = CatalogItem(
        title="Barcode Handler Fix - Copy-Barcode Book",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        barcode=None,
    )
    test_db.add(item)
    await test_db.flush()
    copy = ItemCopy(
        catalog_item_id=item.id,
        barcode="TEST-COPY-BARCODE-004",
        copy_number=1,
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(item)
    return item, copy


@pytest.mark.asyncio
async def test_barcode_lookup_falls_back_to_item_copy_barcode(
    test_db, cataloged_book_with_copy_barcode
):
    item, copy = cataloged_book_with_copy_barcode
    ac = await _client_as(test_db, None)
    try:
        async with ac as client:
            response = await client.get(f"/api/v1/catalog/barcode/{copy.barcode}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == item.id
        assert data["title"] == item.title
    finally:
        app.dependency_overrides.clear()

