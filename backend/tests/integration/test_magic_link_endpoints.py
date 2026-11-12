# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for magic link authentication API endpoints.

Tests the full request → token → verify → login flow, including
edge cases like expired tokens, locked accounts, and rate limiting.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import (
    create_magic_link_token,
    hash_magic_link_token,
    get_magic_link_token_expiry,
)
from app.models.user import User


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.mark.integration
class TestMagicLinkRequest:
    """Test POST /api/v1/auth/magic-link endpoint."""

    async def test_request_magic_link_valid_email(self, client, test_patron):
        """Should return success for a valid, verified email."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sign-in link has been sent" in data["message"]

    async def test_request_magic_link_nonexistent_email(self, client):
        """Should return the same generic success message for unknown emails (prevent enumeration)."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sign-in link has been sent" in data["message"]

    async def test_request_magic_link_unverified_email(self, client, test_db):
        """Should return generic success for an unverified email (no token generated)."""
        from app.core.security import hash_password

        user = User(
            email="unverified@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Unverified",
            last_name="User",
            is_active=True,
            email_verified=False,
        )
        test_db.add(user)
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "unverified@example.com"},
        )
        assert response.status_code == 200

        # Verify no token was stored
        await test_db.refresh(user)
        assert user.magic_link_token is None

    async def test_request_magic_link_inactive_account(self, client, test_db, test_patron):
        """Should return generic success for an inactive account (no token generated)."""
        test_patron.is_active = False
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        assert response.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.magic_link_token is None

    async def test_request_magic_link_locked_account(self, client, test_db, test_patron):
        """Should return generic success for a locked account (no token generated)."""
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        assert response.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.magic_link_token is None

    async def test_request_magic_link_stores_hashed_token(self, client, test_db, test_patron):
        """Token stored in DB should be hashed, not plain."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        assert response.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.magic_link_token is not None
        # Hashed token should be a 64-char hex string (SHA-256)
        assert len(test_patron.magic_link_token) == 64
        assert test_patron.magic_link_token_expires is not None

    async def test_request_magic_link_replaces_previous_token(self, client, test_db, test_patron):
        """Requesting a new magic link should replace any previous token."""
        # Request first magic link
        await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        await test_db.refresh(test_patron)
        first_token = test_patron.magic_link_token

        # Request second magic link
        await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        await test_db.refresh(test_patron)
        second_token = test_patron.magic_link_token

        assert first_token != second_token

    async def test_request_magic_link_invalid_email_format(self, client):
        """Should return 422 for an invalid email format."""
        response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestMagicLinkVerify:
    """Test POST /api/v1/auth/magic-link/verify endpoint."""

    async def _create_magic_link_for_user(self, db, user):
        """Helper to create a magic link token directly in the database."""
        plain_token = create_magic_link_token()
        user.magic_link_token = hash_magic_link_token(plain_token)
        user.magic_link_token_expires = get_magic_link_token_expiry()
        await db.commit()
        return plain_token

    async def test_verify_magic_link_success(self, client, test_db, test_patron):
        """Valid magic link should return access token and set refresh cookie."""
        token = await self._create_magic_link_for_user(test_db, test_patron)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_verify_magic_link_updates_last_login(self, client, test_db, test_patron):
        """Successful magic link login should update last_login timestamp."""
        before = datetime.now(timezone.utc)
        token = await self._create_magic_link_for_user(test_db, test_patron)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.last_login is not None
        assert test_patron.last_login >= before

    async def test_verify_magic_link_single_use(self, client, test_db, test_patron):
        """Magic link token should only work once."""
        token = await self._create_magic_link_for_user(test_db, test_patron)

        # First use should succeed
        response1 = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response1.status_code == 200

        # Second use should fail
        response2 = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response2.status_code == 401

    async def test_verify_magic_link_invalid_token(self, client):
        """Random token should be rejected."""
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "completely-invalid-token"},
        )
        assert response.status_code == 401
        # Copy changed to a friendlier UX message ("This sign-in link is no
        # longer valid. Please request a new one.") -- consistent across
        # app/api/v1/auth/login.py + password.py's other link-expiry paths.
        detail = _error_detail(response).lower()
        assert "no longer valid" in detail or "expired" in detail

    async def test_verify_magic_link_expired_token(self, client, test_db, test_patron):
        """Expired magic link should be rejected."""
        plain_token = create_magic_link_token()
        test_patron.magic_link_token = hash_magic_link_token(plain_token)
        test_patron.magic_link_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": plain_token},
        )
        assert response.status_code == 401
        assert "expired" in _error_detail(response).lower()

        # Token should be cleared after expiry check
        await test_db.refresh(test_patron)
        assert test_patron.magic_link_token is None

    async def test_verify_magic_link_locked_account(self, client, test_db, test_patron):
        """Locked account should not be able to use magic link."""
        token = await self._create_magic_link_for_user(test_db, test_patron)

        # Lock the account after token was created
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 423
        assert "locked" in _error_detail(response).lower()

    async def test_verify_magic_link_inactive_account(self, client, test_db, test_patron):
        """Inactive account should not be able to use magic link."""
        token = await self._create_magic_link_for_user(test_db, test_patron)

        # Deactivate account after token was created
        test_patron.is_active = False
        await test_db.commit()

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 401

    async def test_verify_magic_link_resets_failed_login_attempts(
        self, client, test_db, test_patron
    ):
        """Successful magic link login should reset failed login attempts."""
        test_patron.failed_login_attempts = 3
        await test_db.commit()

        token = await self._create_magic_link_for_user(test_db, test_patron)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.failed_login_attempts == 0

    async def test_verify_magic_link_creates_refresh_token(self, client, test_db, test_patron):
        """Successful magic link login should create a refresh token in the database."""
        from app.models.user import RefreshToken

        token = await self._create_magic_link_for_user(test_db, test_patron)

        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": token},
        )
        assert response.status_code == 200

        # Verify a refresh token was stored
        result = await test_db.execute(
            select(RefreshToken).where(RefreshToken.user_id == test_patron.id)
        )
        refresh_tokens = result.scalars().all()
        assert len(refresh_tokens) >= 1

    async def test_verify_magic_link_empty_token(self, client):
        """Empty token should be rejected."""
        response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": ""},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestMagicLinkFullFlow:
    """Test the full magic link request → verify → authenticated access flow."""

    async def test_full_magic_link_flow(self, client, test_db, test_patron):
        """Test requesting a magic link and using it to authenticate."""
        # Step 1: Request magic link
        request_response = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": test_patron.email},
        )
        assert request_response.status_code == 200

        # Step 2: Extract the token from the database (simulating clicking email link)
        await test_db.refresh(test_patron)
        stored_hash = test_patron.magic_link_token
        assert stored_hash is not None

        # We can't recover the plain token from the hash, but we can create one
        # directly for testing the verify flow
        plain_token = create_magic_link_token()
        test_patron.magic_link_token = hash_magic_link_token(plain_token)
        test_patron.magic_link_token_expires = get_magic_link_token_expiry()
        await test_db.commit()

        # Step 3: Verify the magic link
        verify_response = await client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": plain_token},
        )
        assert verify_response.status_code == 200
        access_token = verify_response.json()["access_token"]

        # Step 4: Use the access token to access a protected endpoint
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == test_patron.email
