# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Date, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ReportStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    REJECTED = "rejected"  # By state


class AnnualReport(Base):
    __tablename__ = "annual_reports"

    id = Column(Integer, primary_key=True, index=True)

    # =======================
    # Report Identification
    # =======================
    fiscal_year = Column(Integer, nullable=False, index=True)  # e.g., 2025
    state_code = Column(String(2), nullable=False)  # e.g., "CA"
    library_id = Column(String(50), nullable=True)  # State library ID / FSCS ID
    library_name = Column(String(255), nullable=False)
    library_type = Column(String(50), nullable=True)  # public, academic, special

    # =======================
    # Report Status & Tracking
    # =======================
    status = Column(
        String(50),
        nullable=False,
        default=ReportStatus.DRAFT,
        index=True,
    )

    # Validation
    is_validated = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONB, nullable=True)  # List of validation errors
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Submission tracking
    submitted_to_state_at = Column(DateTime(timezone=True), nullable=True)
    state_submission_reference = Column(String(100), nullable=True)
    submission_status = Column(String(50), nullable=True)  # accepted, rejected, pending
    submission_feedback = Column(Text, nullable=True)

    # =======================
    # CIRCULATION STATISTICS
    # =======================
    total_checkouts = Column(Integer, nullable=True, default=0)
    total_renewals = Column(Integer, nullable=True, default=0)
    total_returns = Column(Integer, nullable=True, default=0)

    # PLS total circulation = checkouts + renewals
    total_circulation = Column(Integer, nullable=True, default=0)
    # PLS electronic vs physical split (electronic = ebook checkouts)
    electronic_circulation = Column(Integer, nullable=True, default=0)
    physical_circulation = Column(Integer, nullable=True, default=0)
    # PLS children's circulation (checkouts of audience=children items)
    childrens_circulation = Column(Integer, nullable=True, default=0)

    # PLS third-party e-platform circulation (OverDrive/Libby, Hoopla, e-audio).
    # Staff-entered; folded into electronic_circulation and total_circulation.
    third_party_electronic_circulation = Column(Integer, nullable=True)
    # Per-platform breakdown, e.g. {"overdrive": 1200, "hoopla": 300}
    electronic_circulation_by_platform = Column(JSONB, nullable=True)

    # Checkouts by item type (JSONB)
    checkouts_by_item_type = Column(JSONB, nullable=True)
    # e.g., {"book": 10000, "dvd": 2000, "ebook": 5000, "audiobook": 1500, ...}

    total_holds_placed = Column(Integer, nullable=True, default=0)
    total_holds_filled = Column(Integer, nullable=True, default=0)
    avg_hold_wait_days = Column(Numeric(8, 2), nullable=True)

    # Interlibrary loan
    items_loaned_to_other_libraries = Column(Integer, nullable=True, default=0)
    items_borrowed_from_other_libraries = Column(Integer, nullable=True, default=0)

    # In-house usage (use without checkout)
    in_house_use_count = Column(Integer, nullable=True, default=0)

    # Collection turnover rate
    collection_turnover_rate = Column(Numeric(8, 4), nullable=True)

    # =======================
    # PATRON STATISTICS
    # =======================
    total_registered_patrons = Column(Integer, nullable=True, default=0)
    active_patrons = Column(Integer, nullable=True, default=0)  # Had activity in year
    new_patrons_registered = Column(Integer, nullable=True, default=0)
    patrons_renewed_library_cards = Column(Integer, nullable=True, default=0)

    # Demographics by age group (JSONB)
    patrons_by_age_group = Column(JSONB, nullable=True)
    # e.g., {"child_0_5": 200, "child_6_12": 500, "teen_13_18": 300, "adult": 2000, "senior_65": 500}

    # Resident vs non-resident
    resident_patrons = Column(Integer, nullable=True, default=0)
    non_resident_patrons = Column(Integer, nullable=True, default=0)

    # Patron types (JSONB)
    patrons_by_type = Column(JSONB, nullable=True)
    # e.g., {"regular": 2500, "student": 300, "home-delivery": 50, "bookmobile": 100}

    # =======================
    # COLLECTION STATISTICS
    # =======================
    total_items_owned = Column(Integer, nullable=True, default=0)
    total_titles_owned = Column(Integer, nullable=True, default=0)

    # Items by format (JSONB)
    items_by_format = Column(JSONB, nullable=True)
    # e.g., {"books": 5000, "ebooks": 3000, "audiobooks": 1000, "dvds": 500, ...}

    # Collection growth
    items_added_during_year = Column(Integer, nullable=True, default=0)
    items_withdrawn_during_year = Column(Integer, nullable=True, default=0)
    items_withdrawn_by_reason = Column(JSONB, nullable=True)
    # e.g., {"weeded": 200, "lost": 30, "damaged": 20}

    # E-resources
    electronic_titles = Column(Integer, nullable=True, default=0)
    electronic_databases = Column(Integer, nullable=True, default=0)
    electronic_resources_cost = Column(Numeric(15, 2), nullable=True)

    # Collection value
    total_collection_value = Column(Numeric(15, 2), nullable=True)

    # =======================
    # PROGRAM STATISTICS
    # =======================
    total_programs_offered = Column(Integer, nullable=True, default=0)
    total_program_attendance = Column(Integer, nullable=True, default=0)
    avg_attendance_per_program = Column(Numeric(8, 2), nullable=True)

    # Programs by audience (JSONB)
    programs_by_audience = Column(JSONB, nullable=True)
    # e.g., {"children": 50, "teen": 20, "adult": 30, "senior": 15}

    # Program attendance by audience (JSONB)
    program_attendance_by_audience = Column(JSONB, nullable=True)
    # e.g., {"children": 1500, "teen": 400, "adult": 800, "senior": 300}

    # Specific program types
    childrens_programs_count = Column(Integer, nullable=True, default=0)
    childrens_program_attendance = Column(Integer, nullable=True, default=0)

    young_adult_programs_count = Column(Integer, nullable=True, default=0)
    young_adult_program_attendance = Column(Integer, nullable=True, default=0)

    adult_programs_count = Column(Integer, nullable=True, default=0)
    adult_program_attendance = Column(Integer, nullable=True, default=0)

    # Outreach
    outreach_programs_count = Column(Integer, nullable=True, default=0)
    outreach_program_attendance = Column(Integer, nullable=True, default=0)

    # Virtual programs
    virtual_programs_count = Column(Integer, nullable=True, default=0)
    virtual_program_attendance = Column(Integer, nullable=True, default=0)

    # Reading programs
    reading_program_participants = Column(Integer, nullable=True, default=0)
    reading_program_completions = Column(Integer, nullable=True, default=0)

    # =======================
    # FACILITY & OPERATIONS
    # =======================
    # Hours and accessibility
    total_hours_open_per_week = Column(Integer, nullable=True)
    total_hours_open_per_year = Column(Integer, nullable=True)
    days_open_per_week = Column(Integer, nullable=True, default=6)

    # Building information
    building_square_footage = Column(Integer, nullable=True)
    number_of_locations = Column(Integer, nullable=True, default=1)
    has_bookmobile = Column(Boolean, nullable=True, default=False)
    bookmobile_hours_per_week = Column(Integer, nullable=True)

    # Facility amenities (JSONB)
    facility_amenities = Column(JSONB, nullable=True)
    # e.g., {"meeting_rooms": 3, "computer_stations": 25, "study_tables": 50}

    # =======================
    # VISITOR & USAGE STATISTICS
    # =======================
    total_library_visits = Column(Integer, nullable=True, default=0)
    avg_daily_visits = Column(Numeric(10, 2), nullable=True)
    visits_per_capita = Column(Numeric(10, 4), nullable=True)

    # Reference questions
    reference_questions_answered = Column(Integer, nullable=True, default=0)
    avg_reference_duration_minutes = Column(Numeric(8, 2), nullable=True)

    # =======================
    # TECHNOLOGY & INTERNET
    # =======================
    public_computer_stations = Column(Integer, nullable=True, default=0)
    public_computer_sessions_per_year = Column(Integer, nullable=True, default=0)
    wifi_enabled = Column(Boolean, nullable=True, default=True)
    wifi_sessions = Column(Integer, nullable=True, default=0)

    # Technology equipment (JSONB)
    technology_equipment = Column(JSONB, nullable=True)
    # e.g., {"printers": 5, "3d_printers": 1, "scanners": 3, "copiers": 2}

    # =======================
    # FINANCIAL STATISTICS
    # =======================
    # Operating budget
    total_operating_revenue = Column(Numeric(15, 2), nullable=True, default=0)
    total_operating_expenditure = Column(Numeric(15, 2), nullable=True, default=0)

    # Revenue sources (JSONB)
    revenue_by_source = Column(JSONB, nullable=True)
    # e.g., {"municipal_appropriation": 500000, "fines": 10000, "grants": 50000}

    # Expenditure breakdown (JSONB)
    expenditure_by_category = Column(JSONB, nullable=True)
    # e.g., {"personnel": 350000, "collections": 100000, "operations": 50000}

    # Specific expense categories
    personnel_expenditure = Column(Numeric(15, 2), nullable=True)
    collection_expenditure = Column(Numeric(15, 2), nullable=True)
    technology_expenditure = Column(Numeric(15, 2), nullable=True)
    facility_expenditure = Column(Numeric(15, 2), nullable=True)
    other_expenditure = Column(Numeric(15, 2), nullable=True)

    # Capital (PLS: separate from operating; revenue by source + total outlay)
    capital_revenue = Column(JSONB, nullable=True)
    # e.g., {"local": 100000, "state": 0, "federal": 0, "other": 0}
    capital_outlay = Column(Numeric(15, 2), nullable=True)

    # Per capita calculations
    expenditure_per_capita = Column(Numeric(10, 2), nullable=True)
    revenue_per_capita = Column(Numeric(10, 2), nullable=True)

    # Director finance-entry provenance (first-class, audited; supersedes the
    # data_sources["financial"]="manual" JSONB tag as the PLS completeness gate).
    finance_source = Column(String(20), nullable=True)  # "manual" when director-entered
    finance_entered_at = Column(DateTime(timezone=True), nullable=True)
    finance_entered_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # =======================
    # STAFF STATISTICS
    # =======================
    total_staff_fte = Column(Numeric(8, 2), nullable=True)
    librarian_fte = Column(Numeric(8, 2), nullable=True)
    # MLS-credentialed librarian FTE (PLS) — subset of librarian_fte
    mls_librarian_fte = Column(Numeric(8, 2), nullable=True)
    library_technician_fte = Column(Numeric(8, 2), nullable=True)
    other_staff_fte = Column(Numeric(8, 2), nullable=True)
    volunteer_hours = Column(Integer, nullable=True, default=0)

    # Staff by role (JSONB)
    staff_by_role = Column(JSONB, nullable=True)
    # e.g., {"director": 1, "librarians": 5, "technicians": 8, "circulation": 10}

    # =======================
    # SERVICE POPULATION
    # =======================
    legal_service_area_population = Column(Integer, nullable=True)
    unduplicated_service_population = Column(Integer, nullable=True)

    # =======================
    # YEAR-OVER-YEAR COMPARISON
    # =======================
    prior_year_total_checkouts = Column(Integer, nullable=True)
    prior_year_total_patrons = Column(Integer, nullable=True)
    prior_year_total_visits = Column(Integer, nullable=True)
    prior_year_total_programs = Column(Integer, nullable=True)
    prior_year_total_expenditure = Column(Numeric(15, 2), nullable=True)

    # Growth metrics (calculated)
    checkout_growth_percent = Column(Numeric(8, 2), nullable=True)
    patron_growth_percent = Column(Numeric(8, 2), nullable=True)
    visit_growth_percent = Column(Numeric(8, 2), nullable=True)
    program_growth_percent = Column(Numeric(8, 2), nullable=True)

    # =======================
    # ADDITIONAL METRICS
    # =======================
    # Custom/flexible fields (JSONB)
    additional_metrics = Column(JSONB, nullable=True)
    state_specific_fields = Column(JSONB, nullable=True)

    # Notes and observations
    notes = Column(Text, nullable=True)
    highlights = Column(Text, nullable=True)

    # =======================
    # AUDIT & METADATA
    # =======================
    # Data sources and calculation notes
    data_sources = Column(JSONB, nullable=True)
    calculation_notes = Column(Text, nullable=True)

    # Export formats
    pdf_file_path = Column(String(500), nullable=True)
    excel_file_path = Column(String(500), nullable=True)
    xml_file_path = Column(String(500), nullable=True)

    # Generated by
    generated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Modification tracking
    last_modified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    last_modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # =======================
    # RELATIONSHIPS
    # =======================
    generated_by = relationship("User", foreign_keys=[generated_by_id], backref="generated_annual_reports")
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])
    validated_by = relationship("User", foreign_keys=[validated_by_id])

    __table_args__ = (
        Index("ix_annual_reports_fiscal_year_state", "fiscal_year", "state_code"),
        Index("ix_annual_reports_status", "status"),
    )


class AnnualReportValidationRule(Base):
    __tablename__ = "annual_report_validation_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule identification
    state_code = Column(String(2), nullable=True)  # NULL = applies to all states
    field_name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)  # required, min_value, max_value, regex, logic
    description = Column(Text, nullable=True)

    # Rule definition
    rule_value = Column(String(500), nullable=True)  # The constraint value
    error_message = Column(String(500), nullable=False)

    # Dependencies
    depends_on_field = Column(String(100), nullable=True)
    depends_on_operator = Column(String(20), nullable=True)  # >, <, ==, <=, >=
    depends_on_value = Column(String(200), nullable=True)

    # Configuration
    is_active = Column(Boolean, nullable=False, default=True)


class AnnualReportHistory(Base):
    __tablename__ = "annual_report_history"

    id = Column(Integer, primary_key=True, index=True)

    annual_report_id = Column(
        Integer,
        ForeignKey("annual_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Change details
    field_name = Column(String(100), nullable=False)
    old_value = Column(String(1000), nullable=True)
    new_value = Column(String(1000), nullable=True)
    change_reason = Column(Text, nullable=True)

    # Who made the change
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    __table_args__ = (
        Index("ix_annual_report_history_report_id", "annual_report_id"),
        Index("ix_annual_report_history_changed_at", "changed_at"),
    )
