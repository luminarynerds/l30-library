# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Contract tests for patron/user API endpoints.

These tests validate that every patron-facing and admin user-management
endpoint returns responses matching the stored JSON Schema snapshots.

Run snapshot update:
    python scripts/generate_snapshots.py
"""

import pytest

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patron_headers(user) -> dict:
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(user) -> dict:
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Current-user (patron self-service) contracts
# ---------------------------------------------------------------------------


class TestPatronSelfServiceContract:
    """Validate patron self-service endpoints against UserResponse schema."""

    async def test_get_me_response_shape(
        self, client, test_patron, assert_matches_snapshot
    ):
        """GET /users/me must return UserResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        assert_matches_snapshot(resp.json(), "patron/UserResponse.json")


# ---------------------------------------------------------------------------
# Admin user-management contracts
# ---------------------------------------------------------------------------


class TestAdminUserManagementContract:
    """Validate admin user management endpoints against expected schemas."""

    async def test_list_users_response_shape(
        self, client, test_admin, test_patron, assert_matches_snapshot
    ):
        """GET /users must return UserListResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 200
        assert_matches_snapshot(resp.json(), "patron/UserListResponse.json")

    async def test_get_user_by_id_response_shape(
        self, client, test_admin, test_patron, assert_matches_snapshot
    ):
        """GET /users/{id} must return UserResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.get(f"/api/v1/users/{test_patron.id}", headers=headers)
        assert resp.status_code == 200
        assert_matches_snapshot(resp.json(), "patron/UserResponse.json")

    async def test_create_user_response_shape(
        self, client, test_admin, assert_matches_snapshot
    ):
        """POST /users must return UserResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.post(
            "/api/v1/users",
            json={
                "email": "newcontract@example.com",
                "password": "ContractTest123!",
                "first_name": "Contract",
                "last_name": "Test",
                "role": "patron",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert_matches_snapshot(resp.json(), "patron/UserResponse.json")

    async def test_update_user_response_shape(
        self, client, test_admin, test_patron, assert_matches_snapshot
    ):
        """PUT /users/{id} must return UserResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.put(
            f"/api/v1/users/{test_patron.id}",
            json={"first_name": "Updated"},
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "patron/UserResponse.json")

    async def test_lock_user_response_shape(
        self, client, test_admin, test_patron, assert_matches_snapshot
    ):
        """POST /users/{id}/lock must return UserResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.post(
            f"/api/v1/users/{test_patron.id}/lock",
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "patron/UserResponse.json")

    async def test_unlock_user_response_shape(
        self, client, test_admin, test_patron, assert_matches_snapshot
    ):
        """POST /users/{id}/unlock must return UserResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.post(
            f"/api/v1/users/{test_patron.id}/unlock",
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "patron/UserResponse.json")


# ---------------------------------------------------------------------------
# Auth token contract
# ---------------------------------------------------------------------------


class TestAuthTokenContract:
    """Validate auth endpoints against Token schema."""

    async def test_login_response_shape(self, client, test_patron, test_user_data):
        """POST /auth/login must return token fields."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            # TokenWithCookie returns access_token + token_type (refresh in cookie)
            assert "access_token" in data
            assert "token_type" in data


class TestAuthLegacyGetCompatibility:
    """Validate legacy GET auth aliases remain non-breaking while deprecated."""

    async def test_legacy_get_login_sets_deprecation_headers(self, client):
        resp = await client.get('/api/v1/auth/login')

        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}
        assert resp.headers.get('X-Deprecated') == 'true'
        assert resp.headers.get('X-Replacement-Method') == 'POST'
        # Verify RFC 7234 Warning header
        assert '299' in resp.headers.get('Warning', '')

    async def test_legacy_get_forgot_password_sets_deprecation_headers(self, client):
        resp = await client.get('/api/v1/auth/forgot-password')

        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}
        assert resp.headers.get('X-Deprecated') == 'true'
        assert resp.headers.get('X-Replacement-Method') == 'POST'
        # Verify RFC 7234 Warning header
        assert '299' in resp.headers.get('Warning', '')

    async def test_legacy_get_logout_sets_deprecation_headers(self, client):
        # GET /logout is now public for consistency with login/forgot-password
        resp = await client.get('/api/v1/auth/logout')

        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}
        assert resp.headers.get('X-Deprecated') == 'true'
        assert resp.headers.get('X-Replacement-Method') == 'POST'
        # Verify RFC 7234 Warning header
        assert '299' in resp.headers.get('Warning', '')

    async def test_legacy_get_change_password_sets_deprecation_headers(self, client, test_patron):
        # GET /change-password requires authentication (unlike login/forgot-password)
        headers = _patron_headers(test_patron)
        resp = await client.get('/api/v1/auth/change-password', headers=headers)

        assert resp.status_code == 200
        assert resp.json() == {'status': 'ok'}
        assert resp.headers.get('X-Deprecated') == 'true'
        assert resp.headers.get('X-Replacement-Method') == 'POST'
        # Verify RFC 7234 Warning header
        assert '299' in resp.headers.get('Warning', '')
