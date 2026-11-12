# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional, Dict, Tuple
from datetime import datetime, date, time, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.models.literacy_matching import (
    LiteracyTutorMatch, LiteracySessionSchedule, LiteracySessionLog,
    MatchStatus, LiteracySessionStatus, AttendanceStatus
)
from app.models.literacy_learner import LiteracyLearner
from app.models.literacy_tutor import TutorProfile, LiteracyTutorAvailability


class TutorMatchingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_compatible_tutors(
        self,
        learner_id: int,
        criteria: Dict
    ) -> List[Tuple[TutorProfile, float]]:
        learner = await self.db.get(
            LiteracyLearner,
            learner_id,
            options=[selectinload(LiteracyLearner.user)]
        )
        if not learner:
            return []

        # Get all active tutors
        tutors_result = await self.db.scalars(
            select(TutorProfile).where(TutorProfile.is_active == True)
        )
        tutors = list(tutors_result)

        # Calculate compatibility for each tutor
        scored_tutors = []
        for tutor in tutors:
            score = await self.calculate_match_score(learner_id, tutor.id, criteria)
            if score > 0:
                scored_tutors.append((tutor, score))

        # Sort by score descending
        scored_tutors.sort(key=lambda x: x[1], reverse=True)
        return scored_tutors

    async def calculate_match_score(
        self,
        learner_id: int,
        tutor_id: int,
        criteria: Optional[Dict] = None
    ) -> float:
        if criteria is None:
            criteria = {}

        learner = await self.db.get(LiteracyLearner, learner_id)
        tutor = await self.db.get(TutorProfile, tutor_id)

        if not learner or not tutor:
            return 0.0

        scores = []
        weights = []

        # Language match (weight: 20%)
        language_score = self._calculate_language_match(
            learner.languages_spoken,
            tutor.languages_spoken
        )
        scores.append(language_score)
        weights.append(0.20)

        # Specialization alignment (weight: 25%)
        specialization_score = self._calculate_specialization_match(
            learner.primary_goal_type,
            tutor.specializations,
            tutor.can_teach_ged,
            tutor.can_teach_esol
        )
        scores.append(specialization_score)
        weights.append(0.25)

        # Availability compatibility (weight: 20%)
        availability_score = await self._calculate_availability_match(tutor_id)
        scores.append(availability_score)
        weights.append(0.20)

        # Experience level match (weight: 20%)
        experience_score = self._calculate_experience_match(
            tutor.years_experience,
            tutor.total_learners_taught
        )
        scores.append(experience_score)
        weights.append(0.20)

        # Learner preference (weight: 15%)
        preference_score = criteria.get("preference_score", 1.0)
        scores.append(preference_score)
        weights.append(0.15)

        # Calculate weighted average
        if not scores:
            return 0.0

        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        return min(1.0, max(0.0, final_score))

    async def create_match(
        self,
        learner_id: int,
        tutor_id: int,
        reason: str,
        compatibility_score: float,
        score_breakdown: Optional[Dict] = None
    ) -> LiteracyTutorMatch:
        match = LiteracyTutorMatch(
            learner_id=learner_id,
            tutor_id=tutor_id,
            match_date=datetime.now(timezone.utc),
            status=MatchStatus.PROPOSED,
            reason=reason,
            compatibility_score=Decimal(str(compatibility_score)),
            score_breakdown=str(score_breakdown) if score_breakdown else None
        )
        self.db.add(match)
        await self.db.flush()
        return match

    async def activate_match(self, match_id: int) -> LiteracyTutorMatch:
        match = await self.db.get(LiteracyTutorMatch, match_id)
        if match:
            match.status = MatchStatus.ACTIVE
            match.start_date = date.today()
            await self.db.flush()
        return match

    async def end_match(self, match_id: int, reason: str) -> LiteracyTutorMatch:
        match = await self.db.get(LiteracyTutorMatch, match_id)
        if match:
            match.status = MatchStatus.ENDED
            match.end_date = date.today()
            match.end_reason = reason
            await self.db.flush()
        return match

    async def check_tutor_availability(
        self,
        tutor_id: int,
        requested_date: date,
        requested_time: time,
        duration_minutes: int = 60
    ) -> bool:
        day_of_week = requested_date.weekday()

        # Get tutor's availability for this day
        availability_result = await self.db.scalars(
            select(LiteracyTutorAvailability).where(
                and_(
                    LiteracyTutorAvailability.tutor_id == tutor_id,
                    LiteracyTutorAvailability.day_of_week == day_of_week,
                    LiteracyTutorAvailability.is_active == True
                )
            )
        )
        availability_slots = list(availability_result)

        if not availability_slots:
            return False

        # Check if requested time falls within available slots
        requested_end_time = self._add_minutes_to_time(requested_time, duration_minutes)

        for slot in availability_slots:
            slot_start = datetime.strptime(slot.start_time, "%H:%M").time()
            slot_end = datetime.strptime(slot.end_time, "%H:%M").time()

            if slot_start <= requested_time and requested_end_time <= slot_end:
                return True

        return False

    async def schedule_session(
        self,
        match_id: int,
        scheduled_date: date,
        start_time: time,
        duration_minutes: int,
        location: Optional[str] = None,
        is_remote: bool = False,
        meeting_url: Optional[str] = None
    ) -> LiteracySessionSchedule:
        session = LiteracySessionSchedule(
            match_id=match_id,
            scheduled_date=scheduled_date,
            start_time=start_time,
            duration_minutes=duration_minutes,
            status=LiteracySessionStatus.SCHEDULED,
            location=location,
            is_remote=is_remote,
            meeting_url=meeting_url
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def log_session(
        self,
        match_id: int,
        learner_id: int,
        tutor_id: int,
        session_date: date,
        attendance_status: AttendanceStatus,
        actual_duration_minutes: Optional[int] = None,
        engagement_notes: Optional[Dict] = None
    ) -> LiteracySessionLog:
        session_log = LiteracySessionLog(
            match_id=match_id,
            learner_id=learner_id,
            tutor_id=tutor_id,
            session_date=session_date,
            attendance_status=attendance_status,
            actual_duration_minutes=actual_duration_minutes,
            learner_engagement=engagement_notes.get("engagement") if engagement_notes else None,
            learner_focus=engagement_notes.get("focus") if engagement_notes else None,
            progress_observed=engagement_notes.get("progress") if engagement_notes else None
        )

        # Update match session count and hours
        match = await self.db.get(LiteracyTutorMatch, match_id)
        if attendance_status == AttendanceStatus.ATTENDED:
            match.sessions_completed += 1
            if actual_duration_minutes:
                match.total_hours += Decimal(str(actual_duration_minutes / 60))

        self.db.add(session_log)
        await self.db.flush()
        return session_log

    def _calculate_language_match(
        self,
        learner_languages: Optional[str],
        tutor_languages: Optional[str]
    ) -> float:
        if not learner_languages or not tutor_languages:
            return 0.5  # Neutral if unknown

        learner_langs = set(lang.strip().lower() for lang in learner_languages.split(','))
        tutor_langs = set(lang.strip().lower() for lang in tutor_languages.split(','))

        if not learner_langs or not tutor_langs:
            return 0.5

        intersection = len(learner_langs & tutor_langs)
        union = len(learner_langs | tutor_langs)

        return intersection / union if union > 0 else 0.5

    def _calculate_specialization_match(
        self,
        learner_goal: Optional[str],
        tutor_specializations: Optional[str],
        can_teach_ged: bool,
        can_teach_esol: bool
    ) -> float:
        if not learner_goal:
            return 0.5

        score = 0.0

        # Check GED focus
        if "ged" in learner_goal.lower() and can_teach_ged:
            score += 0.5

        # Check ESOL focus
        if "esol" in learner_goal.lower() or "esl" in learner_goal.lower():
            if can_teach_esol:
                score += 0.5

        # Check specializations
        if tutor_specializations and learner_goal.lower() in tutor_specializations.lower():
            score += 0.5

        return min(1.0, score)

    async def _calculate_availability_match(self, tutor_id: int) -> float:
        availability_count = await self.db.scalar(
            select(len(select(LiteracyTutorAvailability).where(
                and_(
                    LiteracyTutorAvailability.tutor_id == tutor_id,
                    LiteracyTutorAvailability.is_active == True
                )
            ).correlate(None)))
        )

        # Score based on number of availability slots (max 7 per week)
        score = min(1.0, (availability_count or 0) / 7)
        return max(0.3, score)  # Minimum 0.3 if some availability

    def _calculate_experience_match(
        self,
        years_experience: Optional[int],
        learners_taught: int
    ) -> float:
        if years_experience is None:
            return 0.5

        # More experienced tutors score higher
        experience_score = min(1.0, years_experience / 5)  # Cap at 5 years
        learner_count_score = min(1.0, learners_taught / 20)  # Cap at 20 learners

        return (experience_score + learner_count_score) / 2

    @staticmethod
    def _add_minutes_to_time(t: time, minutes: int) -> time:
        from datetime import datetime, timedelta
        temp = datetime.combine(date.today(), t)
        temp += timedelta(minutes=minutes)
        return temp.time()
