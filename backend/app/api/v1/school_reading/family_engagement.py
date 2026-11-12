# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""School-reading family engagement route composition.

Child routers are included in historical order. Keep literal paths before
parameterized paths within the visit and reading-list route groups.
"""

from fastapi import APIRouter

from .family_engagement_challenges import (
    challenges_router,
    create_family_reading_challenge,
    get_family_challenge,
    _serialize_challenge_for_school,
    list_family_challenge_registrations_for_school,
    list_family_challenges_for_school,
    register_family_in_challenge,
    create_take_home_bundle,
    list_take_home_bundles,
    list_bundle_distributions,
    DistributeBundleRequest,
    distribute_take_home_bundle,
)
from .family_engagement_professional import (
    professional_router,
    create_training_module,
    list_training_modules,
    start_training_module,
    list_training_completions,
    list_training_certificates,
    CompleteTrainingModuleRequest,
    complete_training_module,
    create_ambassador_certification,
    list_ambassador_certifications,
    download_ambassador_certificate,
    update_ambassador_certification,
    revoke_ambassador_certification,
    renew_ambassador_certification,
    list_consultation_slots,
    create_consultation_slot,
    register_for_consultation,
    list_active_schools,
    get_user_consultation_registrations,
    unregister_from_consultation,
)
from .family_engagement_visits import (
    visits_router,
    _serialize_visit,
    create_library_visit_request,
    list_library_visit_requests,
    cancel_library_visit_request,
    approve_library_visit_request,
    reject_library_visit_request,
    list_scheduled_library_visits,
)
from .family_engagement_reading_lists import (
    reading_lists_router,
    _serialize_reading_list_request,
    create_reading_list_request,
    list_reading_list_requests,
    approve_reading_list_request,
    fulfill_reading_list_request,
    reject_reading_list_request,
    cancel_reading_list_request,
)

router = APIRouter()
router.include_router(challenges_router)
router.include_router(professional_router)
router.include_router(visits_router)
router.include_router(reading_lists_router)
