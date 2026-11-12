# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Router registration registry - single source of truth for all API routes.

This module registers every router used by the L30 API. Both production (main.py)
and tests should call register_all_routers() to ensure identical behavior.

OPTIMIZATION: Uses lazy imports to avoid loading all routers upfront,
significantly reducing startup time during testing (24s -> ~2-3s).
"""

import importlib
import os
from fastapi import Depends, FastAPI

from .feature_guards import (
    require_acquisition_enabled,
    require_ai_tools_enabled,
    require_ama_enabled,
    require_banned_books_tracking_enabled,
    require_beta_features_enabled,
    require_board_features_enabled,
    require_book_clubs_enabled,
    require_cohort_enabled,
    require_collection_management_enabled,
    require_community_features_enabled,
    require_compliance_enabled,
    require_digital_access_enabled,
    require_emergency_services_enabled,
    require_events_enabled,
    require_faq_chatbot_enabled,
    require_financial_reports_enabled,
    require_free_ebooks_enabled,
    require_gamification_enabled,
    require_genealogy_enabled,
    require_home_delivery_enabled,
    require_ill_enabled,
    require_indie_platform_enabled,
    require_learning_platform_enabled,
    require_legal_services_enabled,
    require_literacy_programs_enabled,
    require_makerspace_enabled,
    require_marketing_enabled,
    require_meeting_rooms_enabled,
    require_migration_enabled,
    require_notifications_enabled,
    require_outreach_enabled,
    require_parent_onboarding_enabled,
    require_community_outcomes_enabled,
    require_impact_measurement_enabled,
    require_patron_engagement_enabled,
    require_patron_portal_enabled,
    require_printing_enabled,
    require_processing_queue_enabled,
    require_reading_goals_enabled,
    require_reading_programs_enabled,
    require_reading_shelf_enabled,
    require_saved_searches_enabled,
    require_self_checkout_enabled,
    require_serials_enabled,
    require_shelf_data_export_enabled,
    require_signage_enabled,
    require_sip2_rfid_enabled,
    require_staff_scheduling_enabled,
    require_staff_wellness_enabled,
    require_storytime_enabled,
    require_strategic_planning_enabled,
    require_streaming_enabled,
    require_tech_services_enabled,
    require_training_modules_enabled,
    require_volunteers_enabled,
)

# Cache for imported modules to avoid re-importing
_router_cache = {}


# Lazy import helper - loads modules only when needed
def _lazy_import(module_path: str):
    if module_path not in _router_cache:
        _router_cache[module_path] = importlib.import_module(module_path)
    return _router_cache[module_path]


def register_all_routers(app: FastAPI, *, debug: bool = False) -> None:

    # =====================================================================
    # Core routers (never toggled off)
    # =====================================================================
    auth = _lazy_import('app.api.v1.auth')
    account_security = _lazy_import('app.api.v1.account_security')
    calendar_feed = _lazy_import('app.api.v1.calendar_feed')
    catalog = _lazy_import('app.api.v1.catalog')
    circulation = _lazy_import('app.api.v1.circulation')
    staff_catalog = _lazy_import('app.api.v1.staff.catalog')
    staff_acquisition_rationales = _lazy_import('app.api.v1.staff.acquisition_rationales')
    staff_collection_memory = _lazy_import('app.api.v1.staff.collection_memory')
    catalog_recommendations = _lazy_import('app.api.v1.catalog_recommendations')
    discover = _lazy_import('app.api.v1.discover')
    staff_curated_recs = _lazy_import('app.api.v1.staff.curated_recommendations')
    staff_circulation_policy = _lazy_import('app.api.v1.staff.circulation_policy')
    organization_features = _lazy_import('app.api.v1.organization_features')
    system_status = _lazy_import('app.api.v1.system_status')
    site_search = _lazy_import('app.api.v1.site_search')
    releases = _lazy_import('app.api.v1.releases')
    inventory = _lazy_import('app.api.v1.inventory')
    reports = _lazy_import('app.api.v1.reports')
    patron_requests = _lazy_import('app.api.v1.patron_requests')
    feature_requests = _lazy_import('app.api.v1.feature_requests')
    metislib_ebooks = _lazy_import('app.api.v1.metislib_ebooks')
    indie_catalog = _lazy_import('app.api.v1.indie_catalog')
    indie_lending = _lazy_import('app.api.v1.indie_lending')
    indie_bookmarks = _lazy_import("app.api.v1.indie_bookmarks")
    indie_reading_progress = _lazy_import("app.api.v1.indie_reading_progress")
    indie_recommendations = _lazy_import("app.api.v1.indie_recommendations")
    indie_author_events = _lazy_import("app.api.v1.indie_author_events")
    indie_author_follow = _lazy_import("app.api.v1.indie_author_follow")
    indie_content_preferences = _lazy_import("app.api.v1.indie_content_preferences")
    mood_categories = _lazy_import("app.api.v1.mood_categories")
    waitlist = _lazy_import("app.api.v1.waitlist")

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(waitlist.router, prefix="/api/v1")
    app.include_router(account_security.router, prefix="/api/v1")
    app.include_router(calendar_feed.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(circulation.router, prefix="/api/v1")
    app.include_router(staff_catalog.router, prefix="/api/v1")
    app.include_router(staff_acquisition_rationales.router, prefix="/api/v1")
    app.include_router(staff_collection_memory.router, prefix="/api/v1")
    app.include_router(catalog_recommendations.router, prefix="/api/v1")
    # Discover router uses literal-only routes today; no /{id} sibling
    # mounted at the same prefix, so router shadowing is N/A. If a paired
    # admin router lands later, mount this one BEFORE it (see
    # feedback_l30_fastapi_router_shadowing).
    app.include_router(discover.router, prefix="/api/v1")
    app.include_router(staff_curated_recs.router, prefix="/api/v1")
    app.include_router(staff_circulation_policy.router, prefix="/api/v1")
    app.include_router(mood_categories.public_router, prefix="/api/v1")
    app.include_router(mood_categories.admin_router, prefix="/api/v1")
    app.include_router(organization_features.router, prefix="/api/v1")
    app.include_router(system_status.router, prefix="/api/v1")
    app.include_router(site_search.router, prefix="/api/v1")
    app.include_router(releases.router, prefix="/api/v1")
    app.include_router(inventory.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(patron_requests.router, prefix="/api/v1")
    app.include_router(feature_requests.router, prefix="/api/v1")
    app.include_router(metislib_ebooks.router, prefix="/api/v1")
    app.include_router(indie_catalog.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_lending.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_bookmarks.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_reading_progress.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_recommendations.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_author_events.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_author_follow.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    app.include_router(indie_content_preferences.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    indie_reading_lists = _lazy_import("app.api.v1.indie_reading_lists")
    app.include_router(indie_reading_lists.router, prefix="/api/v1", dependencies=[Depends(require_indie_platform_enabled)])
    blog = _lazy_import("app.api.v1.blog")
    app.include_router(blog.router, prefix="/api/v1")
    blog_bookmarks = _lazy_import("app.api.v1.blog_bookmarks")
    app.include_router(blog_bookmarks.router, prefix="/api/v1")
    blog_subscriptions = _lazy_import("app.api.v1.blog_subscriptions")
    app.include_router(blog_subscriptions.router, prefix="/api/v1")
    setup_wizard = _lazy_import("app.api.v1.setup")
    app.include_router(setup_wizard.router, prefix="/api/v1")
    catalog_import_mod = _lazy_import('app.api.v1.catalog.import_router')
    app.include_router(catalog_import_mod.router, prefix="/api/v1")
    seo_meta = _lazy_import('app.api.v1.seo_meta')
    app.include_router(seo_meta.router, prefix="/api/v1")
    images_mod = _lazy_import('app.api.v1.images')
    app.include_router(images_mod.router, prefix="/api/v1")

    # --- Home page (data-driven hero + shelves; public + admin) ---
    home_page_routes = _lazy_import('app.api.v1.home_page')
    # Public router first so literal `/page` registers before any `/{id}` could
    # shadow it per [[feedback_l30_fastapi_router_shadowing]].
    app.include_router(home_page_routes.router, prefix="/api/v1")
    app.include_router(home_page_routes.admin_router, prefix="/api/v1")

    # --- Patron validation (third-party vendor auth, no toggle) ---
    patron_validation = _lazy_import("app.api.v1.patron_validation")
    app.include_router(patron_validation.router, prefix="/api/v1")

    # --- Carbon metrics (no toggle) ---
    carbon_metrics = _lazy_import("app.api.v1.carbon_metrics")
    app.include_router(carbon_metrics.router, prefix="/api/v1")

    # --- Nudges (no toggle) ---
    nudges = _lazy_import("app.api.v1.nudges")
    app.include_router(nudges.router, prefix="/api/v1")

    # --- Accessibility analytics (no toggle) ---
    a11y_analytics = _lazy_import("app.api.v1.accessibility_analytics")
    app.include_router(a11y_analytics.router, prefix="/api/v1")

    # --- Events ---
    # NOTE: event_series.router MUST be included before events.router. Both
    # mount at /api/v1/events; the series router's literal /series/{series_id}
    # would otherwise be shadowed by events.router's /{event_id:int} (FastAPI
    # 422s on int coercion before checking the next match). See memory
    # feedback_l30_fastapi_literal_before_param_route.
    event_series = _lazy_import('app.api.v1.event_series')
    app.include_router(event_series.router, prefix="/api/v1", dependencies=[Depends(require_events_enabled)])
    events = _lazy_import('app.api.v1.events')
    app.include_router(events.router, prefix="/api/v1", dependencies=[Depends(require_events_enabled)])
    events_feeds = _lazy_import('app.api.v1.events_feeds')
    app.include_router(events_feeds.router, prefix="/api/v1", dependencies=[Depends(require_events_enabled)])

    # --- Event program partners (used by events presenters; reads are public) ---
    program_partners = _lazy_import('app.api.v1.event_program_partners')
    app.include_router(program_partners.router, prefix="/api/v1", dependencies=[Depends(require_events_enabled)])

    # --- Meeting rooms ---
    staff_rooms = _lazy_import('app.api.v1.staff.rooms')
    rooms = _lazy_import('app.api.v1.rooms')
    app.include_router(staff_rooms.router, prefix="/api/v1", dependencies=[Depends(require_meeting_rooms_enabled)])
    app.include_router(rooms.router, prefix="/api/v1", dependencies=[Depends(require_meeting_rooms_enabled)])

    # --- Patron engagement ---
    cohorts = _lazy_import('app.api.v1.cohorts')
    app.include_router(cohorts.router, prefix="/api/v1", dependencies=[Depends(require_patron_engagement_enabled)])

    # --- Board ---
    board = _lazy_import('app.api.v1.board')
    app.include_router(board.router, prefix="/api/v1", dependencies=[Depends(require_board_features_enabled)])

    # --- Acquisition ---
    acquisition = _lazy_import('app.api.v1.acquisition')
    donations = _lazy_import('app.api.v1.donations')
    _acq_deps = [Depends(require_acquisition_enabled)]
    # intelligence must be included BEFORE the main acquisition router: its literal
    # /funds/intelligence and /vendors/compare routes would otherwise be shadowed by
    # main's /funds/{fund_id} (int) -> 422. See feedback-l30-fastapi-router-shadowing.
    app.include_router(acquisition.intelligence.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.po.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.selection.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.external.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.vendors.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(acquisition.templates.router, prefix="/api/v1", dependencies=_acq_deps)
    app.include_router(donations.router, prefix="/api/v1", dependencies=_acq_deps)

    # --- Processing queue ---
    processing = _lazy_import('app.api.v1.processing')
    app.include_router(processing.router, prefix="/api/v1", dependencies=[Depends(require_processing_queue_enabled)])

    # --- AI ---
    ai_settings = _lazy_import('app.api.v1.ai_settings')
    ai_tools = _lazy_import('app.api.v1.ai_tools')
    library_agents = _lazy_import('app.api.v1.library_agents')
    _ai_deps = [Depends(require_ai_tools_enabled)]
    app.include_router(ai_settings.router, prefix="/api/v1", dependencies=_ai_deps)
    app.include_router(ai_tools.router, prefix="/api/v1", dependencies=_ai_deps)
    app.include_router(library_agents.router, prefix="/api/v1", dependencies=_ai_deps)

    # --- Reading programs ---
    reading = _lazy_import('app.api.v1.reading')
    reading_programs = _lazy_import('app.api.v1.reading_programs')
    family_reading = _lazy_import('app.api.v1.family_reading')
    event_reading_credits = _lazy_import('app.api.v1.event_reading_credits')
    reading_status = _lazy_import('app.api.v1.reading_status')
    reading_goals = _lazy_import('app.api.v1.reading_goals')
    shelf_export = _lazy_import('app.api.v1.shelf_export')
    reviews_router = _lazy_import('app.api.v1.reviews')
    app.include_router(reading.router, prefix="/api/v1", dependencies=[Depends(require_reading_programs_enabled)])
    app.include_router(reading_programs.router, prefix="/api/v1", dependencies=[Depends(require_reading_programs_enabled)])
    app.include_router(family_reading.router, prefix="/api/v1", dependencies=[Depends(require_reading_programs_enabled)])
    app.include_router(event_reading_credits.router, prefix="/api/v1", dependencies=[Depends(require_reading_programs_enabled)])
    reading_progress = _lazy_import('app.api.v1.reading_progress')
    app.include_router(reading_status.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    reading_activity = _lazy_import('app.api.v1.reading_activity')
    reading_milestones = _lazy_import('app.api.v1.reading_milestones')
    patron_shelf_preferences = _lazy_import('app.api.v1.patron_shelf_preferences')
    app.include_router(reading_progress.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    app.include_router(reading_activity.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    app.include_router(reading_milestones.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    patron_tags = _lazy_import('app.api.v1.patron_tags')
    app.include_router(patron_shelf_preferences.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    app.include_router(patron_tags.router, prefix="/api/v1", dependencies=[Depends(require_reading_shelf_enabled)])
    app.include_router(reading_goals.router, prefix="/api/v1", dependencies=[Depends(require_reading_goals_enabled)])
    app.include_router(shelf_export.router, prefix="/api/v1", dependencies=[Depends(require_shelf_data_export_enabled)])
    app.include_router(reviews_router.router, prefix="/api/v1")

    # --- Author AMAs (proxied to MetisLib) ---
    metislib_amas = _lazy_import('app.api.v1.metislib_amas')
    app.include_router(metislib_amas.router, prefix="/api/v1", dependencies=[Depends(require_ama_enabled)])

    # --- Notifications ---
    announcements = _lazy_import('app.api.v1.announcements')
    app.include_router(announcements.router, prefix="/api/v1", dependencies=[Depends(require_notifications_enabled)])

    # --- Homepage curated quotes (public read + admin CRUD) ---
    homepage_quotes = _lazy_import("app.api.v1.homepage_quotes")
    admin_homepage_quotes = _lazy_import("app.api.v1.admin_homepage_quotes")
    app.include_router(homepage_quotes.router, prefix="/api/v1")
    app.include_router(admin_homepage_quotes.router, prefix="/api/v1")

    # --- Community ---
    community = _lazy_import('app.api.v1.community')
    app.include_router(community.router, prefix="/api/v1", dependencies=[Depends(require_community_features_enabled)])


    # Community resource links (public + admin)
    community_resources = _lazy_import("app.api.v1.community_resources")
    app.include_router(community_resources.router, prefix="/api/v1")
    admin_community_resources = _lazy_import("app.api.v1.admin_community_resources")
    app.include_router(admin_community_resources.router, prefix="/api/v1", dependencies=[Depends(require_community_features_enabled)])

    # --- Emergency services ---
    panic_alert = _lazy_import('app.api.v1.panic_alert')
    app.include_router(panic_alert.router, prefix="/api/v1", dependencies=[Depends(require_emergency_services_enabled)])

    # --- Core admin / infrastructure (never toggled) ---
    admin = _lazy_import('app.api.v1.admin')
    admin_analytics = _lazy_import('app.api.v1.admin_analytics')
    admin_demand = _lazy_import('app.api.v1.admin_demand')
    admin_collection_velocity = _lazy_import('app.api.v1.admin_collection_velocity')
    website_analytics = _lazy_import('app.api.v1.website_analytics')
    qr_analytics = _lazy_import('app.api.v1.qr_analytics')
    admin_reading_lists = _lazy_import('app.api.v1.admin_reading_lists')
    patron_reading_lists = _lazy_import('app.api.v1.patron_reading_lists')
    api_status = _lazy_import('app.api.v1.api_status')
    audit_logs = _lazy_import('app.api.v1.audit_logs')
    audit_reversal = _lazy_import('app.api.v1.audit_reversal')
    pii_access_log = _lazy_import('app.api.v1.pii_access_log')
    branches = _lazy_import('app.api.v1.branches')
    households = _lazy_import('app.api.v1.households')
    navigation = _lazy_import('app.api.v1.navigation')
    onboarding = _lazy_import('app.api.v1.onboarding')
    patron_onboarding = _lazy_import('app.api.v1.patron_onboarding')
    permissions = _lazy_import('app.api.v1.permissions')
    roles = _lazy_import('app.api.v1.roles')
    staff_command_search = _lazy_import('app.api.v1.staff_command_search')
    staff_patron_profile_edit = _lazy_import('app.api.v1.staff_patron_profile_edit')
    unified_search = _lazy_import('app.api.v1.unified_search')
    semantic_search = _lazy_import('app.api.v1.semantic_search')
    users = _lazy_import('app.api.v1.users')
    bibframe_catalog = _lazy_import('app.api.v1.bibframe_catalog')
    z3950_cataloging = _lazy_import('app.api.v1.z3950_cataloging')
    federated_search = _lazy_import('app.api.v1.federated_search')
    admin_z3950 = _lazy_import('app.api.v1.admin_z3950')
    admin_indie_import = _lazy_import('app.api.v1.admin_indie_import')

    app.include_router(admin.router, prefix="/api/v1")
    # Also mount admin router under /audit-logs for direct access
    from fastapi import APIRouter as _AR
    from ...core.database import get_db as _get_db
    from .auth import get_current_user as _get_user
    _audit_alias = _AR(tags=["audit-logs"])
    @_audit_alias.get("/audit-logs")
    async def _audit_logs_alias(skip: int = 0, limit: int = 50, current_user=Depends(_get_user), db=Depends(_get_db)):
        from .admin import admin_audit_logs
        return await admin_audit_logs(skip=skip, limit=limit, current_user=current_user, db=db)
    app.include_router(_audit_alias, prefix="/api/v1")
    app.include_router(admin_analytics.router, prefix="/api/v1")
    app.include_router(admin_demand.router, prefix="/api/v1")
    app.include_router(admin_collection_velocity.router, prefix="/api/v1")
    app.include_router(website_analytics.router, prefix="/api/v1")
    app.include_router(qr_analytics.router, prefix="/api/v1")
    app.include_router(admin_reading_lists.router, prefix="/api/v1")
    app.include_router(patron_reading_lists.router, prefix="/api/v1")
    app.include_router(api_status.router, prefix="/api/v1")
    app.include_router(audit_logs.router, prefix="/api/v1")
    app.include_router(audit_reversal.router, prefix="/api/v1")
    app.include_router(pii_access_log.router, prefix="/api/v1")
    app.include_router(branches.router, prefix="/api/v1")
    app.include_router(households.router, prefix="/api/v1")
    app.include_router(navigation.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(patron_onboarding.router, prefix="/api/v1")
    app.include_router(permissions.router, prefix="/api/v1")
    app.include_router(roles.router, prefix="/api/v1")
    app.include_router(staff_command_search.router, prefix="/api/v1")
    app.include_router(staff_patron_profile_edit.router, prefix="/api/v1")
    app.include_router(unified_search.router, prefix="/api/v1")
    app.include_router(semantic_search.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(bibframe_catalog.router, prefix="/api/v1")
    app.include_router(z3950_cataloging.router, prefix="/api/v1")
    app.include_router(federated_search.router, prefix="/api/v1")
    app.include_router(admin_z3950.router, prefix="/api/v1")
    app.include_router(admin_indie_import.router, prefix="/api/v1")

    # --- Financial reports ---
    annual_reports = _lazy_import('app.api.v1.annual_reports')
    financial_reports = _lazy_import('app.api.v1.financial_reports')
    staff_fines = _lazy_import('app.api.v1.staff_fines')
    _fin_deps = [Depends(require_financial_reports_enabled)]
    app.include_router(annual_reports.router, prefix="/api/v1", dependencies=_fin_deps)
    app.include_router(financial_reports.router, prefix="/api/v1", dependencies=_fin_deps)
    app.include_router(staff_fines.router, prefix="/api/v1", dependencies=_fin_deps)

    # --- Streaming / audiobooks ---
    audiobooks = _lazy_import('app.api.v1.audiobooks')
    app.include_router(audiobooks.router, prefix="/api/v1", dependencies=[Depends(require_streaming_enabled)])

    # --- Banned books tracking ---
    book_challenges = _lazy_import('app.api.v1.book_challenges')
    content_flags = _lazy_import('app.api.v1.content_flags')
    _banned_deps = [Depends(require_banned_books_tracking_enabled)]
    app.include_router(book_challenges.router, prefix="/api/v1", dependencies=_banned_deps)
    app.include_router(content_flags.router, prefix="/api/v1", dependencies=_banned_deps)

    # --- Book clubs ---
    book_clubs = _lazy_import('app.api.v1.book_clubs')
    book_clubs_patron = _lazy_import('app.api.v1.book_clubs_patron')
    _clubs_deps = [Depends(require_book_clubs_enabled)]
    # Patron router first so its literal routes (e.g. /genres) win over admin's /{club_id}.
    app.include_router(book_clubs_patron.router, prefix="/api/v1", dependencies=_clubs_deps)
    app.include_router(book_clubs.router, prefix="/api/v1", dependencies=_clubs_deps)

    # --- Compliance ---
    cipa_compliance = _lazy_import('app.api.v1.cipa_compliance')
    app.include_router(cipa_compliance.router, prefix="/api/v1", dependencies=[Depends(require_compliance_enabled)])

    # --- Digital access ---
    database_subscriptions = _lazy_import('app.api.v1.database_subscriptions')
    app.include_router(database_subscriptions.router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])
    digital_activity = _lazy_import('app.api.v1.digital_activity')
    app.include_router(digital_activity.router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])
    stanza_import = _lazy_import('app.api.v1.stanza_import')
    app.include_router(stanza_import.router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])
    digital_resource_status = _lazy_import("app.api.v1.digital_resource_status")
    app.include_router(digital_resource_status.router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])

    # --- Home delivery ---
    delivery_requests = _lazy_import('app.api.v1.delivery_requests')
    home_delivery_applications = _lazy_import('app.api.v1.home_delivery_applications')
    home_delivery_deliveries = _lazy_import('app.api.v1.home_delivery_deliveries')
    home_delivery_reports = _lazy_import('app.api.v1.home_delivery_reports')
    home_delivery_volunteers = _lazy_import('app.api.v1.home_delivery_volunteers')
    _hd_deps = [Depends(require_home_delivery_enabled)]
    app.include_router(delivery_requests.router, prefix="/api/v1", dependencies=_hd_deps)
    app.include_router(home_delivery_applications.router, prefix="/api/v1", dependencies=_hd_deps)
    app.include_router(home_delivery_deliveries.router, prefix="/api/v1", dependencies=_hd_deps)
    app.include_router(home_delivery_reports.router, prefix="/api/v1", dependencies=_hd_deps)
    app.include_router(home_delivery_volunteers.router, prefix="/api/v1", dependencies=_hd_deps)

    # --- Parent onboarding ---
    parent_onboarding = _lazy_import('app.api.v1.parent_onboarding')
    app.include_router(parent_onboarding.router, prefix="/api/v1", dependencies=[Depends(require_parent_onboarding_enabled)])

    # --- Emergency services ---
    emergency_operations = _lazy_import('app.api.v1.emergency_operations')
    app.include_router(emergency_operations.router, prefix="/api/v1", dependencies=[Depends(require_emergency_services_enabled)])

    # --- Offline sync (bookmobile) ---
    offline_sync = _lazy_import("app.api.v1.offline_sync")
    app.include_router(offline_sync.router, prefix="/api/v1")

    # --- Tech services ---
    equipment = _lazy_import('app.api.v1.equipment')
    tech_booking = _lazy_import('app.api.v1.tech_booking')
    staff_tech_booking = _lazy_import('app.api.v1.staff_tech_booking')
    _tech_deps = [Depends(require_tech_services_enabled)]
    app.include_router(equipment.router, prefix="/api/v1", dependencies=_tech_deps)
    app.include_router(tech_booking.router, prefix="/api/v1", dependencies=_tech_deps)
    app.include_router(staff_tech_booking.router, prefix="/api/v1", dependencies=_tech_deps)

    # --- Genealogy ---
    genealogy = _lazy_import('app.api.v1.genealogy')
    genealogy_research = _lazy_import('app.api.v1.genealogy_research')
    _gen_deps = [Depends(require_genealogy_enabled)]
    app.include_router(genealogy.router, prefix="/api/v1", dependencies=_gen_deps)
    app.include_router(genealogy_research.router, prefix="/api/v1", dependencies=_gen_deps)

    # --- Learning platform ---
    learning_feedback = _lazy_import('app.api.v1.learning_feedback')
    _learn_deps = [Depends(require_learning_platform_enabled)]
    app.include_router(learning_feedback.router, prefix="/api/v1", dependencies=_learn_deps)

    # --- Marketing ---
    marketing_hub = _lazy_import('app.api.v1.marketing_hub')
    app.include_router(marketing_hub.router, prefix="/api/v1", dependencies=[Depends(require_marketing_enabled)])

    # --- Notifications ---
    notification_preferences = _lazy_import('app.api.v1.notification_preferences')
    app.include_router(notification_preferences.router, prefix="/api/v1", dependencies=[Depends(require_notifications_enabled)])

    # --- Outreach ---
    outreach = _lazy_import('app.api.v1.outreach')
    app.include_router(outreach.router, prefix="/api/v1", dependencies=[Depends(require_outreach_enabled)])

    # --- Patron engagement ---
    patron_reading_insights = _lazy_import('app.api.v1.patron_reading_insights')
    patron_segmentation = _lazy_import('app.api.v1.patron_segmentation')
    _engage_deps = [Depends(require_patron_engagement_enabled)]
    app.include_router(patron_reading_insights.router, prefix="/api/v1", dependencies=_engage_deps)
    app.include_router(patron_segmentation.router, prefix="/api/v1", dependencies=_engage_deps)

    # --- Staff scheduling ---
    pto = _lazy_import('app.api.v1.pto')
    pto_promotion = _lazy_import('app.api.v1.pto_promotion')
    _sched_deps = [Depends(require_staff_scheduling_enabled)]
    app.include_router(pto.router, prefix="/api/v1", dependencies=_sched_deps)
    app.include_router(pto_promotion.router, prefix="/api/v1", dependencies=_sched_deps)

    # --- Reading programs (extended) ---
    reading_certificates = _lazy_import('app.api.v1.reading_certificates')
    reading_leaderboards = _lazy_import('app.api.v1.reading_leaderboards')
    reading_prizes = _lazy_import('app.api.v1.reading_prizes')
    _read_deps = [Depends(require_reading_programs_enabled)]
    app.include_router(reading_certificates.router, prefix="/api/v1", dependencies=_read_deps)
    app.include_router(reading_leaderboards.router, prefix="/api/v1", dependencies=_read_deps)
    app.include_router(reading_prizes.router, prefix="/api/v1", dependencies=_read_deps)

    # --- Community ---
    social_sharing = _lazy_import('app.api.v1.social_sharing')
    app.include_router(social_sharing.router, prefix="/api/v1", dependencies=[Depends(require_community_features_enabled)])

    # --- Makerspace ---
    staff_makerspace = _lazy_import('app.api.v1.staff_makerspace')
    app.include_router(staff_makerspace.router, prefix="/api/v1", dependencies=[Depends(require_makerspace_enabled)])

    # --- Staff wellness ---
    staff_positivity = _lazy_import('app.api.v1.staff_positivity')
    app.include_router(staff_positivity.router, prefix="/api/v1", dependencies=[Depends(require_staff_wellness_enabled)])

    # --- Storytime ---
    storytime = _lazy_import('app.api.v1.storytime')
    app.include_router(storytime.router, prefix="/api/v1", dependencies=[Depends(require_storytime_enabled)])

    # --- Volunteers ---
    volunteers = _lazy_import('app.api.v1.volunteers')
    app.include_router(volunteers.router, prefix="/api/v1", dependencies=[Depends(require_volunteers_enabled)])

    # --- Teen Volunteers ---
    teen_volunteers = _lazy_import("app.api.v1.teen_volunteers")
    app.include_router(teen_volunteers.router, prefix="/api/v1", dependencies=[Depends(require_volunteers_enabled)])

    # --- Meeting rooms ---
    walk_in_rooms = _lazy_import('app.api.v1.walk_in_rooms')
    app.include_router(walk_in_rooms.router, prefix="/api/v1", dependencies=[Depends(require_meeting_rooms_enabled)])

    # --- ILL ---
    interlibrary_loan = _lazy_import('app.api.v1.interlibrary_loan')
    app.include_router(interlibrary_loan.router, prefix="/api/v1", dependencies=[Depends(require_ill_enabled)])

    # --- Serials ---
    serials = _lazy_import('app.api.v1.serials')
    app.include_router(serials.router, prefix="/api/v1", dependencies=[Depends(require_serials_enabled)])

    # --- MARC batch (under acquisition) ---
    marc_batch = _lazy_import('app.api.v1.marc_batch')
    app.include_router(marc_batch.router, prefix="/api/v1", dependencies=_acq_deps)

    # --- MARC macros (cataloger task lists; gated only by require_staff) ---
    marc_macros = _lazy_import('app.api.v1.marc_macros')
    app.include_router(marc_macros.router, prefix="/api/v1")

    # --- Repairs (core -- no toggle, always available) ---
    repairs = _lazy_import('app.api.v1.repairs')
    app.include_router(repairs.router, prefix="/api/v1")

    # --- PLS export (under financial reports) ---
    pls_export = _lazy_import('app.api.v1.pls_export')
    app.include_router(pls_export.router, prefix="/api/v1", dependencies=_fin_deps)

    # --- Core staff (no toggle) ---
    staff_dashboard = _lazy_import('app.api.v1.staff.dashboard')
    staff_message_board = _lazy_import('app.api.v1.staff_message_board')
    stats = _lazy_import('app.api.v1.stats')
    public_stats = _lazy_import('app.api.v1.public_stats')
    app.include_router(staff_dashboard.router, prefix="/api/v1")
    staff_dashboards = _lazy_import('app.api.v1.staff_dashboards')
    app.include_router(staff_dashboards.router, prefix="/api/v1")
    staff_dashboard_profile = _lazy_import('app.api.v1.staff.dashboard_profile')
    app.include_router(staff_dashboard_profile.router, prefix="/api/v1")
    staff_desk_state = _lazy_import('app.api.v1.staff.desk_state')
    app.include_router(staff_desk_state.router, prefix="/api/v1")
    staff_shift_handoff = _lazy_import("app.api.v1.staff.shift_handoff")
    app.include_router(staff_shift_handoff.router, prefix="/api/v1")
    staff_pay_rates = _lazy_import("app.api.v1.staff.pay_rates")
    app.include_router(staff_pay_rates.router, prefix="/api/v1")
    staff_shelver_dash = _lazy_import('app.api.v1.staff.shelver_dashboard')
    app.include_router(staff_shelver_dash.router, prefix="/api/v1")
    staff_schedule = _lazy_import('app.api.v1.staff.schedule_today')
    app.include_router(staff_schedule.router, prefix="/api/v1")
    staff_marketing_dashboard = _lazy_import('app.api.v1.staff.marketing_dashboard')
    app.include_router(staff_marketing_dashboard.router, prefix="/api/v1")
    staff_kids_dashboard = _lazy_import('app.api.v1.staff.kids_dashboard')
    app.include_router(staff_kids_dashboard.router, prefix="/api/v1")
    staff_presence = _lazy_import('app.api.v1.staff.staff_presence')
    app.include_router(staff_presence.router, prefix="/api/v1")
    staff_timesheet = _lazy_import('app.api.v1.staff.timesheet')
    app.include_router(staff_timesheet.router, prefix="/api/v1")
    staff_desk_schedule = _lazy_import('app.api.v1.staff.desk_schedule')
    app.include_router(staff_desk_schedule.router, prefix="/api/v1")
    staff_content_translations = _lazy_import('app.api.v1.staff.content_translations')
    app.include_router(staff_content_translations.router, prefix="/api/v1")
    app.include_router(staff_message_board.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")
    app.include_router(public_stats.router, prefix="/api/v1")

    # --- Youth public page ---
    youth = _lazy_import('app.api.v1.youth')
    app.include_router(youth.router, prefix="/api/v1")

    # --- Tech services ---
    tech_support = _lazy_import('app.api.v1.tech_support')
    app.include_router(tech_support.router, prefix="/api/v1", dependencies=_tech_deps)

    # --- Core circulation / staff (no toggle) ---
    attendance = _lazy_import('app.api.v1.attendance')
    audit = _lazy_import('app.api.v1.audit')
    ban_tracker = _lazy_import('app.api.v1.ban_tracker')
    ban_tracker_subscriptions = _lazy_import('app.api.v1.ban_tracker_subscriptions')
    ban_tracker_subscriptions_public = _lazy_import('app.api.v1.ban_tracker_subscriptions_public')
    card_applications = _lazy_import('app.api.v1.card_applications')
    teacher_applications = _lazy_import('app.api.v1.teacher_applications')
    consortiums = _lazy_import('app.api.v1.consortiums')
    end_of_day = _lazy_import('app.api.v1.end_of_day')
    end_of_shift = _lazy_import('app.api.v1.end_of_shift')
    immigrant_services = _lazy_import('app.api.v1.immigrant_services')
    operations_audit = _lazy_import('app.api.v1.operations_audit')
    patron_account = _lazy_import('app.api.v1.patron_account')
    patron_preferences = _lazy_import('app.api.v1.patron_preferences')
    patron_profile = _lazy_import('app.api.v1.patron_profile')
    privacy = _lazy_import('app.api.v1.privacy')
    public_records = _lazy_import('app.api.v1.public_records')
    report_exports = _lazy_import('app.api.v1.report_exports')
    staff_analytics = _lazy_import('app.api.v1.staff_analytics')
    staff_lost_damaged = _lazy_import('app.api.v1.staff_lost_damaged')
    staff_picks = _lazy_import('app.api.v1.staff.picks')
    staff_patron_operations = _lazy_import('app.api.v1.staff.patron_operations')
    staff_patron_messages = _lazy_import('app.api.v1.staff.patron_messages')
    staff_pii_access_log = _lazy_import('app.api.v1.staff.pii_access_log')
    staff_circulation_checkin = _lazy_import('app.api.v1.staff.circulation_checkin')
    unified_reports = _lazy_import('app.api.v1.unified_reports')
    report_schedules = _lazy_import('app.api.v1.report_schedules')
    community_outcomes = _lazy_import('app.api.v1.community_outcomes')
    impact = _lazy_import('app.api.v1.impact')
    workflows = _lazy_import('app.api.v1.workflows')

    app.include_router(attendance.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(ban_tracker.router, prefix="/api/v1")
    app.include_router(ban_tracker_subscriptions.router, prefix="/api/v1")
    app.include_router(ban_tracker_subscriptions_public.router, prefix="/api/v1")
    app.include_router(card_applications.router, prefix="/api/v1")
    app.include_router(teacher_applications.router, prefix="/api/v1")
    app.include_router(consortiums.router, prefix="/api/v1")
    app.include_router(end_of_day.router, prefix="/api/v1")
    app.include_router(end_of_shift.router, prefix="/api/v1")
    app.include_router(immigrant_services.router, prefix="/api/v1")
    app.include_router(operations_audit.router, prefix="/api/v1")
    app.include_router(patron_account.router, prefix="/api/v1")
    app.include_router(patron_preferences.router, prefix="/api/v1")
    app.include_router(patron_profile.router, prefix="/api/v1")
    # Saved catalog searches — gated by both patron portal and the
    # saved_searches_enabled toggle so it can be rolled out per library.
    saved_searches = _lazy_import("app.api.v1.saved_searches")
    app.include_router(
        saved_searches.router,
        prefix="/api/v1",
        dependencies=[
            Depends(require_patron_portal_enabled),
            Depends(require_saved_searches_enabled),
        ],
    )
    app.include_router(privacy.router, prefix="/api/v1")
    app.include_router(public_records.router, prefix="/api/v1")
    app.include_router(report_exports.router, prefix="/api/v1")
    app.include_router(staff_analytics.router, prefix="/api/v1")
    app.include_router(staff_lost_damaged.router, prefix="/api/v1")
    app.include_router(staff_picks.router, prefix="/api/v1")
    # bulk_router (prefix /staff/patrons/messages) must mount BEFORE
    # staff_patron_operations.router (prefix /staff/patrons) so that
    # /staff/patrons/messages/bulk is not shadowed by /staff/patrons/{patron_id}.
    # See feedback_l30_fastapi_router_shadowing.
    app.include_router(staff_patron_messages.bulk_router, prefix="/api/v1")
    app.include_router(staff_patron_operations.router, prefix="/api/v1")
    app.include_router(staff_patron_messages.router, prefix="/api/v1")
    app.include_router(staff_pii_access_log.router, prefix="/api/v1")
    app.include_router(staff_circulation_checkin.router, prefix="/api/v1")
    staff_circulation_slip = _lazy_import('app.api.v1.staff.circulation_slip')
    app.include_router(staff_circulation_slip.router, prefix="/api/v1")
    app.include_router(unified_reports.router, prefix="/api/v1")
    app.include_router(report_schedules.router, prefix="/api/v1")
    app.include_router(community_outcomes.router, prefix="/api/v1", dependencies=[Depends(require_community_outcomes_enabled)])
    app.include_router(impact.router, prefix="/api/v1", dependencies=[Depends(require_impact_measurement_enabled)])
    app.include_router(workflows.router, prefix="/api/v1")

    # --- Collection management ---
    book_drop = _lazy_import('app.api.v1.book_drop')
    shelf_reading = _lazy_import('app.api.v1.shelf_reading')
    weeding = _lazy_import('app.api.v1.weeding')
    archival_collections = _lazy_import('app.api.v1.archival_collections')
    _coll_deps = [Depends(require_collection_management_enabled)]
    app.include_router(book_drop.router, prefix="/api/v1", dependencies=_coll_deps)
    app.include_router(shelf_reading.router, prefix="/api/v1", dependencies=_coll_deps)
    app.include_router(weeding.router, prefix="/api/v1", dependencies=_coll_deps)
    app.include_router(archival_collections.router, prefix="/api/v1", dependencies=_coll_deps)

    # --- Financial ---
    cash_drawer = _lazy_import('app.api.v1.cash_drawer')
    purchase_requests = _lazy_import('app.api.v1.purchase_requests')
    app.include_router(cash_drawer.router, prefix="/api/v1", dependencies=_fin_deps)
    app.include_router(purchase_requests.router, prefix="/api/v1", dependencies=_acq_deps)

    # --- Tech services ---
    computers = _lazy_import('app.api.v1.computers')
    app.include_router(computers.router, prefix="/api/v1", dependencies=_tech_deps)


    admin_computers = _lazy_import("app.api.v1.admin_computers")
    app.include_router(admin_computers.router, prefix="/api/v1", dependencies=_tech_deps)

    admin_data_export = _lazy_import("app.api.v1.admin_data_export")
    app.include_router(admin_data_export.router, prefix="/api/v1", dependencies=_tech_deps)
    app.include_router(admin_data_export.retention_router, prefix="/api/v1", dependencies=_tech_deps)
    # --- Digital access ---
    ebook_access_cards = _lazy_import('app.api.v1.ebook_access_cards')
    app.include_router(ebook_access_cards.router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])

    # --- Events / marketing ---
    event_marketing = _lazy_import('app.api.v1.event_marketing')
    program_planning = _lazy_import('app.api.v1.program_planning')
    _event_deps = [Depends(require_events_enabled)]
    app.include_router(event_marketing.router, prefix="/api/v1", dependencies=_event_deps)
    app.include_router(program_planning.router, prefix="/api/v1", dependencies=_event_deps)

    # --- Staff wellness ---
    focus_time = _lazy_import('app.api.v1.focus_time')
    public_positivity = _lazy_import('app.api.v1.public_positivity')
    _wellness_deps = [Depends(require_staff_wellness_enabled)]
    app.include_router(focus_time.router, prefix="/api/v1", dependencies=_wellness_deps)
    app.include_router(public_positivity.router, prefix="/api/v1", dependencies=_wellness_deps)

    # --- AI tools ---
    ollama_admin = _lazy_import('app.api.v1.ollama_admin')
    app.include_router(ollama_admin.router, prefix="/api/v1", dependencies=_ai_deps)

    # --- Printing ---
    print_notices = _lazy_import('app.api.v1.print_notices')
    app.include_router(print_notices.router, prefix="/api/v1", dependencies=[Depends(require_printing_enabled)])

    # --- Reading programs ---
    # NOTE: staff_library_visits MUST be included before school_reading.
    # The latter registers GET /library-visits/requests/{school_id} which would
    # otherwise shadow our literal GET /library-visits/requests
    # (see feedback_l30_fastapi_router_shadowing).
    staff_library_visits = _lazy_import('app.api.v1.staff_library_visits')
    app.include_router(staff_library_visits.router, prefix="/api/v1", dependencies=_read_deps)
    school_reading = _lazy_import('app.api.v1.school_reading')
    app.include_router(school_reading.router, prefix="/api/v1", dependencies=_read_deps)

    # --- Staff scheduling ---
    shift_swap = _lazy_import('app.api.v1.shift_swap')
    app.include_router(shift_swap.router, prefix="/api/v1", dependencies=_sched_deps)

    # --- Signage ---
    signage = _lazy_import('app.api.v1.signage')
    app.include_router(signage.router, prefix="/api/v1", dependencies=[Depends(require_signage_enabled)])

    # --- Notifications ---
    sms = _lazy_import('app.api.v1.sms')
    app.include_router(sms.router, prefix="/api/v1", dependencies=[Depends(require_notifications_enabled)])

    # --- Emergency services ---
    staff_safety = _lazy_import('app.api.v1.staff.safety')
    staff_medical_alerts = _lazy_import('app.api.v1.staff.medical_emergency_alerts')
    _emerg_deps = [Depends(require_emergency_services_enabled)]
    app.include_router(staff_safety.router, prefix="/api/v1", dependencies=_emerg_deps)
    app.include_router(staff_medical_alerts.router, prefix="/api/v1", dependencies=_emerg_deps)
    staff_help = _lazy_import("app.api.v1.staff.staff_help")
    app.include_router(staff_help.router, prefix="/api/v1")

    # =====================================================================
    # Batch 4: Top-level routers with feature guards
    # =====================================================================

    # Beta
    beta_feedback = _lazy_import('app.api.v1.beta_feedback')
    app.include_router(beta_feedback.router, prefix="/api/v1", dependencies=[Depends(require_beta_features_enabled)])

    # Board (legacy standalone files removed -- covered by board sub-package aggregator)
    _board_deps = [Depends(require_board_features_enabled)]

    # --- Homepage content management (no toggle) ---
    homepage_quick_links = _lazy_import('app.api.v1.homepage_quick_links')
    library_hours = _lazy_import('app.api.v1.library_hours')
    library_pitch = _lazy_import('app.api.v1.library_pitch')
    app.include_router(homepage_quick_links.router, prefix="/api/v1")
    app.include_router(library_hours.router, prefix="/api/v1")
    app.include_router(library_pitch.router, prefix="/api/v1")

    # Core infrastructure (no toggle)
    branding_router = _lazy_import('app.api.v1.branding')
    cache_dashboard = _lazy_import('app.api.v1.cache_dashboard')
    health_router_mod = _lazy_import('app.api.v1.health')
    import_routes = _lazy_import('app.api.v1.import_routes')
    import_templates = _lazy_import('app.api.v1.import_templates')
    patron_categories = _lazy_import('app.api.v1.patron_categories')
    migration_wizard = _lazy_import('app.api.v1.migration_wizard')
    migration_project = _lazy_import('app.api.v1.migration_project')
    task_batching = _lazy_import('app.api.v1.task_batching')
    library_documents = _lazy_import('app.api.v1.library_documents')
    professional_judgment = _lazy_import('app.api.v1.professional_judgment')
    patron_boundaries = _lazy_import('app.api.v1.patron_boundaries')
    patron_claims_returned = _lazy_import('app.api.v1.patron_claims_returned')
    publishers = _lazy_import('app.api.v1.publishers')
    found_items = _lazy_import('app.api.v1.found_items')

    app.include_router(branding_router.router, prefix="/api/v1")
    app.include_router(cache_dashboard.router, prefix="/api/v1")
    app.include_router(health_router_mod.router, prefix="/api/v1")
    app.include_router(import_routes.router, prefix="/api/v1")
    app.include_router(import_templates.router, prefix="/api/v1")
    app.include_router(patron_categories.router, prefix="/api/v1")
    app.include_router(migration_wizard.router, prefix="/api/v1", dependencies=[Depends(require_migration_enabled)])
    app.include_router(migration_project.router, prefix="/api/v1", dependencies=[Depends(require_migration_enabled)])
    app.include_router(task_batching.router, prefix="/api/v1")
    app.include_router(library_documents.router, prefix="/api/v1")
    app.include_router(professional_judgment.router, prefix="/api/v1")
    app.include_router(patron_boundaries.router, prefix="/api/v1")
    app.include_router(patron_claims_returned.router, prefix="/api/v1")
    app.include_router(publishers.router, prefix="/api/v1")
    app.include_router(found_items.router, prefix="/api/v1")

    # Gamification

    # Digital access

    # Acquisition / EDI
    edi = _lazy_import('app.api.v1.edi')
    app.include_router(edi.router, prefix="/api/v1", dependencies=_acq_deps)

    # Emergency services
    emergency_routing = _lazy_import('app.api.v1.emergency_routing')
    app.include_router(emergency_routing.router, prefix="/api/v1", dependencies=_emerg_deps)

    # Staff scheduling
    fair_scheduling = _lazy_import('app.api.v1.fair_scheduling')
    scheduler_admin = _lazy_import('app.api.v1.scheduler_admin')
    app.include_router(fair_scheduling.router, prefix="/api/v1", dependencies=_sched_deps)
    app.include_router(scheduler_admin.router, prefix="/api/v1", dependencies=_sched_deps)

    # FAQ chatbot
    faq_chatbot = _lazy_import('app.api.v1.faq_chatbot')
    app.include_router(faq_chatbot.router, prefix="/api/v1", dependencies=[Depends(require_faq_chatbot_enabled)])

    # Free ebooks
    free_ebooks = _lazy_import('app.api.v1.free_ebooks')
    gutenberg = _lazy_import('app.api.v1.gutenberg')
    open_library = _lazy_import('app.api.v1.open_library')
    _ebook_deps = [Depends(require_free_ebooks_enabled)]
    app.include_router(free_ebooks.router, prefix="/api/v1", dependencies=_ebook_deps)
    app.include_router(gutenberg.router, prefix="/api/v1", dependencies=_ebook_deps)
    app.include_router(open_library.router, prefix="/api/v1", dependencies=_ebook_deps)

    # Patron engagement
    journey_analytics = _lazy_import("app.api.v1.journey_analytics")
    patron_ws = _lazy_import('app.api.v1.patron_ws')
    app.include_router(journey_analytics.router, prefix="/api/v1", dependencies=_engage_deps)
    app.include_router(patron_ws.router, prefix="/api/v1", dependencies=[Depends(require_patron_portal_enabled)])

    # Staff wellness
    joy_capture = _lazy_import('app.api.v1.joy_capture')
    perfectionism_antidotes = _lazy_import('app.api.v1.perfectionism_antidotes')
    app.include_router(joy_capture.router, prefix="/api/v1", dependencies=_wellness_deps)
    app.include_router(perfectionism_antidotes.router, prefix="/api/v1", dependencies=_wellness_deps)

    # Literacy programs
    literacy_learners = _lazy_import('app.api.v1.literacy_learners')
    literacy_matching = _lazy_import('app.api.v1.literacy_matching')
    literacy_outcomes = _lazy_import('app.api.v1.literacy_outcomes')
    literacy_tutors = _lazy_import('app.api.v1.literacy_tutors')
    _lit_deps = [Depends(require_literacy_programs_enabled)]
    app.include_router(literacy_learners.router, prefix="/api/v1", dependencies=_lit_deps)
    app.include_router(literacy_matching.router, prefix="/api/v1", dependencies=_lit_deps)
    app.include_router(literacy_outcomes.router, prefix="/api/v1", dependencies=_lit_deps)
    app.include_router(literacy_tutors.router, prefix="/api/v1", dependencies=_lit_deps)

    # Community
    partner_collaboration = _lazy_import('app.api.v1.partner_collaboration')
    app.include_router(partner_collaboration.router, prefix="/api/v1", dependencies=[Depends(require_community_features_enabled)])

    # Printing
    print_router_mod = _lazy_import('app.api.v1.print')
    app.include_router(print_router_mod.router, prefix="/api/v1", dependencies=[Depends(require_printing_enabled)])

    # Strategic planning
    strategic_admin = _lazy_import('app.api.v1.strategic_admin')
    strategic_board = _lazy_import('app.api.v1.strategic_board')
    strategic_goals = _lazy_import('app.api.v1.strategic_goals')
    strategic_milestones = _lazy_import('app.api.v1.strategic_milestones')
    strategic_plans = _lazy_import('app.api.v1.strategic_plans')
    _strat_deps = [Depends(require_strategic_planning_enabled)]
    app.include_router(strategic_admin.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_board.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_goals.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_milestones.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_plans.router, prefix="/api/v1", dependencies=_strat_deps)

    # =====================================================================
    # Sub-package routers with feature guards
    # =====================================================================

    # Board sub-packages (removed -- already included via board aggregator at line ~144)

    # Legal sub-packages
    legal_calculators = _lazy_import('app.api.v1.legal.calculators')
    legal_clinics = _lazy_import('app.api.v1.legal.clinics')
    legal_collections = _lazy_import('app.api.v1.legal.collections')
    legal_compliance = _lazy_import('app.api.v1.legal.compliance')
    legal_courts = _lazy_import('app.api.v1.legal.courts')
    legal_documents = _lazy_import('app.api.v1.legal.documents')
    legal_emergency = _lazy_import('app.api.v1.legal.emergency')
    legal_forms = _lazy_import('app.api.v1.legal.forms')
    legal_glossary = _lazy_import('app.api.v1.legal.glossary')
    legal_guides = _lazy_import('app.api.v1.legal.guides')
    legal_packets = _lazy_import('app.api.v1.legal.packets')
    legal_providers = _lazy_import('app.api.v1.legal.providers')
    legal_reporting = _lazy_import('app.api.v1.legal.reporting')
    legal_reviews = _lazy_import('app.api.v1.legal.reviews')
    legal_wizard = _lazy_import('app.api.v1.legal.wizard')
    legal_bankruptcy = _lazy_import('app.api.v1.legal.bankruptcy')
    _legal_deps = [Depends(require_legal_services_enabled)]
    app.include_router(legal_calculators.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_clinics.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_collections.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_compliance.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_courts.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_documents.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_emergency.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_forms.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_glossary.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_guides.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_packets.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_providers.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_reporting.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_reviews.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_wizard.router, prefix="/api/v1", dependencies=_legal_deps)
    app.include_router(legal_bankruptcy.router, prefix="/api/v1", dependencies=_legal_deps)

    # Staff sub-packages (core -- no toggle)
    staff_collection_alerts = _lazy_import('app.api.v1.staff.collection_alerts')
    staff_directory = _lazy_import('app.api.v1.staff.directory')
    staff_error_recovery = _lazy_import('app.api.v1.staff.error_recovery')
    staff_knowledge = _lazy_import('app.api.v1.staff.knowledge')
    staff_patrons_account = _lazy_import('app.api.v1.staff.patrons_account')
    staff_reports = _lazy_import('app.api.v1.staff.reports')
    staff_staff_search = _lazy_import('app.api.v1.staff.staff_search')
    app.include_router(staff_collection_alerts.router, prefix="/api/v1")
    app.include_router(staff_directory.router, prefix="/api/v1")
    app.include_router(staff_error_recovery.router, prefix="/api/v1")
    app.include_router(staff_knowledge.router, prefix="/api/v1")
    app.include_router(staff_patrons_account.router, prefix="/api/v1")
    app.include_router(staff_reports.router, prefix="/api/v1")
    app.include_router(staff_staff_search.router, prefix="/api/v1")

    # Staff outreach
    staff_outreach = _lazy_import('app.api.v1.staff.outreach')
    app.include_router(staff_outreach.router, prefix="/api/v1", dependencies=[Depends(require_outreach_enabled)])

    # Staff training
    staff_training_sub = _lazy_import('app.api.v1.staff.training')
    app.include_router(staff_training_sub.router, prefix="/api/v1", dependencies=[Depends(require_training_modules_enabled)])

    # Staff Lost/Damaged sub-packages (core -- no toggle)
    sld_claims_returned = _lazy_import('app.api.v1.staff_lost_damaged.claims_returned')
    sld_damaged_items = _lazy_import('app.api.v1.staff_lost_damaged.damaged_items')
    sld_item_issues_unified = _lazy_import('app.api.v1.staff_lost_damaged.item_issues_unified')
    sld_lost_items = _lazy_import('app.api.v1.staff_lost_damaged.lost_items')
    sld_reports = _lazy_import('app.api.v1.staff_lost_damaged.reports')
    app.include_router(sld_claims_returned.router, prefix="/api/v1")
    app.include_router(sld_damaged_items.router, prefix="/api/v1")
    app.include_router(sld_item_issues_unified.router, prefix="/api/v1")
    app.include_router(sld_lost_items.router, prefix="/api/v1")
    app.include_router(sld_reports.router, prefix="/api/v1")

    # Strategic planning sub-packages
    strategic_attachments = _lazy_import('app.api.v1.strategic.attachments')
    strategic_collaboration = _lazy_import('app.api.v1.strategic.collaboration')
    strategic_initiatives = _lazy_import('app.api.v1.strategic.initiatives')
    strategic_kpis = _lazy_import('app.api.v1.strategic.kpis')
    app.include_router(strategic_attachments.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_collaboration.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_initiatives.router, prefix="/api/v1", dependencies=_strat_deps)
    app.include_router(strategic_kpis.router, prefix="/api/v1", dependencies=_strat_deps)

    # =====================================================================
    # Batch 5: Previously disabled modules (now with feature guards)
    # =====================================================================
    knowledge_base = _lazy_import('app.api.v1.knowledge_base')
    app.include_router(knowledge_base.router, prefix="/api/v1")
    knowledge_pipeline = _lazy_import('app.api.v1.knowledge_pipeline')
    app.include_router(knowledge_pipeline.router, prefix="/api/v1")

    # Learning platform
    learning = _lazy_import('app.api.v1.learning')
    learning_paths = _lazy_import('app.api.v1.learning_paths')
    learning_path_cohorts = _lazy_import('app.api.v1.learning_path_cohorts')
    learning_lessons = _lazy_import('app.api.v1.learning_lessons')
    learning_certificates = _lazy_import('app.api.v1.learning_certificates')
    learning_quizzes = _lazy_import('app.api.v1.learning_quizzes')
    learning_gamification = _lazy_import('app.api.v1.learning_gamification')
    learning_sessions = _lazy_import('app.api.v1.learning_sessions')
    learning_external_resources = _lazy_import('app.api.v1.learning_external_resources')
    engagement_surveys = _lazy_import('app.api.v1.engagement_surveys')
    app.include_router(learning.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_external_resources.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_paths.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(
        learning_path_cohorts.router,
        prefix="/api/v1",
        dependencies=_learn_deps + [Depends(require_cohort_enabled)],
    )
    app.include_router(learning_lessons.router, prefix="/api/v1", dependencies=_learn_deps)
    # User accessibility/UI preferences are global per-user settings, so they are
    # mounted WITHOUT the learning-platform guard (auth-only). Keeps the same URL
    # (/api/v1/learning/preferences) while staying available when the learning
    # platform feature is disabled.
    app.include_router(learning_lessons.preferences_router, prefix="/api/v1")
    app.include_router(learning_certificates.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_quizzes.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_gamification.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_gamification.router_labs, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(learning_sessions.router, prefix="/api/v1", dependencies=_learn_deps)
    app.include_router(engagement_surveys.router, prefix="/api/v1", dependencies=_learn_deps)

    # Reading programs
    reading_lists_public = _lazy_import('app.api.v1.reading_lists_public')
    reading_minutes = _lazy_import('app.api.v1.reading_minutes')
    app.include_router(reading_lists_public.router, prefix="/api/v1", dependencies=_read_deps)
    app.include_router(reading_minutes.router, prefix="/api/v1", dependencies=_read_deps)

    # Makerspace
    makerspace = _lazy_import('app.api.v1.makerspace')
    app.include_router(makerspace.router, prefix="/api/v1", dependencies=[Depends(require_makerspace_enabled)])

    # Training
    training = _lazy_import('app.api.v1.training')
    app.include_router(training.router, prefix="/api/v1", dependencies=[Depends(require_training_modules_enabled)])

    # Core infrastructure (no toggle)
    lifecycle = _lazy_import('app.api.v1.lifecycle')
    monitoring = _lazy_import('app.api.v1.monitoring')
    usage_statistics = _lazy_import('app.api.v1.usage_statistics')
    linked_data = _lazy_import('app.api.v1.linked_data')
    local_authority = _lazy_import('app.api.v1.local_authority')
    sparql = _lazy_import('app.api.v1.sparql')
    lcsh = _lazy_import('app.api.v1.lcsh')
    rubrics = _lazy_import('app.api.v1.rubrics')
    review_responses = _lazy_import('app.api.v1.review_responses')
    link_health = _lazy_import('app.api.v1.link_health')
    meta_tags = _lazy_import('app.api.v1.meta_tags')
    favorites = _lazy_import('app.api.v1.favorites')
    hub_infra = _lazy_import('app.api.v1.hub_infra')
    support = _lazy_import('app.api.v1.support')
    work_relationships = _lazy_import('app.api.v1.work_relationships')
    series_management = _lazy_import('app.api.v1.series_management')
    postgres_search = _lazy_import('app.api.v1.postgres_search')
    app.include_router(lifecycle.router, prefix="/api/v1")
    app.include_router(monitoring.router, prefix="/api/v1")
    app.include_router(usage_statistics.router, prefix="/api/v1")
    app.include_router(linked_data.router, prefix="/api/v1")
    app.include_router(local_authority.router, prefix="/api/v1")
    app.include_router(sparql.router, prefix="/api/v1")
    app.include_router(lcsh.router, prefix="/api/v1")
    app.include_router(rubrics.router, prefix="/api/v1")
    app.include_router(review_responses.router, prefix="/api/v1")
    app.include_router(link_health.router, prefix="/api/v1")
    app.include_router(meta_tags.router, prefix="/api/v1")
    app.include_router(favorites.router, prefix="/api/v1")
    app.include_router(hub_infra.router, prefix="/api/v1")
    app.include_router(support.router, prefix="/api/v1")

    # --- Admin: integrations status (read-only diagnostics) ---
    integrations = _lazy_import("app.api.v1.integrations")
    app.include_router(integrations.router, prefix="/api/v1")
    app.include_router(work_relationships.router, prefix="/api/v1")
    app.include_router(series_management.router, prefix="/api/v1")
    app.include_router(postgres_search.router, prefix="/api/v1")

    # Bookmobile (stub)
    bookmobile = _lazy_import('app.api.v1.bookmobile')
    app.include_router(bookmobile.router, prefix="/api/v1")

    # Reading history
    reading_history = _lazy_import('app.api.v1.reading_history')
    app.include_router(reading_history.router, prefix="/api/v1")

    # Streaming
    streaming = _lazy_import('app.api.v1.streaming')
    app.include_router(streaming.router, prefix="/api/v1", dependencies=[Depends(require_streaming_enabled)])

    # SIP2/RFID
    sip2 = _lazy_import('app.api.v1.sip2')
    rfid = _lazy_import('app.api.v1.rfid')
    rfid_simulator = _lazy_import('app.api.v1.rfid_simulator')
    _sip_deps = [Depends(require_sip2_rfid_enabled)]
    app.include_router(sip2.router, prefix="/api/v1", dependencies=_sip_deps)
    app.include_router(rfid.router, prefix="/api/v1", dependencies=_sip_deps)
    app.include_router(rfid_simulator.router, prefix="/api/v1", dependencies=_sip_deps)

    # Cataloging (core -- no toggle)
    manga_cataloging = _lazy_import('app.api.v1.manga_cataloging')
    comic_cataloging = _lazy_import('app.api.v1.comic_cataloging')
    app.include_router(manga_cataloging.router, prefix="/api/v1")
    app.include_router(comic_cataloging.router, prefix="/api/v1")

    # Marketing
    marketing = _lazy_import('app.api.v1.marketing')
    app.include_router(marketing.router, prefix="/api/v1", dependencies=[Depends(require_marketing_enabled)])

    # Financial
    material_cost = _lazy_import('app.api.v1.material_cost')
    app.include_router(material_cost.router, prefix="/api/v1", dependencies=_fin_deps)

    # Compliance
    law_enforcement = _lazy_import('app.api.v1.law_enforcement')
    state_compliance = _lazy_import('app.api.v1.state_compliance')
    unified_compliance_audit = _lazy_import('app.api.v1.unified_compliance_audit')
    _comp_deps = [Depends(require_compliance_enabled)]
    app.include_router(law_enforcement.router, prefix="/api/v1", dependencies=_comp_deps)
    app.include_router(state_compliance.router, prefix="/api/v1", dependencies=_comp_deps)
    app.include_router(unified_compliance_audit.router, prefix="/api/v1", dependencies=_comp_deps)

    # Patron engagement
    patron_communication = _lazy_import('app.api.v1.patron_communication')
    patron_engagement = _lazy_import('app.api.v1.patron_engagement')
    app.include_router(patron_communication.router, prefix="/api/v1", dependencies=_engage_deps)
    app.include_router(patron_engagement.router, prefix="/api/v1", dependencies=_engage_deps)

    # Staff scheduling
    intelligent_scheduling = _lazy_import('app.api.v1.intelligent_scheduling')
    app.include_router(intelligent_scheduling.router, prefix="/api/v1", dependencies=_sched_deps)

    # Emergency services
    threat_response = _lazy_import('app.api.v1.threat_response')
    app.include_router(threat_response.router, prefix="/api/v1", dependencies=_emerg_deps)

    # Notifications
    notifications = _lazy_import('app.api.v1.notifications')
    app.include_router(notifications.router, prefix="/api/v1", dependencies=[Depends(require_notifications_enabled)])

    # Staff ebook curation & MARC authority (MetisLib integration)
    staff_ebook_curation = _lazy_import('app.api.v1.staff.ebook_curation')
    app.include_router(staff_ebook_curation.router, prefix="/api/v1")
    staff_marc_authority = _lazy_import('app.api.v1.staff.marc_authority')
    app.include_router(staff_marc_authority.router, prefix="/api/v1")
    staff_invites = _lazy_import('app.api.v1.staff_invites')
    app.include_router(staff_invites.router, prefix="/api/v1")

    # =====================================================================
    # Secondary routers from already-registered modules
    # =====================================================================
    app.include_router(book_challenges.resources_router, prefix="/api/v1", dependencies=_banned_deps)
    app.include_router(ban_tracker.advocacy_router, prefix="/api/v1")
    app.include_router(patron_onboarding.analytics_router, prefix="/api/v1")
    app.include_router(patron_account.staff_router, prefix="/api/v1")
    app.include_router(ebook_access_cards.admin_router, prefix="/api/v1", dependencies=[Depends(require_digital_access_enabled)])

    # =====================================================================
    # Test cleanup (env-var gated, never in production)
    # =====================================================================
    if os.environ.get("TESTING_ENABLED", "").lower() == "true":
        test_cleanup = _lazy_import('app.api.v1.test_cleanup')
        app.include_router(test_cleanup.router, prefix="/api/v1")
