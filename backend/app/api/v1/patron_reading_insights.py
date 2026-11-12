# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Reading Insights API Endpoints

Provides patron-facing reading analytics: summary stats, genre breakdown,
reading velocity, activity heatmap, and year-in-review.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.patron_insights import (
    InsightsSummary,
    GenreBreakdownResponse,
    VelocityResponse,
    HeatmapResponse,
    YearInReviewResponse,
)
from app.services.patron_reading_insights_service import PatronReadingInsightsService
from .auth import get_current_user

router = APIRouter(prefix="/reading/insights", tags=["Reading Insights"])


@router.get("/summary", response_model=InsightsSummary)
async def get_reading_summary(current_user=Depends(get_current_user)):
    """Get reading summary statistics for the current patron."""
    return await PatronReadingInsightsService.get_summary(user_id=current_user.id)


@router.get("/genre-breakdown", response_model=GenreBreakdownResponse)
async def get_genre_breakdown(year: Optional[int] = Query(None), current_user=Depends(get_current_user)):
    """Get genre breakdown from checkout history."""
    return await PatronReadingInsightsService.get_genre_breakdown(user_id=current_user.id, year=year)


@router.get("/velocity", response_model=VelocityResponse)
async def get_reading_velocity(months: int = Query(12, ge=1, le=36), current_user=Depends(get_current_user)):
    """Get monthly reading velocity."""
    return await PatronReadingInsightsService.get_velocity(user_id=current_user.id, months=months)


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_activity_heatmap(year: Optional[int] = Query(None), current_user=Depends(get_current_user)):
    """Get daily activity heatmap for the specified year."""
    return await PatronReadingInsightsService.get_heatmap(user_id=current_user.id, year=year)


@router.get("/year-in-review", response_model=YearInReviewResponse)
async def get_year_in_review(year: Optional[int] = Query(None), current_user=Depends(get_current_user)):
    """Get compiled year-in-review data."""
    return await PatronReadingInsightsService.get_year_in_review(user_id=current_user.id, year=year)
