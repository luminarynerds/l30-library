# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Legal models package exports for backward compatibility."""

from .enums import (
    FormDifficulty,
    FormStatus,
    GuideReadingLevel,
    ProviderType,
    ClinicStatus,
    RegistrationStatus,
    CourtType,
    FormCompletionStatus,
    WizardSessionStatus,
    LegalResourceType,
    EmergencyResourceType,
    LegalFeedbackType,
    DeadlineType
)
from .taxonomy import (
    LegalTopic,
    LegalGuide,
    DeadlineRule,
    DeadlineCalculation,
    KnowYourRightsGuide,
    LegalContentFeedback,
    LegalContentAuditLog,
    LegalResourceStatistics,
    LegalSearchLog,
    LegalStaffGuideline,
    LegalCatalogLink,
    LegalCollection
)
from .forms import (
    LegalForm,
    LegalFormPacket,
    LegalFormPacketItem,
    FormCompletionSession,
    FormFinderWizardSession,
    FormFinderQuestion,
    FormFinderRule,
    FeeWaiverEligibility,
    LegalFormLinkCheck
)
from .providers import (
    LegalServiceProvider,
    LegalClinic,
    LegalClinicRegistration,
    CourtLocation
)
from .resources import (
    LegalGlossaryTerm,
    EmergencyResource,
    ExpungementEligibility,
    ComplianceRequirement
)
from .eligibility import LegalEligibilityThreshold  # noqa: F401

__all__ = [
    'FormDifficulty' ,
    'FormStatus' ,
    'GuideReadingLevel' ,
    'ProviderType' ,
    'ClinicStatus' ,
    'RegistrationStatus' ,
    'CourtType' ,
    'FormCompletionStatus' ,
    'WizardSessionStatus' ,
    'LegalResourceType' ,
    'EmergencyResourceType' ,
    'LegalFeedbackType' ,
    'DeadlineType' ,
    'LegalTopic' ,
    'LegalGuide' ,
    'DeadlineRule' ,
    'DeadlineCalculation' ,
    'KnowYourRightsGuide' ,
    'LegalContentFeedback' ,
    'LegalContentAuditLog' ,
    'LegalResourceStatistics' ,
    'LegalSearchLog' ,
    'LegalStaffGuideline' ,
    'LegalCatalogLink' ,
    'LegalCollection' ,
    'LegalForm' ,
    'LegalFormPacket' ,
    'LegalFormPacketItem' ,
    'FormCompletionSession' ,
    'FormFinderWizardSession' ,
    'FormFinderQuestion' ,
    'FormFinderRule' ,
    'FeeWaiverEligibility' ,
    'LegalFormLinkCheck' ,
    'LegalServiceProvider' ,
    'LegalClinic' ,
    'LegalClinicRegistration' ,
    'CourtLocation' ,
    'LegalGlossaryTerm' ,
    'EmergencyResource' ,
    'ExpungementEligibility' ,
    'ComplianceRequirement' ,
    'LegalEligibilityThreshold'
]
