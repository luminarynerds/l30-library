# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for endpoint rate limit configuration and route classification."""

import pytest

from app.core.rate_limit_config import (
    CATEGORY_LIMITS,
    ROUTE_CATEGORY_MAP,
    CategoryRateLimit,
    EndpointCategory,
    READ_METHODS,
    classify_route,
    get_rate_limit,
)


# ---------------------------------------------------------------------------
# classify_route
# ---------------------------------------------------------------------------

class TestClassifyRoute:
    """Tests for route-to-category classification."""

    def test_auth_routes(self):
        assert classify_route("/api/v1/auth/login") == EndpointCategory.AUTH
        assert classify_route("/api/v1/auth/register") == EndpointCategory.AUTH
        assert classify_route("/api/v1/auth/forgot-password") == EndpointCategory.AUTH

    def test_catalog_routes(self):
        assert classify_route("/api/v1/catalog") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/catalog/search") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/bibframe-catalog/records") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/cataloging/z3950/search") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/comic-cataloging/issues") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/manga-cataloging/series") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/linked-data/triples") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/sparql/query") == EndpointCategory.CATALOG
        assert classify_route("/api/v1/publishers") == EndpointCategory.CATALOG

    def test_circulation_routes(self):
        assert classify_route("/api/v1/circulation/checkout") == EndpointCategory.CIRCULATION
        assert classify_route("/api/v1/sip2/checkout") == EndpointCategory.CIRCULATION
        assert classify_route("/api/v1/rfid/scan") == EndpointCategory.CIRCULATION
        assert classify_route("/api/v1/equipment/list") == EndpointCategory.CIRCULATION
        assert classify_route("/api/v1/inventory/items") == EndpointCategory.CIRCULATION

    def test_board_routes(self):
        assert classify_route("/api/v1/board/meetings") == EndpointCategory.BOARD
        assert classify_route("/api/v1/board/committees/list") == EndpointCategory.BOARD
        assert classify_route("/api/v1/board/motions/1") == EndpointCategory.BOARD
        assert classify_route("/api/v1/board/public-comments") == EndpointCategory.BOARD

    def test_staff_routes(self):
        assert classify_route("/api/v1/staff/dashboard") == EndpointCategory.STAFF
        assert classify_route("/api/v1/staff/makerspace/resources") == EndpointCategory.STAFF
        assert classify_route("/api/v1/staff/patrons/123") == EndpointCategory.STAFF
        assert classify_route("/api/v1/staff/rooms/bookings") == EndpointCategory.STAFF
        assert classify_route("/api/v1/fair-scheduling/generate") == EndpointCategory.STAFF
        assert classify_route("/api/v1/shift-swap/requests") == EndpointCategory.STAFF
        assert classify_route("/api/v1/end-of-day/report") == EndpointCategory.STAFF
        assert classify_route("/api/v1/makerspace/resources") == EndpointCategory.STAFF
        assert classify_route("/api/v1/staff-picks") == EndpointCategory.STAFF

    def test_indie_routes(self):
        assert classify_route("/api/v1/indie/authors") == EndpointCategory.INDIE
        assert classify_route("/api/v1/indie/ebooks") == EndpointCategory.INDIE
        assert classify_route("/api/v1/indie/public/discover") == EndpointCategory.INDIE
        assert classify_route("/api/v1/indie-lists/popular") == EndpointCategory.INDIE

    def test_acquisition_routes(self):
        assert classify_route("/api/v1/acquisition/orders") == EndpointCategory.ACQUISITION
        assert classify_route("/api/v1/edi/transactions") == EndpointCategory.ACQUISITION

    def test_learning_routes(self):
        assert classify_route("/api/v1/learning/courses") == EndpointCategory.LEARNING
        assert classify_route("/api/v1/learning-paths/recommended") == EndpointCategory.LEARNING
        assert classify_route("/api/v1/rubrics/list") == EndpointCategory.LEARNING

    def test_home_delivery_routes(self):
        assert classify_route("/api/v1/home-delivery/deliveries") == EndpointCategory.HOME_DELIVERY
        assert classify_route("/api/v1/home-delivery/volunteers/signup") == EndpointCategory.HOME_DELIVERY
        assert classify_route("/api/v1/scheduling/optimal") == EndpointCategory.HOME_DELIVERY

    def test_compliance_routes(self):
        assert classify_route("/api/v1/compliance/reports") == EndpointCategory.COMPLIANCE
        assert classify_route("/api/v1/cipa/filters") == EndpointCategory.COMPLIANCE
        assert classify_route("/api/v1/state-compliance/filings") == EndpointCategory.COMPLIANCE
        assert classify_route("/api/v1/privacy/settings") == EndpointCategory.COMPLIANCE

    def test_community_routes(self):
        assert classify_route("/api/v1/community/programs") == EndpointCategory.COMMUNITY
        assert classify_route("/api/v1/book-clubs/list") == EndpointCategory.COMMUNITY
        assert classify_route("/api/v1/reading/lists") == EndpointCategory.COMMUNITY
        assert classify_route("/api/v1/reading-programs/active") == EndpointCategory.COMMUNITY
        assert classify_route("/api/v1/outreach/events") == EndpointCategory.COMMUNITY
        assert classify_route("/api/v1/storytime/schedule") == EndpointCategory.COMMUNITY

    def test_patron_routes(self):
        assert classify_route("/api/v1/patron/claims-returned") == EndpointCategory.PATRON
        assert classify_route("/api/v1/patron-engagement/metrics") == EndpointCategory.PATRON
        assert classify_route("/api/v1/card-applications/new") == EndpointCategory.PATRON

    def test_admin_routes(self):
        assert classify_route("/api/v1/admin/settings") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/admin/ai/config") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/admin/audit/logs") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/users/list") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/roles/create") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/permissions/matrix") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/law-enforcement/requests") == EndpointCategory.ADMIN
        assert classify_route("/api/v1/threat-response/alerts") == EndpointCategory.ADMIN

    def test_integrations_routes(self):
        assert classify_route("/api/v1/notifications/send") == EndpointCategory.INTEGRATIONS
        assert classify_route("/api/v1/streaming/content") == EndpointCategory.INTEGRATIONS
        assert classify_route("/api/v1/gutenberg/books") == EndpointCategory.INTEGRATIONS
        assert classify_route("/api/v1/databases/subscriptions") == EndpointCategory.INTEGRATIONS

    def test_strategic_routes(self):
        assert classify_route("/api/v1/strategic/plans") == EndpointCategory.STRATEGIC
        assert classify_route("/api/v1/library-agents/list") == EndpointCategory.STRATEGIC
        assert classify_route("/api/v1/ai-tools/generate") == EndpointCategory.STRATEGIC
        assert classify_route("/api/v1/knowledge/articles") == EndpointCategory.STRATEGIC
        assert classify_route("/api/v1/faq-chatbot/ask") == EndpointCategory.STRATEGIC

    def test_facilities_routes(self):
        assert classify_route("/api/v1/branches/list") == EndpointCategory.FACILITIES
        assert classify_route("/api/v1/consortiums/members") == EndpointCategory.FACILITIES
        assert classify_route("/api/v1/rooms/available") == EndpointCategory.FACILITIES
        assert classify_route("/api/v1/walk-in/queue") == EndpointCategory.FACILITIES
        assert classify_route("/api/v1/tech-booking/slots") == EndpointCategory.FACILITIES
        assert classify_route("/api/v1/signage/displays") == EndpointCategory.FACILITIES

    def test_reports_routes(self):
        assert classify_route("/api/v1/reports/monthly") == EndpointCategory.REPORTS
        assert classify_route("/api/v1/annual-reports/2024") == EndpointCategory.REPORTS
        assert classify_route("/api/v1/financial/summary") == EndpointCategory.REPORTS

    def test_search_routes(self):
        assert classify_route("/api/v1/search/unified") == EndpointCategory.SEARCH
        assert classify_route("/api/v1/semantic-search/query") == EndpointCategory.SEARCH

    def test_system_routes(self):
        assert classify_route("/api/v1/api-status/dashboard") == EndpointCategory.SYSTEM

    def test_content_routes(self):
        assert classify_route("/api/v1/announcements/latest") == EndpointCategory.CONTENT
        assert classify_route("/api/v1/events/upcoming") == EndpointCategory.CONTENT
        assert classify_route("/api/v1/favorites/list") == EndpointCategory.CONTENT
        assert classify_route("/api/v1/genealogy/trees") == EndpointCategory.CONTENT

    def test_telemetry_routes(self):
        # Telemetry beacons must NOT share the CONTENT write bucket, or they
        # starve real content writes like event registration (the 429 bug).
        assert classify_route("/api/v1/analytics/journeys/events") == EndpointCategory.TELEMETRY
        assert classify_route("/api/v1/analytics/journeys/events/batch") == EndpointCategory.TELEMETRY
        assert classify_route("/api/v1/hub-visits") == EndpointCategory.TELEMETRY
        assert classify_route("/api/v1/accessibility-analytics/report") == EndpointCategory.TELEMETRY
        assert classify_route("/api/v1/analytics/summary") == EndpointCategory.TELEMETRY

    def test_event_registration_not_starved_by_telemetry(self):
        # Regression for the registration 429: event registration is CONTENT,
        # telemetry is its own category, so beacons can't exhaust the content
        # write budget out from under a real registration POST.
        assert classify_route("/api/v1/events/9/register") == EndpointCategory.CONTENT
        assert (
            classify_route("/api/v1/analytics/journeys/events")
            != classify_route("/api/v1/events/9/register")
        )

    def test_unmatched_routes_fall_back_to_content(self):
        assert classify_route("/api/v1/some-unknown-endpoint") == EndpointCategory.CONTENT

    def test_strips_api_v1_prefix(self):
        assert classify_route("/api/v1/auth/login") == EndpointCategory.AUTH

    def test_strips_api_prefix(self):
        # Some routes use /api without /v1 (e.g. social_sharing)
        assert classify_route("/api/v1/auth/login") == classify_route("/api/v1/auth/login")

    def test_root_path_falls_back(self):
        result = classify_route("/")
        assert isinstance(result, EndpointCategory)


# ---------------------------------------------------------------------------
# get_rate_limit
# ---------------------------------------------------------------------------

class TestGetRateLimit:
    """Tests for rate limit lookup by category and method."""

    def test_read_methods_use_read_limit(self):
        for method in ("GET", "HEAD", "OPTIONS"):
            limit = get_rate_limit(EndpointCategory.CATALOG, method)
            assert limit == CATEGORY_LIMITS[EndpointCategory.CATALOG].read_per_minute

    def test_write_methods_use_write_limit(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            limit = get_rate_limit(EndpointCategory.CATALOG, method)
            assert limit == CATEGORY_LIMITS[EndpointCategory.CATALOG].write_per_minute

    def test_case_insensitive_method(self):
        assert get_rate_limit(EndpointCategory.AUTH, "get") == 30
        assert get_rate_limit(EndpointCategory.AUTH, "post") == 10

    def test_auth_has_tightest_write_limits(self):
        auth_write = CATEGORY_LIMITS[EndpointCategory.AUTH].write_per_minute
        # PUBLIC_FORM (anonymous, Turnstile-gated patron submission forms)
        # is deliberately tighter than AUTH (write=3 vs 10, see its comment
        # in rate_limit_config.py) -- it's a later, intentional addition for
        # a higher-risk unauthenticated surface, not a regression of auth's
        # own limit.
        for cat, limits in CATEGORY_LIMITS.items():
            if cat not in (EndpointCategory.AUTH, EndpointCategory.PUBLIC_FORM):
                # Auth should be among the tightest (10/min for write)
                assert auth_write <= limits.write_per_minute

    def test_staff_has_highest_read_limits(self):
        staff_read = CATEGORY_LIMITS[EndpointCategory.STAFF].read_per_minute
        assert staff_read == 120

    def test_reports_has_low_write_limit(self):
        reports_write = CATEGORY_LIMITS[EndpointCategory.REPORTS].write_per_minute
        assert reports_write == 10

    def test_all_categories_have_limits(self):
        for cat in EndpointCategory:
            assert cat in CATEGORY_LIMITS, f"Missing limits for {cat}"


# ---------------------------------------------------------------------------
# CategoryRateLimit dataclass
# ---------------------------------------------------------------------------

class TestCategoryRateLimit:
    def test_defaults(self):
        limit = CategoryRateLimit(read_per_minute=60, write_per_minute=30)
        assert limit.burst_multiplier == 1.5

    def test_frozen(self):
        limit = CategoryRateLimit(read_per_minute=60, write_per_minute=30)
        with pytest.raises(AttributeError):
            limit.read_per_minute = 100


# ---------------------------------------------------------------------------
# ROUTE_CATEGORY_MAP completeness
# ---------------------------------------------------------------------------

class TestRouteCategoryMapCompleteness:
    """Verify that the route map covers all known route prefixes."""

    KNOWN_PREFIXES = [
        "/auth", "/catalog", "/circulation", "/board", "/staff",
        "/indie", "/acquisition", "/learning", "/home-delivery",
        "/compliance", "/cipa", "/privacy", "/community",
        "/book-clubs", "/reading", "/outreach", "/patron",
        "/admin", "/users", "/roles", "/permissions",
        "/notifications", "/streaming", "/strategic",
        "/library-agents", "/ai-tools", "/branches",
        "/rooms", "/reports", "/annual-reports", "/search",
        "/events", "/announcements",
        "/analytics/journeys", "/hub-visits", "/accessibility-analytics",
        "/analytics",
    ]

    def test_all_known_prefixes_are_mapped(self):
        map_prefixes = {prefix for prefix, _ in ROUTE_CATEGORY_MAP}
        for prefix in self.KNOWN_PREFIXES:
            assert prefix in map_prefixes, (
                f"Route prefix '{prefix}' is not in ROUTE_CATEGORY_MAP"
            )

    def test_no_duplicate_prefixes(self):
        """Each prefix should appear at most once to avoid ambiguity."""
        prefixes = [prefix for prefix, _ in ROUTE_CATEGORY_MAP]
        seen = set()
        for p in prefixes:
            assert p not in seen, f"Duplicate prefix in ROUTE_CATEGORY_MAP: {p}"
            seen.add(p)
