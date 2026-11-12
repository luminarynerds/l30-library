# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outreach Statistics dashboard, reports, and monthly statistics endpoints."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner,
    OutreachDeposit,
    OutreachVisit,
    InstitutionalCard,
    InstitutionalCheckout,
    BulkCheckout,
    OutreachStatistics,
    OutreachPartnerStatus,
    DepositStatus,
    VisitStatus,
    InstitutionalCardStatus,
    BulkCheckoutStatus,
)
from ....models.user import User
from ....schemas.outreach import (
    OutreachPartnerResponse,
    OutreachPartnerSummary,
    OutreachVisitResponse,
    BulkCheckoutResponse,
    OutreachStatisticsResponse,
    OutreachDashboardResponse,
    OutreachReportRequest,
    OutreachReportResponse,
)
from .helpers import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=OutreachDashboardResponse)
async def get_outreach_dashboard(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_staff)
):
    """Get outreach program dashboard with summary statistics."""
    today = date.today()
    month_start = today.replace(day=1)

    # Active partners count
    active_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
    )
    active_partners = (await db.execute(active_partners_query)).scalar() or 0

    # Pending visits (scheduled for future)
    pending_visits_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.status.in_([VisitStatus.SCHEDULED.value, VisitStatus.CONFIRMED.value]),
            OutreachVisit.scheduled_date >= today,
        )
    )
    pending_visits = (await db.execute(pending_visits_query)).scalar() or 0

    # Overdue bulk checkouts
    overdue_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(
            BulkCheckout.status == BulkCheckoutStatus.ACTIVE.value, BulkCheckout.due_date < today
        )
    )
    overdue_bulk_checkouts = (await db.execute(overdue_query)).scalar() or 0

    # Deposits held
    deposits_query = select(
        func.sum(
            OutreachDeposit.amount
            - OutreachDeposit.amount_applied
            - OutreachDeposit.amount_refunded
        )
    ).where(OutreachDeposit.status == DepositStatus.HELD.value)
    deposits_held = (await db.execute(deposits_query)).scalar() or 0.0

    # Recent completed visits (last 5)
    recent_visits_query = (
        select(OutreachVisit)
        .options(selectinload(OutreachVisit.partner))
        .where(OutreachVisit.status == VisitStatus.COMPLETED.value)
        .order_by(OutreachVisit.scheduled_date.desc())
        .limit(5)
    )
    recent_visits_result = await db.execute(recent_visits_query)
    recent_visits = recent_visits_result.scalars().all()

    # Upcoming visits (next 5)
    upcoming_visits_query = (
        select(OutreachVisit)
        .options(selectinload(OutreachVisit.partner))
        .where(
            OutreachVisit.status.in_([VisitStatus.SCHEDULED.value, VisitStatus.CONFIRMED.value]),
            OutreachVisit.scheduled_date >= today,
        )
        .order_by(OutreachVisit.scheduled_date.asc())
        .limit(5)
    )
    upcoming_visits_result = await db.execute(upcoming_visits_query)
    upcoming_visits = upcoming_visits_result.scalars().all()

    # This month statistics
    visits_this_month_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.scheduled_date >= month_start,
            OutreachVisit.status == VisitStatus.COMPLETED.value,
        )
    )
    visits_this_month = (await db.execute(visits_this_month_query)).scalar() or 0

    attendees_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        OutreachVisit.scheduled_date >= month_start,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    attendees_this_month = (await db.execute(attendees_query)).scalar() or 0

    items_query = select(func.sum(BulkCheckout.total_items)).where(
        BulkCheckout.checkout_date >= month_start
    )
    items_circulated_this_month = (await db.execute(items_query)).scalar() or 0

    cards_query = select(func.sum(OutreachVisit.new_cards_issued)).where(
        OutreachVisit.scheduled_date >= month_start,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    new_cards_this_month = (await db.execute(cards_query)).scalar() or 0

    # Top partners by bulk checkouts (top 5)
    top_checkout_partners_query = (
        select(OutreachPartner, func.count(BulkCheckout.id).label("checkout_count"))
        .join(BulkCheckout, BulkCheckout.partner_id == OutreachPartner.id)
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
        .group_by(OutreachPartner.id)
        .order_by(func.count(BulkCheckout.id).desc())
        .limit(5)
    )
    top_checkout_result = await db.execute(top_checkout_partners_query)
    top_partners_checkouts = [
        OutreachPartnerSummary.model_validate(row[0]) for row in top_checkout_result.all()
    ]

    # Top partners by visits (top 5)
    top_visit_partners_query = (
        select(OutreachPartner, func.count(OutreachVisit.id).label("visit_count"))
        .join(OutreachVisit, OutreachVisit.partner_id == OutreachPartner.id)
        .where(
            OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value,
            OutreachVisit.status == VisitStatus.COMPLETED.value,
        )
        .group_by(OutreachPartner.id)
        .order_by(func.count(OutreachVisit.id).desc())
        .limit(5)
    )
    top_visit_result = await db.execute(top_visit_partners_query)
    top_partners_visits = [
        OutreachPartnerSummary.model_validate(row[0]) for row in top_visit_result.all()
    ]

    # Format visit responses
    recent_visit_responses = []
    for v in recent_visits:
        resp = OutreachVisitResponse.model_validate(v)
        resp.partner_name = v.partner.name if v.partner else None
        recent_visit_responses.append(resp)

    upcoming_visit_responses = []
    for v in upcoming_visits:
        resp = OutreachVisitResponse.model_validate(v)
        resp.partner_name = v.partner.name if v.partner else None
        upcoming_visit_responses.append(resp)

    return OutreachDashboardResponse(
        active_partners=active_partners,
        pending_visits=pending_visits,
        overdue_bulk_checkouts=overdue_bulk_checkouts,
        deposits_held=deposits_held,
        recent_visits=recent_visit_responses,
        upcoming_visits=upcoming_visit_responses,
        visits_this_month=visits_this_month,
        attendees_this_month=attendees_this_month,
        items_circulated_this_month=items_circulated_this_month,
        new_cards_this_month=new_cards_this_month,
        top_partners_by_checkouts=top_partners_checkouts,
        top_partners_by_visits=top_partners_visits,
    )


@router.get("/statistics", response_model=OutreachStatisticsResponse)
async def get_outreach_statistics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_staff)
):
    """Get detailed outreach statistics including visits, cards issued, and checkouts."""
    today = date.today()
    month_start = today.replace(day=1)

    # Partner counts
    total_partners_query = select(func.count()).select_from(OutreachPartner)
    total_partners = (await db.execute(total_partners_query)).scalar() or 0

    active_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
    )
    active_partners = (await db.execute(active_partners_query)).scalar() or 0

    new_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(
            OutreachPartner.partnership_start_date >= month_start,
            OutreachPartner.partnership_start_date <= today,
        )
    )
    new_partners = (await db.execute(new_partners_query)).scalar() or 0

    # Partners by type
    partners_by_type_query = select(
        OutreachPartner.partner_type, func.count().label("count")
    ).group_by(OutreachPartner.partner_type)
    partners_by_type_result = await db.execute(partners_by_type_query)
    partners_by_type = {row[0]: row[1] for row in partners_by_type_result.all()}

    # Visit statistics for current month
    total_visits_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(OutreachVisit.scheduled_date >= month_start, OutreachVisit.scheduled_date <= today)
    )
    total_visits = (await db.execute(total_visits_query)).scalar() or 0

    visits_completed_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.scheduled_date >= month_start,
            OutreachVisit.scheduled_date <= today,
            OutreachVisit.status == VisitStatus.COMPLETED.value,
        )
    )
    visits_completed = (await db.execute(visits_completed_query)).scalar() or 0

    visits_cancelled_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.scheduled_date >= month_start,
            OutreachVisit.scheduled_date <= today,
            OutreachVisit.status == VisitStatus.CANCELLED.value,
        )
    )
    visits_cancelled = (await db.execute(visits_cancelled_query)).scalar() or 0

    total_attendees_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        OutreachVisit.scheduled_date >= month_start,
        OutreachVisit.scheduled_date <= today,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    total_attendees = (await db.execute(total_attendees_query)).scalar() or 0

    # Visits by type
    visits_by_type_query = (
        select(OutreachVisit.visit_type, func.count().label("count"))
        .where(OutreachVisit.scheduled_date >= month_start, OutreachVisit.scheduled_date <= today)
        .group_by(OutreachVisit.visit_type)
    )
    visits_by_type_result = await db.execute(visits_by_type_query)
    visits_by_type = {row[0]: row[1] for row in visits_by_type_result.all()}

    # Bulk checkout statistics
    bulk_created_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(BulkCheckout.checkout_date >= month_start, BulkCheckout.checkout_date <= today)
    )
    bulk_checkouts_created = (await db.execute(bulk_created_query)).scalar() or 0

    bulk_returned_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(BulkCheckout.returned_date >= month_start, BulkCheckout.returned_date <= today)
    )
    bulk_checkouts_returned = (await db.execute(bulk_returned_query)).scalar() or 0

    bulk_items_out_query = select(func.sum(BulkCheckout.total_items)).where(
        BulkCheckout.checkout_date >= month_start, BulkCheckout.checkout_date <= today
    )
    bulk_items_checked_out = (await db.execute(bulk_items_out_query)).scalar() or 0

    bulk_items_ret_query = select(func.sum(BulkCheckout.items_returned)).where(
        BulkCheckout.returned_date >= month_start, BulkCheckout.returned_date <= today
    )
    bulk_items_returned = (await db.execute(bulk_items_ret_query)).scalar() or 0

    bulk_items_lost_query = select(func.sum(BulkCheckout.items_lost)).where(
        BulkCheckout.checkout_date >= month_start, BulkCheckout.checkout_date <= today
    )
    bulk_items_lost = (await db.execute(bulk_items_lost_query)).scalar() or 0

    # Institutional card statistics
    cards_active_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value)
    )
    institutional_cards_active = (await db.execute(cards_active_query)).scalar() or 0

    cards_issued_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(InstitutionalCard.issued_date >= month_start, InstitutionalCard.issued_date <= today)
    )
    institutional_cards_issued = (await db.execute(cards_issued_query)).scalar() or 0

    inst_checkouts_query = (
        select(func.count())
        .select_from(InstitutionalCheckout)
        .where(
            func.date(InstitutionalCheckout.checked_out_at) >= month_start,
            func.date(InstitutionalCheckout.checked_out_at) <= today,
        )
    )
    institutional_checkouts = (await db.execute(inst_checkouts_query)).scalar() or 0

    # Deposit statistics
    deposits_collected_query = select(func.sum(OutreachDeposit.amount)).where(
        OutreachDeposit.collected_date >= month_start, OutreachDeposit.collected_date <= today
    )
    deposits_collected = (await db.execute(deposits_collected_query)).scalar() or 0.0

    deposits_refunded_query = select(func.sum(OutreachDeposit.amount_refunded)).where(
        OutreachDeposit.refund_date >= month_start, OutreachDeposit.refund_date <= today
    )
    deposits_refunded = (await db.execute(deposits_refunded_query)).scalar() or 0.0

    deposits_applied_query = select(func.sum(OutreachDeposit.amount_applied)).where(
        OutreachDeposit.collected_date >= month_start, OutreachDeposit.collected_date <= today
    )
    deposits_applied = (await db.execute(deposits_applied_query)).scalar() or 0.0

    # Impact metrics
    new_cards_query = select(func.sum(OutreachVisit.new_cards_issued)).where(
        OutreachVisit.scheduled_date >= month_start,
        OutreachVisit.scheduled_date <= today,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    new_cards_from_outreach = (await db.execute(new_cards_query)).scalar() or 0

    logger.info(
        "Retrieved detailed outreach statistics",
        extra={"period_start": str(month_start), "period_end": str(today)},
    )

    return OutreachStatisticsResponse(
        id=0,
        period_start=month_start,
        period_end=today,
        branch_id=None,
        total_partners=total_partners,
        active_partners=active_partners,
        new_partners=new_partners,
        partners_by_type=partners_by_type,
        total_visits=total_visits,
        visits_completed=visits_completed,
        visits_cancelled=visits_cancelled,
        total_attendees=total_attendees,
        visits_by_type=visits_by_type,
        bulk_checkouts_created=bulk_checkouts_created,
        bulk_checkouts_returned=bulk_checkouts_returned,
        bulk_items_checked_out=bulk_items_checked_out,
        bulk_items_returned=bulk_items_returned,
        bulk_items_lost=bulk_items_lost,
        institutional_cards_active=institutional_cards_active,
        institutional_cards_issued=institutional_cards_issued,
        institutional_checkouts=institutional_checkouts,
        deposits_collected=deposits_collected,
        deposits_refunded=deposits_refunded,
        deposits_applied_to_fines=deposits_applied,
        new_cards_from_outreach=new_cards_from_outreach,
        reading_program_signups=0,
        generated_at=datetime.now(),
    )


@router.post("/reports", response_model=OutreachReportResponse)
async def create_outreach_report(
    report_request: OutreachReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Generate a custom date-range outreach report with partner counts, visit totals,
    cards issued, and items circulated."""
    start_date = report_request.start_date
    end_date = report_request.end_date

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    # Partner counts
    total_partners_query = select(func.count()).select_from(OutreachPartner)
    if report_request.partner_types:
        total_partners_query = total_partners_query.where(
            OutreachPartner.partner_type.in_([pt.value for pt in report_request.partner_types])
        )
    total_partners = (await db.execute(total_partners_query)).scalar() or 0

    active_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
    )
    if report_request.partner_types:
        active_partners_query = active_partners_query.where(
            OutreachPartner.partner_type.in_([pt.value for pt in report_request.partner_types])
        )
    active_partners = (await db.execute(active_partners_query)).scalar() or 0

    new_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(
            OutreachPartner.partnership_start_date >= start_date,
            OutreachPartner.partnership_start_date <= end_date,
        )
    )
    new_partners = (await db.execute(new_partners_query)).scalar() or 0

    # Partners by type
    partners_by_type_query = (
        select(OutreachPartner.partner_type, func.count().label("count"))
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
        .group_by(OutreachPartner.partner_type)
    )
    partners_by_type_result = await db.execute(partners_by_type_query)
    partners_by_type = {row[0]: row[1] for row in partners_by_type_result.all()}

    # Visit statistics
    visit_filters = [
        OutreachVisit.scheduled_date >= start_date,
        OutreachVisit.scheduled_date <= end_date,
    ]
    if report_request.partner_ids:
        visit_filters.append(OutreachVisit.partner_id.in_(report_request.partner_ids))
    if report_request.visit_types:
        visit_filters.append(
            OutreachVisit.visit_type.in_([vt.value for vt in report_request.visit_types])
        )

    total_visits_query = select(func.count()).select_from(OutreachVisit).where(*visit_filters)
    total_visits = (await db.execute(total_visits_query)).scalar() or 0

    completed_filters = visit_filters + [OutreachVisit.status == VisitStatus.COMPLETED.value]
    visits_completed_query = (
        select(func.count()).select_from(OutreachVisit).where(*completed_filters)
    )
    visits_completed = (await db.execute(visits_completed_query)).scalar() or 0

    cancelled_filters = visit_filters + [OutreachVisit.status == VisitStatus.CANCELLED.value]
    visits_cancelled_query = (
        select(func.count()).select_from(OutreachVisit).where(*cancelled_filters)
    )
    visits_cancelled = (await db.execute(visits_cancelled_query)).scalar() or 0

    total_attendees_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        *completed_filters
    )
    total_attendees = (await db.execute(total_attendees_query)).scalar() or 0

    # Visits by type
    visits_by_type_query = (
        select(OutreachVisit.visit_type, func.count().label("count"))
        .where(*visit_filters)
        .group_by(OutreachVisit.visit_type)
    )
    visits_by_type_result = await db.execute(visits_by_type_query)
    visits_by_type = {row[0]: row[1] for row in visits_by_type_result.all()}

    # Bulk checkout statistics
    bulk_filters = [
        BulkCheckout.checkout_date >= start_date,
        BulkCheckout.checkout_date <= end_date,
    ]
    if report_request.partner_ids:
        bulk_filters.append(BulkCheckout.partner_id.in_(report_request.partner_ids))

    bulk_created_query = select(func.count()).select_from(BulkCheckout).where(*bulk_filters)
    bulk_checkouts_created = (await db.execute(bulk_created_query)).scalar() or 0

    bulk_returned_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(BulkCheckout.returned_date >= start_date, BulkCheckout.returned_date <= end_date)
    )
    bulk_checkouts_returned = (await db.execute(bulk_returned_query)).scalar() or 0

    bulk_items_out_query = select(func.sum(BulkCheckout.total_items)).where(*bulk_filters)
    bulk_items_checked_out = (await db.execute(bulk_items_out_query)).scalar() or 0

    bulk_items_ret_query = select(func.sum(BulkCheckout.items_returned)).where(
        BulkCheckout.returned_date >= start_date, BulkCheckout.returned_date <= end_date
    )
    bulk_items_returned = (await db.execute(bulk_items_ret_query)).scalar() or 0

    bulk_items_lost_query = select(func.sum(BulkCheckout.items_lost)).where(*bulk_filters)
    bulk_items_lost = (await db.execute(bulk_items_lost_query)).scalar() or 0

    # Institutional card statistics
    cards_active_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value)
    )
    institutional_cards_active = (await db.execute(cards_active_query)).scalar() or 0

    cards_issued_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(
            InstitutionalCard.issued_date >= start_date, InstitutionalCard.issued_date <= end_date
        )
    )
    institutional_cards_issued = (await db.execute(cards_issued_query)).scalar() or 0

    inst_checkouts_query = (
        select(func.count())
        .select_from(InstitutionalCheckout)
        .where(
            func.date(InstitutionalCheckout.checked_out_at) >= start_date,
            func.date(InstitutionalCheckout.checked_out_at) <= end_date,
        )
    )
    institutional_checkouts = (await db.execute(inst_checkouts_query)).scalar() or 0

    # Deposit statistics
    deposits_collected_query = select(func.sum(OutreachDeposit.amount)).where(
        OutreachDeposit.collected_date >= start_date, OutreachDeposit.collected_date <= end_date
    )
    deposits_collected = (await db.execute(deposits_collected_query)).scalar() or 0.0

    deposits_refunded_query = select(func.sum(OutreachDeposit.amount_refunded)).where(
        OutreachDeposit.refund_date >= start_date, OutreachDeposit.refund_date <= end_date
    )
    deposits_refunded = (await db.execute(deposits_refunded_query)).scalar() or 0.0

    deposits_applied_query = select(func.sum(OutreachDeposit.amount_applied)).where(
        OutreachDeposit.collected_date >= start_date, OutreachDeposit.collected_date <= end_date
    )
    deposits_applied = (await db.execute(deposits_applied_query)).scalar() or 0.0

    # Impact metrics - cards issued from outreach visits
    new_cards_query = select(func.sum(OutreachVisit.new_cards_issued)).where(*completed_filters)
    new_cards_from_outreach = (await db.execute(new_cards_query)).scalar() or 0

    statistics = OutreachStatisticsResponse(
        id=0,
        period_start=start_date,
        period_end=end_date,
        branch_id=report_request.branch_id,
        total_partners=total_partners,
        active_partners=active_partners,
        new_partners=new_partners,
        partners_by_type=partners_by_type,
        total_visits=total_visits,
        visits_completed=visits_completed,
        visits_cancelled=visits_cancelled,
        total_attendees=total_attendees,
        visits_by_type=visits_by_type,
        bulk_checkouts_created=bulk_checkouts_created,
        bulk_checkouts_returned=bulk_checkouts_returned,
        bulk_items_checked_out=bulk_items_checked_out,
        bulk_items_returned=bulk_items_returned,
        bulk_items_lost=bulk_items_lost,
        institutional_cards_active=institutional_cards_active,
        institutional_cards_issued=institutional_cards_issued,
        institutional_checkouts=institutional_checkouts,
        deposits_collected=deposits_collected,
        deposits_refunded=deposits_refunded,
        deposits_applied_to_fines=deposits_applied,
        new_cards_from_outreach=new_cards_from_outreach,
        reading_program_signups=0,
        generated_at=datetime.now(),
    )

    # Optional detailed breakdowns
    partner_details = None
    visit_details = None
    bulk_checkout_details = None

    if report_request.include_details:
        # Partner details
        partners_query = select(OutreachPartner).where(
            OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value
        )
        if report_request.partner_ids:
            partners_query = partners_query.where(
                OutreachPartner.id.in_(report_request.partner_ids)
            )
        if report_request.partner_types:
            partners_query = partners_query.where(
                OutreachPartner.partner_type.in_([pt.value for pt in report_request.partner_types])
            )
        partners_result = await db.execute(partners_query)
        partner_details = [
            OutreachPartnerResponse.model_validate(p) for p in partners_result.scalars().all()
        ]

        # Visit details
        visits_detail_query = (
            select(OutreachVisit).options(selectinload(OutreachVisit.partner)).where(*visit_filters)
        )
        visits_result = await db.execute(visits_detail_query)
        visit_details = []
        for v in visits_result.scalars().all():
            resp = OutreachVisitResponse.model_validate(v)
            resp.partner_name = v.partner.name if v.partner else None
            visit_details.append(resp)

        # Bulk checkout details. BulkCheckoutResponse declares `items`, so it
        # must be eager-loaded too -- model_validate() would otherwise lazy-load
        # it from pydantic's sync path and raise MissingGreenlet.
        bulk_detail_query = (
            select(BulkCheckout)
            .options(
                selectinload(BulkCheckout.partner),
                selectinload(BulkCheckout.items),
            )
            .where(*bulk_filters)
        )
        bulk_result = await db.execute(bulk_detail_query)
        bulk_checkout_details = []
        for bc in bulk_result.scalars().all():
            resp = BulkCheckoutResponse.model_validate(bc)
            resp.partner_name = bc.partner.name if bc.partner else None
            bulk_checkout_details.append(resp)

    logger.info(
        f"Generated custom outreach report for {start_date} to {end_date}",
        extra={
            "start_date": str(start_date),
            "end_date": str(end_date),
            "user_id": current_user.id,
        },
    )

    return OutreachReportResponse(
        report_period=f"{start_date} to {end_date}",
        generated_at=datetime.now(),
        statistics=statistics,
        partner_details=partner_details,
        visit_details=visit_details,
        bulk_checkout_details=bulk_checkout_details,
    )


@router.post("/reports/generate", response_model=OutreachReportResponse)
async def generate_outreach_report(
    report_request: OutreachReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Generate a comprehensive outreach report for a date range."""
    start_date = report_request.start_date
    end_date = report_request.end_date

    # Build statistics
    # Partner counts
    total_partners_query = select(func.count()).select_from(OutreachPartner)
    total_partners = (await db.execute(total_partners_query)).scalar() or 0

    active_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value)
    )
    active_partners = (await db.execute(active_partners_query)).scalar() or 0

    new_partners_query = (
        select(func.count())
        .select_from(OutreachPartner)
        .where(
            func.date(OutreachPartner.partnership_start_date) >= start_date,
            func.date(OutreachPartner.partnership_start_date) <= end_date,
        )
    )
    new_partners = (await db.execute(new_partners_query)).scalar() or 0

    # Visit statistics
    visit_base_query = select(OutreachVisit).where(
        OutreachVisit.scheduled_date >= start_date, OutreachVisit.scheduled_date <= end_date
    )

    if report_request.partner_ids:
        visit_base_query = visit_base_query.where(
            OutreachVisit.partner_id.in_(report_request.partner_ids)
        )

    total_visits_query = select(func.count()).select_from(visit_base_query.subquery())
    total_visits = (await db.execute(total_visits_query)).scalar() or 0

    completed_visits_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.scheduled_date >= start_date,
            OutreachVisit.scheduled_date <= end_date,
            OutreachVisit.status == VisitStatus.COMPLETED.value,
        )
    )
    visits_completed = (await db.execute(completed_visits_query)).scalar() or 0

    cancelled_visits_query = (
        select(func.count())
        .select_from(OutreachVisit)
        .where(
            OutreachVisit.scheduled_date >= start_date,
            OutreachVisit.scheduled_date <= end_date,
            OutreachVisit.status == VisitStatus.CANCELLED.value,
        )
    )
    visits_cancelled = (await db.execute(cancelled_visits_query)).scalar() or 0

    attendees_query = select(func.sum(OutreachVisit.actual_attendees)).where(
        OutreachVisit.scheduled_date >= start_date,
        OutreachVisit.scheduled_date <= end_date,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    total_attendees = (await db.execute(attendees_query)).scalar() or 0

    # Bulk checkout statistics
    bulk_created_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(BulkCheckout.checkout_date >= start_date, BulkCheckout.checkout_date <= end_date)
    )
    bulk_checkouts_created = (await db.execute(bulk_created_query)).scalar() or 0

    bulk_returned_query = (
        select(func.count())
        .select_from(BulkCheckout)
        .where(BulkCheckout.returned_date >= start_date, BulkCheckout.returned_date <= end_date)
    )
    bulk_checkouts_returned = (await db.execute(bulk_returned_query)).scalar() or 0

    bulk_items_out_query = select(func.sum(BulkCheckout.total_items)).where(
        BulkCheckout.checkout_date >= start_date, BulkCheckout.checkout_date <= end_date
    )
    bulk_items_checked_out = (await db.execute(bulk_items_out_query)).scalar() or 0

    bulk_items_ret_query = select(func.sum(BulkCheckout.items_returned)).where(
        BulkCheckout.returned_date >= start_date, BulkCheckout.returned_date <= end_date
    )
    bulk_items_returned = (await db.execute(bulk_items_ret_query)).scalar() or 0

    bulk_items_lost_query = select(func.sum(BulkCheckout.items_lost)).where(
        BulkCheckout.checkout_date >= start_date, BulkCheckout.checkout_date <= end_date
    )
    bulk_items_lost = (await db.execute(bulk_items_lost_query)).scalar() or 0

    # Institutional card statistics
    cards_active_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(InstitutionalCard.status == InstitutionalCardStatus.ACTIVE.value)
    )
    institutional_cards_active = (await db.execute(cards_active_query)).scalar() or 0

    cards_issued_query = (
        select(func.count())
        .select_from(InstitutionalCard)
        .where(
            InstitutionalCard.issued_date >= start_date, InstitutionalCard.issued_date <= end_date
        )
    )
    institutional_cards_issued = (await db.execute(cards_issued_query)).scalar() or 0

    inst_checkouts_query = (
        select(func.count())
        .select_from(InstitutionalCheckout)
        .where(
            func.date(InstitutionalCheckout.checked_out_at) >= start_date,
            func.date(InstitutionalCheckout.checked_out_at) <= end_date,
        )
    )
    institutional_checkouts = (await db.execute(inst_checkouts_query)).scalar() or 0

    # Deposit statistics
    deposits_collected_query = select(func.sum(OutreachDeposit.amount)).where(
        OutreachDeposit.collected_date >= start_date, OutreachDeposit.collected_date <= end_date
    )
    deposits_collected = (await db.execute(deposits_collected_query)).scalar() or 0.0

    deposits_refunded_query = select(func.sum(OutreachDeposit.amount_refunded)).where(
        OutreachDeposit.refund_date >= start_date, OutreachDeposit.refund_date <= end_date
    )
    deposits_refunded = (await db.execute(deposits_refunded_query)).scalar() or 0.0

    # Impact metrics
    new_cards_query = select(func.sum(OutreachVisit.new_cards_issued)).where(
        OutreachVisit.scheduled_date >= start_date,
        OutreachVisit.scheduled_date <= end_date,
        OutreachVisit.status == VisitStatus.COMPLETED.value,
    )
    new_cards_from_outreach = (await db.execute(new_cards_query)).scalar() or 0

    statistics = OutreachStatisticsResponse(
        id=0,
        period_start=start_date,
        period_end=end_date,
        branch_id=report_request.branch_id,
        total_partners=total_partners,
        active_partners=active_partners,
        new_partners=new_partners,
        partners_by_type={},
        total_visits=total_visits,
        visits_completed=visits_completed,
        visits_cancelled=visits_cancelled,
        total_attendees=total_attendees,
        visits_by_type={},
        bulk_checkouts_created=bulk_checkouts_created,
        bulk_checkouts_returned=bulk_checkouts_returned,
        bulk_items_checked_out=bulk_items_checked_out,
        bulk_items_returned=bulk_items_returned,
        bulk_items_lost=bulk_items_lost,
        institutional_cards_active=institutional_cards_active,
        institutional_cards_issued=institutional_cards_issued,
        institutional_checkouts=institutional_checkouts,
        deposits_collected=deposits_collected,
        deposits_refunded=deposits_refunded,
        deposits_applied_to_fines=0.0,
        new_cards_from_outreach=new_cards_from_outreach,
        reading_program_signups=0,
        generated_at=datetime.now(),
    )

    logger.info(
        f"Generated outreach report for {start_date} to {end_date}",
        extra={"start_date": str(start_date), "end_date": str(end_date)},
    )

    return OutreachReportResponse(
        report_period=f"{start_date} to {end_date}",
        generated_at=datetime.now(),
        statistics=statistics,
        partner_details=None,
        visit_details=None,
        bulk_checkout_details=None,
    )


@router.get("/statistics/monthly", response_model=list[OutreachStatisticsResponse])
async def get_monthly_statistics(
    months: int = Query(default=12, le=36),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get monthly outreach statistics for the specified number of months."""
    query = (
        select(OutreachStatistics).order_by(OutreachStatistics.period_start.desc()).limit(months)
    )

    result = await db.execute(query)
    return result.scalars().all()
