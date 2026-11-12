# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema


class AgeGroupLimitConfig(BaseModel):
    max_checkouts: int = Field(default=10, ge=1, le=50)
    max_holds: int = Field(default=10, ge=1, le=50)
    checkout_duration_days: int = Field(default=28, ge=1, le=365)


class AgeGroupLimits(BaseModel):
    juvenile: AgeGroupLimitConfig = Field(
        default_factory=lambda: AgeGroupLimitConfig(max_checkouts=5, max_holds=3, checkout_duration_days=14)
    )
    teen: AgeGroupLimitConfig = Field(
        default_factory=lambda: AgeGroupLimitConfig(max_checkouts=7, max_holds=5, checkout_duration_days=21)
    )
    adult: AgeGroupLimitConfig = Field(
        default_factory=lambda: AgeGroupLimitConfig(max_checkouts=10, max_holds=10, checkout_duration_days=28)
    )
    senior: AgeGroupLimitConfig = Field(
        default_factory=lambda: AgeGroupLimitConfig(max_checkouts=10, max_holds=10, checkout_duration_days=28)
    )


class OrganizationFeaturesBase(BaseModel):

    # Boolean toggles
    gamification_enabled: bool = True
    reading_programs_enabled: bool = True
    board_features_enabled: bool = True
    training_modules_enabled: bool = True
    community_features_enabled: bool = True
    email_notifications_enabled: bool = True
    banned_books_tracking_enabled: bool = True
    patron_portal_enabled: bool = True
    self_checkout_enabled: bool = True

    # New feature toggles for previously ungated modules
    acquisition_enabled: bool = True
    indie_platform_enabled: bool = True
    learning_platform_enabled: bool = True
    for_teachers_enabled: bool = True
    home_delivery_enabled: bool = True
    ai_tools_enabled: bool = True
    makerspace_enabled: bool = True
    meeting_rooms_enabled: bool = True
    events_enabled: bool = True
    ill_enabled: bool = True
    genealogy_enabled: bool = True
    free_ebooks_enabled: bool = True
    outreach_enabled: bool = True

    # Additional feature toggles for complete coverage
    legal_services_enabled: bool = True
    strategic_planning_enabled: bool = True
    literacy_programs_enabled: bool = True
    tech_services_enabled: bool = True
    emergency_services_enabled: bool = True
    compliance_enabled: bool = True
    volunteers_enabled: bool = True
    notifications_enabled: bool = True
    family_card_enabled: bool = True
    marketing_enabled: bool = True
    streaming_enabled: bool = True
    staff_scheduling_enabled: bool = True
    beta_features_enabled: bool = True
    storytime_enabled: bool = True
    digital_access_enabled: bool = True
    collection_management_enabled: bool = True
    patron_engagement_enabled: bool = True
    staff_wellness_enabled: bool = True
    faq_chatbot_enabled: bool = True
    financial_reports_enabled: bool = True
    book_clubs_enabled: bool = True
    sip2_rfid_enabled: bool = True
    signage_enabled: bool = True
    printing_enabled: bool = True
    ama_enabled: bool = False
    community_outcomes_enabled: bool = True
    front_desk_enabled: bool = True
    serials_enabled: bool = True
    migration_enabled: bool = True
    parent_onboarding_enabled: bool = True
    home_visit_safety_enabled: bool = False
    home_visit_day_plan_enabled: bool = False
    processing_queue_enabled: bool = True
    reading_goals_enabled: bool = True
    reading_shelf_enabled: bool = True
    shelf_data_export_enabled: bool = True
    saved_searches_enabled: bool = False
    reading_programs_booklist_enabled: bool = False
    reading_programs_paper_log_enabled: bool = False
    circulation_print_slip_enabled: bool = True
    circulation_hold_trap_card_enabled: bool = True
    customer_display_enabled: bool = False
    book_club_history_enabled: bool = False
    book_club_waitlist_enabled: bool = False
    pickup_authorization_enabled: bool = False
    cohort_enabled: bool = False
    aggregate_trending_enabled: bool = True
    impact_measurement_enabled: bool = False

    # Array configurations
    enabled_focus_modes: List[str] = Field(default_factory=list)
    enabled_themes: List[str] = Field(default_factory=list)
    enabled_fonts: List[str] = Field(default_factory=list)

    # Numeric configurations
    default_daily_goal_minutes: int = Field(default=30, ge=0, le=480)
    max_holds_per_patron: int = Field(default=10, ge=1, le=50)
    max_checkouts_per_patron: int = Field(default=5, ge=1, le=20)

    # Extensible configuration
    configuration: Optional[Dict[str, Any]] = None

    # Per-age-group circulation limits
    age_group_limits: Optional[AgeGroupLimits] = None

    @field_validator(
        "book_club_history_enabled",
        "book_club_waitlist_enabled",
        "impact_measurement_enabled",
        mode="before",
    )
    @classmethod
    def _none_to_false(cls, v):
        # Legacy rows may carry NULL for bool flags added in later migrations
        # without a NOT NULL backfill. Coerce to False on read paths.
        return False if v is None else v


class OrganizationFeaturesResponse(OrganizationFeaturesBase):

    id: int
    created_at: datetime | None = None
    updated_at: Optional[datetime]
    updated_by_id: Optional[int]

    class Config:
        from_attributes = True


class OrganizationFeaturesUpdate(StrictInputSchema):

    # Boolean toggles
    gamification_enabled: Optional[bool] = None
    reading_programs_enabled: Optional[bool] = None
    board_features_enabled: Optional[bool] = None
    training_modules_enabled: Optional[bool] = None
    community_features_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    banned_books_tracking_enabled: Optional[bool] = None
    patron_portal_enabled: Optional[bool] = None
    self_checkout_enabled: Optional[bool] = None

    # New feature toggles for previously ungated modules
    acquisition_enabled: Optional[bool] = None
    indie_platform_enabled: Optional[bool] = None
    learning_platform_enabled: Optional[bool] = None
    for_teachers_enabled: Optional[bool] = None
    home_delivery_enabled: Optional[bool] = None
    ai_tools_enabled: Optional[bool] = None
    makerspace_enabled: Optional[bool] = None
    meeting_rooms_enabled: Optional[bool] = None
    events_enabled: Optional[bool] = None
    ill_enabled: Optional[bool] = None
    genealogy_enabled: Optional[bool] = None
    free_ebooks_enabled: Optional[bool] = None
    outreach_enabled: Optional[bool] = None

    # Additional feature toggles for complete coverage
    legal_services_enabled: Optional[bool] = None
    strategic_planning_enabled: Optional[bool] = None
    literacy_programs_enabled: Optional[bool] = None
    tech_services_enabled: Optional[bool] = None
    emergency_services_enabled: Optional[bool] = None
    compliance_enabled: Optional[bool] = None
    volunteers_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    family_card_enabled: Optional[bool] = None
    marketing_enabled: Optional[bool] = None
    streaming_enabled: Optional[bool] = None
    staff_scheduling_enabled: Optional[bool] = None
    beta_features_enabled: Optional[bool] = None
    storytime_enabled: Optional[bool] = None
    digital_access_enabled: Optional[bool] = None
    collection_management_enabled: Optional[bool] = None
    patron_engagement_enabled: Optional[bool] = None
    staff_wellness_enabled: Optional[bool] = None
    faq_chatbot_enabled: Optional[bool] = None
    financial_reports_enabled: Optional[bool] = None
    book_clubs_enabled: Optional[bool] = None
    sip2_rfid_enabled: Optional[bool] = None
    signage_enabled: Optional[bool] = None
    printing_enabled: Optional[bool] = None
    ama_enabled: Optional[bool] = None
    community_outcomes_enabled: Optional[bool] = None
    front_desk_enabled: Optional[bool] = None
    serials_enabled: Optional[bool] = None
    migration_enabled: Optional[bool] = None
    parent_onboarding_enabled: Optional[bool] = None
    home_visit_safety_enabled: Optional[bool] = None
    home_visit_day_plan_enabled: Optional[bool] = None
    processing_queue_enabled: Optional[bool] = None
    reading_goals_enabled: Optional[bool] = None
    reading_shelf_enabled: Optional[bool] = None
    shelf_data_export_enabled: Optional[bool] = None
    saved_searches_enabled: Optional[bool] = None
    reading_programs_booklist_enabled: Optional[bool] = None
    reading_programs_paper_log_enabled: Optional[bool] = None
    circulation_print_slip_enabled: Optional[bool] = None
    circulation_hold_trap_card_enabled: Optional[bool] = None
    customer_display_enabled: Optional[bool] = None
    book_club_history_enabled: Optional[bool] = None
    book_club_waitlist_enabled: Optional[bool] = None
    pickup_authorization_enabled: Optional[bool] = None
    cohort_enabled: Optional[bool] = None
    aggregate_trending_enabled: Optional[bool] = None
    impact_measurement_enabled: Optional[bool] = None

    # Array configurations
    enabled_focus_modes: Optional[List[str]] = None
    enabled_themes: Optional[List[str]] = None
    enabled_fonts: Optional[List[str]] = None

    # Numeric configurations
    default_daily_goal_minutes: Optional[int] = Field(None, ge=0, le=480)
    max_holds_per_patron: Optional[int] = Field(None, ge=1, le=50)
    max_checkouts_per_patron: Optional[int] = Field(None, ge=1, le=20)

    # Extensible configuration
    configuration: Optional[Dict[str, Any]] = None

    # Per-age-group circulation limits
    age_group_limits: Optional[AgeGroupLimits] = None

    # Audit reason
    reason: Optional[str] = Field(None, description="Reason for the change")
