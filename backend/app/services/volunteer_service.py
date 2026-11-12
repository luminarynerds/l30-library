# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.volunteer import (
    AppreciationRecord, AvailabilityPreference, BackgroundCheck,
    BackgroundCheckStatus, ReferenceLetter, RecognitionAward,
    ShiftSignup, ShiftSignupStatus, SkillMatch, SkillOpportunity,
    TrainingRecord, TrainingStatus, TrainingType, Volunteer,
    VolunteerApplication, VolunteerApplicationStatus, VolunteerCommunication,
    GeneralVolunteerHourLog, HourLogStatus, VolunteerMilestone, VolunteerShift,
    VolunteerSkill, VolunteerStatus, MilestoneType
)
from ..models.user import User


class VolunteerProfileService:

    @staticmethod
    async def create_volunteer_profile(
        db: AsyncSession,
        user_id: int,
        primary_role_category: str,
        phone: str,
        **kwargs
    ) -> Volunteer:
        # Check if volunteer profile already exists
        existing = await db.execute(
            select(Volunteer).where(Volunteer.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Volunteer profile already exists for this user")

        volunteer = Volunteer(
            user_id=user_id,
            primary_role_category=primary_role_category,
            phone=phone,
            **kwargs
        )
        db.add(volunteer)
        await db.commit()
        await db.refresh(volunteer)
        return volunteer

    @staticmethod
    async def get_volunteer_profile(
        db: AsyncSession,
        volunteer_id: int
    ) -> Optional[Volunteer]:
        result = await db.execute(
            select(Volunteer)
            .where(Volunteer.id == volunteer_id)
            .options(
                joinedload(Volunteer.user),
                joinedload(Volunteer.background_checks),
                joinedload(Volunteer.training_records),
                joinedload(Volunteer.availability_preference)
            )
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update_volunteer_status(
        db: AsyncSession,
        volunteer_id: int,
        status: VolunteerStatus
    ) -> Volunteer:
        result = await db.execute(
            select(Volunteer).where(Volunteer.id == volunteer_id)
        )
        volunteer = result.scalar_one_or_none()
        if not volunteer:
            raise ValueError("Volunteer not found")

        volunteer.status = status
        volunteer.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(volunteer)
        return volunteer

    @staticmethod
    async def get_volunteer_by_user(
        db: AsyncSession,
        user_id: int
    ) -> Optional[Volunteer]:
        result = await db.execute(
            select(Volunteer).where(Volunteer.user_id == user_id)
        )
        return result.scalar_one_or_none()


class VolunteerApplicationService:

    @staticmethod
    async def submit_application(
        db: AsyncSession,
        user_id: int,
        application_data: dict
    ) -> VolunteerApplication:
        # Check if user already has an active application
        existing = await db.execute(
            select(VolunteerApplication)
            .where(
                VolunteerApplication.user_id == user_id,
                VolunteerApplication.status.in_([
                    VolunteerApplicationStatus.submitted,
                    VolunteerApplicationStatus.under_review,
                    VolunteerApplicationStatus.approved
                ])
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You already have an active volunteer application")

        application = VolunteerApplication(
            user_id=user_id,
            status=VolunteerApplicationStatus.draft,
            **application_data
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def submit_application_for_review(
        db: AsyncSession,
        application_id: int
    ) -> VolunteerApplication:
        result = await db.execute(
            select(VolunteerApplication)
            .where(VolunteerApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise ValueError("Application not found")

        if application.status != VolunteerApplicationStatus.draft:
            raise ValueError("Only draft applications can be submitted")

        application.status = VolunteerApplicationStatus.submitted
        application.submitted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def review_application(
        db: AsyncSession,
        application_id: int,
        reviewer_id: int,
        status: VolunteerApplicationStatus,
        review_notes: Optional[str] = None,
        denial_reason: Optional[str] = None
    ) -> VolunteerApplication:
        result = await db.execute(
            select(VolunteerApplication)
            .where(VolunteerApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise ValueError("Application not found")

        application.status = status
        application.reviewed_by_id = reviewer_id
        application.reviewed_at = datetime.now(timezone.utc)
        application.review_notes = review_notes
        if denial_reason:
            application.denial_reason = denial_reason

        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def approve_and_create_profile(
        db: AsyncSession,
        application_id: int,
        approver_id: int
    ) -> Tuple[VolunteerApplication, Volunteer]:
        result = await db.execute(
            select(VolunteerApplication)
            .where(VolunteerApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise ValueError("Application not found")

        # Review the application first
        application = await VolunteerApplicationService.review_application(
            db, application_id, approver_id,
            VolunteerApplicationStatus.approved
        )

        # Create volunteer profile
        volunteer = await VolunteerProfileService.create_volunteer_profile(
            db,
            user_id=application.user_id,
            primary_role_category=application.preferred_roles[0] if application.preferred_roles else "other",
            phone="",  # Will be updated by staff
            status=VolunteerStatus.pending_background,
            approved_at=datetime.now(timezone.utc),
            approved_by_id=approver_id
        )

        return application, volunteer


class BackgroundCheckService:

    @staticmethod
    async def create_background_check(
        db: AsyncSession,
        volunteer_id: int,
        check_type: str
    ) -> BackgroundCheck:
        # Check if already exists
        existing = await db.execute(
            select(BackgroundCheck)
            .where(BackgroundCheck.volunteer_id == volunteer_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Background check already exists for this volunteer")

        bg_check = BackgroundCheck(
            volunteer_id=volunteer_id,
            check_type=check_type,
            status=BackgroundCheckStatus.not_started
        )
        db.add(bg_check)
        await db.commit()
        await db.refresh(bg_check)
        return bg_check

    @staticmethod
    async def mark_check_in_progress(
        db: AsyncSession,
        check_id: int,
        provider_name: str,
        provider_reference_id: str
    ) -> BackgroundCheck:
        result = await db.execute(
            select(BackgroundCheck).where(BackgroundCheck.id == check_id)
        )
        bg_check = result.scalar_one_or_none()
        if not bg_check:
            raise ValueError("Background check not found")

        bg_check.status = BackgroundCheckStatus.in_progress
        bg_check.initiated_at = datetime.now(timezone.utc)
        bg_check.provider_name = provider_name
        bg_check.provider_reference_id = provider_reference_id
        await db.commit()
        await db.refresh(bg_check)
        return bg_check

    @staticmethod
    async def complete_background_check(
        db: AsyncSession,
        check_id: int,
        result_summary: str,
        issues_found: List[str] = None,
        issues_description: Optional[str] = None
    ) -> BackgroundCheck:
        result = await db.execute(
            select(BackgroundCheck).where(BackgroundCheck.id == check_id)
        )
        bg_check = result.scalar_one_or_none()
        if not bg_check:
            raise ValueError("Background check not found")

        bg_check.status = BackgroundCheckStatus.clear if result_summary == "clear" else BackgroundCheckStatus.issues
        bg_check.result_summary = result_summary
        bg_check.issues_found = issues_found or []
        bg_check.issues_description = issues_description
        bg_check.completed_at = datetime.now(timezone.utc)
        bg_check.expires_at = date.today() + timedelta(days=365*3)  # 3-year expiration

        await db.commit()
        await db.refresh(bg_check)
        return bg_check

    @staticmethod
    async def approve_background_check(
        db: AsyncSession,
        check_id: int,
        approver_id: int,
        approval_notes: Optional[str] = None
    ) -> BackgroundCheck:
        result = await db.execute(
            select(BackgroundCheck).where(BackgroundCheck.id == check_id)
        )
        bg_check = result.scalar_one_or_none()
        if not bg_check:
            raise ValueError("Background check not found")

        bg_check.approved_by_id = approver_id
        bg_check.approved_at = datetime.now(timezone.utc)
        bg_check.approval_notes = approval_notes

        # Update volunteer status
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.id == bg_check.volunteer_id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        if volunteer and volunteer.status == VolunteerStatus.pending_background:
            volunteer.status = VolunteerStatus.pending_training

        await db.commit()
        await db.refresh(bg_check)
        return bg_check


class TrainingService:

    @staticmethod
    async def assign_training(
        db: AsyncSession,
        volunteer_id: int,
        training_type_id: int,
        due_at: Optional[datetime] = None
    ) -> TrainingRecord:
        # Check if already assigned
        existing = await db.execute(
            select(TrainingRecord)
            .where(
                TrainingRecord.volunteer_id == volunteer_id,
                TrainingRecord.training_type_id == training_type_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Training already assigned to this volunteer")

        training_record = TrainingRecord(
            volunteer_id=volunteer_id,
            training_type_id=training_type_id,
            status=TrainingStatus.not_started,
            due_at=due_at
        )
        db.add(training_record)
        await db.commit()
        await db.refresh(training_record)
        return training_record

    @staticmethod
    async def complete_training(
        db: AsyncSession,
        training_id: int,
        trainer_id: Optional[int] = None,
        completion_notes: Optional[str] = None,
        score: Optional[float] = None
    ) -> TrainingRecord:
        result = await db.execute(
            select(TrainingRecord).where(TrainingRecord.id == training_id)
        )
        training = result.scalar_one_or_none()
        if not training:
            raise ValueError("Training record not found")

        training.status = TrainingStatus.completed
        training.completed_at = datetime.now(timezone.utc)
        training.trainer_id = trainer_id
        training.completion_notes = completion_notes
        training.score = score

        # Get training type to set expiration
        tt_result = await db.execute(
            select(TrainingType).where(TrainingType.id == training.training_type_id)
        )
        training_type = tt_result.scalar_one_or_none()
        if training_type and training_type.recurrence_months:
            training.expires_at = (
                datetime.now(timezone.utc) + timedelta(days=training_type.recurrence_months * 30)
            ).date()

        await db.commit()
        await db.refresh(training)
        return training


class AvailabilityService:

    @staticmethod
    async def set_availability(
        db: AsyncSession,
        volunteer_id: int,
        availability_data: dict
    ) -> AvailabilityPreference:
        result = await db.execute(
            select(AvailabilityPreference)
            .where(AvailabilityPreference.volunteer_id == volunteer_id)
        )
        preference = result.scalar_one_or_none()

        if preference:
            # Update existing
            for key, value in availability_data.items():
                setattr(preference, key, value)
        else:
            # Create new
            preference = AvailabilityPreference(
                volunteer_id=volunteer_id,
                **availability_data
            )
            db.add(preference)

        preference.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(preference)
        return preference


class ShiftService:

    @staticmethod
    async def create_shift(
        db: AsyncSession,
        shift_data: dict,
        created_by_id: int
    ) -> VolunteerShift:
        shift = VolunteerShift(
            created_by_id=created_by_id,
            **shift_data
        )
        db.add(shift)
        await db.commit()
        await db.refresh(shift)
        return shift

    @staticmethod
    async def update_shift(
        db: AsyncSession,
        shift: VolunteerShift,
        updates: dict,
    ) -> VolunteerShift:
        for key, value in updates.items():
            setattr(shift, key, value)
        await db.commit()
        await db.refresh(shift)
        return shift

    @staticmethod
    async def cancel_shift(
        db: AsyncSession,
        shift: VolunteerShift,
    ) -> VolunteerShift:
        # Soft-cancel: signups/history are kept, patron-facing list hides it.
        shift.cancelled = True
        await db.commit()
        await db.refresh(shift)
        return shift

    @staticmethod
    async def signup_for_shift(
        db: AsyncSession,
        shift_id: int,
        volunteer_id: int
    ) -> ShiftSignup:
        # Check if already signed up
        existing = await db.execute(
            select(ShiftSignup)
            .where(
                ShiftSignup.shift_id == shift_id,
                ShiftSignup.volunteer_id == volunteer_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Volunteer already signed up for this shift")

        # Check if shift has capacity
        shift_result = await db.execute(
            select(VolunteerShift).where(VolunteerShift.id == shift_id)
        )
        shift = shift_result.scalar_one_or_none()
        if not shift:
            raise ValueError("Shift not found")

        if shift.volunteers_signed_up >= shift.volunteers_needed:
            raise ValueError("Shift is at capacity")

        signup = ShiftSignup(
            shift_id=shift_id,
            volunteer_id=volunteer_id,
            status=ShiftSignupStatus.pending
        )
        db.add(signup)

        # Update shift signup count
        shift.volunteers_signed_up += 1

        await db.commit()
        await db.refresh(signup)
        return signup

    @staticmethod
    async def confirm_signup(
        db: AsyncSession,
        signup_id: int
    ) -> ShiftSignup:
        result = await db.execute(
            select(ShiftSignup).where(ShiftSignup.id == signup_id)
        )
        signup = result.scalar_one_or_none()
        if not signup:
            raise ValueError("Signup not found")

        signup.status = ShiftSignupStatus.confirmed
        signup.confirmed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(signup)
        return signup

    @staticmethod
    async def complete_shift(
        db: AsyncSession,
        signup_id: int,
        actual_hours: Optional[float] = None
    ) -> ShiftSignup:
        result = await db.execute(
            select(ShiftSignup).where(ShiftSignup.id == signup_id)
        )
        signup = result.scalar_one_or_none()
        if not signup:
            raise ValueError("Signup not found")

        signup.status = ShiftSignupStatus.completed
        signup.completed_at = datetime.now(timezone.utc)
        signup.actual_hours = actual_hours

        # Update volunteer total hours and shifts
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.id == signup.volunteer_id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        if volunteer:
            volunteer.total_shifts += 1
            if actual_hours:
                volunteer.total_hours += actual_hours
            volunteer.last_active_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(signup)
        return signup


class HourLogService:

    @staticmethod
    async def log_hours(
        db: AsyncSession,
        volunteer_id: int,
        log_date: date,
        hours: float,
        activity_type: str,
        description: Optional[str] = None,
        shift_signup_id: Optional[int] = None
    ) -> GeneralVolunteerHourLog:
        # Logged hours go straight to submitted: the patron UI has no draft
        # step, and every summary counts pending hours from the submitted
        # status (pending logs would never surface anywhere).
        hour_log = GeneralVolunteerHourLog(
            volunteer_id=volunteer_id,
            log_date=log_date,
            hours=hours,
            activity_type=activity_type,
            description=description,
            shift_signup_id=shift_signup_id,
            status=HourLogStatus.submitted,
            submitted_by_volunteer_at=datetime.now(timezone.utc)
        )
        db.add(hour_log)
        await db.commit()
        await db.refresh(hour_log)
        return hour_log

    @staticmethod
    async def submit_hour_log(
        db: AsyncSession,
        log_id: int
    ) -> GeneralVolunteerHourLog:
        result = await db.execute(
            select(GeneralVolunteerHourLog).where(GeneralVolunteerHourLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise ValueError("Hour log not found")

        log.status = HourLogStatus.submitted
        log.submitted_by_volunteer_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def verify_hours(
        db: AsyncSession,
        log_id: int,
        verifier_id: int,
        verification_notes: Optional[str] = None
    ) -> GeneralVolunteerHourLog:
        result = await db.execute(
            select(GeneralVolunteerHourLog).where(GeneralVolunteerHourLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise ValueError("Hour log not found")

        log.status = HourLogStatus.verified
        log.verified_by_id = verifier_id
        log.verified_at = datetime.now(timezone.utc)
        log.verification_notes = verification_notes

        # Update volunteer total hours
        volunteer_result = await db.execute(
            select(Volunteer).where(Volunteer.id == log.volunteer_id)
        )
        volunteer = volunteer_result.scalar_one_or_none()
        if volunteer:
            volunteer.total_hours += log.hours
            volunteer.last_active_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def reject_hours(
        db: AsyncSession,
        log: GeneralVolunteerHourLog,
        reason: str,
        rejector_id: int,
    ) -> GeneralVolunteerHourLog:
        # Deliberately does NOT touch Volunteer.total_hours (only verify does).
        log.status = HourLogStatus.rejected
        log.rejected_reason = reason
        log.rejected_by_id = rejector_id
        log.rejected_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(log)
        return log


class SkillMatchingService:

    @staticmethod
    async def add_volunteer_skill(
        db: AsyncSession,
        volunteer_id: int,
        skill_name: str,
        proficiency_level: str = "intermediate",
        years_of_experience: Optional[float] = None,
        description: Optional[str] = None
    ) -> VolunteerSkill:
        skill = VolunteerSkill(
            volunteer_id=volunteer_id,
            skill_name=skill_name,
            proficiency_level=proficiency_level,
            years_of_experience=years_of_experience,
            description=description,
            verified=False
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return skill

    @staticmethod
    async def calculate_skill_match(
        volunteer_skills: List[VolunteerSkill],
        required_skills: List[str],
        preferred_skills: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        volunteer_skill_names = {s.skill_name.lower() for s in volunteer_skills}

        matched = []
        missing = []

        # Check required skills
        for req_skill in required_skills:
            if req_skill.lower() in volunteer_skill_names:
                matched.append(req_skill)
            else:
                missing.append(req_skill)

        # Check preferred skills
        for pref_skill in preferred_skills:
            if pref_skill.lower() in volunteer_skill_names and pref_skill not in matched:
                matched.append(pref_skill)

        # Calculate score (0-100)
        # All required skills = 70 points, preferred skills = 30 points
        score = 0.0
        if required_skills:
            score += (len(matched) / len(required_skills)) * 70
        if preferred_skills:
            score += min(len([s for s in matched if s in preferred_skills]) / len(preferred_skills), 1.0) * 30

        return score, matched, missing

    @staticmethod
    async def match_volunteer_to_opportunities(
        db: AsyncSession,
        volunteer_id: int
    ) -> List[SkillMatch]:
        # Get volunteer skills
        skills_result = await db.execute(
            select(VolunteerSkill)
            .where(VolunteerSkill.volunteer_id == volunteer_id)
        )
        volunteer_skills = skills_result.scalars().all()

        # Get active opportunities
        opps_result = await db.execute(
            select(SkillOpportunity)
            .where(SkillOpportunity.active == True)
        )
        opportunities = opps_result.scalars().all()

        matches = []
        for opp in opportunities:
            # Check for existing match
            existing = await db.execute(
                select(SkillMatch)
                .where(
                    SkillMatch.volunteer_id == volunteer_id,
                    SkillMatch.opportunity_id == opp.id
                )
            )
            if existing.scalar_one_or_none():
                continue  # Already matched

            # Calculate match score
            score, matched_skills, missing_skills = await SkillMatchingService.calculate_skill_match(
                volunteer_skills,
                opp.required_skills,
                opp.preferred_skills
            )

            # Only create match if score is above 50%
            if score >= 50:
                match = SkillMatch(
                    volunteer_id=volunteer_id,
                    opportunity_id=opp.id,
                    match_score=score,
                    matched_skills=matched_skills,
                    missing_skills=missing_skills
                )
                db.add(match)
                matches.append(match)

        if matches:
            await db.commit()

        return matches


class MilestoneService:

    @staticmethod
    async def check_and_award_milestones(
        db: AsyncSession,
        volunteer_id: int
    ) -> List[VolunteerMilestone]:
        result = await db.execute(
            select(Volunteer).where(Volunteer.id == volunteer_id)
        )
        volunteer = result.scalar_one_or_none()
        if not volunteer:
            raise ValueError("Volunteer not found")

        milestones_awarded = []

        # Check hour-based milestones
        milestone_thresholds = {
            MilestoneType.hours_25: 25,
            MilestoneType.hours_50: 50,
            MilestoneType.hours_100: 100,
            MilestoneType.hours_250: 250,
            MilestoneType.hours_500: 500,
            MilestoneType.hours_1000: 1000,
        }

        for milestone_type, threshold in milestone_thresholds.items():
            # Check if already awarded
            existing = await db.execute(
                select(VolunteerMilestone)
                .where(
                    VolunteerMilestone.volunteer_id == volunteer_id,
                    VolunteerMilestone.milestone_type == milestone_type
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Check if threshold met
            if volunteer.total_hours >= threshold:
                milestone = VolunteerMilestone(
                    volunteer_id=volunteer_id,
                    milestone_type=milestone_type,
                    achievement_value=volunteer.total_hours,
                    celebration_message=f"Congratulations! You've reached {threshold} volunteer hours!"
                )
                db.add(milestone)
                milestones_awarded.append(milestone)

        if milestones_awarded:
            await db.commit()

        return milestones_awarded


class CommunicationService:

    @staticmethod
    async def send_communication(
        db: AsyncSession,
        volunteer_id: int,
        subject: str,
        message_body: str,
        communication_type: str,
        sent_by_id: Optional[int] = None,
        category: Optional[str] = None,
        response_required: bool = False
    ) -> VolunteerCommunication:
        comm = VolunteerCommunication(
            volunteer_id=volunteer_id,
            subject=subject,
            message_body=message_body,
            communication_type=communication_type,
            sent_by_id=sent_by_id,
            category=category,
            response_required=response_required,
            sent_at=datetime.now(timezone.utc)
        )
        db.add(comm)
        await db.commit()
        await db.refresh(comm)
        return comm


class ReferenceLetterService:

    @staticmethod
    async def generate_reference_letter(
        db: AsyncSession,
        volunteer_id: int,
        purpose: str,
        generated_by_id: int,
        recipient_name: Optional[str] = None,
        recipient_organization: Optional[str] = None
    ) -> ReferenceLetter:
        # Get volunteer with stats
        result = await db.execute(
            select(Volunteer)
            .where(Volunteer.id == volunteer_id)
            .options(joinedload(Volunteer.user))
        )
        volunteer = result.unique().scalar_one_or_none()
        if not volunteer:
            raise ValueError("Volunteer not found")

        # Calculate years of service
        created_date = volunteer.created_at.date() if volunteer.created_at else date.today()
        years_of_service = (date.today() - created_date).days / 365.25

        # Build letter
        letter_title = f"Volunteer Reference Letter - {volunteer.user.name}"
        letter_body = f"""
Dear {recipient_organization or 'Recipient'},

I am writing to provide a strong letter of recommendation for {volunteer.user.name},
who has been an exceptional volunteer with our organization.

{volunteer.user.name} has dedicated {volunteer.total_hours:.1f} hours of service over the past {years_of_service:.1f} years.
During this time, they have consistently demonstrated professionalism, reliability, and a genuine commitment to our mission.

Their key accomplishments include:
- Completing {volunteer.total_shifts} volunteer shifts
- Maintaining perfect attendance and punctuality
- Demonstrating leadership and mentoring skills

{volunteer.user.name} is a trustworthy, dedicated individual who would be an asset to any organization.

Sincerely,
L30 Library Management
"""

        letter = ReferenceLetter(
            volunteer_id=volunteer_id,
            purpose=purpose,
            recipient_name=recipient_name,
            recipient_organization=recipient_organization,
            letter_title=letter_title,
            letter_body=letter_body,
            volunteer_total_hours=volunteer.total_hours,
            volunteer_years_of_service=years_of_service,
            volunteer_roles=[volunteer.primary_role_category],
            generated_by_id=generated_by_id
        )
        db.add(letter)
        await db.commit()
        await db.refresh(letter)
        return letter


class AppreciationService:

    @staticmethod
    async def record_appreciation(
        db: AsyncSession,
        volunteer_id: int,
        appreciation_type: str,
        description: str,
        given_by_id: Optional[int] = None,
        reason: Optional[str] = None,
        occasion: Optional[str] = None,
        made_public: bool = False
    ) -> AppreciationRecord:
        record = AppreciationRecord(
            volunteer_id=volunteer_id,
            appreciation_type=appreciation_type,
            description=description,
            given_by_id=given_by_id,
            reason=reason,
            occasion=occasion,
            made_public=made_public,
            given_at=datetime.now(timezone.utc)
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
