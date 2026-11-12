# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_batching import (
    BatchProcessingSession,
    BatchSuggestReason,
    TaskBatchSuggestion,
    TaskBatchType,
    TaskPriorityLevel,
)
from app.core.datetime_utils import utc_now, ensure_utc


class TaskBatchingService:

    @staticmethod
    async def get_active_suggestions(
        db: AsyncSession,
        organization_id: int,
        batch_type: Optional[TaskBatchType] = None,
    ) -> List[TaskBatchSuggestion]:
        query = select(TaskBatchSuggestion).where(
            and_(
                TaskBatchSuggestion.organization_id == organization_id,
                TaskBatchSuggestion.is_active == True,
                TaskBatchSuggestion.is_dismissed == False,
            )
        )

        if batch_type:
            query = query.where(TaskBatchSuggestion.batch_type == batch_type)

        query = query.order_by(
            TaskBatchSuggestion.drop_everything.desc(),
            TaskBatchSuggestion.priority_level.asc(),
            TaskBatchSuggestion.deadline_at.asc().nullslast(),
            TaskBatchSuggestion.confidence_score.desc(),
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def analyze_and_generate_suggestions(
        db: AsyncSession,
        organization_id: int,
        staff_id: Optional[int] = None,
    ) -> List[TaskBatchSuggestion]:
        suggestions = []

        # Example suggestion generation (simplified)
        # In production, query actual data to determine volumes

        # Example: Print hold slips suggestion
        hold_count = 5  # In production: query actual holds
        if hold_count >= 5:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.PRINT_HOLD_SLIPS,
                title=f"{hold_count} hold slips to print - do them all now?",
                description=(
                    f"Group these {hold_count} print jobs into one focused block to reduce context-switching "
                    "exhaustion and keep the desk flow smoother."
                ),
                reason=BatchSuggestReason.VOLUME_THRESHOLD,
                confidence_score=0.85,
                task_count=hold_count,
                estimated_time_minutes=10,
                estimated_savings_minutes=5,
                location_hint="Circulation desk printer",
                timing_hint="Best during a quiet window (before open, mid-afternoon lull, or just after rush)",
                prerequisites={"printer_access": True, "hold_list_updated": True},
                priority_level=TaskPriorityLevel.HIGH,
                deadline_at=(utc_now() + timedelta(hours=6)).replace(tzinfo=None),  # naive column
                protected_time_recommended=True,
                distraction_deflection_script="I'm in a priority print batch right now; I can help after this block ends.",
                created_by_id=staff_id,
                expires_at=(utc_now() + timedelta(hours=4)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        # Example: Batch checkins suggestion
        checkin_count = 25  # In production: query actual returns
        if checkin_count >= 20:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.BATCH_CHECKINS,
                title=f"Batch process {checkin_count} returns",
                description=f"Process all {checkin_count} returned items in one batch to streamline shelving and holds checking.",
                reason=BatchSuggestReason.TIME_EFFICIENCY,
                confidence_score=0.90,
                task_count=checkin_count,
                estimated_time_minutes=15,
                estimated_savings_minutes=8,
                location_hint="Returns cart near circulation desk",
                timing_hint="Run in batch mode right after large return drops or after morning rush",
                prerequisites={"returns_sorted": True, "batch_processing_mode": True},
                priority_level=TaskPriorityLevel.CRITICAL,
                drop_everything=True,
                conflict_resolution_note="Returns with patron waits outrank all other active batches.",
                deadline_at=(utc_now() + timedelta(hours=2)).replace(tzinfo=None),  # naive column
                created_by_id=staff_id,
                extra_data={"mode": "batch_checkin", "goal": "fewer interruptions"},
                expires_at=(utc_now() + timedelta(hours=3)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        # Example: Process card applications
        card_count = 3  # In production: query actual applications
        if card_count >= 3:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.PROCESS_CARDS,
                title=f"{card_count} patrons need cards - batch process?",
                description=(
                    f"Handle these {card_count} card applications back-to-back so ID checks and printer setup happen once, "
                    "not repeatedly."
                ),
                reason=BatchSuggestReason.CONTEXT_SIMILARITY,
                confidence_score=0.80,
                task_count=card_count,
                estimated_time_minutes=20,
                estimated_savings_minutes=10,
                location_hint="Staff workstation with card printer",
                timing_hint="Best during scheduled admin time when interruptions are lower",
                prerequisites={"id_scanner_available": True, "card_stock_sufficient": True},
                priority_level=TaskPriorityLevel.MEDIUM,
                can_wait_until=(utc_now() + timedelta(hours=8)).replace(tzinfo=None),  # naive column
                created_by_id=staff_id,
                expires_at=(utc_now() + timedelta(hours=6)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        # Example: Consolidate notifications
        notification_count = 12  # In production: query pending notifications
        if notification_count >= 8:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.CONSOLIDATE_NOTIFICATIONS,
                title=f"Consolidate {notification_count} staff notifications into one review pass",
                description=(
                    "Review alerts in one sweep and clear low-priority items together to reduce notification fatigue."
                ),
                reason=BatchSuggestReason.TIME_EFFICIENCY,
                confidence_score=0.82,
                task_count=notification_count,
                estimated_time_minutes=12,
                estimated_savings_minutes=6,
                location_hint="Staff dashboard",
                timing_hint="Best at the top of each hour instead of constant interruption",
                prerequisites={"notification_filters_enabled": True},
                created_by_id=staff_id,
                expires_at=(utc_now() + timedelta(hours=2)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        # Example: Group phone calls to return
        callback_count = 6  # In production: query callback queue
        if callback_count >= 4:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.RETURN_PHONE_CALLS,
                title=f"Return {callback_count} patron calls in one block",
                description="Group callbacks together while records are open and scripts are fresh.",
                reason=BatchSuggestReason.CONTEXT_SIMILARITY,
                confidence_score=0.79,
                task_count=callback_count,
                estimated_time_minutes=18,
                estimated_savings_minutes=7,
                location_hint="Quiet staff phone station",
                timing_hint="Best in late morning or early evening when patrons are easier to reach",
                prerequisites={"callback_list_ready": True},
                created_by_id=staff_id,
                expires_at=(utc_now() + timedelta(hours=3)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        # Example: Batch email responses
        email_count = 9  # In production: query shared inbox
        if email_count >= 6:
            suggestion = TaskBatchSuggestion(
                organization_id=organization_id,
                batch_type=TaskBatchType.BATCH_EMAIL_RESPONSES,
                title=f"Batch {email_count} email replies",
                description=(
                    "Answer similar patron emails in a single response block to keep tone and policy language consistent."
                ),
                reason=BatchSuggestReason.CONTEXT_SIMILARITY,
                confidence_score=0.84,
                task_count=email_count,
                estimated_time_minutes=22,
                estimated_savings_minutes=9,
                location_hint="Shared inbox workstation",
                timing_hint="Best after lunch when message volume stabilizes",
                prerequisites={"saved_replies_available": True},
                created_by_id=staff_id,
                expires_at=(utc_now() + timedelta(hours=4)).replace(tzinfo=None),  # naive column
            )
            db.add(suggestion)
            suggestions.append(suggestion)

        await db.commit()
        return suggestions

    @staticmethod
    async def get_daily_priority_snapshot(
        db: AsyncSession,
        organization_id: int,
        limit: int = 3,
    ) -> dict:
        suggestions = await TaskBatchingService.get_active_suggestions(
            db=db,
            organization_id=organization_id,
        )

        now = utc_now()
        # can_wait_until/deadline_at are naive (UTC-implied) columns; compare
        # against a naive "now" to avoid aware-vs-naive TypeError.
        now_naive = now.replace(tzinfo=None)
        actionable = [
            s for s in suggestions
            if not s.can_wait_until or s.can_wait_until <= now_naive
        ]
        top_items = actionable[:limit]

        conflicts = []
        urgent = [s for s in actionable if s.drop_everything]
        if len(urgent) > 1:
            conflicts.append(
                "Multiple drop-everything items detected. Resolve by nearest deadline, then highest confidence."
            )

        same_deadline = [s for s in actionable if s.deadline_at]
        same_deadline.sort(key=lambda s: s.deadline_at)
        if len(same_deadline) > 1 and same_deadline[0].deadline_at == same_deadline[1].deadline_at:
            conflicts.append(
                "Conflicting priorities share the same deadline. Use manager note/conflict resolution guidance."
            )

        return {
            "generated_at": now,
            "most_important": top_items,
            "conflicts": conflicts,
        }

    @staticmethod
    async def accept_suggestion(
        db: AsyncSession,
        suggestion_id: int,
        staff_id: int,
    ) -> TaskBatchSuggestion:
        result = await db.execute(
            select(TaskBatchSuggestion).where(TaskBatchSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise ValueError("Suggestion not found")

        suggestion.is_accepted = True
        suggestion.accepted_at = utc_now().replace(tzinfo=None)  # naive column
        suggestion.accepted_by_id = staff_id

        await db.commit()
        await db.refresh(suggestion)
        return suggestion

    @staticmethod
    async def dismiss_suggestion(
        db: AsyncSession,
        suggestion_id: int,
        reason: Optional[str] = None,
    ) -> TaskBatchSuggestion:
        result = await db.execute(
            select(TaskBatchSuggestion).where(TaskBatchSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise ValueError("Suggestion not found")

        suggestion.is_active = False
        suggestion.is_dismissed = True
        suggestion.dismissed_at = utc_now().replace(tzinfo=None)  # naive column
        suggestion.dismissed_reason = reason

        await db.commit()
        await db.refresh(suggestion)
        return suggestion

    @staticmethod
    async def create_session(
        db: AsyncSession,
        suggestion_id: int,
        staff_id: int,
    ) -> BatchProcessingSession:
        # Get the suggestion
        result = await db.execute(
            select(TaskBatchSuggestion).where(TaskBatchSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise ValueError("Suggestion not found")

        # Create session
        session = BatchProcessingSession(
            organization_id=suggestion.organization_id,
            suggestion_id=suggestion.id,
            staff_id=staff_id,
            batch_type=suggestion.batch_type,
            started_at=utc_now(),
            estimated_time_minutes=suggestion.estimated_time_minutes,
            tasks_attempted=suggestion.task_count,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def complete_session(
        db: AsyncSession,
        session_id: int,
        tasks_completed: int,
        quality_rating: Optional[int] = None,
        efficiency_rating: Optional[int] = None,
        would_batch_again: Optional[bool] = None,
        staff_notes: Optional[str] = None,
        interruptions_count: int = 0,
    ) -> BatchProcessingSession:
        result = await db.execute(
            select(BatchProcessingSession).where(BatchProcessingSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError("Session not found")

        # Calculate metrics
        session.completed_at = utc_now().replace(tzinfo=None)  # naive column
        session.is_complete = True
        session.tasks_completed = tasks_completed

        if session.started_at:
            # completed_at column is naive DateTime; started_at is DateTime(timezone=True).
            # Mixing the two raises TypeError in Postgres on first non-NULL completion.
            # Normalize both to tz-aware UTC at compute time so the subtraction is safe
            # regardless of how the driver materializes the columns.
            duration = (ensure_utc(session.completed_at) - ensure_utc(session.started_at)).total_seconds() / 60
            session.actual_duration_minutes = int(duration)

            if session.estimated_time_minutes:
                session.time_saved_minutes = session.estimated_time_minutes - session.actual_duration_minutes

        if session.tasks_attempted and session.tasks_attempted > 0:
            session.completion_rate = tasks_completed / session.tasks_attempted

        # Store feedback
        session.quality_rating = quality_rating
        session.efficiency_rating = efficiency_rating
        session.would_batch_again = would_batch_again
        session.staff_notes = staff_notes
        session.interruptions_count = interruptions_count

        # Track priority completion progress at suggestion level
        suggestion_result = await db.execute(
            select(TaskBatchSuggestion).where(TaskBatchSuggestion.id == session.suggestion_id)
        )
        suggestion = suggestion_result.scalar_one_or_none()
        if suggestion:
            suggestion.completed_tasks_count = (suggestion.completed_tasks_count or 0) + tasks_completed
            if suggestion.completed_tasks_count >= suggestion.task_count:
                suggestion.priority_completed_at = utc_now().replace(tzinfo=None)  # naive column

        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: int,
    ) -> Optional[BatchProcessingSession]:
        result = await db.execute(
            select(BatchProcessingSession).where(BatchProcessingSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_staff_sessions(
        db: AsyncSession,
        staff_id: int,
        limit: int = 10,
    ) -> List[BatchProcessingSession]:
        query = (
            select(BatchProcessingSession)
            .where(BatchProcessingSession.staff_id == staff_id)
            .order_by(BatchProcessingSession.started_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        return result.scalars().all()
