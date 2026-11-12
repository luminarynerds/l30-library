# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import fcntl
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

from ...core.config import get_settings
from ...core.database import engine
from ...core.logging import get_logger
from ..unified_scheduler import (
    ScheduleConfig,
    ScheduleType,
    SchedulingService,
    get_scheduling_service,
    set_scheduling_service,
)

# Import all job modules
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
    send_event_reminders,
    send_hold_expiration_reminders,
    send_smart_automated_communications,
)
from .room_jobs import (
    process_room_no_shows,
    complete_room_reservations,
    send_room_reservation_reminders,
)
from .computer_jobs import (
    process_computer_no_shows,
    process_computer_auto_logouts,
)
from .patron_lifecycle_jobs import (
    process_expired_suspensions,
    process_child_to_adult_transitions,
    recompute_under_18_flags,
    process_expired_institutional_cards_job,
    send_database_renewal_notifications,
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
from .catalog_velocity_jobs import refresh_catalog_velocity_mv
from .job_heartbeat import check_job_heartbeats
from .notification_retry_job import process_failed_notification_retries
from .notification_queue_job import process_notification_queue
from .retention_jobs import (
    run_data_retention_jobs,
)
from .journey_analytics_jobs import (
    detect_journey_dropoffs,
    aggregate_journey_metrics,
)
from .engagement_jobs import (
    dispatch_longitudinal_surveys,
)
from .misc_jobs import (
    renew_annual_closures,
    send_daily_operational_alerts,
    process_eod_auto_logouts,
    check_certificate_expiration,
    update_database_subscription_statuses,
)
# NOTE: patron_lifecycle_jobs also contains:
# - send_home_delivery_reminders
# - send_home_delivery_feedback_requests
from .patron_lifecycle_jobs import (
    send_home_delivery_reminders,
    send_home_delivery_feedback_requests,
)
from .ban_tracker_jobs import (
    pen_america_sync_job,
    ban_tracker_digest_job,
)
# Payout jobs removed - MetisLib handles payouts
from .release_ingestion_jobs import process_release_ingestion
from .editorial_release_jobs import process_editorial_release_ingestion
from .editorial_rss_jobs import process_editorial_rss_ingestion
from .indie_release_jobs import process_indie_release_ingestion, process_recruitment_digest
from .embedding_jobs import backfill_catalog_embeddings
from .community_metrics_jobs import generate_community_metrics_snapshots
from .indie_lending_jobs import (
    expire_overdue_indie_borrows,
    reconcile_metislib_borrow_sync,
    send_indie_due_soon_notifications,
    send_indie_author_release_digests,
    sync_indie_opds_catalog,
)
from .edi_jobs import poll_edi_inbound_messages, process_edi_retries
from .saved_search_jobs import run_saved_search_notifier
from .digest_jobs import send_notification_digests
from .timesheet_jobs import sweep_dangling_punches
from ..update_checker import run_scheduled_check
from ...tasks.lesson_sweep import sweep_empty_lessons_job
from .parent_onboarding_jobs import (
    send_parent_onboarding_followup_due_tomorrow_reminders,
    send_parent_onboarding_followup_overdue_reminders,
)

settings = get_settings()
logger = get_logger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None
unified_scheduling_service: Optional[SchedulingService] = None
_scheduler_lock_fd = None


def init_scheduler() -> None:
    global scheduler, unified_scheduling_service, _scheduler_lock_fd

    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled via configuration")
        return

    # Acquire exclusive lock — only one worker should run the scheduler
    try:
        _scheduler_lock_fd = open("/tmp/.lsc_scheduler.lock", "w")
        fcntl.flock(_scheduler_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        logger.info("Another worker owns the scheduler lock — skipping scheduler init")
        return

    # Initialize the unified scheduling service
    unified_scheduling_service = SchedulingService()
    set_scheduling_service(unified_scheduling_service)
    logger.info("Initialized unified scheduling service")

    # Configure job stores based on settings
    jobstores = {}
    if settings.scheduler_job_store == "sqlalchemy" and engine is not None:
        try:
            # Use synchronous URL for APScheduler job store
            # APScheduler's SQLAlchemyJobStore doesn't support async
            sync_url = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            ).replace("sqlite+aiosqlite://", "sqlite://")
            jobstores["default"] = SQLAlchemyJobStore(
                url=sync_url,
                tablename="apscheduler_jobs",
            )
            logger.info("Using SQLAlchemy job store for persistent job tracking")
        except Exception as e:  # noqa: BLE001  # job store init - fall back to memory not crash scheduler boot
            logger.warning(
                f"Failed to initialize SQLAlchemy job store, falling back to memory: {e}"
            )

    scheduler = AsyncIOScheduler(
        timezone=settings.scheduler_timezone,
        jobstores=jobstores or {},
    )

    # Set scheduler in unified service for job registration
    unified_scheduling_service.scheduler = scheduler

    def _add_job_to_unified(
        func,
        trigger,
        job_id,
        job_type,
        name,
        misfire_grace_time=3600,
    ):
        scheduler.add_job(
            func,
            trigger,
            id=job_id,
            name=name,
            replace_existing=True,
            misfire_grace_time=misfire_grace_time,
        )
        # Register with unified scheduler for metrics and management (metadata only)
        try:
            unified_scheduling_service.register_job(ScheduleConfig(
                job_id=job_id,
                job_type=job_type,
                name=name,
                handler=func,
                trigger=trigger,
                misfire_grace_time=misfire_grace_time,
            ))
        except Exception as e:  # noqa: BLE001  # scheduler register boundary - skip job not crash startup
            logger.warning(f"Failed to register job {job_id} with unified scheduler: {e}")

    # === CIRCULATION JOBS ===

    # Daily fine calculation at 2 AM
    _add_job_to_unified(
        calculate_daily_overdue_fines,
        CronTrigger(hour=2, minute=0),
        "daily_fine_calculation",
        ScheduleType.FINE_CALCULATION,
        "Daily Overdue Fine Calculation",
        misfire_grace_time=3600,
    )

    # Hourly hold expiration check (at the top of each hour)
    _add_job_to_unified(
        expire_old_holds,
        CronTrigger(minute=0),
        "hourly_hold_expiration",
        ScheduleType.HOLD_EXPIRATION,
        "Hourly Hold Expiration Check",
        misfire_grace_time=1800,
    )

    # Daily overdue notifications at 6 AM (skip if no email provider)
    if settings.resend_api_key:
        _add_job_to_unified(
            send_overdue_notifications,
            CronTrigger(hour=6, minute=0),
            "daily_overdue_notifications",
            ScheduleType.OVERDUE_NOTIFICATIONS,
            "Daily Overdue Notifications",
            misfire_grace_time=3600,
        )

    # === RETENTION JOBS ===

    # Recompute the maintained under_18 age-gate flag daily at 2:15 AM, BEFORE
    # the 3 AM data-retention sweep -- COPPA minor classification
    # (_get_minor_patron_ids) filters on under_18, so the flag must be current
    # for patrons who crossed 18 since their last write.
    scheduler.add_job(
        recompute_under_18_flags,
        CronTrigger(hour=2, minute=15),
        id="recompute_under_18_flags",
        name="Recompute under_18 Age-Gate Flags",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily data retention job at 3 AM
    scheduler.add_job(
        run_data_retention_jobs,
        CronTrigger(hour=3, minute=0),
        id="daily_data_retention",
        name="Daily Data Retention Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Nightly refresh of catalog_circulation_velocity_mv (weed / buy-more
    # / cold-spend report). 03:30 UTC -- runs after the retention sweep
    # at 03:00 so any rows expired in that step are reflected.
    scheduler.add_job(
        refresh_catalog_velocity_mv,
        CronTrigger(hour=3, minute=30),
        id="refresh_catalog_velocity_mv",
        name="Refresh catalog_circulation_velocity_mv",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === ROOM JOBS ===

    # Room reservation no-show processing (every 5 minutes)
    scheduler.add_job(
        process_room_no_shows,
        CronTrigger(minute="*/5"),
        id="room_no_show_processing",
        name="Room No-Show Processing",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Room reservation completion (every 15 minutes)
    scheduler.add_job(
        complete_room_reservations,
        CronTrigger(minute="*/15"),
        id="room_reservation_completion",
        name="Room Reservation Completion",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # === PUBLIC COMPUTER JOBS ===
    # Both no-ops unless their feature flag is set in settings.
    # Job runs every 5 min; no-op when COMPUTERS_AUTO_NO_SHOW_ENABLED=false.
    scheduler.add_job(
        process_computer_no_shows,
        CronTrigger(minute="*/5"),
        id="computer_no_show_processing",
        name="Computer No-Show Processing",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Auto-logout ticks every minute so over-time sessions end promptly.
    # No-op when COMPUTERS_AUTO_LOGOUT_ENABLED=false.
    scheduler.add_job(
        process_computer_auto_logouts,
        CronTrigger(minute="*"),
        id="computer_auto_logout_processing",
        name="Computer Auto-Logout Processing",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Room reservation reminders at 7 AM
    scheduler.add_job(
        send_room_reservation_reminders,
        CronTrigger(hour=7, minute=0),
        id="room_reservation_reminders",
        name="Room Reservation Reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === MISC JOBS ===

    # Daily operational alerts for staff at 7 AM (after room reservation reminders)
    scheduler.add_job(
        send_daily_operational_alerts,
        CronTrigger(hour=7, minute=5),
        id="daily_operational_alerts",
        name="Daily Operational Alerts for Staff",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Annual closure renewal on January 1st at 1 AM
    scheduler.add_job(
        renew_annual_closures,
        CronTrigger(month=1, day=1, hour=1, minute=0),
        id="annual_closure_renewal",
        name="Annual Closure Renewal",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # === PATRON LIFECYCLE JOBS ===

    # Child-to-adult account transitions at 4 AM
    scheduler.add_job(
        process_child_to_adult_transitions,
        CronTrigger(hour=4, minute=0),
        id="child_to_adult_transitions",
        name="Child to Adult Account Transitions",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Expired suspension processing (every hour at :30)
    scheduler.add_job(
        process_expired_suspensions,
        CronTrigger(minute=30),
        id="expired_suspension_processing",
        name="Expired Suspension Processing",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    # SSL/TLS certificate expiration check at 6 AM
    scheduler.add_job(
        check_certificate_expiration,
        CronTrigger(hour=6, minute=30),
        id="certificate_expiration_check",
        name="SSL Certificate Expiration Check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Database subscription status update at 1 AM
    scheduler.add_job(
        update_database_subscription_statuses,
        CronTrigger(hour=1, minute=0),
        id="database_subscription_status_update",
        name="Database Subscription Status Update",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === NOTIFICATION JOBS ===

    # Database subscription renewal notifications at 8 AM
    scheduler.add_job(
        send_database_renewal_notifications,
        CronTrigger(hour=8, minute=0),
        id="database_renewal_notifications",
        name="Database Subscription Renewal Notifications",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    #     # HomeDelivery delivery reminders at 8 AM (day before deliveries)
    #     scheduler.add_job(
    #         send_home_delivery_reminders,
    #         CronTrigger(hour=8, minute=0),
    #         id="home_delivery_reminders",
    #         name="HomeDelivery Delivery Reminders",
    #         replace_existing=True,
    #         misfire_grace_time=3600,
    #     )

    # Hold expiration reminders at 8 AM (2 days before expiry)
    scheduler.add_job(
        send_hold_expiration_reminders,
        CronTrigger(hour=8, minute=0),
        id="hold_expiration_reminders",
        name="Hold Expiration Reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Smart automated patron communications at 9 AM
    scheduler.add_job(
        send_smart_automated_communications,
        CronTrigger(hour=9, minute=0),
        id="smart_automated_communications",
        name="Smart Automated Patron Communications",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Saved-search new-arrival alerts at 6 AM (before staff arrive so
    # patron inboxes are warm by the morning catalog review)
    scheduler.add_job(
        run_saved_search_notifier,
        CronTrigger(hour=6, minute=0),
        id="saved_search_new_arrival_notifier",
        name="Saved Search New-Arrival Notifier",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Event reminders ~24h before start (hourly, top of hour)
    scheduler.add_job(
        send_event_reminders,
        CronTrigger(minute=10),
        id="event_reminders_24h",
        name="Event Reminders (24h before start)",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    # Digest Mode batching: hourly at :20, sends batched summary emails to
    # patrons whose configured digest time falls in the current hour.
    scheduler.add_job(
        send_notification_digests,
        CronTrigger(minute=20),
        id="notification_digests",
        name="Notification Digest Batching",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    #     # HomeDelivery feedback requests at 10 AM (for deliveries completed 24+ hours ago)
    #     scheduler.add_job(
    #         send_home_delivery_feedback_requests,
    #         CronTrigger(hour=10, minute=0),
    #         id="home_delivery_feedback_requests",
    #         name="HomeDelivery Feedback Requests",
    #         replace_existing=True,
    #         misfire_grace_time=3600,
    #     )

    # === OUTREACH JOBS ===

    # Outreach: Overdue bulk checkout notifications at 8 AM
    scheduler.add_job(
        process_outreach_overdue_checkouts,
        CronTrigger(hour=8, minute=0),
        id="outreach_overdue_checkouts",
        name="Outreach Overdue Bulk Checkout Notifications",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Outreach: Visit reminders at 9 AM
    scheduler.add_job(
        send_outreach_visit_reminders,
        CronTrigger(hour=9, minute=0),
        id="outreach_visit_reminders",
        name="Outreach Visit Reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Outreach: Deposit expiry warnings at 10 AM
    scheduler.add_job(
        send_outreach_deposit_warnings,
        CronTrigger(hour=10, minute=0),
        id="outreach_deposit_warnings",
        name="Outreach Deposit Expiry Warnings",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Outreach: Monthly statistics aggregation on 1st of month at 5 AM
    scheduler.add_job(
        aggregate_outreach_statistics,
        CronTrigger(day=1, hour=5, minute=0),
        id="outreach_monthly_statistics",
        name="Outreach Monthly Statistics Aggregation",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Community outcomes: Monthly snapshot generation on 1st of month at 2 AM
    scheduler.add_job(
        generate_community_metrics_snapshots,
        CronTrigger(day=1, hour=2, minute=0),
        id="community_metrics_monthly_snapshot",
        name="Community Metrics Monthly Snapshot",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Outreach: Process expired institutional cards daily at 5:30 AM
    scheduler.add_job(
        process_expired_institutional_cards_job,
        CronTrigger(hour=5, minute=30),
        id="outreach_expired_cards",
        name="Outreach Expired Institutional Cards Processing",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === MAINTENANCE JOBS ===

    # Failed job retry processing (every 10 minutes)
    if settings.scheduler_retry_enabled:
        scheduler.add_job(
            process_failed_job_retries,
            CronTrigger(minute="*/10"),
            id="failed_job_retries",
            name="Failed Job Retry Processing",
            replace_existing=True,
            misfire_grace_time=600,
        )

    # Job log cleanup at 4 AM
    scheduler.add_job(
        cleanup_job_logs,
        CronTrigger(hour=4, minute=0),
        id="job_log_cleanup",
        name="Job Log Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Cache refresh job (configurable interval, default 30 minutes)
    if settings.cache_warming_enabled:
        scheduler.add_job(
            refresh_caches,
            CronTrigger(minute=f"*/{settings.cache_refresh_interval_minutes}"),
            id="cache_refresh",
            name="Cache Refresh",
            replace_existing=True,
            misfire_grace_time=300,
        )

    # === BILLING JOBS ===

    # Monthly billing generation at 1st of month, midnight
    scheduler.add_job(
        generate_monthly_consortium_billing,
        CronTrigger(day=1, hour=0, minute=0),
        id="generate_monthly_consortium_billing",
        name="Generate Monthly Consortium Billing",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Quarterly billing generation (1st, 4th, 7th, 10th month at midnight)
    scheduler.add_job(
        generate_quarterly_consortium_billing,
        CronTrigger(month="1,4,7,10", day=1, hour=0, minute=0),
        id="generate_quarterly_consortium_billing",
        name="Generate Quarterly Consortium Billing",
        replace_existing=True,
        misfire_grace_time=86400,
    )

    # Mark overdue consortium invoices daily at 1 AM
    scheduler.add_job(
        mark_overdue_consortium_invoices,
        CronTrigger(hour=1, minute=0),
        id="mark_overdue_consortium_invoices",
        name="Mark Overdue Consortium Invoices",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Send consortium payment reminders every Friday at 9 AM
    scheduler.add_job(
        send_consortium_payment_reminders,
        CronTrigger(day_of_week=4, hour=9, minute=0),
        id="send_consortium_payment_reminders",
        name="Send Consortium Payment Reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === MISC JOBS (CONTINUED) ===

    # End-of-Day auto-logout processing (every minute)
    scheduler.add_job(
        process_eod_auto_logouts,
        CronTrigger(minute="*"),
        id="eod_auto_logout_processing",
        name="End-of-Day Auto-Logout Processing",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Compliance deadline check at 8 AM
    from ..compliance_deadline_scheduler import check_compliance_deadlines
    scheduler.add_job(
        check_compliance_deadlines,
        CronTrigger(hour=8, minute=0),
        id="compliance_deadline_check",
        name="Compliance Deadline Check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Compliance escalation check (every Monday at 9 AM)
    from ..compliance_deadline_scheduler import escalate_overdue_compliance_items
    scheduler.add_job(
        escalate_overdue_compliance_items,
        CronTrigger(day_of_week=0, hour=9, minute=0),
        id="compliance_escalation_check",
        name="Compliance Escalation Check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === MONITORING JOBS ===

    # Job heartbeat monitor (dead man's switch) - every 15 minutes
    scheduler.add_job(
        check_job_heartbeats,
        CronTrigger(minute="*/15"),
        id="job_heartbeat_monitor",
        name="Job Heartbeat Monitor (Dead Man's Switch)",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Notification retry processing (email/SMS DLQ) - every 5 minutes
    scheduler.add_job(
        process_failed_notification_retries,
        CronTrigger(minute="*/5"),
        id="notification_retry_processing",
        name="Failed Notification Retry Processing",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Notification queue processor - every 2 minutes
    scheduler.add_job(
        process_notification_queue,
        CronTrigger(minute="*/2"),
        id="notification_queue_processor",
        name="Notification Queue Processor",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # === BAN TRACKER JOBS ===

    # PEN America data sync nightly at 3 AM UTC
    scheduler.add_job(
        pen_america_sync_job,
        CronTrigger(hour=3, minute=0),
        id="pen_america_sync",
        name="PEN America Book Ban Data Sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly ban tracker digest email on Monday at 8 AM UTC
    scheduler.add_job(
        ban_tracker_digest_job,
        CronTrigger(day_of_week=0, hour=8, minute=0),
        id="ban_tracker_weekly_digest",
        name="Ban Tracker Weekly Digest Email",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === RELEASE INGESTION JOBS ===

    # Daily release ingestion at 4:30 AM
    scheduler.add_job(
        process_release_ingestion,
        CronTrigger(hour=4, minute=30),
        id="daily_release_ingestion",
        name="Daily Release Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly editorial pre-pub ingestion (LibraryReads) — Mondays 5:00 AM
    scheduler.add_job(
        process_editorial_release_ingestion,
        CronTrigger(day_of_week=0, hour=5, minute=0),
        id="weekly_editorial_release_ingestion",
        name="Weekly Editorial Release Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly editorial RSS ingestion (Millions/LitHub/TLT/Brown Bookshelf) — Tuesdays 5:00 AM
    scheduler.add_job(
        process_editorial_rss_ingestion,
        CronTrigger(day_of_week=1, hour=5, minute=0),
        id="weekly_editorial_rss_ingestion",
        name="Weekly Editorial RSS Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly indie release ingestion (Mastodon buzz + itch.io) — Wednesdays 5:00 AM
    scheduler.add_job(
        process_indie_release_ingestion,
        CronTrigger(day_of_week=2, hour=5, minute=0),
        id="weekly_indie_release_ingestion",
        name="Weekly Indie Release Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly MetisLib recruitment digest — Wednesdays 6:00 AM (after the ingest above)
    scheduler.add_job(
        process_recruitment_digest,
        CronTrigger(day_of_week=2, hour=6, minute=0),
        id="weekly_recruitment_digest",
        name="Weekly Recruitment Digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === EMBEDDING JOBS ===

    # Catalog embedding backfill every 6 hours (at :15 past)
    scheduler.add_job(
        backfill_catalog_embeddings,
        CronTrigger(hour="*/6", minute=15),
        id="catalog_embedding_backfill",
        name="Catalog Embedding Backfill",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === JOURNEY ANALYTICS JOBS ===

    # Detect abandoned journeys every 15 minutes
    scheduler.add_job(
        detect_journey_dropoffs,
        CronTrigger(minute="*/15"),
        id="journey_dropoff_detection",
        name="Journey Drop-off Detection",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Aggregate journey metrics hourly at :05 past
    scheduler.add_job(
        aggregate_journey_metrics,
        CronTrigger(minute=5),
        id="journey_metrics_aggregation",
        name="Journey Metrics Hourly Aggregation",
        replace_existing=True,
        misfire_grace_time=3600,
    )


    # === TIMESHEET JOBS ===

    # Nightly dangling-punch sweep at 07:10 UTC (overnight US Eastern, after
    # the library-local day has ended year-round): closes punches left open
    # past local end-of-day and resets stale presence rows. Auto-closed days
    # stay flagged for manager review via /staff/timesheet/open-shifts/me.
    scheduler.add_job(
        sweep_dangling_punches,
        CronTrigger(hour=7, minute=10),
        id="dangling_punch_sweep",
        name="Dangling Punch Sweep",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # === INDIE LENDING JOBS ===

    # Daily indie ebook borrow expiry at 2:30 AM
    _add_job_to_unified(
        expire_overdue_indie_borrows,
        CronTrigger(hour=2, minute=30),
        "indie_borrow_expiry",
        ScheduleType.INDIE_LENDING,
        "Indie Ebook Borrow Expiry",
        misfire_grace_time=3600,
    )

    # Hourly reconcile of failed L30->MetisLib borrow/return syncs (no silent drift)
    _add_job_to_unified(
        reconcile_metislib_borrow_sync,
        CronTrigger(minute=15),
        "indie_metislib_sync_reconcile",
        ScheduleType.INDIE_LENDING,
        "Indie MetisLib Borrow-Sync Reconcile",
        misfire_grace_time=3600,
    )

    # Nightly owned-catalog refresh from MetisLib's indie OPDS feed at 4:00 AM.
    # No-op unless INDIE_OPDS_IMPORT_ENABLED; /indie browse reads only the
    # owned table, so this is what keeps new indie titles appearing.
    _add_job_to_unified(
        sync_indie_opds_catalog,
        CronTrigger(hour=4, minute=0),
        "indie_opds_catalog_sync",
        ScheduleType.INDIE_LENDING,
        "Indie OPDS Owned-Catalog Sync",
        misfire_grace_time=3600,
    )

    # Daily indie due-soon notifications at 7:30 AM (only if email configured)
    if settings.resend_api_key:
        _add_job_to_unified(
            send_indie_due_soon_notifications,
            CronTrigger(hour=7, minute=30),
            "indie_due_soon_notifications",
            ScheduleType.INDIE_LENDING,
            "Indie Ebook Due Soon Notifications",
            misfire_grace_time=3600,
        )

        # Weekly indie author release digest -- Mondays at 9:00 AM
        _add_job_to_unified(
            send_indie_author_release_digests,
            CronTrigger(day_of_week=0, hour=9, minute=0),
            "indie_author_release_digest",
            ScheduleType.INDIE_LENDING,
            "Indie Author Release Digest",
            misfire_grace_time=3600,
        )

        # === PARENT-ONBOARDING FOLLOW-UP REMINDERS ===
        # Two daily passes with DISTINCT Resend tag names per
        # feedback_resend_tag_name_uniqueness:
        #   08:00 UTC -- due-tomorrow (tag: parent-onboarding-followup-reminder)
        #   09:00 UTC -- overdue      (tag: parent-onboarding-followup-overdue)
        # Email-only feature: gated on resend_api_key alongside other email jobs.
        scheduler.add_job(
            send_parent_onboarding_followup_due_tomorrow_reminders,
            CronTrigger(hour=8, minute=0),
            id="parent_onboarding_followup_due_tomorrow",
            name="Parent Onboarding Followup -- Due Tomorrow Reminder",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            send_parent_onboarding_followup_overdue_reminders,
            CronTrigger(hour=9, minute=0),
            id="parent_onboarding_followup_overdue",
            name="Parent Onboarding Followup -- Overdue Reminder",
            replace_existing=True,
            misfire_grace_time=3600,
        )


    # === EDI JOBS (only if EDI polling is enabled) ===

    if settings.edi_polling_enabled:
        # EDI inbound message polling every 15 minutes (offset: :07,:22,:37,:52)
        _add_job_to_unified(
            poll_edi_inbound_messages,
            CronTrigger(minute="7,22,37,52"),
            "edi_inbound_polling",
            ScheduleType.EDI_POLLING,
            "EDI Inbound Message Polling",
            misfire_grace_time=600,
        )

        # EDI retry processing every 30 minutes (at :00,:30)
        _add_job_to_unified(
            process_edi_retries,
            CronTrigger(minute="0,30"),
            "edi_retry_processing",
            ScheduleType.EDI_RETRY,
            "EDI Retry Processing",
            misfire_grace_time=600,
        )

    # === UPDATE CHECKER ===

    # Daily GitHub release check at 5 AM
    scheduler.add_job(
        run_scheduled_check,
        CronTrigger(hour=5, minute=0),
        id='update_checker',
        name='Daily Update Checker',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Initialize tech booking scheduled jobs
    from ..tech_booking_scheduler import initialize_tech_booking_jobs
    initialize_tech_booking_jobs(scheduler)

    # Daily longitudinal engagement-survey dispatch (9 AM)
    scheduler.add_job(
        dispatch_longitudinal_surveys,
        CronTrigger(hour=9, minute=0),
        id="engagement_longitudinal_dispatch",
        name="Engagement Longitudinal Survey Dispatch",
        replace_existing=True,
        misfire_grace_time=3600,
    )


    # Course-authoring empty-stub sweep (Wave 1 / W1-B). Daily at 02:00 UTC.
    # Deletes lessons that have been empty (title='' + empty body) for >24h,
    # emailing the course creator first. Defers if the daily email cap can't
    # cover the notifications -- see lesson_sweep_service for the rationale
    # (feedback_l30_email_safeguard_cap_masks_failure).
    _add_job_to_unified(
        sweep_empty_lessons_job,
        CronTrigger(hour=2, minute=0),
        "sweep_empty_lessons",
        ScheduleType.SYSTEM_MAINTENANCE,
        "Sweep Empty Course-Authoring Stub Lessons",
        misfire_grace_time=3600,
    )

    # Promote scheduled blog posts whose time has arrived (every minute).
    # PR #1169 originally added this to app/core/scheduler.py, which is the
    # dead module -- this is the live one. Without this registration,
    # status=scheduled posts stay scheduled forever.
    from ...tasks.blog_publisher import publish_scheduled_blog_posts
    scheduler.add_job(
        publish_scheduled_blog_posts,
        CronTrigger(minute="*"),
        id="publish_scheduled_blog_posts",
        name="Publish Scheduled Blog Posts",
        replace_existing=True,
        misfire_grace_time=120,
    )

    scheduler.start()
    logger.info(
        "Background job scheduler started",
        extra={
            "timezone": settings.scheduler_timezone,
            "job_store": settings.scheduler_job_store,
            "retry_enabled": settings.scheduler_retry_enabled,
            "total_jobs": len(scheduler.get_jobs()),
        },
    )

    # Run startup catch-up check for daily jobs
    # This triggers any daily jobs that missed their scheduled run during downtime
    import asyncio
    from .startup_catchup import check_and_catchup_daily_jobs, trigger_daily_job

    asyncio.create_task(_run_startup_catchup(scheduler))


def shutdown_scheduler() -> None:
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background job scheduler shut down")
        scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return scheduler


async def _run_startup_catchup(sched: AsyncIOScheduler) -> None:
    from .startup_catchup import check_and_catchup_daily_jobs, trigger_daily_job

    try:
        logger.info("Running startup catch-up check for daily jobs...")
        result = await check_and_catchup_daily_jobs()

        if result["triggered_jobs"]:
            logger.info(
                f"Triggering {len(result['triggered_jobs'])} overdue daily job(s) on startup",
                extra={
                    "triggered_jobs": result["triggered_jobs"],
                    "skipped_jobs": result["skipped_jobs"],
                },
            )
            for job_id in result["triggered_jobs"]:
                await trigger_daily_job(sched, job_id)
        else:
            logger.info(
                "No overdue daily jobs to catch up on startup",
                extra={"skipped_jobs": result["skipped_jobs"]},
            )

    except Exception as e:
        logger.error(
            "Failed to run startup catch-up check: {e}",
            exc_info=True,
        )
