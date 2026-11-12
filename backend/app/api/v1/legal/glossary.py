# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal terminology glossary.

This module handles legal glossary terms including listing,
viewing, and CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalGlossaryTermCreate, LegalGlossaryTermUpdate,
    LegalGlossaryTermResponse, LegalGlossaryListResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-documents"])


# ============================================================================
# Legal Glossary
# ============================================================================

@router.get("/glossary", response_model=LegalGlossaryListResponse)
async def list_glossary_terms(
    query: Optional[str] = Query(None, description="Search terms"),
    letter: Optional[str] = Query(None, description="Filter by first letter"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List legal glossary terms.

    Includes plain language definitions and pronunciation guides.
    """
    terms, total = await legal_service.list_glossary_terms(
        db, query=query, letter=letter, skip=offset, limit=limit
    )
    return paginated_response(
        key="terms",
        items=terms,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_glossary_to_summary,
    )


@router.get("/glossary/{slug}", response_model=LegalGlossaryTermResponse)
async def get_glossary_term(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a glossary term definition.

    Includes simple definition, standard definition, and legal definition.
    """
    term = require_resource(
        await legal_service.get_glossary_term(db, slug),
        message="Glossary term not found",
    )
    return _glossary_to_response(term)


@router.post("/glossary", response_model=LegalGlossaryTermResponse, status_code=status.HTTP_201_CREATED)
async def create_glossary_term(
    term_data: LegalGlossaryTermCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new glossary term. Requires staff access."""
    term = await legal_service.create_glossary_term(db, term_data.model_dump())
    return _glossary_to_response(term)


# ============================================================================
# Helper Functions
# ============================================================================

def _glossary_to_summary(term) -> dict:
    return {
        "id": term.id,
        "term": term.term,
        "slug": term.slug,
        "definition_standard": term.definition_standard,
        "is_active": term.is_active
    }


def _glossary_to_response(term) -> dict:
    return {
        "id": term.id,
        "term": term.term,
        "slug": term.slug,
        "definition_simple": term.definition_simple,
        "definition_standard": term.definition_standard,
        "definition_legal": term.definition_legal,
        "pronunciation": term.pronunciation,
        "pronunciation_audio_url": term.pronunciation_audio_url,
        "related_term_slugs": term.related_term_slugs or [],
        "see_also": term.see_also or [],
        "usage_example": term.usage_example,
        "context_notes": term.context_notes,
        "translations": term.translations or {},
        "translated_definitions": term.translated_definitions or {},
        "topic_ids": term.topic_ids or [],
        "is_active": term.is_active,
        "view_count": term.view_count,
        "created_at": getattr(term, "created_at", None),
        "updated_at": getattr(term, "updated_at", None)
    }
