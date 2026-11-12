# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Scheduler services module.

This module provides a unified interface for all scheduled background jobs.
All job modules are organized by domain for easy maintenance and discovery.

Job Modules:
- billing_jobs: Consortium billing operations
- circulation_jobs: Circulation management (fines, holds, overdues)
- notification_jobs: Patron notification delivery
- room_jobs: Room reservation management
- patron_lifecycle_jobs: Patron lifecycle transitions and status updates
- outreach_jobs: Outreach program operations
- maintenance_jobs: System maintenance and cleanup
- retention_jobs: Data retention and archival
- misc_jobs: Miscellaneous scheduled jobs

Main Interface:
- init_scheduler(): Initialize and start the scheduler
- shutdown_scheduler(): Gracefully shutdown the scheduler
- get_scheduler(): Get the current scheduler instance for testing/monitoring
"""

from .main import (
    init_scheduler,
    shutdown_scheduler,
    get_scheduler,
    scheduler,
    unified_scheduling_service,
)

# Export all job functions for backward compatibility and discoverability
from .billing_jobs import (
    generate_monthly_consortium_billing,
    generate_quarterly_consortium_billing,
    mark_overdue_consortium_invoices,
    send_consortium_payment_reminders,
)

from .circulation_jobs import (
    calculate_daily_overdue_fines,
    expire_old_holds,
    send_overdue_notifications,
)

from .notification_jobs import (
    send_hold_expiration_reminders,
    send_smart_automated_communications,
)

from .room_jobs import (
    process_room_no_shows,
    complete_room_reservations,
    send_room_reservation_reminders,
)

from .patron_lifecycle_jobs import (
    process_expired_suspensions,
    process_child_to_adult_transitions,
    recompute_under_18_flags,
    send_home_delivery_reminders,
    send_home_delivery_feedback_requests,
    process_expired_institutional_cards_job,
)

from .outreach_jobs import (
    process_outreach_overdue_checkouts,
    send_outreach_visit_reminders,
    send_outreach_deposit_warnings,
    aggregate_outreach_statistics,
)

from .maintenance_jobs import (
    process_failed_job_retries,
    cleanup_job_logs,
    refresh_caches,
)

from .retention_jobs import (
    run_data_retention_jobs,
)

from .misc_jobs import (
    renew_annual_closures,
    send_daily_operational_alerts,
    process_eod_auto_logouts,
    check_certificate_expiration,
    update_database_subscription_statuses,
)

from .release_ingestion_jobs import process_release_ingestion

from .embedding_jobs import backfill_catalog_embeddings

from .indie_lending_jobs import (
    expire_overdue_indie_borrows,
    send_indie_due_soon_notifications,
)

from .weeding_jobs import scheduled_weeding_analysis

__all__ = [
    # Main interface
    "init_scheduler",
    "shutdown_scheduler",
    "get_scheduler",
    "scheduler",
    "unified_scheduling_service",
    # Billing jobs
    "generate_monthly_consortium_billing",
    "generate_quarterly_consortium_billing",
    "mark_overdue_consortium_invoices",
    "send_consortium_payment_reminders",
    # Circulation jobs
    "calculate_daily_overdue_fines",
    "expire_old_holds",
    "send_overdue_notifications",
    # Notification jobs
    "send_hold_expiration_reminders",
    "send_smart_automated_communications",
    # Room jobs
    "process_room_no_shows",
    "complete_room_reservations",
    "send_room_reservation_reminders",
    # Patron lifecycle jobs
    "process_expired_suspensions",
    "process_child_to_adult_transitions",
    "recompute_under_18_flags",
    "send_home_delivery_reminders",
    "send_home_delivery_feedback_requests",
    "process_expired_institutional_cards_job",
    # Outreach jobs
    "process_outreach_overdue_checkouts",
    "send_outreach_visit_reminders",
    "send_outreach_deposit_warnings",
    "aggregate_outreach_statistics",
    # Maintenance jobs
    "process_failed_job_retries",
    "cleanup_job_logs",
    "refresh_caches",
    # Retention jobs
    "run_data_retention_jobs",
    # Misc jobs
    "renew_annual_closures",
    "send_daily_operational_alerts",
    "process_eod_auto_logouts",
    "check_certificate_expiration",
    "update_database_subscription_statuses",
    # Release ingestion jobs
    "process_release_ingestion",
    # Embedding jobs
    "backfill_catalog_embeddings",
    # Indie lending jobs
    "expire_overdue_indie_borrows",
    "send_indie_due_soon_notifications",
    # Weeding jobs
    "scheduled_weeding_analysis",
]
