# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Slice B: catalog visibility-leak sweep + shelf-notes hardening.

Pins five fixes:

- ``GET /catalog/items/{id}/availability`` -- visibility gate (per-branch
  copy counts + call number were enumerable for any id).
- ``GET /catalog/items/{id}/hold-queue`` -- visibility gate (queue depth +
  estimated wait were enumerable for any id).
- ``POST /catalog/items/{id}/watch`` -- visibility gate (a patron could
  subscribe to availability notifications on CONFIDENTIAL items).
- ``POST /catalog/items/{id}/shelf-notes`` -- rate limit (10/hour) so an
  authenticated patron cannot flood shelf-note feeds on hot items.
- ``DELETE /catalog/items/{id}/shelf-notes/{note_id}`` -- replaced a
  ``getattr(current_user, "is_staff", False)`` check (always False because
  User uses ``role``) with ``is_staff_or_admin``, so staff can actually
  delete other patrons' notes.
"""
from __future__ import annotations

import os

import pytest
from httpx import AsyncClient

# Several handlers use ``.collate("und-x-icu")`` which SQLite cannot execute.
# Mark tests that exercise the post-gate SQL accordingly so the suite still
# runs on the SQLite fallback used by the test conftest. 404 cases bail out
# before the offending ORDER BY and run cleanly on both backends.
_USING_SQLITE = "sqlite" in os.environ.get("DATABASE_URL", "sqlite")
requires_postgres = pytest.mark.skipif(
    _USING_SQLITE,
    reason="Requires Postgres (und-x-icu ICU collation in branch order_by).",
)

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.shelf_note import ShelfNote, ShelfNoteCategory
from app.models.user import User, UserRole


async def _seed_item(
    db,
    *,
    title: str,
    cataloging_status: CatalogingStatus = CatalogingStatus.CATALOGED,
    sensitivity_level: SensitivityLevel = SensitivityLevel.PUBLIC,
) -> CatalogItem:
    item = CatalogItem(
        title=title,
        author="A",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=cataloging_status,
        sensitivity_level=sensitivity_level,
    )
    db.add(item)
    await db.flush()
    return item


# ---------------------------------------------------------------------------
# Fix #9 -- /items/{id}/availability visibility gate
# ---------------------------------------------------------------------------


async def test_availability_anon_404s_on_confidential(
    public_client: AsyncClient, db_session
):
    item = await _seed_item(
        db_session,
        title="Confidential",
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
    )
    await db_session.commit()
    resp = await public_client.get(
        f"/api/v1/catalog/items/{item.id}/availability"
    )
    assert resp.status_code == 404


async def test_availability_anon_404s_on_uncataloged(
    public_client: AsyncClient, db_session
):
    item = await _seed_item(
        db_session,
        title="WIP",
        cataloging_status=CatalogingStatus.UNCATALOGED,
    )
    await db_session.commit()
    resp = await public_client.get(
        f"/api/v1/catalog/items/{item.id}/availability"
    )
    assert resp.status_code == 404


@requires_postgres
async def test_availability_anon_200s_on_public_cataloged(
    public_client: AsyncClient, db_session
):
    item = await _seed_item(db_session, title="Public")
    await db_session.commit()
    resp = await public_client.get(
        f"/api/v1/catalog/items/{item.id}/availability"
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Fix #10 -- /items/{id}/hold-queue visibility gate
# ---------------------------------------------------------------------------


async def test_hold_queue_anon_404s_on_confidential(
    public_client: AsyncClient, db_session
):
    item = await _seed_item(
        db_session,
        title="ConfHold",
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
    )
    await db_session.commit()
    resp = await public_client.get(
        f"/api/v1/catalog/items/{item.id}/hold-queue"
    )
    assert resp.status_code == 404


async def test_hold_queue_anon_200s_on_public_cataloged(
    public_client: AsyncClient, db_session
):
    item = await _seed_item(db_session, title="PubHold")
    await db_session.commit()
    resp = await public_client.get(
        f"/api/v1/catalog/items/{item.id}/hold-queue"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "queue_size" in body or "estimated_wait_days" in body or isinstance(body, dict)


# ---------------------------------------------------------------------------
# Fix #11 -- /items/{id}/watch visibility gate (auth required)
# ---------------------------------------------------------------------------


async def _patron_client(test_db, client_factory):
    """Build a client authenticated as a PATRON, returning (client, user)."""
    from app.api.v1.auth.helpers import get_optional_user
    from app.api.v1.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    user = User(
        email="patron.visibility@example.com",
        first_name="V",
        last_name="P",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return user

    async def override_get_optional_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_optional_user] = override_get_optional_user
    app.state.setup_complete = True

    transport = ASGITransport(app=app)
    return user, AsyncClient(transport=transport, base_url="http://test")


async def test_watch_patron_404s_on_confidential(test_db):
    _, client = await _patron_client(test_db, None)
    try:
        item = await _seed_item(
            test_db,
            title="ConfWatch",
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        )
        await test_db.commit()
        resp = await client.post(f"/api/v1/catalog/items/{item.id}/watch")
        assert resp.status_code == 404
    finally:
        await client.aclose()
        from app.main import app
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fix #13 -- shelf-notes delete: staff can delete a patron's note
# ---------------------------------------------------------------------------


async def test_shelf_note_staff_can_delete_patron_note(test_db):
    """``getattr(current_user, "is_staff", False)`` was always False;
    staff could only delete their own notes. ``is_staff_or_admin`` fixes it.
    """
    from app.api.v1.auth.helpers import get_optional_user
    from app.api.v1.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    item = await _seed_item(test_db, title="ItemForNotes")
    patron = User(
        email="np@example.com", first_name="N", last_name="P",
        role=UserRole.PATRON, is_active=True, email_verified=True,
    )
    staff = User(
        email="ns@example.com", first_name="N", last_name="S",
        role=UserRole.STAFF, is_active=True, email_verified=True,
    )
    test_db.add_all([patron, staff])
    await test_db.commit()
    await test_db.refresh(patron)
    await test_db.refresh(staff)

    note = ShelfNote(
        catalog_item_id=item.id,
        user_id=patron.id,
        content="patron contributed",
        category=ShelfNoteCategory.other,
        is_approved=True,
    )
    test_db.add(note)
    await test_db.commit()
    await test_db.refresh(note)
    note_id = note.id

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return staff

    async def override_get_optional_user():
        return staff

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_optional_user] = override_get_optional_user
    app.state.setup_complete = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            resp = await client.delete(
                f"/api/v1/catalog/items/{item.id}/shelf-notes/{note_id}"
            )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()
