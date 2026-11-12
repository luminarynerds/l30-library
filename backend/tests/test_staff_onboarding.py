# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for staff onboarding system.

Tests cover:
- Onboarding initialization and management
- Pre-arrival checklist tracking
- Training module assignments
- Policy acknowledgments
- System access provisioning
- Check-in meeting scheduling
- Feedback collection
- Probation period management
"""

import pytest
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.onboarding import (
    StaffOnboarding,
    OnboardingStatus,
    PreArrivalChecklistItem,
    OnboardingChecklistItemStatus,
    TrainingModule,
    TrainingModuleAssignment,
    TrainingModuleStatus,
    Policy,
    PolicyAcknowledgment,
    SystemAccess,
    SystemAccessProvisioning,
    SystemAccessStatus,
    CheckInMeeting,
    CheckInPeriod,
    OnboardingFeedback,
    FeedbackType,
    ProbationStatus,
)
from app.services.onboarding_service import (
    StaffOnboardingService,
    PreArrivalChecklistService,
    TrainingModuleService,
    PolicyService,
    SystemAccessService,
    CheckInMeetingService,
    ProbationService,
    create_feedback as create_onboarding_feedback,
)


@pytest.mark.asyncio
class TestStaffOnboardingService:
    """Test staff onboarding initialization and management."""

    async def test_create_onboarding(self, db_session: AsyncSession):
        """Test creating a new onboarding record."""
        # Create test user
        user = User(
            email="newstaff@library.org",
            password_hash="hashed",
            first_name="John",
            last_name="Doe",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        # Create onboarding
        start_date = date.today()
        expected_completion = start_date + timedelta(days=90)

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Circulation",
            position="Circulation Assistant",
            start_date=start_date,
            expected_completion_date=expected_completion,
        )

        assert onboarding.user_id == user.id
        assert onboarding.department == "Circulation"
        assert onboarding.position == "Circulation Assistant"
        assert onboarding.status == OnboardingStatus.pending
        assert onboarding.progress_percentage == 0

    async def test_create_duplicate_onboarding_fails(self, db_session: AsyncSession):
        """Test that creating duplicate onboarding fails."""
        user = User(
            email="duplicate@library.org",
            password_hash="hashed",
            first_name="Jane",
            last_name="Smith",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        start_date = date.today()
        expected_completion = start_date + timedelta(days=90)

        # Create first onboarding
        await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Reference",
            position="Reference Librarian",
            start_date=start_date,
            expected_completion_date=expected_completion,
        )

        # Try to create duplicate
        with pytest.raises(ValueError, match="Onboarding already exists"):
            await StaffOnboardingService.create_onboarding(
                db=db_session,
                user_id=user.id,
                department="Reference",
                position="Reference Librarian",
                start_date=start_date,
                expected_completion_date=expected_completion,
            )

    async def test_update_onboarding_status(self, db_session: AsyncSession):
        """Test updating onboarding status."""
        user = User(
            email="status@library.org",
            password_hash="hashed",
            first_name="Bob",
            last_name="Johnson",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Tech",
            position="IT Support",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        # Update status
        updated = await StaffOnboardingService.update_onboarding_status(
            db=db_session,
            onboarding_id=onboarding.id,
            status=OnboardingStatus.in_progress,
        )

        assert updated.status == OnboardingStatus.in_progress


@pytest.mark.asyncio
class TestPreArrivalChecklist:
    """Test pre-arrival checklist management."""

    async def test_create_checklist_item(self, db_session: AsyncSession):
        """Test creating a checklist item."""
        user = User(
            email="checklist@library.org",
            password_hash="hashed",
            first_name="Alice",
            last_name="Brown",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Admin",
            position="Admin Assistant",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=60),
        )

        item = await PreArrivalChecklistService.create_item(
            db=db_session,
            onboarding_id=onboarding.id,
            title="Set up workspace",
            category="office",
            description="Prepare desk and office supplies",
        )

        assert item.title == "Set up workspace"
        assert item.category == "office"
        assert item.status == OnboardingChecklistItemStatus.not_started

    async def test_update_checklist_item_status(self, db_session: AsyncSession):
        """Test updating checklist item status."""
        user = User(
            email="update@library.org",
            password_hash="hashed",
            first_name="Charlie",
            last_name="Davis",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Programs",
            position="Program Coordinator",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        item = await PreArrivalChecklistService.create_item(
            db=db_session,
            onboarding_id=onboarding.id,
            title="Order equipment",
            category="equipment",
        )

        updated = await PreArrivalChecklistService.update_item(
            db=db_session,
            item_id=item.id,
            status=OnboardingChecklistItemStatus.completed,
            notes="All equipment ordered",
        )

        assert updated.status == OnboardingChecklistItemStatus.completed
        assert updated.completed_at is not None


@pytest.mark.asyncio
class TestTrainingModules:
    """Test training module management."""

    async def test_create_training_module(self, db_session: AsyncSession):
        """Test creating a training module."""
        module = await TrainingModuleService.create_module(
            db=db_session,
            title="Safety Training",
            category="safety",
            duration_minutes=60,
            delivery_type="online",
            description="Comprehensive safety training",
        )

        assert module.title == "Safety Training"
        assert module.category == "safety"
        assert module.duration_minutes == 60
        assert module.is_mandatory is True

    async def test_assign_training_module(self, db_session: AsyncSession):
        """Test assigning training module to staff."""
        user = User(
            email="training@library.org",
            password_hash="hashed",
            first_name="David",
            last_name="Evans",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Training",
            position="Trainer",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        module = await TrainingModuleService.create_module(
            db=db_session,
            title="Customer Service",
            category="skills",
            duration_minutes=45,
            delivery_type="in-person",
        )

        due_date = date.today() + timedelta(days=7)
        assignment = await TrainingModuleService.assign_module(
            db=db_session,
            onboarding_id=onboarding.id,
            training_module_id=module.id,
            due_date=due_date,
        )

        assert assignment.training_module_id == module.id
        assert assignment.due_date == due_date
        assert assignment.status == TrainingModuleStatus.not_started


@pytest.mark.asyncio
class TestPolicies:
    """Test policy management and acknowledgments."""

    async def test_create_policy(self, db_session: AsyncSession):
        """Test creating a policy."""
        policy = await PolicyService.create_policy(
            db=db_session,
            title="Code of Conduct",
            content="All staff must follow the code of conduct...",
            category="conduct",
            effective_date=date.today(),
        )

        assert policy.title == "Code of Conduct"
        assert policy.category == "conduct"
        assert policy.is_mandatory is True

    async def test_acknowledge_policy(self, db_session: AsyncSession):
        """Test acknowledging a policy."""
        user = User(
            email="policy@library.org",
            password_hash="hashed",
            first_name="Emma",
            last_name="Foster",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Legal",
            position="Compliance Officer",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        policy = await PolicyService.create_policy(
            db=db_session,
            title="Confidentiality",
            content="All patron data must be kept confidential...",
            category="privacy",
            effective_date=date.today(),
        )

        ack = await PolicyService.acknowledge_policy(
            db=db_session,
            onboarding_id=onboarding.id,
            policy_id=policy.id,
            acknowledged_by_id=user.id,
        )

        assert ack.policy_id == policy.id
        assert ack.acknowledged_at is not None

    async def test_duplicate_acknowledgment_fails(self, db_session: AsyncSession):
        """Test that duplicate policy acknowledgment fails."""
        user = User(
            email="dupolicy@library.org",
            password_hash="hashed",
            first_name="Frank",
            last_name="Garcia",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="HR",
            position="HR Manager",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        policy = await PolicyService.create_policy(
            db=db_session,
            title="Anti-discrimination",
            content="No discrimination based on...",
            category="hr",
            effective_date=date.today(),
        )

        await PolicyService.acknowledge_policy(
            db=db_session,
            onboarding_id=onboarding.id,
            policy_id=policy.id,
            acknowledged_by_id=user.id,
        )

        # Try duplicate
        with pytest.raises(ValueError, match="already acknowledged"):
            await PolicyService.acknowledge_policy(
                db=db_session,
                onboarding_id=onboarding.id,
                policy_id=policy.id,
                acknowledged_by_id=user.id,
            )


@pytest.mark.asyncio
class TestSystemAccess:
    """Test system access provisioning."""

    async def test_create_system_access(self, db_session: AsyncSession):
        """Test creating system access record."""
        system = await SystemAccessService.create_system(
            db=db_session,
            system_name="Email",
            access_type="email",
            description="Company email account",
        )

        assert system.system_name == "Email"
        assert system.access_type == "email"

    async def test_request_system_access(self, db_session: AsyncSession):
        """Test requesting system access."""
        user = User(
            email="access@library.org",
            password_hash="hashed",
            first_name="Grace",
            last_name="Harris",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="IT",
            position="IT Support",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        system = await SystemAccessService.create_system(
            db=db_session,
            system_name="VPN",
            access_type="network",
            description="Remote access VPN",
        )

        provisioning = await SystemAccessService.request_access(
            db=db_session,
            onboarding_id=onboarding.id,
            system_access_id=system.id,
            requested_by_id=user.id,
        )

        assert provisioning.status == SystemAccessStatus.requested


@pytest.mark.asyncio
class TestCheckInMeetings:
    """Test check-in meeting management."""

    async def test_schedule_check_in_meeting(self, db_session: AsyncSession):
        """Test scheduling a check-in meeting."""
        user = User(
            email="checkin@library.org",
            password_hash="hashed",
            first_name="Henry",
            last_name="Ingram",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Management",
            position="Manager",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=90),
        )

        scheduled_date = date.today() + timedelta(days=30)
        meeting = await CheckInMeetingService.schedule_meeting(
            db=db_session,
            onboarding_id=onboarding.id,
            period=CheckInPeriod.thirty_day,
            scheduled_date=scheduled_date,
            topics=["Performance", "Goals"],
        )

        assert meeting.period == CheckInPeriod.thirty_day
        assert meeting.scheduled_date == scheduled_date
        assert "Performance" in meeting.topics

    async def test_complete_check_in_meeting(self, db_session: AsyncSession):
        """Test completing a check-in meeting."""
        user = User(
            email="complete@library.org",
            password_hash="hashed",
            first_name="Isabel",
            last_name="Jackson",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Services",
            position="Service Specialist",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        meeting = await CheckInMeetingService.schedule_meeting(
            db=db_session,
            onboarding_id=onboarding.id,
            period=CheckInPeriod.first_day,
            scheduled_date=date.today(),
        )

        completed = await CheckInMeetingService.complete_meeting(
            db=db_session,
            meeting_id=meeting.id,
            meeting_notes="Great first day",
            feedback_from_new_hire="Very welcoming",
        )

        assert completed.completed_at is not None
        assert completed.meeting_notes == "Great first day"


@pytest.mark.asyncio
class TestFeedback:
    """Test feedback collection."""

    async def test_create_feedback(self, db_session: AsyncSession):
        """Test creating feedback."""
        user = User(
            email="feedback@library.org",
            password_hash="hashed",
            first_name="Jack",
            last_name="Kelly",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Training",
            position="Trainer",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        feedback = await create_onboarding_feedback(
            db=db_session,
            onboarding_id=onboarding.id,
            feedback_type=FeedbackType.training,
            provided_by_id=user.id,
            rating=5,
            comments="Excellent training program",
        )

        assert feedback.rating == 5
        assert feedback.feedback_type == FeedbackType.training


@pytest.mark.asyncio
class TestProbation:
    """Test probation period management."""

    async def test_mark_probation_passed(self, db_session: AsyncSession):
        """Test marking probation as passed."""
        user = User(
            email="probation@library.org",
            password_hash="hashed",
            first_name="Kevin",
            last_name="Lee",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Operations",
            position="Operations Specialist",
            start_date=date.today() - timedelta(days=90),
            expected_completion_date=date.today(),
            probation_end_date=date.today(),
        )

        updated = await ProbationService.mark_probation_passed(
            db=db_session,
            onboarding_id=onboarding.id,
        )

        assert updated.probation_status == ProbationStatus.passed

    async def test_mark_probation_failed(self, db_session: AsyncSession):
        """Test marking probation as failed."""
        user = User(
            email="failed@library.org",
            password_hash="hashed",
            first_name="Laura",
            last_name="Martin",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Archives",
            position="Archivist",
            start_date=date.today() - timedelta(days=90),
            expected_completion_date=date.today(),
            probation_end_date=date.today(),
        )

        updated = await ProbationService.mark_probation_failed(
            db=db_session,
            onboarding_id=onboarding.id,
            notes="Did not meet performance standards",
        )

        assert updated.probation_status == ProbationStatus.failed


@pytest.mark.asyncio
class TestProgressCalculation:
    """Test progress calculation."""

    async def test_update_progress_percentage(self, db_session: AsyncSession):
        """Test progress percentage calculation."""
        user = User(
            email="progress@library.org",
            password_hash="hashed",
            first_name="Michael",
            last_name="Nelson",
            role=UserRole.STAFF,
        )
        db_session.add(user)
        await db_session.flush()

        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=user.id,
            department="Acquisitions",
            position="Acquisitions Librarian",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
        )

        # Add some completed items
        await PreArrivalChecklistService.create_item(
            db=db_session,
            onboarding_id=onboarding.id,
            title="Workspace setup",
            category="office",
        )

        # Update progress
        progress = await StaffOnboardingService.update_progress(
            db=db_session,
            onboarding_id=onboarding.id,
        )

        # Progress should be calculated based on items
        assert isinstance(progress, int)
        assert 0 <= progress <= 100


@pytest.mark.asyncio
class TestOnboardingWorkflow:
    """Test complete onboarding workflow."""

    async def test_complete_onboarding_workflow(self, db_session: AsyncSession):
        """Test a complete onboarding workflow."""
        # Create users
        new_staff = User(
            email="workflow@library.org",
            password_hash="hashed",
            first_name="Olivia",
            last_name="Peterson",
            role=UserRole.STAFF,
        )
        manager = User(
            email="manager@library.org",
            password_hash="hashed",
            first_name="Paul",
            last_name="Quinn",
            role=UserRole.STAFF,
        )
        db_session.add(new_staff)
        db_session.add(manager)
        await db_session.flush()

        # Create onboarding
        onboarding = await StaffOnboardingService.create_onboarding(
            db=db_session,
            user_id=new_staff.id,
            department="Collections",
            position="Collections Manager",
            start_date=date.today(),
            expected_completion_date=date.today() + timedelta(days=30),
            manager_id=manager.id,
            buddy_mentor_id=manager.id,
        )

        # Add checklist items
        await PreArrivalChecklistService.create_item(
            db=db_session,
            onboarding_id=onboarding.id,
            title="Complete I-9",
            category="paperwork",
        )

        # Create and assign training
        module = await TrainingModuleService.create_module(
            db=db_session,
            title="Collections Basics",
            category="training",
            duration_minutes=120,
            delivery_type="in-person",
        )

        await TrainingModuleService.assign_module(
            db=db_session,
            onboarding_id=onboarding.id,
            training_module_id=module.id,
            due_date=date.today() + timedelta(days=14),
        )

        # Create and acknowledge policies
        policy = await PolicyService.create_policy(
            db=db_session,
            title="Collections Policy",
            content="All collection decisions must follow...",
            category="operations",
            effective_date=date.today(),
        )

        await PolicyService.acknowledge_policy(
            db=db_session,
            onboarding_id=onboarding.id,
            policy_id=policy.id,
            acknowledged_by_id=new_staff.id,
        )

        # Schedule check-in
        await CheckInMeetingService.schedule_meeting(
            db=db_session,
            onboarding_id=onboarding.id,
            period=CheckInPeriod.thirty_day,
            scheduled_date=date.today() + timedelta(days=30),
            scheduled_with_id=manager.id,
            topics=["Collections", "Catalog"],
        )

        # Update onboarding status
        await StaffOnboardingService.update_onboarding_status(
            db=db_session,
            onboarding_id=onboarding.id,
            status=OnboardingStatus.in_progress,
        )

        # Verify workflow
        result = await StaffOnboardingService.get_onboarding(
            db=db_session,
            onboarding_id=onboarding.id,
            include_details=True,
        )

        assert result.status == OnboardingStatus.in_progress
        assert len(result.pre_arrival_checklist) > 0
        assert len(result.training_assignments) > 0
        assert len(result.policy_acknowledgments) > 0
        assert len(result.check_in_meetings) > 0
