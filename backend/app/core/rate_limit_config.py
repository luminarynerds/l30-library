# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, List, Tuple


class EndpointCategory(StrEnum):

    AUTH = "auth"
    CATALOG = "catalog"
    CIRCULATION = "circulation"
    BOARD = "board"
    STAFF = "staff"
    INDIE = "indie"
    ACQUISITION = "acquisition"
    LEARNING = "learning"
    HOME_DELIVERY = "home-delivery"
    COMPLIANCE = "compliance"
    COMMUNITY = "community"
    PATRON = "patron"
    ADMIN = "admin"
    INTEGRATIONS = "integrations"
    STRATEGIC = "strategic"
    FACILITIES = "facilities"
    CONTENT = "content"
    TELEMETRY = "telemetry"
    SEARCH = "search"
    REPORTS = "reports"
    SYSTEM = "system"
    PUBLIC_FORM = "public-form"


@dataclass(frozen=True)
class CategoryRateLimit:

    read_per_minute: int
    write_per_minute: int
    burst_multiplier: float = 1.5


# ---------------------------------------------------------------------------
# Per-category rate limits
# ---------------------------------------------------------------------------
# Limits are tuned based on expected traffic patterns:
# - Auth: Tight write limits to prevent brute-force / credential stuffing
# - Staff/Admin: Higher read limits for dashboard-heavy workflows
# - Public-facing (catalog, community, content): Balanced read/write
# - Search: Generous reads, no writes
# - Reports: Low limits because report generation is expensive
# - System: Health checks are cheap, generous limits
# ---------------------------------------------------------------------------

CATEGORY_LIMITS: Dict[EndpointCategory, CategoryRateLimit] = {
    EndpointCategory.AUTH: CategoryRateLimit(
        read_per_minute=30, write_per_minute=10, burst_multiplier=1.0,
    ),
    EndpointCategory.CATALOG: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.CIRCULATION: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.BOARD: CategoryRateLimit(
        read_per_minute=60, write_per_minute=20,
    ),
    EndpointCategory.STAFF: CategoryRateLimit(
        read_per_minute=120, write_per_minute=60,
    ),
    EndpointCategory.INDIE: CategoryRateLimit(
        read_per_minute=120, write_per_minute=30,
    ),
    EndpointCategory.ACQUISITION: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.LEARNING: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.HOME_DELIVERY: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.COMPLIANCE: CategoryRateLimit(
        read_per_minute=60, write_per_minute=20,
    ),
    EndpointCategory.COMMUNITY: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.PATRON: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.ADMIN: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    EndpointCategory.INTEGRATIONS: CategoryRateLimit(
        read_per_minute=120, write_per_minute=60,
    ),
    EndpointCategory.STRATEGIC: CategoryRateLimit(
        read_per_minute=60, write_per_minute=20,
    ),
    EndpointCategory.FACILITIES: CategoryRateLimit(
        read_per_minute=60, write_per_minute=30,
    ),
    # CONTENT is also the fallback bucket for any unmapped route (see
    # classify_route), so an authenticated dashboard fans a dozen-plus GETs
    # (library-hours, system-status, branding, organization-features, the
    # me/* endpoints, plus pollers) into this single per-IP bucket on every
    # page load. A 60/min read cap throttled real single-user sessions, so the
    # read budget is generous; the write cap stays tight to protect content
    # writes (beacons live in their own TELEMETRY bucket).
    EndpointCategory.CONTENT: CategoryRateLimit(
        read_per_minute=300, write_per_minute=30,
    ),
    # Fire-and-forget analytics beacons (journey tracking, hub visits). These
    # POST on nearly every navigation, so a content-sized write budget starves
    # real content writes (e.g. event registration) on a shared per-IP bucket.
    # Generous-but-bounded: dropping a beacon loses a datapoint, not a user
    # action, and the frontend already swallows the 429.
    EndpointCategory.TELEMETRY: CategoryRateLimit(
        read_per_minute=300, write_per_minute=300, burst_multiplier=2.0,
    ),
    EndpointCategory.SEARCH: CategoryRateLimit(
        read_per_minute=60, write_per_minute=20,
    ),
    EndpointCategory.REPORTS: CategoryRateLimit(
        read_per_minute=30, write_per_minute=10,
    ),
    EndpointCategory.SYSTEM: CategoryRateLimit(
        read_per_minute=120, write_per_minute=60,
    ),
    # Public, unauthenticated patron submission forms. Turnstile-gated, so a
    # tight cap is appropriate even with bot verification in place.
    EndpointCategory.PUBLIC_FORM: CategoryRateLimit(
        read_per_minute=30, write_per_minute=3, burst_multiplier=1.0,
    ),
}


# ---------------------------------------------------------------------------
# Route prefix -> category mapping
# ---------------------------------------------------------------------------
# Ordered from most-specific to least-specific so that the first match wins.
# All prefixes are relative to ``/api/v1`` (the common router prefix).
# ---------------------------------------------------------------------------

ROUTE_CATEGORY_MAP: List[Tuple[str, EndpointCategory]] = [
    # ── Auth ──────────────────────────────────────────────────────────────
    ("/auth", EndpointCategory.AUTH),

    # ── Search (before generic content) ───────────────────────────────────
    ("/search", EndpointCategory.SEARCH),

    # ── Catalog & bibliographic ───────────────────────────────────────────
    ("/catalog", EndpointCategory.CATALOG),
    ("/bibframe-catalog", EndpointCategory.CATALOG),
    ("/cataloging/", EndpointCategory.CATALOG),
    ("/comic-cataloging", EndpointCategory.CATALOG),
    ("/manga-cataloging", EndpointCategory.CATALOG),
    ("/linked-data", EndpointCategory.CATALOG),
    ("/sparql", EndpointCategory.CATALOG),
    ("/publishers", EndpointCategory.CATALOG),

    # ── Circulation ───────────────────────────────────────────────────────
    ("/circulation", EndpointCategory.CIRCULATION),
    ("/sip2", EndpointCategory.CIRCULATION),
    ("/rfid", EndpointCategory.CIRCULATION),
    ("/equipment", EndpointCategory.CIRCULATION),
    ("/inventory", EndpointCategory.CIRCULATION),
    ("/book-drop", EndpointCategory.CIRCULATION),

    # ── Board governance ──────────────────────────────────────────────────
    ("/board", EndpointCategory.BOARD),

    # ── Staff operations (more-specific prefixes first) ───────────────────
    ("/staff/makerspace", EndpointCategory.STAFF),
    ("/staff/patrons", EndpointCategory.STAFF),
    ("/staff/rooms", EndpointCategory.STAFF),
    ("/staff/tech-booking", EndpointCategory.STAFF),
    ("/staff/outreach", EndpointCategory.STAFF),
    ("/staff/lost-damaged", EndpointCategory.STAFF),
    ("/staff/error-recovery", EndpointCategory.STAFF),
    ("/staff/panic-alerts", EndpointCategory.STAFF),
    ("/staff/print-notices", EndpointCategory.STAFF),
    ("/staff", EndpointCategory.STAFF),
    ("/staff-picks", EndpointCategory.STAFF),
    ("/staff-knowledge", EndpointCategory.STAFF),
    ("/fair-scheduling", EndpointCategory.STAFF),
    ("/shift-swap", EndpointCategory.STAFF),
    ("/end-of-day", EndpointCategory.STAFF),
    ("/end-of-shift", EndpointCategory.STAFF),
    ("/makerspace", EndpointCategory.STAFF),
    ("/pto", EndpointCategory.STAFF),
    ("/training", EndpointCategory.STAFF),

    # ── Indie author / publisher ──────────────────────────────────────────
    ("/indie", EndpointCategory.INDIE),
    ("/indie-lists", EndpointCategory.INDIE),

    # ── Acquisition & purchasing ──────────────────────────────────────────
    ("/acquisition", EndpointCategory.ACQUISITION),
    ("/edi", EndpointCategory.ACQUISITION),

    # ── Learning ──────────────────────────────────────────────────────────
    ("/learning", EndpointCategory.LEARNING),
    ("/learning-paths", EndpointCategory.LEARNING),
    ("/rubrics", EndpointCategory.LEARNING),

    # ── HomeDelivery services ────────────────────────────────────────────────
    ("/home-delivery", EndpointCategory.HOME_DELIVERY),
    ("/scheduling", EndpointCategory.HOME_DELIVERY),

    # ── Compliance & privacy ──────────────────────────────────────────────
    ("/compliance", EndpointCategory.COMPLIANCE),
    ("/cipa", EndpointCategory.COMPLIANCE),
    ("/state-compliance", EndpointCategory.COMPLIANCE),
    ("/privacy", EndpointCategory.COMPLIANCE),

    # ── Community engagement ──────────────────────────────────────────────
    ("/community", EndpointCategory.COMMUNITY),
    ("/book-clubs", EndpointCategory.COMMUNITY),
    ("/cohorts", EndpointCategory.COMMUNITY),
    ("/reading", EndpointCategory.COMMUNITY),
    ("/reading-lists", EndpointCategory.COMMUNITY),
    ("/reading-minutes", EndpointCategory.COMMUNITY),
    ("/reading-programs", EndpointCategory.COMMUNITY),
    ("/school-partnerships", EndpointCategory.COMMUNITY),
    ("/outreach", EndpointCategory.COMMUNITY),
    ("/partner-collaboration", EndpointCategory.COMMUNITY),
    ("/storytime", EndpointCategory.COMMUNITY),
    # Public reconsideration form — tighter limit (PUBLIC_FORM) than the staff
    # endpoints under /book-challenges. Must appear BEFORE the broader prefix
    # so first-match-wins resolves it correctly.
    ("/book-challenges/public/request", EndpointCategory.PUBLIC_FORM),
    ("/book-challenges", EndpointCategory.COMMUNITY),
    ("/teen-volunteer", EndpointCategory.COMMUNITY),
    ("/volunteers", EndpointCategory.COMMUNITY),

    # ── Patron management ─────────────────────────────────────────────────
    ("/patron", EndpointCategory.PATRON),
    ("/patron-engagement", EndpointCategory.PATRON),
    ("/patron-boundaries", EndpointCategory.PATRON),
    ("/card-applications", EndpointCategory.PATRON),
    ("/onboarding", EndpointCategory.PATRON),

    # ── Admin & security ──────────────────────────────────────────────────
    ("/admin", EndpointCategory.ADMIN),
    ("/users", EndpointCategory.ADMIN),
    ("/roles", EndpointCategory.ADMIN),
    ("/permissions", EndpointCategory.ADMIN),
    ("/law-enforcement", EndpointCategory.ADMIN),
    ("/threat-response", EndpointCategory.ADMIN),
    ("/public-records", EndpointCategory.ADMIN),
    ("/panic-alerts", EndpointCategory.ADMIN),

    # ── Integrations ──────────────────────────────────────────────────────
    ("/notifications", EndpointCategory.INTEGRATIONS),
    ("/streaming", EndpointCategory.INTEGRATIONS),
    ("/gutenberg", EndpointCategory.INTEGRATIONS),
    ("/databases", EndpointCategory.INTEGRATIONS),
    ("/webhooks/", EndpointCategory.INTEGRATIONS),
    ("/sms", EndpointCategory.INTEGRATIONS),
    ("/print", EndpointCategory.INTEGRATIONS),

    # ── Strategic & AI ────────────────────────────────────────────────────
    ("/strategic", EndpointCategory.STRATEGIC),
    ("/library-agents", EndpointCategory.STRATEGIC),
    ("/ai-tools", EndpointCategory.STRATEGIC),
    ("/ai-settings", EndpointCategory.STRATEGIC),
    ("/knowledge", EndpointCategory.STRATEGIC),
    ("/faq-chatbot", EndpointCategory.STRATEGIC),
    ("/meta-tags", EndpointCategory.STRATEGIC),

    # ── Facilities ────────────────────────────────────────────────────────
    ("/branches", EndpointCategory.FACILITIES),
    ("/consortiums", EndpointCategory.FACILITIES),
    ("/focus-time", EndpointCategory.FACILITIES),
    ("/joy-capture", EndpointCategory.FACILITIES),
    ("/task-batching", EndpointCategory.FACILITIES),
    ("/rooms", EndpointCategory.FACILITIES),
    ("/walk-in", EndpointCategory.FACILITIES),
    ("/tech-booking", EndpointCategory.FACILITIES),
    ("/signage", EndpointCategory.FACILITIES),

    # ── Reports ───────────────────────────────────────────────────────────
    ("/reports", EndpointCategory.REPORTS),
    ("/annual-reports", EndpointCategory.REPORTS),
    ("/financial", EndpointCategory.REPORTS),

    # ── System / health ───────────────────────────────────────────────────
    ("/health", EndpointCategory.SYSTEM),
    ("/api-status", EndpointCategory.SYSTEM),
    ("/monitoring", EndpointCategory.SYSTEM),
    ("/usage-statistics", EndpointCategory.SYSTEM),

    # ── Telemetry beacons (own bucket so they don't starve content writes) ─
    # ``/analytics/journeys`` MUST precede the bare ``/analytics`` prefix so
    # first-match-wins routes it correctly. ``/admin`` analytics already match
    # the earlier ADMIN prefix and stay there.
    ("/analytics/journeys", EndpointCategory.TELEMETRY),
    ("/accessibility-analytics", EndpointCategory.TELEMETRY),
    ("/hub-visits", EndpointCategory.TELEMETRY),
    ("/analytics", EndpointCategory.TELEMETRY),

    # ── Remaining content endpoints ───────────────────────────────────────
    ("/announcements", EndpointCategory.CONTENT),
    ("/events", EndpointCategory.CONTENT),
    ("/emergency", EndpointCategory.CONTENT),
    ("/favorites", EndpointCategory.CONTENT),
    ("/genealogy", EndpointCategory.CONTENT),
    ("/legal", EndpointCategory.CONTENT),
    ("/lifecycle", EndpointCategory.CONTENT),
    ("/link-health", EndpointCategory.CONTENT),
    ("/marketing", EndpointCategory.CONTENT),
    ("/material-costs", EndpointCategory.CONTENT),
    ("/organization-features", EndpointCategory.CONTENT),
    ("/releases", EndpointCategory.CONTENT),
    ("/review-responses", EndpointCategory.CONTENT),
    ("/series", EndpointCategory.CONTENT),
    ("/social-sharing", EndpointCategory.CONTENT),
    ("/support", EndpointCategory.CONTENT),
    ("/system-status", EndpointCategory.CONTENT),
    ("/work-relationships", EndpointCategory.CONTENT),
    ("/professional-judgment", EndpointCategory.CONTENT),
    ("/found-items", EndpointCategory.CONTENT),
    ("/semantic-search", EndpointCategory.SEARCH),
]


# HTTP methods classified as "read" operations (all others are "write").
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def classify_route(path: str) -> EndpointCategory:
    # Normalise: strip the /api/v1 or /api prefix for matching
    normalized = path
    if normalized.startswith("/api/v1"):
        normalized = normalized[7:]  # len("/api/v1") == 7
    elif normalized.startswith("/api"):
        normalized = normalized[4:]  # len("/api") == 4

    if not normalized:
        normalized = "/"

    for prefix, category in ROUTE_CATEGORY_MAP:
        if normalized.startswith(prefix):
            return category

    # Fallback: unmatched routes get the CONTENT category limits
    return EndpointCategory.CONTENT


def get_rate_limit(category: EndpointCategory, method: str) -> int:
    limits = CATEGORY_LIMITS[category]
    if method.upper() in READ_METHODS:
        return limits.read_per_minute
    return limits.write_per_minute
