# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional, Dict
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from app.models.literacy_learner import (
    LiteracyLearner, LiteracyAssessmentRecord, LiteracyProgress,
    LiteracyGoal, LiteracyLearnerStatus, AssessmentType, LearnerAssessmentLevel,
    GoalStatus
)
from app.models.user import User
from app.models.program import Program


class LiteraryLearnerService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def intake_learner(
        self,
        user_id: int,
        program_id: int,
        demographics: Dict,
        referred_from: Optional[str] = None
    ) -> LiteracyLearner:
        learner = LiteracyLearner(
            user_id=user_id,
            program_id=program_id,
            status=LiteracyLearnerStatus.INTAKE_SCHEDULED,
            age=demographics.get("age"),
            date_of_birth=demographics.get("date_of_birth"),
            native_language=demographics.get("native_language"),
            languages_spoken=demographics.get("languages_spoken"),
            education_background=demographics.get("education_background"),
            employment_status=demographics.get("employment_status"),
            income_level=demographics.get("income_level"),
            barriers_to_literacy=demographics.get("barriers_to_literacy"),
            health_notes=demographics.get("health_notes"),
            accessibility_needs=demographics.get("accessibility_needs"),
            transportation_needs=demographics.get("transportation_needs", False),
            childcare_needed=demographics.get("childcare_needed", False),
            referred_from=referred_from,
            notes=demographics.get("notes")
        )
        self.db.add(learner)
        await self.db.flush()
        return learner

    async def assess_learner(
        self,
        learner_id: int,
        assessor_id: int,
        assessment_type: AssessmentType,
        score: float,
        level: LearnerAssessmentLevel,
        assessment_data: Dict
    ) -> LiteracyAssessmentRecord:
        # Calculate percentage if provided
        percentage = assessment_data.get("percentage")
        if percentage is None and assessment_data.get("total_points"):
            percentage = (score / assessment_data.get("total_points")) * 100

        assessment = LiteracyAssessmentRecord(
            learner_id=learner_id,
            assessor_id=assessor_id,
            assessment_type=assessment_type,
            assessment_date=datetime.now(timezone.utc),
            score=score,
            percentage=percentage,
            level=level,
            reading_speed_wpm=assessment_data.get("reading_speed_wpm"),
            comprehension_percentage=assessment_data.get("comprehension_percentage"),
            assessment_tool_used=assessment_data.get("assessment_tool_used"),
            location=assessment_data.get("location"),
            notes=assessment_data.get("notes")
        )

        # Update learner's current level
        learner = await self.db.get(LiteracyLearner, learner_id)

        # Determine level progression
        if learner.current_level and learner.current_level != level:
            if self._level_improved(learner.current_level, level):
                assessment.level_progression = "improved"
            elif self._level_declined(learner.current_level, level):
                assessment.level_progression = "regressed"
            else:
                assessment.level_progression = "maintained"
        else:
            assessment.level_progression = "maintained"

        learner.current_level = level
        learner.last_assessment_date = datetime.now(timezone.utc)
        learner.last_assessment_score = score

        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def get_learner(self, learner_id: int) -> Optional[LiteracyLearner]:
        return await self.db.get(
            LiteracyLearner,
            learner_id,
            options=[
                selectinload(LiteracyLearner.assessments),
                selectinload(LiteracyLearner.goals),
                selectinload(LiteracyLearner.sessions)
            ]
        )

    async def get_learner_level(self, learner_id: int) -> Optional[LearnerAssessmentLevel]:
        learner = await self.db.get(LiteracyLearner, learner_id)
        return learner.current_level if learner else None

    async def update_learner_profile(
        self,
        learner_id: int,
        updates: Dict
    ) -> LiteracyLearner:
        learner = await self.db.get(LiteracyLearner, learner_id)
        if not learner:
            raise ValueError(f"Learner {learner_id} not found")

        # Update allowed fields
        allowed_fields = {
            'age', 'native_language', 'languages_spoken',
            'education_background', 'employment_status',
            'accessibility_needs', 'transportation_needs',
            'childcare_needed', 'referred_from', 'notes',
            'status', 'primary_goal_type'
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(learner, field, value)

        await self.db.flush()
        return learner

    async def list_learners(
        self,
        program_id: int,
        status: Optional[LiteracyLearnerStatus] = None,
        level: Optional[LearnerAssessmentLevel] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[LiteracyLearner], int]:
        query = select(LiteracyLearner)

        if program_id:
            query = query.where(LiteracyLearner.program_id == program_id)
        if status:
            query = query.where(LiteracyLearner.status == status)
        if level:
            query = query.where(LiteracyLearner.current_level == level)

        # Get total count
        count_query = select(func.count()).select_from(LiteracyLearner)
        if program_id:
            count_query = count_query.where(LiteracyLearner.program_id == program_id)
        if status:
            count_query = count_query.where(LiteracyLearner.status == status)
        if level:
            count_query = count_query.where(LiteracyLearner.current_level == level)

        total = await self.db.scalar(count_query)

        learners = await self.db.scalars(
            query.order_by(desc(LiteracyLearner.enrollment_date))
                 .limit(limit)
                 .offset(offset)
        )

        return list(learners), total

    def _level_improved(self, old_level: LearnerAssessmentLevel, new_level: LearnerAssessmentLevel) -> bool:
        levels_order = [
            LearnerAssessmentLevel.PRE_LITERACY,
            LearnerAssessmentLevel.EMERGENT,
            LearnerAssessmentLevel.BEGINNING,
            LearnerAssessmentLevel.INTERMEDIATE,
            LearnerAssessmentLevel.ADVANCED,
            LearnerAssessmentLevel.PROFICIENT
        ]
        return levels_order.index(new_level) > levels_order.index(old_level)

    def _level_declined(self, old_level: LearnerAssessmentLevel, new_level: LearnerAssessmentLevel) -> bool:
        levels_order = [
            LearnerAssessmentLevel.PRE_LITERACY,
            LearnerAssessmentLevel.EMERGENT,
            LearnerAssessmentLevel.BEGINNING,
            LearnerAssessmentLevel.INTERMEDIATE,
            LearnerAssessmentLevel.ADVANCED,
            LearnerAssessmentLevel.PROFICIENT
        ]
        return levels_order.index(new_level) < levels_order.index(old_level)
