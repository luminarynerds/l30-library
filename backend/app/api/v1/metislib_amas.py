# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MetisLib AMA Proxy Router — forwards AMA requests to MetisLib.

Exposes MetisLib's Author AMA feature to L30 patrons and staff
via /api/v1/amas/* endpoints. All state lives in MetisLib; this
router handles auth, patron hashing, and error translation.
"""
from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import Response

from ...core.config import get_settings
from ...models.user import User
from ...services.metislib_client import get_metislib_client
from ...services.metislib_errors import (
    MetisLibError, MetisLibUnavailable, MetisLibNotFound,
    MetisLibValidationError,
)
from ...utils.patron_hash import generate_patron_hash
from .auth import get_current_user, get_current_user_optional
from .dependencies import check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/amas", tags=["amas"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_metislib():
    settings = get_settings()
    if not settings.metislib_enabled:
        raise HTTPException(status_code=503, detail="AMA service not available")
    return get_metislib_client()


def _patron_hash(user: User) -> str:
    return generate_patron_hash(user.id)


def _staff_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


# ============================================================================
# Public endpoints (no auth required)
# ============================================================================

@router.get("/sessions")
async def list_sessions(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List AMA sessions (optionally filtered by status)."""
    client = _require_metislib()
    try:
        return await client.ama_list_sessions(status=status, page=page, limit=limit)
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA list error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching AMA sessions") from e


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get AMA session detail. Optionally includes patron_has_upvoted when authed."""
    client = _require_metislib()
    patron_hash = _patron_hash(current_user) if current_user else None
    try:
        return await client.ama_get_session_detail(session_id, patron_hash=patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA detail error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching AMA session") from e


# ============================================================================
# Patron endpoints (auth required)
# ============================================================================

@router.post("/sessions/{session_id}/questions")
async def submit_question(
    session_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Submit a question to an AMA session."""
    client = _require_metislib()
    patron_hash = _patron_hash(current_user)
    question_text = body.get("question_text", "")
    display_name = body.get("display_name") or "A Patron"
    try:
        return await client.ama_submit_question(
            session_id, patron_hash, question_text, display_name=display_name,
        )
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA submit error: {e}")
        raise HTTPException(status_code=502, detail="Error submitting question") from e


@router.post("/questions/{question_id}/upvote")
async def toggle_upvote(
    question_id: int,
    current_user: User = Depends(get_current_user),
):
    """Toggle upvote on a question."""
    client = _require_metislib()
    patron_hash = _patron_hash(current_user)
    try:
        return await client.ama_toggle_upvote(question_id, patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Question not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA upvote error: {e}")
        raise HTTPException(status_code=502, detail="Error toggling upvote") from e


@router.get("/sessions/{session_id}/my-questions")
async def get_my_questions(
    session_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get the current patron's questions for a session."""
    client = _require_metislib()
    patron_hash = _patron_hash(current_user)
    try:
        return await client.ama_get_my_questions(session_id, patron_hash)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA my-questions error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching your questions") from e


# ============================================================================
# Staff endpoints (auth + staff role required)
# ============================================================================

@router.post("/sessions", status_code=201)
async def create_session(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Create a new AMA session (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    staff = _staff_name(current_user)
    try:
        return await client.ama_create_session(body, staff_name=staff)
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA create error: {e}")
        raise HTTPException(status_code=502, detail="Error creating AMA session") from e


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Update an AMA session (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    try:
        return await client.ama_update_session(session_id, body)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA update error: {e}")
        raise HTTPException(status_code=502, detail="Error updating AMA session") from e


@router.put("/sessions/{session_id}/status")
async def transition_session_status(
    session_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Transition AMA session status (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    new_status = body.get("status", "")
    try:
        return await client.ama_transition_status(session_id, new_status)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA status transition error: {e}")
        raise HTTPException(status_code=502, detail="Error transitioning session status") from e


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete an upcoming AMA session (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    try:
        await client.ama_delete_session(session_id)
        return Response(status_code=204)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA delete error: {e}")
        raise HTTPException(status_code=502, detail="Error deleting AMA session") from e


@router.get("/sessions/{session_id}/moderate")
async def get_moderation_queue(
    session_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get moderation queue for an AMA session (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    try:
        return await client.ama_get_moderation_queue(session_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="AMA session not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA moderation queue error: {e}")
        raise HTTPException(status_code=502, detail="Error fetching moderation queue") from e


@router.post("/questions/{question_id}/moderate")
async def moderate_question(
    question_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Moderate a question: approve, reject, or hide (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    staff = _staff_name(current_user)
    action = body.get("action", "")
    reason = body.get("reason")
    try:
        return await client.ama_moderate_question(question_id, action, staff, reason=reason)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Question not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA moderate error: {e}")
        raise HTTPException(status_code=502, detail="Error moderating question") from e


@router.post("/questions/{question_id}/feature")
async def toggle_featured(
    question_id: int,
    current_user: User = Depends(get_current_user),
):
    """Toggle featured status on a question (staff only)."""
    check_staff_access(current_user)
    client = _require_metislib()
    try:
        return await client.ama_toggle_feature(question_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Question not found") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="AMA service temporarily unavailable") from None
    except MetisLibError as e:
        logger.error(f"MetisLib AMA feature toggle error: {e}")
        raise HTTPException(status_code=502, detail="Error toggling featured status") from e
