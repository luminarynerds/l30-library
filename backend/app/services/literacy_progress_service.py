# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.literacy_matching import LiteracySessionLog, AttendanceStatus
from app.models.literacy_learner import (
    LiteracyLearner, LiteracyProgress, LiteracyAssessmentRecord,
    LearnerAssessmentLevel, LiteracyGoal, GoalStatus
)


class ProgressTrackingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_session(
        self,
        session_log_id: int,
        session_date: date,
        learner_id: int
    ) -> None:
        # Update learner's session counts
        learner = await self.db.get(LiteracyLearner, learner_id)
        if learner:
            session_log = await self.db.get(LiteracySessionLog, session_log_id)
            if session_log and session_log.attendance_status == AttendanceStatus.ATTENDED:
                learner.total_sessions_completed += 1
                if session_log.actual_duration_minutes:
                    learner.total_hours_attended += Decimal(
                        str(session_log.actual_duration_minutes / 60)
                    )

            # Update or create progress record for the month
            await self._update_monthly_progress(learner_id, session_date)

    async def calculate_progress(self, learner_id: int) -> Dict:
        learner = await self.db.get(LiteracyLearner, learner_id)
        if not learner:
            return {}

        # Get latest assessment
        latest_assessment = await self.db.scalar(
            select(LiteracyAssessmentRecord)
            .where(LiteracyAssessmentRecord.learner_id == learner_id)
            .order_by(LiteracyAssessmentRecord.assessment_date.desc())
            .limit(1)
        )

        # Get all assessments to calculate progression
        all_assessments = await self.db.scalars(
            select(LiteracyAssessmentRecord)
            .where(LiteracyAssessmentRecord.learner_id == learner_id)
            .order_by(LiteracyAssessmentRecord.assessment_date)
        )
        assessments = list(all_assessments)

        # Get completed goals
        completed_goals = await self.db.scalar(
            select(func.count(LiteracyGoal.id))
            .where(
                and_(
                    LiteracyGoal.learner_id == learner_id,
                    LiteracyGoal.status == GoalStatus.COMPLETED
                )
            )
        )

        # Get active goals
        active_goals = await self.db.scalar(
            select(func.count(LiteracyGoal.id))
            .where(
                and_(
                    LiteracyGoal.learner_id == learner_id,
                    LiteracyGoal.status == GoalStatus.ACTIVE
                )
            )
        )

        # Calculate improvement percentage
        improvement_percentage = 0.0
        if len(assessments) > 1:
            first_score = assessments[0].score
            latest_score = latest_assessment.score if latest_assessment else first_score
            improvement_percentage = float(
                ((latest_score - first_score) / first_score * 100)
                if first_score > 0 else 0
            )

        return {
            "current_level": str(learner.current_level) if learner.current_level else None,
            "total_hours_attended": float(learner.total_hours_attended),
            "total_sessions_completed": learner.total_sessions_completed,
            "total_assessments": len(assessments),
            "latest_score": float(latest_assessment.score) if latest_assessment else None,
            "improvement_percentage": improvement_percentage,
            "completed_goals": completed_goals or 0,
            "active_goals": active_goals or 0,
            "last_assessment_date": latest_assessment.assessment_date.isoformat() if latest_assessment else None,
            "reading_speed_wpm": learner.current_reading_level_wpm
        }

    async def get_level_readiness(self, learner_id: int) -> Dict:
        progress = await self.calculate_progress(learner_id)
        learner = await self.db.get(LiteracyLearner, learner_id)

        if not learner or not learner.current_level:
            return {"ready": False, "confidence": 0.0, "next_level": None}

        # Get recent assessment performance
        recent_assessments = await self.db.scalars(
            select(LiteracyAssessmentRecord)
            .where(LiteracyAssessmentRecord.learner_id == learner_id)
            .order_by(LiteracyAssessmentRecord.assessment_date.desc())
            .limit(5)
        )
        recent = list(recent_assessments)

        if not recent:
            return {"ready": False, "confidence": 0.0, "next_level": None}

        # Average score of recent assessments
        avg_recent_score = sum(a.score for a in recent) / len(recent)

        # Readiness criteria
        score_threshold = 80.0  # 80% on recent assessments
        min_hours = 20.0  # At least 20 hours at current level
        min_sessions = 10  # At least 10 sessions

        meets_score = float(avg_recent_score) >= score_threshold
        meets_hours = float(progress.get("total_hours_attended", 0)) >= min_hours
        meets_sessions = progress.get("total_sessions_completed", 0) >= min_sessions

        confidence = 0.0
        if meets_score:
            confidence += 0.5
        if meets_hours:
            confidence += 0.25
        if meets_sessions:
            confidence += 0.25

        next_level = self._get_next_level(learner.current_level)

        return {
            "ready": confidence >= 0.75,
            "confidence": confidence,
            "next_level": next_level.value if next_level else None,
            "score_ready": meets_score,
            "hours_ready": meets_hours,
            "sessions_ready": meets_sessions
        }

    async def identify_improvement_areas(self, learner_id: int) -> List[Dict]:
        assessments = await self.db.scalars(
            select(LiteracyAssessmentRecord)
            .where(LiteracyAssessmentRecord.learner_id == learner_id)
            .order_by(LiteracyAssessmentRecord.assessment_date.desc())
            .limit(10)
        )
        recent = list(assessments)

        if not recent:
            return []

        improvement_areas = []

        # Analyze by assessment type
        for assessment in recent:
            if assessment.comprehension_percentage:
                comprehension_score = float(assessment.comprehension_percentage)
                if comprehension_score < 70.0:
                    improvement_areas.append({
                        "area": "Reading Comprehension",
                        "score": comprehension_score,
                        "recommendation": "Practice guided reading and comprehension questions",
                        "priority": "high" if comprehension_score < 50 else "medium"
                    })

            if assessment.reading_speed_wpm:
                if assessment.reading_speed_wpm < 80:
                    improvement_areas.append({
                        "area": "Reading Fluency",
                        "score": assessment.reading_speed_wpm,
                        "recommendation": "Increase reading practice and use fluency exercises",
                        "priority": "medium"
                    })

        return improvement_areas[:5]  # Return top 5 areas

    async def generate_recommendations(self, learner_id: int) -> List[Dict]:
        learner = await self.db.get(LiteracyLearner, learner_id)
        if not learner:
            return []

        recommendations = []

        # Recommendation 1: Based on current level
        current_level = learner.current_level
        if current_level:
            recommendations.append({
                "type": "resource_list",
                "title": f"Resources for {current_level.value.replace('_', ' ').title()} Level",
                "description": "Curated materials for your current level",
                "action": "browse_resources"
            })

        # Recommendation 2: Based on goals
        goals = await self.db.scalars(
            select(LiteracyGoal)
            .where(
                and_(
                    LiteracyGoal.learner_id == learner_id,
                    LiteracyGoal.status == GoalStatus.ACTIVE
                )
            )
        )
        for goal in list(goals)[:2]:
            recommendations.append({
                "type": "goal_support",
                "title": "Materials to Support Your Goal",
                "description": goal.goal_statement,
                "goal_id": goal.id,
                "action": "view_goal"
            })

        # Recommendation 3: Based on progress
        progress = await self.calculate_progress(learner_id)
        if progress.get("total_sessions_completed", 0) > 0:
            recommendations.append({
                "type": "challenge",
                "title": "Ready for a Challenge?",
                "description": "You've been making great progress!",
                "action": "take_assessment"
            })

        return recommendations

    async def _update_monthly_progress(
        self,
        learner_id: int,
        session_date: date
    ) -> LiteracyProgress:
        # Find or create progress record for this month
        period_start = date(session_date.year, session_date.month, 1)
        # Calculate last day of month
        if session_date.month == 12:
            period_end = date(session_date.year + 1, 1, 1)
        else:
            period_end = date(session_date.year, session_date.month + 1, 1)
        period_end = date(period_end.year, period_end.month, period_end.day) - \
                     timedelta(days=1)

        progress = await self.db.scalar(
            select(LiteracyProgress).where(
                and_(
                    LiteracyProgress.learner_id == learner_id,
                    LiteracyProgress.period_start == period_start,
                    LiteracyProgress.period_end == period_end
                )
            )
        )

        if not progress:
            progress = LiteracyProgress(
                learner_id=learner_id,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(progress)

        # Increment session count
        progress.sessions_completed += 1

        # Calculate attendance rate
        total_sessions = await self.db.scalar(
            select(func.count(LiteracySessionLog.id)).where(
                and_(
                    LiteracySessionLog.learner_id == learner_id,
                    LiteracySessionLog.session_date >= period_start,
                    LiteracySessionLog.session_date <= period_end
                )
            )
        )

        attended_sessions = await self.db.scalar(
            select(func.count(LiteracySessionLog.id)).where(
                and_(
                    LiteracySessionLog.learner_id == learner_id,
                    LiteracySessionLog.session_date >= period_start,
                    LiteracySessionLog.session_date <= period_end,
                    LiteracySessionLog.attendance_status == AttendanceStatus.ATTENDED
                )
            )
        )

        if total_sessions and total_sessions > 0:
            progress.attendance_rate = Decimal(str((attended_sessions or 0) / total_sessions * 100))

        await self.db.flush()
        return progress

    @staticmethod
    def _get_next_level(current_level: LearnerAssessmentLevel) -> Optional[LearnerAssessmentLevel]:
        level_progression = [
            LearnerAssessmentLevel.PRE_LITERACY,
            LearnerAssessmentLevel.EMERGENT,
            LearnerAssessmentLevel.BEGINNING,
            LearnerAssessmentLevel.INTERMEDIATE,
            LearnerAssessmentLevel.ADVANCED,
            LearnerAssessmentLevel.PROFICIENT
        ]

        if current_level in level_progression:
            idx = level_progression.index(current_level)
            if idx < len(level_progression) - 1:
                return level_progression[idx + 1]

        return None
