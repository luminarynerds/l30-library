# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared feature toggle dependency guards for API routers.

Each guard function checks if a specific organization feature is enabled.
Used as router-level dependencies via `dependencies=[Depends(guard)]`
either on individual routers or at `app.include_router()` call sites.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...services.organization_features_service import OrganizationFeaturesService


FEATURE_REGISTRY: list[dict[str, str]] = []


def _make_feature_guard(feature_name: str, label: str):
    FEATURE_REGISTRY.append({"key": feature_name, "label": label})

    async def _guard(db: AsyncSession = Depends(get_db)) -> None:
        enabled = await OrganizationFeaturesService.is_feature_enabled(
            db, feature_name
        )
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{label} feature is not enabled",
            )

    _guard.__name__ = f"require_{feature_name}"
    _guard.__doc__ = f"Require {label} feature to be enabled."
    return _guard


# New feature guards for previously ungated modules
require_acquisition_enabled = _make_feature_guard(
    "acquisition_enabled", "Acquisition"
)
require_indie_platform_enabled = _make_feature_guard(
    "indie_platform_enabled", "Indie platform"
)
require_learning_platform_enabled = _make_feature_guard(
    "learning_platform_enabled", "Learning platform"
)
require_for_teachers_enabled = _make_feature_guard(
    "for_teachers_enabled", "For Teachers portal"
)
require_home_delivery_enabled = _make_feature_guard(
    "home_delivery_enabled", "Home delivery"
)
require_ai_tools_enabled = _make_feature_guard(
    "ai_tools_enabled", "AI tools"
)
require_makerspace_enabled = _make_feature_guard(
    "makerspace_enabled", "Makerspace"
)
require_meeting_rooms_enabled = _make_feature_guard(
    "meeting_rooms_enabled", "Meeting rooms"
)
require_events_enabled = _make_feature_guard(
    "events_enabled", "Events"
)
require_ill_enabled = _make_feature_guard(
    "ill_enabled", "Interlibrary loan"
)
require_genealogy_enabled = _make_feature_guard(
    "genealogy_enabled", "Genealogy"
)
require_free_ebooks_enabled = _make_feature_guard(
    "free_ebooks_enabled", "Free ebooks"
)
require_outreach_enabled = _make_feature_guard(
    "outreach_enabled", "Outreach"
)

# Guards for existing toggles that need enforcement in additional places
require_board_features_enabled = _make_feature_guard(
    "board_features_enabled", "Board features"
)
require_training_modules_enabled = _make_feature_guard(
    "training_modules_enabled", "Training modules"
)
require_patron_portal_enabled = _make_feature_guard(
    "patron_portal_enabled", "Patron portal"
)
require_self_checkout_enabled = _make_feature_guard(
    "self_checkout_enabled", "Self-checkout"
)

# Guards for additional feature toggles (complete coverage)
require_legal_services_enabled = _make_feature_guard(
    "legal_services_enabled", "Legal services"
)
require_strategic_planning_enabled = _make_feature_guard(
    "strategic_planning_enabled", "Strategic planning"
)
require_literacy_programs_enabled = _make_feature_guard(
    "literacy_programs_enabled", "Literacy programs"
)
require_tech_services_enabled = _make_feature_guard(
    "tech_services_enabled", "Technology services"
)
require_emergency_services_enabled = _make_feature_guard(
    "emergency_services_enabled", "Emergency services"
)
require_compliance_enabled = _make_feature_guard(
    "compliance_enabled", "Compliance"
)
require_volunteers_enabled = _make_feature_guard(
    "volunteers_enabled", "Volunteers"
)
require_notifications_enabled = _make_feature_guard(
    "notifications_enabled", "Notifications"
)
require_family_card_enabled = _make_feature_guard(
    "family_card_enabled", "Family card"
)
require_marketing_enabled = _make_feature_guard(
    "marketing_enabled", "Marketing"
)
require_streaming_enabled = _make_feature_guard(
    "streaming_enabled", "Streaming"
)
require_staff_scheduling_enabled = _make_feature_guard(
    "staff_scheduling_enabled", "Staff scheduling"
)
require_beta_features_enabled = _make_feature_guard(
    "beta_features_enabled", "Beta features"
)
require_storytime_enabled = _make_feature_guard(
    "storytime_enabled", "Storytime"
)
require_digital_access_enabled = _make_feature_guard(
    "digital_access_enabled", "Digital access"
)
require_collection_management_enabled = _make_feature_guard(
    "collection_management_enabled", "Collection management"
)
require_patron_engagement_enabled = _make_feature_guard(
    "patron_engagement_enabled", "Patron engagement"
)
require_staff_wellness_enabled = _make_feature_guard(
    "staff_wellness_enabled", "Staff wellness"
)
require_faq_chatbot_enabled = _make_feature_guard(
    "faq_chatbot_enabled", "FAQ chatbot"
)
require_financial_reports_enabled = _make_feature_guard(
    "financial_reports_enabled", "Financial reports"
)
require_book_clubs_enabled = _make_feature_guard(
    "book_clubs_enabled", "Book clubs"
)
require_book_club_history_enabled = _make_feature_guard(
    "book_club_history_enabled", "Book club discussion archive"
)
require_book_club_waitlist_enabled = _make_feature_guard(
    "book_club_waitlist_enabled", "Book club waitlist"
)
require_pickup_authorization_enabled = _make_feature_guard(
    "pickup_authorization_enabled", "Childcare pickup authorization"
)
require_sip2_rfid_enabled = _make_feature_guard(
    "sip2_rfid_enabled", "SIP2/RFID"
)
require_signage_enabled = _make_feature_guard(
    "signage_enabled", "Signage"
)
require_printing_enabled = _make_feature_guard(
    "printing_enabled", "Printing"
)
require_gamification_enabled = _make_feature_guard(
    "gamification_enabled", "Gamification"
)
require_reading_programs_enabled = _make_feature_guard(
    "reading_programs_enabled", "Reading programs"
)
require_community_features_enabled = _make_feature_guard(
    "community_features_enabled", "Community features"
)
require_email_notifications_enabled = _make_feature_guard(
    "email_notifications_enabled", "Email notifications"
)
require_banned_books_tracking_enabled = _make_feature_guard(
    "banned_books_tracking_enabled", "Banned books tracking"
)
require_ama_enabled = _make_feature_guard(
    "ama_enabled", "Author AMA"
)
require_reading_shelf_enabled = _make_feature_guard(
    "reading_shelf_enabled", "Reading shelf"
)
require_reading_goals_enabled = _make_feature_guard(
    "reading_goals_enabled", "Reading goals"
)
require_shelf_data_export_enabled = _make_feature_guard(
    "shelf_data_export_enabled", "Shelf data export"
)
require_processing_queue_enabled = _make_feature_guard(
    "processing_queue_enabled", "Processing queue"
)
require_serials_enabled = _make_feature_guard(
    "serials_enabled", "Serials management"
)
require_parent_onboarding_enabled = _make_feature_guard(
    "parent_onboarding_enabled", "Parent onboarding"
)

require_community_outcomes_enabled = _make_feature_guard(
    "community_outcomes_enabled", "Community outcomes reporting"
)

require_impact_measurement_enabled = _make_feature_guard(
    "impact_measurement_enabled", "Impact measurement (Phase 1)"
)

require_saved_searches_enabled = _make_feature_guard(
    "saved_searches_enabled", "Saved catalog searches"
)

require_circulation_print_slip_enabled = _make_feature_guard(
    "circulation_print_slip_enabled", "Printable checkout slip"
)

require_migration_enabled = _make_feature_guard(
    "migration_enabled", "Migration"
)

require_reading_programs_booklist_enabled = _make_feature_guard(
    "reading_programs_booklist_enabled", "Reading programs booklist"
)

require_reading_programs_paper_log_enabled = _make_feature_guard(
    "reading_programs_paper_log_enabled", "Reading programs paper log"
)
# Registry-only declaration: this flag gates a frontend-only UI surface
# (the hold-trap card on the staff check-in success path), so no router
# attaches this guard. Declared here so the admin Feature Toggles page
# (registry-driven) renders the switch automatically.
require_circulation_hold_trap_card_enabled = _make_feature_guard(
    "circulation_hold_trap_card_enabled", "Hold-trap card at check-in"
)

# Registry-only declaration: this flag gates a frontend-only UI surface
# (the patron-facing customer display at /staff/circulation/display, plus
# the desk header link). No router attaches this guard.
require_customer_display_enabled = _make_feature_guard(
    "customer_display_enabled", "Customer-facing patron display"
)

# Learning-path cohorts V1: opt-in pair-up + shared discussion wall.
# Default OFF: opt-in per library while the feature bakes in.
require_cohort_enabled = _make_feature_guard(
    "cohort_enabled", "Learning path cohorts"
)

# Aggregate trending rails on /discover. Default ON; flag exists only as a
# system-level kill-switch (e.g. if a patron-privacy concern surfaces).
require_aggregate_trending_enabled = _make_feature_guard(
    "aggregate_trending_enabled", "Discover trending rails"
)
