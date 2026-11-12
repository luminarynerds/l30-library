# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Patterns for endpoints with different caching strategies
class CacheStrategy:

    # Immutable/Reference data - cache aggressively (24 hours)
    # These endpoints return stable data that rarely changes
    IMMUTABLE_PATTERNS = [
        re.compile(r"^/api/v\d+/categories(?:/|$)"),  # Categories
        re.compile(r"^/api/v\d+/subjects(?:/|$)"),  # Subject lists
        re.compile(r"^/api/v\d+/item-types(?:/|$)"),  # Item types
        re.compile(r"^/api/v\d+/health(?:/|$)"),  # Health checks
        re.compile(r"^/api/v\d+/config(?:/|$)"),  # Configuration data
        re.compile(r"^/api/v\d+/organization(?:/|$)"),  # Organization settings
    ]

    # Reference/lookup data - cache for 1 hour
    # These are slower-changing reference data
    REFERENCE_PATTERNS = [
        re.compile(r"^/api/v\d+/authors(?:/|$)"),  # Author lists
        re.compile(r"^/api/v\d+/publishers(?:/|$)"),  # Publisher lists
        re.compile(r"^/api/v\d+/patrons/(?:public|search)"),  # Public patron info
    ]

    # Catalog special endpoints - cache briefly (not immutable like catalog browse)
    CATALOG_DYNAMIC_PATTERNS = [
        re.compile(r"^/api/v\d+/catalog/special/"),  # new-arrivals, random
        re.compile(r"^/api/v\d+/staff/picks/public"),  # staff picks
    ]

    # Catalog browse/search/detail - short cache, must-revalidate. Inventory
    # changes (new items, status flips) must surface promptly. These were
    # previously marked `immutable`, which made browsers serve a stale catalog
    # for 24h even on hard refresh.
    CATALOG_BROWSE_PATTERNS = [
        re.compile(r"^/api/v\d+/catalog(?:/|$)"),
    ]

    # Dynamic/Frequently-changing data - cache briefly (5-10 minutes)
    # These endpoints return data that may change frequently
    DYNAMIC_PATTERNS = [
        re.compile(r"^/api/v\d+/circulation/checkouts/active"),  # Active checkouts
        re.compile(r"^/api/v\d+/circulation/holds/active"),  # Active holds
        re.compile(r"^/api/v\d+/board/meetings"),  # Board meetings
        re.compile(r"^/api/v\d+/announcements(?:/|$)"),  # Announcements
        re.compile(r"^/api/v\d+/events(?:/|$)"),  # Events
        re.compile(r"^/api/v\d+/statistics(?:/|$)"),  # Statistics
    ]

    # Search queries - cache briefly (1-2 minutes, but private)
    # These are user-dependent and should not be cached on CDN
    SEARCH_PATTERNS = [
        re.compile(r"^/api/v\d+/catalog/search"),
        re.compile(r"^/api/v\d+/.*search"),
    ]

    # Streaming/media endpoints - longer cache (30 min)
    # Media catalogs change less frequently
    MEDIA_PATTERNS = [
        re.compile(r"^/api/v\d+/streaming(?:/|$)"),
        re.compile(r"^/api/v\d+/indie(?:/|$)"),
    ]


def _get_cache_header(path: str, method: str) -> str | None:
    # Only cache GET requests
    if method != "GET":
        return None

    # Catalog special endpoints - cache for 5 minutes (these change with new data)
    for pattern in CacheStrategy.CATALOG_DYNAMIC_PATTERNS:
        if pattern.search(path):
            return "private, max-age=300"

    # Catalog browse/search/detail - short cache, revalidate (inventory changes)
    for pattern in CacheStrategy.CATALOG_BROWSE_PATTERNS:
        if pattern.search(path):
            return "public, max-age=60, must-revalidate"

    # Immutable content - cache for 24 hours, can be cached by public CDNs
    for pattern in CacheStrategy.IMMUTABLE_PATTERNS:
        if pattern.search(path):
            return "public, max-age=86400, immutable"

    # Reference data - cache for 1 hour
    for pattern in CacheStrategy.REFERENCE_PATTERNS:
        if pattern.search(path):
            return "public, max-age=3600"

    # Search queries - cache for 2 minutes, but private (user-dependent)
    for pattern in CacheStrategy.SEARCH_PATTERNS:
        if pattern.search(path):
            return "private, max-age=120"

    # Streaming/media content - cache for 30 minutes
    for pattern in CacheStrategy.MEDIA_PATTERNS:
        if pattern.search(path):
            return "public, max-age=1800"

    # Dynamic content - cache for 5 minutes
    for pattern in CacheStrategy.DYNAMIC_PATTERNS:
        if pattern.search(path):
            return "private, max-age=300"

    return None


class CachingHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        request_path = request.url.path

        # Only add caching headers if not already present
        if "Cache-Control" not in response.headers:
            cache_header = _get_cache_header(request_path, request.method)
            if cache_header:
                response.headers["Cache-Control"] = cache_header

        return response
