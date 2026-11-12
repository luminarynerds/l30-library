# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive unit tests for JWT key rotation functionality.

Tests cover:
- Token creation with primary key
- Token verification with primary key
- Token verification with previous key during rotation
- Backwards compatibility with legacy secret_key
- Grace period acceptance of previous key
- Rejection of invalid tokens
- Rotation logging
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from app.core.security import (
    create_access_token,
    verify_token,
    decode_token,
    JWTError,
)
from app.core.config import get_settings


@pytest.mark.unit
class TestJWTKeyRotation:
    """Test JWT key rotation functionality."""

    def test_create_access_token_uses_primary_jwt_key(self):
        """Test that create_access_token uses jwt_secret_key if configured."""
        with patch('app.core.security.settings') as mock_settings:
            # Configure mock settings
            mock_settings.jwt_secret_key = "primary-key-xyz"
            mock_settings.secret_key = "legacy-key-abc"
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token
            token = create_access_token(
                subject="user123",
                email="user@example.com"
            )

            # Token should be created successfully
            assert isinstance(token, str)
            assert len(token) > 0
            # Token is three parts separated by dots
            assert token.count('.') == 2

    def test_create_access_token_falls_back_to_secret_key(self):
        """Test that create_access_token falls back to secret_key when jwt_secret_key is not set."""
        with patch('app.core.security.settings') as mock_settings:
            # Configure mock settings with no jwt_secret_key
            mock_settings.jwt_secret_key = ""
            mock_settings.secret_key = "legacy-key-abc"
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token
            token = create_access_token(
                subject="user456",
                email="user@example.com"
            )

            # Token should be created successfully with fallback key
            assert isinstance(token, str)
            assert len(token) > 0
            assert token.count('.') == 2

    def test_verify_token_succeeds_with_primary_key(self):
        """Test that verify_token accepts tokens signed with primary key."""
        with patch('app.core.security.settings') as mock_settings:
            # Use same key for signing and verification
            primary_key = "test-primary-key-12345"
            mock_settings.jwt_secret_key = primary_key
            mock_settings.secret_key = "legacy-key"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token
            token = create_access_token(
                subject="user789",
                email="user@example.com"
            )

            # Verify token should succeed
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == "user789"
            assert payload["email"] == "user@example.com"

    def test_verify_token_falls_back_to_previous_key(self):
        """Test that verify_token accepts tokens signed with previous key during rotation."""
        with patch('app.core.security.settings') as mock_settings:
            previous_key = "test-previous-key-old"
            primary_key = "test-primary-key-new"

            # Create token with previous key
            mock_settings.jwt_secret_key = previous_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            token = create_access_token(
                subject="user_rotation",
                email="rotate@example.com"
            )

            # Switch to new key for verification
            mock_settings.jwt_secret_key = primary_key
            mock_settings.jwt_secret_key_previous = previous_key

            # Verify token should succeed with fallback to previous key
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == "user_rotation"
            assert payload["email"] == "rotate@example.com"

    def test_verify_token_tries_primary_key_first(self):
        """Test that verify_token tries primary key before previous key."""
        with patch('app.core.security.settings') as mock_settings:
            primary_key = "test-primary-key-new"
            previous_key = "test-previous-key-old"

            # Create token with primary key
            mock_settings.jwt_secret_key = primary_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            token = create_access_token(
                subject="user_primary",
                email="primary@example.com"
            )

            # Configure both keys
            mock_settings.jwt_secret_key = primary_key
            mock_settings.jwt_secret_key_previous = previous_key

            # Verify token should succeed with primary key (not previous)
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == "user_primary"

    def test_verify_token_rejects_invalid_tokens(self):
        """Test that verify_token rejects tokens with invalid signatures."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "primary-key"
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = "different-key"
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token with one key
            import jwt as pyjwt
            token = pyjwt.encode(
                {"sub": "user", "email": "user@example.com"},
                "completely-different-key",
                algorithm="HS256"
            )

            # Verify should fail
            with pytest.raises(JWTError) as exc_info:
                verify_token(token, check_revocation=False)
            assert "signature" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()

    def test_verify_token_logs_previous_key_usage(self, caplog, monkeypatch):
        """Test that verify_token logs when token is verified with previous key."""
        import logging
        # App startup disables propagation on the app logger. Capture on the
        # emitting logger directly so this also works with full app fixtures.
        logger = logging.getLogger("app.core.security")
        caplog.set_level(logging.INFO, logger=logger.name)
        monkeypatch.setattr(logger, "handlers", [caplog.handler])

        with patch('app.core.security.settings') as mock_settings:
            previous_key = "old-key"
            primary_key = "new-key"

            # Create token with previous key
            mock_settings.jwt_secret_key = previous_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            token = create_access_token(
                subject="user_log_test",
                email="log@example.com"
            )

            # Switch to new keys
            mock_settings.jwt_secret_key = primary_key
            mock_settings.jwt_secret_key_previous = previous_key

            # Verify token (will use previous key)
            payload = verify_token(token, check_revocation=False)

            # Check that log message was created
            assert "previous key" in caplog.text.lower() or "rotation" in caplog.text.lower()

    def test_decode_token_uses_primary_key(self):
        """Test that decode_token (legacy) uses primary key."""
        with patch('app.core.security.settings') as mock_settings:
            primary_key = "test-decode-primary"
            mock_settings.jwt_secret_key = primary_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token
            token = create_access_token(
                subject="user_decode",
                email="decode@example.com"
            )

            # Decode should succeed
            user_id = decode_token(token)
            assert user_id == "user_decode"

    def test_decode_token_falls_back_to_previous_key(self):
        """Test that decode_token falls back to previous key during rotation."""
        with patch('app.core.security.settings') as mock_settings:
            previous_key = "old-decode-key"
            primary_key = "new-decode-key"

            # Create token with previous key
            mock_settings.jwt_secret_key = previous_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            token = create_access_token(
                subject="user_decode_rotate",
                email="decode@example.com"
            )

            # Switch to new keys
            mock_settings.jwt_secret_key = primary_key
            mock_settings.jwt_secret_key_previous = previous_key

            # Decode should succeed with previous key
            user_id = decode_token(token)
            assert user_id == "user_decode_rotate"

    def test_backwards_compatibility_with_secret_key_only(self):
        """Test that implementation works when only secret_key is set (no jwt_secret_key)."""
        with patch('app.core.security.settings') as mock_settings:
            legacy_key = "legacy-secret-key"
            mock_settings.jwt_secret_key = ""  # Not configured
            mock_settings.secret_key = legacy_key
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token
            token = create_access_token(
                subject="user_legacy",
                email="legacy@example.com"
            )

            # Verify token should work
            payload = verify_token(token, check_revocation=False)
            assert payload["sub"] == "user_legacy"

    def test_expired_token_rejected_even_with_valid_key(self):
        """Test that expired tokens are rejected regardless of key validity."""
        with patch('app.core.security.settings') as mock_settings:
            primary_key = "test-expiry-key"
            mock_settings.jwt_secret_key = primary_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token that's already expired
            expired_token = create_access_token(
                subject="user_expired",
                email="expired@example.com",
                expires_delta=timedelta(seconds=-1)  # Already expired
            )

            # Verify should raise ExpiredSignatureError
            from jwt import ExpiredSignatureError
            with pytest.raises(ExpiredSignatureError):
                verify_token(expired_token, check_revocation=False)

    def test_malformed_token_rejected(self):
        """Test that malformed tokens are rejected."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "primary-key"
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"

            # Test various malformed tokens
            malformed_tokens = [
                "not.valid",  # Only 2 parts
                "way.too.many.parts.here",  # Too many parts
                "",  # Empty
                "   ",  # Whitespace
            ]

            for malformed_token in malformed_tokens:
                with pytest.raises(JWTError):
                    verify_token(malformed_token, check_revocation=False)

    def test_token_format_validation(self):
        """Test that token format is validated before key checking."""
        with patch('app.core.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "primary-key"
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = "previous-key"
            mock_settings.algorithm = "HS256"

            # Malformed token should fail format validation
            with pytest.raises(JWTError) as exc_info:
                verify_token("invalid.format", check_revocation=False)
            assert "format" in str(exc_info.value).lower()


@pytest.mark.unit
class TestJWTKeyRotationIntegration:
    """Integration tests for JWT key rotation across the auth flow."""

    def test_full_rotation_scenario(self):
        """Test complete key rotation scenario: old tokens still work, new tokens use new key."""
        with patch('app.core.security.settings') as mock_settings:
            # Phase 1: Initial state with old key
            old_key = "initial-secret-key"
            new_key = "rotated-secret-key"

            mock_settings.jwt_secret_key = old_key
            mock_settings.secret_key = "legacy"
            mock_settings.jwt_secret_key_previous = ""
            mock_settings.algorithm = "HS256"
            mock_settings.access_token_expire_minutes = 15

            # Create token with old key
            old_token = create_access_token(
                subject="user_rotation_test",
                email="rotation@example.com"
            )

            # Verify old token works
            payload = verify_token(old_token, check_revocation=False)
            assert payload["sub"] == "user_rotation_test"

            # Phase 2: Rotation begins - new key is primary, old key is previous
            mock_settings.jwt_secret_key = new_key
            mock_settings.jwt_secret_key_previous = old_key

            # Old token should still work
            payload = verify_token(old_token, check_revocation=False)
            assert payload["sub"] == "user_rotation_test"

            # New tokens should be signed with new key
            new_token = create_access_token(
                subject="user_rotation_test",
                email="rotation@example.com"
            )

            # Both tokens verify successfully
            old_payload = verify_token(old_token, check_revocation=False)
            new_payload = verify_token(new_token, check_revocation=False)

            assert old_payload["sub"] == new_payload["sub"]

            # Phase 3: After grace period, remove old key
            mock_settings.jwt_secret_key = new_key
            mock_settings.jwt_secret_key_previous = ""

            # New token still works
            payload = verify_token(new_token, check_revocation=False)
            assert payload["sub"] == "user_rotation_test"

            # Old token no longer works
            with pytest.raises(JWTError):
                verify_token(old_token, check_revocation=False)
