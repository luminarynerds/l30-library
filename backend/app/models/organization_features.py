# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.models.mixins import TimestampMixin

from ..core.database import Base


class OrganizationFeatures(Base, TimestampMixin):
    __tablename__ = "organization_features"

    id = Column(Integer, primary_key=True, index=True)

    # Boolean Feature Toggles
    gamification_enabled = Column(Boolean, nullable=False, default=True)
    reading_programs_enabled = Column(Boolean, nullable=False, default=True)
    board_features_enabled = Column(Boolean, nullable=False, default=True)
    training_modules_enabled = Column(Boolean, nullable=False, default=True)
    community_features_enabled = Column(Boolean, nullable=False, default=True)
    email_notifications_enabled = Column(Boolean, nullable=False, default=True)
    banned_books_tracking_enabled = Column(Boolean, nullable=False, default=True)
    patron_portal_enabled = Column(Boolean, nullable=False, default=True)
    self_checkout_enabled = Column(Boolean, nullable=False, default=True)

    # New feature toggles for previously ungated modules
    acquisition_enabled = Column(Boolean, nullable=False, default=True)
    indie_platform_enabled = Column(Boolean, nullable=False, default=True)
    learning_platform_enabled = Column(Boolean, nullable=False, default=True)
    for_teachers_enabled = Column(Boolean, nullable=False, default=True)
    home_delivery_enabled = Column(Boolean, nullable=False, default=True)
    ai_tools_enabled = Column(Boolean, nullable=False, default=True)
    makerspace_enabled = Column(Boolean, nullable=False, default=True)
    meeting_rooms_enabled = Column(Boolean, nullable=False, default=True)
    events_enabled = Column(Boolean, nullable=False, default=True)
    ill_enabled = Column(Boolean, nullable=False, default=True)
    genealogy_enabled = Column(Boolean, nullable=False, default=True)
    free_ebooks_enabled = Column(Boolean, nullable=False, default=True)
    outreach_enabled = Column(Boolean, nullable=False, default=True)
    migration_enabled = Column(Boolean, nullable=False, default=True)

    # Additional feature toggles for complete coverage
    legal_services_enabled = Column(Boolean, nullable=False, default=True)
    strategic_planning_enabled = Column(Boolean, nullable=False, default=True)
    literacy_programs_enabled = Column(Boolean, nullable=False, default=True)
    tech_services_enabled = Column(Boolean, nullable=False, default=True)
    emergency_services_enabled = Column(Boolean, nullable=False, default=True)
    compliance_enabled = Column(Boolean, nullable=False, default=True)
    volunteers_enabled = Column(Boolean, nullable=False, default=True)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    family_card_enabled = Column(Boolean, nullable=False, default=True)
    marketing_enabled = Column(Boolean, nullable=False, default=True)
    streaming_enabled = Column(Boolean, nullable=False, default=True)
    staff_scheduling_enabled = Column(Boolean, nullable=False, default=True)
    beta_features_enabled = Column(Boolean, nullable=False, default=False)
    storytime_enabled = Column(Boolean, nullable=False, default=True)
    digital_access_enabled = Column(Boolean, nullable=False, default=True)
    collection_management_enabled = Column(Boolean, nullable=False, default=True)
    patron_engagement_enabled = Column(Boolean, nullable=False, default=True)
    staff_wellness_enabled = Column(Boolean, nullable=False, default=True)
    faq_chatbot_enabled = Column(Boolean, nullable=False, default=True)
    financial_reports_enabled = Column(Boolean, nullable=False, default=True)
    book_clubs_enabled = Column(Boolean, nullable=False, default=True)
    sip2_rfid_enabled = Column(Boolean, nullable=False, default=True)
    signage_enabled = Column(Boolean, nullable=False, default=True)
    printing_enabled = Column(Boolean, nullable=False, default=True)
    ama_enabled = Column(Boolean, nullable=False, default=False)
    processing_queue_enabled = Column(Boolean, nullable=False, default=True)
    community_outcomes_enabled = Column(Boolean, nullable=False, default=True)
    # Phase 1 governance scaffolding — default off, opt-in per library.
    impact_measurement_enabled = Column(Boolean, nullable=False, default=False)

    # Parent onboarding
    parent_onboarding_enabled = Column(Boolean, nullable=False, default=True)

    # Lone-worker safety check-in for staff home visits. Default OFF until
    # the library reviews the supervisor notification path + cron schedule.
    home_visit_safety_enabled = Column(Boolean, nullable=False, default=False)

    # Map-aware "Today's route" day-plan view for staff home visits.
    # Default OFF until the maintainer validates a real day plan in production and
    # confirms the Nominatim public-instance volume is within policy.
    home_visit_day_plan_enabled = Column(Boolean, nullable=False, default=False)

    # Reading shelf expansion toggles
    reading_shelf_enabled = Column(Boolean, nullable=False, default=True)
    reading_goals_enabled = Column(Boolean, nullable=False, default=True)
    shelf_data_export_enabled = Column(Boolean, nullable=False, default=True)
    front_desk_enabled = Column(Boolean, nullable=False, default=True)
    serials_enabled = Column(Boolean, nullable=False, default=True)

    # Patron saved catalog searches + new-arrival alerts.
    # Default on — notifier delivery verified, rolling out org-wide.
    saved_searches_enabled = Column(Boolean, nullable=False, default=True)
    reading_programs_booklist_enabled = Column(Boolean, nullable=False, default=False)
    reading_programs_paper_log_enabled = Column(Boolean, nullable=False, default=False)

    # Printable + emailable post-checkout slip toolbar at the staff
    # circulation desk. Default ON: fundamental library workflow.
    circulation_print_slip_enabled = Column(Boolean, nullable=False, default=True)

    # Surface a hold-trap card on the staff check-in success path when the
    # returned item is the next available copy for an active hold.
    circulation_hold_trap_card_enabled = Column(Boolean, nullable=False, default=True)

    # Patron-facing customer display (second monitor) at the staff
    # circulation desk. Default OFF: most desks lack a second monitor —
    # opt-in per library.
    customer_display_enabled = Column(Boolean, nullable=False, default=False)

    # Book club discussion archive + Postgres FTS search across past
    # discussions. Default OFF: opt-in per library while the feature
    # bakes in. Toggled via the staff feature-flags admin page.
    book_club_history_enabled = Column(Boolean, nullable=False, default=False)

    # FIFO waitlist + capacity signals on book clubs. Default OFF:
    # opt-in per library while the feature bakes in. Toggled via the
    # staff feature-flags admin page.
    book_club_waitlist_enabled = Column(Boolean, nullable=False, default=False)

    # Childcare authorized-pickup enforcement. Parents list adults they
    # authorize to pick up the child; staff checkout endpoint validates
    # the named pickup person against that list. Default OFF -- existing
    # childcare registrations were created without a pickup list and
    # silently flipping enforcement on would block checkouts at the desk.
    pickup_authorization_enabled = Column(Boolean, nullable=False, default=False)

    # Learning-path cohorts V1: opt-in pair-up + shared discussion wall.
    # Default OFF: opt-in per library while the feature bakes in. Toggled
    # via the staff feature-flags admin page.
    cohort_enabled = Column(Boolean, nullable=False, default=False)

    # Aggregate trending rails on /discover ("what neighbors are reading").
    # Aggregate-only, k-anon floor, per-patron opt-out. Default ON: the
    # /discover subhead promises this; flag exists as a system-level kill
    # switch only.
    aggregate_trending_enabled = Column(Boolean, nullable=False, default=True)

    # Array Configurations (stored as JSONB arrays)
    enabled_focus_modes = Column(JSONB, nullable=False, default=list)
    enabled_themes = Column(JSONB, nullable=False, default=list)
    enabled_fonts = Column(JSONB, nullable=False, default=list)

    # Numeric Configurations
    default_daily_goal_minutes = Column(Integer, nullable=False, default=30)
    max_holds_per_patron = Column(Integer, nullable=False, default=10)
    max_checkouts_per_patron = Column(Integer, nullable=False, default=5)

    # Extensible configuration JSON
    configuration = Column(JSONB, nullable=True, default=dict)

    # Per-age-group circulation limits (NULL = use role-based limits)
    age_group_limits = Column(JSONB, nullable=True, default=None)

    # Audit fields, server_default=func.now()), onupdate=func.now(), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
