# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum


# ============================================================================
# Enums
# ============================================================================

class FormDifficulty(StrEnum):
    easy = "easy"
    moderate = "moderate"
    complex = "complex"
    requires_attorney = "requires_attorney"

class FormStatus(StrEnum):
    active = "active"
    superseded = "superseded"
    archived = "archived"
    draft = "draft"

class GuideReadingLevel(StrEnum):
    elementary = "elementary"  # 5th grade
    middle_school = "middle_school"  # 8th grade
    high_school = "high_school"  # 12th grade
    college = "college"

class ProviderType(StrEnum):
    legal_aid = "legal_aid"
    pro_bono = "pro_bono"
    law_school_clinic = "law_school_clinic"
    bar_association = "bar_association"
    court_self_help = "court_self_help"
    nonprofit = "nonprofit"
    sliding_scale = "sliding_scale"
    hotline = "hotline"
    online_service = "online_service"

class ClinicStatus(StrEnum):
    scheduled = "scheduled"
    registration_open = "registration_open"
    registration_closed = "registration_closed"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class RegistrationStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    waitlisted = "waitlisted"
    cancelled = "cancelled"
    no_show = "no_show"
    attended = "attended"

class CourtType(StrEnum):
    superior = "superior"
    district = "district"
    municipal = "municipal"
    small_claims = "small_claims"
    family = "family"
    juvenile = "juvenile"
    probate = "probate"
    traffic = "traffic"
    federal_district = "federal_district"
    federal_bankruptcy = "federal_bankruptcy"
    appeals = "appeals"

class FormCompletionStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"

class WizardSessionStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    referred_to_help = "referred_to_help"

class LegalResourceType(StrEnum):
    guide = "guide"
    form = "form"
    packet = "packet"
    video = "video"
    external_link = "external_link"
    book = "book"
    glossary = "glossary"

class EmergencyResourceType(StrEnum):
    hotline = "hotline"
    shelter = "shelter"
    crisis_center = "crisis_center"
    emergency_filing = "emergency_filing"
    police = "police"

class LegalFeedbackType(StrEnum):
    helpful = "helpful"
    not_helpful = "not_helpful"
    outdated = "outdated"
    broken_link = "broken_link"
    suggestion = "suggestion"
    content_request = "content_request"

class DeadlineType(StrEnum):
    response = "response"
    appeal = "appeal"
    filing = "filing"
    statute_of_limitations = "statute_of_limitations"
    motion = "motion"
    discovery = "discovery"


# ============================================================================
# Legal Topics Taxonomy
# ============================================================================
