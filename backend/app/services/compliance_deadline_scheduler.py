# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..core.logging import get_logger
from ..services.compliance_service import ComplianceService
from ..models.user import User, UserRole
from ..core.email import send_email
from .unified_scheduler import ScheduleType, get_scheduling_service

logger = get_logger(__name__)


async def check_compliance_deadlines() -> None:
    logger.info("Starting compliance deadline check")

    try:
        async with AsyncSessionLocal() as db:
            # Get all organizations (assuming multi-tenant setup)
            # For now, we'll check for organization_id = 1
            # In production, this should iterate through all organizations
            organization_id = 1

            # Check and create deadline alerts
            alerts = await ComplianceService.check_and_create_deadline_alerts(
                db=db,
                organization_id=organization_id
            )

            if alerts:
                logger.info(
                    f"Created {len(alerts)} compliance deadline alerts",
                    extra={"alert_count": len(alerts), "org_id": organization_id}
                )

                # Get staff to notify (Directors, Compliance Officers)
                staff_result = await db.execute(
                    select(User).where(
                        User.role.in_([UserRole.DIRECTOR, UserRole.STAFF])
                    )
                )
                staff = staff_result.scalars().all()

                # Send notifications for critical alerts
                critical_alerts = [a for a in alerts if (a.deadline_date - date.today()).days <= 7]
                if critical_alerts and staff:
                    await _send_alert_notifications(
                        db=db,
                        alerts=critical_alerts,
                        staff=staff,
                        organization_id=organization_id
                    )
            else:
                logger.info(
                    "No new compliance deadline alerts needed",
                    extra={"org_id": organization_id}
                )

    except Exception as e:
        logger.error(f"Error in compliance deadline check: {e}", exc_info=True)


async def _send_alert_notifications(
    db: AsyncSession,
    alerts: list,
    staff: list,
    organization_id: int
) -> None:
    try:
        for alert in alerts:
            days_until = (alert.deadline_date - date.today()).days
            alert_priority = "CRITICAL" if days_until <= 0 else "URGENT" if days_until <= 7 else "HIGH"

            # Build alert details
            alert_details = f"""
{alert_priority}: {alert.alert_type.replace('_', ' ').title()}

Deadline: {alert.deadline_date.strftime('%B %d, %Y')}
Days Until Deadline: {days_until}
Source: {alert.source_model}

This is an automated compliance deadline notification. Please take action to ensure compliance.
"""

            # Send email to each staff member
            for staff_member in staff:
                try:
                    await send_email(
                        to_email=staff_member.email,
                        subject=f"[{alert_priority}] Compliance Deadline Alert - {alert.alert_type}",
                        html_content=alert_details,
                    )

                    # Mark alert as sent
                    alert.first_alert_sent = date.today()
                    alert.last_alert_sent = date.today()
                    alert.reminder_alerts_sent += 1

                except Exception as e:  # noqa: BLE001 - per-iteration boundary — single staff email failure must not block other recipients
                    logger.error(
                        f"Error sending alert email to {staff_member.email}: {e}",
                        extra={"alert_id": alert.id, "user_id": staff_member.id}
                    )

            await db.commit()

    except Exception as e:
        logger.error(
            f"Error in alert notification process: {e}",
            exc_info=True
        )


async def escalate_overdue_compliance_items() -> None:
    logger.info("Starting overdue compliance escalation check")

    try:
        async with AsyncSessionLocal() as db:
            organization_id = 1

            # Get overdue items
            overdue_inspections = await ComplianceService.check_safety_inspections_overdue(
                db=db,
                organization_id=organization_id
            )

            overdue_certifications = await ComplianceService.check_staff_certifications_expiring(
                db=db,
                organization_id=organization_id,
                days_until=0  # Only truly expired
            )

            overdue_policies = await ComplianceService.check_policy_reviews_overdue(
                db=db,
                organization_id=organization_id
            )

            total_overdue = (
                len(overdue_inspections) +
                len(overdue_certifications) +
                len(overdue_policies)
            )

            if total_overdue > 0:
                logger.warning(
                    f"Found {total_overdue} overdue compliance items",
                    extra={
                        "org_id": organization_id,
                        "overdue_inspections": len(overdue_inspections),
                        "overdue_certifications": len(overdue_certifications),
                        "overdue_policies": len(overdue_policies)
                    }
                )

                # Get director/admin emails
                result = await db.execute(
                    select(User).where(
                        User.role == UserRole.DIRECTOR
                    )
                )
                directors = result.scalars().all()

                # Send escalation email
                if directors:
                    escalation_summary = f"""
CRITICAL: {total_overdue} Overdue Compliance Items

Overdue Safety Inspections: {len(overdue_inspections)}
Expired Staff Certifications: {len(overdue_certifications)}
Overdue Policy Reviews: {len(overdue_policies)}

Please review and address these items immediately to maintain compliance.
"""

                    for director in directors:
                        try:
                            await send_email(
                                to_email=director.email,
                                subject="ESCALATION: Overdue Compliance Items Require Immediate Action",
                                html_content=escalation_summary,
                            )
                        except Exception as e:  # noqa: BLE001 - per-iteration boundary — single director email failure must not block other recipients
                            logger.error(
                                f"Error sending escalation email to director: {e}",
                                extra={"director_id": director.id}
                            )

            else:
                logger.info(
                    "No overdue compliance items found",
                    extra={"org_id": organization_id}
                )

    except Exception as e:
        logger.error(
            f"Error in compliance escalation check: {e}",
            exc_info=True
        )


def initialize_compliance_deadline_jobs(scheduler_instance) -> None:
    from apscheduler.triggers.cron import CronTrigger

    unified_scheduler = get_scheduling_service()

    def _add_job(func, trigger, job_id, job_type, name):
        scheduler_instance.add_job(
            func,
            trigger,
            id=job_id,
            name=name,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        try:
            if unified_scheduler and unified_scheduler.scheduler:
                unified_scheduler.add_job(
                    func,
                    trigger,
                    job_id,
                    job_type,
                    name,
                    misfire_grace_time=3600,
                )
        except Exception as e:  # noqa: BLE001 - scheduler job boundary — registration failure must not crash scheduler
            logger.warning(f"Failed to register job {job_id} with unified scheduler: {e}")

    # Compliance deadline check at 8 AM
    _add_job(
        check_compliance_deadlines,
        CronTrigger(hour=8, minute=0),
        "compliance_deadline_check",
        ScheduleType.COMPLIANCE_DEADLINE,
        "Compliance Deadline Check",
    )

    # Compliance escalation check (every Monday at 9 AM)
    _add_job(
        escalate_overdue_compliance_items,
        CronTrigger(day_of_week=0, hour=9, minute=0),
        "compliance_escalation_check",
        ScheduleType.COMPLIANCE_ESCALATION,
        "Compliance Escalation Check",
    )

    logger.info("Initialized compliance deadline scheduled jobs")
