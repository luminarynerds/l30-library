# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive Staff Onboarding API Endpoints

Provides endpoints for:
- Onboarding initialization and management
- Pre-arrival checklist tracking
- Orientation scheduling
- Training module assignments and tracking
- Policy acknowledgments
- System access provisioning
- Check-in meeting scheduling
- Feedback collection
- Probation period tracking
"""
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...models.onboarding import (
    StaffOnboarding, OnboardingStatus, PreArrivalChecklistItem,
    TrainingModule, TrainingModuleAssignment, Policy, PolicyAcknowledgment,
    SystemAccess, SystemAccessProvisioning, CheckInMeeting,
    IntroductionAnnouncement, OnboardingFeedback
)
from ...schemas.onboarding import (
    StaffOnboardingCreateRequest, StaffOnboardingUpdateRequest,
    StaffOnboardingProgressResponse, StaffOnboardingBasicResponse,
    StaffOnboardingListResponse, OnboardingProgressSummary,
    PreArrivalChecklistItemCreateRequest, PreArrivalChecklistItemUpdateRequest,
    PreArrivalChecklistItemResponse, OrientationScheduleCreateRequest,
    OrientationScheduleUpdateRequest, OrientationScheduleResponse,
    TrainingModuleCreateRequest, TrainingModuleResponse,
    TrainingModuleAssignmentCreateRequest, TrainingModuleAssignmentUpdateRequest,
    TrainingModuleAssignmentResponse, PolicyCreateRequest, PolicyResponse,
    PolicyAcknowledgmentCreateRequest, PolicyAcknowledgmentResponse,
    SystemAccessCreateRequest, SystemAccessResponse,
    SystemAccessProvisioningCreateRequest, SystemAccessProvisioningUpdateRequest,
    SystemAccessProvisioningResponse, CheckInMeetingCreateRequest,
    CheckInMeetingUpdateRequest, CheckInMeetingResponse,
    IntroductionAnnouncementCreateRequest, IntroductionAnnouncementUpdateRequest,
    IntroductionAnnouncementResponse, OnboardingFeedbackCreateRequest,
    OnboardingFeedbackResponse
)
from ...services.onboarding_service import (
    StaffOnboardingService, PreArrivalChecklistService,
    OrientationScheduleService, TrainingModuleService, PolicyService,
    SystemAccessService, CheckInMeetingService,
    ProbationService,
    create_feedback as create_onboarding_feedback,
)
from .auth import get_current_user
from .dependencies import require_authenticated, require_staff
from app.core.authorization import require_role
from app.core.datetime_utils import utc_now

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ============================================================================
# Staff Onboarding Endpoints
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED, response_model=StaffOnboardingBasicResponse)
async def create_onboarding(
    request: StaffOnboardingCreateRequest,
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Create a new staff onboarding record (admin/director/super_admin only).

    Matches StaffOnboardingPage's MANAGER_ROLES gate; previously the wider
    `require_staff` allowed STAFF/LEGAL to mutate records the UI hid from them.
    """
    try:
        onboarding = await StaffOnboardingService.create_onboarding(
            db=db,
            user_id=request.user_id,
            department=request.department,
            position=request.position,
            start_date=request.start_date,
            expected_completion_date=request.expected_completion_date,
            manager_id=request.manager_id,
            buddy_mentor_id=request.buddy_mentor_id,
            probation_end_date=request.probation_end_date,
        )
        return onboarding
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/me", response_model=StaffOnboardingProgressResponse)
async def get_my_onboarding(
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's onboarding record with all details."""
    onboarding = await StaffOnboardingService.get_onboarding_by_user(db, current_user.id)
    if not onboarding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No onboarding record found for current user"
        )

    onboarding = await StaffOnboardingService.get_onboarding(db, onboarding.id, include_details=True)
    return onboarding


@router.get("/{onboarding_id}", response_model=StaffOnboardingProgressResponse)
async def get_onboarding(
    onboarding_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get onboarding record by ID (staff only)."""
    onboarding = await StaffOnboardingService.get_onboarding(db, onboarding_id, include_details=True)
    if not onboarding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding record not found"
        )
    return onboarding


@router.patch("/{onboarding_id}", response_model=StaffOnboardingBasicResponse)
async def update_onboarding(
    onboarding_id: int,
    request: StaffOnboardingUpdateRequest,
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """Update onboarding record (admin/director/super_admin only).

    Matches StaffOnboardingPage's MANAGER_ROLES gate; see create_onboarding.
    """
    onboarding = await StaffOnboardingService.get_onboarding(db, onboarding_id)
    if not onboarding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding record not found"
        )

    # Update fields
    if request.status:
        onboarding.status = request.status
    if request.department:
        onboarding.department = request.department
    if request.position:
        onboarding.position = request.position
    if request.expected_completion_date:
        onboarding.expected_completion_date = request.expected_completion_date
    if request.actual_completion_date:
        onboarding.actual_completion_date = request.actual_completion_date
    if request.manager_id:
        onboarding.manager_id = request.manager_id
    if request.buddy_mentor_id:
        onboarding.buddy_mentor_id = request.buddy_mentor_id
        onboarding.buddy_mentor_assigned_at = utc_now()
    if request.probation_status:
        onboarding.probation_status = request.probation_status
    if request.notes:
        onboarding.notes = request.notes

    await db.commit()

    # Recalculate progress_percentage so PATCH callers can't leave
    # status/percentage out of sync (e.g. status=completed with 0%).
    # update_progress walks all checklist relationships and issues its
    # own commit, so the flush above is required for status changes
    # to be visible in that recalculation.
    await StaffOnboardingService.update_progress(db, onboarding_id)
    await db.refresh(onboarding)
    return onboarding


@router.get("", response_model=List[StaffOnboardingListResponse])
async def list_onboardings(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List onboarding records (staff only, with optional filters)."""
    query = select(StaffOnboarding)

    if status:
        query = query.where(StaffOnboarding.status == status)
    if department:
        query = query.where(StaffOnboarding.department == department)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/progress/summary", response_model=OnboardingProgressSummary)
async def get_progress_summary(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get onboarding progress summary (staff only)."""
    result = await db.execute(select(StaffOnboarding))
    onboardings = result.scalars().all()

    in_progress = sum(1 for o in onboardings if o.status == OnboardingStatus.in_progress)
    completed = sum(1 for o in onboardings if o.status == OnboardingStatus.completed)
    pending = sum(1 for o in onboardings if o.status == OnboardingStatus.pending)
    on_hold = sum(1 for o in onboardings if o.status == OnboardingStatus.on_hold)
    overdue = sum(1 for o in onboardings if o.expected_completion_date < date.today() and o.status != OnboardingStatus.completed)

    average_progress = (
        sum(o.progress_percentage for o in onboardings) / len(onboardings)
        if onboardings else 0
    )

    return OnboardingProgressSummary(
        total_onboarding_count=len(onboardings),
        in_progress_count=in_progress,
        completed_count=completed,
        pending_count=pending,
        on_hold_count=on_hold,
        average_progress_percentage=average_progress,
        overdue_count=overdue,
        probation_failures_count=0,
    )


# ============================================================================
# Pre-Arrival Checklist Endpoints
# ============================================================================

@router.post("/{onboarding_id}/pre-arrival-checklist", status_code=status.HTTP_201_CREATED, response_model=PreArrivalChecklistItemResponse)
async def create_checklist_item(
    onboarding_id: int,
    request: PreArrivalChecklistItemCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a pre-arrival checklist item (staff only)."""
    try:
        item = await PreArrivalChecklistService.create_item(
            db=db,
            onboarding_id=onboarding_id,
            title=request.title,
            category=request.category,
            description=request.description,
            assigned_to_id=request.assigned_to_id,
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{onboarding_id}/pre-arrival-checklist/{item_id}", response_model=PreArrivalChecklistItemResponse)
async def update_checklist_item(
    onboarding_id: int,
    item_id: int,
    request: PreArrivalChecklistItemUpdateRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a pre-arrival checklist item."""
    try:
        item = await PreArrivalChecklistService.update_item(
            db=db,
            item_id=item_id,
            status=request.status,
            notes=request.notes,
            evidence_url=request.evidence_url,
        )
        await StaffOnboardingService.update_progress(db, onboarding_id)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Orientation Schedule Endpoints
# ============================================================================

@router.post("/{onboarding_id}/orientation", status_code=status.HTTP_201_CREATED, response_model=OrientationScheduleResponse)
async def create_orientation_item(
    onboarding_id: int,
    request: OrientationScheduleCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create an orientation schedule item (staff only)."""
    try:
        schedule = await OrientationScheduleService.create_item(
            db=db,
            onboarding_id=onboarding_id,
            activity_title=request.activity_title,
            scheduled_time=request.scheduled_time,
            duration_minutes=request.duration_minutes,
            description=request.description,
            location=request.location,
            facilitator_id=request.facilitator_id,
        )
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{onboarding_id}/orientation/{item_id}", response_model=OrientationScheduleResponse)
async def update_orientation_item(
    onboarding_id: int,
    item_id: int,
    request: OrientationScheduleUpdateRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update an orientation schedule item."""
    try:
        item = await OrientationScheduleService.update_item(
            db=db,
            item_id=item_id,
            status=request.status,
            notes=request.notes,
        )
        await StaffOnboardingService.update_progress(db, onboarding_id)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Training Module Endpoints
# ============================================================================

@router.post("/training-modules", status_code=status.HTTP_201_CREATED, response_model=TrainingModuleResponse)
async def create_training_module(
    request: TrainingModuleCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a training module (staff only)."""
    try:
        module = await TrainingModuleService.create_module(
            db=db,
            title=request.title,
            category=request.category,
            duration_minutes=request.duration_minutes,
            delivery_type=request.delivery_type,
            description=request.description,
            is_mandatory=request.is_mandatory,
            content_url=request.content_url,
            passing_score=request.passing_score,
            order=request.order,
        )
        return module
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{onboarding_id}/training-assignments", status_code=status.HTTP_201_CREATED, response_model=TrainingModuleAssignmentResponse)
async def assign_training_module(
    onboarding_id: int,
    request: TrainingModuleAssignmentCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign a training module to a staff member (staff only)."""
    try:
        assignment = await TrainingModuleService.assign_module(
            db=db,
            onboarding_id=onboarding_id,
            training_module_id=request.training_module_id,
            due_date=request.due_date,
        )
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{onboarding_id}/training-assignments/{assignment_id}", response_model=TrainingModuleAssignmentResponse)
async def update_training_assignment(
    onboarding_id: int,
    assignment_id: int,
    request: TrainingModuleAssignmentUpdateRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a training module assignment."""
    try:
        assignment = await TrainingModuleService.update_assignment(
            db=db,
            assignment_id=assignment_id,
            status=request.status,
            score=request.score,
            verified_by_id=request.verified_by_id,
        )
        await StaffOnboardingService.update_progress(db, onboarding_id)
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Policy Endpoints
# ============================================================================

@router.post("/policies", status_code=status.HTTP_201_CREATED, response_model=PolicyResponse)
async def create_policy(
    request: PolicyCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new policy (staff only)."""
    try:
        policy = await PolicyService.create_policy(
            db=db,
            title=request.title,
            content=request.content,
            category=request.category,
            effective_date=request.effective_date,
            version=request.version,
            description=request.description,
            is_mandatory=request.is_mandatory,
        )
        return policy
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    category: Optional[str] = Query(None),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List all policies."""
    query = select(Policy)
    if category:
        query = query.where(Policy.category == category)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{onboarding_id}/acknowledge-policy", status_code=status.HTTP_201_CREATED, response_model=PolicyAcknowledgmentResponse)
async def acknowledge_policy(
    onboarding_id: int,
    request: PolicyAcknowledgmentCreateRequest,
    http_request: Request,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a policy."""
    try:
        # Capture client IP for the audit trail. `request` is the Pydantic body
        # param, so the FastAPI Request is bound to `http_request`.
        client_ip = http_request.client.host if http_request.client else None
        acknowledgment = await PolicyService.acknowledge_policy(
            db=db,
            onboarding_id=onboarding_id,
            policy_id=request.policy_id,
            acknowledged_by_id=current_user.id,
            ip_address=client_ip,
        )
        return acknowledgment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# System Access Endpoints
# ============================================================================

@router.post("/systems", status_code=status.HTTP_201_CREATED, response_model=SystemAccessResponse)
async def create_system_access(
    request: SystemAccessCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a system access record (staff only)."""
    try:
        system = await SystemAccessService.create_system(
            db=db,
            system_name=request.system_name,
            access_type=request.access_type,
            description=request.description,
            provisioning_instructions=request.provisioning_instructions,
            deprovisioning_instructions=request.deprovisioning_instructions,
        )
        return system
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/systems", response_model=List[SystemAccessResponse])
async def list_systems(
    access_type: Optional[str] = Query(None),
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List all system access records."""
    query = select(SystemAccess)
    if access_type:
        query = query.where(SystemAccess.access_type == access_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{onboarding_id}/request-access", status_code=status.HTTP_201_CREATED, response_model=SystemAccessProvisioningResponse)
async def request_system_access(
    onboarding_id: int,
    request: SystemAccessProvisioningCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Request system access provisioning (staff only)."""
    try:
        provisioning = await SystemAccessService.request_access(
            db=db,
            onboarding_id=onboarding_id,
            system_access_id=request.system_access_id,
            requested_by_id=current_user.id,
        )
        return provisioning
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{onboarding_id}/system-access/{provisioning_id}", response_model=SystemAccessProvisioningResponse)
async def update_system_access(
    onboarding_id: int,
    provisioning_id: int,
    request: SystemAccessProvisioningUpdateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update system access provisioning status (staff only)."""
    try:
        provisioning = await SystemAccessService.provision_access(
            db=db,
            provisioning_id=provisioning_id,
            provisioned_by_id=current_user.id,
        )
        await StaffOnboardingService.update_progress(db, onboarding_id)
        return provisioning
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Check-in Meeting Endpoints
# ============================================================================

@router.post("/{onboarding_id}/check-in-meetings", status_code=status.HTTP_201_CREATED, response_model=CheckInMeetingResponse)
async def schedule_check_in_meeting(
    onboarding_id: int,
    request: CheckInMeetingCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a check-in meeting (staff only)."""
    try:
        meeting = await CheckInMeetingService.schedule_meeting(
            db=db,
            onboarding_id=onboarding_id,
            period=request.period,
            scheduled_date=request.scheduled_date,
            scheduled_with_id=request.scheduled_with_id,
            topics=request.topics,
        )
        return meeting
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{onboarding_id}/check-in-meetings/{meeting_id}", response_model=CheckInMeetingResponse)
async def complete_check_in_meeting(
    onboarding_id: int,
    meeting_id: int,
    request: CheckInMeetingUpdateRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Complete a check-in meeting."""
    try:
        meeting = await CheckInMeetingService.complete_meeting(
            db=db,
            meeting_id=meeting_id,
            meeting_notes=request.meeting_notes,
            feedback_from_new_hire=request.feedback_from_new_hire,
            feedback_from_manager=request.feedback_from_manager,
            action_items=request.action_items,
        )
        await StaffOnboardingService.update_progress(db, onboarding_id)
        return meeting
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Introduction Announcement Endpoints
# ============================================================================

@router.post("/{onboarding_id}/introduction-announcements", status_code=status.HTTP_201_CREATED, response_model=IntroductionAnnouncementResponse)
async def create_introduction_announcement(
    onboarding_id: int,
    request: IntroductionAnnouncementCreateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create an introduction announcement for a new staff member (staff only)."""
    announcement = IntroductionAnnouncement(
        onboarding_id=onboarding_id,
        title=request.title,
        content=request.content,
        announcement_type=request.announcement_type,
        scheduled_date=request.scheduled_date,
        distributed_to=request.distributed_to,
        created_by_id=current_user.id,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return announcement


@router.get("/{onboarding_id}/introduction-announcements", response_model=List[IntroductionAnnouncementResponse])
async def list_introduction_announcements(
    onboarding_id: int,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List all introduction announcements for an onboarding record."""
    result = await db.execute(
        select(IntroductionAnnouncement).where(
            IntroductionAnnouncement.onboarding_id == onboarding_id
        )
    )
    return result.scalars().all()


@router.patch("/{onboarding_id}/introduction-announcements/{announcement_id}", response_model=IntroductionAnnouncementResponse)
async def update_introduction_announcement(
    onboarding_id: int,
    announcement_id: int,
    request: IntroductionAnnouncementUpdateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update an introduction announcement (staff only)."""
    result = await db.execute(
        select(IntroductionAnnouncement).where(IntroductionAnnouncement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )

    if request.title:
        announcement.title = request.title
    if request.content:
        announcement.content = request.content
    if request.announcement_type:
        announcement.announcement_type = request.announcement_type
    if request.scheduled_date:
        announcement.scheduled_date = request.scheduled_date
    if request.distributed_to is not None:
        announcement.distributed_to = request.distributed_to
    if request.published_at:
        announcement.published_at = request.published_at
    if request.published_by_id:
        announcement.published_by_id = request.published_by_id

    await db.commit()
    await db.refresh(announcement)
    return announcement


# ============================================================================
# Feedback Endpoints
# ============================================================================

@router.post("/{onboarding_id}/feedback", status_code=status.HTTP_201_CREATED, response_model=OnboardingFeedbackResponse)
async def create_feedback(
    onboarding_id: int,
    request: OnboardingFeedbackCreateRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create onboarding feedback."""
    try:
        feedback = await create_onboarding_feedback(
            db=db,
            onboarding_id=onboarding_id,
            feedback_type=request.feedback_type,
            provided_by_id=current_user.id,
            rating=request.rating,
            comments=request.comments,
            is_anonymous=request.is_anonymous,
        )
        return feedback
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============================================================================
# Dynamic Configuration Endpoints
# ============================================================================

from pydantic import BaseModel

class CheckInPeriodOption(BaseModel):
    key: str
    label: str
    days_offset: int | None = None

class FeedbackTypeOption(BaseModel):
    key: str
    label: str


@router.get("/config/periods", response_model=list[CheckInPeriodOption])
async def get_checkin_periods(
    current_user: User = Depends(require_authenticated),
):
    """Get all available check-in meeting periods for form population.

    Returns the standard onboarding check-in periods used across the system.
    """
    periods = [
        CheckInPeriodOption(key="first_day", label="First Day", days_offset=0),
        CheckInPeriodOption(key="one_week", label="One Week", days_offset=7),
        CheckInPeriodOption(key="thirty_day", label="30 Day", days_offset=30),
        CheckInPeriodOption(key="sixty_day", label="60 Day", days_offset=60),
        CheckInPeriodOption(key="ninety_day", label="90 Day", days_offset=90),
    ]
    return periods


@router.get("/config/feedback-types", response_model=list[FeedbackTypeOption])
async def get_feedback_types(
    current_user: User = Depends(require_authenticated),
):
    """Get all available feedback types for form population.

    Returns the feedback categories used in onboarding feedback collection.
    """
    feedback_types = [
        FeedbackTypeOption(key="training", label="Training Quality"),
        FeedbackTypeOption(key="orientation", label="Orientation"),
        FeedbackTypeOption(key="buddy_mentor", label="Buddy/Mentor Support"),
        FeedbackTypeOption(key="system_access", label="System Access"),
        FeedbackTypeOption(key="general", label="General Feedback"),
    ]
    return feedback_types


class ChecklistCategoryOption(BaseModel):
    key: str
    label: str


class FollowUpPeriodOption(BaseModel):
    key: str
    label: str
    days_offset: int


@router.get("/config/checklist-categories", response_model=list[ChecklistCategoryOption])
async def get_checklist_categories(
    current_user: User = Depends(require_authenticated),
):
    """Get all available pre-arrival checklist categories for form population.

    Returns the categories used to organize pre-arrival checklist items.
    """
    categories = [
        ChecklistCategoryOption(key="office", label="Office Setup"),
        ChecklistCategoryOption(key="equipment", label="Equipment"),
        ChecklistCategoryOption(key="accounts", label="System Accounts"),
        ChecklistCategoryOption(key="keys", label="Keys & Access"),
        ChecklistCategoryOption(key="paperwork", label="Paperwork & Forms"),
        ChecklistCategoryOption(key="other", label="Other"),
    ]
    return categories


@router.get("/config/follow-up-periods", response_model=list[FollowUpPeriodOption])
async def get_follow_up_periods(
    current_user: User = Depends(require_authenticated),
):
    """Get available follow-up period options for check-in meetings.

    Returns the standard time periods for scheduling follow-up check-in meetings
    with new staff members during their onboarding.
    """
    return [
        FollowUpPeriodOption(
            key="one_week",
            label="1 Week",
            days_offset=7,
        ),
        FollowUpPeriodOption(
            key="two_weeks",
            label="2 Weeks",
            days_offset=14,
        ),
        FollowUpPeriodOption(
            key="one_month",
            label="1 Month",
            days_offset=30,
        ),
        FollowUpPeriodOption(
            key="thirty_days",
            label="30 Days",
            days_offset=30,
        ),
    ]
