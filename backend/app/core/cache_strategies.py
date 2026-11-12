# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .branding import branding
from .cache import (
    get_cached_with_lock,
    invalidate_cache,
    make_cache_key,
)

logger = logging.getLogger("app.cache_strategies")


# ---------------------------------------------------------------------------
# TTL Tiers
# ---------------------------------------------------------------------------

class CacheTTL(int, Enum):

    # Highly volatile - active circulation state
    REALTIME = 15          # 15 seconds: hold positions, availability counts
    VOLATILE = 30          # 30 seconds: active checkouts, fine balances
    SHORT = 60             # 1 minute: patron activity feeds
    # Moderately volatile - catalog and patron data
    MEDIUM = 300           # 5 minutes: search results, catalog listings
    STANDARD = 600         # 10 minutes: patron profiles, reading lists
    WARM = 900             # 15 minutes: recommendations, discovery feeds
    HALF_HOUR = 1800       # 30 minutes: search results, trending, sitemaps
    # Stable reference data
    LONG = 3600            # 1 hour: branch info, policies, schedules
    EXTENDED = 14400       # 4 hours: statistical summaries
    DAILY = 86400          # 24 hours: system config, fee schedules


# ---------------------------------------------------------------------------
# Cache Key Builders (Namespace: {CACHE_NAMESPACE}:{domain}:{entity}:{identifier})
# ---------------------------------------------------------------------------

class CacheKeyBuilder:

    PREFIX = branding.CACHE_NAMESPACE

    # --- Patron Domain ---
    @staticmethod
    def patron(patron_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:patron:profile:{patron_id}"

    @staticmethod
    def patron_fines(patron_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:patron:fines:{patron_id}"

    @staticmethod
    def patron_checkouts(patron_id: int, status: Optional[str] = None) -> str:
        suffix = f":{status}" if status else ":all"
        return f"{CacheKeyBuilder.PREFIX}:patron:checkouts:{patron_id}{suffix}"

    @staticmethod
    def patron_holds(patron_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:patron:holds:{patron_id}"

    @staticmethod
    def patron_activity(patron_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:patron:activity:{patron_id}"

    @staticmethod
    def patron_reading_history(patron_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:patron:reading:{patron_id}"

    # --- Catalog Domain ---
    @staticmethod
    def catalog_item(item_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:catalog:item:{item_id}"

    @staticmethod
    def catalog_search(**params) -> str:
        return make_cache_key(f"{CacheKeyBuilder.PREFIX}:catalog:search", **params)

    @staticmethod
    def catalog_browse(item_type: str, page: int, per_page: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:catalog:browse:{item_type}:{page}:{per_page}"

    @staticmethod
    def catalog_availability(item_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:catalog:avail:{item_id}"

    @staticmethod
    def catalog_new_arrivals(item_type: Optional[str] = None) -> str:
        suffix = f":{item_type}" if item_type else ":all"
        return f"{CacheKeyBuilder.PREFIX}:catalog:newarrivals{suffix}"

    # --- Circulation Domain ---
    @staticmethod
    def hold_queue(item_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:circ:holdqueue:{item_id}"

    @staticmethod
    def overdue_count(branch_id: Optional[int] = None) -> str:
        suffix = f":{branch_id}" if branch_id else ":all"
        return f"{CacheKeyBuilder.PREFIX}:circ:overdue_count{suffix}"

    # --- Branch & Reference Domain ---
    @staticmethod
    def branch(branch_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:branch:info:{branch_id}"

    @staticmethod
    def branch_hours(branch_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:branch:hours:{branch_id}"

    @staticmethod
    def branch_list() -> str:
        return f"{CacheKeyBuilder.PREFIX}:branch:list"

    @staticmethod
    def fine_policies() -> str:
        return f"{CacheKeyBuilder.PREFIX}:ref:finepolicies"

    # --- Reporting Domain ---
    @staticmethod
    def report(report_type: str, **params) -> str:
        return make_cache_key(f"{CacheKeyBuilder.PREFIX}:report:{report_type}", **params)

    @staticmethod
    def daily_stats(date_str: str, branch_id: Optional[int] = None) -> str:
        suffix = f":{branch_id}" if branch_id else ":all"
        return f"{CacheKeyBuilder.PREFIX}:report:daily:{date_str}{suffix}"

    # --- Indie Ebook Domain ---
    @staticmethod
    def indie_ebook(ebook_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:indie:ebook:{ebook_id}"

    @staticmethod
    def indie_discovery(feed_type: str, **params) -> str:
        return make_cache_key(f"{CacheKeyBuilder.PREFIX}:indie:discovery:{feed_type}", **params)

    @staticmethod
    def indie_recommendations(ebook_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:indie:recs:{ebook_id}"

    # --- Staff & Schedule Domain ---
    @staticmethod
    def staff_schedule(branch_id: int, date_str: str) -> str:
        return f"{CacheKeyBuilder.PREFIX}:staff:schedule:{branch_id}:{date_str}"

    # --- Reading Programs ---
    @staticmethod
    def reading_program(program_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:reading:program:{program_id}"

    @staticmethod
    def reading_leaderboard(program_id: int) -> str:
        return f"{CacheKeyBuilder.PREFIX}:reading:leaderboard:{program_id}"


# ---------------------------------------------------------------------------
# Domain-Specific Cache Strategies
# ---------------------------------------------------------------------------

class CacheStrategy:

    # --- Patron Operations ---

    async def get_patron_profile(
        self, patron_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.patron(patron_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.STANDARD)

    async def get_patron_fines(
        self, patron_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.patron_fines(patron_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.VOLATILE)

    async def get_patron_checkouts(
        self, patron_id: int, status: Optional[str], fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.patron_checkouts(patron_id, status)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.VOLATILE)

    async def get_patron_holds(
        self, patron_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.patron_holds(patron_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.REALTIME)

    async def invalidate_patron(self, patron_id: int) -> int:
        prefix = CacheKeyBuilder.PREFIX
        count = await invalidate_cache(f"{prefix}:patron:profile:{patron_id}")
        count += await invalidate_cache(f"{prefix}:patron:fines:{patron_id}")
        count += await invalidate_cache(f"{prefix}:patron:checkouts:{patron_id}*")
        count += await invalidate_cache(f"{prefix}:patron:holds:{patron_id}")
        count += await invalidate_cache(f"{prefix}:patron:activity:{patron_id}")
        count += await invalidate_cache(f"{prefix}:patron:reading:{patron_id}")
        return count

    # --- Catalog Operations ---

    async def get_catalog_item(
        self, item_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.catalog_item(item_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.STANDARD)

    async def get_catalog_search(
        self, params: Dict[str, Any], fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.catalog_search(**params)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.MEDIUM)

    async def get_catalog_availability(
        self, item_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.catalog_availability(item_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.REALTIME)

    async def invalidate_catalog_item(self, item_id: int) -> int:
        count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:item:{item_id}")
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:avail:{item_id}")
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:circ:holdqueue:{item_id}")
        # Also invalidate search results (they may contain this item)
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:search:*")
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:browse:*")
        return count

    async def invalidate_all_catalog(self) -> int:
        return await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:*")

    # --- Circulation Operations ---

    async def get_hold_queue(
        self, item_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.hold_queue(item_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.REALTIME)

    async def invalidate_circulation(
        self,
        patron_id: Optional[int] = None,
        item_id: Optional[int] = None,
    ) -> int:
        count = 0
        if patron_id:
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:patron:checkouts:{patron_id}*")
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:patron:holds:{patron_id}")
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:patron:fines:{patron_id}")
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:patron:activity:{patron_id}")
        if item_id:
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:catalog:avail:{item_id}")
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:circ:holdqueue:{item_id}")
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:circ:overdue_count:*")
        return count

    # --- Branch & Reference Data ---

    async def get_branch_info(
        self, branch_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.branch(branch_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.LONG)

    async def get_branch_list(self, fetch_func: Callable) -> Optional[Any]:
        key = CacheKeyBuilder.branch_list()
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.LONG)

    async def get_fine_policies(self, fetch_func: Callable) -> Optional[Any]:
        key = CacheKeyBuilder.fine_policies()
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.DAILY)

    async def invalidate_branch(self, branch_id: Optional[int] = None) -> int:
        if branch_id:
            count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:branch:*:{branch_id}")
        else:
            count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:branch:*")
        return count

    # --- Report Caching ---

    async def get_report(
        self, report_type: str, params: Dict[str, Any], fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.report(report_type, **params)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.EXTENDED)

    async def get_daily_stats(
        self, date_str: str, branch_id: Optional[int], fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.daily_stats(date_str, branch_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.EXTENDED)

    async def invalidate_reports(self) -> int:
        return await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:report:*")

    # --- Indie Ebook Operations ---

    async def get_indie_discovery(
        self, feed_type: str, params: Dict[str, Any], fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.indie_discovery(feed_type, **params)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.WARM)

    async def get_indie_recommendations(
        self, ebook_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.indie_recommendations(ebook_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.WARM)

    async def invalidate_indie(self, ebook_id: Optional[int] = None) -> int:
        if ebook_id:
            count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:indie:ebook:{ebook_id}")
            count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:indie:recs:{ebook_id}")
        else:
            count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:indie:*")
        return count

    # --- Reading Programs ---

    async def get_reading_leaderboard(
        self, program_id: int, fetch_func: Callable
    ) -> Optional[Any]:
        key = CacheKeyBuilder.reading_leaderboard(program_id)
        return await get_cached_with_lock(key, fetch_func, ttl_seconds=CacheTTL.SHORT)

    async def invalidate_reading_program(self, program_id: int) -> int:
        count = await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:reading:program:{program_id}")
        count += await invalidate_cache(f"{CacheKeyBuilder.PREFIX}:reading:leaderboard:{program_id}")
        return count


# ---------------------------------------------------------------------------
# Invalidation Event Map
# Maps database mutations to cache invalidation actions
# ---------------------------------------------------------------------------

_P = CacheKeyBuilder.PREFIX
INVALIDATION_MAP: Dict[str, Dict[str, List[str]]] = {
    # Table: { operation: [cache patterns to invalidate] }
    # Placeholders like {user_id}, {item_id}, {id} are resolved at runtime by handle_mutation_invalidation
    "checkouts": {
        "INSERT": [f"{_P}:patron:checkouts:{{user_id}}*", f"{_P}:catalog:avail:{{item_id}}",
                    f"{_P}:circ:overdue_count:*", f"{_P}:patron:activity:{{user_id}}"],
        "UPDATE": [f"{_P}:patron:checkouts:{{user_id}}*", f"{_P}:catalog:avail:{{item_id}}",
                    f"{_P}:circ:overdue_count:*", f"{_P}:patron:fines:{{user_id}}"],
        "DELETE": [f"{_P}:patron:checkouts:{{user_id}}*", f"{_P}:catalog:avail:{{item_id}}"],
    },
    "holds": {
        "INSERT": [f"{_P}:patron:holds:{{user_id}}", f"{_P}:circ:holdqueue:{{item_id}}",
                    f"{_P}:catalog:avail:{{item_id}}"],
        "UPDATE": [f"{_P}:patron:holds:{{user_id}}", f"{_P}:circ:holdqueue:{{item_id}}"],
        "DELETE": [f"{_P}:patron:holds:{{user_id}}", f"{_P}:circ:holdqueue:{{item_id}}"],
    },
    "fines": {
        "INSERT": [f"{_P}:patron:fines:{{user_id}}", f"{_P}:patron:activity:{{user_id}}"],
        "UPDATE": [f"{_P}:patron:fines:{{user_id}}"],
        "DELETE": [f"{_P}:patron:fines:{{user_id}}"],
    },
    "catalog_items": {
        "INSERT": [f"{_P}:catalog:search:*", f"{_P}:catalog:browse:*",
                    f"{_P}:catalog:newarrivals:*"],
        "UPDATE": [f"{_P}:catalog:item:{{id}}", f"{_P}:catalog:search:*",
                    f"{_P}:catalog:browse:*"],
        "DELETE": [f"{_P}:catalog:item:{{id}}", f"{_P}:catalog:search:*",
                    f"{_P}:catalog:browse:*"],
    },
    "users": {
        "UPDATE": [f"{_P}:patron:profile:{{id}}"],
        "DELETE": [f"{_P}:patron:*:{{id}}*"],
    },
    "fine_policies": {
        "INSERT": [f"{_P}:ref:finepolicies"],
        "UPDATE": [f"{_P}:ref:finepolicies"],
        "DELETE": [f"{_P}:ref:finepolicies"],
    },
    "branches": {
        "UPDATE": [f"{_P}:branch:*:{{id}}", f"{_P}:branch:list"],
        "DELETE": [f"{_P}:branch:*:{{id}}", f"{_P}:branch:list"],
    },
    "reading_logs": {
        "INSERT": [f"{_P}:patron:reading:{{user_id}}", f"{_P}:reading:leaderboard:*"],
        "UPDATE": [f"{_P}:patron:reading:{{user_id}}", f"{_P}:reading:leaderboard:*"],
    },
}


async def handle_mutation_invalidation(
    table: str, operation: str, row_data: Dict[str, Any]
) -> int:
    table_rules = INVALIDATION_MAP.get(table, {})
    patterns = table_rules.get(operation, [])

    if not patterns:
        return 0

    total_invalidated = 0
    for pattern in patterns:
        # Substitute placeholders with actual values
        resolved = pattern
        for key, value in row_data.items():
            resolved = resolved.replace(f"{{{key}}}", str(value))

        # Only invalidate if all placeholders were resolved
        if "{" not in resolved:
            count = await invalidate_cache(resolved)
            total_invalidated += count

    # Cascade invalidation for dependent domains
    cascade_count = await cascade_invalidate_for_table(table, row_data)
    total_invalidated += cascade_count

    if total_invalidated > 0:
        logger.debug(
            f"Cache invalidation: {table}.{operation} cleared {total_invalidated} keys "
            f"({cascade_count} from cascade)"
        )

    return total_invalidated


# ---------------------------------------------------------------------------
# Cascade Invalidation
# ---------------------------------------------------------------------------

# Dependency graph: when the SOURCE domain is invalidated, the DEPENDENT
# domains must also be invalidated. Each entry maps a cache domain prefix
# to the list of dependent domain patterns that should also be cleared.
#
# Example: invalidating a catalog item should also invalidate search results
# that may contain that item, and recommendation feeds that reference it.

CASCADE_DEPENDENCIES: Dict[str, List[str]] = {
    # When a catalog item changes, search/browse results and recommendations
    # that reference it become stale.
    f"{CacheKeyBuilder.PREFIX}:catalog:item": [
        f"{CacheKeyBuilder.PREFIX}:catalog:search:*",
        f"{CacheKeyBuilder.PREFIX}:catalog:browse:*",
        f"{CacheKeyBuilder.PREFIX}:catalog:newarrivals:*",
        f"{CacheKeyBuilder.PREFIX}:indie:discovery:*",
    ],
    # When availability changes, hold queues and catalog listings are affected.
    f"{CacheKeyBuilder.PREFIX}:catalog:avail": [
        f"{CacheKeyBuilder.PREFIX}:circ:holdqueue:*",
    ],
    # When a patron's checkouts change, their activity feed and fines may change.
    f"{CacheKeyBuilder.PREFIX}:patron:checkouts": [
        f"{CacheKeyBuilder.PREFIX}:patron:activity:*",
        f"{CacheKeyBuilder.PREFIX}:patron:fines:*",
        f"{CacheKeyBuilder.PREFIX}:circ:overdue_count:*",
    ],
    # When holds change, availability and hold queues need refresh.
    f"{CacheKeyBuilder.PREFIX}:patron:holds": [
        f"{CacheKeyBuilder.PREFIX}:catalog:avail:*",
        f"{CacheKeyBuilder.PREFIX}:circ:holdqueue:*",
    ],
    # When fines change, patron profile summaries may need refresh.
    f"{CacheKeyBuilder.PREFIX}:patron:fines": [
        f"{CacheKeyBuilder.PREFIX}:patron:profile:*",
    ],
    # When branch info changes, schedules and list also change.
    f"{CacheKeyBuilder.PREFIX}:branch:info": [
        f"{CacheKeyBuilder.PREFIX}:branch:hours:*",
        f"{CacheKeyBuilder.PREFIX}:branch:list",
    ],
    # When a reading log entry is added, leaderboards update.
    f"{CacheKeyBuilder.PREFIX}:patron:reading": [
        f"{CacheKeyBuilder.PREFIX}:reading:leaderboard:*",
    ],
    # When an indie ebook changes, discovery feeds and recommendations update.
    f"{CacheKeyBuilder.PREFIX}:indie:ebook": [
        f"{CacheKeyBuilder.PREFIX}:indie:discovery:*",
        f"{CacheKeyBuilder.PREFIX}:indie:recs:*",
    ],
    # When fine policies change, patron fine calculations may differ.
    f"{CacheKeyBuilder.PREFIX}:ref:finepolicies": [
        f"{CacheKeyBuilder.PREFIX}:patron:fines:*",
    ],
    # When report data is invalidated, daily stats may also be stale.
    f"{CacheKeyBuilder.PREFIX}:report": [
        f"{CacheKeyBuilder.PREFIX}:report:daily:*",
    ],
}

# Maps database table names to the cache domain prefixes they affect.
# Used by handle_mutation_invalidation to trigger cascade invalidation.
TABLE_TO_CACHE_DOMAINS: Dict[str, List[str]] = {
    "catalog_items": [f"{CacheKeyBuilder.PREFIX}:catalog:item"],
    "checkouts": [f"{CacheKeyBuilder.PREFIX}:patron:checkouts", f"{CacheKeyBuilder.PREFIX}:catalog:avail"],
    "holds": [f"{CacheKeyBuilder.PREFIX}:patron:holds", f"{CacheKeyBuilder.PREFIX}:catalog:avail"],
    "fines": [f"{CacheKeyBuilder.PREFIX}:patron:fines"],
    "users": [f"{CacheKeyBuilder.PREFIX}:patron:profile"],
    "branches": [f"{CacheKeyBuilder.PREFIX}:branch:info"],
    "fine_policies": [f"{CacheKeyBuilder.PREFIX}:ref:finepolicies"],
    "reading_logs": [f"{CacheKeyBuilder.PREFIX}:patron:reading"],
}

# Maximum cascade depth to prevent infinite loops
MAX_CASCADE_DEPTH = 3


async def cascade_invalidate(
    domain_prefix: str,
    _visited: Optional[Set[str]] = None,
    _depth: int = 0,
) -> int:
    if _visited is None:
        _visited = set()

    # Depth limit and cycle prevention
    if _depth >= MAX_CASCADE_DEPTH or domain_prefix in _visited:
        return 0

    _visited.add(domain_prefix)

    dependents = CASCADE_DEPENDENCIES.get(domain_prefix, [])
    if not dependents:
        return 0

    total = 0
    for dep_pattern in dependents:
        # Extract the domain prefix from the pattern for recursion
        dep_domain = dep_pattern.rstrip(":*")

        if dep_domain in _visited:
            continue

        # Invalidate matching keys
        count = await invalidate_cache(dep_pattern)
        total += count

        # Recurse into dependents of this dependent
        cascade_count = await cascade_invalidate(dep_domain, _visited, _depth + 1)
        total += cascade_count

    if total > 0:
        logger.debug(
            f"Cascade invalidation from {domain_prefix}: cleared {total} dependent keys "
            f"(depth={_depth})"
        )

    return total


async def cascade_invalidate_for_table(
    table: str,
    row_data: Dict[str, Any],
) -> int:
    domains = TABLE_TO_CACHE_DOMAINS.get(table, [])
    if not domains:
        return 0

    total = 0
    for domain in domains:
        count = await cascade_invalidate(domain)
        total += count

    return total


def get_cascade_dependencies() -> Dict[str, List[str]]:
    return dict(CASCADE_DEPENDENCIES)


# Global strategy instance
_strategy: Optional[CacheStrategy] = None


def get_cache_strategy() -> CacheStrategy:
    global _strategy
    if _strategy is None:
        _strategy = CacheStrategy()
    return _strategy
