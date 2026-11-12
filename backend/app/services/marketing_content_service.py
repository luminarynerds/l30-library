# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .ollama_service import OllamaService, OllamaError, get_ollama_service

logger = get_logger(__name__)


# Content-type-specific system prompts
SYSTEM_PROMPTS = {
    "social_post": (
        "You are a social media specialist for a public library. "
        "Write engaging, concise social media posts that are warm, inviting, and community-focused. "
        "Include relevant hashtags. Keep posts under 280 characters when possible. "
        "Use an enthusiastic but professional tone. Never use generic filler content."
    ),
    "newsletter": (
        "You are a newsletter writer for a public library. "
        "Write warm, informative newsletter content that keeps the community engaged. "
        "Use a friendly, conversational tone. Structure content with clear sections. "
        "Include calls to action where appropriate."
    ),
    "flyer": (
        "You are a copywriter creating flyer text for a public library. "
        "Write attention-grabbing headlines and concise, compelling body copy. "
        "Include a clear call to action with relevant details (dates, times, location). "
        "Keep text scannable with short paragraphs and bullet points."
    ),
    "program_promo": (
        "You are a marketing specialist promoting library reading programs. "
        "Write enthusiastic, motivating promotional content that encourages participation. "
        "Highlight specific program details like goals, prizes, and age groups. "
        "Make the program sound fun and achievable."
    ),
    "event_promo": (
        "You are an events promoter for a public library. "
        "Write exciting, informative promotional content for library events. "
        "Include key details: what, when, where, who it's for, and why they should attend. "
        "Create a sense of anticipation and community."
    ),
}


async def _get_program_context(db: AsyncSession, program_id: int) -> Optional[dict]:
    try:
        from ..models.reading import ReadingProgram
        result = await db.execute(
            select(ReadingProgram).where(ReadingProgram.id == program_id)
        )
        program = result.scalar_one_or_none()
        if program:
            return {
                "program_name": program.name,
                "program_description": program.description,
                "program_type": program.program_type.value if hasattr(program.program_type, 'value') else str(program.program_type),
                "age_group": program.age_group,
                "start_date": str(program.start_date),
                "end_date": str(program.end_date),
                "reading_goal_type": program.reading_goal_type,
                "reading_goal_value": program.reading_goal_value,
                "is_active": program.is_active,
            }
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch program context: {e}")
    return None


async def _get_event_context(db: AsyncSession, event_id: int) -> Optional[dict]:
    try:
        from ..models.event import Event
        result = await db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            return {
                "event_name": event.title,
                "event_description": event.description,
                "start_time": str(event.start_time) if event.start_time else None,
                "end_time": str(event.end_time) if event.end_time else None,
                "location": event.location,
            }
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch event context: {e}")
    return None


def _build_user_prompt(
    user_instructions: str,
    content_type: str,
    program_context: Optional[dict] = None,
    event_context: Optional[dict] = None,
    tone: Optional[str] = None,
) -> str:
    parts = []

    if tone:
        parts.append(f"Tone: {tone}")

    parts.append(f"Content type: {content_type.replace('_', ' ')}")

    if program_context:
        parts.append(
            f"\nLibrary Program Details:\n"
            f"- Name: {program_context.get('program_name', 'N/A')}\n"
            f"- Description: {program_context.get('program_description', 'N/A')}\n"
            f"- Type: {program_context.get('program_type', 'N/A')}\n"
            f"- Age Group: {program_context.get('age_group', 'All ages')}\n"
            f"- Dates: {program_context.get('start_date', '?')} to {program_context.get('end_date', '?')}\n"
            f"- Goal: Read {program_context.get('reading_goal_value', '?')} {program_context.get('reading_goal_type', 'items')}"
        )

    if event_context:
        parts.append(
            f"\nEvent Details:\n"
            f"- Name: {event_context.get('event_name', 'N/A')}\n"
            f"- Description: {event_context.get('event_description', 'N/A')}\n"
            f"- When: {event_context.get('start_time', 'TBD')}\n"
            f"- Location: {event_context.get('location', 'Library')}"
        )

    parts.append(f"\nInstructions: {user_instructions}")

    return "\n".join(parts)


async def generate_marketing_content(
    db: AsyncSession,
    content_type: str,
    user_instructions: str,
    program_id: Optional[int] = None,
    event_id: Optional[int] = None,
    tone: Optional[str] = None,
    temperature: float = 0.7,
) -> dict:
    ollama = get_ollama_service()

    # Check availability
    available = await ollama.is_available()
    if not available:
        raise OllamaError("AI service is not available. Please check that Ollama is running.")

    # Gather context
    program_context = None
    event_context = None
    if program_id:
        program_context = await _get_program_context(db, program_id)
    if event_id:
        event_context = await _get_event_context(db, event_id)

    # Build prompts
    system_prompt = SYSTEM_PROMPTS.get(content_type, SYSTEM_PROMPTS["social_post"])
    full_prompt = _build_user_prompt(
        user_instructions=user_instructions,
        content_type=content_type,
        program_context=program_context,
        event_context=event_context,
        tone=tone,
    )

    # Generate
    result = await ollama.generate(
        prompt=full_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=2000,
    )

    context_data = {}
    if program_context:
        context_data["program"] = program_context
    if event_context:
        context_data["event"] = event_context

    return {
        "generated_text": result["response"],
        "system_prompt": system_prompt,
        "full_prompt": full_prompt,
        "context_data": context_data or None,
        "model": result["model"],
        "generation_time_ms": result["generation_time_ms"],
    }
