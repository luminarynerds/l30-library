# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for authentication module.
"""

from datetime import datetime, timedelta, timezone

import pytest
import jwt
from jwt.exceptions import PyJWTError as JWTError

from app.core.config import get_settings
from app.core.security import (PasswordValidationError, revoke_token,
                               create_access_token, create_refresh_token,
                               decode_token, hash_password,
                               is_token_revoked, validate_password,
                               verify_password, verify_token)
from app.core.datetime_utils import utc_now


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_creates_hash(self):
        """Test that hashing a password creates a hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 20

    def test_verify_password_valid(self):
        """Test verifying a correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Test verifying an incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that same password hashed twice produces different hashes (due to salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestTokenGeneration:
    """Test JWT token generation and validation."""

    def test_create_access_token(self):
        """Test creating an access token."""
        subject = "test@example.com"
        token = create_access_token(subject)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        token = create_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test decoding a valid access token."""
        subject = "test@example.com"
        token = create_access_token(subject)
        # decode_token returns only the subject claim (backward compatibility)
        payload = decode_token(token)
        assert payload == subject

    def test_decode_refresh_token(self):
        """Test decoding a valid refresh token returns None (not JWT)."""
        # Refresh tokens are random strings, not JWTs, so decode_token returns None
        token = create_refresh_token()
        payload = decode_token(token)
        assert payload is None

    def test_verify_access_token_returns_full_payload(self):
        """Test verify_token returns full payload with all claims."""
        subject = "test@example.com"
        token = create_access_token(subject)
        # Skip revocation check — Redis isn't available in unit tests
        payload = verify_token(token, check_revocation=False)
        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "email" in payload

    def test_access_token_expiry(self):
        """Test that access tokens have correct expiry time."""
        settings = get_settings()
        subject = "test@example.com"
        token = create_access_token(subject)
        # Skip revocation check — Redis isn't available in unit tests
        payload = verify_token(token, check_revocation=False)

        # Check that expiry is set approximately to the configured duration
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = utc_now()
        duration = (exp_time - now).total_seconds() / 60

        # Should be approximately the configured duration (allow 5 minute variance)
        assert (
            settings.access_token_expire_minutes - 5
            < duration
            < settings.access_token_expire_minutes + 1
        )

    def test_expired_token_raises_error(self):
        """Test that expired tokens raise ExpiredSignatureError."""
        # Create an expired token by using negative expiry
        subject = "test@example.com"
        expired_token = create_access_token(
            subject, expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(expired_token, check_revocation=False)

    def test_invalid_token_raises_error(self):
        """Test that invalid tokens raise JWTError."""
        invalid_token = "invalid.token.here"

        with pytest.raises(JWTError):
            verify_token(invalid_token, check_revocation=False)

    def test_tampered_token_raises_error(self):
        """Test that tampered tokens raise JWTError."""
        subject = "test@example.com"
        token = create_access_token(subject)
        # Tamper with the token
        tampered = token[:-10] + "tampered!!"

        with pytest.raises(JWTError):
            verify_token(tampered, check_revocation=False)


@pytest.mark.unit
class TestPasswordValidation:
    """Test password validation rules."""

    def test_password_length_requirement(self):
        """Test that passwords must meet minimum length."""
        # "Short1!aB" is 9 chars, which actually clears
        # settings.password_min_length (default 8) -- it never tripped the
        # length check this test is named for. Use something genuinely
        # under the minimum.
        short_password = "Sh1!aB"
        with pytest.raises(PasswordValidationError):
            validate_password(short_password)

    def test_password_requires_number(self):
        """Test that passwords must contain at least one number."""
        no_number = "ValidPasswords!"
        with pytest.raises(PasswordValidationError):
            validate_password(no_number)

    def test_password_requires_uppercase(self):
        """Test that passwords must contain at least one uppercase letter."""
        no_upper = "validpassword1!"
        with pytest.raises(PasswordValidationError):
            validate_password(no_upper)

    def test_password_requires_lowercase(self):
        """Test that passwords must contain at least one lowercase letter."""
        no_lower = "VALIDPASSWORD1!"
        with pytest.raises(PasswordValidationError):
            validate_password(no_lower)

    def test_password_requires_special_char(self):
        """Test that passwords must contain at least one special character."""
        no_special = "ValidPassword1x"
        with pytest.raises(PasswordValidationError):
            validate_password(no_special)

    def test_strong_password_passes(self):
        """Test that strong passwords pass validation."""
        strong_password = "ValidPassword123!"
        # Should not raise
        validate_password(strong_password)

    def test_common_password_rejected(self):
        """Test that common passwords are rejected even when meeting all other requirements."""
        # "Password123!" lowered → "password123!" which is in the common passwords set
        common_password = "Password123!"
        with pytest.raises(PasswordValidationError):
            validate_password(common_password)
