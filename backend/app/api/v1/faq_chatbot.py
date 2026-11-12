# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""FAQ Chatbot API - Smart FAQ handling and patron support."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from app.core.logging import get_logger
from ...models.knowledge_base import (
    FAQChatbotConversation, FAQAnalytics, FAQPattern,
    SeasonalFAQ, PatronChatbotContext, KnowledgeEntry
)
from ...models.notification import Notification, NotificationStatus, NotificationType
from ...models.support_ticket import (
    SupportTicket,
    SupportTicketCategory,
    SupportTicketContactMethod,
    SupportTicketStatus,
)
from ...models.user import User, UserRole
from ...core.pii_redaction import redact_pii
from ...services.faq_chatbot_service import FAQChatbotService
from .auth import get_current_user, get_optional_user
from .dependencies import is_admin, is_staff_or_admin

router = APIRouter(prefix="/faq-chatbot", tags=["faq-chatbot"])


# ============================================================================
# Schemas
# ============================================================================


class ChatbotQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    device_type: str = "web"
    location: str = "homepage"


class ChatbotResponseData(BaseModel):
    id: int
    question: str
    answer: Optional[str] = None
    category: Optional[str] = None
    confidence_score: int  # 0-100
    faq_id: Optional[int] = None
    has_answer: bool  # Whether an FAQ was found
    source_title: Optional[str] = None  # Title of the matched help article (citation)
    source_id: Optional[int] = None  # KnowledgeEntry id the answer came from

    class Config:
        from_attributes = True


class ChatbotFeedbackRequest(BaseModel):
    was_helpful: bool = Field(..., description="Did the patron find the answer helpful?")
    escalate: bool = False


class FAQAnalyticsResponse(BaseModel):
    question_text: str
    ask_count: int
    satisfaction_rate: int
    category: Optional[str] = None
    is_trending: bool
    trend_score: int

    class Config:
        from_attributes = True


class PatronContextResponse(BaseModel):
    last_question: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    total_interactions: int
    questions_resolved_count: int
    questions_escalated_count: int
    current_unresolved_question: Optional[str] = None

    class Config:
        from_attributes = True


class SeasonalFAQResponse(BaseModel):
    id: int
    knowledge_entry_id: int
    season: str
    start_date: str
    end_date: str
    seasonal_note: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# Routes
# ============================================================================


@router.post("/chat", response_model=ChatbotResponseData, status_code=201)
@limiter.limit("10/minute")
async def chat_with_faq(  # noqa: role-check -- public FAQ chat, optional auth
    request: Request,
    payload: ChatbotQuestionRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
) -> ChatbotResponseData:
    """
    Chat with the FAQ chatbot.

    The chatbot:
    - Matches patron questions to FAQs using pattern matching
    - Returns relevant FAQ answers with confidence scores
    - Tracks conversations for analytics
    - Escalates to support if no match found
    """
    # Block patrons whose accounts cannot be used (e.g., minors awaiting
    # parental consent). Mirrors the minor-gating policy used by /ai-tools.
    if user is not None and getattr(user, "requires_parental_consent", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A parent or guardian must give consent before you can use the chatbot.",
        )

    service = FAQChatbotService()
    session_id = str(uuid4())
    question = redact_pii(payload.question)

    # Try to find matching FAQ
    match_result = await service.find_matching_faq(db, question)

    if match_result:
        faq_entry, faq_pattern, confidence = match_result
        has_answer = True
    else:
        faq_entry = None
        faq_pattern = None
        confidence = 0
        has_answer = False

    # Record the conversation
    conversation = await service.record_conversation(
        db=db,
        user_id=user.id if user else None,
        session_id=session_id,
        question=question,
        faq_entry=faq_entry,
        faq_pattern=faq_pattern,
        confidence_score=confidence,
        device_type=payload.device_type,
        location=payload.location
    )

    await db.commit()

    return ChatbotResponseData(
        id=conversation.id,
        question=payload.question,
        answer=faq_entry.content if faq_entry else None,
        category=faq_entry.category if faq_entry else None,
        confidence_score=confidence,
        faq_id=faq_entry.id if faq_entry else None,
        has_answer=has_answer,
        source_title=faq_entry.title if faq_entry else None,
        source_id=faq_entry.id if faq_entry else None,
    )


@router.post("/chat/{conversation_id}/feedback", status_code=204)
async def submit_feedback(  # noqa: role-check -- public FAQ feedback, optional auth
    conversation_id: int,
    feedback: ChatbotFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
) -> None:
    """
    Submit feedback on a chatbot response.

    Helps track which answers are helpful and identify questions
    that need staff attention.
    """
    service = FAQChatbotService()

    await service.record_feedback(
        db=db,
        conversation_id=conversation_id,
        was_helpful=feedback.was_helpful,
        escalated=feedback.escalate
    )

    await db.commit()


@router.get("/trending", response_model=List[dict])
async def get_trending_questions(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Get trending FAQ questions from the last N days.

    Used to identify frequently asked questions and topics
    that patrons struggle with.
    """
    service = FAQChatbotService()
    trending = await service.get_trending_questions(db, days=days, limit=limit)

    return [
        {"question": q, "ask_count": count}
        for q, count in trending
    ]


@router.get("/signage-suggestions", response_model=List[FAQAnalyticsResponse])
async def get_signage_suggestions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> List[FAQAnalyticsResponse]:
    """
    Get questions that should be added to library signage.

    Staff use this to identify which FAQ topics are asked most
    frequently and have the lowest satisfaction rates.
    """
    # Verify staff access
    if not is_staff_or_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    service = FAQChatbotService()
    suggestions = await service.suggest_signage_updates(db)

    return [
        FAQAnalyticsResponse(
            question_text=s.question_text,
            ask_count=s.ask_count,
            satisfaction_rate=s.satisfaction_rate,
            category=s.category,
            is_trending=s.is_trending,
            trend_score=s.trend_score
        )
        for s in suggestions
    ]


@router.get("/patron-context/{patron_id}", response_model=Optional[PatronContextResponse])
async def get_patron_context(
    patron_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> Optional[PatronContextResponse]:
    """
    Get chatbot context for a patron (staff view).

    Helps staff understand if patron already used the chatbot
    and what questions they asked. Shows context like:
    - Total chatbot interactions
    - Questions resolved
    - Current unresolved question
    """
    # Verify staff access
    if not is_staff_or_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    service = FAQChatbotService()
    context = await service.get_patron_context(db, patron_id)

    if not context:
        return None

    return PatronContextResponse(
        last_question=context.last_question,
        last_interaction_at=context.last_interaction_at,
        total_interactions=context.total_interactions,
        questions_resolved_count=context.questions_resolved_count,
        questions_escalated_count=context.questions_escalated_count,
        current_unresolved_question=context.current_unresolved_question
    )


@router.get("/seasonal", response_model=List[SeasonalFAQResponse])
async def get_seasonal_faqs(
    db: AsyncSession = Depends(get_db)
) -> List[SeasonalFAQResponse]:
    """
    Get seasonal FAQs active for the current date.

    Includes temporary FAQs like:
    - Tax form questions (tax season)
    - Summer reading program questions
    - Holiday hours and closures
    """
    service = FAQChatbotService()
    seasonal_faqs = await service.get_seasonal_faqs(db)

    # Get seasonal metadata
    stmt = select(SeasonalFAQ).where(SeasonalFAQ.knowledge_entry_id.in_(
        [f.id for f in seasonal_faqs]
    ))
    result = await db.execute(stmt)
    seasonal_entries = result.scalars().all()

    seasonal_map = {s.knowledge_entry_id: s for s in seasonal_entries}

    return [
        SeasonalFAQResponse(
            id=seasonal_map[f.id].id,
            knowledge_entry_id=f.id,
            season=seasonal_map[f.id].season,
            start_date=seasonal_map[f.id].start_date,
            end_date=seasonal_map[f.id].end_date,
            seasonal_note=seasonal_map[f.id].seasonal_note,
            is_active=seasonal_map[f.id].is_active
        )
        for f in seasonal_faqs
        if f.id in seasonal_map
    ]


@router.post("/patterns", status_code=201)
async def create_faq_pattern(
    faq_id: int = Query(...),
    pattern_text: str = Query(..., min_length=1, max_length=500),
    match_type: str = Query("keyword", pattern="^(exact|keyword|semantic)$"),
    priority: int = Query(1, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> dict:
    """
    Create a new FAQ pattern for question matching.

    Admin staff can define how variations of questions should match.
    Pattern types:
    - exact: Exact text match
    - keyword: Match based on keywords
    - semantic: Semantic similarity (future)
    """
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    # Verify FAQ exists
    stmt = select(KnowledgeEntry).where(KnowledgeEntry.id == faq_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    pattern = FAQPattern(
        knowledge_entry_id=faq_id,
        pattern_text=pattern_text,
        match_type=match_type,
        priority=priority
    )

    db.add(pattern)
    await db.commit()

    return {"id": pattern.id, "created_at": pattern.created_at}


@router.get("/patterns/{faq_id}", response_model=List[dict])
async def get_faq_patterns(
    faq_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """Get all patterns for a specific FAQ."""
    stmt = select(FAQPattern).where(
        FAQPattern.knowledge_entry_id == faq_id
    ).order_by(FAQPattern.priority.desc())

    result = await db.execute(stmt)
    patterns = result.scalars().all()

    return [
        {
            "id": p.id,
            "pattern_text": p.pattern_text,
            "match_type": p.match_type,
            "priority": p.priority,
            "match_count": p.match_count,
            "is_active": p.is_active
        }
        for p in patterns
    ]


@router.get("/analytics/top-questions", response_model=List[FAQAnalyticsResponse])
async def get_top_questions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> List[FAQAnalyticsResponse]:
    """
    Get top asked questions with analytics.

    Shows which questions are asked most frequently and their
    satisfaction rates. Used for identifying improvement areas.
    """
    if not is_staff_or_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    stmt = select(FAQAnalytics).where(
        FAQAnalytics.ask_count > 0
    ).order_by(FAQAnalytics.ask_count.desc()).limit(limit)

    result = await db.execute(stmt)
    analytics = result.scalars().all()

    return [
        FAQAnalyticsResponse(
            question_text=a.question_text,
            ask_count=a.ask_count,
            satisfaction_rate=a.satisfaction_rate,
            category=a.category,
            is_trending=a.is_trending,
            trend_score=a.trend_score
        )
        for a in analytics
    ]


# ============================================================================
# Librarian Handoff
# ============================================================================


class LibrarianHandoffRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    contact_method: str = Field("email", pattern="^(email|phone|in_person)$")
    patron_name: Optional[str] = Field(None, max_length=100)
    conversation_context: List[dict] = Field(default_factory=list)


class LibrarianHandoffResponse(BaseModel):
    success: bool
    message: str
    estimated_wait: str


@router.post("/handoff", response_model=LibrarianHandoffResponse)
async def request_librarian_handoff(  # noqa: role-check -- public librarian handoff request, optional auth
    request: LibrarianHandoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Escalate a chatbot conversation to a librarian.

    Creates a SupportTicket, notifies supervisors in-app, and records the
    escalation on the conversation. The patron's account name/email live only on
    the access-controlled ticket, never in application logs. The free-text message
    is PII-redacted; the raw transcript is summarized to an exchange count.
    """
    # Imported here rather than at module scope to avoid a circular import:
    # both this router and support.py are pulled by the v1 router aggregator.
    from .support import generate_ticket_number, SUPPORT_CATEGORY_ROUTES, _record_event
    from ...models.support_ticket import SupportTicketEventType

    logger = get_logger(__name__)

    redacted_message = redact_pii(request.message)
    exchange_count = len(request.conversation_context)
    issue_description = (
        f"Patron requested a librarian after {exchange_count} help-chat "
        f"exchange(s).\n\nWhat they need help with: {redacted_message}"
    )

    if current_user:
        submitted_name = f"{current_user.first_name} {current_user.last_name}".strip()
        submitted_email = current_user.email
    else:
        submitted_name = request.patron_name
        submitted_email = None

    contact_value = {"email": "email", "phone": "phone", "in_person": "visit"}.get(
        request.contact_method, "email"
    )
    category_value = SupportTicketCategory.REFERENCE.value

    ticket_number = generate_ticket_number()
    ticket = SupportTicket(
        ticket_number=ticket_number,
        name=submitted_name,
        email=submitted_email,
        issue_description=issue_description,
        contact_method=SupportTicketContactMethod(contact_value),
        category=category_value,
        subject_line="Help chat handoff",
        is_anonymous=current_user is None,
        response_route=SUPPORT_CATEGORY_ROUTES.get(category_value),
        status=SupportTicketStatus.OPEN,
    )
    db.add(ticket)
    await db.flush()  # populate ticket.id

    await _record_event(
        db,
        ticket=ticket,
        event_type=SupportTicketEventType.CREATED,
        actor=current_user,
        to_value=ticket_number,
    )

    conversation = FAQChatbotConversation(
        session_id=str(uuid4()),
        user_id=current_user.id if current_user else None,
        original_question=f"[HANDOFF] {redacted_message}",
        confidence_score=0,
        was_helpful=False,
        device_type="web",
        escalated_to_support=True,
        support_ticket_id=ticket.id,
    )
    db.add(conversation)

    supervisor_stmt = select(User).where(
        or_(
            User.role.in_([UserRole.ADMIN, UserRole.DIRECTOR, UserRole.SUPER_ADMIN]),
            (User.role == UserRole.STAFF) & (User.staff_role == "manager"),
        )
    )
    supervisors = (await db.execute(supervisor_stmt)).scalars().all()
    if not supervisors:
        logger.warning(
            "Handoff ticket created with no supervisors to notify",
            extra={"ticket_number": ticket_number},
        )
    for supervisor in supervisors:
        db.add(
            Notification(
                user_id=supervisor.id,
                notification_type=NotificationType.STAFF_HELP_REQUESTED,
                status=NotificationStatus.PENDING,
                subject=f"Help chat handoff — ticket {ticket_number}",
                message=(
                    f"A patron asked for a librarian via the help chat after "
                    f"{exchange_count} exchange(s). See ticket {ticket_number}."
                ),
                context_data={
                    "ticket_number": ticket_number,
                    "ticket_id": ticket.id,
                    "patron_name": submitted_name or "Anonymous",
                },
            )
        )

    await db.commit()

    logger.info(
        "Librarian handoff ticket created",
        extra={"ticket_number": ticket_number, "exchange_count": exchange_count},
    )

    return LibrarianHandoffResponse(
        success=True,
        message="Your request has been sent to our librarians. Someone will follow up with you soon.",
        estimated_wait="Within 1 business day",
    )
