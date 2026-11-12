# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for Redis circuit breaker in token revocation checking.

Tests cover:
- Normal path: Redis available, tokens checked and cached
- Degraded path: Redis down, recently-verified tokens allowed via cache
- Fail-secure: Unknown/expired tokens rejected when Redis is down
- Cache invalidation on revoke_token()
- Cache size limits (LRU eviction)
- Redis recovery after outage
"""

import hashlib
import time
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest


# Module path for patching
SECURITY_MODULE = "app.core.security"


def _make_token_hash(token: str) -> str:
    """Compute the SHA-256 hex digest of a token, matching security._get_token_hash."""
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture(autouse=True)
def _reset_circuit_breaker_state():
    """Reset all circuit breaker module-level state before each test.

    This ensures tests are isolated and don't leak state to each other.
    """
    import app.core.security as sec

    # Save original state
    original_cache = sec._TOKEN_VERIFY_CACHE
    original_redis_available = sec._redis_available
    original_redis_last_check = sec._redis_last_check
    original_redis_last_warning = sec._redis_last_warning

    # Reset to clean state
    sec._TOKEN_VERIFY_CACHE = OrderedDict()
    sec._redis_available = True
    sec._redis_last_check = 0.0
    sec._redis_last_warning = 0.0

    yield

    # Restore original state
    sec._TOKEN_VERIFY_CACHE = original_cache
    sec._redis_available = original_redis_available
    sec._redis_last_check = original_redis_last_check
    sec._redis_last_warning = original_redis_last_warning


@pytest.mark.unit
class TestNormalPath:
    """Tests for normal operation when Redis is available."""

    def test_non_revoked_token_returns_false_and_is_cached(self):
        """When Redis is available and token is not revoked, return False and cache the result."""
        import app.core.security as sec

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0  # Token not in revocation list

        token = "valid.jwt.token"
        token_hash = _make_token_hash(token)

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        assert result is False
        # Verify the token was cached
        assert token_hash in sec._TOKEN_VERIFY_CACHE

    def test_revoked_token_returns_true_and_is_not_cached(self):
        """When Redis is available and token IS revoked, return True and do NOT cache."""
        import app.core.security as sec

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # Token is in revocation list

        token = "revoked.jwt.token"
        token_hash = _make_token_hash(token)

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        assert result is True
        # Revoked tokens should NOT be cached as non-revoked
        assert token_hash not in sec._TOKEN_VERIFY_CACHE

    def test_redis_checked_on_normal_path(self):
        """Verify that Redis exists() is actually called during normal operation."""
        import app.core.security as sec

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        token = "check.redis.call"

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            sec.is_token_revoked(token)

        # Redis should have been queried with the correct revocation key
        expected_key = f"token_revocation:{_make_token_hash(token)}"
        mock_redis.exists.assert_called_once_with(expected_key)


@pytest.mark.unit
class TestRedisDownCachedToken:
    """Tests for degraded operation when Redis is down and token is in cache."""

    def test_cached_token_returns_not_revoked(self):
        """A recently-verified token should return False (not revoked) when Redis goes down."""
        import app.core.security as sec

        token = "cached.jwt.token"
        token_hash = _make_token_hash(token)

        # Simulate: token was previously verified and cached
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()

        # Now simulate Redis going down
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = ConnectionError("Redis connection refused")

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Token was recently verified — should be allowed through
        assert result is False

    def test_cached_token_survives_redis_client_none(self):
        """Cached token returns False even when get_redis_client returns None."""
        import app.core.security as sec

        token = "cached.none.client"
        token_hash = _make_token_hash(token)

        # Pre-cache the token
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()

        with patch.object(sec, "get_redis_client", return_value=None):
            result = sec.is_token_revoked(token)

        assert result is False


@pytest.mark.unit
class TestRedisDowUnknownToken:
    """Tests for degraded operation when Redis is down and token is NOT in cache."""

    def test_unknown_token_returns_revoked(self):
        """An unknown token (not in cache) should return True (fail-secure) when Redis is down."""
        import app.core.security as sec

        token = "unknown.jwt.token"

        # Simulate Redis failure
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = ConnectionError("Redis connection refused")

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Unknown token during Redis outage — fail-secure
        assert result is True

    def test_unknown_token_with_none_client_returns_revoked(self):
        """Unknown token returns True when Redis client is None."""
        import app.core.security as sec

        token = "unknown.none.client"

        with patch.object(sec, "get_redis_client", return_value=None):
            result = sec.is_token_revoked(token)

        assert result is True


@pytest.mark.unit
class TestRedisDowExpiredCache:
    """Tests for degraded operation when cache entry has expired."""

    def test_expired_cache_entry_returns_revoked(self):
        """A cached token older than TTL should return True (fail-secure) when Redis is down."""
        import app.core.security as sec

        token = "expired.cache.token"
        token_hash = _make_token_hash(token)

        # Cache the token with a timestamp that's older than TTL
        expired_timestamp = time.monotonic() - sec._TOKEN_CACHE_TTL_SECONDS - 1
        sec._TOKEN_VERIFY_CACHE[token_hash] = expired_timestamp

        # Simulate Redis failure
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = ConnectionError("Redis connection refused")

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Cache entry is expired — fail-secure
        assert result is True

    def test_expired_entry_is_removed_from_cache(self):
        """When checking an expired entry, it should be removed from the cache."""
        import app.core.security as sec

        token = "expired.removal.token"
        token_hash = _make_token_hash(token)

        # Cache with an expired timestamp
        expired_timestamp = time.monotonic() - sec._TOKEN_CACHE_TTL_SECONDS - 1
        sec._TOKEN_VERIFY_CACHE[token_hash] = expired_timestamp

        # Simulate Redis failure
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = ConnectionError("Redis connection refused")

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            sec.is_token_revoked(token)

        # The expired entry should have been cleaned up
        assert token_hash not in sec._TOKEN_VERIFY_CACHE


@pytest.mark.unit
class TestRevokeRemovesFromCache:
    """Tests that revoke_token() removes tokens from the in-memory cache."""

    def test_revoke_removes_cached_token(self):
        """revoke_token() should remove the token from _TOKEN_VERIFY_CACHE."""
        import app.core.security as sec

        token = "to.be.revoked"
        token_hash = _make_token_hash(token)

        # Pre-cache the token
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()
        assert token_hash in sec._TOKEN_VERIFY_CACHE

        # Mock Redis for the revocation call
        mock_redis = MagicMock()
        mock_redis.setex.return_value = True

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            sec.revoke_token(token, expiry_seconds=3600)

        # Token should be removed from in-memory cache
        assert token_hash not in sec._TOKEN_VERIFY_CACHE

    def test_revoke_handles_token_not_in_cache(self):
        """revoke_token() should not error if token is not in cache."""
        import app.core.security as sec

        token = "not.in.cache"
        token_hash = _make_token_hash(token)

        # Ensure token is NOT in cache
        assert token_hash not in sec._TOKEN_VERIFY_CACHE

        mock_redis = MagicMock()
        mock_redis.setex.return_value = True

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            # Should not raise
            sec.revoke_token(token, expiry_seconds=3600)

    def test_revoke_removes_from_cache_even_if_redis_fails(self):
        """Even if Redis is unavailable, the token should still be removed from the cache."""
        import app.core.security as sec

        token = "revoke.redis.down"
        token_hash = _make_token_hash(token)

        # Pre-cache the token
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()

        with patch.object(sec, "get_redis_client", return_value=None):
            with pytest.raises(Exception, match="Redis unavailable"):
                sec.revoke_token(token, expiry_seconds=3600)

        # Even though Redis failed, the token should be removed from cache
        assert token_hash not in sec._TOKEN_VERIFY_CACHE


@pytest.mark.unit
class TestCacheSizeLimit:
    """Tests that the cache respects the maximum size limit."""

    def test_cache_evicts_oldest_when_full(self):
        """Cache should not grow beyond _TOKEN_CACHE_MAX_SIZE."""
        import app.core.security as sec

        # Use a small max size for testing
        original_max = sec._TOKEN_CACHE_MAX_SIZE
        sec._TOKEN_CACHE_MAX_SIZE = 5

        try:
            mock_redis = MagicMock()
            mock_redis.exists.return_value = 0  # Not revoked

            with patch.object(sec, "get_redis_client", return_value=mock_redis):
                # Add more tokens than the max size
                for i in range(10):
                    token = f"token.number.{i}"
                    sec.is_token_revoked(token)

            # Cache should not exceed max size
            assert len(sec._TOKEN_VERIFY_CACHE) <= 5

            # The most recent tokens should be in the cache
            for i in range(5, 10):
                token = f"token.number.{i}"
                token_hash = _make_token_hash(token)
                assert token_hash in sec._TOKEN_VERIFY_CACHE

            # The oldest tokens should have been evicted
            for i in range(5):
                token = f"token.number.{i}"
                token_hash = _make_token_hash(token)
                assert token_hash not in sec._TOKEN_VERIFY_CACHE

        finally:
            sec._TOKEN_CACHE_MAX_SIZE = original_max

    def test_cache_put_respects_size_limit(self):
        """Direct _cache_put calls should respect size limit."""
        import app.core.security as sec

        original_max = sec._TOKEN_CACHE_MAX_SIZE
        sec._TOKEN_CACHE_MAX_SIZE = 3

        try:
            now = time.monotonic()
            sec._cache_put("hash_a", now)
            sec._cache_put("hash_b", now)
            sec._cache_put("hash_c", now)
            assert len(sec._TOKEN_VERIFY_CACHE) == 3

            # Adding a 4th should evict the oldest (hash_a)
            sec._cache_put("hash_d", now)
            assert len(sec._TOKEN_VERIFY_CACHE) == 3
            assert "hash_a" not in sec._TOKEN_VERIFY_CACHE
            assert "hash_d" in sec._TOKEN_VERIFY_CACHE

        finally:
            sec._TOKEN_CACHE_MAX_SIZE = original_max


@pytest.mark.unit
class TestRedisRecovery:
    """Tests that normal behavior resumes when Redis comes back online."""

    def test_redis_recovery_resumes_normal_checks(self):
        """When Redis recovers, tokens should be checked against Redis again."""
        import app.core.security as sec

        token = "recovery.test.token"
        token_hash = _make_token_hash(token)

        # Step 1: Redis is down, mark as unavailable
        sec._redis_available = False
        sec._redis_last_check = 0.0  # Allow immediate retry

        # Step 2: Redis comes back — mock a working Redis
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0  # Token not revoked

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Should have checked Redis and returned not-revoked
        assert result is False
        assert sec._redis_available is True
        # Token should be cached
        assert token_hash in sec._TOKEN_VERIFY_CACHE

    def test_redis_recovery_detects_revoked_token(self):
        """After recovery, a token that was revoked during the outage is detected."""
        import app.core.security as sec

        token = "revoked.during.outage"
        token_hash = _make_token_hash(token)

        # Token was cached before the outage
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()

        # Redis is back, and the token was revoked during the outage
        sec._redis_available = True
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # Token IS revoked now

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Redis says revoked, so the answer is True
        assert result is True

    def test_redis_recovery_logs_restoration(self):
        """When Redis recovers, an info log should be emitted."""
        import app.core.security as sec

        sec._redis_available = False
        sec._redis_last_check = 0.0

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        with (
            patch.object(sec, "get_redis_client", return_value=mock_redis),
            patch.object(sec.logger, "info") as mock_log,
        ):
            sec.is_token_revoked("recovery.log.test")

        mock_log.assert_called_once()
        assert "restored" in mock_log.call_args[0][0].lower()

    def test_retry_interval_respected(self):
        """Redis reconnection should not be attempted more often than _REDIS_RETRY_INTERVAL."""
        import app.core.security as sec

        token = "retry.interval.token"
        token_hash = _make_token_hash(token)

        # Simulate: Redis just went down very recently
        sec._redis_available = False
        sec._redis_last_check = time.monotonic()  # Just checked

        # Pre-cache the token so it gets a cache hit
        sec._TOKEN_VERIFY_CACHE[token_hash] = time.monotonic()

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        with patch.object(sec, "get_redis_client", return_value=mock_redis):
            result = sec.is_token_revoked(token)

        # Should NOT have called Redis (retry interval not elapsed)
        mock_redis.exists.assert_not_called()
        # Should return from cache
        assert result is False


@pytest.mark.unit
class TestGetTokenCacheStatus:
    """Tests for the monitoring/status function."""

    def test_status_returns_expected_keys(self):
        """get_token_cache_status() should return all expected monitoring fields."""
        import app.core.security as sec

        status = sec.get_token_cache_status()

        assert "redis_available" in status
        assert "cached_tokens" in status
        assert "cache_max_size" in status
        assert "cache_ttl_seconds" in status

    def test_status_reflects_current_state(self):
        """Status should reflect the actual module state."""
        import app.core.security as sec

        # Add some tokens to cache
        sec._TOKEN_VERIFY_CACHE["hash1"] = time.monotonic()
        sec._TOKEN_VERIFY_CACHE["hash2"] = time.monotonic()
        sec._redis_available = False

        status = sec.get_token_cache_status()

        assert status["redis_available"] is False
        assert status["cached_tokens"] == 2
        assert status["cache_max_size"] == sec._TOKEN_CACHE_MAX_SIZE
        assert status["cache_ttl_seconds"] == sec._TOKEN_CACHE_TTL_SECONDS
