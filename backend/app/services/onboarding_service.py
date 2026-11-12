# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.onboarding import (
    StaffOnboarding, OnboardingStatus, PreArrivalChecklistItem,
    OnboardingChecklistItemStatus, OrientationSchedule, TrainingModule,
    TrainingModuleAssignment, TrainingModuleStatus, Policy,
    PolicyAcknowledgment, SystemAccess, SystemAccessProvisioning,
    SystemAccessStatus, CheckInMeeting, IntroductionAnnouncement,
    OnboardingFeedback, CheckInPeriod, ProbationStatus
)
from ..models.user import User


class OrientationScheduleService:

    @staticmethod
    async def create_item(
        db: AsyncSession,
        onboarding_id: int,
        activity_title: str,
        scheduled_time: datetime,
        duration_minutes: int,
        description: Optional[str] = None,
        location: Optional[str] = None,
        facilitator_id: Optional[int] = None,
    ) -> OrientationSchedule:
        schedule = OrientationSchedule(
            onboarding_id=onboarding_id,
            activity_title=activity_title,
            description=description,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            location=location,
            facilitator_id=facilitator_id,
            status=OnboardingChecklistItemStatus.not_started,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @staticmethod
    async def update_item(
        db: AsyncSession,
        item_id: int,
        status: Optional[OnboardingChecklistItemStatus] = None,
        notes: Optional[str] = None,
    ) -> OrientationSchedule:
        result = await db.execute(
            select(OrientationSchedule).where(OrientationSchedule.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError("Orientation schedule item not found")

        if status:
            item.status = status
            if status == OnboardingChecklistItemStatus.completed:
                item.completed_at = datetime.now(timezone.utc)

        if notes is not None:
            item.notes = notes

        await db.commit()
        await db.refresh(item)
        return item


class StaffOnboardingService:

    @staticmethod
    async def create_onboarding(
        db: AsyncSession,
        user_id: int,
        department: str,
        position: str,
        start_date: date,
        expected_completion_date: date,
        manager_id: Optional[int] = None,
        buddy_mentor_id: Optional[int] = None,
        probation_end_date: Optional[date] = None,
    ) -> StaffOnboarding:
        # Check if onboarding already exists
        existing = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Onboarding already exists for this user")

        onboarding = StaffOnboarding(
            user_id=user_id,
            department=department,
            position=position,
            start_date=start_date,
            expected_completion_date=expected_completion_date,
            manager_id=manager_id,
            buddy_mentor_id=buddy_mentor_id,
            probation_start_date=start_date,
            probation_end_date=probation_end_date or (start_date + timedelta(days=90)),
            status=OnboardingStatus.pending,
        )
        db.add(onboarding)
        await db.commit()
        await db.refresh(onboarding)

        # Automatically schedule check-in meetings
        await StaffOnboardingService._schedule_standard_checkins(db, onboarding)

        return onboarding

    @staticmethod
    async def _schedule_standard_checkins(
        db: AsyncSession,
        onboarding: StaffOnboarding,
    ) -> None:
        checkin_schedule = [
            (CheckInPeriod.first_day, 0),
            (CheckInPeriod.one_week, 7),
            (CheckInPeriod.thirty_day, 30),
            (CheckInPeriod.sixty_day, 60),
            (CheckInPeriod.ninety_day, 90),
        ]

        for period, days_offset in checkin_schedule:
            scheduled_date = onboarding.start_date + timedelta(days=days_offset)
            meeting = CheckInMeeting(
                onboarding_id=onboarding.id,
                period=period,
                scheduled_date=scheduled_date,
                scheduled_with_id=onboarding.manager_id,
                topics=[
                    "Progress update",
                    "Feedback and concerns",
                    "Support needs",
                    "Next steps",
                ] if days_offset == 0 else [],
            )
            db.add(meeting)

        await db.commit()

    @staticmethod
    async def get_onboarding(
        db: AsyncSession,
        onboarding_id: int,
        include_details: bool = False
    ) -> Optional[StaffOnboarding]:
        query = select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)

        if include_details:
            query = query.options(
                selectinload(StaffOnboarding.pre_arrival_checklist),
                selectinload(StaffOnboarding.orientation_schedule),
                selectinload(StaffOnboarding.training_assignments),
                selectinload(StaffOnboarding.policy_acknowledgments),
                selectinload(StaffOnboarding.system_access_provisioning),
                selectinload(StaffOnboarding.check_in_meetings),
                selectinload(StaffOnboarding.introduction_announcements),
                selectinload(StaffOnboarding.feedback),
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_onboarding_by_user(
        db: AsyncSession,
        user_id: int
    ) -> Optional[StaffOnboarding]:
        result = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_onboarding_status(
        db: AsyncSession,
        onboarding_id: int,
        status: OnboardingStatus
    ) -> StaffOnboarding:
        result = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)
        )
        onboarding = result.scalar_one_or_none()
        if not onboarding:
            raise ValueError("Onboarding not found")

        onboarding.status = status
        if status == OnboardingStatus.completed:
            onboarding.actual_completion_date = datetime.now(timezone.utc)
            onboarding.progress_percentage = 100

        await db.commit()
        await db.refresh(onboarding)
        return onboarding

    @staticmethod
    async def update_progress(
        db: AsyncSession,
        onboarding_id: int
    ) -> int:
        onboarding = await StaffOnboardingService.get_onboarding(db, onboarding_id, include_details=True)
        if not onboarding:
            raise ValueError("Onboarding not found")

        # Calculate progress based on completed items
        total_items = 0
        completed_items = 0

        # Pre-arrival checklist
        for item in onboarding.pre_arrival_checklist:
            total_items += 1
            if item.status == OnboardingChecklistItemStatus.completed:
                completed_items += 1

        # Orientation schedule
        for item in onboarding.orientation_schedule:
            total_items += 1
            if item.status == OnboardingChecklistItemStatus.completed:
                completed_items += 1

        # Training modules
        for assignment in onboarding.training_assignments:
            total_items += 1
            if assignment.status == TrainingModuleStatus.completed:
                completed_items += 1

        # Policies
        for ack in onboarding.policy_acknowledgments:
            total_items += 1
            completed_items += 1  # If acknowledged, it's complete

        # System access
        for access in onboarding.system_access_provisioning:
            total_items += 1
            if access.status == SystemAccessStatus.provisioned:
                completed_items += 1

        # Check-in meetings
        for meeting in onboarding.check_in_meetings:
            total_items += 1
            if meeting.completed_at:
                completed_items += 1

        # Calculate percentage
        # NOTE: multiply BEFORE integer-divide; the old `// total_items * 100`
        # form floored to 0 until everything was complete.
        progress_percentage = (completed_items * 100) // total_items if total_items > 0 else 0
        onboarding.progress_percentage = progress_percentage
        await db.commit()

        return progress_percentage


class PreArrivalChecklistService:

    @staticmethod
    async def create_item(
        db: AsyncSession,
        onboarding_id: int,
        title: str,
        category: str,
        description: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
    ) -> PreArrivalChecklistItem:
        item = PreArrivalChecklistItem(
            onboarding_id=onboarding_id,
            title=title,
            category=category,
            description=description,
            assigned_to_id=assigned_to_id,
            status=OnboardingChecklistItemStatus.not_started,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def update_item(
        db: AsyncSession,
        item_id: int,
        status: Optional[OnboardingChecklistItemStatus] = None,
        notes: Optional[str] = None,
        evidence_url: Optional[str] = None,
    ) -> PreArrivalChecklistItem:
        result = await db.execute(
            select(PreArrivalChecklistItem).where(PreArrivalChecklistItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError("Checklist item not found")

        if status:
            item.status = status
            if status == OnboardingChecklistItemStatus.completed:
                item.completed_at = datetime.now(timezone.utc)

        if notes is not None:
            item.notes = notes
        if evidence_url is not None:
            item.evidence_url = evidence_url

        await db.commit()
        await db.refresh(item)
        return item


class TrainingModuleService:

    @staticmethod
    async def create_module(
        db: AsyncSession,
        title: str,
        category: str,
        duration_minutes: int,
        delivery_type: str,
        description: Optional[str] = None,
        is_mandatory: bool = True,
        content_url: Optional[str] = None,
        passing_score: int = 80,
        order: Optional[int] = None,
    ) -> TrainingModule:
        module = TrainingModule(
            title=title,
            category=category,
            duration_minutes=duration_minutes,
            delivery_type=delivery_type,
            description=description,
            is_mandatory=is_mandatory,
            content_url=content_url,
            passing_score=passing_score,
            order=order,
        )
        db.add(module)
        await db.commit()
        await db.refresh(module)
        return module

    @staticmethod
    async def assign_module(
        db: AsyncSession,
        onboarding_id: int,
        training_module_id: int,
        due_date: date,
    ) -> TrainingModuleAssignment:
        # Check if already assigned
        existing = await db.execute(
            select(TrainingModuleAssignment).where(
                and_(
                    TrainingModuleAssignment.onboarding_id == onboarding_id,
                    TrainingModuleAssignment.training_module_id == training_module_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Module already assigned to this onboarding record")

        assignment = TrainingModuleAssignment(
            onboarding_id=onboarding_id,
            training_module_id=training_module_id,
            due_date=due_date,
            status=TrainingModuleStatus.not_started,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    @staticmethod
    async def update_assignment(
        db: AsyncSession,
        assignment_id: int,
        status: Optional[TrainingModuleStatus] = None,
        score: Optional[int] = None,
        verified_by_id: Optional[int] = None,
    ) -> TrainingModuleAssignment:
        result = await db.execute(
            select(TrainingModuleAssignment).where(TrainingModuleAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise ValueError("Assignment not found")

        if status:
            assignment.status = status
            if status == TrainingModuleStatus.completed:
                assignment.completed_at = datetime.now(timezone.utc)
                # Look up the module's passing_score; fall back to 80 if the
                # assignment has no attached module (legacy/ad-hoc rows).
                module_result = await db.execute(
                    select(TrainingModule.passing_score).where(
                        TrainingModule.id == assignment.training_module_id
                    )
                )
                threshold = module_result.scalar_one_or_none()
                if threshold is None:
                    threshold = 80
                assignment.passed = (score or 0) >= threshold

        if score is not None:
            assignment.score = score

        if verified_by_id:
            assignment.verified_by_id = verified_by_id
            assignment.verified_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(assignment)
        return assignment


class PolicyService:

    @staticmethod
    async def create_policy(
        db: AsyncSession,
        title: str,
        content: str,
        category: str,
        effective_date: date,
        version: str = "1.0",
        description: Optional[str] = None,
        is_mandatory: bool = True,
    ) -> Policy:
        policy = Policy(
            title=title,
            content=content,
            category=category,
            effective_date=effective_date,
            version=version,
            description=description,
            is_mandatory=is_mandatory,
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def acknowledge_policy(
        db: AsyncSession,
        onboarding_id: int,
        policy_id: int,
        acknowledged_by_id: int,
        ip_address: Optional[str] = None,
    ) -> PolicyAcknowledgment:
        # Check if already acknowledged
        existing = await db.execute(
            select(PolicyAcknowledgment).where(
                and_(
                    PolicyAcknowledgment.onboarding_id == onboarding_id,
                    PolicyAcknowledgment.policy_id == policy_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Policy already acknowledged")

        acknowledgment = PolicyAcknowledgment(
            onboarding_id=onboarding_id,
            policy_id=policy_id,
            acknowledged_by_id=acknowledged_by_id,
            acknowledged_at=datetime.now(timezone.utc),
            ip_address=ip_address,
        )
        db.add(acknowledgment)
        await db.commit()
        await db.refresh(acknowledgment)

        # Check if all mandatory policies are acknowledged
        await PolicyService._update_policy_status(db, onboarding_id)

        return acknowledgment

    @staticmethod
    async def _update_policy_status(
        db: AsyncSession,
        onboarding_id: int
    ) -> None:
        # Get all mandatory policies
        result = await db.execute(
            select(Policy).where(Policy.is_mandatory == True)
        )
        mandatory_policies = result.scalars().all()

        # Get acknowledged policies for this onboarding
        ack_result = await db.execute(
            select(PolicyAcknowledgment.policy_id).where(
                PolicyAcknowledgment.onboarding_id == onboarding_id
            )
        )
        acknowledged_policy_ids = set(ack_result.scalars().all())

        # Check if all mandatory policies are acknowledged
        all_acknowledged = all(
            policy.id in acknowledged_policy_ids for policy in mandatory_policies
        )

        # Update onboarding
        onboarding = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)
        )
        onboarding_record = onboarding.scalar_one_or_none()
        if onboarding_record:
            onboarding_record.all_policies_acknowledged = all_acknowledged
            await db.commit()


class SystemAccessService:

    @staticmethod
    async def create_system(
        db: AsyncSession,
        system_name: str,
        access_type: str,
        description: Optional[str] = None,
        provisioning_instructions: Optional[str] = None,
        deprovisioning_instructions: Optional[str] = None,
    ) -> SystemAccess:
        system = SystemAccess(
            system_name=system_name,
            access_type=access_type,
            description=description,
            provisioning_instructions=provisioning_instructions,
            deprovisioning_instructions=deprovisioning_instructions,
        )
        db.add(system)
        await db.commit()
        await db.refresh(system)
        return system

    @staticmethod
    async def request_access(
        db: AsyncSession,
        onboarding_id: int,
        system_access_id: int,
        requested_by_id: Optional[int] = None,
    ) -> SystemAccessProvisioning:
        # Check if already requested
        existing = await db.execute(
            select(SystemAccessProvisioning).where(
                and_(
                    SystemAccessProvisioning.onboarding_id == onboarding_id,
                    SystemAccessProvisioning.system_access_id == system_access_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Access already requested for this system")

        provisioning = SystemAccessProvisioning(
            onboarding_id=onboarding_id,
            system_access_id=system_access_id,
            requested_by_id=requested_by_id,
            status=SystemAccessStatus.requested,
        )
        db.add(provisioning)
        await db.commit()
        await db.refresh(provisioning)
        return provisioning

    @staticmethod
    async def provision_access(
        db: AsyncSession,
        provisioning_id: int,
        provisioned_by_id: int,
    ) -> SystemAccessProvisioning:
        result = await db.execute(
            select(SystemAccessProvisioning).where(SystemAccessProvisioning.id == provisioning_id)
        )
        provisioning = result.scalar_one_or_none()
        if not provisioning:
            raise ValueError("Provisioning record not found")

        provisioning.status = SystemAccessStatus.provisioned
        provisioning.provisioned_by_id = provisioned_by_id
        provisioning.provisioned_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(provisioning)

        # Check if all systems are provisioned
        await SystemAccessService._update_access_status(db, provisioning.onboarding_id)

        return provisioning

    @staticmethod
    async def _update_access_status(
        db: AsyncSession,
        onboarding_id: int
    ) -> None:
        result = await db.execute(
            select(SystemAccessProvisioning).where(
                SystemAccessProvisioning.onboarding_id == onboarding_id
            )
        )
        provisionings = result.scalars().all()

        all_provisioned = all(
            p.status == SystemAccessStatus.provisioned for p in provisionings
        ) if provisionings else False

        onboarding = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)
        )
        onboarding_record = onboarding.scalar_one_or_none()
        if onboarding_record:
            onboarding_record.all_systems_provisioned = all_provisioned
            await db.commit()


class CheckInMeetingService:

    @staticmethod
    async def schedule_meeting(
        db: AsyncSession,
        onboarding_id: int,
        period: CheckInPeriod,
        scheduled_date: date,
        scheduled_with_id: Optional[int] = None,
        topics: Optional[List[str]] = None,
    ) -> CheckInMeeting:
        meeting = CheckInMeeting(
            onboarding_id=onboarding_id,
            period=period,
            scheduled_date=scheduled_date,
            scheduled_time=None,
            scheduled_with_id=scheduled_with_id,
            topics=topics or [],
        )
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)
        return meeting

    @staticmethod
    async def complete_meeting(
        db: AsyncSession,
        meeting_id: int,
        meeting_notes: Optional[str] = None,
        feedback_from_new_hire: Optional[str] = None,
        feedback_from_manager: Optional[str] = None,
        action_items: Optional[List[str]] = None,
    ) -> CheckInMeeting:
        result = await db.execute(
            select(CheckInMeeting).where(CheckInMeeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise ValueError("Meeting not found")

        meeting.completed_at = datetime.now(timezone.utc)
        meeting.meeting_notes = meeting_notes
        meeting.feedback_from_new_hire = feedback_from_new_hire
        meeting.feedback_from_manager = feedback_from_manager
        meeting.action_items = action_items or []

        await db.commit()
        await db.refresh(meeting)
        return meeting


async def create_feedback(
    db: AsyncSession,
    onboarding_id: int,
    feedback_type: str,
    provided_by_id: int,
    rating: Optional[int] = None,
    comments: Optional[str] = None,
    is_anonymous: bool = False,
) -> OnboardingFeedback:
    feedback = OnboardingFeedback(
        onboarding_id=onboarding_id,
        feedback_type=feedback_type,
        provided_by_id=provided_by_id,
        rating=rating,
        comments=comments,
        is_anonymous=is_anonymous,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


class ProbationService:

    @staticmethod
    async def get_overdue_probations(
        db: AsyncSession,
    ) -> List[StaffOnboarding]:
        today = date.today()
        result = await db.execute(
            select(StaffOnboarding).where(
                and_(
                    StaffOnboarding.probation_end_date < today,
                    StaffOnboarding.probation_status == ProbationStatus.active,
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def mark_probation_passed(
        db: AsyncSession,
        onboarding_id: int,
    ) -> StaffOnboarding:
        result = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)
        )
        onboarding = result.scalar_one_or_none()
        if not onboarding:
            raise ValueError("Onboarding not found")

        onboarding.probation_status = ProbationStatus.passed
        await db.commit()
        await db.refresh(onboarding)
        return onboarding

    @staticmethod
    async def mark_probation_failed(
        db: AsyncSession,
        onboarding_id: int,
        notes: Optional[str] = None,
    ) -> StaffOnboarding:
        result = await db.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding_id)
        )
        onboarding = result.scalar_one_or_none()
        if not onboarding:
            raise ValueError("Onboarding not found")

        onboarding.probation_status = ProbationStatus.failed
        if notes:
            onboarding.notes = (onboarding.notes or "") + f"\nProbation failed: {notes}"

        await db.commit()
        await db.refresh(onboarding)
        return onboarding
