# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal services package for legal resource center operations.

This package is organized into domain-specific modules:
- document_service: Forms, packets, guides
- compliance_service: Topics, courts, providers, eligibility checks
- contract_service: Clinics, registrations, deadlines, form sessions
- policy_service: Wizard, know your rights, collections, feedback
- _utils: Shared logging and analytics functions
"""

# Import from document services
from .document_service import (
    # Form services
    get_form_by_id,
    list_forms,
    search_forms,
    create_form,
    update_form,
    increment_form_views,
    increment_form_downloads,
    # Packet services
    get_packet_by_id,
    get_packet_by_slug,
    list_packets,
    create_packet,
    update_packet,
    add_form_to_packet,
    remove_form_from_packet,
    # Guide services
    get_guide_by_id,
    get_guide_by_slug,
    list_guides,
    create_guide,
    update_guide,
    publish_guide,
    record_guide_helpful,
)

# Import from compliance services
from .compliance_service import (
    # Topic services
    get_topic_by_id,
    get_topic_by_slug,
    list_topics,
    get_topic_tree,
    create_topic,
    update_topic,
    increment_topic_views,
    # Court services
    get_court_by_id,
    list_courts,
    create_court,
    update_court,
    # Provider services
    get_provider_by_id,
    list_providers,
    create_provider,
    update_provider,
    # Glossary services
    get_glossary_term,
    list_glossary_terms,
    create_glossary_term,
    # Eligibility services
    check_fee_waiver_eligibility,
    check_expungement_eligibility,
    # Staff guidelines
    list_staff_guidelines,
    get_staff_guideline,
    # Link checking
    check_form_links,
    get_broken_links,
)

# Import from contract services
from .contract_service import (
    # Clinic services
    get_clinic_by_id,
    list_clinics,
    list_upcoming_clinics,
    create_clinic,
    update_clinic,
    register_for_clinic,
    cancel_clinic_registration,
    # Deadline services
    get_deadline_rule,
    list_deadline_rules,
    calculate_deadline,
    # Form session services
    start_form_session,
    complete_form_session,
)

# Import from policy services
from .policy_service import (
    # Wizard services
    start_wizard_session,
    get_wizard_session,
    get_wizard_question,
    get_first_wizard_question,
    submit_wizard_answer,
    complete_wizard,
    refer_to_help,
    # Know your rights services
    get_know_your_rights_guide,
    list_know_your_rights_guides,
    # Emergency resources
    list_emergency_resources,
    # Content feedback
    submit_feedback,
    list_feedback,
    # Collections
    list_collections,
    get_collection_by_id,
    get_collection_by_slug,
    create_collection,
    update_collection,
    increment_collection_views,
    record_collection_click,
    record_collection_helpful,
)

# Import shared utilities and logging functions
from ._utils import (
    log_content_change,
    log_search,
    get_resource_statistics,
    get_top_searches,
    get_zero_result_searches,
)

__all__ = [
    # Document services
    "get_form_by_id",
    "list_forms",
    "search_forms",
    "create_form",
    "update_form",
    "increment_form_views",
    "increment_form_downloads",
    "get_packet_by_id",
    "get_packet_by_slug",
    "list_packets",
    "create_packet",
    "update_packet",
    "add_form_to_packet",
    "remove_form_from_packet",
    "get_guide_by_id",
    "get_guide_by_slug",
    "list_guides",
    "create_guide",
    "update_guide",
    "publish_guide",
    "record_guide_helpful",
    # Compliance services
    "get_topic_by_id",
    "get_topic_by_slug",
    "list_topics",
    "get_topic_tree",
    "create_topic",
    "update_topic",
    "increment_topic_views",
    "get_court_by_id",
    "list_courts",
    "create_court",
    "update_court",
    "get_provider_by_id",
    "list_providers",
    "create_provider",
    "update_provider",
    "get_glossary_term",
    "list_glossary_terms",
    "create_glossary_term",
    "check_fee_waiver_eligibility",
    "check_expungement_eligibility",
    "list_staff_guidelines",
    "get_staff_guideline",
    "check_form_links",
    "get_broken_links",
    # Contract services
    "get_clinic_by_id",
    "list_clinics",
    "list_upcoming_clinics",
    "create_clinic",
    "update_clinic",
    "register_for_clinic",
    "cancel_clinic_registration",
    "get_deadline_rule",
    "list_deadline_rules",
    "calculate_deadline",
    "start_form_session",
    "complete_form_session",
    # Policy services
    "start_wizard_session",
    "get_wizard_session",
    "get_wizard_question",
    "get_first_wizard_question",
    "submit_wizard_answer",
    "complete_wizard",
    "refer_to_help",
    "get_know_your_rights_guide",
    "list_know_your_rights_guides",
    "list_emergency_resources",
    "submit_feedback",
    "list_feedback",
    "list_collections",
    "get_collection_by_id",
    "get_collection_by_slug",
    "create_collection",
    "update_collection",
    "increment_collection_views",
    "record_collection_click",
    "record_collection_helpful",
    # Utilities
    "log_content_change",
    "log_search",
    "get_resource_statistics",
    "get_top_searches",
    "get_zero_result_searches",
]
