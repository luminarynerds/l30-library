# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public API for homepage quotes (no auth, patron-facing)."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...schemas.homepage_quote import HomepageQuotePublic
from ...services import homepage_quote_service

router = APIRouter(prefix="/homepage-quotes", tags=["homepage-quotes"])


@router.get("", response_model=List[HomepageQuotePublic])
async def list_quotes_for_locale(
    locale: str = Query(..., min_length=2, max_length=8),
    db: AsyncSession = Depends(get_db),
):
    """List active homepage quotes for a given locale.

    Returns empty list when no quotes are configured for the locale -- the
    frontend hides the section entirely rather than falling back to English.
    """
    quotes = await homepage_quote_service.list_active_for_locale(db, locale)
    return [HomepageQuotePublic.model_validate(q) for q in quotes]
