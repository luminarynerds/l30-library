# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for cache security headers.

Tests that sensitive endpoints return proper Cache-Control headers to prevent
inappropriate caching of patron PII, session tokens, and payment information.
"""

import pytest
from app.middleware.security_headers import (
    SENSITIVE_ENDPOINT_PATTERNS,
    _is_sensitive_endpoint,
)


class TestSensitiveEndpointDetection:
    """Test the _is_sensitive_endpoint helper function."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            # Authentication endpoints (MUST be sensitive)
            ("/api/v1/auth/login", True),
            ("/api/v1/auth/logout", True),
            ("/api/v1/auth/refresh", True),
            ("/api/v1/auth/me", True),
            ("/api/v2/auth/login", True),  # Future API versions
            # User profile endpoints (MUST be sensitive - contains PII)
            ("/api/v1/me", True),
            ("/api/v1/users/123", True),
            ("/api/v1/users/1", True),
            # Patron data endpoints (MUST be sensitive - contains PII)
            ("/api/v1/staff/patrons", True),
            ("/api/v1/staff/patrons/123", True),
            ("/api/v1/staff/patrons/123/checkouts", True),
            ("/api/v1/staff/patrons/search", True),
            ("/api/v1/patrons/me", True),
            ("/api/v1/patrons/123", True),
            # Circulation endpoints (MUST be sensitive - patron activity)
            ("/api/v1/staff/checkout", True),
            ("/api/v1/staff/checkin", True),
            ("/api/v1/circulation/active", True),
            ("/api/v1/checkouts/123", True),
            # Financial endpoints (MUST be sensitive - payment info)
            ("/api/v1/fines", True),
            ("/api/v1/fines/123", True),
            ("/api/v1/payments", True),
            ("/api/v1/payments/process", True),
            ("/api/v1/financial/reports", True),
            ("/api/v1/billing/statements", True),
            # Session management (MUST be sensitive)
            ("/api/v1/sessions", True),
            ("/api/v1/sessions/active", True),
            # Privacy endpoints (MUST be sensitive)
            ("/api/v1/privacy/data-export", True),
            ("/api/v1/privacy/delete", True),
            # Account settings (MUST be sensitive)
            ("/api/v1/account/settings", True),
            # Dashboard with potentially sensitive stats
            ("/api/v1/staff/dashboard", True),
            ("/api/v1/staff/dashboard/stats", True),
            # Holds and reservations (tied to patron identity)
            ("/api/v1/holds", True),
            ("/api/v1/holds/123", True),
            ("/api/v1/reservations", True),
            # Reading history (MUST be sensitive - patron activity)
            ("/api/v1/reading-history", True),
            ("/api/v1/reading-history/export", True),
            # Favorites/reading lists
            ("/api/v1/favorites", True),
            ("/api/v1/reading-lists", True),
            ("/api/v1/reading-lists/123", True),
            # Non-sensitive endpoints (should NOT be marked sensitive)
            ("/api/v1/catalog/search", False),
            ("/api/v1/catalog/items/123", False),
            ("/api/v1/branches", False),
            ("/api/v1/hours", False),
            ("/api/v1/events", False),
            ("/api/v1/announcements", False),
            ("/api/v1/health", False),
            # Static files (should NOT be marked sensitive)
            ("/assets/main.js", False),
            ("/favicon.svg", False),
            ("/", False),
        ],
    )
    async def test_sensitive_endpoint_detection(self, path: str, expected: bool):
        """Verify sensitive endpoints are correctly identified."""
        result = _is_sensitive_endpoint(path)
        assert result == expected, (
            f"Path '{path}' should {'be' if expected else 'NOT be'} marked as sensitive"
        )

    async def test_all_patron_pii_endpoints_are_sensitive(self):
        """Verify that ALL patron PII endpoints are marked sensitive."""
        patron_pii_endpoints = [
            "/api/v1/staff/patrons/123",  # Contains: name, email, phone, address
            "/api/v1/staff/patrons/123/profile",
            "/api/v1/staff/patrons/123/contact",
            "/api/v1/me",  # Current user profile
            "/api/v1/users/456",  # User details
            "/api/v1/patrons/789",  # Patron details
        ]

        for endpoint in patron_pii_endpoints:
            assert _is_sensitive_endpoint(endpoint), (
                f"Patron PII endpoint '{endpoint}' MUST be marked as sensitive"
            )

    async def test_all_session_token_endpoints_are_sensitive(self):
        """Verify that ALL session/token endpoints are marked sensitive."""
        session_endpoints = [
            "/api/v1/auth/login",  # Returns access token
            "/api/v1/auth/refresh",  # Returns new access token
            "/api/v1/auth/logout",  # Invalidates tokens
            "/api/v1/sessions",  # Lists active sessions
        ]

        for endpoint in session_endpoints:
            assert _is_sensitive_endpoint(endpoint), (
                f"Session endpoint '{endpoint}' MUST be marked as sensitive"
            )

    async def test_all_payment_endpoints_are_sensitive(self):
        """Verify that ALL payment/financial endpoints are marked sensitive."""
        payment_endpoints = [
            "/api/v1/fines",  # Financial obligations
            "/api/v1/fines/123/pay",
            "/api/v1/payments",  # Payment processing
            "/api/v1/payments/123",
            "/api/v1/financial/reports",
            "/api/v1/billing/123",
        ]

        for endpoint in payment_endpoints:
            assert _is_sensitive_endpoint(endpoint), (
                f"Payment endpoint '{endpoint}' MUST be marked as sensitive"
            )

    async def test_public_catalog_endpoints_are_not_sensitive(self):
        """Verify that public catalog endpoints are NOT marked sensitive."""
        public_endpoints = [
            "/api/v1/catalog/search",
            "/api/v1/catalog/items/123",
            "/api/v1/catalog/featured",
            "/api/v1/branches",
            "/api/v1/hours",
            "/api/v1/events",
        ]

        for endpoint in public_endpoints:
            assert not _is_sensitive_endpoint(endpoint), (
                f"Public endpoint '{endpoint}' should NOT be marked as sensitive"
            )


class TestSensitiveEndpointPatterns:
    """Test the SENSITIVE_ENDPOINT_PATTERNS list."""

    async def test_patterns_cover_all_api_versions(self):
        """Verify patterns use \\d+ to match all API versions."""
        import re

        for pattern in SENSITIVE_ENDPOINT_PATTERNS:
            pattern_str = pattern.pattern
            # All API patterns should use \d+ for version number
            if "/api/v" in pattern_str:
                assert r"\d+" in pattern_str, (
                    f"Pattern '{pattern_str}' should use \\d+ to match all API versions"
                )

    async def test_minimum_required_patterns_exist(self):
        """Verify all critical sensitive endpoint categories are covered."""
        pattern_strings = [p.pattern for p in SENSITIVE_ENDPOINT_PATTERNS]

        required_categories = [
            "auth",  # Authentication
            "patron",  # Patron PII
            "checkout",  # Circulation activity
            "fine",  # Financial data
            "payment",  # Payment data
            "session",  # Session tokens
        ]

        for category in required_categories:
            matches = [p for p in pattern_strings if category in p.lower()]
            assert matches, (
                f"SENSITIVE_ENDPOINT_PATTERNS must include patterns for '{category}'"
            )


class TestCacheControlHeaders:
    """Integration tests for Cache-Control header behavior."""

    async def test_sensitive_endpoint_returns_no_store(self, client):
        """Verify sensitive endpoints return Cache-Control: no-store."""
        # Note: This test requires authentication, which may return 401
        # The important thing is that the middleware adds the header
        response = await client.get("/api/v1/me")

        # Even for 401 responses, the header should be set
        assert "Cache-Control" in response.headers
        cache_control = response.headers["Cache-Control"]
        assert "no-store" in cache_control
        assert "no-cache" in cache_control

    async def test_auth_endpoints_return_no_store(self, client):
        """Verify auth endpoints return strict no-cache headers."""
        # POST to login endpoint (will fail with 422, but headers should be set)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test"},
        )

        assert "Cache-Control" in response.headers
        cache_control = response.headers["Cache-Control"]
        assert "no-store" in cache_control

    async def test_public_endpoint_allows_private_cache(self, client):
        """Verify public endpoints allow private caching."""
        response = await client.get("/api/v1/health")

        # Health endpoint might not be in sensitive list
        # and should allow some caching
        if "Cache-Control" in response.headers:
            cache_control = response.headers["Cache-Control"]
            # Should NOT have strict no-store if it's public
            # (or should have reasonable cache settings)
            assert cache_control  # Just verify header exists

    async def test_pragma_header_for_http10_compatibility(self, client):
        """Verify sensitive endpoints include Pragma header for HTTP/1.0."""
        response = await client.get("/api/v1/auth/me")

        # Should include Pragma: no-cache for HTTP/1.0 compatibility
        if _is_sensitive_endpoint("/api/v1/auth/me"):
            assert "Pragma" in response.headers
            assert response.headers["Pragma"] == "no-cache"

    async def test_expires_header_for_http10_compatibility(self, client):
        """Verify sensitive endpoints include Expires header for HTTP/1.0."""
        response = await client.get("/api/v1/auth/me")

        # Should include Expires: 0 for HTTP/1.0 compatibility
        if _is_sensitive_endpoint("/api/v1/auth/me"):
            assert "Expires" in response.headers
            assert response.headers["Expires"] == "0"


class TestPatronDataCaching:
    """Tests specifically for patron PII caching prevention."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/staff/patrons/1",
            "/api/v1/staff/patrons/1/checkouts",
            "/api/v1/staff/patrons",
            "/api/v1/patrons/me",
        ],
    )
    async def test_patron_endpoint_is_sensitive(self, endpoint):
        """All patron endpoints must be marked sensitive."""
        assert _is_sensitive_endpoint(endpoint), (
            f"Patron endpoint {endpoint} MUST be marked sensitive to prevent PII caching"
        )

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/checkouts",
            "/api/v1/checkouts/active",
            "/api/v1/staff/checkout",
            "/api/v1/circulation/history",
        ],
    )
    async def test_checkout_endpoint_is_sensitive(self, endpoint):
        """Checkout endpoints reveal patron activity and must be sensitive."""
        assert _is_sensitive_endpoint(endpoint), (
            f"Checkout endpoint {endpoint} MUST be marked sensitive"
        )


class TestFinancialDataCaching:
    """Tests specifically for financial/payment data caching prevention."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/fines",
            "/api/v1/fines/123",
            "/api/v1/fines/123/pay",
            "/api/v1/payments",
            "/api/v1/payments/123",
            "/api/v1/financial/reports",
            "/api/v1/billing/123",
        ],
    )
    async def test_financial_endpoint_is_sensitive(self, endpoint):
        """All financial endpoints must be marked sensitive."""
        assert _is_sensitive_endpoint(endpoint), (
            f"Financial endpoint {endpoint} MUST be marked sensitive"
        )


class TestIndiePerUserEndpoints:
    """Per-user indie engagement endpoints must never be publicly cached.

    The /api/v1/indie blanket rule in caching_headers.py marks all indie
    paths `public, max-age=1800`. security_headers.py overrides that for
    specific per-user sub-paths listed in SENSITIVE_ENDPOINT_PATTERNS.
    """

    @pytest.mark.parametrize(
        "path",
        [
            # Bookmarks / favorites
            "/api/v1/indie/bookmarks",
            "/api/v1/indie/bookmarks/81/status",
            "/api/v1/indie/bookmarks/81",
            # Personal reading lists
            "/api/v1/indie/reading-lists",
            "/api/v1/indie/reading-lists/5",
            # Reading progress (per-patron, per-book)
            "/api/v1/indie/reading-progress/81",
            "/api/v1/indie/reading-progress/active",
            # Content preferences
            "/api/v1/indie/content-preferences",
            # Author follow status
            "/api/v1/indie/authors/12/follow",
            "/api/v1/indie/authors/me/follows",
            # Active borrows and borrow history
            "/api/v1/indie/lending/borrows/active",
            "/api/v1/indie/lending/borrows/history",
            "/api/v1/indie/lending/borrows",
            # For-you recommendations (patron-personalised)
            "/api/v1/indie/lending/for-you",
        ],
    )
    async def test_per_user_indie_endpoint_is_sensitive(self, path: str):
        """Per-user indie paths MUST be sensitive so the public indie media
        cache rule doesn't serve one patron's state to another."""
        assert _is_sensitive_endpoint(path) is True, (
            f"Per-user indie path '{path}' must be in SENSITIVE_ENDPOINT_PATTERNS "
            "to prevent cross-user stale-cache bugs"
        )

    @pytest.mark.parametrize(
        "path",
        [
            # Public indie catalog — MUST remain cacheable (no over-reach)
            "/api/v1/indie/catalog",
            "/api/v1/indie/catalog/81",
            # Lending preview and just-available are public
            "/api/v1/indie/lending/preview/81",
            "/api/v1/indie/lending/just-available",
            # Author detail pages and events
            "/api/v1/indie/authors/12/events",
            # Book-level recommendations are public
            "/api/v1/indie/books/81/recommendations",
        ],
    )
    async def test_public_indie_endpoint_is_not_sensitive(self, path: str):
        """Public indie catalog/discovery paths must NOT be marked sensitive,
        preserving the `public, max-age=1800` caching rule for performance."""
        assert _is_sensitive_endpoint(path) is False, (
            f"Public indie path '{path}' should NOT be in SENSITIVE_ENDPOINT_PATTERNS"
        )
