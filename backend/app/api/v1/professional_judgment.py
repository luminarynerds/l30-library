# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Professional Judgment API routes for L30.

Supports staff as trusted professionals with endpoints for:
- Policy overrides (reason-based, not permission-based)
- Committee participation
- Project leadership and proposals
- Policy feedback and voice
- Expertise recognition and registry
- Professional development planning
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.professional_judgment import (
    StaffCommittee as Committee,
    StaffCommitteeMember as CommitteeMember,
    ExpertiseRecognition,
    MembershipStatus,
    PolicyFeedback,
    PolicyOverride,
    ProfessionalDevelopmentActivity,
    ProfessionalDevelopmentPlan,
    StaffExpertise,
    StaffProject,
)
from ...models.user import User, UserRole
from ...schemas.professional_judgment import (
    CommitteeCreate,
    CommitteeMemberCreate,
    CommitteeMemberResponse,
    CommitteeMemberUpdate,
    CommitteeResponse,
    CommitteeUpdate,
    DevelopmentActivityCreate,
    DevelopmentActivityResponse,
    DevelopmentActivityUpdate,
    ExpertiseRecognitionCreate,
    ExpertiseRecognitionResponse,
    PolicyFeedbackCreate,
    PolicyFeedbackListResponse,
    PolicyFeedbackResponse,
    PolicyFeedbackReview,
    PolicyOverrideCreate,
    PolicyOverrideListResponse,
    PolicyOverrideResponse,
    PolicyOverrideUpdate,
    ProfessionalDevelopmentPlanCreate,
    ProfessionalDevelopmentPlanResponse,
    ProfessionalDevelopmentPlanUpdate,
    StaffExpertiseCreate,
    StaffExpertiseResponse,
    StaffExpertiseUpdate,
    StaffProjectApproval,
    StaffProjectCreate,
    StaffProjectListResponse,
    StaffProjectResponse,
    StaffProjectUpdate,
)

from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/professional-judgment", tags=["professional-judgment"])


_ADMIN_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def _require_org_id(user: User) -> int:
    org_id = getattr(user, "organization_id", None)
    if org_id is None:
        raise HTTPException(status_code=400, detail="User has no organization")
    return org_id


def _is_admin(user: User) -> bool:
    return getattr(user, "role", None) in _ADMIN_ROLES


# ============================================================================
# Policy Override Endpoints
# ============================================================================


@router.post("/overrides", response_model=PolicyOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_override(
    data: PolicyOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Record a policy override with professional reasoning.

    Override with reason, not permission. Any staff member can override
    standard policy by providing a clear rationale.
    """
    override = PolicyOverride(
        organization_id=_require_org_id(current_user),
        staff_id=current_user.id,
        policy_area=data.policy_area,
        standard_policy=data.standard_policy,
        action_taken=data.action_taken,
        reasoning=data.reasoning,
        patron_circumstance=data.patron_circumstance,
        category=data.category,
        financial_impact=data.financial_impact,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return override


@router.get("/overrides", response_model=list[PolicyOverrideListResponse])
async def list_policy_overrides(
    policy_area: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List policy overrides, optionally filtered by policy area."""
    query = select(PolicyOverride).order_by(PolicyOverride.created_at.desc())
    if policy_area:
        query = query.where(PolicyOverride.policy_area == policy_area)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/overrides/{override_id}", response_model=PolicyOverrideResponse)
async def get_policy_override(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of a specific policy override."""
    override = await get_or_404(db, PolicyOverride, override_id, "Override not found")
    return override


@router.patch("/overrides/{override_id}", response_model=PolicyOverrideResponse)
async def update_policy_override(
    override_id: int,
    data: PolicyOverrideUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a policy override (outcome, review, status).

    Only the original author or an admin may edit. A policy override is a
    record of the staff member's own reasoning; peers must not rewrite it.
    """
    override = await get_or_404(db, PolicyOverride, override_id, "Override not found")

    if override.staff_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only the author or an admin may edit this override")

    update_data = data.model_dump(exclude_unset=True)
    if "review_notes" in update_data:
        override.reviewed_by_id = current_user.id
        override.review_date = sa_func.now()
    for field, value in update_data.items():
        setattr(override, field, value)

    await db.commit()
    await db.refresh(override)
    return override


# ============================================================================
# Committee Endpoints
# ============================================================================


@router.post("/committees", response_model=CommitteeResponse, status_code=status.HTTP_201_CREATED)
async def create_committee(
    data: CommitteeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Propose a new committee or working group.

    Any staff member can propose a new committee by describing the purpose
    and expected outcomes.
    """
    committee = Committee(
        organization_id=_require_org_id(current_user),
        name=data.name,
        purpose=data.purpose,
        meeting_frequency=data.meeting_frequency,
        is_standing=data.is_standing,
        focus_areas=data.focus_areas,
        expected_outcomes=data.expected_outcomes,
        proposed_by_id=current_user.id,
    )
    db.add(committee)
    await db.commit()
    await db.refresh(committee)
    return committee


@router.get("/committees", response_model=list[CommitteeResponse])
async def list_committees(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all committees, optionally filtered by status."""
    query = select(Committee).order_by(Committee.name)
    if status_filter:
        query = query.where(Committee.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/committees/{committee_id}", response_model=CommitteeResponse)
async def get_committee(
    committee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of a specific committee."""
    committee = await get_or_404(db, Committee, committee_id, "Committee not found")
    return committee


@router.patch("/committees/{committee_id}", response_model=CommitteeResponse)
async def update_committee(
    committee_id: int,
    data: CommitteeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update committee details."""
    committee = await get_or_404(db, Committee, committee_id, "Committee not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(committee, field, value)

    await db.commit()
    await db.refresh(committee)
    return committee


@router.post("/committees/{committee_id}/join", response_model=CommitteeMemberResponse, status_code=status.HTTP_201_CREATED)
async def join_committee(
    committee_id: int,
    data: Optional[CommitteeMemberCreate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Join a committee voluntarily.

    Participation is optional, never compelled. Time spent on committees
    counts as work time.
    """
    # Verify committee exists
    await get_or_404(db, Committee, committee_id, "Committee not found")

    # Check if already a member
    existing = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee_id,
            CommitteeMember.staff_id == current_user.id,
            CommitteeMember.status == MembershipStatus.active,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member of this committee")

    role = data.role if data else "member"
    member = CommitteeMember(
        committee_id=committee_id,
        staff_id=current_user.id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.post("/committees/{committee_id}/leave", response_model=CommitteeMemberResponse)
async def leave_committee(
    committee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Leave a committee. Staff may leave committees as their interests change."""
    result = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee_id,
            CommitteeMember.staff_id == current_user.id,
            CommitteeMember.status == MembershipStatus.active,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not a member of this committee")

    member.status = MembershipStatus.departed
    member.departed_date = sa_func.now()
    await db.commit()
    await db.refresh(member)
    return member


@router.get("/committees/{committee_id}/members", response_model=list[CommitteeMemberResponse])
async def list_committee_members(
    committee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List members of a committee."""
    result = await db.execute(
        select(CommitteeMember)
        .where(CommitteeMember.committee_id == committee_id)
        .order_by(CommitteeMember.joined_date)
    )
    return result.scalars().all()


# ============================================================================
# Project Leadership Endpoints
# ============================================================================


@router.post("/projects", response_model=StaffProjectResponse, status_code=status.HTTP_201_CREATED)
async def propose_project(
    data: StaffProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Propose a new staff-led project.

    Project leadership is based on expertise and interest, not hierarchy.
    Any staff member can propose a project aligned with library goals.
    """
    project = StaffProject(
        organization_id=_require_org_id(current_user),
        title=data.title,
        description=data.description,
        expected_impact=data.expected_impact,
        resources_needed=data.resources_needed,
        lead_id=current_user.id,
        team_member_ids=data.team_member_ids,
        budget_requested=data.budget_requested,
        proposed_start_date=data.proposed_start_date,
        proposed_end_date=data.proposed_end_date,
        is_innovation_project=data.is_innovation_project,
        tags=data.tags,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[StaffProjectListResponse])
async def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    lead_id: Optional[int] = None,
    innovation_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List staff projects with optional filters."""
    query = select(StaffProject).order_by(StaffProject.created_at.desc())
    if status_filter:
        query = query.where(StaffProject.status == status_filter)
    if lead_id:
        query = query.where(StaffProject.lead_id == lead_id)
    if innovation_only:
        query = query.where(StaffProject.is_innovation_project.is_(True))
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/projects/{project_id}", response_model=StaffProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of a specific project."""
    project = await get_or_404(db, StaffProject, project_id, "Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=StaffProjectResponse)
async def update_project(
    project_id: int,
    data: StaffProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a project (by project lead)."""
    project = await get_or_404(db, StaffProject, project_id, "Project not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.post("/projects/{project_id}/approve", response_model=StaffProjectResponse)
async def approve_project(
    project_id: int,
    data: StaffProjectApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve or adjust a project proposal (director/supervisor)."""
    project = await get_or_404(db, StaffProject, project_id, "Project not found")

    project.status = data.status
    project.approved_by_id = current_user.id
    project.approved_date = sa_func.now()
    project.approval_notes = data.approval_notes
    if data.budget_approved is not None:
        project.budget_approved = data.budget_approved

    await db.commit()
    await db.refresh(project)
    return project


# ============================================================================
# Policy Feedback Endpoints
# ============================================================================


@router.post("/feedback", response_model=PolicyFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_policy_feedback(
    data: PolicyFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Submit feedback on a policy.

    Any staff member can propose changes, comment on policies, or raise
    concerns. Anonymous submission is supported.
    """
    feedback = PolicyFeedback(
        organization_id=_require_org_id(current_user),
        submitted_by_id=None if data.is_anonymous else current_user.id,
        is_anonymous=data.is_anonymous,
        policy_name=data.policy_name,
        policy_document=data.policy_document,
        feedback_type=data.feedback_type,
        title=data.title,
        content=data.content,
        proposed_change=data.proposed_change,
        rationale=data.rationale,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.get("/feedback", response_model=list[PolicyFeedbackListResponse])
async def list_policy_feedback(
    policy_name: Optional[str] = None,
    feedback_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List policy feedback with optional filters."""
    query = select(PolicyFeedback).order_by(PolicyFeedback.created_at.desc())
    if policy_name:
        query = query.where(PolicyFeedback.policy_name == policy_name)
    if feedback_type:
        query = query.where(PolicyFeedback.feedback_type == feedback_type)
    if status_filter:
        query = query.where(PolicyFeedback.status == status_filter)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/feedback/{feedback_id}", response_model=PolicyFeedbackResponse)
async def get_policy_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of specific policy feedback."""
    feedback = await get_or_404(db, PolicyFeedback, feedback_id, "Feedback not found")
    return feedback


@router.post("/feedback/{feedback_id}/review", response_model=PolicyFeedbackResponse)
async def review_policy_feedback(
    feedback_id: int,
    data: PolicyFeedbackReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Review submitted policy feedback (supervisor/director)."""
    feedback = await get_or_404(db, PolicyFeedback, feedback_id, "Feedback not found")

    feedback.status = data.status
    feedback.reviewed_by_id = current_user.id
    feedback.review_date = sa_func.now()
    feedback.review_response = data.review_response
    feedback.led_to_change = data.led_to_change
    feedback.change_description = data.change_description

    await db.commit()
    await db.refresh(feedback)
    return feedback


# ============================================================================
# Expertise Recognition Endpoints
# ============================================================================


@router.post("/expertise", response_model=StaffExpertiseResponse, status_code=status.HTTP_201_CREATED)
async def register_expertise(
    data: StaffExpertiseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Register an area of expertise.

    Staff self-identify areas of expertise and indicate willingness to
    mentor, train, or consult.
    """
    expertise = StaffExpertise(
        staff_id=current_user.id,
        organization_id=_require_org_id(current_user),
        domain=data.domain,
        description=data.description,
        level=data.level,
        relevant_credentials=data.relevant_credentials,
        years_experience=data.years_experience,
        willing_to_mentor=data.willing_to_mentor,
        willing_to_train=data.willing_to_train,
        willing_to_consult=data.willing_to_consult,
        is_public=data.is_public,
    )
    db.add(expertise)
    await db.commit()
    await db.refresh(expertise)
    return expertise


@router.get("/expertise", response_model=list[StaffExpertiseResponse])
async def search_expertise(
    domain: Optional[str] = None,
    willing_to_mentor: Optional[bool] = None,
    willing_to_train: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Search the expertise registry to find colleagues with specific knowledge."""
    query = select(StaffExpertise).where(StaffExpertise.is_public.is_(True))
    if domain:
        safe_domain = domain.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(StaffExpertise.domain.ilike(f"%{safe_domain}%"))
    if willing_to_mentor is not None:
        query = query.where(StaffExpertise.willing_to_mentor == willing_to_mentor)
    if willing_to_train is not None:
        query = query.where(StaffExpertise.willing_to_train == willing_to_train)
    query = query.order_by(StaffExpertise.domain)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/expertise/me", response_model=list[StaffExpertiseResponse])
async def get_my_expertise(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get current user's registered expertise areas."""
    result = await db.execute(
        select(StaffExpertise)
        .where(StaffExpertise.staff_id == current_user.id)
        .order_by(StaffExpertise.domain)
    )
    return result.scalars().all()


@router.patch("/expertise/{expertise_id}", response_model=StaffExpertiseResponse)
async def update_expertise(
    expertise_id: int,
    data: StaffExpertiseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an expertise entry."""
    result = await db.execute(
        select(StaffExpertise).where(
            StaffExpertise.id == expertise_id,
            StaffExpertise.staff_id == current_user.id,
        )
    )
    expertise = result.scalar_one_or_none()
    if not expertise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expertise entry not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expertise, field, value)

    await db.commit()
    await db.refresh(expertise)
    return expertise


@router.post("/recognitions", response_model=ExpertiseRecognitionResponse, status_code=status.HTTP_201_CREATED)
async def recognize_expertise(
    data: ExpertiseRecognitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Recognize a colleague's expertise.

    Peer recognition, conference presentations, internal training,
    publications, and mentorship can all be formally recognized.
    """
    recognition = ExpertiseRecognition(
        organization_id=_require_org_id(current_user),
        staff_id=data.staff_id,
        recognition_type=data.recognition_type,
        title=data.title,
        description=data.description,
        recognized_by_id=current_user.id,
        expertise_domain=data.expertise_domain,
        event_name=data.event_name,
        event_date=data.event_date,
        external_url=data.external_url,
    )
    db.add(recognition)
    await db.commit()
    await db.refresh(recognition)
    return recognition


@router.get("/recognitions/{staff_id}", response_model=list[ExpertiseRecognitionResponse])
async def get_staff_recognitions(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all recognitions for a staff member."""
    result = await db.execute(
        select(ExpertiseRecognition)
        .where(ExpertiseRecognition.staff_id == staff_id)
        .order_by(ExpertiseRecognition.created_at.desc())
    )
    return result.scalars().all()


# ============================================================================
# Professional Development Endpoints
# ============================================================================


@router.post("/development/plans", response_model=ProfessionalDevelopmentPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_development_plan(
    data: ProfessionalDevelopmentPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Create a professional development plan.

    Plans are created by the staff member, not imposed by management.
    They reflect the staff member's own career goals and interests.
    """
    plan = ProfessionalDevelopmentPlan(
        staff_id=current_user.id,
        organization_id=_require_org_id(current_user),
        title=data.title,
        career_goals=data.career_goals,
        focus_areas=data.focus_areas,
        planned_activities=data.planned_activities,
        annual_budget=data.annual_budget,
        plan_year=data.plan_year,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/development/plans/me", response_model=list[ProfessionalDevelopmentPlanResponse])
async def get_my_development_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get current user's professional development plans."""
    result = await db.execute(
        select(ProfessionalDevelopmentPlan)
        .where(ProfessionalDevelopmentPlan.staff_id == current_user.id)
        .order_by(ProfessionalDevelopmentPlan.plan_year.desc())
    )
    return result.scalars().all()


@router.get("/development/plans/{plan_id}", response_model=ProfessionalDevelopmentPlanResponse)
async def get_development_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get details of a development plan."""
    plan = await get_or_404(db, ProfessionalDevelopmentPlan, plan_id, "Development plan not found")
    return plan


@router.patch("/development/plans/{plan_id}", response_model=ProfessionalDevelopmentPlanResponse)
async def update_development_plan(
    plan_id: int,
    data: ProfessionalDevelopmentPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a development plan (staff updates their own plan)."""
    result = await db.execute(
        select(ProfessionalDevelopmentPlan).where(
            ProfessionalDevelopmentPlan.id == plan_id,
            ProfessionalDevelopmentPlan.staff_id == current_user.id,
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Development plan not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/development/activities", response_model=DevelopmentActivityResponse, status_code=status.HTTP_201_CREATED)
async def record_development_activity(
    data: DevelopmentActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Record a professional development activity.

    Staff choose their own activities. Diverse forms of growth are recognized
    including conferences, courses, reading, peer learning, and mentoring.
    """
    activity = ProfessionalDevelopmentActivity(
        plan_id=data.plan_id,
        staff_id=current_user.id,
        title=data.title,
        description=data.description,
        activity_type=data.activity_type,
        category=data.category,
        start_date=data.start_date,
        end_date=data.end_date,
        hours_spent=data.hours_spent,
        cost=data.cost,
        provider=data.provider,
        external_url=data.external_url,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


@router.patch("/development/activities/{activity_id}", response_model=DevelopmentActivityResponse)
async def update_development_activity(
    activity_id: int,
    data: DevelopmentActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a development activity (completion, reflection, etc.)."""
    result = await db.execute(
        select(ProfessionalDevelopmentActivity).where(
            ProfessionalDevelopmentActivity.id == activity_id,
            ProfessionalDevelopmentActivity.staff_id == current_user.id,
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)

    await db.commit()
    await db.refresh(activity)
    return activity


@router.get("/development/activities", response_model=list[DevelopmentActivityResponse])
async def list_my_activities(
    plan_id: Optional[int] = None,
    completed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List current user's development activities."""
    query = select(ProfessionalDevelopmentActivity).where(
        ProfessionalDevelopmentActivity.staff_id == current_user.id
    )
    if plan_id:
        query = query.where(ProfessionalDevelopmentActivity.plan_id == plan_id)
    if completed is not None:
        query = query.where(ProfessionalDevelopmentActivity.completed == completed)
    query = query.order_by(ProfessionalDevelopmentActivity.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
