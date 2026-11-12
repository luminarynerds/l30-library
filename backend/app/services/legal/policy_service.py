# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.error_codes import ErrorCode
from ...core.exceptions import ResourceNotFoundError

from ...models.legal import (
    FormFinderWizardSession, FormFinderQuestion, FormFinderRule,
    WizardSessionStatus, KnowYourRightsGuide, EmergencyResource,
    LegalContentFeedback, LegalResourceStatistics, LegalSearchLog,
    LegalCollection
)

logger = get_logger(__name__)


# ============================================================================
# Form Finder Wizard Services
# ============================================================================

async def start_wizard_session(
    db: AsyncSession,
    patron_id: Optional[int] = None
) -> FormFinderWizardSession:
    session_token = secrets.token_urlsafe(32)

    session = FormFinderWizardSession(
        session_token=session_token,
        patron_id=patron_id,
        status=WizardSessionStatus.in_progress,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_wizard_session(
    db: AsyncSession,
    session_token: str
) -> Optional[FormFinderWizardSession]:
    result = await db.execute(
        select(FormFinderWizardSession)
        .where(FormFinderWizardSession.session_token == session_token)
    )
    return result.scalar_one_or_none()


async def get_wizard_question(
    db: AsyncSession,
    slug: str
) -> Optional[FormFinderQuestion]:
    result = await db.execute(
        select(FormFinderQuestion)
        .where(
            FormFinderQuestion.slug == slug,
            FormFinderQuestion.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def get_first_wizard_question(
    db: AsyncSession
) -> Optional[FormFinderQuestion]:
    result = await db.execute(
        select(FormFinderQuestion)
        .where(FormFinderQuestion.is_active == True)
        .order_by(FormFinderQuestion.display_order)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def submit_wizard_answer(
    db: AsyncSession,
    session_token: str,
    question_slug: str,
    answer: str | list[str]
) -> FormFinderWizardSession:
    session = await get_wizard_session(db, session_token)
    if not session:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Wizard session not found"
        )

    # Update answers
    answers = session.answers or {}
    answers[question_slug] = answer
    session.answers = answers

    # Get current question to determine next
    question = await get_wizard_question(db, question_slug)
    if question and question.branching:
        # Determine next question based on branching logic
        answer_key = answer if isinstance(answer, str) else answer[0]
        next_slug = question.branching.get(answer_key) or question.branching.get("default")
        session.current_step = next_slug

    await db.commit()
    await db.refresh(session)
    return session


async def complete_wizard(
    db: AsyncSession,
    session_token: str
) -> FormFinderWizardSession:
    session = await get_wizard_session(db, session_token)
    if not session:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Wizard session not found"
        )

    # Apply rules to determine recommendations
    recommendations = await _apply_wizard_rules(db, session.answers)

    session.recommended_form_ids = recommendations.get("form_ids", [])
    session.recommended_packet_ids = recommendations.get("packet_ids", [])
    session.recommended_guide_ids = recommendations.get("guide_ids", [])
    session.jurisdiction_state = recommendations.get("jurisdiction_state")
    session.jurisdiction_county = recommendations.get("jurisdiction_county")
    session.court_type_determined = recommendations.get("court_type")
    session.status = WizardSessionStatus.completed
    session.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    return session


async def _apply_wizard_rules(
    db: AsyncSession,
    answers: dict
) -> dict:
    result = await db.execute(
        select(FormFinderRule)
        .where(FormFinderRule.is_active == True)
        .order_by(FormFinderRule.priority.desc())
    )
    rules = result.scalars().all()

    form_ids = []
    packet_ids = []
    guide_ids = []
    jurisdiction_state = None
    jurisdiction_county = None
    court_type = None

    for rule in rules:
        if _rule_matches(rule.conditions, answers):
            form_ids.extend(rule.form_ids or [])
            packet_ids.extend(rule.packet_ids or [])
            guide_ids.extend(rule.guide_ids or [])

    # Extract jurisdiction from answers
    if "state" in answers:
        jurisdiction_state = answers["state"]
    if "county" in answers:
        jurisdiction_county = answers["county"]
    if "court_type" in answers:
        court_type = answers["court_type"]

    return {
        "form_ids": list(set(form_ids)),
        "packet_ids": list(set(packet_ids)),
        "guide_ids": list(set(guide_ids)),
        "jurisdiction_state": jurisdiction_state,
        "jurisdiction_county": jurisdiction_county,
        "court_type": court_type
    }


def _rule_matches(conditions: list[dict], answers: dict) -> bool:
    for condition in conditions:
        question_slug = condition.get("question_slug")
        operator = condition.get("operator", "equals")
        value = condition.get("value")

        answer = answers.get(question_slug)
        if answer is None:
            return False

        if operator == "equals":
            if answer != value:
                return False
        elif operator == "contains":
            if isinstance(answer, list):
                if value not in answer:
                    return False
            elif value not in answer:
                return False
        elif operator == "in":
            if answer not in value:
                return False

    return True


async def refer_to_help(
    db: AsyncSession,
    session_token: str,
    reason: str
) -> FormFinderWizardSession:
    session = await get_wizard_session(db, session_token)
    if not session:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Wizard session not found"
        )

    session.status = WizardSessionStatus.referred_to_help
    session.referred_to_help = True
    session.referral_reason = reason
    session.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    return session


# ============================================================================
# Know Your Rights Services
# ============================================================================

async def get_know_your_rights_guide(
    db: AsyncSession,
    slug: str
) -> Optional[KnowYourRightsGuide]:
    result = await db.execute(
        select(KnowYourRightsGuide)
        .where(
            KnowYourRightsGuide.slug == slug,
            KnowYourRightsGuide.is_published == True
        )
    )
    return result.scalar_one_or_none()


async def list_know_your_rights_guides(
    db: AsyncSession,
    situation: Optional[str] = None,
    language: Optional[str] = None,
    is_published: bool = True,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[KnowYourRightsGuide], int]:
    base_query = select(KnowYourRightsGuide)
    count_query = select(func.count(KnowYourRightsGuide.id))

    filters = [KnowYourRightsGuide.is_published == is_published]
    if situation:
        filters.append(KnowYourRightsGuide.situation == situation)
    if language:
        filters.append(KnowYourRightsGuide.languages_available.any(language))

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(KnowYourRightsGuide.title)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    guides = result.scalars().all()

    return guides, total


# ============================================================================
# Emergency Resources Services
# ============================================================================

async def list_emergency_resources(
    db: AsyncSession,
    situation: Optional[str] = None,
    resource_type: Optional[str] = None,
    is_featured: Optional[bool] = None
) -> list[EmergencyResource]:
    query = select(EmergencyResource).where(EmergencyResource.is_active == True)

    if situation:
        query = query.where(EmergencyResource.situation == situation)
    if resource_type:
        query = query.where(EmergencyResource.resource_type == resource_type)
    if is_featured is not None:
        query = query.where(EmergencyResource.is_featured == is_featured)

    query = query.order_by(EmergencyResource.display_order, EmergencyResource.name)
    result = await db.execute(query)
    return result.scalars().all()


# ============================================================================
# Content Feedback Services
# ============================================================================

async def submit_feedback(
    db: AsyncSession,
    feedback_data: dict,
    session_token: Optional[str] = None
) -> LegalContentFeedback:
    feedback = LegalContentFeedback(
        **feedback_data,
        session_token=session_token
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def list_feedback(
    db: AsyncSession,
    content_type: Optional[str] = None,
    content_id: Optional[int] = None,
    feedback_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalContentFeedback], int]:
    base_query = select(LegalContentFeedback)
    count_query = select(func.count(LegalContentFeedback.id))

    filters = []
    if content_type:
        filters.append(LegalContentFeedback.content_type == content_type)
    if content_id:
        filters.append(LegalContentFeedback.content_id == content_id)
    if feedback_type:
        filters.append(LegalContentFeedback.feedback_type == feedback_type)
    if resolved is not None:
        filters.append(LegalContentFeedback.resolved == resolved)

    if filters:
        base_query = base_query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalContentFeedback.id.desc())
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    feedback = result.scalars().all()

    return feedback, total


# ============================================================================
# Legal Collection Services
# ============================================================================

async def list_collections(
    db: AsyncSession,
    situation: Optional[str] = None,
    complexity_level: Optional[str] = None,
    fee_waiver_available: Optional[bool] = None,
    estimated_cost_max: Optional[float] = None,
    language: Optional[str] = None,
    is_published: bool = True,
    is_featured: Optional[bool] = None,
    search_query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "featured",
) -> tuple[list[LegalCollection], int]:
    query = select(LegalCollection)
    count_query = select(func.count(LegalCollection.id))

    # Apply filters
    filters = [LegalCollection.is_published == is_published]
    if situation:
        filters.append(LegalCollection.situation == situation)
    if is_featured is not None:
        filters.append(LegalCollection.is_featured == is_featured)
    if complexity_level:
        filters.append(LegalCollection.complexity_level == complexity_level)
    if fee_waiver_available is not None:
        filters.append(LegalCollection.fee_waiver_available == fee_waiver_available)
    if estimated_cost_max is not None:
        filters.append(LegalCollection.estimated_cost_max <= estimated_cost_max)
    if language:
        # available_languages is JSONB (not ARRAY) — .any() AttributeErrors;
        # JSONB containment is the correct filter for a JSON array of strings.
        filters.append(LegalCollection.available_languages.contains([language]))
    if search_query:
        safe_q = search_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(
            LegalCollection.title.ilike(f"%{safe_q}%")
            | LegalCollection.description.ilike(f"%{safe_q}%")
        )

    query = query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get paginated results
    if sort_by == "alphabetical":
        query = query.order_by(LegalCollection.title)
    elif sort_by == "newest":
        query = query.order_by(LegalCollection.created_at.desc())
    else:
        query = query.order_by(
            LegalCollection.is_featured.desc(),
            LegalCollection.display_order,
            LegalCollection.created_at.desc()
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    collections = result.scalars().all()

    return collections, total


async def get_collection_by_id(
    db: AsyncSession,
    collection_id: int
) -> Optional[LegalCollection]:
    result = await db.execute(
        select(LegalCollection).where(LegalCollection.id == collection_id)
    )
    return result.scalar_one_or_none()


async def get_collection_by_slug(
    db: AsyncSession,
    slug: str
) -> Optional[LegalCollection]:
    result = await db.execute(
        select(LegalCollection).where(LegalCollection.slug == slug)
    )
    return result.scalar_one_or_none()


async def create_collection(
    db: AsyncSession,
    collection_data: dict,
    created_by_id: Optional[int] = None
) -> LegalCollection:
    collection = LegalCollection(
        **collection_data,
        created_by_id=created_by_id
    )
    db.add(collection)
    await db.flush()
    return collection


async def update_collection(
    db: AsyncSession,
    collection_id: int,
    update_data: dict
) -> Optional[LegalCollection]:
    collection = await get_collection_by_id(db, collection_id)
    if not collection:
        return None

    for key, value in update_data.items():
        if value is not None:
            setattr(collection, key, value)

    collection.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return collection


async def increment_collection_views(
    db: AsyncSession,
    collection_id: int
) -> None:
    collection = await get_collection_by_id(db, collection_id)
    if collection:
        collection.view_count = (collection.view_count or 0) + 1
        collection.updated_at = datetime.now(timezone.utc)
        await db.flush()


async def record_collection_click(
    db: AsyncSession,
    collection_id: int
) -> None:
    collection = await get_collection_by_id(db, collection_id)
    if collection:
        collection.click_through_count = (collection.click_through_count or 0) + 1
        collection.updated_at = datetime.now(timezone.utc)
        await db.flush()


async def record_collection_helpful(
    db: AsyncSession,
    collection_id: int,
    was_helpful: bool
) -> None:
    collection = await get_collection_by_id(db, collection_id)
    if collection:
        if was_helpful:
            collection.helpful_count = (collection.helpful_count or 0) + 1
        else:
            collection.unhelpful_count = (collection.unhelpful_count or 0) + 1
        collection.updated_at = datetime.now(timezone.utc)
        await db.flush()
