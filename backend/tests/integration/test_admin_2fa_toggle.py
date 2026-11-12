# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Admin 2FA enforcement is gated on the require_admin_2fa setting.

Default (hosted deployments): admins without TOTP are forced into 2FA setup.
Self-host / fork builds set REQUIRE_ADMIN_2FA=false so an operator can log in
and evaluate the system without standing up an authenticator first; 2FA stays
available to opt into via account settings.
"""
import pytest

from app.api.v1.auth import login as login_module


@pytest.mark.integration
class TestAdminTwoFactorToggle:
    async def test_admin_2fa_forced_by_default(self, client, test_admin, test_admin_data):
        """Default require_admin_2fa=True: an admin with no TOTP is pushed into setup."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_admin_data["email"], "password": test_admin_data["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("requires_2fa_setup") is True

    async def test_admin_2fa_optional_when_disabled(self, client, test_admin, test_admin_data, monkeypatch):
        """Fork build (require_admin_2fa=False): admin logs in with a normal token, no forced setup."""
        monkeypatch.setattr(login_module.settings, "require_admin_2fa", False)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_admin_data["email"], "password": test_admin_data["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "requires_2fa_setup" not in data
        assert data["access_token"]
        assert data["token_type"] == "bearer"
