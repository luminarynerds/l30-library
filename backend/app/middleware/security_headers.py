# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import re
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# In non-production environments, allow localhost connections for development
_IS_DEV = os.environ.get("TESTING_ENABLED", "").lower() == "true" or os.environ.get("ENV", "") == "development"

# Patterns for endpoints that contain sensitive data and must NEVER be cached
# These patterns match API endpoints that return PII, session data, or financial info
SENSITIVE_ENDPOINT_PATTERNS = [
    # Authentication and session endpoints
    re.compile(r"^/api/v\d+/auth/"),
    # User profile endpoints (contains PII)
    re.compile(r"^/api/v\d+/me$"),
    re.compile(r"^/api/v\d+/users/\d+$"),
    # Patron data endpoints (contains PII: email, address, phone, etc.)
    re.compile(r"^/api/v\d+/staff/patrons"),
    re.compile(r"^/api/v\d+/patrons"),
    # Checkout/circulation endpoints (contains patron activity)
    re.compile(r"^/api/v\d+/staff/checkout"),
    re.compile(r"^/api/v\d+/staff/checkin"),
    re.compile(r"^/api/v\d+/circulation"),
    re.compile(r"^/api/v\d+/checkouts"),
    # Financial and payment endpoints
    re.compile(r"^/api/v\d+/fines"),
    re.compile(r"^/api/v\d+/payments"),
    re.compile(r"^/api/v\d+/financial"),
    re.compile(r"^/api/v\d+/billing"),
    # Session management
    re.compile(r"^/api/v\d+/sessions"),
    # Privacy-related endpoints
    re.compile(r"^/api/v\d+/privacy"),
    # Account settings
    re.compile(r"^/api/v\d+/account"),
    # Dashboard with potentially sensitive stats
    re.compile(r"^/api/v\d+/staff/dashboard"),
    # Holds and reservations (tied to patron identity)
    re.compile(r"^/api/v\d+/holds"),
    re.compile(r"^/api/v\d+/reservations"),
    # Reading history (sensitive patron activity)
    re.compile(r"^/api/v\d+/reading-history"),
    # Favorites/reading lists when authenticated
    re.compile(r"^/api/v\d+/favorites"),
    re.compile(r"^/api/v\d+/reading-lists"),
    # Indie reader engagement — per-user state (favorites, reading lists,
    # progress, content prefs, author follows, active borrows). Must never be
    # publicly cached; the /indie blanket media rule would otherwise mark these
    # `public, max-age=1800` and serve one patron stale/cross-user state.
    re.compile(r"^/api/v\d+/indie/bookmarks"),
    re.compile(r"^/api/v\d+/indie/reading-lists"),
    re.compile(r"^/api/v\d+/indie/reading-progress"),
    re.compile(r"^/api/v\d+/indie/content-preferences"),
    re.compile(r"^/api/v\d+/indie/authors/[^/]+/follow"),
    re.compile(r"^/api/v\d+/indie/authors/me/follows"),
    re.compile(r"^/api/v\d+/indie/lending/borrows"),
    re.compile(r"^/api/v\d+/indie/lending/for-you"),
]


def _is_sensitive_endpoint(path: str) -> bool:
    for pattern in SENSITIVE_ENDPOINT_PATTERNS:
        if pattern.match(path):
            return True
    return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, and Referrer-Policy
    are set at the nginx/Cloudflare edge layer (see nginx.prod.conf and Cloudflare
    Transform Rules) - this middleware only owns the headers nginx doesnt set."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        request_path = request.url.path

        # HSTS: Force all future connections to use HTTPS for 1 year
        # includeSubDomains: Apply policy to all subdomains
        # preload: Allow inclusion in HSTS preload lists (optional but recommended)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, and
        # Referrer-Policy are set in nginx (the edge layer). Do not duplicate here.

        # Restrict browser features
        # Note: geolocation=(self) is enabled for bookmobile tracking and branch finder features
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), microphone=(), camera=(), payment=()"
        )

        # Content Security Policy - enforcing mode
        # SECURITY: CSP helps prevent XSS attacks by controlling resource loading
        #
        # STRICT EXTERNAL-ONLY SCRIPT-SRC:
        # All scripts are loaded from external files (no inline scripts in index.html).
        # The theme-init.js was extracted from inline to support this strict policy.
        # 'unsafe-inline' is NOT needed for script-src since all scripts are external.
        #
        # STYLE-SRC USES UNSAFE-INLINE:
        # Tailwind CSS requires inline styles for its utility class system.
        # Style injection is far lower risk than script injection (standard practice).
        #
        # NOTE: This CSP applies to API responses only. Frontend HTML served by nginx
        # has its own CSP set in frontend/nginx.conf.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            f"connect-src 'self' https:{' http://localhost http://localhost:*' if _IS_DEV else ''}; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # CACHE CONTROL FOR SENSITIVE DATA
        # SECURITY: Prevent browsers and proxies from caching sensitive data
        #
        # Sensitive endpoints (PII, session tokens, payment info) get strict no-cache headers:
        # - no-store: Never store the response in any cache
        # - no-cache: Must revalidate with server before using cached copy
        # - must-revalidate: Once stale, must not use without revalidation
        # - private: Only browser can cache (no CDN/proxy caching), though no-store overrides this
        # - max-age=0: Immediately stale
        #
        # This prevents:
        # - Browser back button revealing sensitive data to other users on shared computers
        # - Proxy servers caching and serving PII to other users
        # - Browser disk cache storing session tokens or payment information
        if _is_sensitive_endpoint(request_path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
            response.headers["Pragma"] = "no-cache"  # HTTP/1.0 backwards compatibility
            response.headers["Expires"] = "0"  # HTTP/1.0 backwards compatibility

        return response
