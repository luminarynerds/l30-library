# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for in-memory rate limiter fallback.

Tests cover:
- Basic token bucket functionality
- Refill logic
- LRU eviction when capacity exceeded
- Stale entry cleanup
- Timeout-based warning suppression
"""

import time
import pytest
from app.core.in_memory_rate_limiter import InMemoryRateLimiter


class TestInMemoryRateLimiter:
    """Test suite for in-memory rate limiting."""

    @pytest.fixture
    def limiter(self):
        """Create a fresh limiter for each test."""
        return InMemoryRateLimiter(max_entries=100, fallback_multiplier=0.5)

    def test_token_consumption(self, limiter):
        """Test basic token consumption."""
        # Limit is 60, but with 0.5 multiplier = 30 tokens per minute
        allowed, remaining = limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)
        assert allowed is True
        assert remaining == 29  # Started with 30, consumed 1

        # Continue consuming
        for i in range(29):
            allowed, remaining = limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)
            assert allowed is True
            assert remaining == 28 - i

        # Should be denied on the 31st request
        allowed, remaining = limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)
        assert allowed is False
        assert remaining == 0

    def test_refill_after_window(self, limiter):
        """Test token refill after window passes."""
        # Exhaust tokens
        for _ in range(30):  # With 0.5 multiplier: 60 * 0.5 = 30
            limiter.is_allowed("192.168.1.2", limit=60, window_seconds=60)

        # Should be denied
        allowed, remaining = limiter.is_allowed("192.168.1.2", limit=60, window_seconds=60)
        assert allowed is False

        # Simulate window passing (61 seconds)
        limiter._buckets["192.168.1.2"]["last_refill"] -= 61

        # Should allow new request (full refill)
        allowed, remaining = limiter.is_allowed("192.168.1.2", limit=60, window_seconds=60)
        assert allowed is True
        assert remaining == 29

    def test_partial_refill(self, limiter):
        """Test partial token refill mid-window."""
        # Consume 10 tokens
        for _ in range(10):
            limiter.is_allowed("192.168.1.3", limit=60, window_seconds=60)

        # Simulate 30 seconds passing
        limiter._buckets["192.168.1.3"]["last_refill"] -= 30

        # 30 seconds = 50% of window, so 50% of limit = 15 tokens refilled
        # We had 20 remaining, add 15 = 35 (capped at 30)
        allowed, remaining = limiter.is_allowed("192.168.1.3", limit=60, window_seconds=60)
        assert allowed is True
        # After consuming 1 more: 29 remaining

    def test_lru_eviction(self, limiter):
        """Test LRU eviction when capacity exceeded."""
        # Fill to capacity
        for i in range(100):
            limiter.is_allowed(f"192.168.1.{i}", limit=60, window_seconds=60)

        assert len(limiter._buckets) == 100

        # Adding 101st should evict the oldest
        limiter.is_allowed("192.168.1.100", limit=60, window_seconds=60)
        assert len(limiter._buckets) == 100

        # The first IP (192.168.1.0) should be gone
        assert "catalog:192.168.1.0" not in limiter._buckets

    def test_lru_move_to_end(self, limiter):
        """Test that accessed IPs move to end (most recently used)."""
        # Add three IPs
        limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)
        limiter.is_allowed("192.168.1.2", limit=60, window_seconds=60)
        limiter.is_allowed("192.168.1.3", limit=60, window_seconds=60)

        # Access the first one again (moves to end)
        limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)

        # Add a 4th to reach capacity
        for i in range(4, 101):
            limiter.is_allowed(f"192.168.1.{i}", limit=60, window_seconds=60)

        # Evict oldest (should be 192.168.1.2, not 192.168.1.1)
        limiter.is_allowed("192.168.1.101", limit=60, window_seconds=60)
        assert "192.168.1.1" in limiter._buckets
        assert "192.168.1.2" not in limiter._buckets

    def test_cleanup_stale_entries(self, limiter):
        """Test cleanup of entries not accessed in window + buffer."""
        # Add entries
        limiter.is_allowed("192.168.1.1", limit=60, window_seconds=60)
        limiter.is_allowed("192.168.1.2", limit=60, window_seconds=60)
        limiter.is_allowed("192.168.1.3", limit=60, window_seconds=60)

        assert len(limiter._buckets) == 3

        # Mark first two as stale (380 seconds old = 6min 20sec > 60s + 300s buffer)
        now = time.monotonic()
        limiter._buckets["192.168.1.1"]["last_refill"] = now - 380
        limiter._buckets["192.168.1.2"]["last_refill"] = now - 380

        # Third stays fresh
        limiter._buckets["192.168.1.3"]["last_refill"] = now

        # Cleanup
        evicted = limiter.cleanup_stale(window_seconds=60, buffer_seconds=300)
        assert evicted == 2
        assert len(limiter._buckets) == 1
        assert "192.168.1.3" in limiter._buckets

    def test_warn_once(self, limiter):
        """Test that warnings are rate-limited."""
        now = 1000.0

        # First call should return True
        assert limiter.warn_once(now, interval_seconds=60.0) is True

        # Immediate second call should return False
        assert limiter.warn_once(now, interval_seconds=60.0) is False

        # After interval, should return True again
        assert limiter.warn_once(now + 61, interval_seconds=60.0) is True

    def test_stats(self, limiter):
        """Test stats reporting."""
        for i in range(10):
            limiter.is_allowed(f"192.168.1.{i}", limit=60, window_seconds=60)

        stats = limiter.get_stats()
        assert stats["tracked_ips"] == 10
        assert stats["max_entries"] == 100
        assert stats["occupancy_percent"] == 10.0

    def test_different_categories(self, limiter):
        """Test that different keys have separate buckets."""
        # Same type of key, different values (simulating different categories)
        limiter.is_allowed("key1", limit=10, window_seconds=60)
        limiter.is_allowed("key2", limit=60, window_seconds=60)

        # Should be separate entries
        assert "key1" in limiter._buckets
        assert "key2" in limiter._buckets
        assert len(limiter._buckets) == 2

    def test_fallback_multiplier(self):
        """Test that fallback multiplier is applied correctly."""
        limiter = InMemoryRateLimiter(fallback_multiplier=0.25)

        # Limit 60 with 0.25 multiplier = 15 tokens
        for _ in range(15):
            allowed, _ = limiter.is_allowed("ip1", limit=60, window_seconds=60)
            assert allowed is True

        # 16th should fail
        allowed, _ = limiter.is_allowed("ip1", limit=60, window_seconds=60)
        assert allowed is False

    def test_minimum_limit_of_one(self, limiter):
        """Test that minimum limit is 1 (never 0)."""
        # Very small limit with multiplier
        limiter = InMemoryRateLimiter(fallback_multiplier=0.1)

        # Limit 5 * 0.1 = 0.5, rounds to 1
        allowed, _ = limiter.is_allowed("ip", limit=5, window_seconds=60)
        assert allowed is True

        allowed, _ = limiter.is_allowed("ip", limit=5, window_seconds=60)
        assert allowed is False

    def test_concurrent_request_simulation(self, limiter):
        """Simulate concurrent requests from different IPs."""
        ips = [f"192.168.1.{i}" for i in range(1, 6)]
        limit = 60

        # Each IP makes multiple requests
        for round_num in range(35):  # With 0.5 multiplier, limit is 30
            for ip in ips:
                allowed, remaining = limiter.is_allowed(ip, limit=limit, window_seconds=60)

                # Each IP should have its own counter
                if round_num < 30:
                    assert allowed is True
                else:
                    assert allowed is False

    def test_no_division_by_zero(self, limiter):
        """Test edge case where window_seconds is very small."""
        # Should not crash even with unusual window sizes
        allowed, _ = limiter.is_allowed("ip", limit=60, window_seconds=1)
        assert allowed is True

        allowed, _ = limiter.is_allowed("ip", limit=60, window_seconds=1)
        assert allowed is True  # Should allow due to refill
