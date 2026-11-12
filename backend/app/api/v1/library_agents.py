# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Library AI Agents API endpoints."""

from app.core.logging import get_logger
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from limits import parse as parse_rate_limit
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.config import get_settings
from ...core.rate_limit import limiter, client_ip
from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .auth import get_current_user, get_current_user_optional
from .dependencies import is_admin, is_staff_or_admin, require_staff
from ...models.usage_statistics import QuestionType, ReferenceQuestion
from ...models.branch import Branch
from ...models.ai_agents import (
    LibraryAgent,
    AgentConversation,
    AgentKnowledgeBase,
    AgentAnalytics,
)
from ...models.ai_config import AIConfiguration
from ...models.ai_guardrails import AIUsageLimit
from ...models.user import User, UserRole
from ...services.ollama_service import get_ollama_service
from ...services.faq_chatbot_service import FAQChatbotService
from ...services.knowledge_pipeline_service import KnowledgePipelineService
from ...services.notifications.reference_chat import send_staff_reply_notification

logger = get_logger(__name__)


def _is_staff_role(user: "User") -> bool:
    return user.role in (
        UserRole.STAFF,
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DIRECTOR,
    )


router = APIRouter(prefix="/library-agents", tags=["Library Agents"])


# ============ Schemas ============


class AgentBase(BaseModel):
    name: str
    nickname: Optional[str] = None
    role: str
    department: str
    bio: str
    personality: str = "friendly"
    tone: Optional[str] = None
    specialties: List[str] = []
    can_help_with: List[str] = []
    avatar_color: Optional[str] = None
    initials: Optional[str] = None
    emoji: Optional[str] = None
    greeting_message: Optional[str] = None


class AgentResponse(AgentBase):
    id: int
    is_active: bool
    email: Optional[str] = None

    class Config:
        from_attributes = True


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[dict] = None
    followup_email: Optional[str] = Field(default=None, max_length=254)


class MessageResponse(BaseModel):
    agent_name: str
    agent_role: str
    response: str
    session_id: str
    conversation_id: int
    detected_intent: Optional[str] = None
    mode: str
    suggested_followups: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    conversation_id: int
    helpful: bool
    note: Optional[str] = None


class KnowledgeBaseEntry(BaseModel):
    category: str
    question: str
    answer: str
    tags: List[str] = []
    department: Optional[str] = None


class KnowledgeBaseResponse(KnowledgeBaseEntry):
    id: int
    is_frequently_asked: bool

    class Config:
        from_attributes = True


class StaffReplyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    question_type: Optional[str] = "ready_reference"
    subject_area: Optional[str] = None
    branch_id: Optional[int] = None
    branch_location: Optional[str] = Field(default=None, deprecated=True)


class StaffReplyResponse(BaseModel):
    conversation_id: int
    session_id: str
    staff_message: str
    reference_question_id: int
    agent_name: str


class ChatSessionSummary(BaseModel):
    session_id: str
    agent_id: int
    agent_name: str
    patron_user_id: Optional[int] = None
    last_message: str
    last_message_at: str
    message_count: int
    has_staff_reply: bool
    unread_staff_reply_count: int = 0

    class Config:
        from_attributes = True


# Canonical branch-label map. Source of truth lives in
# backend/migrations/backfill_branch_id_phase2.sql; mirror new entries there.
# See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 1).
_BRANCH_LABEL_MAP: dict[str, int] = {
    "Main": 7,
    "Main Branch": 7,
    "Main Library": 7,
    "Main Circulation Desk": 7,
    "Elmdale": 8,
    "Elmdale Branch": 8,
    "Community Annex": 9,
    "Annex": 9,
    "Bookmobile": 10,
}


def _label_to_branch_id(label: Optional[str]) -> Optional[int]:
    if not label:
        return None
    label = label.strip()
    if not label:
        return None
    if label in _BRANCH_LABEL_MAP:
        return _BRANCH_LABEL_MAP[label]
    if label.startswith("Main - "):
        return 7
    if label.startswith("Elmdale"):
        return 8
    if label.startswith("Community Annex") or label.startswith("Annex "):
        return 9
    return None


async def _resolve_branch(
    branch_id: Optional[int],
    branch_label: Optional[str],
    db: AsyncSession,
) -> tuple[Optional[int], Optional[str]]:
    if branch_id is None:
        branch_id = _label_to_branch_id(branch_label)
    if branch_id is None:
        return None, branch_label
    result = await db.execute(select(Branch.name).where(Branch.id == branch_id))
    canonical = result.scalar_one_or_none()
    return branch_id, canonical


# ============ Public Endpoints ============


@router.get("/", response_model=List[AgentResponse])
async def get_available_agents(
    department: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get all available library agents."""
    query = select(LibraryAgent).where(LibraryAgent.is_active == is_active)

    if department:
        query = query.where(LibraryAgent.department == department)

    result = await db.execute(query.order_by(LibraryAgent.name))
    agents = result.scalars().all()

    return agents


@router.post("/{agent_id}/chat", response_model=MessageResponse)
@limiter.limit("10/minute")
async def chat_with_agent(  # noqa: role-check -- public agent chat, optional auth
    request: Request,
    agent_id: int,
    message_req: MessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Send a message to an agent and get a response."""
    from ...services.ai_guardrails_service import (
        GuardrailResult,
        apply_response_guardrails,
        apply_youth_guardrails,
        check_minor_access,
        check_model_allowed,
        check_prompt_guardrails,
        check_usage_limits,
        log_ai_usage,
    )

    # Get agent
    result = await db.execute(
        select(LibraryAgent).where(LibraryAgent.id == agent_id, LibraryAgent.is_active == True)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or inactive")

    # Generate or use existing session ID
    session_id = message_req.session_id or str(uuid.uuid4())

    # Get conversation context if session exists
    conversation_context = message_req.context or {}
    if message_req.session_id:
        # Load recent conversation history
        result = await db.execute(
            select(AgentConversation)
            .where(AgentConversation.session_id == session_id)
            .order_by(AgentConversation.created_at.desc())
            .limit(5)
        )
        recent_conversations = result.scalars().all()
        conversation_context["history"] = [
            {
                "user": conv.user_message,
                "agent": conv.agent_response,
                "timestamp": conv.created_at.isoformat(),
            }
            for conv in reversed(recent_conversations)
        ]

    # Snapshot audience attributes once, used for guardrail scoping and the audit log.
    # Unknown age (anonymous, current_user is None) is treated as a minor: age
    # can't be verified, so the cautious default applies rather than exempting
    # anonymous callers from youth guardrails and usage limits.
    is_minor = True if current_user is None else bool(getattr(current_user, "is_minor", False))
    patron_type = getattr(current_user, "patron_type", None) if current_user else None

    guardrail_result = GuardrailResult()
    # Failures here mean "could not check", not "checked and clean" -- tracked
    # separately from guardrail_result.block_reason so the audit row (below)
    # never records an unguarded pass as though it were a clean one.
    guardrail_check_failures: List[str] = []

    # --- Guardrails: agent-level minor / consent / patron-type gating.
    # check_minor_access(tool, user) already treats user=None as an
    # unverifiable minor (blocks when the agent blocks minors or requires
    # parental consent, since neither can be confirmed anonymously) rather
    # than crashing or silently allowing, so no anonymous special-casing is
    # needed here.
    minor_ok, minor_reason = check_minor_access(agent, current_user)
    if not minor_ok:
        guardrail_result.blocked = True
        guardrail_result.block_reason = minor_reason

    # --- Guardrails: usage limits. Authenticated callers are counted
    # per-account by check_usage_limits (DB-backed, keyed by user_id).
    # Anonymous callers have no account, and privacy rules forbid recording
    # one on this path (see log_ai_usage's log_content=False below), so
    # they're rate-limited instead through the route's existing slowapi
    # per-IP limiter (_check_anonymous_usage_limit) -- the same transient
    # store the blanket @limiter.limit("10/minute") above already uses, not a
    # new durable record. check_minor_access already treats unknown age as a
    # minor; this applies the matching "child" rate rather than exempting
    # anonymous callers entirely.
    if not guardrail_result.blocked:
        if current_user:
            try:
                usage_ok, usage_reason = await check_usage_limits(
                    db,
                    current_user.id,
                    current_user.role.value
                    if hasattr(current_user.role, "value")
                    else str(current_user.role),
                )
            except SQLAlchemyError as e:  # transient DB issue -- fail open, but loudly
                logger.error(
                    f"Usage-limit check failed, allowing message through: {e}", exc_info=True
                )
                sentry_sdk.capture_exception(e)
                guardrail_check_failures.append(f"usage-limit check did not run: {e}")
                usage_ok, usage_reason = True, None
        else:
            try:
                usage_ok, usage_reason = await _check_anonymous_usage_limit(db, request)
            except Exception as e:  # noqa: BLE001  # rate-limit storage issue -- fail open, but loudly
                logger.error(
                    f"Anonymous rate-limit check failed, allowing message through: {e}",
                    exc_info=True,
                )
                sentry_sdk.capture_exception(e)
                guardrail_check_failures.append(f"anonymous rate-limit check did not run: {e}")
                usage_ok, usage_reason = True, None
        if not usage_ok:
            guardrail_result.blocked = True
            guardrail_result.block_reason = usage_reason

    # --- Guardrails: model allowlist. The model actually used for generation
    # is resolved from the admin-editable "agent_chat" AIConfiguration row
    # inside generate_agent_response (config_value["model"]); peek at that
    # same override here so it gets the same allowlist check the staff
    # AI-tool path already applies to AITool.model. The Ollama service's own
    # built-in default (used when no override is configured) is deploy-time
    # settings, not runtime-admin-editable, so it isn't in scope here.
    if not guardrail_result.blocked:
        try:
            agent_chat_config_result = await db.execute(
                select(AIConfiguration).where(AIConfiguration.config_key == "agent_chat")
            )
            agent_chat_config = agent_chat_config_result.scalar_one_or_none()
            configured_model = (
                agent_chat_config.config_value.get("model")
                if agent_chat_config and agent_chat_config.config_value
                else None
            )
            if configured_model:
                model_ok, model_reason = await check_model_allowed(db, configured_model)
                if not model_ok:
                    guardrail_result.blocked = True
                    guardrail_result.block_reason = model_reason
        except SQLAlchemyError as e:  # transient DB issue -- fail open, but loudly
            logger.error(
                f"Model-allowlist check failed, allowing message through: {e}", exc_info=True
            )
            sentry_sdk.capture_exception(e)
            guardrail_check_failures.append(f"model-allowlist check did not run: {e}")

    # --- Guardrails: prompt content (blocked topics, filters, disclaimers).
    # tool_id=None so every enabled guardrail applies regardless of scoping --
    # LibraryAgent personas (Marlene, Stevie, ...) don't correspond to any
    # AITool.tool_id or existing applies_to_tools entry, so a made-up tool_id
    # here would silently exclude scoped guardrails instead of including them.
    if not guardrail_result.blocked:
        try:
            guardrail_result = await check_prompt_guardrails(
                db,
                message_req.message,
                tool_id=None,
                is_minor=is_minor,
                patron_type=patron_type,
            )
        except SQLAlchemyError as e:  # transient DB issue -- fail open, but loudly
            logger.error(
                f"Prompt guardrail check failed, allowing message through unguarded: {e}",
                exc_info=True,
            )
            sentry_sdk.capture_exception(e)
            guardrail_check_failures.append(f"prompt guardrail check did not run: {e}")
            guardrail_result = GuardrailResult()

    # --- Guardrails: youth patron protections. apply_youth_guardrails()
    # returns early on user=None, so an anonymous caller (treated as a minor,
    # see is_minor above) needs the same system-prompt addition applied here
    # instead -- duplicated rather than changing that shared function's
    # signature, which the staff AI-tool path also calls.
    if current_user:
        guardrail_result = apply_youth_guardrails(guardrail_result, current_user)
    elif is_minor:
        guardrail_result.system_prompt_additions.append(
            "The current user is a minor. Keep all responses age-appropriate. "
            "Do not generate reading recommendations that reference or reveal "
            "this user's borrowing history, reading patterns, or hold list."
        )

    # Generate agent response
    start_time = datetime.now()
    if guardrail_result.blocked:
        agent_response = (
            guardrail_result.block_reason
            or "I'm not able to help with that. Please contact library staff directly."
        )
        detected_intent = detect_intent(message_req.message)
        response_mode = "rule_based"
    else:
        agent_response, detected_intent, response_mode = await generate_agent_response(
            agent, message_req.message, conversation_context, db, guardrail_result
        )
        agent_response = apply_response_guardrails(agent_response, guardrail_result)
    response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    # Save conversation
    conversation = AgentConversation(
        agent_id=agent.id,
        user_id=current_user.id if current_user else None,
        session_id=session_id,
        user_message=message_req.message,
        agent_response=agent_response,
        conversation_context=conversation_context,
        detected_intent=detected_intent,
        response_time_ms=response_time_ms,
        patron_followup_email=message_req.followup_email,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Audit error_message distinguishes "checked and clean" (None) from
    # "blocked" (the block reason) from "could not check" (recorded even
    # though success stays True -- the chat itself still went through).
    audit_error_message = guardrail_result.block_reason if guardrail_result.blocked else None
    if guardrail_check_failures:
        failures_note = "; ".join(guardrail_check_failures)
        audit_error_message = (
            f"{audit_error_message} | guardrail check(s) did not run: {failures_note}"
            if audit_error_message
            else f"guardrail check(s) did not run: {failures_note}"
        )

    # Guardrail audit trail -- best-effort and isolated in its own commit so a
    # logging failure can never undo the conversation record above or block
    # the patron's reply.
    try:
        # log_content=False: patron chat questions are a reading-history
        # record. This audit row carries guardrail/outcome metadata only --
        # no patron identity (user_id), no demographic snapshot (was_minor,
        # patron_type_at_request), and no message/response/system-prompt
        # content. Contrast the staff AI-tool path (ai_tools.py), which
        # deliberately keeps the log_ai_usage default (log_content=True) and
        # writes full previews.
        await log_ai_usage(
            db,
            None,
            "library_agent",
            None,
            message_req.message,
            agent_response,
            response_time_ms,
            guardrail_result=guardrail_result,
            success=not guardrail_result.blocked,
            error_message=audit_error_message,
            log_content=False,
        )
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to record AI usage/guardrail audit log: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)

    # Capture interaction for knowledge pipeline (opt-in; default off pending patron consent).
    # Skipped for guardrail-blocked exchanges -- a refusal isn't library knowledge worth
    # feeding back into the pipeline.
    if (
        not guardrail_result.blocked
        and os.getenv("KNOWLEDGE_PIPELINE_CAPTURE_ENABLED", "false").lower() == "true"
    ):
        try:
            pipeline = KnowledgePipelineService()
            await pipeline.ingest_patron_interaction(
                db=db,
                title=message_req.message[:200],
                content=f"Q: {message_req.message}\n\nA: {agent_response}",
                category="patron_chat",
                source_reference_id=str(conversation.id),
                persona_domain=agent.department or "shared",
                satisfaction_signal=None,
                patron_id=current_user.id if current_user else None,
            )
        except Exception as e:  # noqa: BLE001  # knowledge pipeline best-effort — chat response already returned
            logger.warning(f"Failed to capture interaction for pipeline: {e}")

    # Generate suggested follow-ups
    suggested_followups = get_suggested_followups(agent, detected_intent)

    return MessageResponse(
        agent_name=agent.name,
        agent_role=agent.role,
        response=agent_response,
        session_id=session_id,
        conversation_id=conversation.id,
        detected_intent=detected_intent,
        mode=response_mode,
        suggested_followups=suggested_followups,
    )


@router.post("/feedback")
async def submit_feedback(  # noqa: role-check -- public feedback on agent conversation
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback for an agent conversation."""
    conversation = await get_or_404(
        db, AgentConversation, feedback.conversation_id, "Conversation not found"
    )

    conversation.helpful = feedback.helpful
    conversation.feedback_note = feedback.note
    await db.commit()

    return {"message": "Thank you for your feedback!"}


# ============ Knowledge Base ============


@router.get("/knowledge/search", response_model=List[KnowledgeBaseResponse])
async def search_knowledge_base(
    query: str = Query(..., min_length=2),
    category: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search the agent knowledge base."""
    safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    stmt = select(AgentKnowledgeBase).where(
        (AgentKnowledgeBase.question.ilike(f"%{safe_query}%"))
        | (AgentKnowledgeBase.answer.ilike(f"%{safe_query}%"))
    )

    if category:
        stmt = stmt.where(AgentKnowledgeBase.category == category)

    if department:
        stmt = stmt.where(AgentKnowledgeBase.department == department)

    stmt = stmt.order_by(
        AgentKnowledgeBase.is_frequently_asked.desc(),
        AgentKnowledgeBase.priority.desc(),
    ).limit(limit)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    return entries


# ============ Staff Chat Endpoints ============


@router.get("/chat-sessions", response_model=List[ChatSessionSummary])
async def get_active_chat_sessions(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chat sessions for the current user.

    Staff/admin see ALL sessions (review queue). Patrons see only sessions
    they own (drives the unread-reply badge on the patron client).
    """
    # Get distinct sessions with their latest message
    from sqlalchemy import distinct, case

    is_staff = _is_staff_role(current_user)

    base = select(
        AgentConversation.session_id,
        func.max(AgentConversation.id).label("latest_id"),
        func.count(AgentConversation.id).label("msg_count"),
    )
    if not is_staff:
        base = base.where(AgentConversation.user_id == current_user.id)
    subquery = (
        base.group_by(AgentConversation.session_id)
        .order_by(func.max(AgentConversation.created_at).desc())
        .limit(limit)
        .subquery()
    )

    result = await db.execute(
        select(AgentConversation, subquery.c.msg_count)
        .join(subquery, AgentConversation.id == subquery.c.latest_id)
        .options(selectinload(AgentConversation.agent))
    )
    rows = result.all()
    conversations = [row[0] for row in rows]
    count_map = {row[0].session_id: row[1] for row in rows}

    # Check which sessions have staff replies
    staff_reply_result = await db.execute(
        select(AgentConversation.session_id)
        .where(
            AgentConversation.session_id.in_([c.session_id for c in conversations]),
            AgentConversation.conversation_context.op("->>")("staff_reply").isnot(None),
        )
        .distinct()
    )
    sessions_with_staff_reply = {row[0] for row in staff_reply_result}

    # Count UNREAD staff replies per session for the current user. This is
    # informational for staff dashboards; the same field surfaces a patron
    # badge once we let patrons read their own session list.
    unread_counts_result = await db.execute(
        select(
            AgentConversation.session_id,
            func.count(AgentConversation.id),
        )
        .where(
            AgentConversation.user_id == current_user.id,
            AgentConversation.conversation_context.op("->>")("staff_reply").isnot(None),
            AgentConversation.seen_by_patron_at.is_(None),
        )
        .group_by(AgentConversation.session_id)
    )
    unread_by_session = {row[0]: row[1] for row in unread_counts_result}

    summaries = []
    for conv in conversations:
        summaries.append(
            ChatSessionSummary(
                session_id=conv.session_id,
                agent_id=conv.agent_id,
                agent_name=conv.agent.name if conv.agent else "Unknown",
                patron_user_id=conv.user_id,
                last_message=conv.user_message[:200],
                last_message_at=conv.created_at.isoformat(),
                message_count=count_map.get(conv.session_id, 1),
                has_staff_reply=conv.session_id in sessions_with_staff_reply,
                unread_staff_reply_count=unread_by_session.get(conv.session_id, 0),
            )
        )

    return summaries


@router.get("/chat-sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a chat session.

    Both staff (reviewing/responding) and the session-owning patron may call
    this endpoint. Only the session-owning patron triggers the mark-seen
    side effect on staff replies — staff fetches stay non-mutating so the
    patrons unread badge isnt cleared by staff activity.
    """
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.session_id == session_id)
        .options(selectinload(AgentConversation.agent))
        .order_by(AgentConversation.created_at.asc())
    )
    conversations = result.scalars().all()

    if not conversations:
        raise HTTPException(status_code=404, detail="Session not found")

    is_staff = _is_staff_role(current_user)
    if not is_staff and conversations[0].user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session")

    # Mark unread staff replies as seen ONLY when the requester owns the
    # session. Staff hitting this endpoint via the reference-chat dashboard
    # must NOT clear the patron's unread badge.
    if conversations[0].user_id == current_user.id:
        await db.execute(
            update(AgentConversation)
            .where(
                AgentConversation.session_id == session_id,
                AgentConversation.conversation_context.op("->>")("staff_reply").isnot(None),
                AgentConversation.seen_by_patron_at.is_(None),
            )
            .values(seen_by_patron_at=datetime.now(timezone.utc))
        )
        await db.commit()

    messages = []
    for conv in conversations:
        messages.append(
            {
                "id": conv.id,
                "user_message": conv.user_message,
                "agent_response": conv.agent_response,
                "agent_name": conv.agent.name if conv.agent else "Unknown",
                "detected_intent": conv.detected_intent,
                "created_at": conv.created_at.isoformat(),
                "is_staff_reply": bool(
                    conv.conversation_context and conv.conversation_context.get("staff_reply")
                ),
                "staff_id": (
                    conv.conversation_context.get("staff_id") if conv.conversation_context else None
                ),
                "staff_name": (
                    conv.conversation_context.get("staff_name")
                    if conv.conversation_context
                    else None
                ),
            }
        )

    return {
        "session_id": session_id,
        "agent_id": conversations[0].agent_id,
        "agent_name": conversations[0].agent.name if conversations[0].agent else "Unknown",
        "messages": messages,
    }


@router.post("/chat-sessions/{session_id}/staff-reply", response_model=StaffReplyResponse)
async def staff_reply_to_session(
    session_id: str,
    reply: StaffReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Staff member replies to a patron chat session.
    Automatically logs a reference question for IMLS/PLA statistics.
    """
    # Find the session and agent (lock to prevent concurrent duplicate replies)
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.session_id == session_id)
        .options(selectinload(AgentConversation.agent))
        .order_by(AgentConversation.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    latest = result.scalar_one_or_none()

    if not latest:
        raise HTTPException(status_code=404, detail="Chat session not found")

    agent = latest.agent

    # Save the staff reply as a conversation entry
    conversation = AgentConversation(
        agent_id=agent.id,
        user_id=latest.user_id,
        session_id=session_id,
        user_message="[Staff reply]",
        agent_response=reply.message,
        conversation_context={
            "staff_reply": True,
            "staff_id": current_user.id,
            "staff_name": current_user.first_name or current_user.email,
        },
        detected_intent="staff_response",
        response_time_ms=0,
    )
    db.add(conversation)

    # Auto-log as a reference question
    question_type_map = {
        "directional": "directional",
        "ready_reference": "ready_reference",
        "research": "research",
        "readers_advisory": "readers_advisory",
        "technical": "technical",
    }
    q_type = QuestionType(question_type_map.get(reply.question_type, "ready_reference"))

    resolved_branch_id, resolved_branch_label = await _resolve_branch(
        reply.branch_id, reply.branch_location, db
    )
    ref_question = ReferenceQuestion(
        asked_at=datetime.now(timezone.utc),
        branch_id=resolved_branch_id,
        branch_location=resolved_branch_label,
        question_type=q_type,
        contact_method="chat",
        patron_type="unknown",
        subject_area=reply.subject_area,
        was_referred=False,
        answered_by_id=current_user.id,
        notes=f"Chat session {session_id} - Patron asked: {latest.user_message[:200]}",
    )
    db.add(ref_question)

    await db.commit()
    await db.refresh(conversation)
    await db.refresh(ref_question)

    try:
        await send_staff_reply_notification(db, conversation)
    except Exception:
        logger.exception("staff_reply notification dispatch failed for conv %s", conversation.id)

    return StaffReplyResponse(
        conversation_id=conversation.id,
        session_id=session_id,
        staff_message=reply.message,
        reference_question_id=ref_question.id,
        agent_name=agent.name,
    )


# ============ Admin Analytics (must precede /{agent_id}) ============


class AdminAgentConversation(BaseModel):
    id: int
    agent_id: int
    agent_name: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    session_id: str
    user_message: str
    agent_response: str
    detected_intent: Optional[str] = None
    helpful: Optional[bool] = None
    feedback_note: Optional[str] = None
    response_time_ms: Optional[int] = None
    created_at: str


class AdminConversationListResponse(BaseModel):
    conversations: List[AdminAgentConversation]
    total: int
    page: int
    per_page: int


class AdminAgentStats(BaseModel):
    total_agents: int
    active_agents: int
    total_conversations: int
    total_feedback: int
    avg_helpfulness_rate: float
    knowledge_base_entries: int


@router.get("/admin/conversations", response_model=AdminConversationListResponse)
async def list_admin_conversations(
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    helpful: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    """Paginated agent Q+A exchanges for the admin analytics view."""
    stmt = select(AgentConversation).options(
        selectinload(AgentConversation.agent),
        selectinload(AgentConversation.user),
    )
    count_stmt = select(func.count(AgentConversation.id))

    if agent_id is not None:
        stmt = stmt.where(AgentConversation.agent_id == agent_id)
        count_stmt = count_stmt.where(AgentConversation.agent_id == agent_id)
    if user_id is not None:
        stmt = stmt.where(AgentConversation.user_id == user_id)
        count_stmt = count_stmt.where(AgentConversation.user_id == user_id)
    if helpful is not None:
        stmt = stmt.where(AgentConversation.helpful.is_(helpful))
        count_stmt = count_stmt.where(AgentConversation.helpful.is_(helpful))
    if start_date:
        stmt = stmt.where(AgentConversation.created_at >= start_date)
        count_stmt = count_stmt.where(AgentConversation.created_at >= start_date)
    if end_date:
        stmt = stmt.where(AgentConversation.created_at <= end_date)
        count_stmt = count_stmt.where(AgentConversation.created_at <= end_date)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(AgentConversation.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )

    conversations = [
        AdminAgentConversation(
            id=c.id,
            agent_id=c.agent_id,
            agent_name=c.agent.name if c.agent else None,
            user_id=c.user_id,
            user_email=c.user.email if c.user else None,
            session_id=c.session_id,
            user_message=c.user_message,
            agent_response=c.agent_response,
            detected_intent=c.detected_intent,
            helpful=c.helpful,
            feedback_note=c.feedback_note,
            response_time_ms=c.response_time_ms,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in rows
    ]
    return AdminConversationListResponse(
        conversations=conversations,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/admin/stats", response_model=AdminAgentStats)
async def get_admin_agent_stats(
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
):
    """Aggregate counts across all agents (admin dashboard)."""
    total_agents = (await db.execute(select(func.count(LibraryAgent.id)))).scalar_one()
    active_agents = (
        await db.execute(
            select(func.count(LibraryAgent.id)).where(LibraryAgent.is_active.is_(True))
        )
    ).scalar_one()
    total_conversations = (await db.execute(select(func.count(AgentConversation.id)))).scalar_one()
    total_feedback = (
        await db.execute(
            select(func.count(AgentConversation.id)).where(AgentConversation.helpful.isnot(None))
        )
    ).scalar_one()
    helpful_count = (
        await db.execute(
            select(func.count(AgentConversation.id)).where(AgentConversation.helpful.is_(True))
        )
    ).scalar_one()
    avg_helpfulness_rate = (helpful_count / total_feedback) if total_feedback else 0.0
    knowledge_base_entries = (
        await db.execute(select(func.count(AgentKnowledgeBase.id)))
    ).scalar_one()

    return AdminAgentStats(
        total_agents=total_agents,
        active_agents=active_agents,
        total_conversations=total_conversations,
        total_feedback=total_feedback,
        avg_helpfulness_rate=avg_helpfulness_rate,
        knowledge_base_entries=knowledge_base_entries,
    )


# ============ Single-Agent Lookup (after all static paths) ============


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific agent by ID."""
    agent = await get_or_404(db, LibraryAgent, agent_id, "Agent not found")

    return agent


@router.get("/name/{agent_name}", response_model=AgentResponse)
async def get_agent_by_name(agent_name: str, db: AsyncSession = Depends(get_db)):
    """Get an agent by name (case-insensitive)."""
    result = await db.execute(
        select(LibraryAgent).where(func.lower(LibraryAgent.name) == agent_name.lower())
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    return agent


# ============ Admin Endpoints ============


@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new library agent (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Generate system prompt
    system_prompt = generate_system_prompt(agent_data)

    agent = LibraryAgent(
        **agent_data.model_dump(),
        system_prompt=system_prompt,
        is_active=True,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an agent (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    agent = await get_or_404(db, LibraryAgent, agent_id, "Agent not found")

    for key, value in agent_data.model_dump().items():
        setattr(agent, key, value)

    agent.system_prompt = generate_system_prompt(agent_data)
    await db.commit()
    await db.refresh(agent)

    return agent


@router.post("/knowledge", response_model=KnowledgeBaseResponse)
async def add_knowledge(
    entry: KnowledgeBaseEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add knowledge base entry (staff only)."""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Staff access required")

    kb_entry = AgentKnowledgeBase(
        **entry.model_dump(),
        created_by_id=current_user.id,
    )

    db.add(kb_entry)
    await db.commit()
    await db.refresh(kb_entry)

    return kb_entry


# ============ Helper Functions ============


async def _check_anonymous_usage_limit(
    db: AsyncSession, request: Request
) -> tuple[bool, Optional[str]]:
    """Rate-limits anonymous library-agent chat callers at the "child" role's
    configured rate (AIUsageLimit.role == "child"), without writing any
    per-client identifier to a database row.

    Uses the same slowapi limiter/store already backing this route's blanket
    @limiter.limit("10/minute") decorator -- a transient, already-existing
    per-IP bucket, not a new durable record. slowapi's declarative decorator
    syntax can't express "a stricter limit only when unauthenticated" cleanly:
    its dynamic-limit-value and exempt_when hooks are called with the
    resolved rate-limit key (or nothing) but never with auth state, which
    requires resolving get_current_user_optional -- a FastAPI dependency, not
    something slowapi's callables have access to. So this calls the
    limiter's underlying hit() directly, gated on current_user being None at
    the call site in chat_with_agent instead of via the decorator.
    """
    result = await db.execute(
        select(AIUsageLimit).where(AIUsageLimit.role == "child", AIUsageLimit.enabled == True)
    )
    child_limit = result.scalar_one_or_none()
    if not child_limit:
        return True, None  # No limit configured = unlimited, same convention as check_usage_limits

    # Transient rate-limit key only -- resolved per request, never persisted.
    key = client_ip(request)

    hourly_ok = limiter.limiter.hit(
        parse_rate_limit(f"{child_limit.hourly_limit}/hour"), key, "agent-chat-anon-hourly"
    )
    if not hourly_ok:
        return (
            False,
            f"Hourly AI usage limit reached ({child_limit.hourly_limit} requests/hour). Please try again later.",
        )

    daily_ok = limiter.limiter.hit(
        parse_rate_limit(f"{child_limit.daily_limit}/day"), key, "agent-chat-anon-daily"
    )
    if not daily_ok:
        return (
            False,
            f"Daily AI usage limit reached ({child_limit.daily_limit} requests/day). Please try again tomorrow.",
        )

    return True, None


async def generate_agent_response(
    agent: LibraryAgent, user_message: str, context: dict, db: AsyncSession, guardrail_result
) -> tuple[str, Optional[str], str]:
    detected_intent = detect_intent(user_message)

    # Bypass LLM and use grounded rule-based replies when set. Intended for hosts
    # where the available local model is too small to follow the system prompt
    # reliably (it agrees with user-suggested premises and invents facts). Flip
    # this off once a larger model is viable. The rule-based path has no system
    # prompt at all (see _rule_based_response below), so guardrail_result's
    # system_prompt_additions have nothing to attach to here -- they only
    # matter on the LLM branch below.
    if os.getenv("DISABLE_AGENT_LLM", "").lower() in ("1", "true", "yes"):
        return _rule_based_response(agent, user_message, context), detected_intent, "rule_based"

    # Try Ollama first
    try:
        ollama = get_ollama_service()
        if await ollama.is_available():
            # Load admin config from DB (same pattern as ai_settings.py)
            result = await db.execute(
                select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
            )
            ollama_config = result.scalar_one_or_none()
            if ollama_config and ollama_config.config_value:
                base_url = ollama_config.config_value.get("base_url", ollama.base_url)
                if base_url != ollama.base_url:
                    ollama = get_ollama_service(base_url=base_url)

            # Load generation settings (temperature, max_tokens, model)
            result = await db.execute(
                select(AIConfiguration).where(AIConfiguration.config_key == "agent_chat")
            )
            agent_chat_config = result.scalar_one_or_none()
            config_temperature = 0.7
            config_max_tokens = 500
            config_model = None
            if agent_chat_config and agent_chat_config.config_value:
                config_temperature = agent_chat_config.config_value.get("temperature", 0.7)
                config_max_tokens = agent_chat_config.config_value.get("max_tokens", 500)
                config_model = agent_chat_config.config_value.get("model")

            if config_model and config_model != ollama.model:
                ollama = get_ollama_service(model=config_model)

            # Build system prompt from agent personality, then apply the same
            # guardrail wrapping (youth age-appropriateness instruction,
            # response-prefix rules, etc.) the staff AI-tool path already
            # applies to its own system prompt at ai_tools.py:390. Without
            # this, guardrail_result.system_prompt_additions was computed in
            # chat_with_agent but silently dropped -- correct in code review,
            # inert at runtime. Wrapped before the RAG context is appended so
            # the guardrail instruction stays at the very front of the
            # prompt (matching the staff path's intent of wrapping the
            # tool's own system prompt) rather than being buried after the
            # retrieved knowledge-base block, which is reference data, not
            # an instruction, and shouldn't dilute the guardrail's position.
            from ...services.ai_guardrails_service import build_guarded_system_prompt

            system_prompt = generate_system_prompt(agent)
            system_prompt = build_guarded_system_prompt(system_prompt, guardrail_result)

            # Inject RAG context from knowledge base (non-blocking)
            try:
                faq_service = FAQChatbotService()
                rag_results = await faq_service._semantic_search(
                    db, user_message, location_id=None, limit=3
                )
                rag_context = ""
                if rag_results["results"]:
                    rag_context = "\n\n---\nRelevant library knowledge (use this to inform your response, but respond naturally):\n"
                    for r in rag_results["results"]:
                        rag_context += f"- {r['text_content']}\n"
                    rag_context += "---\n"
                enriched_prompt = system_prompt + rag_context
            except Exception as rag_err:  # noqa: BLE001  # RAG context best-effort — continue without
                logger.warning(f"RAG context unavailable, continuing without it: {rag_err}")
                enriched_prompt = system_prompt

            # Build multi-turn messages from conversation history
            messages = []
            history = context.get("history", [])
            for turn in history:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["agent"]})
            messages.append({"role": "user", "content": user_message})

            # Call Ollama with multi-turn chat
            result = await ollama.chat(
                messages=messages,
                system_prompt=enriched_prompt,
                temperature=config_temperature,
                max_tokens=config_max_tokens,
            )
            return result["response"], detected_intent, "llm"
    except Exception as e:  # noqa: BLE001  # Ollama unavailable — fall back to rule-based
        logger.warning(f"Ollama unavailable, falling back to rules: {e}")

    # Fallback to existing rule-based logic
    return _rule_based_response(agent, user_message, context), detected_intent, "rule_based"


def _rule_based_response(agent: LibraryAgent, user_message: str, context: dict) -> str:
    message_lower = user_message.lower()

    # Greetings
    greeting_words = ["hi", "hello", "hey", "howdy", "greetings"]
    if any(word in message_lower for word in greeting_words):
        return (
            agent.greeting_message
            or f"Hi there! I'm {agent.name}, {agent.role} at {get_settings().library_name}. {agent.bio} How can I help you today?"
        )

    # Hours questions
    if any(word in message_lower for word in ["hours", "open", "close", "when"]):
        responses = {
            "Marlene": "Great question! Our main branch is open Mon-Thu 9am-8pm, Fri 9am-6pm, Sat 10am-5pm, Sun 1pm-5pm. The Elmdale branch runs Mon-Fri 10am-6pm, Sat 10am-4pm. We also have the Jamie Chick Community Annex with more limited hours. Planning a visit?",
            "Stevie": "Hey! Main branch hours are Mon-Thu 9-8, Fri 9-6, Sat 10-5, Sun 1-5. Elmdale is Mon-Fri 10-6, Sat 10-4. And heads up-our website has a live chat feature during open hours too!",
            "Donna Fay": "Well, my Elmdale branch is open Mon-Fri 10am-6pm and Sat 10am-4pm. We're smaller than the main branch but mighty! The main branch on Oak Street has longer hours-open until 8pm most weeknights. When were you thinking of stopping by?",
        }
        response = responses.get(
            agent.name,
            "Our main branch is open Mon-Thu 9-8, Fri 9-6, Sat 10-5, Sun 1-5. The Elmdale branch has slightly different hours. What location are you interested in?",
        )
        return get_personality_response(agent, response)

    # Book recommendations
    if any(word in message_lower for word in ["recommend", "suggestion", "book", "read"]):
        if agent.name == "Sophie":
            response = "Oh I LOVE this question! What age are we shopping for? I've got amazing picture books for the little ones, early readers for kids just starting out, and chapter books that'll hook even reluctant readers. Also, I just got in some gorgeous bilingual books!"
        elif agent.name == "Twyla":
            response = "Ooh yes! Book recs are my jam. Are we talking contemporary? Fantasy? Romance? Graphic novels? I've been reading a TON of BookTok favorites lately, and honestly? Some of them slap. What vibe are you going for?"
        elif agent.name == "Pat":
            response = "I'd be delighted to help. Are you looking for fiction or non-fiction? Any particular genre or subject matter? I can also help you find books similar to ones you've enjoyed before, or suggest award winners if you're not sure where to start."
        else:
            response = "I'd be happy to help! What genres or topics interest you? We have an amazing collection and I can also check our digital offerings."
        return get_personality_response(agent, response)

    # Library card questions
    if any(
        word in message_lower
        for word in ["card", "library card", "membership", "sign up", "register"]
    ):
        response = "Getting a library card is easy and totally free! Just bring a photo ID and proof of address (like a utility bill or lease) to any of our locations. If you're under 18, bring a parent or guardian. You can start using your card right away!"
        if agent.name == "Thel":
            response = "That's my specialty! Library cards are free and super easy to get. Bring a photo ID and proof of address to any branch, and we'll set you up in just a few minutes. Already have a card but forgot your number? I can look that up for you too!"
        return get_personality_response(agent, response)

    # Programs and events
    if any(
        word in message_lower for word in ["event", "program", "class", "workshop", "story time"]
    ):
        if agent.name == "Sophie":
            response = "Story time is my favorite! We have Toddler Time on Tuesdays at 10am, Preschool Story Time on Thursdays at 10:30am, and Baby Bounce on Fridays at 11am. Plus we do special themed story times once a month-next one is dinosaurs!"
        elif agent.name == "Jordan":
            response = "The Makerspace is where it's at! We have Intro to 3D Printing workshops every other Saturday, a teen coding club on Wednesdays, and drop-in hours for creative projects. Want me to sign you up for something?"
        elif agent.name == "Twyla":
            response = "Oh! We've got book club for teens on the first Tuesday of every month, gaming nights (both video and tabletop), and our sensory-friendly programs. Plus summer reading is coming up and it's going to be EPIC this year."
        else:
            response = "We have programs for all ages! Story times for kids, book clubs for adults, Makerspace workshops, genealogy classes, tech help sessions, and seasonal events. Check our Events page or let me know what you're interested in!"
        return get_personality_response(agent, response)

    # Digital resources
    if any(
        word in message_lower
        for word in ["ebook", "e-book", "audiobook", "audio book", "digital", "online", "app"]
    ):
        if agent.name == "Stevie":
            response = "YES! We've got you covered digitally. Download the Palace Project app (my favorite!), sign in with your library card, and boom - thousands of ebooks and audiobooks from an open-source platform built by libraries. Need help setting it up? I can walk you through it!"
        else:
            response = "We offer digital collections through Palace Project and our Indie Authors catalog! Use your library card number to access thousands of e-books and audiobooks. All open-source, no corporate tracking. Stevie or Jordan can help you get set up if you need it."
        return get_personality_response(agent, response)

    # Makerspace
    if any(word in message_lower for word in ["makerspace", "3d print", "laser cut", "maker"]):
        if agent.name == "Jordan":
            response = "The Makerspace is my baby! We've got 3D printers, laser cutters, vinyl cutters, button makers, and tons more. Some equipment needs training first (free workshops every other week!), but lots of stuff is drop-in friendly. What did you want to make?"
        elif agent.name == "Stevie":
            response = "Our Makerspace is AMAZING. Jordan runs it and they're seriously talented. We've got all the toys-3D printers, laser cutters, the works. Equipment training is required for some stuff but it's quick and free. Jordan will get you creating in no time!"
        else:
            response = "Our Makerspace has 3D printers, laser cutters, vinyl cutters, button makers, sewing machines, and more! Jordan coordinates all Makerspace activities and can help you with training and reservations."
        return get_personality_response(agent, response)

    # Thanks/gratitude
    if any(word in message_lower for word in ["thank", "thanks", "appreciate"]):
        responses = {
            "Marlene": "You're very welcome! That's what we're here for. Don't hesitate to reach out anytime.",
            "Stevie": "No problem! Happy to help!",
            "Twyla": "Of course! Come back anytime you need anything!",
            "Sophie": "De nada! That's what I'm here for!",
        }
        response = responses.get(agent.name, "You're welcome! Happy to help anytime!")
        return get_personality_response(agent, response)

    # Default response with personality
    default_responses = {
        "Marlene": "That's an excellent question. While strategic planning is my main focus, I can point you in the right direction. Could you tell me a bit more about what you're looking for?",
        "Stevie": "Hmm, interesting question! I'm better with tech stuff, but let me think... Could you give me a bit more detail about what you need?",
        "Twyla": "Oh! That's not really my area (I mostly work with teens and tweens), but I bet one of my colleagues can help. Want me to point you to the right person?",
    }

    response = default_responses.get(
        agent.name,
        f"That's a great question! As {agent.role}, I can help with {', '.join(agent.can_help_with[:3])}. Could you tell me a bit more about what you're looking for?",
    )

    return get_personality_response(agent, response)


def detect_intent(message: str) -> Optional[str]:
    message_lower = message.lower()

    if any(word in message_lower for word in ["hours", "open", "close", "when"]):
        return "hours_question"
    elif any(word in message_lower for word in ["recommend", "suggest", "book", "read"]):
        return "book_recommendation"
    elif any(word in message_lower for word in ["event", "program", "class", "workshop"]):
        return "program_inquiry"
    elif any(word in message_lower for word in ["card", "library card", "membership", "sign up"]):
        return "library_card"
    elif any(word in message_lower for word in ["reserve", "hold", "request"]):
        return "hold_request"

    return "general_inquiry"


def get_personality_response(agent: LibraryAgent, base_message: str) -> str:
    personality = agent.personality

    if personality == "enthusiastic":
        return f"{base_message} (I love helping with library stuff!)"
    elif personality == "quirky":
        return f"Oh! {base_message} (I get excited about library stuff!)"
    elif personality == "witty":
        return f"{base_message}"
    elif personality == "calm":
        return f"{base_message} Take your time, I'm here to help."
    else:  # friendly
        return base_message


def get_suggested_followups(agent: LibraryAgent, intent: Optional[str]) -> List[str]:
    if intent == "hours_question":
        return [
            "What are the holiday hours?",
            "Is there parking available?",
            "Do you have a bookmobile?",
        ]
    elif intent == "book_recommendation":
        return [
            "What's new this month?",
            "Do you have bestsellers?",
            "Can I request a specific book?",
        ]
    elif intent == "program_inquiry":
        return [
            "How do I sign up?",
            "Are programs free?",
            "What's happening this week?",
        ]
    else:
        return [
            "What are your hours?",
            "Can you recommend a book?",
            "What programs do you offer?",
        ]


def generate_system_prompt(agent: AgentBase) -> str:
    _lib_name = get_settings().library_name
    return f"""You are {agent.name}, {agent.role} at {_lib_name}.

PERSONALITY: {agent.personality}
TONE: {agent.tone or "warm and helpful"}

ABOUT YOU:
{agent.bio}

YOUR SPECIALTIES:
{chr(10).join(f"- {s}" for s in agent.specialties)}

YOU CAN HELP WITH:
{chr(10).join(f"- {h}" for h in agent.can_help_with)}

LIBRARY FACTS (these are the ONLY facts you may state about the library):
- The library is called {_lib_name}. This is the ONLY name. Do not use any other name.
- Branches: Main Branch, Elmdale Branch, Jamie Chick Community Annex. Those are the only three.
- Motto: "Everyone belongs at the library"

CRITICAL RULES (follow exactly):
1. The library's name is "{_lib_name}". Never substitute or invent any other name.
2. Do NOT invent branches, programs, hours, fees, statistics, dates, URLs, frameworks, or staff names.
3. If asked something specific you don't know, reply: "I'm not sure — let me check with a colleague and follow up." Never guess.
4. Keep replies to 2-3 short sentences.
5. Stay in character as {agent.name}, {agent.role} in {agent.department}."""
