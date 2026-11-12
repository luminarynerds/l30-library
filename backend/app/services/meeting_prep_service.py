# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import AgendaItem, BoardMeeting, BoardMeetingBrief
from app.schemas.meeting_prep import MeetingPrepPacket
from app.core.cache_strategies import CacheTTL
from app.services.ollama_service import OllamaError, get_ollama_service

logger = get_logger(__name__)


class MeetingPrepService:

    def __init__(self, db: AsyncSession = None):
        self.db = db

    @staticmethod
    async def compile_prep_packet(
        meeting_id: int, db: AsyncSession = None
    ) -> Optional[MeetingPrepPacket]:
        if db is None:
            return None

        from app.models.board import (
            BoardMeeting, AgendaItem, BoardMotion, MeetingActionItem, BoardMinutes
        )

        # Fetch meeting
        result = await db.execute(
            select(BoardMeeting).where(BoardMeeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return None

        # Fetch agenda items
        agenda_result = await db.execute(
            select(AgendaItem)
            .where(AgendaItem.meeting_id == meeting_id)
            .order_by(AgendaItem.sort_order)
        )
        agenda_items = agenda_result.scalars().all()

        # Fetch pending motions for this meeting
        motions_result = await db.execute(
            select(BoardMotion)
            .where(BoardMotion.meeting_id == meeting_id)
        )
        motions = motions_result.scalars().all()

        # Fetch open action items from previous meetings
        action_result = await db.execute(
            select(MeetingActionItem)
            .where(MeetingActionItem.status.in_([open, in_progress]))
            .order_by(MeetingActionItem.due_date)
            .limit(20)
        )
        action_items = action_result.scalars().all()

        # Fetch most recent approved minutes
        prev_minutes_result = await db.execute(
            select(BoardMinutes)
            .where(BoardMinutes.approved == True)
            .order_by(BoardMinutes.created_at.desc())
            .limit(1)
        )
        prev_minutes = prev_minutes_result.scalar_one_or_none()

        from app.schemas.meeting_prep import (
            PrepAgendaItem, PrepMotionItem, PrepActionItem, PrepPreviousMinutes
        )

        prep_agenda = [
            PrepAgendaItem(
                id=a.id,
                title=a.title,
                description=a.description,
                duration_minutes=getattr(a, 'estimated_duration', None),
                order=a.sort_order or 0,
            )
            for a in agenda_items
        ]

        prep_motions = [
            PrepMotionItem(
                id=m.id,
                title=m.title,
                description=m.motion_text,
                status=m.status,
                proposed_by=None,
                requires_vote=m.status in (seconded, under_discussion, called_to_vote),
            )
            for m in motions
        ]

        prep_actions = [
            PrepActionItem(
                id=ai.id,
                description=ai.description or ai.title,
                assigned_to=None,
                due_date=ai.due_date,
                status=ai.status,
            )
            for ai in action_items
        ]

        prep_prev = None
        if prev_minutes:
            prep_prev = PrepPreviousMinutes(
                meeting_id=prev_minutes.meeting_id,
                meeting_date=prev_minutes.created_at,
                summary=prev_minutes.plain_language_summary,
                key_decisions=[],
            )

        return MeetingPrepPacket(
            meeting_id=meeting_id,
            meeting_title=meeting.title,
            meeting_date=meeting.scheduled_date,
            location=meeting.location,
            agenda_items=prep_agenda,
            pending_motions=prep_motions,
            open_action_items=prep_actions,
            financial_snapshot=None,
            compliance_items=[],
            previous_minutes=prep_prev,
            generated_at=datetime.now(timezone.utc),
        )

    async def generate_brief(self, meeting_id: int, user_id: int) -> BoardMeetingBrief:
        db = self.db

        # Fetch meeting with agenda items
        result = await db.execute(
            select(BoardMeeting).where(BoardMeeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        agenda_result = await db.execute(
            select(AgendaItem)
            .where(AgendaItem.meeting_id == meeting_id)
            .order_by(AgendaItem.sort_order)
        )
        agenda_items = agenda_result.scalars().all()

        # Check for existing brief -- update instead of creating duplicate
        existing_result = await db.execute(
            select(BoardMeetingBrief).where(BoardMeetingBrief.meeting_id == meeting_id)
        )
        existing_brief = existing_result.scalar_one_or_none()

        if existing_brief:
            brief = existing_brief
            brief.status = "generating"
            brief.executive_summary = ""
            brief.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(brief)
        else:
            brief = BoardMeetingBrief(
                meeting_id=meeting_id,
                status="generating",
                executive_summary="",
                created_by_id=user_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(brief)
            await db.commit()
            await db.refresh(brief)

        # Build prompt for Ollama
        agenda_text = ""
        if agenda_items:
            for i, item in enumerate(agenda_items, 1):
                desc = f" - {item.description}" if item.description else ""
                agenda_text += f"{i}. {item.title}{desc}\n"
        else:
            agenda_text = "No agenda items listed yet."

        scheduled = meeting.scheduled_date.strftime("%B %d, %Y") if meeting.scheduled_date else "TBD"
        location = meeting.location or "TBD"

        prompt = f"""You are a helpful assistant preparing a board meeting brief for library board members.

Meeting: {meeting.title}
Type: {meeting.meeting_type}
Date: {scheduled}
Location: {location}
Description: {meeting.description or 'No description provided.'}

Agenda Items:
{agenda_text}

Please provide a JSON response with these exact keys:
{{
  "executive_summary": "A concise 2-3 paragraph executive summary of what this meeting will cover and what board members should know",
  "agenda_highlights": ["highlight 1", "highlight 2", "highlight 3"],
  "recommended_prep": ["preparation item 1", "preparation item 2", "preparation item 3"],
  "background_context": "Relevant background context that would help board members prepare"
}}

Respond ONLY with valid JSON, no other text."""

        response_text = None
        ollama_result = None
        try:
            ollama = get_ollama_service()
            ollama_result = await ollama.generate(
                prompt=prompt,
                system_prompt="You are a professional board meeting analyst. Always respond with valid JSON only.",
                temperature=0.5,
                cache_ttl=CacheTTL.LONG,
            )

            response_text = ollama_result["response"]

            # Parse JSON from the response - strip markdown code fences if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.index("\n")
                cleaned = cleaned[first_newline + 1:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

            parsed = json.loads(cleaned)

            brief.executive_summary = parsed.get("executive_summary", "Brief generated successfully.")
            brief.agenda_highlights = parsed.get("agenda_highlights", [])
            brief.recommended_prep = parsed.get("recommended_prep", [])
            brief.background_context = parsed.get("background_context", "")
            brief.ai_model_used = ollama_result.get("model", "unknown")
            brief.generation_time_ms = ollama_result.get("generation_time_ms", 0)
            brief.prompt_tokens = ollama_result.get("prompt_tokens", 0)
            brief.completion_tokens = ollama_result.get("completion_tokens", 0)
            brief.status = "completed"
            brief.generated_at = datetime.now(timezone.utc)
            brief.updated_at = datetime.now(timezone.utc)

        except OllamaError as e:
            logger.error(f"Ollama error generating brief for meeting {meeting_id}: {e}")
            brief.status = "failed"
            brief.error_message = str(e)
            brief.updated_at = datetime.now(timezone.utc)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Ollama response for meeting {meeting_id}: {e}")
            # Use raw response as summary if JSON parsing fails
            brief.executive_summary = response_text or "Generation completed but response could not be parsed."
            brief.status = "completed"
            brief.generated_at = datetime.now(timezone.utc)
            brief.ai_model_used = ollama_result.get("model", "unknown") if ollama_result else "unknown"
            brief.updated_at = datetime.now(timezone.utc)
        except Exception as e:  # noqa: BLE001 -- LLM generation boundary: any failure marks brief as failed for retry, never crash route
            logger.error(f"Unexpected error generating brief for meeting {meeting_id}: {e}")
            brief.status = "failed"
            brief.error_message = f"Unexpected error: {str(e)}"
            brief.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(brief)
        return brief

    async def get_brief(self, meeting_id: int) -> Optional[BoardMeetingBrief]:
        result = await self.db.execute(
            select(BoardMeetingBrief).where(
                BoardMeetingBrief.meeting_id == meeting_id
            )
        )
        return result.scalar_one_or_none()

    async def get_meeting_checklist(self, meeting_id: int):
        return {"meeting_id": meeting_id, "items": []}


def get_meeting_prep_service(db=None) -> MeetingPrepService:
    return MeetingPrepService(db=db)
