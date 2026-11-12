# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session

from app.models.perfectionism_antidotes import (
    PerfectionismAntidote, UserAntidote, CoachingSession, ProgressMilestone,
    DailyReminder, ManagerCoachingModel, AntidoteType, SessionStatus, AdoptionStatus
)
from app.models.user import User


class PerfectionismAntidotesService:

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # ANTIDOTE MANAGEMENT
    # ========================================================================

    def get_all_antidotes(self, include_inactive: bool = False) -> List[Dict]:
        query = self.db.query(PerfectionismAntidote)

        if not include_inactive:
            query = query.filter(PerfectionismAntidote.is_active == True)

        antidotes = query.order_by(PerfectionismAntidote.sort_order).all()

        return [self._antidote_to_dict(a) for a in antidotes]

    def get_antidote_by_type(self, antidote_type: AntidoteType) -> Optional[Dict]:
        antidote = self.db.query(PerfectionismAntidote).filter(
            PerfectionismAntidote.antidote_type == antidote_type
        ).first()

        return self._antidote_to_dict(antidote) if antidote else None

    async def create_antidote(self, antidote_type: AntidoteType, title: str, reminder_text: str,
                       description: str = None, advice: str = None, example: str = None) -> Dict:
        # Check if already exists
        existing = self.db.query(PerfectionismAntidote).filter(
            PerfectionismAntidote.antidote_type == antidote_type
        ).first()

        if existing:
            raise ValueError(f"Antidote type {antidote_type} already exists")

        antidote = PerfectionismAntidote(
            antidote_type=antidote_type,
            title=title,
            reminder_text=reminder_text,
            description=description,
            advice=advice,
            example_scenario=example
        )
        self.db.add(antidote)
        await self.db.commit()
        await self.db.refresh(antidote)

        return self._antidote_to_dict(antidote)

    # ========================================================================
    # USER ANTIDOTE TRACKING
    # ========================================================================

    def get_user_antidotes(self, user_id: int) -> List[Dict]:
        user_antidotes = self.db.query(UserAntidote).filter(
            UserAntidote.user_id == user_id
        ).all()

        result = []
        for ua in user_antidotes:
            antidote_dict = self._antidote_to_dict(ua.antidote)
            antidote_dict.update({
                "user_adoption_id": ua.id,
                "adoption_status": str(ua.adoption_status),
                "confidence_level": ua.confidence_level,
                "reminder_count": ua.reminder_count,
                "times_acknowledged": ua.times_acknowledged,
                "times_applied": ua.times_applied,
                "is_favorite": ua.is_favorite,
                "last_reminder_at": ua.last_reminder_at.isoformat() if ua.last_reminder_at else None,
            })
            result.append(antidote_dict)

        return result

    async def track_antidote_application(self, user_id: int, antidote_id: int,
                                  action: str = "acknowledged") -> Dict:
        user_antidote = self.db.query(UserAntidote).filter(
            and_(
                UserAntidote.user_id == user_id,
                UserAntidote.antidote_id == antidote_id
            )
        ).first()

        if not user_antidote:
            # Create tracking record
            user_antidote = UserAntidote(
                user_id=user_id,
                antidote_id=antidote_id,
                adoption_status=AdoptionStatus.DISCOVERING
            )
            self.db.add(user_antidote)

        if action == "acknowledged":
            user_antidote.times_acknowledged += 1
            user_antidote.last_reminder_at = datetime.now(timezone.utc)
            # Increase confidence slightly
            user_antidote.confidence_level = min(1.0, user_antidote.confidence_level + 0.05)
        elif action == "applied":
            user_antidote.times_applied += 1
            user_antidote.confidence_level = min(1.0, user_antidote.confidence_level + 0.10)
            # Update adoption status based on usage
            if user_antidote.times_applied >= 5:
                user_antidote.adoption_status = AdoptionStatus.ADOPTED
            elif user_antidote.times_applied >= 2:
                user_antidote.adoption_status = AdoptionStatus.TRYING

        await self.db.commit()
        await self.db.refresh(user_antidote)

        return {
            "user_adoption_id": user_antidote.id,
            "times_acknowledged": user_antidote.times_acknowledged,
            "times_applied": user_antidote.times_applied,
            "confidence_level": user_antidote.confidence_level,
            "adoption_status": str(user_antidote.adoption_status)
        }

    async def mark_favorite(self, user_id: int, antidote_id: int, is_favorite: bool = True) -> Dict:
        user_antidote = self.db.query(UserAntidote).filter(
            and_(
                UserAntidote.user_id == user_id,
                UserAntidote.antidote_id == antidote_id
            )
        ).first()

        if not user_antidote:
            user_antidote = UserAntidote(
                user_id=user_id,
                antidote_id=antidote_id
            )
            self.db.add(user_antidote)

        user_antidote.is_favorite = is_favorite
        await self.db.commit()
        await self.db.refresh(user_antidote)

        return {"is_favorite": user_antidote.is_favorite}

    # ========================================================================
    # COACHING SESSIONS
    # ========================================================================

    async def create_coaching_session(self, user_id: int, topic: str, challenge: str,
                               coach_id: int = None, antidote_id: int = None) -> Dict:
        session = CoachingSession(
            user_id=user_id,
            coach_id=coach_id,
            antidote_id=antidote_id,
            topic=topic,
            challenge_description=challenge,
            session_status=SessionStatus.SCHEDULED,
            scheduled_at=datetime.now(timezone.utc)
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return self._session_to_dict(session)

    def get_user_coaching_sessions(self, user_id: int, status: str = None) -> List[Dict]:
        query = self.db.query(CoachingSession).filter(
            CoachingSession.user_id == user_id
        )

        if status:
            query = query.filter(CoachingSession.session_status == SessionStatus[status.upper()])

        sessions = query.order_by(desc(CoachingSession.scheduled_at)).all()
        return [self._session_to_dict(s) for s in sessions]

    async def update_coaching_session(self, session_id: int, updates: Dict) -> Dict:
        session = self.db.query(CoachingSession).filter(
            CoachingSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        if "status" in updates:
            session.session_status = SessionStatus[updates["status"].upper()]
        if "started_at" in updates:
            session.started_at = updates["started_at"]
        if "completed_at" in updates:
            session.completed_at = updates["completed_at"]
        if "coaching_notes" in updates:
            session.coaching_notes = updates["coaching_notes"]
        if "action_plan" in updates:
            session.action_plan = updates["action_plan"]
        if "confidence_increase" in updates:
            session.confidence_increase = updates["confidence_increase"]
        if "progress_made" in updates:
            session.progress_made = updates["progress_made"]

        await self.db.commit()
        await self.db.refresh(session)

        return self._session_to_dict(session)

    # ========================================================================
    # PROGRESS MILESTONES
    # ========================================================================

    async def create_milestone(self, user_id: int, title: str, what_happened: str,
                        milestone_type: str, what_learned: str = None,
                        how_felt: str = None) -> Dict:
        milestone = ProgressMilestone(
            user_id=user_id,
            title=title,
            description=f"User achieved: {title}",
            milestone_type=milestone_type,
            what_happened=what_happened,
            what_learned=what_learned,
            how_felt=how_felt
        )
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)

        return self._milestone_to_dict(milestone)

    def get_user_milestones(self, user_id: int, only_celebrated: bool = False) -> List[Dict]:
        query = self.db.query(ProgressMilestone).filter(
            ProgressMilestone.user_id == user_id
        )

        if only_celebrated:
            query = query.filter(ProgressMilestone.is_celebrated == True)

        milestones = query.order_by(desc(ProgressMilestone.created_at)).all()
        return [self._milestone_to_dict(m) for m in milestones]

    async def celebrate_milestone(self, milestone_id: int) -> Dict:
        milestone = self.db.query(ProgressMilestone).filter(
            ProgressMilestone.id == milestone_id
        ).first()

        if not milestone:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone.is_celebrated = True
        milestone.celebration_date = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(milestone)

        return self._milestone_to_dict(milestone)

    # ========================================================================
    # DAILY REMINDERS
    # ========================================================================

    async def send_daily_reminder(self, user_id: int, antidote_id: int, reminder_text: str) -> Dict:
        reminder = DailyReminder(
            user_id=user_id,
            antidote_id=antidote_id,
            reminder_text=reminder_text,
            reminder_date=datetime.now(timezone.utc)
        )
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)

        return self._reminder_to_dict(reminder)

    def get_pending_reminders(self, user_id: int) -> List[Dict]:
        reminders = self.db.query(DailyReminder).filter(
            and_(
                DailyReminder.user_id == user_id,
                DailyReminder.was_acknowledged == False
            )
        ).order_by(desc(DailyReminder.created_at)).all()

        return [self._reminder_to_dict(r) for r in reminders]

    async def acknowledge_reminder(self, reminder_id: int, reflection: str = None) -> Dict:
        reminder = self.db.query(DailyReminder).filter(
            DailyReminder.id == reminder_id
        ).first()

        if not reminder:
            raise ValueError(f"Reminder {reminder_id} not found")

        reminder.was_acknowledged = True
        reminder.acknowledged_at = datetime.now(timezone.utc)
        reminder.user_reflection = reflection

        await self.db.commit()
        await self.db.refresh(reminder)

        return self._reminder_to_dict(reminder)

    # ========================================================================
    # MANAGER COACHING MODEL
    # ========================================================================

    async def create_manager_model(self, manager_id: int, commitment: str = None,
                           boundaries: str = None, mistake_sharing: str = None,
                           grace_examples: str = None) -> Dict:
        model = ManagerCoachingModel(
            manager_id=manager_id,
            personal_commitment=commitment,
            visible_boundaries=boundaries,
            mistake_sharing=mistake_sharing,
            grace_examples=grace_examples
        )
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)

        return self._manager_model_to_dict(model)

    def get_manager_model(self, manager_id: int) -> Optional[Dict]:
        model = self.db.query(ManagerCoachingModel).filter(
            ManagerCoachingModel.manager_id == manager_id
        ).first()

        return self._manager_model_to_dict(model) if model else None

    async def update_manager_model(self, manager_id: int, updates: Dict) -> Dict:
        model = self.db.query(ManagerCoachingModel).filter(
            ManagerCoachingModel.manager_id == manager_id
        ).first()

        if not model:
            return await self.create_manager_model(manager_id, **updates)

        if "personal_commitment" in updates:
            model.personal_commitment = updates["personal_commitment"]
        if "visible_boundaries" in updates:
            model.visible_boundaries = updates["visible_boundaries"]
        if "mistake_sharing" in updates:
            model.mistake_sharing = updates["mistake_sharing"]
        if "grace_examples" in updates:
            model.grace_examples = updates["grace_examples"]
        if "team_feedback" in updates:
            model.team_feedback = updates["team_feedback"]
        if "observed_improvements" in updates:
            model.observed_improvements = updates["observed_improvements"]

        await self.db.commit()
        await self.db.refresh(model)

        return self._manager_model_to_dict(model)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _antidote_to_dict(self, antidote: PerfectionismAntidote) -> Dict:
        if not antidote:
            return None

        return {
            "id": antidote.id,
            "type": str(antidote.antidote_type),
            "title": antidote.title,
            "description": antidote.description,
            "reminder_text": antidote.reminder_text,
            "advice": antidote.advice,
            "example_scenario": antidote.example_scenario,
            "time_limit_minutes": antidote.time_limit_minutes,
            "priority_score": antidote.priority_score,
            "is_active": antidote.is_active,
            "icon_name": antidote.icon_name,
            "color_code": antidote.color_code,
            "created_at": antidote.created_at.isoformat() if antidote.created_at else None,
        }

    def _session_to_dict(self, session: CoachingSession) -> Dict:
        if not session:
            return None

        return {
            "id": session.id,
            "user_id": session.user_id,
            "coach_id": session.coach_id,
            "antidote_id": session.antidote_id,
            "topic": session.topic,
            "challenge_description": session.challenge_description,
            "coaching_notes": session.coaching_notes,
            "action_plan": session.action_plan,
            "status": str(session.session_status),
            "progress_made": session.progress_made,
            "confidence_increase": session.confidence_increase,
            "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "duration_minutes": session.duration_minutes,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }

    def _milestone_to_dict(self, milestone: ProgressMilestone) -> Dict:
        if not milestone:
            return None

        return {
            "id": milestone.id,
            "user_id": milestone.user_id,
            "title": milestone.title,
            "description": milestone.description,
            "type": milestone.milestone_type,
            "what_happened": milestone.what_happened,
            "what_learned": milestone.what_learned,
            "how_felt": milestone.how_felt,
            "is_celebrated": milestone.is_celebrated,
            "celebration_date": milestone.celebration_date.isoformat() if milestone.celebration_date else None,
            "created_at": milestone.created_at.isoformat() if milestone.created_at else None,
        }

    def _reminder_to_dict(self, reminder: DailyReminder) -> Dict:
        if not reminder:
            return None

        return {
            "id": reminder.id,
            "user_id": reminder.user_id,
            "antidote_id": reminder.antidote_id,
            "reminder_text": reminder.reminder_text,
            "reminder_date": reminder.reminder_date.isoformat() if reminder.reminder_date else None,
            "was_acknowledged": reminder.was_acknowledged,
            "acknowledged_at": reminder.acknowledged_at.isoformat() if reminder.acknowledged_at else None,
            "user_reflection": reminder.user_reflection,
            "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
        }

    def _manager_model_to_dict(self, model: ManagerCoachingModel) -> Dict:
        if not model:
            return None

        return {
            "id": model.id,
            "manager_id": model.manager_id,
            "personal_commitment": model.personal_commitment,
            "visible_boundaries": model.visible_boundaries,
            "mistake_sharing": model.mistake_sharing,
            "grace_examples": model.grace_examples,
            "team_feedback": model.team_feedback,
            "observed_improvements": model.observed_improvements,
            "created_at": model.created_at.isoformat() if model.created_at else None,
        }
