# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.branch_resolver import label_to_branch_id
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.email import send_email, COLORS
from ..core.logging import get_logger
from ..models.outreach import (
    OutreachPartner, OutreachVisit, OutreachDeposit, BulkCheckout,
    InstitutionalCard, InstitutionalCheckout, OutreachStatistics,
    OutreachPartnerStatus, VisitStatus, BulkCheckoutStatus, DepositStatus,
    InstitutionalCardStatus
)
from ..models.usage_statistics import ProgramStatistics
from ..models.user import User

settings = get_settings()
logger = get_logger(__name__)


async def generate_monthly_outreach_statistics(
    db: AsyncSession,
    period_start: date,
    period_end: date,
    branch_id: Optional[int] = None,
    generated_by_id: Optional[int] = None
) -> OutreachStatistics:
    logger.info(f"Generating outreach statistics for {period_start} to {period_end}")

    # Partner statistics
    total_partners_query = select(func.count()).select_from(OutreachPartner)
    total_partners = (await db.execute(total_partners_query)).scalar() or 0

    active_partners_query = select(func.count()).select_from(OutreachPartner).where(
        OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value
    )
    active_partners = (await db.execute(active_partners_query)).scalar() or 0

    new_partners_query = select(func.count()).select_from(OutreachPartner).where(
        func.date(OutreachPartner.partnership_start_date) >= period_start,
        func.date(OutreachPartner.partnership_start_date) <= period_end
    )
    new_partners = (await db.execute(new_partners_query)).scalar() or 0

    # Partners by type
    partners_by_type_query = select(
        OutreachPartner.partner_type,
        func.count(OutreachPartner.id)
    ).group_by(OutreachPartner.partner_type)
    partners_by_type_result = await db.execute(partners_by_type_query)
    partners_by_type = {row[0]: row[1] for row in partners_by_type_result.fetchall()}

    # Visit statistics
    total_visits_query = select(func.count()).select_from(OutreachVisit).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end
    )
    total_visits = (await db.execute(total_visits_query)).scalar() or 0

    completed_visits_query = select(func.count()).select_from(OutreachVisit).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.COMPLETED.value
    )
    visits_completed = (await db.execute(completed_visits_query)).scalar() or 0

    cancelled_visits_query = select(func.count()).select_from(OutreachVisit).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.CANCELLED.value
    )
    visits_cancelled = (await db.execute(cancelled_visits_query)).scalar() or 0

    attendees_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.COMPLETED.value
    )
    total_attendees = (await db.execute(attendees_query)).scalar() or 0

    # Visits by type
    visits_by_type_query = select(
        OutreachVisit.visit_type,
        func.count(OutreachVisit.id)
    ).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end
    ).group_by(OutreachVisit.visit_type)
    visits_by_type_result = await db.execute(visits_by_type_query)
    visits_by_type = {row[0]: row[1] for row in visits_by_type_result.fetchall()}

    # Bulk checkout statistics
    bulk_created_query = select(func.count()).select_from(BulkCheckout).where(
        BulkCheckout.checkout_date >= period_start,
        BulkCheckout.checkout_date <= period_end
    )
    bulk_checkouts_created = (await db.execute(bulk_created_query)).scalar() or 0

    bulk_returned_query = select(func.count()).select_from(BulkCheckout).where(
        BulkCheckout.returned_date >= period_start,
        BulkCheckout.returned_date <= period_end
    )
    bulk_checkouts_returned = (await db.execute(bulk_returned_query)).scalar() or 0

    bulk_items_out_query = select(func.sum(BulkCheckout.total_items)).where(
        BulkCheckout.checkout_date >= period_start,
        BulkCheckout.checkout_date <= period_end
    )
    bulk_items_checked_out = (await db.execute(bulk_items_out_query)).scalar() or 0

    bulk_items_ret_query = select(func.sum(BulkCheckout.items_returned)).where(
        BulkCheckout.returned_date >= period_start,
        BulkCheckout.returned_date <= period_end
    )
    bulk_items_returned = (await db.execute(bulk_items_ret_query)).scalar() or 0

    bulk_items_lost_query = select(func.sum(BulkCheckout.items_lost)).where(
        BulkCheckout.checkout_date >= period_start,
        BulkCheckout.checkout_date <= period_end
    )
    bulk_items_lost = (await db.execute(bulk_items_lost_query)).scalar() or 0

    # Institutional card statistics
    cards_active_query = select(func.count()).select_from(InstitutionalCard).where(
        InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value
    )
    institutional_cards_active = (await db.execute(cards_active_query)).scalar() or 0

    cards_issued_query = select(func.count()).select_from(InstitutionalCard).where(
        InstitutionalCard.issued_date >= period_start,
        InstitutionalCard.issued_date <= period_end
    )
    institutional_cards_issued = (await db.execute(cards_issued_query)).scalar() or 0

    inst_checkouts_query = select(func.count()).select_from(InstitutionalCheckout).where(
        func.date(InstitutionalCheckout.checked_out_at) >= period_start,
        func.date(InstitutionalCheckout.checked_out_at) <= period_end
    )
    institutional_checkouts = (await db.execute(inst_checkouts_query)).scalar() or 0

    # Deposit statistics
    deposits_collected_query = select(func.sum(OutreachDeposit.amount)).where(
        OutreachDeposit.collected_date >= period_start,
        OutreachDeposit.collected_date <= period_end
    )
    deposits_collected = (await db.execute(deposits_collected_query)).scalar() or 0.0

    deposits_refunded_query = select(func.sum(OutreachDeposit.amount_refunded)).where(
        OutreachDeposit.refund_date >= period_start,
        OutreachDeposit.refund_date <= period_end
    )
    deposits_refunded = (await db.execute(deposits_refunded_query)).scalar() or 0.0

    deposits_applied_query = select(func.sum(OutreachDeposit.amount_applied)).where(
        OutreachDeposit.collected_date >= period_start,
        OutreachDeposit.collected_date <= period_end
    )
    deposits_applied = (await db.execute(deposits_applied_query)).scalar() or 0.0

    # Impact metrics
    new_cards_query = select(func.sum(OutreachVisit.new_cards_issued)).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.COMPLETED.value
    )
    new_cards_from_outreach = (await db.execute(new_cards_query)).scalar() or 0

    # Check for existing record
    existing_query = select(OutreachStatistics).where(
        OutreachStatistics.period_start == period_start,
        OutreachStatistics.period_end == period_end,
        OutreachStatistics.branch_id == branch_id
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()

    if existing:
        # Update existing record
        stats = existing
    else:
        # Create new record
        stats = OutreachStatistics(
            period_start=period_start,
            period_end=period_end,
            branch_id=branch_id,
        )
        db.add(stats)

    # Update all fields
    stats.total_partners = total_partners
    stats.active_partners = active_partners
    stats.new_partners = new_partners
    stats.partners_by_type = partners_by_type
    stats.total_visits = total_visits
    stats.visits_completed = visits_completed
    stats.visits_cancelled = visits_cancelled
    stats.total_attendees = total_attendees
    stats.visits_by_type = visits_by_type
    stats.bulk_checkouts_created = bulk_checkouts_created
    stats.bulk_checkouts_returned = bulk_checkouts_returned
    stats.bulk_items_checked_out = bulk_items_checked_out
    stats.bulk_items_returned = bulk_items_returned
    stats.bulk_items_lost = bulk_items_lost
    stats.institutional_cards_active = institutional_cards_active
    stats.institutional_cards_issued = institutional_cards_issued
    stats.institutional_checkouts = institutional_checkouts
    stats.deposits_collected = float(deposits_collected)
    stats.deposits_refunded = float(deposits_refunded)
    stats.deposits_applied_to_fines = float(deposits_applied)
    stats.new_cards_from_outreach = new_cards_from_outreach
    stats.generated_at = datetime.now(timezone.utc)
    stats.generated_by_id = generated_by_id

    await db.commit()
    await db.refresh(stats)

    logger.info(
        "Generated outreach statistics",
        extra={
            "period_start": str(period_start),
            "period_end": str(period_end),
            "total_visits": total_visits,
            "total_attendees": total_attendees,
        }
    )

    return stats


async def sync_outreach_to_program_statistics(
    db: AsyncSession,
    period_start: date,
    period_end: date,
    branch_location: Optional[str] = None
) -> None:
    # Get outreach visit counts
    visits_query = select(func.count()).select_from(OutreachVisit).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.COMPLETED.value
    )
    outreach_count = (await db.execute(visits_query)).scalar() or 0

    # Get total attendance
    attendance_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        OutreachVisit.scheduled_date >= period_start,
        OutreachVisit.scheduled_date <= period_end,
        OutreachVisit.status == VisitStatus.COMPLETED.value
    )
    outreach_attendance = (await db.execute(attendance_query)).scalar() or 0

    # Resolve missing branch side via canonical map.
    if branch_id is None and branch_location is not None:
        branch_id = label_to_branch_id(branch_location)

    # Find or create ProgramStatistics record (prefer branch_id).
    if branch_id is not None:
        stats_query = select(ProgramStatistics).where(
            ProgramStatistics.period_start == period_start,
            ProgramStatistics.period_end == period_end,
            ProgramStatistics.branch_id == branch_id,
        )
    else:
        stats_query = select(ProgramStatistics).where(
            ProgramStatistics.period_start == period_start,
            ProgramStatistics.period_end == period_end,
            ProgramStatistics.branch_location == branch_location,
        )
    stats = (await db.execute(stats_query)).scalar_one_or_none()

    if stats:
        stats.outreach_programs_count = outreach_count
        stats.outreach_program_attendance = outreach_attendance
        await db.commit()

        logger.info(
            "Synced outreach to program statistics",
            extra={
                "outreach_count": outreach_count,
                "outreach_attendance": outreach_attendance,
            }
        )


async def send_bulk_checkout_overdue_notifications(db: AsyncSession) -> int:
    today = date.today()
    notifications_sent = 0

    # Find overdue bulk checkouts
    query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner)
    ).where(
        BulkCheckout.status == BulkCheckoutStatus.ACTIVE.value,
        BulkCheckout.due_date < today
    )

    result = await db.execute(query)
    overdue_checkouts = result.scalars().all()

    for checkout in overdue_checkouts:
        try:
            # Mark as overdue
            checkout.status = BulkCheckoutStatus.OVERDUE.value

            # Send notification if partner has email
            if checkout.requestor_email:
                days_overdue = (today - checkout.due_date).days
                success = await _send_bulk_checkout_overdue_email(
                    checkout, days_overdue
                )
                if success:
                    notifications_sent += 1

        except Exception as e:
            logger.error(
                f"Error processing overdue bulk checkout {checkout.id}: {e}",
                exc_info=True
            )
            continue

    await db.commit()

    logger.info(
        "Processed overdue bulk checkouts",
        extra={
            "overdue_count": len(overdue_checkouts),
            "notifications_sent": notifications_sent,
        }
    )

    return notifications_sent


async def _send_bulk_checkout_overdue_email(checkout: BulkCheckout, days_overdue: int) -> bool:
    subject = f"Overdue Library Materials: {checkout.checkout_name}"

    items_outstanding = checkout.total_items - checkout.items_returned - checkout.items_lost

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Library Materials Overdue</h2>
        <p>Dear {checkout.requestor_name},</p>
        <p>The following bulk checkout is now <strong>{days_overdue} day(s) overdue</strong>:</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">{checkout.checkout_name}</strong>
            <br><span style="color: {COLORS['body']};">Due Date: {checkout.due_date.strftime('%B %d, %Y')}</span>
            <br><span style="color: {COLORS['body']};">Items Outstanding: {items_outstanding}</span>
        </div>
        <p>Please return the materials as soon as possible to avoid any fees.</p>
        <p>If you have questions, please contact the library.</p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(checkout.requestor_email, subject, html_content)
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash outreach flow
        logger.error(f"Failed to send bulk checkout overdue email: {e}")
        return False


async def send_visit_reminders(db: AsyncSession) -> int:
    tomorrow = date.today() + timedelta(days=1)
    reminders_sent = 0

    # Find visits scheduled for tomorrow
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner),
        selectinload(OutreachVisit.lead_staff)
    ).where(
        OutreachVisit.scheduled_date == tomorrow,
        OutreachVisit.status.in_([
            VisitStatus.SCHEDULED.value,
            VisitStatus.CONFIRMED.value
        ])
    )

    result = await db.execute(query)
    upcoming_visits = result.scalars().all()

    for visit in upcoming_visits:
        try:
            # Send to lead staff
            if visit.lead_staff and visit.lead_staff.email:
                success = await _send_visit_reminder_email(
                    visit,
                    visit.lead_staff.email,
                    visit.lead_staff.first_name,
                    is_staff=True
                )
                if success:
                    reminders_sent += 1

            # Send to partner primary contact
            if visit.partner and visit.partner.primary_contact_email:
                success = await _send_visit_reminder_email(
                    visit,
                    visit.partner.primary_contact_email,
                    visit.partner.primary_contact_name,
                    is_staff=False
                )
                if success:
                    reminders_sent += 1

        except Exception as e:
            logger.error(
                f"Error sending visit reminder for visit {visit.id}: {e}",
                exc_info=True
            )
            continue

    logger.info(
        "Sent visit reminders",
        extra={
            "visits_count": len(upcoming_visits),
            "reminders_sent": reminders_sent,
        }
    )

    return reminders_sent


async def _send_visit_reminder_email(
    visit: OutreachVisit,
    email: str,
    recipient_name: str,
    is_staff: bool
) -> bool:
    subject = f"Reminder: Outreach Visit Tomorrow - {visit.title}"

    role_text = "you are scheduled to lead" if is_staff else "the library is scheduled to visit"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Outreach Visit Reminder</h2>
        <p>Hi {recipient_name},</p>
        <p>This is a reminder that {role_text} an outreach visit tomorrow:</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">{visit.title}</strong>
            <br><span style="color: {COLORS['body']};">Date: {visit.scheduled_date.strftime('%A, %B %d, %Y')}</span>
            {f'<br><span style="color: {COLORS["body"]};">Time: {visit.scheduled_start_time} - {visit.scheduled_end_time}</span>' if visit.scheduled_start_time else ''}
            {f'<br><span style="color: {COLORS["body"]};">Location: {visit.location_name}</span>' if visit.location_name else ''}
            {f'<br><span style="color: {COLORS["body"]};">Room: {visit.location_room}</span>' if visit.location_room else ''}
            {f'<br><span style="color: {COLORS["body"]};">Expected Attendees: {visit.expected_attendees}</span>' if visit.expected_attendees else ''}
        </div>
        {f'<p><strong>Description:</strong> {visit.description}</p>' if visit.description else ''}
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(email, subject, html_content)
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash visit reminder flow
        logger.error(f"Failed to send visit reminder email: {e}")
        return False


async def send_deposit_expiry_warnings(db: AsyncSession) -> int:
    warning_date = date.today() + timedelta(days=7)
    warnings_sent = 0

    # Find deposits expiring in 7 days
    query = select(OutreachDeposit).options(
        selectinload(OutreachDeposit.partner)
    ).where(
        OutreachDeposit.status == DepositStatus.HELD.value,
        OutreachDeposit.expiry_date == warning_date
    )

    result = await db.execute(query)
    expiring_deposits = result.scalars().all()

    for deposit in expiring_deposits:
        try:
            if deposit.partner and deposit.partner.primary_contact_email:
                success = await _send_deposit_expiry_warning_email(deposit)
                if success:
                    warnings_sent += 1

        except Exception as e:
            logger.error(
                f"Error sending deposit expiry warning for deposit {deposit.id}: {e}",
                exc_info=True
            )
            continue

    logger.info(
        "Sent deposit expiry warnings",
        extra={
            "deposits_count": len(expiring_deposits),
            "warnings_sent": warnings_sent,
        }
    )

    return warnings_sent


async def _send_deposit_expiry_warning_email(deposit: OutreachDeposit) -> bool:
    partner = deposit.partner
    subject = "Library Deposit Expiring Soon - Action Required"

    remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Deposit Expiry Warning</h2>
        <p>Dear {partner.primary_contact_name},</p>
        <p>Your library deposit is scheduled to expire in 7 days:</p>
        <div style="background-color: {COLORS['border']}; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong style="color: {COLORS['heading']};">Deposit Details</strong>
            <br><span style="color: {COLORS['body']};">Organization: {partner.name}</span>
            <br><span style="color: {COLORS['body']};">Original Amount: ${deposit.amount:.2f}</span>
            <br><span style="color: {COLORS['body']};">Remaining Balance: ${remaining:.2f}</span>
            <br><span style="color: {COLORS['body']};">Expiry Date: {deposit.expiry_date.strftime('%B %d, %Y')}</span>
        </div>
        <p>Please contact the library to arrange a refund of the remaining balance
           or to extend the deposit period.</p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(partner.primary_contact_email, subject, html_content)
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash deposit expiry flow
        logger.error(f"Failed to send deposit expiry warning email: {e}")
        return False


async def process_expired_institutional_cards(db: AsyncSession) -> int:
    today = date.today()
    cards_expired = 0

    # Find cards that should be expired
    query = select(InstitutionalCard).where(
        InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value,
        InstitutionalCard.expiry_date < today
    )

    result = await db.execute(query)
    expired_cards = result.scalars().all()

    for card in expired_cards:
        card.status = InstitutionalCardStatus.EXPIRED.value
        cards_expired += 1

    await db.commit()

    logger.info(f"Processed {cards_expired} expired institutional cards")

    return cards_expired
