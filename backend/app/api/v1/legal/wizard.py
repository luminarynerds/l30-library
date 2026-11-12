# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for the form finder wizard.

This module implements the form finder wizard which uses a state machine
approach to guide users through a series of questions and recommend
appropriate legal forms, packets, and guides.

State Machine Design:
- Sessions are tracked by a unique session_token
- Each session progresses through a sequence of questions
- Answers determine which question comes next (branching logic)
- The wizard tracks progress and can calculate completion percentage
- Users can request human help at any point
- Upon completion, the wizard recommends forms, packets, and guides
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    FormFinderWizardStart, FormFinderWizardResponse,
    FormFinderAnswerSubmit, FormFinderResultsResponse,
    FormFinderQuestionResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional

router = APIRouter(prefix="/legal", tags=["legal-forms"])


# ============================================================================
# Wizard State Machine Constants
# ============================================================================

# Typical number of questions in a wizard session, used for progress estimation
TYPICAL_QUESTION_COUNT = 5


# ============================================================================
# Wizard Session Management
# ============================================================================

@router.post("/wizard/start", response_model=FormFinderWizardResponse)
async def start_wizard(
    start_data: Optional[FormFinderWizardStart] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Start a form finder wizard session.

    The wizard asks plain language questions to help determine
    which forms and packets you need.
    """
    patron_id = None
    if start_data and start_data.patron_id:
        patron_id = start_data.patron_id
    elif current_user:
        patron_id = current_user.id

    session = await legal_service.start_wizard_session(db, patron_id=patron_id)
    first_question = await legal_service.get_first_wizard_question(db)

    return {
        "session_token": session.session_token,
        "current_step": first_question.slug if first_question else None,
        "status": session.status,
        "next_question": _question_to_response(first_question) if first_question else None,
        "progress_percentage": 0
    }


# ============================================================================
# Wizard Answer Processing
# ============================================================================

@router.post("/wizard/{session_token}/answer", response_model=FormFinderWizardResponse)
async def submit_wizard_answer(
    session_token: str,
    answer_data: FormFinderAnswerSubmit,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit an answer to a wizard question.

    The state machine processes the answer and determines the next question
    based on the answer value and the current session state.
    """
    session = await legal_service.submit_wizard_answer(
        db, session_token, answer_data.question_slug, answer_data.answer
    )

    next_question = None
    if session.current_step:
        next_question = await legal_service.get_wizard_question(db, session.current_step)

    return {
        "session_token": session.session_token,
        "current_step": session.current_step,
        "status": session.status,
        "next_question": _question_to_response(next_question) if next_question else None,
        "progress_percentage": _calculate_wizard_progress(session)
    }


# ============================================================================
# Wizard Completion and Results
# ============================================================================

@router.post("/wizard/{session_token}/complete", response_model=FormFinderResultsResponse)
async def complete_wizard(
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete the wizard and get recommendations.

    Returns recommended forms, packets, and guides based on your answers.
    The recommendation engine analyzes all answers to match against
    the form database and produces ranked results.
    """
    session = await legal_service.complete_wizard(db, session_token)

    # Get recommended items
    forms = []
    for form_id in session.recommended_form_ids:
        form = await legal_service.get_form_by_id(db, form_id)
        if form:
            forms.append(_form_to_summary(form))

    packets = []
    for packet_id in session.recommended_packet_ids:
        packet = await legal_service.get_packet_by_id(db, packet_id)
        if packet:
            packets.append(_packet_to_summary(packet))

    guides = []
    for guide_id in session.recommended_guide_ids:
        guide = await legal_service.get_guide_by_id(db, guide_id)
        if guide:
            guides.append(_guide_to_summary(guide))

    return {
        "session_token": session.session_token,
        "recommended_forms": forms,
        "recommended_packets": packets,
        "recommended_guides": guides,
        "jurisdiction_state": session.jurisdiction_state,
        "jurisdiction_county": session.jurisdiction_county,
        "court_type_determined": session.court_type_determined,
        "printable_checklist": _generate_checklist(forms, packets)
    }


# ============================================================================
# Wizard Help Referral
# ============================================================================

@router.get("/wizard/{session_token}/progress")
async def get_wizard_progress(
    session_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get progress details for a wizard session.

    Shows:
    - Current progress percentage
    - Questions answered so far
    - Estimated time remaining
    - Current step and next steps
    - Session status
    """
    session = await legal_service.get_wizard_session(db, session_token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate progress
    progress_pct = _calculate_wizard_progress(session)

    # Get current and next question
    current_question = None
    if session.current_step:
        current_question = await legal_service.get_wizard_question(db, session.current_step)

    return {
        "session_token": session_token,
        "status": session.status,
        "progress": {
            "percentage": progress_pct,
            "questions_answered": len(session.answers) if session.answers else 0,
            "estimated_questions_total": TYPICAL_QUESTION_COUNT,
            "estimated_time_minutes": max(1, TYPICAL_QUESTION_COUNT - (progress_pct / 100 * TYPICAL_QUESTION_COUNT))
        },
        "current_question": _question_to_response(current_question),
        "session_info": {
            "started_at": session.started_at,
            "expires_at": session.expires_at,
            "time_elapsed_minutes": (
                (session.completed_at - session.started_at).total_seconds() / 60
                if session.completed_at else
                (datetime.now(timezone.utc) - session.started_at).total_seconds() / 60
            )
        },
        "can_resume": session.status in ["in_progress", "referred"],
        "results_ready": session.status == "completed"
    }


@router.post("/wizard/{session_token}/help")
async def request_wizard_help(
    session_token: str,
    reason: str = Query(..., description="What do you need help with?"),
    db: AsyncSession = Depends(get_db)
):
    """
    Request human help from the wizard.

    Use this when you're not sure how to answer or your situation is complex.
    Transitions the session state to 'referred' and provides next steps.
    """
    await legal_service.refer_to_help(db, session_token, reason)
    return {
        "status": "referred",
        "message": "A staff member will contact you about your legal question.",
        "next_steps": [
            "Visit the library's legal resource desk",
            "Call the legal help line",
            "Schedule an appointment with the self-help center"
        ]
    }


# ============================================================================
# State Machine Helper Functions
# ============================================================================

def _question_to_response(question) -> dict:
    if not question:
        return None
    return {
        "id": question.id,
        "slug": question.slug,
        "question_text": question.question_text,
        "help_text": question.help_text,
        "question_type": question.question_type,
        "options": question.options or [],
        "required": question.required,
        "category": question.category
    }


def _calculate_wizard_progress(session) -> int:
    answers = session.answers or {}
    if not answers:
        return 0
    return min(100, int((len(answers) / TYPICAL_QUESTION_COUNT) * 100))


def _generate_checklist(forms, packets) -> list[dict]:
    checklist = []

    for form in forms:
        checklist.append({
            "item": f"Form: {form.get('title')}",
            "form_number": form.get("form_number"),
            "completed": False
        })

    for packet in packets:
        checklist.append({
            "item": f"Packet: {packet.get('name')}",
            "completed": False
        })

    return checklist


# ============================================================================
# Summary Response Helpers (for wizard results)
# ============================================================================

def _form_to_summary(form) -> dict:
    return {
        "id": form.id,
        "title": form.title,
        "form_number": form.form_number,
        "plain_language_title": form.plain_language_title,
        "jurisdiction": form.jurisdiction,
        "difficulty_level": form.difficulty_level,
        "filing_fee": form.filing_fee,
        "languages_available": form.languages_available or ["English"],
        "status": form.status,
        "topic_id": form.topic_id,
        "topic_name": form.topic.name if form.topic else None
    }


def _packet_to_summary(packet) -> dict:
    return {
        "id": packet.id,
        "name": packet.name,
        "slug": packet.slug,
        "description": packet.description,
        "jurisdiction": packet.jurisdiction,
        "total_filing_fee": packet.total_filing_fee,
        "form_count": len(packet.forms) if packet.forms else 0,
        "is_active": packet.is_active,
        "topic_name": packet.topic.name if packet.topic else None
    }


def _guide_to_summary(guide) -> dict:
    return {
        "id": guide.id,
        "title": guide.title,
        "slug": guide.slug,
        "summary": guide.summary,
        "reading_level": guide.reading_level,
        "is_published": guide.is_published,
        "is_featured": guide.is_featured,
        "topic_id": guide.topic_id,
        "topic_name": guide.topic.name if guide.topic else None
    }
