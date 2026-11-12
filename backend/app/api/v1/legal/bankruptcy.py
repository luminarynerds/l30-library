# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bankruptcy filing search powered by CourtListener / RECAP."""

from typing import Optional
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from ....core.rate_limit import limiter
from ....services.courtlistener_service import (
    CourtListenerService, BankruptcyFiling, BankruptcyCourt
)

router = APIRouter(prefix="/legal/bankruptcy", tags=["legal-bankruptcy"])


class BankruptcyFilingOut(BaseModel):
    docket_id: int
    case_name: str
    docket_number: str
    date_filed: Optional[str] = None
    court_name: str
    court_id: str
    chapter: Optional[str] = None
    trustee: Optional[str] = None
    courtlistener_url: str


class BankruptcyCourtOut(BaseModel):
    id: str
    short_name: str
    full_name: str


class BankruptcySearchResponse(BaseModel):
    filings: list[BankruptcyFilingOut]
    source: str = "CourtListener / RECAP Archive"
    source_url: str = "https://www.courtlistener.com/recap/"


@router.get("/courts", response_model=list[BankruptcyCourtOut])
@limiter.limit("30/minute")
async def list_bankruptcy_courts(request: Request):
    """List all federal bankruptcy courts."""
    service = CourtListenerService()
    courts = await service.get_bankruptcy_courts()
    return [BankruptcyCourtOut(id=c.id, short_name=c.short_name, full_name=c.full_name) for c in courts]


@router.get("/recent", response_model=BankruptcySearchResponse)
@limiter.limit("10/minute")
async def recent_filings(
    request: Request,
    court_id: Optional[str] = Query(None, description="Court code, e.g. 'cacb'"),
    days: int = Query(7, ge=1, le=30, description="Number of days back to search"),
):
    """Get recent bankruptcy filings, optionally filtered by court."""
    service = CourtListenerService()
    filings = await service.get_recent_filings(court_id=court_id, days=days)
    return BankruptcySearchResponse(filings=[BankruptcyFilingOut(**f.model_dump()) for f in filings])


@router.get("/search", response_model=BankruptcySearchResponse)
@limiter.limit("10/minute")
async def search_filings(
    request: Request,
    q: str = Query(..., min_length=2, description="Search by party name or case number"),
    court_id: Optional[str] = Query(None, description="Optional court code filter"),
):
    """Search bankruptcy filings by party name or case number."""
    service = CourtListenerService()
    filings = await service.search_filings(query=q, court_id=court_id)
    return BankruptcySearchResponse(filings=[BankruptcyFilingOut(**f.model_dump()) for f in filings])
