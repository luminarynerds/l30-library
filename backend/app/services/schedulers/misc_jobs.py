# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal, engine
from ...core.email import send_email, COLORS
from ...core.logging import get_logger
from ...models.audit_log import AuditAction, AuditLog
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.event import Event
from ...models.event_registration import EventRegistration, EventRegistrationStatus
from ...models.event_review import EventReview
from ...models.fine import Fine, FineStatus, FineType
from ...models.job_failure import JobSeverity
from ...models.multi_branch import BranchClosure, SystemSettings
from ...models.notification import NotificationPreferences, NotificationType
from ...models.permission import RoleSettings
from ...models.reading import ReadingAchievement
from ...models.sms import SMSNotificationType
from ...models.room import Room, RoomReservation, ReservationStatus
from ...models.user import User, UserRole
from ..job_failure_service import (
    JobExecutionContext,
    cleanup_old_job_logs,
    process_retry_queue,
)
from ..unified_scheduler import ScheduleType, SchedulingService, set_scheduling_service
from ...models.notification import NotificationQueue
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
from .maintenance_jobs import (
    process_failed_job_retries,
    cleanup_job_logs,
    refresh_caches,
)
from .notification_jobs import (
    send_hold_expiration_reminders,
    send_smart_automated_communications,
)
from .outreach_jobs import (
    process_outreach_overdue_checkouts,
    send_outreach_visit_reminders,
    send_outreach_deposit_warnings,
    aggregate_outreach_statistics,
)
from .patron_lifecycle_jobs import (
    process_child_to_adult_transitions,
    process_expired_suspensions,
    send_database_renewal_notifications,
    send_home_delivery_reminders,
    send_home_delivery_feedback_requests,
    process_expired_institutional_cards_job,
)
from .retention_jobs import run_data_retention_jobs
from .room_jobs import (
    process_room_no_shows,
    complete_room_reservations,
    send_room_reservation_reminders,
)

settings = get_settings()
logger = get_logger(__name__)


def get_overdue_fine_per_day() -> Decimal:
    return Decimal(settings.overdue_fine_per_day)

async def renew_annual_closures() -> None:
    logger.info("Starting annual closure renewal job")
    closures_renewed = 0
    closures_skipped = 0
    errors = 0

    try:
        async with AsyncSessionLocal() as db:
            today = date.today()
            current_year = today.year

            # Find all annual closures where the end_date is before the current year
            # This means closures from last year or earlier that haven't been renewed yet
            stmt = select(BranchClosure).where(
                and_(
                    BranchClosure.is_annual == True,
                    BranchClosure.end_date < date(current_year, 1, 1),
                )
            )
            result = await db.execute(stmt)
            annual_closures = result.scalars().all()

            logger.info(
                f"Found {len(annual_closures)} annual closures to potentially renew"
            )

            for closure in annual_closures:
                try:
                    # Calculate next year's dates
                    # Handle leap year edge case: Feb 29 -> Feb 28
                    try:
                        new_start_date = closure.start_date.replace(
                            year=closure.start_date.year + 1
                        )
                    except ValueError:
                        # Feb 29 on a leap year -> Feb 28
                        new_start_date = closure.start_date.replace(
                            year=closure.start_date.year + 1, day=28
                        )

                    try:
                        new_end_date = closure.end_date.replace(
                            year=closure.end_date.year + 1
                        )
                    except ValueError:
                        new_end_date = closure.end_date.replace(
                            year=closure.end_date.year + 1, day=28
                        )

                    # Check if a closure with same branch, reason, and dates already exists
                    existing_stmt = select(BranchClosure).where(
                        and_(
                            BranchClosure.branch_id == closure.branch_id,
                            BranchClosure.start_date == new_start_date,
                            BranchClosure.end_date == new_end_date,
                            BranchClosure.reason == closure.reason,
                        )
                    )
                    existing_result = await db.execute(existing_stmt)
                    existing_closure = existing_result.scalar_one_or_none()

                    if existing_closure:
                        logger.debug(
                            f"Skipping duplicate closure for branch {closure.branch_id}: "
                            f"{closure.reason} on {new_start_date}"
                        )
                        closures_skipped += 1
                        continue

                    # Create the new closure for next year
                    new_closure = BranchClosure(
                        branch_id=closure.branch_id,
                        start_date=new_start_date,
                        end_date=new_end_date,
                        start_time=closure.start_time,
                        end_time=closure.end_time,
                        reason=closure.reason,
                        description=closure.description,
                        is_system_wide=closure.is_system_wide,
                        is_annual=True,  # Carry forward the annual flag
                        created_by_id=closure.created_by_id,
                    )
                    db.add(new_closure)
                    closures_renewed += 1

                    logger.debug(
                        f"Created renewal closure for branch {closure.branch_id}: "
                        f"{closure.reason} from {new_start_date} to {new_end_date}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error renewing closure {closure.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
                    continue

            await db.commit()

        logger.info(
            "Annual closure renewal job completed",
            extra={
                "closures_renewed": closures_renewed,
                "closures_skipped": closures_skipped,
                "errors": errors,
            },
        )
    except Exception as e:
        logger.error(f"Fatal error in annual closure renewal: {e}", exc_info=True)
        raise



async def send_daily_operational_alerts() -> None:
    async with JobExecutionContext(
        job_id="daily_operational_alerts",
        job_name="Daily Operational Alerts for Staff",
        severity=JobSeverity.LOW,
    ) as ctx:
        logger.info("Starting daily operational alerts generation")

        async with AsyncSessionLocal() as db:
            from .daily_alerts_service import DailyAlertsService
            from ...core.email import send_email
            from ...core.logging import get_logger

            # Generate morning dashboard
            dashboard = await DailyAlertsService.generate_morning_dashboard(db)
            summary = await DailyAlertsService.compile_alerts_summary(dashboard)

            # Query staff members who have enabled daily alerts
            staff_result = await db.execute(
                select(User).where(User.role.in_([UserRole.STAFF, UserRole.ADMIN]))
            )
            staff_members = staff_result.scalars().all()

            alert_count = 0
            for staff in staff_members:
                try:
                    # Get staff notification preferences
                    from ...models.notification import NotificationPreferences

                    prefs_result = await db.execute(
                        select(NotificationPreferences).where(
                            NotificationPreferences.user_id == staff.id
                        )
                    )
                    prefs = prefs_result.scalar_one_or_none()

                    # Check if staff has enabled daily alerts
                    if not prefs or not prefs.email_staff_daily_alert:
                        continue

                    # Format dashboard as HTML email
                    alert_html = _render_daily_alerts_email(staff, dashboard)

                    # Queue notification in database
                    notification = NotificationQueue(
                        user_id=staff.id,
                        notification_type=NotificationType.STAFF_DAILY_ALERT,
                        recipient_email=staff.email,
                        subject=f"Daily Operations Alert - {date.today().strftime('%B %d, %Y')}",
                        html_body=alert_html,
                        scheduled_for=datetime.now(timezone.utc),
                        context_data={
                            "alert_count": dashboard.total_alerts,
                            "critical_alerts": summary["alert_count"],
                        },
                    )
                    db.add(notification)
                    alert_count += 1

                except Exception as e:
                    logger.error(
                        f"Error processing daily alerts for staff {staff.id}: {e}",
                        exc_info=True,
                    )

            await db.commit()
            ctx.add_metric("staff_notified", alert_count)
            ctx.add_metric("total_alerts", dashboard.total_alerts)
            ctx.items_processed = alert_count
            ctx.items_succeeded = alert_count
            logger.info(
                f"Generated daily operational alerts for {alert_count} staff members",
                extra={
                    "staff_count": alert_count,
                    "total_alerts": dashboard.total_alerts,
                },
            )


def _render_daily_alerts_email(user: User, dashboard) -> str:
    from ...core.email import COLORS

    alerts_html = []
    for alert in dashboard.alerts:
        severity_icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(
            alert.severity, "•"
        )

        severity_color = {
            "critical": "#C0392B",
            "warning": "#E67E22",
            "info": "#3498DB",
        }.get(alert.severity, "#95A5A6")

        alerts_html.append(
            f"""
        <div style="border-left: 4px solid {severity_color}; padding: 15px; margin: 10px 0; background-color: #F8F9FA; border-radius: 4px;">
            <h3 style="color: {severity_color}; margin-top: 0;">
                {severity_icon} {alert.description}
            </h3>
            <p style="margin: 10px 0; color: {COLORS['body']};">
                <strong>Count:</strong> {alert.count}
            </p>
        </div>
        """
        )

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: {COLORS['heading']}; border-bottom: 2px solid {COLORS['divider']}; padding-bottom: 10px;">
            Daily Operations Dashboard
        </h1>
        <p style="color: {COLORS['text_light']};">
            Generated: {dashboard.generated_at.strftime('%B %d, %Y at %I:%M %p')}
        </p>

        <div style="background-color: #ECF0F1; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 5px 0; color: {COLORS['body']};">
                <strong>Total Alerts:</strong> {dashboard.total_alerts}
            </p>
            <p style="margin: 5px 0; color: #C0392B;">
                <strong>Critical:</strong> {dashboard.to_dict()['alerts_by_severity']['critical']}
            </p>
            <p style="margin: 5px 0; color: #E67E22;">
                <strong>Warnings:</strong> {dashboard.to_dict()['alerts_by_severity']['warning']}
            </p>
        </div>

        <h2 style="color: {COLORS['heading']}; margin-top: 30px;">Operational Alerts</h2>
        {''.join(alerts_html)}

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            This is your daily operational alert summary. Visit the staff dashboard for detailed information.
            You can customize your alert preferences in your notification settings.
        </p>
    </div>
    """


# =============================================================================
# END-OF-DAY AUTO-LOGOUT JOB
# =============================================================================

async def process_eod_auto_logouts() -> None:
    try:
        async with AsyncSessionLocal() as db:
            from ...models.end_of_day import EODSession, EODSessionStatus

            now = datetime.now(timezone.utc)

            # Find sessions that have reached auto-logout time
            result = await db.execute(
                select(EODSession).where(
                    and_(
                        EODSession.auto_logout_at.isnot(None),
                        EODSession.auto_logout_at <= now,
                        EODSession.auto_logout_performed == False,
                        EODSession.status == EODSessionStatus.COMPLETED,
                    )
                )
            )
            sessions = result.scalars().all()

            for session in sessions:
                try:
                    # Mark as auto-logout performed
                    session.auto_logout_performed = True

                    # Log the auto-logout event
                    audit_log = AuditLog(
                        user_id=session.staff_id,
                        action=AuditAction.LOGOUT,
                        resource_type="EODSession",
                        resource_id=session.id,
                        description=f"Auto-logout triggered after EOD session {session.session_code}",
                        timestamp=now,
                    )
                    db.add(audit_log)

                    logger.info(
                        f"EOD auto-logout triggered for session {session.session_code}",
                        extra={"session_id": session.id, "staff_id": session.staff_id},
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing EOD auto-logout for session {session.id}: {e}",
                        exc_info=True,
                    )

            if sessions:
                await db.commit()
                logger.info(
                    f"Processed {len(sessions)} EOD auto-logouts",
                    extra={"logout_count": len(sessions)},
                )

    except Exception as e:
        logger.error(f"Error in EOD auto-logout processing: {e}", exc_info=True)


def init_scheduler() -> None:
    global scheduler, unified_scheduling_service

    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled via configuration")
        return

    # Initialize the unified scheduling service
    unified_scheduling_service = SchedulingService()
    set_scheduling_service(unified_scheduling_service)
    logger.info("Initialized unified scheduling service")

    # Configure job stores based on settings
    jobstores = {}
    if settings.scheduler_job_store == "sqlalchemy" and engine is not None:
        try:
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

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
        jobstores=jobstores if jobstores else None,
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
        # Also register with unified scheduler for metrics and management
        try:
            unified_scheduling_service.add_job(
                func,
                trigger,
                job_id,
                job_type,
                name,
                misfire_grace_time=misfire_grace_time,
            )
        except Exception as e:  # noqa: BLE001  # scheduler register boundary - skip job not crash startup
            logger.warning(f"Failed to register job {job_id} with unified scheduler: {e}")

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

    # Daily overdue notifications at 6 AM
    _add_job_to_unified(
        send_overdue_notifications,
        CronTrigger(hour=6, minute=0),
        "daily_overdue_notifications",
        ScheduleType.OVERDUE_NOTIFICATIONS,
        "Daily Overdue Notifications",
        misfire_grace_time=3600,
    )

    # Daily data retention job at 3 AM
    scheduler.add_job(
        run_data_retention_jobs,
        CronTrigger(hour=3, minute=0),
        id="daily_data_retention",
        name="Daily Data Retention Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Room reservation no-show processing (every 5 minutes)
    scheduler.add_job(
        process_room_no_shows,
        CronTrigger(minute="*/5"),  # Every 5 minutes
        id="room_no_show_processing",
        name="Room No-Show Processing",
        replace_existing=True,
        misfire_grace_time=300,  # 5 minute grace period
    )

    # Room reservation completion (every 15 minutes)
    scheduler.add_job(
        complete_room_reservations,
        CronTrigger(minute="*/15"),  # Every 15 minutes
        id="room_reservation_completion",
        name="Room Reservation Completion",
        replace_existing=True,
        misfire_grace_time=600,  # 10 minute grace period
    )

    # Room reservation reminders at 7 AM
    scheduler.add_job(
        send_room_reservation_reminders,
        CronTrigger(hour=7, minute=0),
        id="room_reservation_reminders",
        name="Room Reservation Reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Daily operational alerts for staff at 7 AM (after room reservation reminders)
    scheduler.add_job(
        send_daily_operational_alerts,
        CronTrigger(hour=7, minute=5),
        id="daily_operational_alerts",
        name="Daily Operational Alerts for Staff",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Annual closure renewal on January 1st at 1 AM
    scheduler.add_job(
        renew_annual_closures,
        CronTrigger(month=1, day=1, hour=1, minute=0),
        id="annual_closure_renewal",
        name="Annual Closure Renewal",
        replace_existing=True,
        misfire_grace_time=86400,  # 24 hour grace period (yearly job)
    )

    # Child-to-adult account transitions at 4 AM
    scheduler.add_job(
        process_child_to_adult_transitions,
        CronTrigger(hour=4, minute=0),
        id="child_to_adult_transitions",
        name="Child to Adult Account Transitions",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Expired suspension processing (every hour at :30)
    scheduler.add_job(
        process_expired_suspensions,
        CronTrigger(minute=30),  # Every hour at :30
        id="expired_suspension_processing",
        name="Expired Suspension Processing",
        replace_existing=True,
        misfire_grace_time=1800,  # 30 minute grace period
    )

    # SSL/TLS certificate expiration check at 6 AM
    scheduler.add_job(
        check_certificate_expiration,
        CronTrigger(hour=6, minute=30),
        id="certificate_expiration_check",
        name="SSL Certificate Expiration Check",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Database subscription status update at 1 AM
    scheduler.add_job(
        update_database_subscription_statuses,
        CronTrigger(hour=1, minute=0),
        id="database_subscription_status_update",
        name="Database Subscription Status Update",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Database subscription renewal notifications at 8 AM
    scheduler.add_job(
        send_database_renewal_notifications,
        CronTrigger(hour=8, minute=0),
        id="database_renewal_notifications",
        name="Database Subscription Renewal Notifications",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # HomeDelivery delivery reminders at 8 AM (day before deliveries)
    scheduler.add_job(
        send_home_delivery_reminders,
        CronTrigger(hour=8, minute=0),
        id="home_delivery_reminders",
        name="HomeDelivery Delivery Reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Hold expiration reminders at 8 AM (2 days before expiry)
    scheduler.add_job(
        send_hold_expiration_reminders,
        CronTrigger(hour=8, minute=0),
        id="hold_expiration_reminders",
        name="Hold Expiration Reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Smart automated patron communications at 9 AM
    scheduler.add_job(
        send_smart_automated_communications,
        CronTrigger(hour=9, minute=0),
        id="smart_automated_communications",
        name="Smart Automated Patron Communications",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Outreach: Overdue bulk checkout notifications at 8 AM
    scheduler.add_job(
        process_outreach_overdue_checkouts,
        CronTrigger(hour=8, minute=0),
        id="outreach_overdue_checkouts",
        name="Outreach Overdue Bulk Checkout Notifications",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Outreach: Visit reminders at 9 AM
    scheduler.add_job(
        send_outreach_visit_reminders,
        CronTrigger(hour=9, minute=0),
        id="outreach_visit_reminders",
        name="Outreach Visit Reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # HomeDelivery feedback requests at 10 AM (for deliveries completed 24+ hours ago)
    scheduler.add_job(
        send_home_delivery_feedback_requests,
        CronTrigger(hour=10, minute=0),
        id="home_delivery_feedback_requests",
        name="HomeDelivery Feedback Requests",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Outreach: Deposit expiry warnings at 10 AM
    scheduler.add_job(
        send_outreach_deposit_warnings,
        CronTrigger(hour=10, minute=0),
        id="outreach_deposit_warnings",
        name="Outreach Deposit Expiry Warnings",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Outreach: Monthly statistics aggregation on 1st of month at 5 AM
    scheduler.add_job(
        aggregate_outreach_statistics,
        CronTrigger(day=1, hour=5, minute=0),
        id="outreach_monthly_statistics",
        name="Outreach Monthly Statistics Aggregation",
        replace_existing=True,
        misfire_grace_time=86400,  # 24 hour grace period
    )

    # Outreach: Process expired institutional cards daily at 5:30 AM
    scheduler.add_job(
        process_expired_institutional_cards_job,
        CronTrigger(hour=5, minute=30),
        id="outreach_expired_cards",
        name="Outreach Expired Institutional Cards Processing",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # === Job Failure Handling Jobs ===

    # Failed job retry processing (every 10 minutes)
    if settings.scheduler_retry_enabled:
        scheduler.add_job(
            process_failed_job_retries,
            CronTrigger(minute="*/10"),  # Every 10 minutes
            id="failed_job_retries",
            name="Failed Job Retry Processing",
            replace_existing=True,
            misfire_grace_time=600,  # 10 minute grace period
        )

    # Job log cleanup at 4 AM
    scheduler.add_job(
        cleanup_job_logs,
        CronTrigger(hour=4, minute=0),
        id="job_log_cleanup",
        name="Job Log Cleanup",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Cache refresh job (configurable interval, default 30 minutes)
    if settings.cache_warming_enabled:
        scheduler.add_job(
            refresh_caches,
            CronTrigger(minute=f"*/{settings.cache_refresh_interval_minutes}"),
            id="cache_refresh",
            name="Cache Refresh",
            replace_existing=True,
            misfire_grace_time=300,  # 5 minute grace period
        )

    # Consortium billing jobs
    # Monthly billing generation at 1st of month, midnight
    scheduler.add_job(
        generate_monthly_consortium_billing,
        CronTrigger(day=1, hour=0, minute=0),
        id="generate_monthly_consortium_billing",
        name="Generate Monthly Consortium Billing",
        replace_existing=True,
        misfire_grace_time=86400,  # 24 hour grace period
    )

    # Quarterly billing generation (1st, 4th, 7th, 10th month at midnight)
    scheduler.add_job(
        generate_quarterly_consortium_billing,
        CronTrigger(month="1,4,7,10", day=1, hour=0, minute=0),
        id="generate_quarterly_consortium_billing",
        name="Generate Quarterly Consortium Billing",
        replace_existing=True,
        misfire_grace_time=86400,  # 24 hour grace period
    )

    # Mark overdue consortium invoices daily at 1 AM
    scheduler.add_job(
        mark_overdue_consortium_invoices,
        CronTrigger(hour=1, minute=0),
        id="mark_overdue_consortium_invoices",
        name="Mark Overdue Consortium Invoices",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Send consortium payment reminders every Friday at 9 AM
    scheduler.add_job(
        send_consortium_payment_reminders,
        CronTrigger(day_of_week=4, hour=9, minute=0),  # Friday 9 AM
        id="send_consortium_payment_reminders",
        name="Send Consortium Payment Reminders",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # End-of-Day auto-logout processing (every minute)
    scheduler.add_job(
        process_eod_auto_logouts,
        CronTrigger(minute="*"),  # Every minute
        id="eod_auto_logout_processing",
        name="End-of-Day Auto-Logout Processing",
        replace_existing=True,
        misfire_grace_time=60,  # 1 minute grace period
    )

    # Compliance deadline check at 8 AM
    from ..compliance_deadline_scheduler import check_compliance_deadlines
    scheduler.add_job(
        check_compliance_deadlines,
        CronTrigger(hour=8, minute=0),
        id="compliance_deadline_check",
        name="Compliance Deadline Check",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # Compliance escalation check (every Monday at 9 AM)
    from ..compliance_deadline_scheduler import escalate_overdue_compliance_items
    scheduler.add_job(
        escalate_overdue_compliance_items,
        CronTrigger(day_of_week=0, hour=9, minute=0),  # Monday 9 AM
        id="compliance_escalation_check",
        name="Compliance Escalation Check",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
    )

    # === RELEASE INGESTION JOBS ===

    # Daily release ingestion at 4:30 AM
    from .release_ingestion_jobs import process_release_ingestion
    scheduler.add_job(
        process_release_ingestion,
        CronTrigger(hour=4, minute=30),
        id="daily_release_ingestion",
        name="Daily Release Ingestion",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Initialize tech booking scheduled jobs
    from ..tech_booking_scheduler import initialize_tech_booking_jobs
    initialize_tech_booking_jobs(scheduler)

    scheduler.start()
    logger.info(
        "Background job scheduler started",
        extra={
            "timezone": settings.scheduler_timezone,
            "job_store": settings.scheduler_job_store,
            "retry_enabled": settings.scheduler_retry_enabled,
            "jobs": [
                "daily_fine_calculation (2:00 AM)",
                "hourly_hold_expiration (every hour at :00)",
                "daily_overdue_notifications (6:00 AM)",
                "certificate_expiration_check (6:30 AM)",
                "daily_data_retention (3:00 AM)",
                "child_to_adult_transitions (4:00 AM)",
                "expired_suspension_processing (every hour at :30)",
                "room_no_show_processing (every 5 minutes)",
                "room_reservation_completion (every 15 minutes)",
                "room_reservation_reminders (7:00 AM)",
                "annual_closure_renewal (January 1st, 1:00 AM)",
                "certificate_expiration_check (6:30 AM)",
                "database_subscription_status_update (1:00 AM)",
                "database_renewal_notifications (8:00 AM)",
                "home_delivery_reminders (8:00 AM)",
                "hold_expiration_reminders (8:00 AM)",
                "smart_automated_communications (9:00 AM)",
                "outreach_overdue_checkouts (8:00 AM)",
                "outreach_visit_reminders (9:00 AM)",
                "home_delivery_feedback_requests (10:00 AM)",
                "outreach_deposit_warnings (10:00 AM)",
                "outreach_monthly_statistics (1st of month, 5:00 AM)",
                "outreach_expired_cards (5:30 AM)",
                "generate_monthly_consortium_billing (1st of month, 12:00 AM)",
                "generate_quarterly_consortium_billing (1st of Q months, 12:00 AM)",
                "mark_overdue_consortium_invoices (1:00 AM)",
                "send_consortium_payment_reminders (Friday, 9:00 AM)",
                "daily_release_ingestion (4:30 AM)",
                (
                    "failed_job_retries (every 10 minutes)"
                    if settings.scheduler_retry_enabled
                    else None
                ),
                "job_log_cleanup (4:00 AM)",
                (
                    f"cache_refresh (every {settings.cache_refresh_interval_minutes} minutes)"
                    if settings.cache_warming_enabled
                    else None
                ),
            ],
        },
    )


def shutdown_scheduler() -> None:
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background job scheduler shut down")
        scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return scheduler


async def process_eod_auto_logouts() -> None:
    try:
        async with AsyncSessionLocal() as db:
            from ...models.end_of_day import EODSession, EODSessionStatus

            now = datetime.now(timezone.utc)

            # Find sessions that have reached auto-logout time
            result = await db.execute(
                select(EODSession).where(
                    and_(
                        EODSession.auto_logout_at.isnot(None),
                        EODSession.auto_logout_at <= now,
                        EODSession.auto_logout_performed == False,
                        EODSession.status == EODSessionStatus.COMPLETED,
                    )
                )
            )
            sessions = result.scalars().all()

            for session in sessions:
                try:
                    # Mark as auto-logout performed
                    session.auto_logout_performed = True

                    # Log the auto-logout event
                    audit_log = AuditLog(
                        user_id=session.staff_id,
                        action=AuditAction.LOGOUT,
                        resource_type="EODSession",
                        resource_id=session.id,
                        description=f"Auto-logout triggered after EOD session {session.session_code}",
                        timestamp=now,
                    )
                    db.add(audit_log)

                    logger.info(
                        f"EOD auto-logout triggered for session {session.session_code}",
                        extra={"session_id": session.id, "staff_id": session.staff_id},
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing EOD auto-logout for session {session.id}: {e}",
                        exc_info=True,
                    )

            if sessions:
                await db.commit()
                logger.info(
                    f"Processed {len(sessions)} EOD auto-logouts",
                    extra={"logout_count": len(sessions)},
                )

    except Exception as e:
        logger.error(f"Error in EOD auto-logout processing: {e}", exc_info=True)



async def check_certificate_expiration() -> None:
    async with JobExecutionContext(
        job_id="certificate_expiration_check",
        job_name="SSL Certificate Expiration Check",
        severity=JobSeverity.HIGH,
    ) as ctx:
        logger.info("Starting certificate expiration check")

        from .certificate_monitor_service import run_certificate_check

        summary = await run_certificate_check()

        for key in ("total_checked", "valid", "warning", "critical", "expired", "errors"):
            ctx.add_metric(key, summary.get(key, 0))
        ctx.items_processed = summary.get("total_checked", 0)
        ctx.items_succeeded = summary.get("valid", 0)
        logger.info(
            "Certificate expiration check completed",
            extra={
                "total_checked": summary["total_checked"],
                "valid": summary["valid"],
                "warning": summary["warning"],
                "critical": summary["critical"],
                "expired": summary["expired"],
                "errors": summary["errors"],
            },
        )


async def update_database_subscription_statuses() -> None:
    async with JobExecutionContext(
        job_id="database_subscription_status_update",
        job_name="Database Subscription Status Update",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        logger.info("Starting database subscription status update job")
        updated = 0
        total = 0

        async with AsyncSessionLocal() as db:
            from ...models.database_subscription import (
                DatabaseSubscription,
                SubscriptionStatus,
            )

            today = date.today()

            # Get all subscriptions
            result = await db.execute(select(DatabaseSubscription))
            subscriptions = result.scalars().all()
            total = len(subscriptions)

            for sub in subscriptions:
                old_status = sub.status
                new_status = old_status

                if sub.subscription_end < today:
                    new_status = SubscriptionStatus.EXPIRED.value
                elif sub.trial_end and sub.trial_end >= today:
                    new_status = SubscriptionStatus.TRIAL.value
                elif sub.subscription_start > today:
                    new_status = SubscriptionStatus.PENDING.value
                elif sub.is_expiring_soon:
                    new_status = SubscriptionStatus.EXPIRING_SOON.value
                else:
                    new_status = SubscriptionStatus.ACTIVE.value

                if old_status != new_status:
                    sub.status = new_status
                    updated += 1
                    logger.debug(
                        f"Updated subscription {sub.id} status: {old_status} -> {new_status}"
                    )

            await db.commit()

        ctx.add_metric("subscriptions_updated", updated)
        ctx.add_metric("subscriptions_total", total)
        ctx.items_processed = total
        ctx.items_succeeded = total
        logger.info(
            "Database subscription status update completed",
            extra={"subscriptions_updated": updated},
        )
