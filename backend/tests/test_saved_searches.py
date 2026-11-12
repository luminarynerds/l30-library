# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backend tests for patron saved-search endpoints.

Covers:
- CRUD round trip as the owning patron.
- Cross-patron access returns 404 (not 403) so the existence of another
  patron's row is never leaked.
- ``run`` returns the catalog-search response shape, plus the saved_search_id.
- Feature flag off causes the entire router to 404.

Uses the project's ``client`` / ``test_db`` fixtures (see conftest.py) so
SQLite connection lifecycle is managed correctly across tests.
"""
from __future__ import annotations

import uuid

import pytest

from app.api.v1.auth.helpers import get_current_user
from app.api.v1.feature_guards import (
    require_patron_portal_enabled,
    require_saved_searches_enabled,
)
from app.main import app
from app.models.catalog import CatalogItem, ItemStatus
from app.models.user import User, UserRole


# -- helpers ----------------------------------------------------------------


async def _make_patron(test_db, email: str) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        password_hash=hash_password("Pa$$word123!"),
        first_name="P",
        last_name="One",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _noop():
    """Stand-in for feature-guard deps so the router is reachable in tests.

    The feature flag is verified separately in
    ``TestSavedSearchesFeatureFlag``.
    """
    return None


# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def enable_feature():
    """Override the feature-flag guards so the saved-searches router is reachable.

    Yields nothing; cleans up the overrides on teardown.
    """
    app.dependency_overrides[require_saved_searches_enabled] = _noop
    app.dependency_overrides[require_patron_portal_enabled] = _noop
    yield
    app.dependency_overrides.pop(require_saved_searches_enabled, None)
    app.dependency_overrides.pop(require_patron_portal_enabled, None)


@pytest.fixture
async def patron_a(test_db):
    return await _make_patron(test_db, "patron-a@example.com")


@pytest.fixture
async def patron_b(test_db):
    return await _make_patron(test_db, "patron-b@example.com")


@pytest.fixture
def auth_as_patron_a(patron_a):
    app.dependency_overrides[get_current_user] = lambda: patron_a
    yield patron_a
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_as_patron_b(patron_b):
    app.dependency_overrides[get_current_user] = lambda: patron_b
    yield patron_b
    app.dependency_overrides.pop(get_current_user, None)


# -- tests ------------------------------------------------------------------


class TestSavedSearchesCRUD:
    """Round-trip CRUD as the owning patron."""

    @pytest.mark.asyncio
    async def test_create_then_list_then_get(
        self, client, enable_feature, auth_as_patron_a
    ):
        # Empty to start
        empty = await client.get("/api/v1/patrons/me/saved-searches")
        assert empty.status_code == 200, empty.text
        assert empty.json()["total"] == 0
        assert empty.json()["items"] == []

        # Create
        create_resp = await client.post(
            "/api/v1/patrons/me/saved-searches",
            json={
                "name": "  Sci-fi 2024+  ",
                "query": "space opera",
                "filters_json": {
                    "year_min": 2024,
                    "item_type": "book",
                    "status": "available",
                },
                "sort_by": "publication_year",
                "view_mode": "grid",
                "notify_on_new": True,
                "notify_email": False,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        created = create_resp.json()
        assert created["name"] == "Sci-fi 2024+"  # trimmed by validator
        assert created["filters_json"]["year_min"] == 2024
        assert created["notify_on_new"] is True
        search_id = created["id"]
        uuid.UUID(search_id)  # parseable

        # List shows the one row
        listed = await client.get("/api/v1/patrons/me/saved-searches")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["id"] == search_id

        # Detail
        detail = await client.get(
            f"/api/v1/patrons/me/saved-searches/{search_id}"
        )
        assert detail.status_code == 200
        assert detail.json()["query"] == "space opera"

    @pytest.mark.asyncio
    async def test_patch_renames_and_toggles_notify(
        self, client, enable_feature, auth_as_patron_a
    ):
        created = (
            await client.post(
                "/api/v1/patrons/me/saved-searches",
                json={"name": "Initial", "filters_json": {}},
            )
        ).json()
        sid = created["id"]
        assert created["notify_on_new"] is False

        patched = await client.patch(
            f"/api/v1/patrons/me/saved-searches/{sid}",
            json={"name": "Renamed", "notify_on_new": True},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["name"] == "Renamed"
        assert patched.json()["notify_on_new"] is True
        # Untouched fields remain
        assert patched.json()["notify_in_app"] is True

    @pytest.mark.asyncio
    async def test_delete_removes_the_row(
        self, client, enable_feature, auth_as_patron_a
    ):
        sid = (
            await client.post(
                "/api/v1/patrons/me/saved-searches",
                json={"name": "Ephemeral", "filters_json": {}},
            )
        ).json()["id"]

        deleted = await client.delete(
            f"/api/v1/patrons/me/saved-searches/{sid}"
        )
        assert deleted.status_code == 204

        missing = await client.get(
            f"/api/v1/patrons/me/saved-searches/{sid}"
        )
        assert missing.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_blank_name(
        self, client, enable_feature, auth_as_patron_a
    ):
        resp = await client.post(
            "/api/v1/patrons/me/saved-searches",
            json={"name": "   ", "filters_json": {}},
        )
        assert resp.status_code == 422


class TestSavedSearchesAuthorization:
    """Cross-patron access must not succeed."""

    @pytest.mark.asyncio
    async def test_other_patrons_search_is_404(
        self, client, enable_feature, patron_a, patron_b
    ):
        # Create as patron_a
        app.dependency_overrides[get_current_user] = lambda: patron_a
        try:
            sid = (
                await client.post(
                    "/api/v1/patrons/me/saved-searches",
                    json={"name": "Owner's search", "filters_json": {}},
                )
            ).json()["id"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # Read / patch / delete as patron_b all 404
        app.dependency_overrides[get_current_user] = lambda: patron_b
        try:
            assert (
                await client.get(
                    f"/api/v1/patrons/me/saved-searches/{sid}"
                )
            ).status_code == 404
            assert (
                await client.patch(
                    f"/api/v1/patrons/me/saved-searches/{sid}",
                    json={"name": "hijacked"},
                )
            ).status_code == 404
            assert (
                await client.delete(
                    f"/api/v1/patrons/me/saved-searches/{sid}"
                )
            ).status_code == 404
            # patron_b's own list does NOT contain patron_a's row
            listed = await client.get("/api/v1/patrons/me/saved-searches")
            assert listed.json()["total"] == 0
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestSavedSearchesRun:
    """``run`` returns the catalog-search shape and uses saved filters."""

    @pytest.mark.asyncio
    async def test_run_returns_matching_items(
        self, client, enable_feature, auth_as_patron_a, test_db
    ):
        # Seed two catalog items: one matches, one doesn't.
        match = CatalogItem(
            title="Advanced Python Programming",
            author="Doe, J.",
            status=ItemStatus.available,
            publication_year=2024,
        )
        miss = CatalogItem(
            title="Beginner Java",
            author="Smith, A.",
            status=ItemStatus.available,
            publication_year=2020,
        )
        test_db.add_all([match, miss])
        await test_db.commit()

        sid = (
            await client.post(
                "/api/v1/patrons/me/saved-searches",
                json={
                    "name": "Python only",
                    "query": "Python",
                    "filters_json": {},
                },
            )
        ).json()["id"]

        run = await client.post(
            f"/api/v1/patrons/me/saved-searches/{sid}/run"
        )
        assert run.status_code == 200, run.text
        body = run.json()
        assert body["saved_search_id"] == sid
        assert body["total"] == 1
        assert body["results"][0]["title"] == match.title
        # Same shape as the catalog endpoint
        assert "page" in body
        assert "per_page" in body
        assert "pages" in body

        # last_run_at is now populated
        detail = (
            await client.get(f"/api/v1/patrons/me/saved-searches/{sid}")
        ).json()
        assert detail["last_run_at"] is not None


class TestSavedSearchesFeatureFlag:
    """Feature-flag-off must hide the entire router (per L30 convention)."""

    @pytest.mark.asyncio
    async def test_router_returns_404_when_feature_disabled(
        self, client, auth_as_patron_a, test_db
    ):
        # NOTE: deliberately NOT using the enable_feature fixture -- that
        # overrides the dependency entirely rather than exercising the real
        # guard. saved_searches_enabled flipped to default=True org-wide
        # once notifier delivery was verified (see git blame on
        # app/models/organization_features.py), so the disabled path now
        # has to be constructed explicitly rather than relying on the
        # out-of-the-box default.
        from app.services.organization_features_service import (
            OrganizationFeaturesService,
        )

        features = await OrganizationFeaturesService.get_or_create_features(test_db)
        features.saved_searches_enabled = False
        await test_db.commit()
        await OrganizationFeaturesService.invalidate_cache()

        resp = await client.get("/api/v1/patrons/me/saved-searches")
        assert resp.status_code == 404
        resp = await client.post(
            "/api/v1/patrons/me/saved-searches",
            json={"name": "X", "filters_json": {}},
        )
        assert resp.status_code == 404
