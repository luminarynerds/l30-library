# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for magic link authentication token logic.

Tests the core token generation, hashing, verification,
and expiry functions used for passwordless login.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import (
    create_magic_link_token,
    get_magic_link_token_expiry,
    hash_magic_link_token,
    verify_magic_link_token,
)


@pytest.mark.unit
class TestMagicLinkTokenGeneration:
    """Test magic link token generation."""

    def test_create_magic_link_token_returns_string(self):
        """Token generation returns a non-empty string."""
        token = create_magic_link_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_magic_link_token_is_url_safe(self):
        """Token should be URL-safe (no +, /, = characters from base64)."""
        token = create_magic_link_token()
        assert "+" not in token
        assert "/" not in token
        # url-safe base64 may have = for padding, but token_urlsafe strips it
        # The token should only contain alphanumeric, -, and _ characters
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', token)

    def test_create_magic_link_token_sufficient_entropy(self):
        """Token should have at least 32 bytes of entropy (43+ chars in base64url)."""
        token = create_magic_link_token()
        assert len(token) >= 43  # 32 bytes = 43 chars in url-safe base64

    def test_create_magic_link_token_uniqueness(self):
        """Each generated token should be unique."""
        tokens = {create_magic_link_token() for _ in range(100)}
        assert len(tokens) == 100


@pytest.mark.unit
class TestMagicLinkTokenHashing:
    """Test magic link token hashing."""

    def test_hash_magic_link_token_returns_hex_digest(self):
        """Hash should return a 64-character hex string (SHA-256)."""
        token = create_magic_link_token()
        hashed = hash_magic_link_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64
        # Should be valid hex
        int(hashed, 16)

    def test_hash_magic_link_token_deterministic(self):
        """Same token should always produce the same hash."""
        token = create_magic_link_token()
        hash1 = hash_magic_link_token(token)
        hash2 = hash_magic_link_token(token)
        assert hash1 == hash2

    def test_hash_magic_link_token_different_tokens_different_hashes(self):
        """Different tokens should produce different hashes."""
        token1 = create_magic_link_token()
        token2 = create_magic_link_token()
        assert hash_magic_link_token(token1) != hash_magic_link_token(token2)

    def test_hash_magic_link_token_matches_sha256(self):
        """Hash should match a manual SHA-256 computation."""
        token = "test-token-value"
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert hash_magic_link_token(token) == expected


@pytest.mark.unit
class TestMagicLinkTokenVerification:
    """Test magic link token verification."""

    def test_verify_magic_link_token_valid(self):
        """Valid token should verify against its hash."""
        token = create_magic_link_token()
        hashed = hash_magic_link_token(token)
        assert verify_magic_link_token(token, hashed) is True

    def test_verify_magic_link_token_invalid(self):
        """Invalid token should not verify."""
        token = create_magic_link_token()
        hashed = hash_magic_link_token(token)
        wrong_token = create_magic_link_token()
        assert verify_magic_link_token(wrong_token, hashed) is False

    def test_verify_magic_link_token_tampered_hash(self):
        """Tampered hash should not verify."""
        token = create_magic_link_token()
        tampered_hash = "a" * 64
        assert verify_magic_link_token(token, tampered_hash) is False

    def test_verify_magic_link_token_empty_inputs(self):
        """Empty token or hash should not verify against real values."""
        token = create_magic_link_token()
        hashed = hash_magic_link_token(token)
        assert verify_magic_link_token("", hashed) is False
        assert verify_magic_link_token(token, "") is False

    def test_verify_magic_link_token_constant_time(self):
        """Verification uses secrets.compare_digest (constant-time)."""
        # We verify this by checking the implementation uses compare_digest
        # which is tested via the function's behavior being correct
        token = create_magic_link_token()
        hashed = hash_magic_link_token(token)
        # Should use constant-time comparison
        with patch("app.core.security.secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
            verify_magic_link_token(token, hashed)
            mock_compare.assert_called_once()


@pytest.mark.unit
class TestMagicLinkTokenExpiry:
    """Test magic link token expiry."""

    def test_get_magic_link_token_expiry_returns_future(self):
        """Expiry should be in the future."""
        expiry = get_magic_link_token_expiry()
        assert expiry > datetime.now(timezone.utc)

    def test_get_magic_link_token_expiry_is_15_minutes(self):
        """Expiry should be approximately 15 minutes from now."""
        before = datetime.now(timezone.utc)
        expiry = get_magic_link_token_expiry()
        after = datetime.now(timezone.utc)

        expected_min = before + timedelta(minutes=15)
        expected_max = after + timedelta(minutes=15)

        assert expected_min <= expiry <= expected_max

    def test_get_magic_link_token_expiry_is_timezone_aware(self):
        """Expiry should be timezone-aware (UTC)."""
        expiry = get_magic_link_token_expiry()
        assert expiry.tzinfo is not None
