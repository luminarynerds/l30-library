# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
HomeDelivery Delivery Service - Reports API Endpoints

Provides endpoints for:
- Summary statistics
- Patron reports
- Volunteer reports
- Delivery reports
- Analytics and trends
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.database import get_db
from ...models.home_delivery import (
    Delivery, DeliveryFeedback, DeliveryStatus, DeliveryVolunteer,
    HomeDeliveryApplication, HomeDeliveryApplicationStatus, HomeDeliveryEnrollment,
    HomeDeliveryEnrollmentStatus, VolunteerHourLog, DeliveryVolunteerStatus
)
from ...models.user import User
from ...schemas.home_delivery import (
    DeliveryAnalytics, ExportRequest, ExportResponse,
    HomeDeliveryDeliveryReport, HomeDeliveryPatronReport, HomeDeliveryReportResponse,
    HomeDeliveryReportSummary, HomeDeliveryVolunteerReport, RouteSuggestion,
    RouteSuggestionsResponse, ServiceAnalytics, VolunteerAnalytics
)
from ...services.home_delivery_service import HomeDeliveryReportService
from ...services.route_optimization_service import ClusteringService
from .dependencies import require_staff

router = APIRouter(prefix="/home-delivery/reports", tags=["home-delivery-reports"])


@router.get("/summary", response_model=HomeDeliveryReportSummary)
async def get_summary_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics for home delivery service."""
    stats = await HomeDeliveryReportService.get_summary_stats(db)
    return HomeDeliveryReportSummary(**stats)


@router.get("/patrons", response_model=list[HomeDeliveryPatronReport])
async def get_patron_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get reports on patrons served."""
    reports = await HomeDeliveryReportService.get_patron_reports(db, limit, offset)
    return [HomeDeliveryPatronReport(**r) for r in reports]


@router.get("/volunteers", response_model=list[HomeDeliveryVolunteerReport])
async def get_volunteer_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get reports on volunteer contributions."""
    reports = await HomeDeliveryReportService.get_volunteer_reports(db, limit, offset)
    return [HomeDeliveryVolunteerReport(**r) for r in reports]


@router.get("/deliveries", response_model=list[HomeDeliveryDeliveryReport])
async def get_delivery_reports(
    period_type: str = Query("month", description="Period type: week or month"),
    periods: int = Query(6, ge=1, le=24, description="Number of periods to include"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery reports grouped by time period."""
    reports = []
    now = datetime.now(timezone.utc)

    for i in range(periods):
        if period_type == "week":
            # Calculate week start (Monday)
            days_ago = i * 7
            period_end = now - timedelta(days=days_ago)
            period_start = period_end - timedelta(days=7)
            period_label = period_start.strftime("%Y-W%W")
        else:  # month
            # Calculate month
            month_offset = i
            year = now.year
            month = now.month - month_offset
            while month <= 0:
                month += 12
                year -= 1
            period_label = f"{year}-{month:02d}"
            period_start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Get delivery stats for this period
        total_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date()
        )

        completed_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivered
        )

        failed_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivery_failed
        )

        items_delivered_query = select(func.sum(Delivery.items_delivered)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivered
        )

        items_picked_up_query = select(func.sum(Delivery.items_picked_up)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date()
        )

        avg_rating_query = (
            select(func.avg(DeliveryFeedback.overall_rating))
            .join(Delivery)
            .where(
                Delivery.scheduled_date >= period_start.date(),
                Delivery.scheduled_date < period_end.date()
            )
        )

        total = (await db.execute(total_query)).scalar() or 0
        completed = (await db.execute(completed_query)).scalar() or 0
        failed = (await db.execute(failed_query)).scalar() or 0
        items_delivered = (await db.execute(items_delivered_query)).scalar() or 0
        items_picked_up = (await db.execute(items_picked_up_query)).scalar() or 0
        avg_rating = (await db.execute(avg_rating_query)).scalar()

        avg_items = items_delivered / completed if completed > 0 else 0

        reports.append(HomeDeliveryDeliveryReport(
            period=period_label,
            total_deliveries=total,
            completed_deliveries=completed,
            failed_deliveries=failed,
            total_items_delivered=items_delivered,
            total_items_picked_up=items_picked_up,
            average_items_per_delivery=round(avg_items, 2),
            average_rating=round(avg_rating, 2) if avg_rating else None
        ))

    return reports


@router.get("/full", response_model=HomeDeliveryReportResponse)
async def get_full_report(
    limit: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive home delivery service report."""
    summary = await HomeDeliveryReportService.get_summary_stats(db)
    patron_reports = await HomeDeliveryReportService.get_patron_reports(db, limit, 0)
    volunteer_reports = await HomeDeliveryReportService.get_volunteer_reports(db, limit, 0)

    # Get last 6 months of delivery reports
    delivery_reports = []
    now = datetime.now(timezone.utc)

    for i in range(6):
        month_offset = i
        year = now.year
        month = now.month - month_offset
        while month <= 0:
            month += 12
            year -= 1

        period_label = f"{year}-{month:02d}"
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        total_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date()
        )

        completed_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivered
        )

        failed_query = select(func.count(Delivery.id)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivery_failed
        )

        items_delivered_query = select(func.sum(Delivery.items_delivered)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date(),
            Delivery.status == DeliveryStatus.delivered
        )

        items_picked_up_query = select(func.sum(Delivery.items_picked_up)).where(
            Delivery.scheduled_date >= period_start.date(),
            Delivery.scheduled_date < period_end.date()
        )

        avg_rating_query = (
            select(func.avg(DeliveryFeedback.overall_rating))
            .join(Delivery)
            .where(
                Delivery.scheduled_date >= period_start.date(),
                Delivery.scheduled_date < period_end.date()
            )
        )

        total = (await db.execute(total_query)).scalar() or 0
        completed = (await db.execute(completed_query)).scalar() or 0
        failed = (await db.execute(failed_query)).scalar() or 0
        items_delivered = (await db.execute(items_delivered_query)).scalar() or 0
        items_picked_up = (await db.execute(items_picked_up_query)).scalar() or 0
        avg_rating = (await db.execute(avg_rating_query)).scalar()

        avg_items = items_delivered / completed if completed > 0 else 0

        delivery_reports.append(HomeDeliveryDeliveryReport(
            period=period_label,
            total_deliveries=total,
            completed_deliveries=completed,
            failed_deliveries=failed,
            total_items_delivered=items_delivered,
            total_items_picked_up=items_picked_up,
            average_items_per_delivery=round(avg_items, 2),
            average_rating=round(avg_rating, 2) if avg_rating else None
        ))

    return HomeDeliveryReportResponse(
        summary=HomeDeliveryReportSummary(**summary),
        patron_reports=[HomeDeliveryPatronReport(**r) for r in patron_reports],
        volunteer_reports=[HomeDeliveryVolunteerReport(**r) for r in volunteer_reports],
        delivery_reports=delivery_reports,
        generated_at=datetime.now(timezone.utc)
    )


@router.get("/volunteer-recognition")
async def get_volunteer_recognition(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get volunteer recognition data (top volunteers, milestones, etc.)."""
    # Top volunteers by hours
    top_by_hours = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
        .order_by(DeliveryVolunteer.total_volunteer_hours.desc())
        .limit(10)
    )
    top_hours = top_by_hours.unique().scalars().all()

    # Top volunteers by deliveries
    top_by_deliveries = await db.execute(
        select(DeliveryVolunteer)
        .options(joinedload(DeliveryVolunteer.user))
        .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
        .order_by(DeliveryVolunteer.total_deliveries.desc())
        .limit(10)
    )
    top_deliveries = top_by_deliveries.unique().scalars().all()

    # Recent milestones (volunteers who recently crossed hour thresholds)
    milestones = []
    milestone_thresholds = [50, 100, 250, 500, 1000]

    for volunteer in top_hours:
        for threshold in milestone_thresholds:
            if volunteer.total_volunteer_hours >= threshold:
                # Check if they recently crossed this threshold
                hours_result = await db.execute(
                    select(func.sum(VolunteerHourLog.hours))
                    .where(
                        VolunteerHourLog.volunteer_id == volunteer.id,
                        VolunteerHourLog.date >= (date.today() - timedelta(days=30))
                    )
                )
                recent_hours = hours_result.scalar() or 0

                if volunteer.total_volunteer_hours - recent_hours < threshold:
                    milestones.append({
                        "volunteer_id": volunteer.id,
                        "volunteer_name": volunteer.user.full_name if volunteer.user else "Unknown",
                        "milestone": f"{threshold} hours",
                        "total_hours": volunteer.total_volunteer_hours
                    })
                    break

    # Recognition level distribution
    level_counts = await db.execute(
        select(
            DeliveryVolunteer.recognition_level,
            func.count(DeliveryVolunteer.id)
        )
        .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
        .group_by(DeliveryVolunteer.recognition_level)
    )
    level_distribution = {row[0]: row[1] for row in level_counts.all()}

    return {
        "top_by_hours": [
            {
                "volunteer_id": v.id,
                "name": v.user.full_name if v.user else "Unknown",
                "hours": round(v.total_volunteer_hours, 2),
                "recognition_level": v.recognition_level
            }
            for v in top_hours
        ],
        "top_by_deliveries": [
            {
                "volunteer_id": v.id,
                "name": v.user.full_name if v.user else "Unknown",
                "deliveries": v.total_deliveries,
                "recognition_level": v.recognition_level
            }
            for v in top_deliveries
        ],
        "recent_milestones": milestones,
        "recognition_levels": level_distribution
    }


@router.get("/application-pipeline")
async def get_application_pipeline(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get application pipeline statistics."""
    # Count by status
    status_counts = await db.execute(
        select(
            HomeDeliveryApplication.status,
            func.count(HomeDeliveryApplication.id)
        )
        .group_by(HomeDeliveryApplication.status)
    )
    by_status = {row[0].value: row[1] for row in status_counts.all()}

    # Average processing time (submitted to reviewed)
    processing_time = await db.execute(
        select(
            func.avg(
                func.extract('epoch', HomeDeliveryApplication.reviewed_at) -
                func.extract('epoch', HomeDeliveryApplication.submitted_at)
            ) / 86400  # Convert to days
        )
        .where(HomeDeliveryApplication.reviewed_at.isnot(None))
    )
    avg_processing_days = processing_time.scalar()

    # Weekly trend
    weekly_trend = []
    now = datetime.now(timezone.utc)
    for i in range(8):  # Last 8 weeks
        week_end = now - timedelta(days=i * 7)
        week_start = week_end - timedelta(days=7)

        submitted = await db.execute(
            select(func.count(HomeDeliveryApplication.id))
            .where(
                HomeDeliveryApplication.submitted_at >= week_start,
                HomeDeliveryApplication.submitted_at < week_end
            )
        )

        approved = await db.execute(
            select(func.count(HomeDeliveryApplication.id))
            .where(
                HomeDeliveryApplication.reviewed_at >= week_start,
                HomeDeliveryApplication.reviewed_at < week_end,
                HomeDeliveryApplication.status == HomeDeliveryApplicationStatus.approved
            )
        )

        weekly_trend.append({
            "week": week_start.strftime("%Y-W%W"),
            "submitted": submitted.scalar() or 0,
            "approved": approved.scalar() or 0
        })

    return {
        "by_status": by_status,
        "average_processing_days": round(avg_processing_days, 1) if avg_processing_days else None,
        "weekly_trend": weekly_trend
    }


@router.get("/satisfaction-metrics")
async def get_satisfaction_metrics(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get patron satisfaction metrics."""
    # Overall average ratings
    overall = await db.execute(
        select(
            func.avg(DeliveryFeedback.overall_rating),
            func.avg(DeliveryFeedback.item_satisfaction),
            func.avg(DeliveryFeedback.volunteer_rating),
            func.avg(DeliveryFeedback.timeliness_rating),
            func.count(DeliveryFeedback.id)
        )
    )
    overall_row = overall.one()

    # Would recommend percentage
    recommend_yes = await db.execute(
        select(func.count(DeliveryFeedback.id))
        .where(DeliveryFeedback.would_recommend == True)
    )
    recommend_no = await db.execute(
        select(func.count(DeliveryFeedback.id))
        .where(DeliveryFeedback.would_recommend == False)
    )
    yes_count = recommend_yes.scalar() or 0
    no_count = recommend_no.scalar() or 0
    recommend_rate = yes_count / (yes_count + no_count) * 100 if (yes_count + no_count) > 0 else None

    # Rating distribution
    rating_dist = await db.execute(
        select(
            DeliveryFeedback.overall_rating,
            func.count(DeliveryFeedback.id)
        )
        .group_by(DeliveryFeedback.overall_rating)
    )
    distribution = {row[0]: row[1] for row in rating_dist.all()}

    # Monthly trend
    monthly_trend = []
    now = datetime.now(timezone.utc)
    for i in range(6):
        month_offset = i
        year = now.year
        month = now.month - month_offset
        while month <= 0:
            month += 12
            year -= 1

        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        month_avg = await db.execute(
            select(func.avg(DeliveryFeedback.overall_rating))
            .where(
                DeliveryFeedback.submitted_at >= period_start,
                DeliveryFeedback.submitted_at < period_end
            )
        )

        monthly_trend.append({
            "period": f"{year}-{month:02d}",
            "average_rating": round(month_avg.scalar(), 2) if month_avg.scalar() else None
        })

    # Follow-up statistics
    needs_followup = await db.execute(
        select(func.count(DeliveryFeedback.id))
        .where(
            DeliveryFeedback.requires_follow_up == True,
            DeliveryFeedback.follow_up_completed == False
        )
    )

    completed_followup = await db.execute(
        select(func.count(DeliveryFeedback.id))
        .where(DeliveryFeedback.follow_up_completed == True)
    )

    return {
        "overall_ratings": {
            "overall": round(overall_row[0], 2) if overall_row[0] else None,
            "item_satisfaction": round(overall_row[1], 2) if overall_row[1] else None,
            "volunteer_rating": round(overall_row[2], 2) if overall_row[2] else None,
            "timeliness_rating": round(overall_row[3], 2) if overall_row[3] else None,
            "total_responses": overall_row[4]
        },
        "would_recommend_rate": round(recommend_rate, 1) if recommend_rate else None,
        "rating_distribution": distribution,
        "monthly_trend": monthly_trend,
        "follow_up_stats": {
            "pending_follow_up": needs_followup.scalar() or 0,
            "completed_follow_up": completed_followup.scalar() or 0
        }
    }


# ============================================================================
# Enhanced Analytics
# ============================================================================

@router.get("/analytics/deliveries", response_model=DeliveryAnalytics)
async def get_delivery_analytics(
    start_date: date = Query(None, description="Start of period"),
    end_date: date = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive delivery analytics for a period."""
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Total and successful deliveries
    total_query = select(func.count(Delivery.id)).where(
        Delivery.scheduled_date >= start_date,
        Delivery.scheduled_date <= end_date
    )
    total = (await db.execute(total_query)).scalar() or 0

    successful_query = select(func.count(Delivery.id)).where(
        Delivery.scheduled_date >= start_date,
        Delivery.scheduled_date <= end_date,
        Delivery.status == DeliveryStatus.delivered
    )
    successful = (await db.execute(successful_query)).scalar() or 0

    failed_query = select(func.count(Delivery.id)).where(
        Delivery.scheduled_date >= start_date,
        Delivery.scheduled_date <= end_date,
        Delivery.status == DeliveryStatus.delivery_failed
    )
    failed = (await db.execute(failed_query)).scalar() or 0

    # Items statistics
    items_delivered_query = select(func.sum(Delivery.items_delivered)).where(
        Delivery.scheduled_date >= start_date,
        Delivery.scheduled_date <= end_date,
        Delivery.status == DeliveryStatus.delivered
    )
    items_delivered = (await db.execute(items_delivered_query)).scalar() or 0

    items_picked_up_query = select(func.sum(Delivery.items_picked_up)).where(
        Delivery.scheduled_date >= start_date,
        Delivery.scheduled_date <= end_date
    )
    items_picked_up = (await db.execute(items_picked_up_query)).scalar() or 0

    # Average rating
    avg_rating_query = (
        select(func.avg(DeliveryFeedback.overall_rating))
        .join(Delivery)
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date
        )
    )
    avg_rating = (await db.execute(avg_rating_query)).scalar()

    # Unique patrons served
    unique_patrons_query = (
        select(func.count(func.distinct(HomeDeliveryEnrollment.patron_id)))
        .join(Delivery, Delivery.enrollment_id == HomeDeliveryEnrollment.id)
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date,
            Delivery.status == DeliveryStatus.delivered
        )
    )
    unique_patrons = (await db.execute(unique_patrons_query)).scalar() or 0

    # Deliveries by day of week
    deliveries_by_day_query = (
        select(
            func.to_char(Delivery.scheduled_date, 'Day').label("day_of_week"),
            func.count(Delivery.id)
        )
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date
        )
        .group_by(text("day_of_week"))
    )
    day_results = await db.execute(deliveries_by_day_query)
    deliveries_by_day = {row[0].strip(): row[1] for row in day_results.all()}

    # Deliveries by status
    status_query = (
        select(Delivery.status, func.count(Delivery.id))
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date
        )
        .group_by(Delivery.status)
    )
    status_results = await db.execute(status_query)
    deliveries_by_status = {row[0].value: row[1] for row in status_results.all()}

    # Ratings distribution
    ratings_query = (
        select(DeliveryFeedback.overall_rating, func.count(DeliveryFeedback.id))
        .join(Delivery)
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date
        )
        .group_by(DeliveryFeedback.overall_rating)
    )
    ratings_results = await db.execute(ratings_query)
    ratings_distribution = {row[0]: row[1] for row in ratings_results.all()}

    success_rate = (successful / total * 100) if total > 0 else 0.0
    avg_items = items_delivered / successful if successful > 0 else 0.0

    return DeliveryAnalytics(
        period_start=start_date,
        period_end=end_date,
        total_deliveries=total,
        successful_deliveries=successful,
        failed_deliveries=failed,
        success_rate=round(success_rate, 2),
        average_items_per_delivery=round(avg_items, 2),
        average_rating=round(avg_rating, 2) if avg_rating else None,
        total_items_delivered=items_delivered,
        total_items_picked_up=items_picked_up,
        unique_patrons_served=unique_patrons,
        deliveries_by_day=deliveries_by_day,
        deliveries_by_status=deliveries_by_status,
        ratings_distribution=ratings_distribution
    )


@router.get("/analytics/volunteers", response_model=VolunteerAnalytics)
async def get_volunteer_analytics(
    start_date: date = Query(None, description="Start of period"),
    end_date: date = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive volunteer analytics for a period."""
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Active volunteers
    active_query = select(func.count(DeliveryVolunteer.id)).where(
        DeliveryVolunteer.status == DeliveryVolunteerStatus.active
    )
    active_volunteers = (await db.execute(active_query)).scalar() or 0

    # Hours logged in period
    hours_query = select(func.sum(VolunteerHourLog.hours)).where(
        VolunteerHourLog.date >= start_date,
        VolunteerHourLog.date <= end_date
    )
    total_hours = (await db.execute(hours_query)).scalar() or 0.0

    # Hours by activity type
    activity_hours_query = (
        select(VolunteerHourLog.activity_type, func.sum(VolunteerHourLog.hours))
        .where(
            VolunteerHourLog.date >= start_date,
            VolunteerHourLog.date <= end_date
        )
        .group_by(VolunteerHourLog.activity_type)
    )
    activity_results = await db.execute(activity_hours_query)
    hours_by_activity = {row[0]: float(row[1]) for row in activity_results.all()}

    # Volunteers by status
    status_query = (
        select(DeliveryVolunteer.status, func.count(DeliveryVolunteer.id))
        .group_by(DeliveryVolunteer.status)
    )
    status_results = await db.execute(status_query)
    volunteers_by_status = {row[0].value: row[1] for row in status_results.all()}

    # Top volunteers by hours in period
    top_query = (
        select(
            DeliveryVolunteer.id,
            User.first_name,
            User.last_name,
            func.sum(VolunteerHourLog.hours).label('period_hours')
        )
        .join(VolunteerHourLog, VolunteerHourLog.volunteer_id == DeliveryVolunteer.id)
        .join(User, DeliveryVolunteer.user_id == User.id)
        .where(
            VolunteerHourLog.date >= start_date,
            VolunteerHourLog.date <= end_date
        )
        .group_by(DeliveryVolunteer.id, User.first_name, User.last_name)
        .order_by(func.sum(VolunteerHourLog.hours).desc())
        .limit(10)
    )
    top_results = await db.execute(top_query)
    top_volunteers = [
        {
            "volunteer_id": row[0],
            "name": f"{row[1]} {row[2]}",
            "hours": float(row[3])
        }
        for row in top_results.all()
    ]

    # Calculate deliveries made
    deliveries_query = (
        select(func.count(Delivery.id))
        .join(HomeDeliveryEnrollment, Delivery.enrollment_id == HomeDeliveryEnrollment.id)
        .where(
            Delivery.scheduled_date >= start_date,
            Delivery.scheduled_date <= end_date,
            Delivery.status == DeliveryStatus.delivered
        )
    )
    total_deliveries = (await db.execute(deliveries_query)).scalar() or 0

    avg_hours = total_hours / active_volunteers if active_volunteers > 0 else 0.0
    avg_deliveries = total_deliveries / active_volunteers if active_volunteers > 0 else 0.0

    return VolunteerAnalytics(
        period_start=start_date,
        period_end=end_date,
        total_active_volunteers=active_volunteers,
        total_hours_logged=round(total_hours, 2),
        average_hours_per_volunteer=round(avg_hours, 2),
        total_deliveries_made=total_deliveries,
        average_deliveries_per_volunteer=round(avg_deliveries, 2),
        top_volunteers=top_volunteers,
        volunteers_by_status=volunteers_by_status,
        hours_by_activity_type=hours_by_activity
    )


# ============================================================================
# Combined Service Analytics Dashboard
# ============================================================================

@router.get("/analytics/service", response_model=ServiceAnalytics)
async def get_service_analytics(
    start_date: date = Query(None, description="Start of period"),
    end_date: date = Query(None, description="End of period"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get combined service analytics including deliveries, volunteers, and patrons."""
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Get delivery analytics
    delivery_analytics = await get_delivery_analytics(start_date, end_date, staff_user, db)

    # Get volunteer analytics
    volunteer_analytics = await get_volunteer_analytics(start_date, end_date, staff_user, db)

    # Patron metrics
    active_patrons = await db.execute(
        select(func.count(HomeDeliveryEnrollment.id))
        .where(HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active)
    )
    paused_patrons = await db.execute(
        select(func.count(HomeDeliveryEnrollment.id))
        .where(HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.paused)
    )
    new_patrons = await db.execute(
        select(func.count(HomeDeliveryEnrollment.id))
        .where(
            HomeDeliveryEnrollment.enrolled_at >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc),
            HomeDeliveryEnrollment.enrolled_at <= datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
        )
    )

    patron_metrics = {
        "active_patrons": active_patrons.scalar() or 0,
        "paused_patrons": paused_patrons.scalar() or 0,
        "new_enrollments_in_period": new_patrons.scalar() or 0
    }

    # Trend calculations (compare to previous period)
    period_length = (end_date - start_date).days
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date - timedelta(days=1)

    # Previous period deliveries
    prev_deliveries = await db.execute(
        select(func.count(Delivery.id))
        .where(
            Delivery.scheduled_date >= prev_start,
            Delivery.scheduled_date <= prev_end,
            Delivery.status == DeliveryStatus.delivered
        )
    )
    prev_delivery_count = prev_deliveries.scalar() or 0

    # Calculate trends
    current_deliveries = delivery_analytics.successful_deliveries
    delivery_trend = 0.0
    if prev_delivery_count > 0:
        delivery_trend = ((current_deliveries - prev_delivery_count) / prev_delivery_count) * 100

    trends = {
        "delivery_count_change_pct": round(delivery_trend, 1),
        "period_length_days": period_length,
        "compared_to_previous_period": f"{prev_start} to {prev_end}"
    }

    return ServiceAnalytics(
        period_start=start_date,
        period_end=end_date,
        delivery_analytics=delivery_analytics,
        volunteer_analytics=volunteer_analytics,
        patron_metrics=patron_metrics,
        trends=trends
    )


# ============================================================================
# Route Planning
# ============================================================================

@router.get("/route-suggestions", response_model=RouteSuggestionsResponse)
async def get_route_suggestions(
    target_date: date = Query(..., description="Date to plan routes for"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-suggested route groupings for a date."""
    suggestions = await ClusteringService.suggest_routes_for_date(
        db=db,
        target_date=target_date,
        max_routes=5
    )

    # Count unassigned deliveries
    unassigned_query = select(func.count(Delivery.id)).where(
        Delivery.scheduled_date == target_date,
        Delivery.status == DeliveryStatus.scheduled,
        Delivery.route_id.is_(None)
    )
    unassigned = (await db.execute(unassigned_query)).scalar() or 0

    return RouteSuggestionsResponse(
        date=target_date,
        suggestions=[RouteSuggestion(**s) for s in suggestions],
        unassigned_delivery_count=unassigned
    )


# ============================================================================
# Data Export
# ============================================================================

@router.post("/export", response_model=ExportResponse)
async def request_export(
    request: ExportRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Request a data export (CSV, JSON, or XLSX)."""
    import uuid

    export_id = str(uuid.uuid4())

    # In production, this would queue a background job
    # For now, return a placeholder response
    return ExportResponse(
        export_id=export_id,
        status="processing",
        download_url=None,
        file_name=f"home_delivery_{request.report_type}_{export_id[:8]}.{request.format}",
        record_count=None,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )


@router.get("/export/{export_id}", response_model=ExportResponse)
async def get_export_status(
    export_id: str,
    staff_user: User = Depends(require_staff),
):
    """Check status of an export request."""
    # In production, this would check the actual export job status
    return ExportResponse(
        export_id=export_id,
        status="completed",
        download_url=f"/api/v1/home-delivery/reports/export/{export_id}/download",
        file_name=f"home_delivery_export_{export_id[:8]}.csv",
        record_count=100,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Download an exported file."""
    from fastapi.responses import StreamingResponse
    import io
    import csv

    # Generate CSV data for demonstration
    # In production, this would retrieve the pre-generated file

    output = io.StringIO()
    writer = csv.writer(output)

    # Get recent deliveries for export
    result = await db.execute(
        select(Delivery)
        .options(joinedload(Delivery.enrollment).joinedload(HomeDeliveryEnrollment.patron))
        .order_by(Delivery.scheduled_date.desc())
        .limit(100)
    )
    deliveries = result.unique().scalars().all()

    # Write header
    writer.writerow([
        "Delivery ID", "Patron Name", "Scheduled Date", "Status",
        "Items Count", "Items Delivered", "Delivery Address"
    ])

    # Write data
    for d in deliveries:
        patron_name = d.enrollment.patron.full_name if d.enrollment and d.enrollment.patron else "Unknown"
        writer.writerow([
            d.id,
            patron_name,
            d.scheduled_date,
            str(d.status),
            d.items_count or 0,
            d.items_delivered or 0,
            d.delivery_address
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=deliveries_export_{export_id[:8]}.csv"
        }
    )
