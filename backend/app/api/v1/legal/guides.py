# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal guide content.

This module handles step-by-step legal guides, Know Your Rights guides,
and staff guidelines for legal resource assistance.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.content_i18n import translated
from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalGuideCreate, LegalGuideUpdate, LegalGuideResponse,
    LegalGuideSummaryResponse, LegalGuideListResponse,
    KnowYourRightsGuideResponse, KnowYourRightsListResponse,
    LegalStaffGuidelineResponse,
    LegalContentFeedbackCreate, LegalContentFeedbackResponse,
    LegalDisclaimerResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-resources"])


# ============================================================================
# Standard Disclaimer (required on every response)
# ============================================================================

LEGAL_DISCLAIMER = {
    "disclaimer_text": (
        "IMPORTANT: This is legal INFORMATION, not legal ADVICE. "
        "Using these resources does not create an attorney-client relationship. "
        "Laws change frequently - verify current requirements with the court. "
        "Complex legal situations require consultation with a licensed attorney. "
        "The library is not responsible for outcomes based on this information. "
        "For emergency situations, call 911 or contact the appropriate crisis line."
    ),
    "emergency_contacts": [
        {"name": "Emergency Services", "phone": "911", "description": "Life-threatening emergencies"},
        {"name": "National Domestic Violence Hotline", "phone": "1-800-799-7233", "is_24_7": True},
        {"name": "National Crisis Line", "phone": "988", "is_24_7": True},
    ],
    "quick_exit_enabled": True
}


@router.get("/disclaimer", response_model=LegalDisclaimerResponse)
async def get_disclaimer():
    """Get the standard legal disclaimer for all legal resource pages."""
    return LEGAL_DISCLAIMER


# ============================================================================
# Legal Topics
# ============================================================================

from ....schemas.legal import (
    LegalTopicCreate, LegalTopicUpdate, LegalTopicResponse,
    LegalTopicTreeResponse, LegalTopicListResponse,
)


@router.get("/topics", response_model=LegalTopicListResponse)
async def list_topics(
    parent_id: Optional[int] = Query(None, description="Filter by parent topic ID"),
    is_active: bool = Query(True, description="Filter by active status"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    lang: Optional[str] = Query(None, max_length=10),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List legal topics with optional filtering.

    By default returns root-level topics (no parent).
    Set parent_id to get children of a specific topic.
    """
    topics, total = await legal_service.list_topics(
        db, parent_id=parent_id, is_active=is_active,
        is_featured=is_featured, skip=offset, limit=limit
    )
    return paginated_response(
        key="topics",
        items=topics,
        total=total,
        limit=limit,
        offset=offset,
        mapper=lambda t: _topic_to_response(t, lang),
    )


@router.get("/topics/tree", response_model=list[LegalTopicTreeResponse])
async def get_topic_tree(
    is_active: bool = Query(True),
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Get the complete hierarchical topic tree."""
    topics = await legal_service.get_topic_tree(db, is_active=is_active)
    return [_topic_to_tree_response(t, lang) for t in topics]


@router.get("/topics/{topic_id}", response_model=LegalTopicResponse)
async def get_topic(
    topic_id: int,
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific legal topic by ID."""
    topic = require_resource(
        await legal_service.get_topic_by_id(db, topic_id),
        message="Legal topic not found",
    )

    # Increment view count (async, non-blocking)
    await legal_service.increment_topic_views(db, topic_id)

    return _topic_to_response(topic, lang)


@router.get("/topics/slug/{slug}", response_model=LegalTopicResponse)
async def get_topic_by_slug(
    slug: str,
    lang: Optional[str] = Query(None, max_length=10),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific legal topic by slug."""
    topic = require_resource(
        await legal_service.get_topic_by_slug(db, slug),
        message="Legal topic not found",
    )

    await legal_service.increment_topic_views(db, topic.id)
    return _topic_to_response(topic, lang)


@router.post("/topics", response_model=LegalTopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic_data: LegalTopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new legal topic. Requires staff access."""
    topic = await legal_service.create_topic(
        db, topic_data.model_dump(), created_by_id=current_user.id
    )
    return _topic_to_response(topic)


@router.patch("/topics/{topic_id}", response_model=LegalTopicResponse)
async def update_topic(
    topic_id: int,
    topic_data: LegalTopicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a legal topic. Requires staff access."""
    topic = await legal_service.update_topic(
        db, topic_id, topic_data.model_dump(exclude_unset=True)
    )
    return _topic_to_response(topic)


# ============================================================================
# Legal Guides
# ============================================================================

@router.get("/guides", response_model=LegalGuideListResponse)
async def list_guides(
    topic_id: Optional[int] = Query(None),
    is_featured: Optional[bool] = Query(None),
    reading_level: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List step-by-step legal guides.

    Guides are written at an 8th grade reading level by default
    and include flowcharts, timelines, and printable checklists.
    """
    guides, total = await legal_service.list_guides(
        db, topic_id=topic_id, is_featured=is_featured,
        reading_level=reading_level, skip=offset, limit=limit
    )
    return paginated_response(
        key="guides",
        items=guides,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_guide_to_summary,
    )


@router.get("/guides/{guide_id}", response_model=LegalGuideResponse)
async def get_guide(
    guide_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a complete step-by-step legal guide.

    Includes all steps, timelines, cost breakdowns, common scenarios,
    and guidance on when an attorney is needed.
    """
    guide = require_resource(
        await legal_service.get_guide_by_id(db, guide_id),
        message="Legal guide not found",
    )
    return _guide_to_response(guide)


@router.get("/guides/slug/{slug}", response_model=LegalGuideResponse)
async def get_guide_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a legal guide by its URL slug."""
    guide = require_resource(
        await legal_service.get_guide_by_slug(db, slug),
        message="Legal guide not found",
    )
    return _guide_to_response(guide)


@router.post("/guides/{guide_id}/helpful")
async def record_guide_feedback(
    guide_id: int,
    was_helpful: bool = Query(..., description="Was this guide helpful?"),
    db: AsyncSession = Depends(get_db)
):
    """Record whether a guide was helpful (anonymous feedback)."""
    await legal_service.record_guide_helpful(db, guide_id, was_helpful)
    return {"status": "recorded"}


@router.get("/guides/{guide_id}/helpful")
async def get_guide_helpful_stats(
    guide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get helpfulness ratings for a legal guide."""
    guide = require_resource(
        await legal_service.get_guide_by_id(db, guide_id),
        message="Legal guide not found",
    )

    return {
        "guide_id": guide.id,
        "title": guide.title,
        "total_ratings": guide.helpful_count + guide.not_helpful_count if hasattr(guide, 'helpful_count') else 0,
        "helpful_count": getattr(guide, 'helpful_count', 0),
        "not_helpful_count": getattr(guide, 'not_helpful_count', 0),
        "helpfulness_percentage": round(
            (getattr(guide, 'helpful_count', 0) / (getattr(guide, 'helpful_count', 0) + getattr(guide, 'not_helpful_count', 1))) * 100
        ) if (getattr(guide, 'helpful_count', 0) + getattr(guide, 'not_helpful_count', 0)) > 0 else 0,
        "rating_help_text": "Help us improve by rating if this guide was helpful"
    }


@router.post("/guides", response_model=LegalGuideResponse, status_code=status.HTTP_201_CREATED)
async def create_guide(
    guide_data: LegalGuideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new legal guide. Requires staff access."""
    guide = await legal_service.create_guide(
        db, guide_data.model_dump(), created_by_id=current_user.id
    )
    return _guide_to_response(guide)


@router.patch("/guides/{guide_id}", response_model=LegalGuideResponse)
async def update_guide(
    guide_id: int,
    guide_data: LegalGuideUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a legal guide. Requires staff access."""
    guide = await legal_service.update_guide(
        db, guide_id, guide_data.model_dump(exclude_unset=True),
        updated_by_id=current_user.id
    )
    return _guide_to_response(guide)


@router.post("/guides/{guide_id}/publish", response_model=LegalGuideResponse)
async def publish_guide(
    guide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish a legal guide. Requires staff access."""
    guide = await legal_service.publish_guide(
        db, guide_id, published_by_id=current_user.id
    )
    return _guide_to_response(guide)


@router.get("/guides/{guide_id}/publish")
async def get_guide_publish_status(
    guide_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get publication status and history for a legal guide."""
    guide = require_resource(
        await legal_service.get_guide_by_id(db, guide_id),
        message="Legal guide not found",
    )

    return {
        "guide_id": guide.id,
        "title": guide.title,
        "is_published": getattr(guide, 'is_published', False),
        "published_at": getattr(guide, 'published_at', None),
        "published_by_id": getattr(guide, 'published_by_id', None),
        "draft_content": not getattr(guide, 'is_published', False),
        "visibility": "published" if getattr(guide, 'is_published', False) else "draft",
        "staff_only": True,
        "publication_help": "POST to /guides/{guide_id}/publish to publish this guide"
    }


# ============================================================================
# Know Your Rights
# ============================================================================

@router.get("/know-your-rights", response_model=KnowYourRightsListResponse)
async def list_know_your_rights_guides(
    situation: Optional[str] = Query(None, description="Filter by situation type"),
    language: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List Know Your Rights guides.

    Guides cover situations like police encounters, ICE encounters,
    landlord disputes, and debt collection.
    """
    guides, total = await legal_service.list_know_your_rights_guides(
        db, situation=situation, language=language, skip=offset, limit=limit
    )
    return paginated_response(
        key="guides",
        items=guides,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_kyr_to_summary,
    )


@router.get("/know-your-rights/{slug}", response_model=KnowYourRightsGuideResponse)
async def get_know_your_rights_guide(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a Know Your Rights guide.

    Includes key rights, do's and don'ts, scripts for what to say,
    and printable wallet cards.
    """
    guide = require_resource(
        await legal_service.get_know_your_rights_guide(db, slug),
        message="Know Your Rights guide not found",
    )
    return _kyr_to_response(guide)


# ============================================================================
# Content Feedback
# ============================================================================

@router.post("/feedback", response_model=LegalContentFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: LegalContentFeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback on legal content.

    Help us improve by reporting outdated information, broken links,
    or suggesting new content.
    """
    feedback = await legal_service.submit_feedback(db, feedback_data.model_dump())
    return _feedback_to_response(feedback)


@router.get("/feedback")
async def list_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    content_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List feedback submissions about legal content (staff only)."""
    feedback_items, total = await legal_service.list_feedback(
        db, content_type=content_type, resolved=resolved,
        skip=offset, limit=limit
    )

    title_map = await _resolve_content_titles(db, feedback_items)

    def mapper(fb):
        resp = _feedback_to_response(fb)
        resp["content_title"] = title_map.get((fb.content_type, fb.content_id))
        return resp

    return paginated_response(
        key="feedback",
        items=feedback_items,
        total=total,
        limit=limit,
        offset=offset,
        mapper=mapper,
    )


# ============================================================================
# Staff Guidelines (Staff Only)
# ============================================================================

@router.get("/staff/guidelines", response_model=list[LegalStaffGuidelineResponse])
async def list_staff_guidelines(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List staff guidelines for legal resource assistance.

    Includes what staff CAN and CANNOT do, scripts, and referral guidance.
    """
    guidelines = await legal_service.list_staff_guidelines(db, category=category)
    return [_guideline_to_response(g) for g in guidelines]


@router.get("/staff/guidelines/{slug}", response_model=LegalStaffGuidelineResponse)
async def get_staff_guideline(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific staff guideline."""
    guideline = require_resource(
        await legal_service.get_staff_guideline(db, slug),
        message="Staff guideline not found",
    )
    return _guideline_to_response(guideline)


# ============================================================================
# Helper Functions
# ============================================================================


async def _resolve_content_titles(
    db: AsyncSession,
    feedback_items: list,
) -> dict[tuple[str, int], str]:
    from ....models.legal import LegalGuide
    from sqlalchemy import select as sa_select

    guide_ids = {fb.content_id for fb in feedback_items if fb.content_type == "guide"}
    title_map: dict[tuple[str, int], str] = {}

    if guide_ids:
        result = await db.execute(
            sa_select(LegalGuide.id, LegalGuide.title).where(
                LegalGuide.id.in_(guide_ids)
            )
        )
        for row in result:
            title_map[("guide", row.id)] = row.title

    return title_map


# ============================================================================

def _topic_to_response(topic, lang: Optional[str] = None) -> dict:
    return {
        "id": topic.id,
        "name": translated(topic, "name", lang),
        "slug": topic.slug,
        "description": translated(topic, "description", lang),
        "parent_id": topic.parent_id,
        "display_order": topic.display_order,
        "icon": topic.icon,
        "color": topic.color,
        "is_active": topic.is_active,
        "is_featured": topic.is_featured,
        "keywords": topic.keywords or [],
        "meta_description": topic.meta_description,
        "related_resources": topic.related_resources or [],
        "view_count": topic.view_count,
        "created_at": getattr(topic, "created_at", None),
        "updated_at": getattr(topic, "updated_at", None),
        "created_by_id": topic.created_by_id
    }


def _topic_to_tree_response(topic, lang: Optional[str] = None) -> dict:
    response = _topic_to_response(topic, lang)
    response["children"] = [_topic_to_tree_response(c, lang) for c in topic.children]
    return response


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


def _guide_to_response(guide) -> dict:
    return {
        "id": guide.id,
        "title": guide.title,
        "slug": guide.slug,
        "topic_id": guide.topic_id,
        "summary": guide.summary,
        "content": guide.content,
        "reading_level": guide.reading_level,
        "steps": guide.steps or [],
        "related_form_ids": guide.related_form_ids or [],
        "related_guide_ids": guide.related_guide_ids or [],
        "related_resource_urls": guide.related_resource_urls or [],
        "flowchart_data": guide.flowchart_data,
        "flowchart_image_url": guide.flowchart_image_url,
        "timeline_description": guide.timeline_description,
        "cost_breakdown": guide.cost_breakdown or [],
        "common_scenarios": guide.common_scenarios or [],
        "when_need_lawyer": guide.when_need_lawyer,
        "complexity_warning_signs": guide.complexity_warning_signs or [],
        "video_url": guide.video_url,
        "video_transcript": guide.video_transcript,
        "printable_checklist": guide.printable_checklist or [],
        "languages_available": guide.languages_available or ["English"],
        "is_published": guide.is_published,
        "is_featured": guide.is_featured,
        "view_count": guide.view_count,
        "helpful_count": guide.helpful_count,
        "not_helpful_count": guide.not_helpful_count,
        "created_at": getattr(guide, "created_at", None),
        "updated_at": getattr(guide, "updated_at", None),
        "published_at": guide.published_at,
        "created_by_id": guide.created_by_id,
        "last_reviewed_at": guide.last_reviewed_at,
        "last_reviewed_by_id": guide.last_reviewed_by_id,
        "topic_name": guide.topic.name if guide.topic else None
    }


def _kyr_to_summary(guide) -> dict:
    return {
        "id": guide.id,
        "title": guide.title,
        "slug": guide.slug,
        "situation": guide.situation,
        "summary": guide.summary,
        "languages_available": guide.languages_available or ["English"],
        "is_published": guide.is_published
    }


def _kyr_to_response(guide) -> dict:
    return {
        "id": guide.id,
        "title": guide.title,
        "slug": guide.slug,
        "situation": guide.situation,
        "summary": guide.summary,
        "content": guide.content,
        "key_rights": guide.key_rights or [],
        "dos": guide.dos or [],
        "donts": guide.donts or [],
        "scripts": guide.scripts or [],
        "when_silent": guide.when_silent,
        "documentation_tips": guide.documentation_tips or [],
        "emergency_contacts": guide.emergency_contacts or [],
        "wallet_card_content": guide.wallet_card_content,
        "wallet_card_pdf_url": guide.wallet_card_pdf_url,
        "video_url": guide.video_url,
        "languages_available": guide.languages_available or ["English"],
        "is_published": guide.is_published,
        "view_count": guide.view_count
    }


def _feedback_to_response(feedback) -> dict:
    return {
        "id": feedback.id,
        "content_type": feedback.content_type,
        "content_id": feedback.content_id,
        "feedback_type": feedback.feedback_type,
        "was_helpful": feedback.was_helpful,
        "comments": feedback.comments,
        "staff_reviewed": feedback.staff_reviewed,
        "resolved": feedback.resolved,
        "created_at": getattr(feedback, "created_at", None)
    }


def _guideline_to_response(guideline) -> dict:
    return {
        "id": guideline.id,
        "title": guideline.title,
        "slug": guideline.slug,
        "category": guideline.category,
        "content": guideline.content,
        "can_do_examples": guideline.can_do_examples or [],
        "cannot_do_examples": guideline.cannot_do_examples or [],
        "scripts": guideline.scripts or [],
        "referral_tree": guideline.referral_tree,
        "is_active": guideline.is_active
    }
