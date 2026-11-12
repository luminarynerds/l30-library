# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fair Scheduling System API Endpoints

Provides REST API for:
- Constraint-based schedule generation
- Schedule transparency and explanations
- Preference learning
- Call-out coverage management
- Exhaustion/fatigue monitoring
- Payroll integration
- Staff scheduling profiles
- Fair scheduling dashboard
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_staff, require_admin
from ...models import User
from ...schemas.fair_scheduling import (
    # Schedule Generation
    ScheduleGenerationCreate, ScheduleGenerationResponse, SchedulePublishRequest,
    # Explanations
    ScheduleExplanationResponse, StaffScheduleExplanation,
    # Preferences
    LearnedPreferenceResponse, PreferenceLearningRequest,
    PreferenceConfirmRequest, StaffPreferenceSummary,
    # Callout
    CalloutCreateRequest, CalloutCoverageResponse, CoverageCandidate,
    CoverageAssignRequest, CoverageResponseRecord,
    # Fatigue
    FatigueRecordResponse, TeamFatigueResponse,
    # Payroll
    PayrollExportRequest, PayrollExportResponse, PayrollSummaryResponse,
    PayrollApproveRequest, PayrollRecordResponse,
    PayrollPolicyResponse, PayrollPolicyUpdate,
    # Profiles
    StaffSchedulingProfileCreate, StaffSchedulingProfileUpdate,
    StaffSchedulingProfileResponse,
    # Dashboard
    FairSchedulingDashboardResponse,
    # My Shifts
    MyShiftResponse, MyShiftsResponse,
)

router = APIRouter(prefix="/fair-scheduling", tags=["fair-scheduling"])


# ============================================================================
# My Shifts (current user's upcoming shifts — for the staff dashboard tile)
# ============================================================================

@router.get("/me/shifts", response_model=MyShiftsResponse, dependencies=[Depends(require_staff)])
async def get_my_shifts(
    days_ahead: int = Query(14, ge=1, le=60),
    include_today: bool = Query(True),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return upcoming shifts for the current staff member, plus open swap/callout flags.

    Used by the staff dashboard's "My Shifts" tile. Excludes cancelled shifts.
    """
    from datetime import timedelta
    from ...models.staff_schedule_fairness import StaffShift, ShiftStatus
    from ...models.shift_swap import ShiftSwapListing, ShiftSwapListingStatus
    from ...models.fair_scheduling import CalloutCoverageRequest, CalloutStatus

    today = date.today()
    range_start = today if include_today else today + timedelta(days=1)
    range_end = today + timedelta(days=days_ahead)

    shifts_result = await db.execute(
        select(StaffShift)
        .where(
            StaffShift.staff_id == current_user.id,
            StaffShift.shift_date >= range_start,
            StaffShift.shift_date <= range_end,
            StaffShift.status != ShiftStatus.CANCELLED,
        )
        .order_by(StaffShift.shift_date.asc(), StaffShift.scheduled_start.asc())
    )
    shifts = shifts_result.scalars().all()

    if not shifts:
        return MyShiftsResponse(shifts=[], range_start=range_start, range_end=range_end)

    shift_ids = [s.id for s in shifts]

    # Open swap listings — match by (date, start, end) composite since ShiftSwapListing
    # has no FK to StaffShift. Adding end_time reduces false positives when a staffer
    # has two shifts on the same day with the same start (e.g. split shift, two branches).
    # A proper fix would add a shift_id FK via migration.
    swap_result = await db.execute(
        select(
            ShiftSwapListing.shift_date,
            ShiftSwapListing.shift_start_time,
            ShiftSwapListing.shift_end_time,
        ).where(
            ShiftSwapListing.user_id == current_user.id,
            ShiftSwapListing.shift_date >= range_start,
            ShiftSwapListing.shift_date <= range_end,
            ShiftSwapListing.status == ShiftSwapListingStatus.open,
            ShiftSwapListing.listing_type == "giving_away",
        )
    )
    swap_keys = {(row[0], row[1], row[2]) for row in swap_result.all()}

    # Open callout coverage requests for this staffer's shifts
    callout_result = await db.execute(
        select(CalloutCoverageRequest.original_shift_id).where(
            CalloutCoverageRequest.original_shift_id.in_(shift_ids),
            CalloutCoverageRequest.callout_staff_id == current_user.id,
            CalloutCoverageRequest.status.in_([CalloutStatus.OPEN, CalloutStatus.SEARCHING, CalloutStatus.PARTIAL]),
        )
    )
    callout_shift_ids = {row[0] for row in callout_result.all()}

    return MyShiftsResponse(
        shifts=[
            MyShiftResponse(
                shift_id=s.id,
                branch_id=s.branch_id,
                shift_date=s.shift_date,
                shift_type=s.shift_type.value if hasattr(s.shift_type, "value") else str(s.shift_type),
                status=s.status.value if hasattr(s.status, "value") else str(s.status),
                scheduled_start=s.scheduled_start,
                scheduled_end=s.scheduled_end,
                scheduled_hours=s.scheduled_hours,
                is_holiday=s.is_holiday,
                is_weekend=s.is_weekend,
                has_open_swap=(s.shift_date, s.scheduled_start, s.scheduled_end) in swap_keys,
                has_open_callout=s.id in callout_shift_ids,
            )
            for s in shifts
        ],
        range_start=range_start,
        range_end=range_end,
    )


# ============================================================================
# Schedule Generation (Constraint Solver)
# ============================================================================

@router.post("/generate", response_model=ScheduleGenerationResponse, dependencies=[Depends(require_staff)])
async def generate_schedule(
    request: ScheduleGenerationCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Generate an optimized fair schedule using the constraint solver."""
    try:
        from ...services.constraint_schedule_solver import ConstraintScheduleSolver
        solver = ConstraintScheduleSolver(db)
        generation, result = await solver.generate_schedule(
            branch_id=request.branch_id,
            period_start=request.period_start,
            period_end=request.period_end,
            generated_by_id=current_user.id,
            config=request.solver_config,
        )
        return ScheduleGenerationResponse.model_validate(generation)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/generations", response_model=list, dependencies=[Depends(require_staff)])
async def list_generations(
    branch_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List recent schedule generation runs."""
    from ...models.fair_scheduling import ScheduleGeneration

    stmt = select(ScheduleGeneration)
    if branch_id:
        stmt = stmt.where(ScheduleGeneration.branch_id == branch_id)

    result = await db.execute(
        stmt.order_by(ScheduleGeneration.created_at.desc()).limit(limit)
    )
    generations = result.scalars().all()
    return [ScheduleGenerationResponse.model_validate(g) for g in generations]


@router.get("/generations/{generation_id}", response_model=ScheduleGenerationResponse, dependencies=[Depends(require_staff)])
async def get_generation(
    generation_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a schedule generation run."""
    from ...models.fair_scheduling import ScheduleGeneration

    result = await db.execute(
        select(ScheduleGeneration).where(ScheduleGeneration.id == generation_id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    return ScheduleGenerationResponse.model_validate(gen)


@router.post("/generations/{generation_id}/publish", response_model=ScheduleGenerationResponse, dependencies=[Depends(require_staff)])
async def publish_schedule(
    generation_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Publish a generated schedule, making it the active schedule."""
    from ...models.fair_scheduling import ScheduleGeneration, ScheduleGenerationStatus

    result = await db.execute(
        select(ScheduleGeneration).where(ScheduleGeneration.id == generation_id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    if gen.status not in (ScheduleGenerationStatus.OPTIMAL, ScheduleGenerationStatus.FEASIBLE):
        raise HTTPException(status_code=400, detail="Can only publish optimal or feasible schedules")

    gen.is_published = True
    gen.published_at = datetime.now()
    gen.published_by_id = current_user.id
    await db.commit()
    return ScheduleGenerationResponse.model_validate(gen)


# ============================================================================
# Schedule Explanations (Transparency)
# ============================================================================

@router.get("/explanations/{generation_id}", response_model=list, dependencies=[Depends(require_staff)])
async def get_schedule_explanations(
    generation_id: int,
    staff_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get explanations for why shifts were assigned in a generation."""
    from ...models.fair_scheduling import ScheduleExplanation

    stmt = select(ScheduleExplanation).where(ScheduleExplanation.generation_id == generation_id)
    if staff_id:
        stmt = stmt.where(ScheduleExplanation.staff_id == staff_id)

    result = await db.execute(stmt)
    explanations = result.scalars().all()
    return [ScheduleExplanationResponse.model_validate(e) for e in explanations]


@router.get("/explanations/staff/{staff_id}", response_model=StaffScheduleExplanation, dependencies=[Depends(require_staff)])
async def get_staff_schedule_explanation(
    staff_id: int,
    generation_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive explanation for a staff member's schedule."""
    from ...models.fair_scheduling import ScheduleExplanation, ScheduleGeneration
    from ...models.staff_schedule_fairness import ScheduleBalanceMetrics

    # Get latest generation if not specified
    if not generation_id:
        gen_result = await db.execute(
            select(ScheduleGeneration).order_by(ScheduleGeneration.created_at.desc())
        )
        gen = gen_result.scalar_one_or_none()
        if gen:
            generation_id = gen.id

    explanations_result = await db.execute(
        select(ScheduleExplanation).where(
            ScheduleExplanation.staff_id == staff_id,
            ScheduleExplanation.generation_id == generation_id,
        )
    )
    explanations = explanations_result.scalars().all()

    user_result = await db.execute(select(User).where(User.id == staff_id))
    user = user_result.scalar_one_or_none()
    name = f"{user.first_name} {user.last_name}" if user and hasattr(user, 'first_name') else f"#{staff_id}"

    total_hours = sum(e.fairness_impact for e in explanations)
    metrics_result = await db.execute(
        select(ScheduleBalanceMetrics)
        .where(ScheduleBalanceMetrics.staff_id == staff_id)
        .order_by(ScheduleBalanceMetrics.period_end.desc())
    )
    metrics = metrics_result.scalar_one_or_none()

    # Count preference matches
    pref_honored = sum(1 for e in explanations if "preference" in e.explanation_type.value.lower())

    # Get top factors
    factor_counts = {}
    for e in explanations:
        for f in (e.contributing_factors or []):
            fname = f.get("factor", "")
            if fname not in factor_counts:
                factor_counts[fname] = 0
            factor_counts[fname] += 1
    top_factors = sorted(factor_counts.keys(), key=lambda k: factor_counts[k], reverse=True)[:5]

    return StaffScheduleExplanation(
        staff_id=staff_id,
        staff_name=name,
        total_shifts=len(explanations),
        total_hours=round(total_hours, 1),
        fairness_score=metrics.overall_fairness_score if metrics else 0,
        explanations=[ScheduleExplanationResponse.model_validate(e) for e in explanations],
        preference_honor_rate=round(pref_honored / max(len(explanations), 1), 2),
        top_factors=top_factors,
    )


# ============================================================================
# Preference Learning
# ============================================================================

@router.post("/preferences/learn", response_model=list, dependencies=[Depends(require_staff)])
async def learn_staff_preferences(
    request: PreferenceLearningRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Run preference learning for a staff member."""
    try:
        from ...services.preference_learning_service import PreferenceLearningService
        service = PreferenceLearningService(db)
        prefs = await service.learn_preferences(
            staff_id=request.staff_id,
            lookback_days=request.lookback_days,
        )
        return [LearnedPreferenceResponse.model_validate(p) for p in prefs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/preferences/learned/{staff_id}", response_model=list, dependencies=[Depends(require_staff)])
async def get_learned_preferences(
    staff_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all learned preferences for a staff member."""
    from ...services.preference_learning_service import PreferenceLearningService
    service = PreferenceLearningService(db)
    prefs = await service.get_staff_preferences(staff_id)
    return [LearnedPreferenceResponse.model_validate(p) for p in prefs]


@router.post("/preferences/{preference_id}/confirm", response_model=LearnedPreferenceResponse, dependencies=[Depends(require_staff)])
async def confirm_learned_preference(
    preference_id: int,
    request: PreferenceConfirmRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff confirms or rejects a learned preference."""
    from ...services.preference_learning_service import PreferenceLearningService
    service = PreferenceLearningService(db)
    pref = await service.confirm_preference(
        staff_id=current_user.id,
        preference_id=preference_id,
        confirmed=request.confirmed,
    )
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found or not yours")
    return LearnedPreferenceResponse.model_validate(pref)


# ============================================================================
# Call-Out Coverage
# ============================================================================

@router.post("/callout", response_model=CalloutCoverageResponse, dependencies=[Depends(require_staff)])
async def create_callout(
    request: CalloutCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record a staff call-out and begin coverage search."""
    try:
        from ...services.callout_coverage_service import CalloutCoverageService
        service = CalloutCoverageService(db)
        result = await service.create_callout(
            branch_id=request.branch_id,
            shift_id=request.shift_id,
            callout_staff_id=request.callout_staff_id,
            callout_reason=request.callout_reason,
            handled_by_id=current_user.id,
        )
        return CalloutCoverageResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/callout/open", response_model=list, dependencies=[Depends(require_staff)])
async def get_open_callouts(
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all open call-out coverage requests."""
    from ...services.callout_coverage_service import CalloutCoverageService
    service = CalloutCoverageService(db)
    requests = await service.get_open_requests(branch_id)
    return [CalloutCoverageResponse.model_validate(r) for r in requests]


@router.get("/callout/{request_id}/candidates", response_model=list, dependencies=[Depends(require_staff)])
async def get_coverage_candidates(
    request_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get ranked candidates for covering a call-out."""
    try:
        from ...services.callout_coverage_service import CalloutCoverageService
        service = CalloutCoverageService(db)
        candidates = await service.get_coverage_candidates(request_id)
        return [CoverageCandidate(**c) for c in candidates]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/callout/{request_id}/assign", response_model=CalloutCoverageResponse, dependencies=[Depends(require_staff)])
async def assign_callout_coverage(
    request_id: int,
    request: CoverageAssignRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign a staff member to cover a call-out."""
    try:
        from ...services.callout_coverage_service import CalloutCoverageService
        service = CalloutCoverageService(db)
        result = await service.assign_coverage(
            request_id=request_id,
            covering_staff_id=request.covering_staff_id,
            notes=request.notes,
        )
        return CalloutCoverageResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/callout/{request_id}/respond", response_model=CalloutCoverageResponse, dependencies=[Depends(require_staff)])
async def respond_to_callout(
    request_id: int,
    response: CoverageResponseRecord,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record a staff member's response to a coverage request."""
    try:
        from ...services.callout_coverage_service import CalloutCoverageService
        service = CalloutCoverageService(db)
        result = await service.record_staff_response(
            request_id=request_id,
            staff_id=response.staff_id,
            response=response.response,
            reason=response.reason,
        )
        return CalloutCoverageResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Exhaustion / Fatigue Tracking
# ============================================================================

@router.get("/fatigue/{staff_id}", response_model=FatigueRecordResponse, dependencies=[Depends(require_staff)])
async def get_staff_fatigue(
    staff_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get current fatigue level for a staff member."""
    try:
        from ...services.exhaustion_tracking_service import ExhaustionTrackingService
        service = ExhaustionTrackingService(db)
        record = await service.calculate_fatigue(staff_id)
        return FatigueRecordResponse.model_validate(record)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/fatigue/{staff_id}/history", response_model=list, dependencies=[Depends(require_staff)])
async def get_fatigue_history(
    staff_id: int,
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get fatigue history for a staff member."""
    from ...services.exhaustion_tracking_service import ExhaustionTrackingService
    service = ExhaustionTrackingService(db)
    records = await service.get_fatigue_history(staff_id, days)
    return [FatigueRecordResponse.model_validate(r) for r in records]


@router.get("/fatigue/team/{branch_id}", response_model=TeamFatigueResponse, dependencies=[Depends(require_staff)])
async def get_team_fatigue(
    branch_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get fatigue summary for all staff at a branch."""
    from ...services.exhaustion_tracking_service import ExhaustionTrackingService
    service = ExhaustionTrackingService(db)
    results = await service.get_team_fatigue(branch_id)

    fatigue_levels = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    for r in results:
        level = r.get("fatigue_level", "low")
        fatigue_levels[level] = fatigue_levels.get(level, 0) + 1

    avg_score = sum(r["fatigue_score"] for r in results) / max(len(results), 1)

    return TeamFatigueResponse(
        branch_id=branch_id,
        as_of_date=date.today(),
        staff_fatigue=results,
        critical_count=fatigue_levels["critical"],
        high_count=fatigue_levels["high"],
        moderate_count=fatigue_levels["moderate"],
        low_count=fatigue_levels["low"],
        average_score=round(avg_score, 1),
    )


# ============================================================================
# Payroll Integration
# ============================================================================

@router.post("/payroll/generate", response_model=list, dependencies=[Depends(require_admin)])
async def generate_payroll(
    pay_period_start: date = Query(...),
    pay_period_end: date = Query(...),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generate payroll records for a pay period."""
    try:
        from ...services.payroll_integration_service import PayrollIntegrationService
        service = PayrollIntegrationService(db)
        records = await service.generate_payroll_records(branch_id, pay_period_start, pay_period_end)
        return [PayrollRecordResponse.model_validate(r) for r in records]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/payroll/export", response_model=PayrollExportResponse, dependencies=[Depends(require_admin)])
async def export_payroll(
    request: PayrollExportRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export payroll data in specified format."""
    try:
        from ...services.payroll_integration_service import PayrollIntegrationService
        service = PayrollIntegrationService(db)
        batch, data = await service.export_payroll(
            branch_id=request.branch_id,
            pay_period_start=request.pay_period_start,
            pay_period_end=request.pay_period_end,
            export_format=request.export_format,
            exported_by_id=current_user.id,
        )
        return PayrollExportResponse(
            batch_id=batch.batch_id,
            export_status=str(batch.export_status),
            total_records=batch.total_records,
            total_regular_hours=batch.total_regular_hours,
            total_overtime_hours=batch.total_overtime_hours,
            total_holiday_hours=batch.total_holiday_hours,
            export_format=batch.export_format,
            exported_at=batch.exported_at,
            error_message=batch.error_message,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/payroll/summary", response_model=PayrollSummaryResponse, dependencies=[Depends(require_admin)])
async def get_payroll_summary(
    pay_period_start: date = Query(...),
    pay_period_end: date = Query(...),
    branch_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get payroll summary for a pay period."""
    from ...services.payroll_integration_service import PayrollIntegrationService
    service = PayrollIntegrationService(db)
    summary = await service.get_payroll_summary(branch_id, pay_period_start, pay_period_end)
    return PayrollSummaryResponse(**summary)


@router.post("/payroll/approve", dependencies=[Depends(require_admin)])
async def approve_payroll(
    request: PayrollApproveRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve payroll records for a pay period."""
    from ...services.payroll_integration_service import PayrollIntegrationService
    service = PayrollIntegrationService(db)
    count = await service.approve_payroll(
        pay_period_start=request.pay_period_start,
        pay_period_end=request.pay_period_end,
        approved_by_id=current_user.id,
        staff_id=request.staff_id,
    )
    return {"approved_count": count}


@router.get("/payroll/policy", response_model=PayrollPolicyResponse, dependencies=[Depends(require_admin)])
async def get_payroll_policy(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Current pay policy; lazily seeds the default row when missing."""
    from ...models.fair_scheduling import PayrollPolicy

    policy = await db.get(PayrollPolicy, 1)
    if policy is None:
        policy = PayrollPolicy(id=1)
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
    return PayrollPolicyResponse.model_validate(policy)


@router.put("/payroll/policy", response_model=PayrollPolicyResponse, dependencies=[Depends(require_admin)])
async def update_payroll_policy(
    update: PayrollPolicyUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Partial update. Applies to future payroll runs only: generated records
    keep the multipliers they were stamped with."""
    from ...models.fair_scheduling import PayrollPolicy

    policy = await db.get(PayrollPolicy, 1)
    if policy is None:
        policy = PayrollPolicy(id=1)
        db.add(policy)

    for key, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(policy, key, value)
    policy.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(policy)
    return PayrollPolicyResponse.model_validate(policy)


# ============================================================================
# Staff Scheduling Profiles
# ============================================================================

@router.post("/profiles", response_model=StaffSchedulingProfileResponse, dependencies=[Depends(require_admin)])
async def create_scheduling_profile(
    profile: StaffSchedulingProfileCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a scheduling profile for a staff member."""
    from ...models.fair_scheduling import StaffSchedulingProfile
    new_profile = StaffSchedulingProfile(**profile.dict())
    db.add(new_profile)
    await db.commit()
    return StaffSchedulingProfileResponse.model_validate(new_profile)


@router.get("/profiles/{staff_id}", response_model=StaffSchedulingProfileResponse, dependencies=[Depends(require_staff)])
async def get_scheduling_profile(
    staff_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get scheduling profile for a staff member."""
    from ...models.fair_scheduling import StaffSchedulingProfile

    result = await db.execute(
        select(StaffSchedulingProfile).where(StaffSchedulingProfile.staff_id == staff_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return StaffSchedulingProfileResponse.model_validate(profile)


@router.put("/profiles/{staff_id}", response_model=StaffSchedulingProfileResponse, dependencies=[Depends(require_admin)])
async def update_scheduling_profile(
    staff_id: int,
    update: StaffSchedulingProfileUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update scheduling profile for a staff member."""
    from ...models.fair_scheduling import StaffSchedulingProfile

    result = await db.execute(
        select(StaffSchedulingProfile).where(StaffSchedulingProfile.staff_id == staff_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in update.dict(exclude_unset=True).items():
        if value is not None:
            setattr(profile, key, value)

    await db.commit()
    return StaffSchedulingProfileResponse.model_validate(profile)


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/dashboard", response_model=FairSchedulingDashboardResponse, dependencies=[Depends(require_staff)])
async def get_fair_scheduling_dashboard(
    branch_id: int = Query(...),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive fair scheduling dashboard."""
    from ...models.fair_scheduling import (
        ScheduleGeneration, CalloutCoverageRequest, CalloutStatus,
        StaffSchedulingProfile,
    )
    from ...models.staff_schedule_fairness import ScheduleBalanceMetrics
    from ...services.exhaustion_tracking_service import ExhaustionTrackingService

    # Latest generation
    latest_gen_result = await db.execute(
        select(ScheduleGeneration)
        .where(ScheduleGeneration.branch_id == branch_id)
        .order_by(ScheduleGeneration.created_at.desc())
    )
    latest_gen = latest_gen_result.scalar_one_or_none()

    # Staff fairness scores — JOIN User to avoid N+1
    metrics_result = await db.execute(
        select(ScheduleBalanceMetrics, User.first_name, User.last_name)
        .outerjoin(User, User.id == ScheduleBalanceMetrics.staff_id)
        .where(ScheduleBalanceMetrics.branch_id == branch_id)
    )
    rows = metrics_result.all()
    metrics = [row[0] for row in rows]

    staff_fairness = []
    for row in rows:
        m, first_name, last_name = row
        name = f"{first_name} {last_name}" if first_name else f"#{m.staff_id}"
        staff_fairness.append({
            "staff_id": m.staff_id,
            "name": name,
            "overall_score": m.overall_fairness_score,
            "hours_score": m.hours_fairness_score,
            "weekend_score": m.weekend_fairness_score,
            "shift_type_score": m.shift_type_fairness_score,
            "total_hours": m.total_hours_scheduled,
        })

    overall_fairness = (
        sum(m.overall_fairness_score for m in metrics) / max(len(metrics), 1)
        if metrics else 0
    )

    # Fatigue summary
    try:
        fatigue_service = ExhaustionTrackingService(db)
        fatigue_results = await fatigue_service.get_team_fatigue(branch_id)
        fatigue_levels = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
        for r in fatigue_results:
            level = r.get("fatigue_level", "low")
            fatigue_levels[level] = fatigue_levels.get(level, 0) + 1
        fatigue_summary = {
            "total_staff": len(fatigue_results),
            "levels": fatigue_levels,
            "average_score": round(
                sum(r["fatigue_score"] for r in fatigue_results) / max(len(fatigue_results), 1), 1
            ),
            "alerts": [r for r in fatigue_results if r.get("alert")],
        }
    except Exception:  # noqa: BLE001  # fatigue summary best-effort — return empty on any failure
        fatigue_summary = {"total_staff": 0, "levels": {}, "average_score": 0, "alerts": []}

    # Open callouts
    open_callouts_result = await db.execute(
        select(CalloutCoverageRequest).where(
            CalloutCoverageRequest.branch_id == branch_id,
            CalloutCoverageRequest.status.in_([CalloutStatus.OPEN, CalloutStatus.SEARCHING]),
        )
    )
    open_callouts = open_callouts_result.scalars().all()

    # Preference insights — SQL aggregation instead of loading all rows
    from ...models.fair_scheduling import LearnedPreference
    pref_stats = (await db.execute(
        select(
            func.count(LearnedPreference.id).label("total_learned"),
            func.count(LearnedPreference.id).filter(LearnedPreference.is_confirmed == True).label("confirmed"),
            func.count(LearnedPreference.id).filter(LearnedPreference.confidence >= 0.7).label("high_confidence"),
        )
    )).one()
    preference_insights = {
        "total_learned": pref_stats.total_learned,
        "confirmed": pref_stats.confirmed,
        "high_confidence": pref_stats.high_confidence,
    }

    # Payroll status
    from ...models.fair_scheduling import PayrollExportBatch
    latest_batch_result = await db.execute(
        select(PayrollExportBatch).order_by(PayrollExportBatch.id.desc()).limit(1)
    )
    latest_batch = latest_batch_result.scalars().first()
    payroll_status = {
        "latest_batch": latest_batch.batch_id if latest_batch else None,
        "latest_status": str(latest_batch.export_status) if latest_batch else "none",
        "latest_period": str(latest_batch.pay_period_start) if latest_batch else None,
    }

    return FairSchedulingDashboardResponse(
        current_generation=ScheduleGenerationResponse.model_validate(latest_gen) if latest_gen else None,
        overall_fairness_score=round(overall_fairness, 1),
        staff_fairness=staff_fairness,
        fatigue_summary=fatigue_summary,
        open_callouts=[CalloutCoverageResponse.model_validate(c) for c in open_callouts],
        preference_insights=preference_insights,
        payroll_status=payroll_status,
        upcoming_highlights=[],
    )
