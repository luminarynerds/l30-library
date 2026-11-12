# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff/Admin Outreach Management API endpoints.

Provides administrative operations for outreach program management including:
- Bulk operations on partners, visits, and checkouts
- Data export in CSV/Excel formats
- Statistics regeneration
- Audit and compliance reports
"""

import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner, OutreachPartnerContact, OutreachDeposit,
    OutreachVisit, InstitutionalCard, BulkCheckout, BulkCheckoutItem,
    OutreachStatistics, OutreachPartnerStatus, VisitStatus, BulkCheckoutStatus,
    DepositStatus, InstitutionalCardStatus
)
from ....models.user import User
from ....schemas.outreach import (
    OutreachPartnerResponse, OutreachVisitResponse, BulkCheckoutResponse,
    OutreachDepositResponse, InstitutionalCardResponse,
    OutreachStatisticsResponse, OutreachReportResponse
)
from ..auth import get_current_user
from ..dependencies import require_staff, require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/outreach", tags=["staff-outreach"])


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/partners/bulk-status-update")
async def bulk_update_partner_status(
    partner_ids: list[int],
    new_status: OutreachPartnerStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk update status for multiple partners (Admin only)."""
    if len(partner_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per bulk operation")
    query = select(OutreachPartner).where(OutreachPartner.id.in_(partner_ids))
    result = await db.execute(query)
    partners = result.scalars().all()

    updated_count = 0
    for partner in partners:
        partner.status = new_status.value
        updated_count += 1

    await db.commit()

    logger.info(
        f"Bulk updated {updated_count} partner statuses to {new_status.value}",
        extra={"user_id": current_user.id, "partner_ids": partner_ids}
    )

    return {"updated_count": updated_count, "new_status": new_status.value}


@router.post("/visits/bulk-cancel")
async def bulk_cancel_visits(
    visit_ids: list[int],
    cancellation_reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Bulk cancel multiple scheduled visits."""
    if len(visit_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per bulk operation")
    query = select(OutreachVisit).where(
        OutreachVisit.id.in_(visit_ids),
        OutreachVisit.status.in_([VisitStatus.SCHEDULED.value, VisitStatus.CONFIRMED.value])
    )
    result = await db.execute(query)
    visits = result.scalars().all()

    cancelled_count = 0
    for visit in visits:
        visit.status = VisitStatus.CANCELLED.value
        visit.cancellation_reason = cancellation_reason
        visit.cancelled_by_id = current_user.id
        visit.cancelled_at = datetime.now(timezone.utc)
        cancelled_count += 1

    await db.commit()

    logger.info(
        f"Bulk cancelled {cancelled_count} visits",
        extra={"user_id": current_user.id, "visit_ids": visit_ids}
    )

    return {"cancelled_count": cancelled_count}


@router.post("/bulk-checkouts/bulk-extend")
async def bulk_extend_due_dates(
    checkout_ids: list[int],
    extension_days: int = Query(..., ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Bulk extend due dates for multiple bulk checkouts."""
    query = select(BulkCheckout).where(
        BulkCheckout.id.in_(checkout_ids),
        BulkCheckout.status.in_([
            BulkCheckoutStatus.ACTIVE.value,
            BulkCheckoutStatus.OVERDUE.value
        ])
    )
    result = await db.execute(query)
    checkouts = result.scalars().all()

    extended_count = 0
    for checkout in checkouts:
        checkout.due_date = checkout.due_date + timedelta(days=extension_days)
        if checkout.status == BulkCheckoutStatus.OVERDUE.value:
            # Reset to active if extension brings it back in compliance
            if checkout.due_date >= date.today():
                checkout.status = BulkCheckoutStatus.ACTIVE.value
        extended_count += 1

    await db.commit()

    logger.info(
        f"Bulk extended {extended_count} checkout due dates by {extension_days} days",
        extra={"user_id": current_user.id, "checkout_ids": checkout_ids}
    )

    return {"extended_count": extended_count, "extension_days": extension_days}


@router.post("/deposits/bulk-forfeit")
async def bulk_forfeit_deposits(
    deposit_ids: list[int],
    reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk forfeit expired deposits (Admin only)."""
    query = select(OutreachDeposit).where(
        OutreachDeposit.id.in_(deposit_ids),
        OutreachDeposit.status == DepositStatus.HELD.value
    )
    result = await db.execute(query)
    deposits = result.scalars().all()

    forfeited_count = 0
    total_amount = 0.0
    for deposit in deposits:
        remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded
        deposit.status = DepositStatus.FORFEITED.value
        deposit.refund_reason = f"Forfeited: {reason}"
        total_amount += remaining
        forfeited_count += 1

    await db.commit()

    logger.info(
        f"Bulk forfeited {forfeited_count} deposits totaling ${total_amount:.2f}",
        extra={"user_id": current_user.id, "deposit_ids": deposit_ids}
    )

    return {
        "forfeited_count": forfeited_count,
        "total_amount_forfeited": total_amount
    }


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export/partners")
async def export_partners_csv(
    status: Optional[OutreachPartnerStatus] = None,
    partner_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Export partners to CSV format."""
    query = select(OutreachPartner)

    if status:
        query = query.where(OutreachPartner.status == status.value)
    if partner_type:
        query = query.where(OutreachPartner.partner_type == partner_type)

    query = query.order_by(OutreachPartner.name)
    result = await db.execute(query)
    partners = result.scalars().all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Name", "Type", "Status", "Address", "City", "State", "Zip",
        "Primary Contact", "Contact Email", "Contact Phone",
        "School Level", "School District", "Student Count", "Teacher Count",
        "Partnership Start", "Partnership End",
        "Allows Bulk Checkout", "Allows Institutional Card",
        "Requires Deposit", "Default Deposit", "Checkout Limit", "Loan Period Days",
        "Created At"
    ])

    # Data rows
    for p in partners:
        writer.writerow([
            p.id, p.name, p.partner_type, p.status,
            p.address_line1, p.city, p.state, p.zip_code,
            p.primary_contact_name, p.primary_contact_email, p.primary_contact_phone,
            p.school_level, p.school_district, p.student_count, p.teacher_count,
            p.partnership_start_date, p.partnership_end_date,
            p.allows_bulk_checkout, p.allows_institutional_card,
            p.requires_deposit, p.default_deposit_amount, p.checkout_limit, p.loan_period_days,
            getattr(p, "created_at", None).isoformat() if getattr(p, "created_at", None) else ""
        ])

    output.seek(0)

    logger.info(f"Exported {len(partners)} partners to CSV", extra={"user_id": current_user.id})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=outreach_partners_{date.today()}.csv"}
    )


@router.get("/export/visits")
async def export_visits_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[VisitStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Export visits to CSV format."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.partner),
        selectinload(OutreachVisit.lead_staff)
    )

    if start_date:
        query = query.where(OutreachVisit.scheduled_date >= start_date)
    if end_date:
        query = query.where(OutreachVisit.scheduled_date <= end_date)
    if status:
        query = query.where(OutreachVisit.status == status.value)

    query = query.order_by(OutreachVisit.scheduled_date.desc())
    result = await db.execute(query)
    visits = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Partner", "Visit Type", "Status", "Title",
        "Scheduled Date", "Start Time", "End Time",
        "Location", "Room",
        "Expected Attendees", "Actual Attendees", "Age Group",
        "Lead Staff",
        "Items Delivered", "Items Picked Up",
        "New Cards Issued", "Books Checked Out",
        "Partner Rating", "Follow Up Needed",
        "Created At"
    ])

    for v in visits:
        writer.writerow([
            v.id,
            v.partner.name if v.partner else "",
            v.visit_type, v.status, v.title,
            v.scheduled_date, v.scheduled_start_time, v.scheduled_end_time,
            v.location_name, v.location_room,
            v.expected_attendees, v.actual_attendees, v.age_group,
            v.lead_staff.full_name if v.lead_staff else "",
            v.items_delivered, v.items_picked_up,
            v.new_cards_issued, v.books_checked_out,
            v.partner_rating, v.follow_up_needed,
            getattr(v, "created_at", None).isoformat() if getattr(v, "created_at", None) else ""
        ])

    output.seek(0)

    logger.info(f"Exported {len(visits)} visits to CSV", extra={"user_id": current_user.id})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=outreach_visits_{date.today()}.csv"}
    )


@router.get("/export/bulk-checkouts")
async def export_bulk_checkouts_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[BulkCheckoutStatus] = None,
    include_items: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Export bulk checkouts to CSV format."""
    query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner),
        selectinload(BulkCheckout.items) if include_items else selectinload(BulkCheckout.partner)
    )

    if start_date:
        query = query.where(BulkCheckout.checkout_date >= start_date)
    if end_date:
        query = query.where(BulkCheckout.checkout_date <= end_date)
    if status:
        query = query.where(BulkCheckout.status == status.value)

    query = query.order_by(BulkCheckout.checkout_date.desc())
    result = await db.execute(query)
    checkouts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    if include_items:
        writer.writerow([
            "Checkout ID", "Partner", "Checkout Name", "Status",
            "Requestor", "Classroom", "Grade Level",
            "Checkout Date", "Due Date", "Returned Date",
            "Item Barcode", "Item Title", "Item Status", "Item Returned At"
        ])

        for c in checkouts:
            for item in c.items:
                writer.writerow([
                    c.id, c.partner.name if c.partner else "", c.checkout_name, c.status,
                    c.requestor_name, c.classroom_name, c.grade_level,
                    c.checkout_date, c.due_date, c.returned_date,
                    item.barcode, item.title, item.status,
                    item.returned_at.isoformat() if item.returned_at else ""
                ])
    else:
        writer.writerow([
            "ID", "Partner", "Checkout Name", "Status",
            "Requestor", "Email", "Phone", "Classroom", "Grade Level",
            "Checkout Date", "Due Date", "Returned Date",
            "Total Items", "Returned", "Lost", "Damaged",
            "Deposit Required", "Deposit Amount", "Deposit Collected",
            "Created At"
        ])

        for c in checkouts:
            writer.writerow([
                c.id, c.partner.name if c.partner else "", c.checkout_name, c.status,
                c.requestor_name, c.requestor_email, c.requestor_phone,
                c.classroom_name, c.grade_level,
                c.checkout_date, c.due_date, c.returned_date,
                c.total_items, c.items_returned, c.items_lost, c.items_damaged,
                c.deposit_required, c.deposit_amount, c.deposit_collected,
                getattr(c, "created_at", None).isoformat() if getattr(c, "created_at", None) else ""
            ])

    output.seek(0)

    logger.info(f"Exported {len(checkouts)} bulk checkouts to CSV", extra={"user_id": current_user.id})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bulk_checkouts_{date.today()}.csv"}
    )


@router.get("/export/deposits")
async def export_deposits_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[DepositStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Export deposits to CSV format."""
    query = select(OutreachDeposit).options(
        selectinload(OutreachDeposit.partner),
        selectinload(OutreachDeposit.collected_by),
        selectinload(OutreachDeposit.refunded_by)
    )

    if start_date:
        query = query.where(OutreachDeposit.collected_date >= start_date)
    if end_date:
        query = query.where(OutreachDeposit.collected_date <= end_date)
    if status:
        query = query.where(OutreachDeposit.status == status.value)

    query = query.order_by(OutreachDeposit.collected_date.desc())
    result = await db.execute(query)
    deposits = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Partner", "Deposit Type", "Status",
        "Amount", "Amount Applied", "Amount Refunded", "Balance",
        "Payment Method", "Payment Reference", "Receipt Number",
        "Collected Date", "Refund Date", "Expiry Date",
        "Collected By", "Refunded By",
        "Notes", "Refund Reason"
    ])

    for d in deposits:
        balance = d.amount - d.amount_applied - d.amount_refunded
        writer.writerow([
            d.id, d.partner.name if d.partner else "", d.deposit_type, d.status,
            d.amount, d.amount_applied, d.amount_refunded, balance,
            d.payment_method, d.payment_reference, d.receipt_number,
            d.collected_date, d.refund_date, d.expiry_date,
            d.collected_by.full_name if d.collected_by else "",
            d.refunded_by.full_name if d.refunded_by else "",
            d.notes, d.refund_reason
        ])

    output.seek(0)

    logger.info(f"Exported {len(deposits)} deposits to CSV", extra={"user_id": current_user.id})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=outreach_deposits_{date.today()}.csv"}
    )


@router.get("/export/institutional-cards")
async def export_institutional_cards_csv(
    status: Optional[InstitutionalCardStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Export institutional cards to CSV format."""
    query = select(InstitutionalCard).options(
        selectinload(InstitutionalCard.partner),
        selectinload(InstitutionalCard.issued_by)
    )

    if status:
        query = query.where(InstitutionalCard.status == status.value)

    query = query.order_by(InstitutionalCard.card_name)
    result = await db.execute(query)
    cards = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Card Number", "Card Name", "Status", "Partner",
        "Checkout Limit", "Hold Limit", "Loan Period Days", "Renewal Limit",
        "Exempt From Fines", "Fine Cap",
        "Deposit Required", "Deposit Amount",
        "Issued Date", "Expiry Date",
        "Total Checkouts", "Current Checkouts", "Current Holds", "Current Fines",
        "Issued By"
    ])

    for c in cards:
        writer.writerow([
            c.id, c.card_number, c.card_name, c.status,
            c.partner.name if c.partner else "",
            c.checkout_limit, c.hold_limit, c.loan_period_days, c.renewal_limit,
            c.exempt_from_fines, c.fine_cap,
            c.deposit_required, c.deposit_amount,
            c.issued_date, c.expiry_date,
            c.total_checkouts, c.current_checkouts, c.current_holds, c.current_fines,
            c.issued_by.full_name if c.issued_by else ""
        ])

    output.seek(0)

    logger.info(f"Exported {len(cards)} institutional cards to CSV", extra={"user_id": current_user.id})

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=institutional_cards_{date.today()}.csv"}
    )


# =============================================================================
# Statistics & Reports
# =============================================================================

@router.post("/statistics/regenerate")
async def regenerate_statistics(
    period_start: date,
    period_end: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Regenerate outreach statistics for a specific period (Admin only)."""
    from ....services.outreach_service import (
        generate_monthly_outreach_statistics,
        sync_outreach_to_program_statistics
    )

    stats = await generate_monthly_outreach_statistics(
        db, period_start, period_end, generated_by_id=current_user.id
    )

    await sync_outreach_to_program_statistics(db, period_start, period_end)

    logger.info(
        f"Regenerated outreach statistics for {period_start} to {period_end}",
        extra={"user_id": current_user.id}
    )

    return OutreachStatisticsResponse.model_validate(stats)


@router.get("/reports/partner-activity")
async def get_partner_activity_report(
    partner_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get detailed activity report for a specific partner."""
    # Default to last 12 months
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365)

    # Get partner
    partner_query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Visit statistics
    visits_query = select(OutreachVisit).where(
        OutreachVisit.partner_id == partner_id,
        OutreachVisit.scheduled_date >= start_date,
        OutreachVisit.scheduled_date <= end_date
    )
    visits_result = await db.execute(visits_query)
    visits = visits_result.scalars().all()

    completed_visits = [v for v in visits if v.status == VisitStatus.COMPLETED.value]
    total_attendees = sum(v.actual_attendees or 0 for v in completed_visits)
    total_cards_issued = sum(v.new_cards_issued or 0 for v in completed_visits)

    # Bulk checkout statistics
    checkouts_query = select(BulkCheckout).where(
        BulkCheckout.partner_id == partner_id,
        BulkCheckout.checkout_date >= start_date,
        BulkCheckout.checkout_date <= end_date
    )
    checkouts_result = await db.execute(checkouts_query)
    checkouts = checkouts_result.scalars().all()

    total_items_checked_out = sum(c.total_items for c in checkouts)
    total_items_returned = sum(c.items_returned for c in checkouts)
    total_items_lost = sum(c.items_lost for c in checkouts)

    # Deposit statistics
    deposits_query = select(OutreachDeposit).where(
        OutreachDeposit.partner_id == partner_id,
        OutreachDeposit.collected_date >= start_date,
        OutreachDeposit.collected_date <= end_date
    )
    deposits_result = await db.execute(deposits_query)
    deposits = deposits_result.scalars().all()

    total_deposits = sum(d.amount for d in deposits)
    total_refunds = sum(d.amount_refunded for d in deposits)
    total_applied = sum(d.amount_applied for d in deposits)

    # Institutional card statistics
    cards_query = select(InstitutionalCard).where(
        InstitutionalCard.partner_id == partner_id
    )
    cards_result = await db.execute(cards_query)
    cards = cards_result.scalars().all()

    total_card_checkouts = sum(c.total_checkouts for c in cards)

    return {
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "type": partner.partner_type,
            "status": partner.status
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "visits": {
            "total": len(visits),
            "completed": len(completed_visits),
            "cancelled": len([v for v in visits if v.status == VisitStatus.CANCELLED.value]),
            "total_attendees": total_attendees,
            "cards_issued": total_cards_issued,
            "average_attendance": total_attendees / len(completed_visits) if completed_visits else 0
        },
        "bulk_checkouts": {
            "total": len(checkouts),
            "items_checked_out": total_items_checked_out,
            "items_returned": total_items_returned,
            "items_lost": total_items_lost,
            "return_rate": (total_items_returned / total_items_checked_out * 100) if total_items_checked_out else 0
        },
        "deposits": {
            "total_collected": total_deposits,
            "total_refunded": total_refunds,
            "total_applied": total_applied,
            "net_held": total_deposits - total_refunds - total_applied
        },
        "institutional_cards": {
            "count": len(cards),
            "active": len([c for c in cards if c.status == InstitutionalCardStatus.ACTIVE.value]),
            "total_checkouts": total_card_checkouts
        }
    }


@router.get("/reports/overdue-summary")
async def get_overdue_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get summary of all overdue bulk checkouts."""
    today = date.today()

    query = select(BulkCheckout).options(
        selectinload(BulkCheckout.partner)
    ).where(
        BulkCheckout.status.in_([
            BulkCheckoutStatus.ACTIVE.value,
            BulkCheckoutStatus.OVERDUE.value
        ]),
        BulkCheckout.due_date < today
    ).order_by(BulkCheckout.due_date)

    result = await db.execute(query)
    overdue_checkouts = result.scalars().all()

    summary = []
    total_items_overdue = 0
    for checkout in overdue_checkouts:
        days_overdue = (today - checkout.due_date).days
        items_outstanding = checkout.total_items - checkout.items_returned - checkout.items_lost
        total_items_overdue += items_outstanding

        summary.append({
            "checkout_id": checkout.id,
            "checkout_name": checkout.checkout_name,
            "partner_name": checkout.partner.name if checkout.partner else "Unknown",
            "requestor": checkout.requestor_name,
            "requestor_email": checkout.requestor_email,
            "due_date": checkout.due_date.isoformat(),
            "days_overdue": days_overdue,
            "total_items": checkout.total_items,
            "items_returned": checkout.items_returned,
            "items_outstanding": items_outstanding
        })

    return {
        "total_overdue_checkouts": len(overdue_checkouts),
        "total_items_overdue": total_items_overdue,
        "checkouts": summary
    }


@router.get("/reports/deposit-summary")
async def get_deposit_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get summary of all held deposits."""
    query = select(OutreachDeposit).options(
        selectinload(OutreachDeposit.partner)
    ).where(
        OutreachDeposit.status == DepositStatus.HELD.value
    ).order_by(OutreachDeposit.expiry_date)

    result = await db.execute(query)
    deposits = result.scalars().all()

    today = date.today()
    total_held = 0.0
    expiring_soon = []
    expired = []

    for deposit in deposits:
        remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded
        total_held += remaining

        deposit_info = {
            "deposit_id": deposit.id,
            "partner_name": deposit.partner.name if deposit.partner else "Unknown",
            "amount": deposit.amount,
            "remaining": remaining,
            "collected_date": deposit.collected_date.isoformat(),
            "expiry_date": deposit.expiry_date.isoformat() if deposit.expiry_date else None
        }

        if deposit.expiry_date:
            days_until_expiry = (deposit.expiry_date - today).days
            if days_until_expiry < 0:
                expired.append({**deposit_info, "days_expired": abs(days_until_expiry)})
            elif days_until_expiry <= 30:
                expiring_soon.append({**deposit_info, "days_until_expiry": days_until_expiry})

    return {
        "total_deposits_held": len(deposits),
        "total_amount_held": total_held,
        "expired_deposits": expired,
        "expiring_within_30_days": expiring_soon
    }


# =============================================================================
# Audit & Compliance
# =============================================================================

@router.get("/audit/visit-completion-rate")
async def get_visit_completion_audit(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Audit visit completion rates by staff member."""
    query = select(OutreachVisit).options(
        selectinload(OutreachVisit.lead_staff)
    ).where(
        OutreachVisit.scheduled_date >= start_date,
        OutreachVisit.scheduled_date <= end_date
    )

    result = await db.execute(query)
    visits = result.scalars().all()

    # Group by staff
    staff_stats = {}
    for visit in visits:
        staff_id = visit.lead_staff_id or 0
        staff_name = visit.lead_staff.full_name if visit.lead_staff else "Unassigned"

        if staff_id not in staff_stats:
            staff_stats[staff_id] = {
                "staff_name": staff_name,
                "total": 0,
                "completed": 0,
                "cancelled": 0,
                "no_show": 0,
                "total_attendees": 0
            }

        staff_stats[staff_id]["total"] += 1

        if visit.status == VisitStatus.COMPLETED.value:
            staff_stats[staff_id]["completed"] += 1
            staff_stats[staff_id]["total_attendees"] += visit.actual_attendees or 0
        elif visit.status == VisitStatus.CANCELLED.value:
            staff_stats[staff_id]["cancelled"] += 1
        elif visit.status == VisitStatus.NO_SHOW.value:
            staff_stats[staff_id]["no_show"] += 1

    # Calculate completion rates
    audit_data = []
    for staff_id, stats in staff_stats.items():
        completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_attendance = (stats["total_attendees"] / stats["completed"]) if stats["completed"] > 0 else 0

        audit_data.append({
            "staff_id": staff_id if staff_id != 0 else None,
            "staff_name": stats["staff_name"],
            "total_visits": stats["total"],
            "completed": stats["completed"],
            "cancelled": stats["cancelled"],
            "no_show": stats["no_show"],
            "completion_rate": round(completion_rate, 1),
            "total_attendees": stats["total_attendees"],
            "avg_attendance": round(avg_attendance, 1)
        })

    # Sort by completion rate
    audit_data.sort(key=lambda x: x["completion_rate"], reverse=True)

    return {
        "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "staff_performance": audit_data
    }


@router.get("/audit/partner-engagement")
async def get_partner_engagement_audit(
    months: int = Query(default=12, le=36),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Audit partner engagement levels over time."""
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    # Get all active partners
    partners_query = select(OutreachPartner).where(
        OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value
    )
    partners_result = await db.execute(partners_query)
    partners = partners_result.scalars().all()

    engagement_data = []
    for partner in partners:
        # Count visits
        visits_query = select(func.count()).select_from(OutreachVisit).where(
            OutreachVisit.partner_id == partner.id,
            OutreachVisit.scheduled_date >= start_date,
            OutreachVisit.status == VisitStatus.COMPLETED.value
        )
        visit_count = (await db.execute(visits_query)).scalar() or 0

        # Count bulk checkouts
        checkouts_query = select(func.count()).select_from(BulkCheckout).where(
            BulkCheckout.partner_id == partner.id,
            BulkCheckout.checkout_date >= start_date
        )
        checkout_count = (await db.execute(checkouts_query)).scalar() or 0

        # Calculate engagement score
        engagement_score = visit_count * 10 + checkout_count * 5

        last_activity = None
        # Get last visit
        last_visit_query = select(OutreachVisit.scheduled_date).where(
            OutreachVisit.partner_id == partner.id,
            OutreachVisit.status == VisitStatus.COMPLETED.value
        ).order_by(OutreachVisit.scheduled_date.desc()).limit(1)
        last_visit = (await db.execute(last_visit_query)).scalar_one_or_none()

        if last_visit:
            last_activity = last_visit

        engagement_data.append({
            "partner_id": partner.id,
            "partner_name": partner.name,
            "partner_type": partner.partner_type,
            "visits_completed": visit_count,
            "bulk_checkouts": checkout_count,
            "engagement_score": engagement_score,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "days_since_activity": (end_date - last_activity).days if last_activity else None
        })

    # Sort by engagement score
    engagement_data.sort(key=lambda x: x["engagement_score"], reverse=True)

    # Categorize
    high_engagement = [p for p in engagement_data if p["engagement_score"] >= 50]
    medium_engagement = [p for p in engagement_data if 20 <= p["engagement_score"] < 50]
    low_engagement = [p for p in engagement_data if 0 < p["engagement_score"] < 20]
    no_engagement = [p for p in engagement_data if p["engagement_score"] == 0]

    return {
        "period_months": months,
        "total_partners": len(partners),
        "engagement_breakdown": {
            "high": len(high_engagement),
            "medium": len(medium_engagement),
            "low": len(low_engagement),
            "none": len(no_engagement)
        },
        "partners": engagement_data
    }


# =============================================================================
# Notification Templates
# =============================================================================

@router.get("/notification-templates")
async def list_notification_templates(
    notification_type: Optional[str] = None,
    channel: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List notification templates with optional filtering."""
    from ....models.outreach import OutreachNotificationTemplate
    from ....schemas.outreach import (
        OutreachNotificationTemplateResponse,
        OutreachNotificationTemplateListResponse
    )

    query = select(OutreachNotificationTemplate)

    if notification_type:
        query = query.where(OutreachNotificationTemplate.notification_type == notification_type)
    if channel:
        query = query.where(OutreachNotificationTemplate.channel == channel)
    if is_active is not None:
        query = query.where(OutreachNotificationTemplate.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(OutreachNotificationTemplate.name).offset(offset).limit(limit)
    result = await db.execute(query)
    templates = result.scalars().all()

    return OutreachNotificationTemplateListResponse(
        templates=[OutreachNotificationTemplateResponse.model_validate(t) for t in templates],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/notification-templates", status_code=status.HTTP_201_CREATED)
async def create_notification_template(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new notification template (Admin only)."""
    from ....models.outreach import OutreachNotificationTemplate
    from ....schemas.outreach import (
        OutreachNotificationTemplateCreate,
        OutreachNotificationTemplateResponse
    )

    template_data = OutreachNotificationTemplateCreate(**data)

    template = OutreachNotificationTemplate(
        name=template_data.name,
        notification_type=template_data.notification_type,
        channel=template_data.channel,
        subject=template_data.subject,
        body=template_data.body,
        html_body=template_data.html_body,
        available_variables=template_data.available_variables,
        days_before_event=template_data.days_before_event,
        send_time=template_data.send_time,
        is_active=template_data.is_active,
        is_default=template_data.is_default,
        created_by_id=current_user.id
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(
        f"Created notification template: {template.name}",
        extra={"user_id": current_user.id, "template_id": template.id}
    )

    return OutreachNotificationTemplateResponse.model_validate(template)


@router.post("/notification-templates/preview")
async def preview_notification(
    template_id: int,
    partner_id: Optional[int] = None,
    visit_id: Optional[int] = None,
    bulk_checkout_id: Optional[int] = None,
    custom_variables: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Preview a notification template with variable substitution."""
    from ....models.outreach import OutreachNotificationTemplate
    import re

    query = select(OutreachNotificationTemplate).where(OutreachNotificationTemplate.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Notification template not found")

    # Build variables dict
    variables = custom_variables or {}

    # Add partner variables
    if partner_id:
        partner_query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
        partner = (await db.execute(partner_query)).scalar_one_or_none()
        if partner:
            variables.update({
                "partner_name": partner.name,
                "partner_type": partner.partner_type,
                "partner_address": partner.address or "",
                "partner_city": partner.city or "",
            })

    # Add visit variables
    if visit_id:
        visit_query = select(OutreachVisit).options(
            selectinload(OutreachVisit.lead_staff)
        ).where(OutreachVisit.id == visit_id)
        visit = (await db.execute(visit_query)).scalar_one_or_none()
        if visit:
            variables.update({
                "visit_date": visit.scheduled_date.isoformat() if visit.scheduled_date else "",
                "visit_time": visit.scheduled_time or "",
                "visit_type": visit.visit_type,
                "staff_name": visit.lead_staff.full_name if visit.lead_staff else "",
            })

    # Add bulk checkout variables
    if bulk_checkout_id:
        checkout_query = select(BulkCheckout).where(BulkCheckout.id == bulk_checkout_id)
        checkout = (await db.execute(checkout_query)).scalar_one_or_none()
        if checkout:
            variables.update({
                "checkout_name": checkout.checkout_name,
                "requestor_name": checkout.requestor_name,
                "due_date": checkout.due_date.isoformat() if checkout.due_date else "",
                "item_count": str(checkout.total_items),
                "items_outstanding": str(checkout.total_items - checkout.items_returned - checkout.items_lost),
            })

    # Substitute variables in template
    def substitute_vars(text: str, vars_dict: dict) -> str:
        if not text:
            return text
        for key, value in vars_dict.items():
            text = re.sub(r'\{\{\s*' + key + r'\s*\}\}', str(value), text)
        return text

    rendered_subject = substitute_vars(template.subject, variables)
    rendered_body = substitute_vars(template.body, variables)
    rendered_html = substitute_vars(template.html_body, variables) if template.html_body else None

    return {
        "subject": rendered_subject,
        "body": rendered_body,
        "html_body": rendered_html,
        "variables_used": variables
    }


# =============================================================================
# Notification Logs
# =============================================================================

@router.get("/notification-logs")
async def list_notification_logs(
    notification_type: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    partner_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List notification logs with filtering options."""
    from ....models.outreach import OutreachNotificationLog
    from ....schemas.outreach import (
        OutreachNotificationLogResponse,
        OutreachNotificationLogListResponse
    )

    query = select(OutreachNotificationLog)

    if notification_type:
        query = query.where(OutreachNotificationLog.notification_type == notification_type)
    if channel:
        query = query.where(OutreachNotificationLog.channel == channel)
    if status:
        query = query.where(OutreachNotificationLog.status == status)
    if partner_id:
        query = query.where(OutreachNotificationLog.partner_id == partner_id)
    if start_date:
        query = query.where(OutreachNotificationLog.created_at >= start_date)
    if end_date:
        query = query.where(OutreachNotificationLog.created_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination and order
    query = query.order_by(OutreachNotificationLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return OutreachNotificationLogListResponse(
        logs=[OutreachNotificationLogResponse.model_validate(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/notification-logs/stats")
async def get_notification_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Get notification delivery statistics."""
    from ....models.outreach import OutreachNotificationLog

    base_query = select(OutreachNotificationLog)

    if start_date:
        base_query = base_query.where(OutreachNotificationLog.created_at >= start_date)
    if end_date:
        base_query = base_query.where(OutreachNotificationLog.created_at <= end_date)

    result = await db.execute(base_query)
    logs = result.scalars().all()

    # Aggregate stats
    by_type = {}
    by_channel = {}
    by_status = {}

    for log in logs:
        # By type
        if log.notification_type not in by_type:
            by_type[log.notification_type] = {"sent": 0, "delivered": 0, "failed": 0}
        if log.status == "delivered":
            by_type[log.notification_type]["delivered"] += 1
        elif log.status == "failed":
            by_type[log.notification_type]["failed"] += 1
        else:
            by_type[log.notification_type]["sent"] += 1

        # By channel
        if log.channel not in by_channel:
            by_channel[log.channel] = 0
        by_channel[log.channel] += 1

        # By status
        if log.status not in by_status:
            by_status[log.status] = 0
        by_status[log.status] += 1

    total = len(logs)
    delivered = by_status.get("delivered", 0)
    failed = by_status.get("failed", 0)

    return {
        "total_notifications": total,
        "delivery_rate": (delivered / total * 100) if total > 0 else 0,
        "failure_rate": (failed / total * 100) if total > 0 else 0,
        "by_type": by_type,
        "by_channel": by_channel,
        "by_status": by_status
    }


@router.get("/bulk-checkouts/bulk-extend")
async def get_bulk_checkouts_bulk_extend_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of /bulk-checkouts/bulk-extend operation."""
    return {"status": "pending", "processed": 0, "total": 0}



@router.get("/deposits/bulk-forfeit")
async def get_deposits_bulk_forfeit_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of /deposits/bulk-forfeit operation."""
    return {"status": "pending", "processed": 0, "total": 0}

