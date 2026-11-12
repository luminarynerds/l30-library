# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal form library and downloads.

This module handles individual legal form management including
listing, searching, viewing, downloading, and CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalFormCreate, LegalFormUpdate, LegalFormResponse,
    LegalFormSummaryResponse, LegalFormListResponse, LegalFormSearchRequest,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-forms"])


# ============================================================================
# Legal Forms
# ============================================================================

@router.get("/forms", response_model=LegalFormListResponse)
async def list_forms(
    topic_id: Optional[int] = Query(None, description="Filter by topic"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    court_type: Optional[str] = Query(None, description="Filter by court type"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    language: Optional[str] = Query(None, description="Filter by available language"),
    query: Optional[str] = Query(None, description="Search forms"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List legal forms with filtering and search.

    Forms are returned with plain language descriptions to help
    users understand which form they need.
    """
    forms, total = await legal_service.list_forms(
        db, topic_id=topic_id, jurisdiction=jurisdiction,
        court_type=court_type, difficulty_level=difficulty_level,
        language=language, query=query, skip=offset, limit=limit
    )
    return paginated_response(
        key="forms",
        items=forms,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_form_to_summary,
    )


@router.post("/forms/search", response_model=LegalFormListResponse)
async def search_forms(
    search_request: LegalFormSearchRequest,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for legal forms by keyword.

    Searches form titles, numbers, descriptions, and "when to use" content.
    Search queries are logged anonymously for content improvement.
    """
    forms, total = await legal_service.search_forms(
        db, search_request.query,
        filters=search_request.model_dump(exclude={"query"}, exclude_none=True),
        skip=offset, limit=limit
    )
    return paginated_response(
        key="forms",
        items=forms,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_form_to_summary,
    )


@router.get("/forms/search")
async def get_forms_search(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get information about the forms search feature and how to use it."""
    return {
        "description": "Search for legal forms by keyword and filters",
        "search_fields": [
            "title", "form_number", "description", "when_to_use",
            "who_should_use", "plain_language_title"
        ],
        "available_filters": [
            "jurisdiction", "court_type", "difficulty_level", "language",
            "topic_id", "category", "has_fee", "fillable"
        ],
        "pagination": {
            "default_limit": 20,
            "max_limit": 100
        },
        "sorting_options": ["relevance", "difficulty", "filing_fee", "title"],
        "help": "Use POST /forms/search with a query to search for forms"
    }


@router.get("/forms/{form_id}", response_model=LegalFormResponse)
async def get_form(
    form_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a legal form.

    Includes plain language descriptions, filing fees, instructions,
    and field-by-field help where available.
    """
    form = require_resource(
        await legal_service.get_form_by_id(db, form_id),
        message="Legal form not found",
    )

    await legal_service.increment_form_views(db, form_id)
    return _form_to_response(form)


@router.post("/forms/{form_id}/download")
async def track_form_download(
    form_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Track a form download for analytics."""
    await legal_service.increment_form_downloads(db, form_id)
    return {"status": "recorded"}


@router.get("/forms/{form_id}/download")
async def get_forms__form_id__download(
    form_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get download information for a specific form."""
    form = require_resource(
        await legal_service.get_form_by_id(db, form_id),
        message="Legal form not found",
    )

    download_info = {
        "form_id": form.id,
        "form_number": form.form_number,
        "title": form.title,
        "download_options": {
            "fillable": form.fillable_pdf,
            "download_url": form.url,
            "instructions_url": form.instructions_url,
            "example_url": form.example_url
        },
        "accessibility_options": {
            "screen_reader_friendly": form.screen_reader_friendly,
            "large_print_available": form.large_print_available
        },
        "languages_available": form.languages_available or ["English"],
        "file_size_note": "File sizes vary - check browser download",
        "free_to_download": True
    }
    return download_info


@router.post("/forms", response_model=LegalFormResponse, status_code=status.HTTP_201_CREATED)
async def create_form(
    form_data: LegalFormCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new legal form. Requires staff access."""
    form = await legal_service.create_form(
        db, form_data.model_dump(), created_by_id=current_user.id
    )
    return _form_to_response(form)


@router.patch("/forms/{form_id}", response_model=LegalFormResponse)
async def update_form(
    form_id: int,
    form_data: LegalFormUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a legal form. Requires staff access."""
    form = await legal_service.update_form(
        db, form_id, form_data.model_dump(exclude_unset=True),
        updated_by_id=current_user.id
    )
    return _form_to_response(form)


# ============================================================================
# Helper Functions
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


def _form_to_response(form) -> dict:
    return {
        "id": form.id,
        "title": form.title,
        "form_number": form.form_number,
        "topic_id": form.topic_id,
        "category": form.category,
        "subcategory": form.subcategory,
        "jurisdiction": form.jurisdiction,
        "jurisdiction_code": form.jurisdiction_code,
        "court_type": form.court_type,
        "court_name": form.court_name,
        "description": form.description,
        "when_to_use": form.when_to_use,
        "who_should_use": form.who_should_use,
        "plain_language_title": form.plain_language_title,
        "form_url": getattr(form, "form_url", None) or form.url,
        "instructions_url": form.instructions_url,
        "example_url": form.example_url,
        "page_count": form.page_count,
        "filing_fee": form.filing_fee,
        "fee_waiver_form_id": form.fee_waiver_form_id,
        "difficulty_level": form.difficulty_level,
        "estimated_completion_time": form.estimated_completion_time,
        "notarization_required": form.notarization_required,
        "signature_requirements": form.signature_requirements,
        "languages_available": form.languages_available or ["English"],
        "screen_reader_friendly": form.screen_reader_friendly,
        "large_print_available": form.large_print_available,
        "fillable_pdf": form.fillable_pdf,
        "version": form.version,
        "effective_date": form.effective_date,
        "last_updated": form.last_updated,
        "change_notes": form.change_notes,
        "status": form.status,
        "superseded_by_id": form.superseded_by_id,
        "related_form_ids": form.related_form_ids or [],
        "common_mistakes": form.common_mistakes or [],
        "tips": form.tips or [],
        "field_help": form.field_help or {},
        "download_count": form.download_count,
        "view_count": form.view_count,
        "created_at": getattr(form, "created_at", None),
        "updated_at": getattr(form, "updated_at", None),
        "created_by_id": form.created_by_id,
        "last_reviewed_at": form.last_reviewed_at,
        "last_reviewed_by_id": form.last_reviewed_by_id,
        "topic_name": form.topic.name if form.topic else None
    }
