# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Makerspace services package.

Re-exports all service classes for backwards compatibility.
Import from this package directly:

    from app.services.makerspace import MakerspaceResourceService

Or import from the specific module:

    from app.services.makerspace.resource_service import MakerspaceResourceService
"""

from .base_service import BaseMakerspaceService
from .resource_service import MakerspaceResourceService
from .certification_service import CertificationService
from .reservation_service import ReservationService
from .job_queue_service import JobQueueService
from .consumable_service import ConsumableService
from .safety_incident_service import SafetyIncidentService
from .maintenance_service import MaintenanceService
from .payment_service import MakerspacePaymentService
from .reports_service import MakerspaceReportsService

__all__ = [
    "BaseMakerspaceService",
    "MakerspaceResourceService",
    "CertificationService",
    "ReservationService",
    "JobQueueService",
    "ConsumableService",
    "SafetyIncidentService",
    "MaintenanceService",
    "MakerspacePaymentService",
    "MakerspaceReportsService",
]
