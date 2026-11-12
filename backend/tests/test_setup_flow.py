# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the setup wizard flow."""

import pytest
from httpx import AsyncClient


class TestSetupStatus:
    """Tests for GET /api/v1/setup/status."""

    @pytest.mark.asyncio
    async def test_fresh_install_reports_setup_required(self, client: AsyncClient, test_db):
        """setup_required reflects whether an admin/super_admin user exists.

        This suite runs against a long-lived, shared test database (many
        parallel test invocations across the whole rebaseline effort reuse
        it), so a prior test run may have already committed a real admin
        user -- "the DB starts empty" isn't a safe assumption here. Assert
        the endpoint is internally consistent with the actual admin count
        instead of hardcoding the fresh-install case.
        """
        from sqlalchemy import func, select
        from app.models.user import User, UserRole

        result = await test_db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
        )
        admin_count = result.scalar_one()

        response = await client.get("/api/v1/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is (admin_count == 0)
        assert "demo_mode" in data
        assert "demo_public" in data


class TestAdminCreation:
    """Tests for POST /api/v1/setup/admin."""

    @pytest.mark.asyncio
    async def test_create_admin_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "Test",
                "last_name": "Admin",
                "email": "admin@test.org",
                "password": "securepass123",
            },
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_create_admin_blocked_after_setup(self, client: AsyncClient):
        """Cannot create second admin via setup endpoint."""
        # First admin
        await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "First",
                "last_name": "Admin",
                "email": "first@test.org",
                "password": "securepass123",
            },
        )
        # Attempt second
        response = await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "Hacker",
                "last_name": "Evil",
                "email": "hack@evil.com",
                "password": "password123",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_admin_validates_password_length(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@test.org",
                "password": "short",  # < 8 chars
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_admin_validates_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "not-an-email",
                "password": "securepass123",
            },
        )
        assert response.status_code == 422


class TestLibraryInfo:
    """Tests for POST /api/v1/setup/library-info."""

    @pytest.mark.asyncio
    async def test_save_library_info(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/library-info",
            json={
                "name": "Test Library",
                "code": "TL",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_library_info_requires_name(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/library-info",
            json={
                "name": "",
                "code": "TL",
            },
        )
        assert response.status_code == 422


class TestBranding:
    """Tests for POST /api/v1/setup/branding."""

    @pytest.mark.asyncio
    async def test_save_branding(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/branding",
            json={
                "primary_color": "#ff0000",
                "accent_color": "#00ff00",
                "hero_title": "Welcome",
                "tagline": "Books for all",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_branding_validates_color_format(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/branding",
            json={
                "primary_color": "red",  # Not hex
                "accent_color": "#00ff00",
            },
        )
        assert response.status_code == 422


class TestSetupAuthGate:
    """Once a founding admin exists, /setup/* (except /status and /admin's
    own self-gate) requires an authenticated admin. Pre-admin bootstrap stays
    open — there is nothing to authenticate against yet."""

    async def _create_admin(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "first_name": "Founding",
                "last_name": "Admin",
                "email": "founder@test.org",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        assert token, "/setup/admin must return an access token for the founding admin"
        return token

    @pytest.mark.asyncio
    async def test_pre_admin_bootstrap_window_is_open(self, client: AsyncClient):
        """No admin yet: wizard endpoints accept unauthenticated calls."""
        resp = await client.post(
            "/api/v1/setup/branding",
            json={
                "primary_color": "#111111",
                "accent_color": "#222222",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_blocked_after_admin_exists(self, client: AsyncClient):
        await self._create_admin(client)
        for path, payload in [
            ("/api/v1/setup/branding", {"primary_color": "#111111", "accent_color": "#222222"}),
            ("/api/v1/setup/library-info", {"name": "Hijack Library", "code": "HL"}),
            ("/api/v1/setup/domain", {"domain": "evil.example"}),
            ("/api/v1/setup/demo/load", {}),
            ("/api/v1/setup/complete", {}),
        ]:
            resp = await client.post(path, json=payload)
            assert resp.status_code == 401, (
                f"{path} must 401 for anonymous callers once an admin exists, got {resp.status_code}"
            )

    @pytest.mark.asyncio
    async def test_founding_admin_token_allows_wizard_steps(self, client: AsyncClient, monkeypatch):
        # No Redis in the test env: revocation fail-secure would reject every
        # token. Revocation is orthogonal to the gate under test.
        from app.core import security

        monkeypatch.setattr(security, "is_token_revoked", lambda _t: False)

        token = await self._create_admin(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/setup/branding",
            headers=headers,
            json={
                "primary_color": "#333333",
                "accent_color": "#444444",
            },
        )
        assert resp.status_code == 200
        resp = await client.post(
            "/api/v1/setup/library-info",
            headers=headers,
            json={
                "name": "Founded Library",
                "code": "FL",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_admin_token_forbidden(self, client: AsyncClient, test_db, monkeypatch):
        """A patron token must not pass the gate."""
        from app.core import security
        from app.core.security import create_access_token, hash_password
        from app.models.user import User, UserRole

        monkeypatch.setattr(security, "is_token_revoked", lambda _t: False)

        await self._create_admin(client)
        patron = User(
            first_name="Pat",
            last_name="Ron",
            email="patron@test.org",
            password_hash=hash_password("securepass123"),
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(patron)
        await test_db.commit()
        await test_db.refresh(patron)
        token = create_access_token(subject=patron.id, email=patron.email, role="patron")
        resp = await client.post(
            "/api/v1/setup/branding",
            headers={"Authorization": f"Bearer {token}"},
            json={"primary_color": "#555555", "accent_color": "#666666"},
        )
        assert resp.status_code == 403


class TestWizardBrandingGoesLive:
    """Wizard writes must take effect on GET /api/v1/branding — the live,
    LibraryBranding-DB-backed path. branding.json only feeds boot-time
    defaults, so a wizard that writes the file but not the DB row leaves the
    site showing stock branding."""

    @pytest.mark.asyncio
    async def test_branding_step_reflected_live(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/setup/branding",
            json={
                "primary_color": "#123456",
                "accent_color": "#654321",
                "hero_title": "Welcome to Maple Falls",
                "tagline": "Books for all",
            },
        )
        assert resp.status_code == 200
        live = (await client.get("/api/v1/branding")).json()
        assert live["primary_color"] == "#123456"
        assert live["accent_color"] == "#654321"
        assert live["hero_title"] == "Welcome to Maple Falls"
        assert live["tagline"] == "Books for all"

    @pytest.mark.asyncio
    async def test_library_info_identity_reflected_live(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/setup/library-info",
            json={
                "name": "Maple Falls Public Library",
                "code": "MFPL",
                "email": "hello@maplefalls.example",
                "address": "1 Library Way",
            },
        )
        assert resp.status_code == 200
        live = (await client.get("/api/v1/branding")).json()
        assert live["library_name"] == "Maple Falls Public Library"
        assert live["contact_email"] == "hello@maplefalls.example"
        assert live["address_line1"] == "1 Library Way"

    @pytest.mark.asyncio
    async def test_domain_step_reflected_live(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/setup/domain",
            json={
                "domain": "library.maplefalls.example",
            },
        )
        assert resp.status_code == 200
        live = (await client.get("/api/v1/branding")).json()
        assert live["domain"] == "library.maplefalls.example"

    @pytest.mark.asyncio
    async def test_logo_stored_under_uploads_mount_and_reflected_live(
        self, client: AsyncClient, tmp_path, monkeypatch
    ):
        """The logo must land under the /uploads StaticFiles mount (the old
        /app/static/branding location had no route) and set logo_url."""
        monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
        resp = await client.post(
            "/api/v1/setup/branding/logo",
            files={"file": ("logo.png", b"\x89PNG-fake-bytes", "image/png")},
        )
        assert resp.status_code == 200
        assert (tmp_path / "branding" / "logo.png").exists()
        live = (await client.get("/api/v1/branding")).json()
        assert live["logo_url"] == "/uploads/branding/logo.png"


class TestPolicies:
    """Tests for POST /api/v1/setup/policies."""

    @pytest.mark.asyncio
    async def test_save_policies(self, client: AsyncClient):
        # Need library info first (creates SystemSettings)
        await client.post(
            "/api/v1/setup/library-info",
            json={
                "name": "Test Library",
                "code": "TL",
            },
        )
        response = await client.post(
            "/api/v1/setup/policies",
            json={
                "default_loan_period_days": 21,
                "default_renewal_limit": 3,
                "default_hold_limit": 10,
                "default_overdue_fine_per_day": 0.25,
                "default_max_fine": 10.0,
                "grace_period_days": 3,
                "fine_free_juvenile": True,
                "lost_item_threshold_days": 45,
            },
        )
        assert response.status_code == 200


class TestDemoWipe:
    """Tests for POST /api/v1/setup/demo/wipe.

    SECURITY DECISION (report-only, not fixed here): this endpoint doesn't
    exist. app/api/v1/admin_data_export.py:8 states outright "The actual
    wipe of a library system's data is deliberately NOT in this [module]"
    -- _wipe_instructions() returns manual/CLI instructions instead of
    exposing a destructive action over HTTP. grep across app/api/ confirms
    no route registers "/wipe" or "demo/wipe" anywhere. These tests
    predate that removal. Not resurrecting an HTTP-triggerable data-wipe
    endpoint to make a test pass -- flagging for a maintainer decision on
    whether the tests should just be deleted.
    """

    @pytest.mark.skip(
        reason="POST /api/v1/setup/demo/wipe was deliberately removed (see class docstring)"
    )
    @pytest.mark.asyncio
    async def test_wipe_requires_exact_confirmation(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/demo/wipe",
            json={
                "confirmation": "wrong text",
            },
        )
        assert response.status_code == 422

    @pytest.mark.skip(
        reason="POST /api/v1/setup/demo/wipe was deliberately removed (see class docstring)"
    )
    @pytest.mark.asyncio
    async def test_wipe_rejects_empty_confirmation(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/setup/demo/wipe",
            json={
                "confirmation": "",
            },
        )
        assert response.status_code == 422


class TestSetupComplete:
    """Tests for POST /api/v1/setup/complete."""

    @pytest.mark.asyncio
    async def test_complete_requires_library_info_first(self, client: AsyncClient):
        response = await client.post("/api/v1/setup/complete")
        assert response.status_code == 400


class TestUpdateStatus:
    """Tests for GET /api/v1/setup/update-status."""

    @pytest.mark.asyncio
    async def test_update_status_returns_structure(self, client: AsyncClient):
        response = await client.get("/api/v1/setup/update-status")
        assert response.status_code == 200
        data = response.json()
        assert "update_available" in data
        assert "update_info" in data
