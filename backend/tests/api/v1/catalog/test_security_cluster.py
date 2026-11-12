# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Slice A: catalog-security cluster regression tests.

Pins the four catalog-route fixes in one focused file:

1. ``GET /catalog/{id}/recommendations`` -- no auth dep, no visibility filter
   meant pinned/algorithmic CONFIDENTIAL or non-cataloged items leaked to
   anonymous callers (and patrons could see CONFIDENTIAL).
2. ``GET /catalog/items/{id}/state-history`` -- ``current_user`` was used to
   gate the ``actor_name`` field but no sensitivity / cataloging-status gate
   ran on the row, so existence + ``reason`` text of CONFIDENTIAL items
   leaked to anonymous callers.
3. ``_visibility_ok`` in the cover proxy hard-coded ``(STAFF, ADMIN)`` for
   the non-cataloged bypass, so SUPER_ADMIN / DIRECTOR / LEGAL got 404 on
   covers they could see everywhere else.
4. Legacy ``GET /opds/catalog.xml`` filtered sensitivity to
   ``in_([PUBLIC, SENSITIVE])`` while every other anonymous OPDS path went
   PUBLIC-only.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.api.v1.catalog.covers import _visibility_ok
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.curated_recommendations import CuratedRecommendation
from app.models.user import User, UserRole


async def _seed_item(
    db,
    *,
    title: str,
    cataloging_status: CatalogingStatus = CatalogingStatus.CATALOGED,
    sensitivity_level: SensitivityLevel = SensitivityLevel.PUBLIC,
    item_type: ItemType = ItemType.book,
    status: ItemStatus = ItemStatus.available,
    cover_url: str | None = None,
) -> CatalogItem:
    item = CatalogItem(
        title=title,
        author="Test Author",
        item_type=item_type,
        status=status,
        cataloging_status=cataloging_status,
        sensitivity_level=sensitivity_level,
        cover_url=cover_url,
    )
    db.add(item)
    await db.flush()
    return item


# ---------------------------------------------------------------------------
# Fix #3 -- cover proxy _visibility_ok: SUPER_ADMIN / DIRECTOR / LEGAL bypass
# ---------------------------------------------------------------------------


def _user(role: UserRole) -> User:
    """Bare User stub for visibility predicate tests; not persisted."""
    return User(
        email=f"{role.value}@example.com",
        first_name="V",
        last_name="X",
        role=role,
    )


def test_visibility_ok_super_admin_sees_uncataloged_cover():
    item = CatalogItem(
        title="Uncataloged WIP",
        cataloging_status=CatalogingStatus.UNCATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    # Pre-fix: returned False because the inline check was (STAFF, ADMIN)
    # only. SUPER_ADMIN, DIRECTOR, LEGAL all 404'd despite seeing the item
    # everywhere else.
    assert _visibility_ok(item, _user(UserRole.SUPER_ADMIN)) is True
    assert _visibility_ok(item, _user(UserRole.DIRECTOR)) is True
    assert _visibility_ok(item, _user(UserRole.LEGAL)) is True
    # Regression checks: STAFF/ADMIN still bypass; PATRON/anon still 404.
    assert _visibility_ok(item, _user(UserRole.STAFF)) is True
    assert _visibility_ok(item, _user(UserRole.ADMIN)) is True
    assert _visibility_ok(item, _user(UserRole.PATRON)) is False
    assert _visibility_ok(item, None) is False


def test_visibility_ok_anonymous_only_sees_public_cataloged():
    cataloged_public = CatalogItem(
        title="ok",
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    cataloged_sensitive = CatalogItem(
        title="sens",
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.SENSITIVE,
    )
    cataloged_confidential = CatalogItem(
        title="conf",
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
    )
    assert _visibility_ok(cataloged_public, None) is True
    # Anonymous never sees SENSITIVE or CONFIDENTIAL.
    assert _visibility_ok(cataloged_sensitive, None) is False
    assert _visibility_ok(cataloged_confidential, None) is False


# ---------------------------------------------------------------------------
# Fix #1 -- recommendations endpoint visibility
# ---------------------------------------------------------------------------


async def test_recommendations_anon_does_not_leak_confidential_pin(
    public_client: AsyncClient, db_session
):
    """Anonymous caller must not see a pinned CONFIDENTIAL item in recs."""
    source = await _seed_item(db_session, title="Public Source")
    confidential_target = await _seed_item(
        db_session,
        title="Secret Acquisition Note",
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
    )
    db_session.add(
        CuratedRecommendation(
            source_item_id=source.id,
            target_item_id=confidential_target.id,
            display_order=0,
            is_hidden=False,
        )
    )
    await db_session.commit()

    resp = await public_client.get(f"/api/v1/catalog/{source.id}/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    titles = [it["title"] for it in body["items"]]
    assert "Secret Acquisition Note" not in titles
    # The pinned item was filtered, so total_pinned should be zero from the
    # caller's perspective.
    assert body["total_pinned"] == 0


async def test_recommendations_anon_does_not_leak_uncataloged_pin(
    public_client: AsyncClient, db_session
):
    """Anonymous caller must not see a pinned non-cataloged item in recs."""
    source = await _seed_item(db_session, title="Public Source 2")
    wip_target = await _seed_item(
        db_session,
        title="WIP Cataloging Record",
        cataloging_status=CatalogingStatus.UNCATALOGED,
    )
    db_session.add(
        CuratedRecommendation(
            source_item_id=source.id,
            target_item_id=wip_target.id,
            display_order=0,
            is_hidden=False,
        )
    )
    await db_session.commit()

    resp = await public_client.get(f"/api/v1/catalog/{source.id}/recommendations")
    assert resp.status_code == 200
    titles = [it["title"] for it in resp.json()["items"]]
    assert "WIP Cataloging Record" not in titles


# ---------------------------------------------------------------------------
# Fix #2 -- state-history endpoint visibility
# ---------------------------------------------------------------------------


async def test_state_history_anon_404s_on_confidential(
    public_client: AsyncClient, db_session
):
    confidential = await _seed_item(
        db_session,
        title="Confidential Record",
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
    )
    await db_session.commit()

    resp = await public_client.get(
        f"/api/v1/catalog/items/{confidential.id}/state-history"
    )
    assert resp.status_code == 404


async def test_state_history_anon_404s_on_uncataloged(
    public_client: AsyncClient, db_session
):
    wip = await _seed_item(
        db_session,
        title="WIP",
        cataloging_status=CatalogingStatus.UNCATALOGED,
    )
    await db_session.commit()

    resp = await public_client.get(
        f"/api/v1/catalog/items/{wip.id}/state-history"
    )
    assert resp.status_code == 404


async def test_state_history_anon_200s_on_public_cataloged(
    public_client: AsyncClient, db_session
):
    """Regression: the visibility gate must not break the happy path."""
    public_item = await _seed_item(db_session, title="Public Item")
    await db_session.commit()

    resp = await public_client.get(
        f"/api/v1/catalog/items/{public_item.id}/state-history"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Fix #4 -- legacy OPDS feed SENSITIVE leak
# ---------------------------------------------------------------------------


async def test_legacy_opds_excludes_sensitive(
    public_client: AsyncClient, db_session
):
    public_book = await _seed_item(
        db_session,
        title="Public Book Title XYZZY",
    )
    sensitive_book = await _seed_item(
        db_session,
        title="Sensitive Book Title PLUGH",
        sensitivity_level=SensitivityLevel.SENSITIVE,
    )
    await db_session.commit()

    resp = await public_client.get("/api/v1/catalog/opds/catalog.xml")
    assert resp.status_code == 200
    body = resp.text
    # Pre-fix: the SENSITIVE title appeared because the filter was
    # ``sensitivity_level.in_([PUBLIC, SENSITIVE])``.
    assert "Sensitive Book Title PLUGH" not in body
    # Regression: PUBLIC items still surface.
    assert "Public Book Title XYZZY" in body
