# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Usage Statistics API for IMLS/PLA Reporting.

Provides endpoints for:
- Circulation, collection, patron, program statistics
- Computer usage, reference questions, visits tracking
- Trend analysis (month-over-month, year-over-year)
- Peer comparison data management
- Report export (CSV, Excel, PDF) with HTTP 206 Partial Content support
- IMLS Survey data generation
"""

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils.range_response import create_range_response

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.usage_statistics import (
    CirculationStatistics, CollectionStatistics, ComputerUsageStatistics,
    PatronStatistics, PeerComparisonData, PeerComparisonLibrary,
    ProgramStatistics, ReferenceQuestion, ReferenceStatistics,
    StatisticalReport, ReportStatus, UsageStatisticsSettings,
    VisitCount, VisitStatistics,
)
from ...models.user import User
from ...schemas.usage_statistics import (
    CirculationStatisticsCreate, CirculationStatisticsResponse,
    CirculationStatisticsSummary, CollectionStatisticsCreate,
    CollectionStatisticsResponse, CollectionStatisticsSummary,
    ComputerUsageStatisticsCreate, ComputerUsageStatisticsResponse,
    ComputerUsageSummary, ExportFormat, IMLSSurveyData,
    MonthOverMonthTrend, PatronStatisticsCreate, PatronStatisticsResponse,
    PatronStatisticsSummary, PeerComparisonDataCreate,
    PeerComparisonDataResponse, PeerComparisonReport, PeerComparisonResult,
    PeerLibraryCreate, PeerLibraryResponse, PeerLibraryUpdate,
    PeriodType, ProgramStatisticsCreate, ProgramStatisticsResponse,
    ProgramStatisticsSummary, ReferenceQuestionCreate,
    ReferenceQuestionResponse, ReferenceStatisticsCreate,
    ReferenceStatisticsResponse, ReferenceStatisticsSummary,
    StatisticalReportCreate, StatisticalReportResponse,
    StatisticsExportRequest, UsageStatisticsDashboard,
    UsageStatisticsSettingsCreate, UsageStatisticsSettingsResponse,
    UsageStatisticsSettingsUpdate, VisitCountCreate, VisitCountResponse,
    VisitCountUpdate, VisitStatisticsCreate, VisitStatisticsResponse,
    VisitStatisticsSummary, YearOverYearTrend,
)
from ...services.usage_statistics_service import UsageStatisticsService
from ...services.statistics_export_service import StatisticsExportService
from .auth import get_current_user
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/usage-statistics", tags=["usage-statistics"])


# ============================================================================
# Dashboard Endpoints
# ============================================================================


@router.get("/dashboard", response_model=UsageStatisticsDashboard)
@limiter.limit("20/hour")
async def get_statistics_dashboard(
    request: Request,
    period_start: date = Query(..., description="Start date of period"),
    period_end: date = Query(..., description="End date of period"),
    period_type: PeriodType = Query(PeriodType.MONTHLY, description="Period type"),
    branch_location: Optional[str] = Query(None, description="Branch filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get comprehensive usage statistics dashboard.

    Returns all statistics summaries for a given period including:
    - Circulation statistics
    - Collection statistics
    - Patron statistics
    - Program statistics
    - Computer usage
    - Reference transactions
    - Visit counts

    Rate Limit: 20 requests per hour (expensive aggregation queries)
    """
    service = UsageStatisticsService(db)
    return await service.get_dashboard(
        period_start, period_end, period_type.value, branch_location
    )


# ============================================================================
# Circulation Statistics
# ============================================================================


@router.get("/circulation/summary", response_model=CirculationStatisticsSummary)
async def get_circulation_summary(
    period_start: date = Query(..., description="Start date of period"),
    period_end: date = Query(..., description="End date of period"),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get circulation statistics summary for a period."""
    service = UsageStatisticsService(db)
    return await service.get_circulation_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/circulation", response_model=CirculationStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_circulation_statistics(
    data: CirculationStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually create/override circulation statistics for a period."""
    service = UsageStatisticsService(db)
    return await service.generate_circulation_statistics(
        data.period_start,
        data.period_end,
        str(data.period_type),
        data.branch_location,
        current_user.id,
        branch_id=data.branch_id,
    )


@router.get("/circulation/history", response_model=List[CirculationStatisticsResponse])
async def get_circulation_history(
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get historical circulation statistics."""
    result = await db.execute(
        select(CirculationStatistics)
        .where(
            CirculationStatistics.period_type == period_type.value,
            CirculationStatistics.branch_location == branch_location,
        )
        .order_by(CirculationStatistics.period_start.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ============================================================================
# Collection Statistics
# ============================================================================


@router.get("/collection/summary", response_model=CollectionStatisticsSummary)
async def get_collection_summary(
    snapshot_date: Optional[date] = Query(None, description="Snapshot date (defaults to today)"),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get collection statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_collection_summary(snapshot_date, branch_location, branch_id=branch_id)


@router.post("/collection", response_model=CollectionStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_collection_statistics(
    data: CollectionStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually create collection statistics snapshot."""
    service = UsageStatisticsService(db)
    return await service.generate_collection_statistics(
        data.snapshot_date,
        data.branch_location,
        current_user.id,
        branch_id=data.branch_id,
    )


# ============================================================================
# Patron Statistics
# ============================================================================


@router.get("/patron/summary", response_model=PatronStatisticsSummary)
async def get_patron_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None, description="Legacy branch label; prefer branch_id"),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3 tranche 1)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get patron statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_patron_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/patron", response_model=PatronStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_patron_statistics(
    data: PatronStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually create patron statistics for a period."""
    service = UsageStatisticsService(db)
    return await service.generate_patron_statistics(
        data.period_start,
        data.period_end,
        str(data.period_type),
        data.branch_location,
        current_user.id,
        branch_id=data.branch_id,
    )


# ============================================================================
# Program Statistics
# ============================================================================


@router.get("/program/summary", response_model=ProgramStatisticsSummary)
async def get_program_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get program/event statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_program_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/program", response_model=ProgramStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_program_statistics(
    data: ProgramStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually create program statistics for a period."""
    service = UsageStatisticsService(db)
    return await service.generate_program_statistics(
        data.period_start,
        data.period_end,
        str(data.period_type),
        data.branch_location,
        current_user.id,
        branch_id=data.branch_id,
    )


# ============================================================================
# Computer Usage Statistics
# ============================================================================


@router.get("/computer/summary", response_model=ComputerUsageSummary)
async def get_computer_usage_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get computer usage statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_computer_usage_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/computer", response_model=ComputerUsageStatisticsResponse, status_code=status.HTTP_201_CREATED)
async def create_computer_usage_statistics(
    data: ComputerUsageStatisticsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually create computer usage statistics for a period."""
    stats = ComputerUsageStatistics(
        period_start=data.period_start,
        period_end=data.period_end,
        period_type=str(data.period_type),
        branch_location=data.branch_location,
        total_sessions=data.total_sessions,
        unique_users=data.unique_users,
        total_hours_used=data.total_hours_used,
        avg_session_length_minutes=data.avg_session_length_minutes,
        sessions_by_hour_of_day=data.sessions_by_hour_of_day,
        sessions_by_day_of_week=data.sessions_by_day_of_week,
        wifi_sessions=data.wifi_sessions,
        wifi_unique_devices=data.wifi_unique_devices,
        print_jobs=data.print_jobs,
        pages_printed=data.pages_printed,
        generated_by_id=current_user.id,
    )
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats


# ============================================================================
# Reference Questions
# ============================================================================


@router.get("/reference/summary", response_model=ReferenceStatisticsSummary)
async def get_reference_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get reference statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_reference_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/reference/questions", response_model=ReferenceQuestionResponse, status_code=status.HTTP_201_CREATED)
async def log_reference_question(
    data: ReferenceQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Log a reference question for statistics tracking."""
    question = ReferenceQuestion(
        asked_at=data.asked_at or datetime.now(timezone.utc),
        branch_location=data.branch_location,
        question_type=data.question_type,
        contact_method=data.contact_method,
        duration_minutes=data.duration_minutes,
        patron_type=data.patron_type,
        subject_area=data.subject_area,
        was_referred=data.was_referred,
        referred_to=data.referred_to,
        answered_by_id=current_user.id,
        notes=data.notes,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


@router.get("/reference/questions", response_model=List[ReferenceQuestionResponse])
async def list_reference_questions(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    branch_location: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List logged reference questions."""
    query = select(ReferenceQuestion)

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.where(ReferenceQuestion.asked_at >= start_dt)

    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.where(ReferenceQuestion.asked_at <= end_dt)

    if branch_location:
        query = query.where(ReferenceQuestion.branch_location == branch_location)

    query = query.order_by(ReferenceQuestion.asked_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# ============================================================================
# Visit Statistics
# ============================================================================


@router.get("/visits/summary", response_model=VisitStatisticsSummary)
async def get_visit_summary(
    period_start: date = Query(...),
    period_end: date = Query(...),
    period_type: PeriodType = Query(PeriodType.MONTHLY),
    branch_location: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None, description="Branch FK (Phase 3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get visit statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_visit_summary(
        period_start, period_end, period_type.value, branch_location,
        branch_id=branch_id,
    )


@router.post("/visits/count", response_model=VisitCountResponse, status_code=status.HTTP_201_CREATED)
async def record_visit_count(
    data: VisitCountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Record daily visit/door count."""
    # Check for existing record
    existing_result = await db.execute(
        select(VisitCount).where(
            VisitCount.count_date == data.count_date,
            VisitCount.branch_location == data.branch_location,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Visit count already exists for {data.count_date}. Use PATCH to update.",
        )

    # Calculate adjusted count if adjustment factor provided
    adjusted_count = None
    if data.adjustment_factor:
        adjusted_count = int(data.door_count * data.adjustment_factor)

    visit_count = VisitCount(
        count_date=data.count_date,
        branch_location=data.branch_location,
        door_count=data.door_count,
        count_source=data.count_source,
        counts_by_hour=data.counts_by_hour,
        adjustment_factor=data.adjustment_factor,
        adjusted_count=adjusted_count,
        weather_notes=data.weather_notes,
        special_circumstances=data.special_circumstances,
        recorded_by_id=current_user.id,
    )
    db.add(visit_count)
    await db.commit()
    await db.refresh(visit_count)
    return visit_count


@router.patch("/visits/count/{count_date}", response_model=VisitCountResponse)
async def update_visit_count(
    count_date: date,
    data: VisitCountUpdate,
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an existing visit count."""
    result = await db.execute(
        select(VisitCount).where(
            VisitCount.count_date == count_date,
            VisitCount.branch_location == branch_location,
        )
    )
    visit_count = result.scalar_one_or_none()

    if not visit_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit count not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(visit_count, field, value)

    # Recalculate adjusted count
    if visit_count.adjustment_factor:
        visit_count.adjusted_count = int(visit_count.door_count * float(visit_count.adjustment_factor))

    await db.commit()
    await db.refresh(visit_count)
    return visit_count


@router.get("/visits/counts", response_model=List[VisitCountResponse])
async def list_visit_counts(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List daily visit counts for a date range."""
    query = select(VisitCount).where(
        VisitCount.count_date >= start_date,
        VisitCount.count_date <= end_date,
    )

    if branch_location:
        query = query.where(VisitCount.branch_location == branch_location)

    query = query.order_by(VisitCount.count_date.desc())

    result = await db.execute(query)
    return result.scalars().all()


# ============================================================================
# Trend Analysis
# ============================================================================


@router.get("/trends/month-over-month", response_model=List[MonthOverMonthTrend])
async def get_month_over_month_trends(
    metric: str = Query(..., description="Metric name (checkouts, visits, registrations, programs, attendance, reference)"),
    months: int = Query(12, ge=3, le=36),
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get month-over-month trends for a metric.

    Supported metrics: checkouts, visits, registrations, programs, attendance, reference
    """
    valid_metrics = ["checkouts", "visits", "registrations", "programs", "attendance", "reference"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    service = UsageStatisticsService(db)
    return await service.get_month_over_month_trends(metric, months, branch_location)


@router.get("/trends/year-over-year", response_model=List[YearOverYearTrend])
async def get_year_over_year_trends(
    metric: str = Query(...),
    years: int = Query(3, ge=2, le=10),
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get year-over-year trends for a metric.

    Supported metrics: checkouts, visits, registrations, programs, attendance, reference
    """
    valid_metrics = ["checkouts", "visits", "registrations", "programs", "attendance", "reference"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}",
        )

    service = UsageStatisticsService(db)
    return await service.get_year_over_year_trends(metric, years, branch_location)


# ============================================================================
# Peer Comparison
# ============================================================================


@router.get("/peers", response_model=List[PeerLibraryResponse])
async def list_peer_libraries(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List peer libraries for comparison."""
    query = select(PeerComparisonLibrary)
    if not include_inactive:
        query = query.where(PeerComparisonLibrary.is_active == True)
    query = query.order_by(PeerComparisonLibrary.library_name)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/peers", response_model=PeerLibraryResponse, status_code=status.HTTP_201_CREATED)
async def create_peer_library(
    data: PeerLibraryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Add a peer library for comparison."""
    library = PeerComparisonLibrary(
        library_name=data.library_name,
        library_id=data.library_id,
        state=data.state,
        city=data.city,
        population_served=data.population_served,
        total_operating_expenditure=data.total_operating_expenditure,
        total_staff_fte=data.total_staff_fte,
        collection_size=data.collection_size,
        service_area_sq_miles=data.service_area_sq_miles,
        is_our_library=data.is_our_library,
        notes=data.notes,
        added_by_id=current_user.id,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.patch("/peers/{peer_id}", response_model=PeerLibraryResponse)
async def update_peer_library(
    peer_id: int,
    data: PeerLibraryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a peer library."""
    library = await get_or_404(db, PeerComparisonLibrary, peer_id, "Peer library not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(library, field, value)

    await db.commit()
    await db.refresh(library)
    return library


@router.delete("/peers/{peer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_peer_library(
    peer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a peer library (soft delete - sets inactive)."""
    library = await get_or_404(db, PeerComparisonLibrary, peer_id, "Peer library not found")

    library.is_active = False
    await db.commit()


@router.post("/peers/{peer_id}/data", response_model=PeerComparisonDataResponse, status_code=status.HTTP_201_CREATED)
async def add_peer_comparison_data(
    peer_id: int,
    data: PeerComparisonDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Add annual statistics data for a peer library."""
    # Verify library exists
    await get_or_404(db, PeerComparisonLibrary, peer_id, "Peer library not found")

    # Check for existing data for this year
    existing_result = await db.execute(
        select(PeerComparisonData).where(
            PeerComparisonData.peer_library_id == peer_id,
            PeerComparisonData.data_year == data.data_year,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data already exists for {data.data_year}. Use PATCH to update.",
        )

    comparison_data = PeerComparisonData(
        peer_library_id=peer_id,
        data_year=data.data_year,
        data_source=data.data_source,
        total_circulation=data.total_circulation,
        total_visits=data.total_visits,
        registered_borrowers=data.registered_borrowers,
        total_programs=data.total_programs,
        total_program_attendance=data.total_program_attendance,
        reference_transactions=data.reference_transactions,
        computer_uses=data.computer_uses,
        print_collection=data.print_collection,
        electronic_collection=data.electronic_collection,
        audio_collection=data.audio_collection,
        video_collection=data.video_collection,
        total_operating_revenue=data.total_operating_revenue,
        total_operating_expenditure=data.total_operating_expenditure,
        collection_expenditure=data.collection_expenditure,
        staff_expenditure=data.staff_expenditure,
        total_staff_fte=data.total_staff_fte,
        librarian_fte=data.librarian_fte,
        circulation_per_capita=data.circulation_per_capita,
        visits_per_capita=data.visits_per_capita,
        expenditure_per_capita=data.expenditure_per_capita,
        additional_metrics=data.additional_metrics,
        notes=data.notes,
        imported_by_id=current_user.id,
    )
    db.add(comparison_data)
    await db.commit()
    await db.refresh(comparison_data)
    return comparison_data


@router.get("/peers/comparison/{data_year}", response_model=List[PeerComparisonResult])
async def get_peer_comparison(
    data_year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get peer comparison analysis for a given year."""
    service = UsageStatisticsService(db)
    return await service.get_peer_comparison(data_year)


# ============================================================================
# Reports & Exports
# ============================================================================


@router.post("/export", response_model=StatisticalReportResponse)
@limiter.limit("10/hour")
async def export_statistics(
    request: Request,
    export_request: StatisticsExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Export statistics to file (CSV, Excel, or PDF).

    Rate Limit: 10 requests per hour (resource-intensive operation)
    """
    service = StatisticsExportService(db)
    return await service.export_statistics(export_request, current_user.id)


@router.get("/reports", response_model=List[StatisticalReportResponse])
async def list_reports(
    report_type: Optional[str] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List generated statistical reports."""
    query = select(StatisticalReport)

    if report_type:
        query = query.where(StatisticalReport.report_type == report_type)
    if status:
        query = query.where(StatisticalReport.status == status)

    query = query.order_by(StatisticalReport.generated_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/reports/{report_id}", response_model=StatisticalReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get a specific statistical report."""
    report = await get_or_404(db, StatisticalReport, report_id, "Report not found")

    return report


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Download a generated report file.

    Supports HTTP 206 Partial Content for resumable downloads:
    - Use Range header to request specific byte ranges
    - Example: Range: bytes=0-1023 (first 1KB)
    - Example: Range: bytes=1024- (from 1KB to end)

    Returns:
    - 200 OK: Full file content (no Range header)
    - 206 Partial Content: Requested byte range(s)
    - 304 Not Modified: If ETag matches (cache hit)
    - 416 Range Not Satisfiable: Invalid range requested
    """
    report = await get_or_404(db, StatisticalReport, report_id, "Report not found")

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Report status is {report.status}")

    if not report.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report file not available")

    # Only update download count on initial request (not range requests)
    range_header = request.headers.get("range")
    if not range_header:
        report.download_count += 1
        report.last_downloaded_at = datetime.now(timezone.utc)
        await db.commit()

    # Determine media type
    media_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
    }
    media_type = media_types.get(report.file_format, "application/octet-stream")

    # Return range-aware response with streaming support
    return await create_range_response(
        request=request,
        file_path=report.file_path,
        media_type=media_type,
        filename=f"{report.report_name}.{report.file_format}",
        include_etag=True
    )


@router.post("/imls-survey/{fiscal_year}", response_model=StatisticalReportResponse)
@limiter.limit("5/hour")
async def generate_imls_survey(
    request: Request,
    fiscal_year: int,
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Generate IMLS Public Libraries Survey formatted data.

    Rate Limit: 5 requests per hour (comprehensive data aggregation)
    """
    service = StatisticsExportService(db)
    return await service.export_imls_survey(fiscal_year, branch_location, current_user.id)


@router.get("/imls-survey/{fiscal_year}/data", response_model=IMLSSurveyData)
async def get_imls_survey_data(
    fiscal_year: int,
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get IMLS survey data without generating a report file."""
    service = UsageStatisticsService(db)
    return await service.generate_imls_survey_data(fiscal_year, branch_location)


# ============================================================================
# Settings
# ============================================================================


@router.get("/settings", response_model=List[UsageStatisticsSettingsResponse])
async def list_settings(
    branch_location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List usage statistics settings."""
    query = select(UsageStatisticsSettings).where(
        UsageStatisticsSettings.is_active == True
    )
    if branch_location:
        query = query.where(UsageStatisticsSettings.branch_location == branch_location)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/settings", response_model=UsageStatisticsSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_settings(
    data: UsageStatisticsSettingsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create usage statistics settings."""
    settings = UsageStatisticsSettings(
        branch_location=data.branch_location,
        auto_generate_daily=data.auto_generate_daily,
        auto_generate_weekly=data.auto_generate_weekly,
        auto_generate_monthly=data.auto_generate_monthly,
        auto_generate_yearly=data.auto_generate_yearly,
        fiscal_year_start_month=data.fiscal_year_start_month,
        legal_service_area_population=data.legal_service_area_population,
        population_data_year=data.population_data_year,
        door_counter_enabled=data.door_counter_enabled,
        door_counter_adjustment_factor=data.door_counter_adjustment_factor,
        reference_sampling_enabled=data.reference_sampling_enabled,
        reference_sample_weeks=data.reference_sample_weeks,
        reference_extrapolation_factor=data.reference_extrapolation_factor,
        imls_library_id=data.imls_library_id,
        state_library_id=data.state_library_id,
        created_by_id=current_user.id,
    )
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.patch("/settings/{settings_id}", response_model=UsageStatisticsSettingsResponse)
async def update_settings(
    settings_id: int,
    data: UsageStatisticsSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update usage statistics settings."""
    settings = await get_or_404(db, UsageStatisticsSettings, settings_id, "Settings not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/circulation", response_model=CirculationStatisticsSummary)
async def get_circulation(
    period_start: date = Query(..., description="Start date of period"),
    period_end: date = Query(..., description="End date of period"),
    period_type: PeriodType = Query(PeriodType.MONTHLY, description="Period type"),
    branch_location: Optional[str] = Query(None, description="Branch filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get circulation statistics summary for a period."""
    service = UsageStatisticsService(db)
    return await service.get_circulation_summary(
        period_start, period_end, period_type.value, branch_location
    )



@router.get("/collection", response_model=CollectionStatisticsSummary)
async def get_collection(
    snapshot_date: Optional[date] = Query(None, description="Snapshot date (defaults to latest)"),
    branch_location: Optional[str] = Query(None, description="Branch filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get collection statistics summary."""
    service = UsageStatisticsService(db)
    return await service.get_collection_summary(snapshot_date, branch_location)



@router.get("/computer", response_model=ComputerUsageSummary)
async def get_computer(
    period_start: date = Query(..., description="Start date of period"),
    period_end: date = Query(..., description="End date of period"),
    period_type: PeriodType = Query(PeriodType.MONTHLY, description="Period type"),
    branch_location: Optional[str] = Query(None, description="Branch filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get computer usage statistics summary for a period."""
    service = UsageStatisticsService(db)
    return await service.get_computer_usage_summary(
        period_start, period_end, period_type.value, branch_location
    )



@router.get("/imls-survey/{fiscal_year}", response_model=IMLSSurveyData)
async def get_imls_survey__fiscal_year_(
    fiscal_year: int,
    branch_location: Optional[str] = Query(None, description="Branch filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get IMLS survey data for a fiscal year."""
    service = UsageStatisticsService(db)
    return await service.generate_imls_survey_data(fiscal_year, branch_location)

