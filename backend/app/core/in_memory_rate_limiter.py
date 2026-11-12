# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import threading
import time
from collections import OrderedDict
from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:

    def __init__(self, max_entries: int = 10_000, fallback_multiplier: float = 0.5):
        self.max_entries = max_entries
        self.fallback_multiplier = fallback_multiplier
        self._buckets: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._lock_warned_until = 0.0  # Suppress repeated warnings

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        # Apply fallback multiplier to make limits stricter in memory mode
        adjusted_limit = max(1, int(limit * self.fallback_multiplier))
        now = time.monotonic()

        with self._lock:
            if key in self._buckets:
                # Move to end (mark as recently used for LRU)
                self._buckets.move_to_end(key)
                bucket = self._buckets[key]

                # Refill tokens based on elapsed time since last refill
                elapsed = now - bucket["last_refill"]
                refill_amount = int(elapsed / window_seconds * adjusted_limit)

                if refill_amount > 0:
                    bucket["tokens"] = min(adjusted_limit, bucket["tokens"] + refill_amount)
                    bucket["last_refill"] = now
            else:
                # New entry: evict oldest if at capacity
                if len(self._buckets) >= self.max_entries:
                    evicted_key = self._buckets.popitem(last=False)[0]
                    logger.debug(
                        "LRU evicted rate limiter entry",
                        extra={"evicted_ip": evicted_key, "total_entries": len(self._buckets)},
                    )

                self._buckets[key] = {
                    "tokens": adjusted_limit,
                    "last_refill": now,
                }
                bucket = self._buckets[key]

            # Consume a token if available
            if bucket["tokens"] > 0:
                bucket["tokens"] -= 1
                return True, bucket["tokens"]
            else:
                return False, 0

    def cleanup_stale(self, window_seconds: int, buffer_seconds: int = 300) -> int:
        now = time.monotonic()
        cutoff = now - (window_seconds + buffer_seconds)

        with self._lock:
            stale_keys = [
                key for key, bucket in self._buckets.items()
                if bucket["last_refill"] < cutoff
            ]
            for key in stale_keys:
                del self._buckets[key]

        if stale_keys:
            logger.debug(
                "Cleaned up stale rate limit entries",
                extra={"evicted_count": len(stale_keys), "remaining": len(self._buckets)},
            )

        return len(stale_keys)

    def get_stats(self) -> dict:
        return {
            "tracked_ips": len(self._buckets),
            "max_entries": self.max_entries,
            "occupancy_percent": round(100 * len(self._buckets) / self.max_entries, 2),
        }

    def warn_once(self, now: float, interval_seconds: float = 60.0) -> bool:
        if now >= self._lock_warned_until:
            self._lock_warned_until = now + interval_seconds
            return True
        return False
