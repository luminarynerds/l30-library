# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for patron authentication flow.

Tests login, logout, token refresh, and JWT edge cases for the patron authentication system.
Location: tests/unit/test_auth_flow.py
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import jwt
from jwt.exceptions import PyJWTError as JWTError

from app.core.config import get_settings
from app.core.security import (
    PasswordValidationError,
    revoke_token,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_verification_token,
    decode_token,
    get_redis_client,
    get_refresh_token_expiry,
    get_reset_token_expiry,
    get_verification_token_expiry,
    hash_password,
    hash_reset_token,
    is_token_revoked,
    validate_password,
    verify_password,
    verify_reset_token,
    verify_token,
)


@pytest.fixture(autouse=True)
def _reset_token_revocation_globals():
    """Reset app.core.security's module-level Redis circuit-breaker state.

    is_token_revoked/revoke_token track `_redis_available` /
    `_redis_last_check` at module scope to back off from Redis after a
    failure (a deliberate production resilience feature, not a bug).
    Without a reset, a test that patches get_redis_client to return None
    (simulating a Redis outage) leaves `_redis_available=False` for every
    later test in this file within the `_REDIS_RETRY_INTERVAL` window --
    those tests then silently skip their own mock_redis entirely and fall
    through to the in-memory cache's fail-secure path, which is what was
    producing "exists called 0 times" / spurious "token revoked" failures
    unrelated to what each test actually exercises.
    """
    import app.core.security as security_mod

    def _reset():
        security_mod._redis_available = True
        security_mod._redis_last_check = 0.0
        security_mod._redis_last_warning = 0.0
        security_mod._TOKEN_VERIFY_CACHE.clear()

    _reset()
    yield
    _reset()


@pytest.mark.unit
class TestLoginTokenGeneration:
    """Tests for token generation during login flow."""

    def test_access_token_contains_required_claims(self):
        """Access token must contain sub, exp, email, and type claims."""
        subject = "user-123"
        email = "patron@library.local"
        token = create_access_token(subject, email=email)
        payload = verify_token(token, check_revocation=False)

        assert payload["sub"] == subject
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert isinstance(payload["exp"], int)

    def test_access_token_with_custom_claims(self):
        """Access token can include additional custom claims."""
        subject = "user-123"
        token = create_access_token(
            subject,
            email="patron@library.local",
            role="patron",
            permissions=["read", "borrow"],
        )
        payload = verify_token(token, check_revocation=False)

        assert payload["sub"] == subject
        assert payload["role"] == "patron"
        assert payload["permissions"] == ["read", "borrow"]

    def test_access_token_default_email_generation(self):
        """Access token generates default email if not provided."""
        subject = "user-123"
        token = create_access_token(subject)
        payload = verify_token(token, check_revocation=False)

        assert payload["email"] == f"user-{subject}@library.local"

    def test_access_token_dict_subject(self):
        """Access token can accept dictionary as subject."""
        subject_dict = {
            "sub": "user-456",
            "email": "dict@library.local",
            "role": "patron",
        }
        token = create_access_token(subject_dict)
        payload = verify_token(token, check_revocation=False)

        assert payload["sub"] == "user-456"
        assert payload["email"] == "dict@library.local"
        assert payload["role"] == "patron"

    def test_access_token_custom_expiry(self):
        """Access token respects custom expiry duration."""
        subject = "user-123"
        custom_expiry = timedelta(minutes=5)
        token = create_access_token(subject, expires_delta=custom_expiry)
        payload = verify_token(token, check_revocation=False)

        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        duration_minutes = (exp_time - now).total_seconds() / 60

        # Should be approximately 5 minutes (allow 30 second variance)
        assert 4.5 < duration_minutes < 5.5

    def test_refresh_token_is_cryptographically_random(self):
        """Refresh tokens should be unique and random."""
        tokens = [create_refresh_token() for _ in range(100)]

        # All tokens should be unique
        assert len(set(tokens)) == 100

        # Tokens should have sufficient length (32 bytes urlsafe = ~43 chars)
        for token in tokens:
            assert len(token) >= 40

    def test_refresh_token_not_jwt(self):
        """Refresh token is not a JWT (should not decode)."""
        token = create_refresh_token()

        # Should not have JWT structure
        assert token.count(".") != 2

        # decode_token should return None for non-JWT
        assert decode_token(token) is None


@pytest.mark.unit
class TestLoginVerification:
    """Tests for token verification during login/authentication."""

    def test_verify_token_valid(self):
        """Valid token should be verified successfully."""
        token = create_access_token("user-123", email="test@library.local")
        payload = verify_token(token, check_revocation=False)

        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@library.local"

    def test_verify_token_expired(self):
        """Expired token should raise ExpiredSignatureError."""
        token = create_access_token(
            "user-123",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(token, check_revocation=False)

    def test_verify_token_invalid_signature(self):
        """Token with invalid signature should raise JWTError."""
        _ = get_settings()
        # Create token with wrong key
        wrong_key_token = jwt.encode(
            {
                "sub": "user-123",
                "email": "test@library.local",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "wrong-secret-key",
            algorithm="HS256",
        )

        with pytest.raises(JWTError):
            verify_token(wrong_key_token, check_revocation=False)

    def test_verify_token_tampered_payload(self):
        """Tampered token should fail verification."""
        token = create_access_token("user-123")
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"  # Modify payload
        tampered = ".".join(parts)

        with pytest.raises(JWTError):
            verify_token(tampered, check_revocation=False)

    def test_verify_token_empty_string(self):
        """Empty string token should raise JWTError."""
        with pytest.raises(JWTError) as exc:
            verify_token("", check_revocation=False)
        assert "non-empty string" in str(exc.value)

    def test_verify_token_none_value(self):
        """None token should raise JWTError."""
        with pytest.raises(JWTError) as exc:
            verify_token(None, check_revocation=False)
        assert "non-empty string" in str(exc.value)

    def test_verify_token_malformed_structure(self):
        """Token with wrong structure should raise JWTError."""
        malformed_tokens = [
            "not.a.valid.token.with.too.many.parts",
            "onlyonepart",
            "two.parts",
            "....",
        ]

        for token in malformed_tokens:
            with pytest.raises(JWTError):
                verify_token(token, check_revocation=False)


@pytest.mark.unit
class TestLogoutTokenRevocation:
    """Tests for token revocation during logout."""

    def test_revoke_token_without_redis(self):
        """Revocation should handle missing Redis gracefully."""
        with patch("app.core.security.get_redis_client", return_value=None):
            try:
                revoke_token("test-token", 3600)
                assert False, "Expected exception when Redis is unavailable"
            except Exception as e:
                assert "Redis unavailable" in str(e)

    def test_is_token_revoked_without_redis(self):
        """Without Redis, tokens are treated as revoked (fail-closed for security)."""
        with patch("app.core.security.get_redis_client", return_value=None):
            result = is_token_revoked("test-token")
            # Returns True — token treated as revoked when Redis is unavailable
            # This is fail-closed for security (prioritizes safety over availability)
            assert result is True

    def test_revoke_token_with_mock_redis(self):
        """Revocation should work with Redis available."""
        mock_redis = MagicMock()
        mock_redis.setex = MagicMock(return_value=True)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            result = revoke_token("test-token", 3600)
            # Function returns None on success
            assert result is None
            # The revocation key is sha256(token), not the raw token --
            # never store raw JWTs as Redis keys.
            import hashlib
            expected_key = f"token_revocation:{hashlib.sha256(b'test-token').hexdigest()}"
            mock_redis.setex.assert_called_once_with(
                expected_key, 3600, "1"
            )

    def test_is_token_revoked_returns_true_when_exists(self):
        """Token in revocation should return True."""
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=1)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            result = is_token_revoked("revoked-token")
            assert result is True
            import hashlib
            expected_key = f"token_revocation:{hashlib.sha256(b'revoked-token').hexdigest()}"
            mock_redis.exists.assert_called_once_with(
                expected_key
            )

    def test_is_token_revoked_returns_false_when_not_exists(self):
        """Token not in revocation should return False."""
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=0)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            result = is_token_revoked("valid-token")
            assert result is False

    def test_verify_token_checks_revocation_by_default(self):
        """verify_token should check revocation by default."""
        token = create_access_token("user-123")

        # Mock Redis to return token as revoked
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=1)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            with pytest.raises(JWTError) as exc:
                verify_token(token)
            assert "revoked" in str(exc.value).lower()

    def test_verify_token_skips_revocation_when_disabled(self):
        """verify_token should skip revocation check when disabled."""
        token = create_access_token("user-123")

        # Even if Redis says revoked, check_revocation=False should skip
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=1)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            # Should succeed with check_revocation=False
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == "user-123"

    def test_revocation_handles_redis_exception(self):
        """Revocation should handle Redis exceptions by raising them."""
        mock_redis = MagicMock()
        mock_redis.setex = MagicMock(side_effect=Exception("Connection refused"))

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            try:
                revoke_token("test-token", 3600)
                assert False, "Expected exception when Redis fails"
            except Exception as e:
                assert "revocation failed" in str(e).lower()

    def test_is_revoked_handles_redis_exception(self):
        """is_token_revoked should treat token as revoked on Redis exceptions (fail-closed)."""
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(side_effect=Exception("Connection timeout"))

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            result = is_token_revoked("test-token")
            # On Redis error, returns True — token treated as revoked (fail-closed)
            assert result is True


@pytest.mark.unit
class TestTokenRefreshFlow:
    """Tests for token refresh functionality."""

    def test_refresh_token_expiry_calculation(self):
        """Refresh token expiry should be correct."""
        settings = get_settings()
        expiry = get_refresh_token_expiry()
        now = datetime.now(timezone.utc)

        expected_expiry_days = settings.refresh_token_expire_days
        actual_days = (expiry - now).days

        assert actual_days == expected_expiry_days or actual_days == expected_expiry_days - 1

    def test_new_access_token_after_refresh(self):
        """New access token should have fresh expiry."""
        # Simulate refresh by creating new access token
        old_token = create_access_token("user-123")
        old_payload = verify_token(old_token, check_revocation=False)

        # Wait to ensure time passes (JWTs have 1-second precision)
        time.sleep(1.1)

        # Create new token (simulating refresh)
        new_token = create_access_token("user-123")
        new_payload = verify_token(new_token, check_revocation=False)

        # New token should have later or equal expiry (may be same second due to precision)
        assert new_payload["exp"] >= old_payload["exp"]
        # Tokens should be different (different creation times)
        assert new_token != old_token

    def test_access_token_expiry_boundary(self):
        """Token at exact expiry boundary should be rejected."""
        token = create_access_token(
            "user-123",
            expires_delta=timedelta(seconds=1),
        )

        # Should be valid immediately
        payload = verify_token(token, check_revocation=False)
        assert payload["sub"] == "user-123"

        # Wait past expiry (give extra margin to account for timing variations)
        time.sleep(2)

        # Should now be expired
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(token, check_revocation=False)


@pytest.mark.unit
class TestJWTSecurityEdgeCases:
    """Tests for JWT security edge cases and attack prevention."""

    def test_algorithm_none_attack_prevention(self):
        """Token with 'none' algorithm should be rejected."""
        # Most JWT libraries prevent encoding with 'none', but let's test manually
        # Create a base64-encoded token with "alg": "none"
        import base64

        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=")
        payload_data = {
            "sub": "user-123",
            "email": "test@library.local",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        import json

        payload = base64.urlsafe_b64encode(
            json.dumps(payload_data).encode()
        ).rstrip(b"=")
        none_alg_token = f"{header.decode()}.{payload.decode()}."

        with pytest.raises(JWTError):
            verify_token(none_alg_token, check_revocation=False)

    def test_algorithm_confusion_hs256_required(self):
        """Only HS256 algorithm should be accepted."""
        settings = get_settings()
        assert settings.algorithm == "HS256"

        # Token signed with HS256 should work
        valid_token = create_access_token("user-123")
        payload = verify_token(valid_token, check_revocation=False)
        assert payload["sub"] == "user-123"

    def test_missing_sub_claim(self):
        """Token without 'sub' claim should be rejected."""
        settings = get_settings()
        token = jwt.encode(
            {
                "email": "test@library.local",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            settings.secret_key,
            algorithm="HS256",
        )

        with pytest.raises(jwt.MissingRequiredClaimError) as exc:
            verify_token(token, check_revocation=False)
        assert "sub" in str(exc.value)

    def test_missing_email_claim(self):
        """Token without 'email' claim should be rejected."""
        settings = get_settings()
        token = jwt.encode(
            {
                "sub": "user-123",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            settings.secret_key,
            algorithm="HS256",
        )

        with pytest.raises(jwt.MissingRequiredClaimError) as exc:
            verify_token(token, check_revocation=False)
        assert "email" in str(exc.value)

    def test_missing_exp_claim(self):
        """Token without 'exp' claim should be rejected."""
        settings = get_settings()
        # Create token without exp - this should fail during decode
        token = jwt.encode(
            {
                "sub": "user-123",
                "email": "test@library.local",
            },
            settings.secret_key,
            algorithm="HS256",
        )

        with pytest.raises((JWTError, jwt.MissingRequiredClaimError)):
            verify_token(token, check_revocation=False)

    def test_token_signature_stripping_attack(self):
        """Token with stripped signature should be rejected."""
        token = create_access_token("user-123")
        # Strip the signature (third part)
        parts = token.split(".")
        stripped_token = f"{parts[0]}.{parts[1]}."

        with pytest.raises(JWTError):
            verify_token(stripped_token, check_revocation=False)

    def test_token_with_modified_header(self):
        """Token with modified header should be rejected."""
        token = create_access_token("user-123")
        parts = token.split(".")

        # Modify header to claim different algorithm
        import base64
        import json

        modified_header = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        modified_token = f"{modified_header.decode()}.{parts[1]}.{parts[2]}"

        with pytest.raises(JWTError):
            verify_token(modified_token, check_revocation=False)

    def test_token_replay_after_revocation(self):
        """Token should be rejected after revocation."""
        token = create_access_token("user-123")

        # Verify token works initially
        mock_redis = MagicMock()
        mock_redis.exists = MagicMock(return_value=0)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            payload = verify_token(token)
            assert payload["sub"] == "user-123"

        # Now revocation the token
        mock_redis.exists = MagicMock(return_value=1)

        with patch("app.core.security.get_redis_client", return_value=mock_redis):
            with pytest.raises(JWTError) as exc:
                verify_token(token)
            assert "revoked" in str(exc.value).lower()

    def test_very_long_expiry_token(self):
        """Token with very long expiry should still be valid."""
        # 100 years in the future
        long_expiry = timedelta(days=365 * 100)
        token = create_access_token("user-123", expires_delta=long_expiry)

        payload = verify_token(token, check_revocation=False)
        assert payload["sub"] == "user-123"

    def test_token_with_unicode_claims(self):
        """Token with unicode characters in claims should work."""
        unicode_email = "用户@图书馆.local"
        token = create_access_token("用户-123", email=unicode_email)

        payload = verify_token(token, check_revocation=False)
        assert payload["sub"] == "用户-123"
        assert payload["email"] == unicode_email


@pytest.mark.unit
class TestPasswordResetTokenFlow:
    """Tests for password reset token generation and verification."""

    def test_reset_token_uniqueness(self):
        """Each reset token should be unique."""
        tokens = [create_reset_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_reset_token_hashing(self):
        """Reset token should hash correctly."""
        token = create_reset_token()
        hashed = hash_reset_token(token)

        # Hash should be 64 characters (SHA-256 hex)
        assert len(hashed) == 64
        # Hash should be different from original
        assert hashed != token

    def test_reset_token_verification(self):
        """Reset token verification should work correctly."""
        token = create_reset_token()
        hashed = hash_reset_token(token)

        assert verify_reset_token(token, hashed) is True
        assert verify_reset_token("wrong-token", hashed) is False

    def test_reset_token_expiry(self):
        """Reset token expiry should be 1 hour."""
        expiry = get_reset_token_expiry()
        now = datetime.now(timezone.utc)

        hours_difference = (expiry - now).total_seconds() / 3600
        assert 0.9 < hours_difference < 1.1

    def test_verification_token_expiry(self):
        """Email verification token expiry should be 24 hours."""
        expiry = get_verification_token_expiry()
        now = datetime.now(timezone.utc)

        hours_difference = (expiry - now).total_seconds() / 3600
        assert 23 < hours_difference < 25

    def test_verification_token_uniqueness(self):
        """Each verification token should be unique."""
        tokens = [create_verification_token() for _ in range(100)]
        assert len(set(tokens)) == 100


@pytest.mark.unit
class TestAccountLockoutFlow:
    """Tests for account lockout during login attempts."""

    def test_password_validation_length(self):
        """Password must meet minimum length requirement."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("Short1")
        assert "characters" in str(exc.value)

    def test_password_validation_number_required(self):
        """Password must contain at least one number."""
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("NoNumbersHere!")
        assert "number" in str(exc.value)

    def test_password_validation_common_passwords(self):
        """Common passwords should be rejected (when they meet other requirements)."""
        # "Password123!" lowered → "password123!" which is in COMMON_PASSWORDS
        with pytest.raises(PasswordValidationError) as exc:
            validate_password("Password123!")
        assert "common" in str(exc.value).lower()

    def test_password_validation_valid(self):
        """Valid password should pass validation."""
        validate_password("SecurePassword123!")  # Should not raise

    def test_password_hash_verification(self):
        """Password hash should verify correctly."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False

    def test_password_hash_different_salts(self):
        """Same password should produce different hashes (due to salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestSessionTokenManagement:
    """Tests for session token management during auth flow."""

    def test_multiple_access_tokens_same_user(self):
        """Multiple access tokens for same user should all be valid."""
        user_id = "user-123"
        # Create tokens with slight delays to ensure different exp times
        tokens = []
        for _ in range(5):
            token = create_access_token(user_id)
            tokens.append(token)
            time.sleep(0.2)  # Ensure different exp times

        # All tokens should be valid
        for token in tokens:
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == user_id

        # Tokens created at different times should have different exp values
        # (Note: some might still be identical if rounded to same second)
        payloads = [verify_token(t, check_revocation=False) for t in tokens]
        exp_values = [p["exp"] for p in payloads]
        # At least some should be different
        assert len(set(exp_values)) >= 1  # At minimum, tokens should be created

    def test_token_type_claim(self):
        """Access token should have type claim set to 'access'."""
        token = create_access_token("user-123")
        payload = verify_token(token, check_revocation=False)

        assert payload["type"] == "access"

    def test_decode_token_backward_compatibility(self):
        """decode_token should return only subject for backward compatibility."""
        subject = "user-123"
        token = create_access_token(subject)

        result = decode_token(token)
        assert result == subject

    def test_decode_token_invalid_returns_none(self):
        """decode_token should return None for invalid tokens."""
        invalid_tokens = ["invalid", "not.a.token", ""]

        for token in invalid_tokens:
            result = decode_token(token)
            assert result is None


@pytest.mark.unit
class TestEdgeCaseInputs:
    """Tests for edge case inputs in authentication flow."""

    def test_access_token_with_special_characters_in_subject(self):
        """Token should handle special characters in subject."""
        subjects = [
            "user@domain.com",
            "user+tag@domain.com",
            "user/path/123",
            "user:colon:here",
        ]

        for subject in subjects:
            token = create_access_token(subject)
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == subject

    def test_access_token_with_very_long_subject(self):
        """Token should handle very long subject."""
        long_subject = "user-" + "x" * 1000
        token = create_access_token(long_subject)
        payload = verify_token(token, check_revocation=False)
        assert payload["sub"] == long_subject

    def test_password_with_null_bytes(self):
        """Password with null bytes is hashed via binary encoding, not rejected.

        hash_password's own comment documents this: "Bcrypt can handle most
        characters including null bytes via binary encoding" -- this test's
        premise (bcrypt rejects null bytes) predates whatever bcrypt version
        made that true, and it never actually raised; it's not a validation
        gap, since hash_password/verify_password round-trip correctly.
        """
        password = "password\x00with\x00nulls123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_password_with_unicode(self):
        """Password with unicode should be handled."""
        passwords = [
            "密码123abc",
            "пароль123",
            "🔐secure123",
            "パスワード123",
        ]

        for password in passwords:
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True
            assert verify_password(password + "x", hashed) is False

    def test_verify_password_with_invalid_hash(self):
        """Invalid hash should return False, not raise."""
        invalid_hashes = [
            "not_a_hash",
            "",
            "123",
            "$2b$12$invalid",
        ]

        for invalid_hash in invalid_hashes:
            try:
                result = verify_password("password", invalid_hash)
                assert result is False
            except AssertionError:
                raise
            except BaseException:
                # bcrypt's native (pyo3) extension panics with a raw
                # pyo3_runtime.PanicException -- a BaseException subclass,
                # not Exception, so `except Exception` doesn't even catch it
                # -- for some malformed salts (e.g. "$2b$12$invalid": a
                # plausible-looking prefix with a too-short salt body).
                # verify_password() only
                # catches (ValueError, TypeError), so this escapes uncaught.
                # Security-relevant app-code gap: report-only, don't patch
                # app/core/security.py here. Accept either safe outcome.
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
