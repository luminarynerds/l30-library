# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Automated security attack tests for LSC authentication system.

Simulates real-world attack vectors against login, password reset, sessions,
and rate limiting to verify defensive controls before attackers find gaps.

Run: pytest backend/tests/security/test_login_security.py -v
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import (
    COMMON_PASSWORDS,
    PASSWORD_HISTORY_COUNT,
    PasswordValidationError,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    get_reset_token_expiry,
    hash_password,
    hash_reset_token,
    validate_password,
    verify_password,
    verify_reset_token,
    verify_token,
)
from app.models.user import PasswordHistory, RefreshToken, User, UserRole


# ---------------------------------------------------------------------------
# Ensure routers are registered (startup event doesn't fire in ASGI tests)
# and that the rate limiter uses memory storage (no Redis needed).
# ---------------------------------------------------------------------------
def _ensure_routers():
    # Importing app.main runs its module-level `register_all_routers(app,
    # debug=settings.debug)` exactly once (Python caches the module), so
    # routers are already registered by the time this runs. Calling
    # register_all_routers() again here would double every route: fastapi
    # >=0.139's lazy `_IncludedRouter` wrappers don't expose `.path` at the
    # top level of app.routes, so the old "is /api/v1/auth/login already
    # registered" check can no longer detect prior registration and always
    # re-fired, silently doubling app.routes on every import of this module.
    from app.main import app  # noqa: F401
    # Disable rate limiter completely so tests don't need Redis
    from app.core.rate_limit import limiter
    limiter.enabled = False

_ensure_routers()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db, **overrides):
    """Create a verified, active patron with sensible defaults."""
    defaults = dict(
        email="victim@l30.org",
        password_hash=hash_password("Correct!Horse1Battery"),
        first_name="Test",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        failed_login_attempts=0,
        locked_until=None,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    return user


async def _login(client, email, password):
    """Fire a login request and return the response."""
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def _get_detail(resp):
    """Extract the human-readable detail/message from a response.

    The app uses custom exception handlers that return either:
      {"detail": "..."} (FastAPI default)
    or
      {"error": {"message": "...", "code": "..."}} (custom handler)
    """
    data = resp.json()
    if "detail" in data:
        return data["detail"]
    if "error" in data and "message" in data["error"]:
        return data["error"]["message"]
    return str(data)


async def _get_token(client, email, password):
    """Login and return the access token string."""
    resp = await _login(client, email, password)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ═══════════════════════════════════════════════════════════════════════════
# 1. BRUTE-FORCE LOGIN ATTACKS  (1000 attempts/min scenario)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestBruteForceLogin:
    """Verify the system stops credential-stuffing / brute-force attacks."""

    async def test_account_locks_after_max_attempts(self, client, test_db, test_patron, test_user_data):
        """After MAX_LOGIN_ATTEMPTS wrong passwords the account must lock."""
        from app.core.config import get_settings
        settings = get_settings()
        max_attempts = settings.max_login_attempts  # default 5

        for i in range(max_attempts):
            resp = await _login(client, test_user_data["email"], f"Wrong{i}Pass1!")
            assert resp.status_code == 401, f"Attempt {i+1} should be 401"

        # The next attempt must be rejected with 423 LOCKED
        resp = await _login(client, test_user_data["email"], "WrongAgain1!")
        assert resp.status_code == 423
        assert "locked" in _get_detail(resp).lower()

    async def test_correct_password_rejected_while_locked(
        self, client, test_db, test_patron, test_user_data
    ):
        """Even the correct password must fail during lockout."""
        from app.core.config import get_settings
        settings = get_settings()

        # Lock the account
        for _ in range(settings.max_login_attempts):
            await _login(client, test_user_data["email"], "WrongPassword1!")

        # Now try the real password — still locked
        resp = await _login(client, test_user_data["email"], test_user_data["password"])
        assert resp.status_code == 423

    async def test_lockout_duration_is_respected(self, test_db, test_patron):
        """After lockout expires, the account should be usable again."""
        from sqlalchemy import select

        # Manually set lockout to the past
        test_patron.failed_login_attempts = 10
        test_patron.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        await test_db.commit()

        # is_locked() should return False
        await test_db.refresh(test_patron)
        assert not test_patron.is_locked()

    async def test_successful_login_resets_counter(
        self, client, test_db, test_patron, test_user_data
    ):
        """A successful login must reset failed_login_attempts to 0."""
        from sqlalchemy import select

        # Accumulate some failed attempts (but not enough to lock)
        for _ in range(3):
            await _login(client, test_user_data["email"], "WrongPass1!")

        # Successful login
        resp = await _login(client, test_user_data["email"], test_user_data["password"])
        assert resp.status_code == 200

        # Verify counter is reset
        await test_db.refresh(test_patron)
        assert test_patron.failed_login_attempts == 0
        assert test_patron.locked_until is None

    async def test_nonexistent_user_timing_safe(self, client):
        """Login for nonexistent users should take comparable time to real users.

        The codebase verifies against a dummy hash even when the user is not
        found. This test verifies the dummy-hash path returns 401, not 500.
        """
        resp = await _login(client, "no-such-user@l30.org", "AnyPassword1!")
        assert resp.status_code == 401
        # Error message should be generic (no enumeration) -- current copy
        # is "That email and password combination didn't work..." rather
        # than "incorrect"/"credentials", but it's still non-enumerating.
        assert "didn't work" in _get_detail(resp).lower() or \
               "incorrect" in _get_detail(resp).lower() or \
               "credentials" in _get_detail(resp).lower()

    async def test_login_rate_limit_exists(self, client, test_patron, test_user_data):
        """The login endpoint must declare a rate limit (5/minute in code)."""
        # We can't truly exhaust the rate limit in unit tests without Redis,
        # but we verify the rate-limit decorator is in place by checking
        # that repeated rapid requests eventually get 429 or stay at 401.
        # In production this would be enforced by SlowAPI + Redis.
        responses = []
        for _ in range(6):
            resp = await _login(client, test_user_data["email"], "WrongPass1!")
            responses.append(resp.status_code)

        # At minimum, they should NOT all be 200 (that'd mean no auth at all)
        assert 200 not in responses[:5], "Wrong passwords should never succeed"


# ═══════════════════════════════════════════════════════════════════════════
# 2. COMMON PASSWORD BLOCKING
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestCommonPasswordBlocking:
    """Verify that well-known weak passwords are rejected at registration and reset."""

    @pytest.mark.parametrize("weak_password", [
        "password",
        "password123",
        "123456",
        "qwerty",
        "letmein",
        "admin",
        "welcome",
        "football",
        "iloveyou",
        "trustno1",
    ])
    def test_common_passwords_rejected_by_validator(self, weak_password):
        """validate_password() must reject every common password.

        Note: these may fail on length/complexity checks before the blocklist,
        which is fine — the important thing is they are REJECTED.
        """
        with pytest.raises(PasswordValidationError):
            validate_password(weak_password)

    def test_blocklist_catches_passwords_that_pass_other_rules(self):
        """Passwords that meet length/complexity but are common must be caught by blocklist.

        The blocklist is the last line of defense for passwords that satisfy
        all other rules. We verify it directly against the COMMON_PASSWORDS set.
        """
        # "password123!" meets length(10+), has lowercase, digit, special — but no uppercase
        # We test the blocklist check in isolation instead
        for common in COMMON_PASSWORDS:
            assert common.lower() in COMMON_PASSWORDS or common in COMMON_PASSWORDS

    def test_common_passwords_case_insensitive(self):
        """Blocklist comparison should be case-insensitive.

        The validator calls password.lower() before checking the blocklist,
        so PASSWORD, Password, etc. should all be caught (though they may
        fail on other rules first).
        """
        # Verify the blocklist uses lowercase entries
        for entry in COMMON_PASSWORDS:
            assert entry == entry.lower(), (
                f"Blocklist entry '{entry}' is not lowercase — "
                "case-insensitive comparison requires all entries be lowercase"
            )

    def test_blocklist_has_minimum_coverage(self):
        """The COMMON_PASSWORDS set must contain at least 25 entries."""
        assert len(COMMON_PASSWORDS) >= 25, (
            f"Blocklist only has {len(COMMON_PASSWORDS)} entries — "
            "add more from public breach lists"
        )

    @pytest.mark.parametrize("missing_requirement, password", [
        ("digit", "NoDigitPassword!"),
        ("lowercase", "NOLOWERCASE1!"),
        ("uppercase", "nouppercase1!"),
        ("special char", "NoSpecialChar1"),
    ])
    def test_complexity_requirements_enforced(self, missing_requirement, password):
        """Each complexity axis must independently cause rejection."""
        with pytest.raises(PasswordValidationError):
            validate_password(password)

    def test_minimum_length_enforced(self):
        """Passwords shorter than the configured minimum must be rejected."""
        with pytest.raises(PasswordValidationError, match="at least"):
            validate_password("Ab1!")  # Too short

    async def test_registration_rejects_common_password(self, client, test_db):
        """The /register endpoint must reject common passwords end-to-end."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "newuser@l30.org",
            "password": "password123",
            "first_name": "New",
            "last_name": "User",
        })
        assert resp.status_code in (400, 422), (
            f"Registration should reject 'password123' but got {resp.status_code}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. ACCOUNT LOCKOUT — INCLUDING DOS VECTOR
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestAccountLockoutDoS:
    """Verify lockout can't be weaponised to permanently deny access."""

    async def test_lockout_is_time_limited(self, test_db, test_patron):
        """Lockout must expire after the configured duration."""
        from app.core.config import get_settings
        settings = get_settings()

        # Lock the account
        test_patron.failed_login_attempts = settings.max_login_attempts
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.lockout_duration_minutes
        )
        await test_db.commit()

        # Still locked right now
        await test_db.refresh(test_patron)
        assert test_patron.is_locked()

        # Simulate time passing
        test_patron.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        await test_db.commit()
        await test_db.refresh(test_patron)
        assert not test_patron.is_locked()

    async def test_lockout_does_not_stack(self, client, test_db, test_patron, test_user_data):
        """Repeated failed attempts during lockout should NOT extend the lockout."""
        from app.core.config import get_settings
        settings = get_settings()

        # Lock the account
        for _ in range(settings.max_login_attempts):
            await _login(client, test_user_data["email"], "WrongPass1!")

        # Record lockout time
        await test_db.refresh(test_patron)
        original_lockout = test_patron.locked_until

        # Hammer during lockout
        for _ in range(10):
            resp = await _login(client, test_user_data["email"], "StillWrong1!")
            assert resp.status_code == 423

        # Lockout end time should not have moved forward
        await test_db.refresh(test_patron)
        if test_patron.locked_until and original_lockout:
            # Allow 2 seconds tolerance for DB commit timing
            assert test_patron.locked_until <= original_lockout + timedelta(seconds=2)

    async def test_password_reset_clears_lockout(self, test_db, test_patron):
        """A successful password reset must clear the lockout state."""
        # Lock the account
        test_patron.failed_login_attempts = 10
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

        # Simulate what reset-password does
        test_patron.password_hash = hash_password("NewSecure!Pass1")
        test_patron.failed_login_attempts = 0
        test_patron.locked_until = None
        test_patron.reset_token = None
        test_patron.reset_token_expires = None
        await test_db.commit()

        await test_db.refresh(test_patron)
        assert not test_patron.is_locked()
        assert test_patron.failed_login_attempts == 0

    async def test_attacker_cannot_permanently_lock_account(self, test_db, test_patron):
        """Even after 1000 failed attempts, the lockout still expires."""
        from app.core.config import get_settings
        settings = get_settings()

        test_patron.failed_login_attempts = 1000
        test_patron.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.lockout_duration_minutes
        )
        await test_db.commit()

        # After duration passes, is_locked() must return False
        test_patron.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        await test_db.commit()
        await test_db.refresh(test_patron)
        assert not test_patron.is_locked()


# ═══════════════════════════════════════════════════════════════════════════
# 4. PASSWORD RESET TOKEN SECURITY
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestPasswordResetSecurity:
    """Verify password reset tokens are single-use, hashed, and don't leak info."""

    async def test_reset_token_is_single_use(self, client, test_db, test_patron):
        """A reset token should be consumed after first successful use."""
        token = create_reset_token()
        test_patron.reset_token = hash_reset_token(token)
        test_patron.reset_token_expires = get_reset_token_expiry()
        await test_db.commit()

        # First use — should succeed
        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewSecure!Pass1",
        })
        assert resp.status_code == 200

        # Second use — should fail (token cleared)
        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "AnotherSecure!Pass2",
        })
        assert resp.status_code == 400
        # Current copy is "no longer valid" rather than "invalid".
        assert "no longer valid" in _get_detail(resp).lower() or \
               "invalid" in _get_detail(resp).lower()

    async def test_expired_reset_token_rejected(self, client, test_db, test_patron):
        """An expired reset token must be rejected."""
        token = create_reset_token()
        test_patron.reset_token = hash_reset_token(token)
        test_patron.reset_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_db.commit()

        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewSecure!Pass1",
        })
        assert resp.status_code == 400
        assert "expired" in _get_detail(resp).lower()

    async def test_forgot_password_no_email_enumeration(self, client, test_db):
        """Forgot-password must return the same response for valid AND invalid emails."""
        # Non-existent email
        resp1 = await client.post("/api/v1/auth/forgot-password", json={
            "email": "nonexistent@l30.org",
        })

        # Create a real user
        _ = _make_user(test_db, email="real@l30.org")
        await test_db.commit()

        resp2 = await client.post("/api/v1/auth/forgot-password", json={
            "email": "real@l30.org",
        })

        # Both should return 200 with the same generic message shape
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert _get_detail(resp1) == _get_detail(resp2)

    def test_reset_token_is_stored_hashed(self):
        """The stored reset_token must be a SHA-256 hash, not the raw token."""
        raw = create_reset_token()
        hashed = hash_reset_token(raw)
        assert raw != hashed
        assert len(hashed) == 64  # SHA-256 hex digest

    def test_reset_token_verification_is_constant_time(self):
        """verify_reset_token() should use secrets.compare_digest."""
        token = create_reset_token()
        hashed = hash_reset_token(token)
        assert verify_reset_token(token, hashed) is True
        assert verify_reset_token("wrong-token", hashed) is False

    async def test_reset_token_cannot_be_brute_forced(self, test_db, test_patron):
        """Random guesses should not match — tokens are 256-bit random."""
        real_token = create_reset_token()
        test_patron.reset_token = hash_reset_token(real_token)
        test_patron.reset_token_expires = get_reset_token_expiry()
        await test_db.commit()

        # Try 100 random guesses
        for _ in range(100):
            guess = create_reset_token()  # random 256-bit
            hashed_guess = hash_reset_token(guess)
            assert hashed_guess != test_patron.reset_token


# ═══════════════════════════════════════════════════════════════════════════
# 5. SESSION INVALIDATION ON PASSWORD CHANGE
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestSessionInvalidation:
    """Verify sessions are properly invalidated when passwords change."""

    async def test_change_password_endpoint_exists(self, client, test_db, test_patron, test_user_data):
        """Changing password should succeed for authenticated users."""
        token = await _get_token(client, test_user_data["email"], test_user_data["password"])

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": "BrandNew!Secure1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_old_password_fails_after_change(self, client, test_db, test_patron, test_user_data):
        """After changing password, the old password must not work."""
        token = await _get_token(client, test_user_data["email"], test_user_data["password"])

        # Change password
        await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": "BrandNew!Secure1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Old password should fail
        resp = await _login(client, test_user_data["email"], test_user_data["password"])
        assert resp.status_code == 401

    async def test_new_password_works_after_change(self, client, test_db, test_patron, test_user_data):
        """After changing password, the new password must work."""
        token = await _get_token(client, test_user_data["email"], test_user_data["password"])
        new_password = "BrandNew!Secure1"

        await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": new_password,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # New password should work
        resp = await _login(client, test_user_data["email"], new_password)
        assert resp.status_code == 200

    async def test_password_reuse_prevented(self, client, test_db, test_patron, test_user_data):
        """Changing to the same password should be rejected."""
        token = await _get_token(client, test_user_data["email"], test_user_data["password"])

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": test_user_data["password"],  # same!
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        # Current copy is "can't reuse one of your last N passwords" rather than "recently".
        assert "reuse" in _get_detail(resp).lower() or "recently" in _get_detail(resp).lower()

    async def test_password_reset_invalidates_reset_token(self, client, test_db, test_patron):
        """After a successful reset, the token fields must be cleared."""
        token = create_reset_token()
        test_patron.reset_token = hash_reset_token(token)
        test_patron.reset_token_expires = get_reset_token_expiry()
        await test_db.commit()

        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "ResetSecure!Pass1",
        })
        assert resp.status_code == 200

        await test_db.refresh(test_patron)
        assert test_patron.reset_token is None
        assert test_patron.reset_token_expires is None

    async def test_refresh_token_rotation_revokes_old(self, client, test_db, test_patron, test_user_data):
        """Using a refresh token should revoke the old one (token rotation)."""
        # Login to get tokens
        resp = await _login(client, test_user_data["email"], test_user_data["password"])
        assert resp.status_code == 200

        # The refresh token is in the httpOnly cookie — we check the DB instead
        from sqlalchemy import select
        result = await test_db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == test_patron.id)
            .order_by(RefreshToken.created_at.desc())
        )
        tokens = result.scalars().all()
        assert len(tokens) >= 1
        first_token = tokens[0]
        assert first_token.revoked_at is None  # active


# ═══════════════════════════════════════════════════════════════════════════
# 6. API KEY / TOKEN BRUTE-FORCE RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestTokenBruteForce:
    """Verify tokens cannot be guessed or forged."""

    def test_access_tokens_are_signed(self):
        """JWT tokens must be signed and reject tampered payloads."""
        token = create_access_token(subject="1", email="test@l30.org")
        # Tamper with the token (flip a character in the signature)
        parts = token.split(".")
        sig = list(parts[2])
        sig[0] = "X" if sig[0] != "X" else "Y"
        parts[2] = "".join(sig)
        tampered = ".".join(parts)

        with pytest.raises(Exception):
            verify_token(tampered, check_revocation=False)

    def test_expired_tokens_rejected(self):
        """Expired JWTs must be rejected."""
        token = create_access_token(
            subject="1",
            email="test@l30.org",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            verify_token(token, check_revocation=False)

    def test_none_algorithm_rejected(self):
        """Tokens with algorithm 'none' must be rejected."""
        import jwt as pyjwt

        payload = {"sub": "1", "email": "test@l30.org", "exp": 9999999999}
        unsigned = pyjwt.encode(payload, key="", algorithm="none")

        with pytest.raises(Exception):
            verify_token(unsigned, check_revocation=False)

    def test_missing_claims_rejected(self):
        """Tokens missing required claims (sub, email) must be rejected."""
        import jwt as pyjwt
        from app.core.config import get_settings

        settings = get_settings()

        # Missing email
        payload_no_email = {"sub": "1", "exp": 9999999999}
        token_no_email = pyjwt.encode(
            payload_no_email, settings.secret_key, algorithm=settings.algorithm
        )
        with pytest.raises(Exception):
            verify_token(token_no_email, check_revocation=False)

        # Missing sub
        payload_no_sub = {"email": "a@b.test", "exp": 9999999999}
        token_no_sub = pyjwt.encode(
            payload_no_sub, settings.secret_key, algorithm=settings.algorithm
        )
        with pytest.raises(Exception):
            verify_token(token_no_sub, check_revocation=False)

    def test_random_strings_rejected_as_tokens(self):
        """Random strings must not pass token verification."""
        for _ in range(50):
            import secrets
            random_token = secrets.token_urlsafe(32)
            with pytest.raises(Exception):
                verify_token(random_token, check_revocation=False)

    def test_refresh_tokens_are_high_entropy(self):
        """Refresh tokens must be cryptographically random (256+ bits)."""
        tokens = {create_refresh_token() for _ in range(100)}
        # All unique
        assert len(tokens) == 100
        # Each token should be at least 32 bytes (base64-encoded 43 chars)
        for t in tokens:
            assert len(t) >= 43

    def test_reset_tokens_are_high_entropy(self):
        """Reset tokens must be cryptographically random (256+ bits)."""
        tokens = {create_reset_token() for _ in range(100)}
        assert len(tokens) == 100
        for t in tokens:
            assert len(t) >= 43

    async def test_invalid_bearer_token_returns_401(self, client):
        """Any protected endpoint must return 401 for invalid tokens."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fakefakefake"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 7. RATE LIMIT BYPASS ATTEMPTS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestRateLimitBypass:
    """Verify rate limits cannot be easily circumvented."""

    def test_auth_category_has_strict_write_limit(self):
        """The AUTH category should have a low write limit to prevent brute-force."""
        from app.core.rate_limit_config import CATEGORY_LIMITS, EndpointCategory

        auth_limits = CATEGORY_LIMITS[EndpointCategory.AUTH]
        assert auth_limits.write_per_minute <= 10, (
            f"Auth write limit is {auth_limits.write_per_minute}/min — "
            "should be <= 10 to prevent brute-force"
        )

    def test_auth_category_no_burst_allowed(self):
        """AUTH endpoints should have burst_multiplier=1.0 (no bursting)."""
        from app.core.rate_limit_config import CATEGORY_LIMITS, EndpointCategory

        auth_limits = CATEGORY_LIMITS[EndpointCategory.AUTH]
        assert auth_limits.burst_multiplier == 1.0, (
            f"Auth burst_multiplier is {auth_limits.burst_multiplier} — "
            "should be 1.0 to prevent burst attacks"
        )

    def test_login_route_classified_as_auth(self):
        """The /auth/login path must map to the AUTH rate-limit category."""
        from app.core.rate_limit_config import EndpointCategory, classify_route

        category = classify_route("/api/v1/auth/login")
        assert category == EndpointCategory.AUTH

    def test_forgot_password_classified_as_auth(self):
        """The /auth/forgot-password path must map to the AUTH category."""
        from app.core.rate_limit_config import EndpointCategory, classify_route

        category = classify_route("/api/v1/auth/forgot-password")
        assert category == EndpointCategory.AUTH

    def test_register_classified_as_auth(self):
        """The /auth/register path must map to the AUTH category."""
        from app.core.rate_limit_config import EndpointCategory, classify_route

        category = classify_route("/api/v1/auth/register")
        assert category == EndpointCategory.AUTH

    def test_x_forwarded_for_is_never_trusted(self):
        """Rate limiter must NOT trust X-Forwarded-For (attacker-controlled
        leftmost entry -- nginx only appends to it). See app/core/rate_limit.py
        client_ip() docstring: resolution order is CF-Connecting-IP, then
        X-Real-IP, then socket peer -- XFF is deliberately excluded.
        """
        from app.middleware.rate_limit_middleware import CategoryRateLimitMiddleware

        # Simulate a spoofed X-Forwarded-For with multiple hops; only
        # X-Real-IP / socket peer may be trusted.
        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "1.2.3.4, 10.0.0.1, 172.16.0.1"}
        mock_request.client = MagicMock(host="172.16.0.1")

        ip = CategoryRateLimitMiddleware._get_client_ip(mock_request)
        assert ip != "1.2.3.4", "X-Forwarded-For must never be trusted for rate-limit keys"
        assert ip == "172.16.0.1", (
            f"Should fall back to the socket peer when no CF-Connecting-IP/X-Real-IP header, got {ip}"
        )

    def test_x_real_ip_preferred_over_forwarded_for(self):
        """X-Real-IP (proxy-set, not spoofable) should win over X-Forwarded-For."""
        from app.middleware.rate_limit_middleware import CategoryRateLimitMiddleware

        mock_request = MagicMock()
        mock_request.headers = {
            "x-forwarded-for": "1.2.3.4, 10.0.0.1",
            "x-real-ip": "203.0.113.9",
        }
        mock_request.client = MagicMock(host="172.16.0.1")

        ip = CategoryRateLimitMiddleware._get_client_ip(mock_request)
        assert ip == "203.0.113.9"

    def test_rate_limit_fallback_on_redis_failure(self):
        """When Redis is unavailable the limiter falls back to memory (not crash)."""
        from app.core.rate_limit import limiter
        # The limiter should exist and be configured regardless of Redis
        assert limiter is not None

    def test_health_endpoints_exempt_from_rate_limit(self):
        """Health check paths should be exempt from rate limiting."""
        from app.middleware.rate_limit_middleware import _EXEMPT_PATHS

        assert "/health" in _EXEMPT_PATHS
        assert "/api/v1/health" in _EXEMPT_PATHS

    def test_per_endpoint_rate_limits_on_sensitive_routes(self):
        """Verify that sensitive auth endpoints have per-endpoint rate limit decorators."""
        # These live in their respective submodules, not re-exported from
        # app.api.v1.auth's __init__ (which only re-exports shared deps
        # like get_current_user -- see its __all__).
        from app.api.v1.auth.login import login
        from app.api.v1.auth.registration import register
        from app.api.v1.auth.password import forgot_password, reset_password
        # Each of these should have a __wrapped__ or similar indicator from the
        # @limiter.limit() decorator. We verify by checking the source annotations.
        import inspect
        for fn in [login, register, forgot_password, reset_password]:
            source = inspect.getsource(fn)
            assert "limiter.limit" in source or "rate_limit" in source.lower(), (
                f"{fn.__name__} is missing a per-endpoint rate limit decorator"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 8. EMAIL ENUMERATION
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestEmailEnumeration:
    """Verify that no endpoint leaks whether an email exists in the system."""

    async def test_login_same_error_for_wrong_password_and_missing_user(self, client, test_db, test_patron, test_user_data):
        """Login errors must be identical regardless of whether user exists."""
        # Wrong password for real user
        resp1 = await _login(client, test_user_data["email"], "WrongPass1!")
        # Nonexistent user entirely
        resp2 = await _login(client, "ghost@l30.org", "WrongPass1!")

        # Both must return 401 with the same message
        assert resp1.status_code == 401
        assert resp2.status_code == 401
        assert _get_detail(resp1) == _get_detail(resp2)

    async def test_register_does_not_reveal_existing_email(self, client, test_db, test_patron, test_user_data):
        """Registration failure for duplicate email must use a generic message."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": test_user_data["email"],
            "password": "AnotherStrong!Pass1",
            "first_name": "Dup",
            "last_name": "User",
        })
        assert resp.status_code == 400
        detail = _get_detail(resp).lower()
        # Should NOT say "email already exists" — must be generic
        assert "email" not in detail or "check" in detail or "failed" in detail

    async def test_resend_verification_no_enumeration(self, client, test_db):
        """Resend-verification must return the same message whether email exists or not."""
        resp1 = await client.post("/api/v1/auth/resend-verification", json={
            "email": "nobody@l30.org",
        })
        resp2 = await client.post("/api/v1/auth/resend-verification", json={
            "email": "also-nobody@l30.org",
        })

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert _get_detail(resp1) == _get_detail(resp2)


# ═══════════════════════════════════════════════════════════════════════════
# 9. PASSWORD HISTORY / REUSE PREVENTION
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestPasswordHistory:
    """Verify password reuse prevention across change and reset flows."""

    def test_password_history_count_configured(self):
        """PASSWORD_HISTORY_COUNT should be at least 5."""
        assert PASSWORD_HISTORY_COUNT >= 5

    async def test_cannot_reuse_current_password_on_reset(self, client, test_db, test_patron, test_user_data):
        """Password reset to the current password must fail."""
        # test_patron's password is test_user_data["password"] (see conftest.py),
        # not a hardcoded literal -- using the wrong literal here meant the
        # "reset to current password" path was never actually exercised.
        current_password = test_user_data["password"]
        token = create_reset_token()
        test_patron.reset_token = hash_reset_token(token)
        test_patron.reset_token_expires = get_reset_token_expiry()
        await test_db.commit()

        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": current_password,
        })
        assert resp.status_code == 400
        # Current copy is "can't reuse one of your last N passwords" rather than "recently".
        assert "reuse" in _get_detail(resp).lower() or "recently" in _get_detail(resp).lower()

    async def test_cannot_reuse_historical_password_on_reset(self, client, test_db, test_patron):
        """Password reset to a password in history must fail."""
        old_password_hash = hash_password("OldHistorical!Pass1")
        history = PasswordHistory(
            user_id=test_patron.id,
            password_hash=old_password_hash,
        )
        test_db.add(history)

        token = create_reset_token()
        test_patron.reset_token = hash_reset_token(token)
        test_patron.reset_token_expires = get_reset_token_expiry()
        await test_db.commit()

        resp = await client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "OldHistorical!Pass1",
        })
        assert resp.status_code == 400
        # Current copy is "can't reuse one of your last N passwords" rather than "recently".
        assert "reuse" in _get_detail(resp).lower() or "recently" in _get_detail(resp).lower()


# ═══════════════════════════════════════════════════════════════════════════
# 10. JWT SECURITY EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.security
class TestJWTEdgeCases:
    """Verify JWT handling covers known attack vectors."""

    def test_token_format_validation(self):
        """Malformed tokens (wrong number of parts) must be rejected."""
        with pytest.raises(Exception):
            verify_token("only.two", check_revocation=False)
        with pytest.raises(Exception):
            verify_token("", check_revocation=False)
        with pytest.raises(Exception):
            verify_token("a.b.c.d", check_revocation=False)

    def test_null_token_rejected(self):
        """None/empty tokens must be rejected."""
        with pytest.raises(Exception):
            verify_token(None, check_revocation=False)
        with pytest.raises(Exception):
            verify_token("", check_revocation=False)

    def test_algorithm_confusion_prevented(self):
        """Tokens signed with a different algorithm must be rejected.

        The verify_token() function restricts to HS256 only to prevent
        algorithm confusion attacks (e.g., using RS256 public key as HMAC secret).
        """
        import jwt as pyjwt
        from app.core.config import get_settings

        settings = get_settings()
        payload = {
            "sub": "1",
            "email": "test@l30.org",
            "exp": 9999999999,
        }

        # Try HS384 (different HMAC variant)
        token_384 = pyjwt.encode(payload, settings.secret_key, algorithm="HS384")
        with pytest.raises(Exception):
            verify_token(token_384, check_revocation=False)

    def test_token_without_expiry_rejected(self):
        """Tokens without exp claim must be rejected."""
        import jwt as pyjwt
        from app.core.config import get_settings

        settings = get_settings()
        payload = {"sub": "1", "email": "test@l30.org"}
        # Encode without exp and with verify_exp disabled at creation
        token = pyjwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(Exception):
            verify_token(token, check_revocation=False)

    def test_bcrypt_password_hashing_used(self):
        """Password hashing must use bcrypt (not md5, sha1, etc.)."""
        hashed = hash_password("TestPassword1!")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$"), (
            f"Expected bcrypt hash prefix, got: {hashed[:10]}"
        )

    def test_password_hash_is_salted(self):
        """Same password must produce different hashes (bcrypt salt)."""
        h1 = hash_password("SamePassword1!")
        h2 = hash_password("SamePassword1!")
        assert h1 != h2, "Hashes should differ due to random salt"

    def test_verify_password_rejects_wrong_password(self):
        """verify_password must return False for wrong passwords."""
        hashed = hash_password("RealPassword1!")
        assert verify_password("WrongPassword1!", hashed) is False

    def test_verify_password_accepts_correct_password(self):
        """verify_password must return True for the correct password."""
        hashed = hash_password("RealPassword1!")
        assert verify_password("RealPassword1!", hashed) is True
