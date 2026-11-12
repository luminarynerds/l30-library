# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, timedelta
from collections import Counter, defaultdict
from typing import Optional

from app.schemas.patron_insights import (
    InsightsSummary,
    GenreBreakdownResponse,
    GenreCount,
    VelocityResponse,
    MonthlyCount,
    HeatmapResponse,
    DailyActivity,
    YearInReviewResponse,
)


class PatronReadingInsightsService:

    @staticmethod
    async def get_summary(user_id: int, db=None) -> InsightsSummary:
        # In production, this would query the database
        # For now, return a structured response that the frontend can consume
        return InsightsSummary(
            total_books_this_year=0,
            total_books_all_time=0,
            avg_books_per_month=0.0,
            favorite_genre=None,
            current_streak_days=0,
            total_reading_minutes=0,
            unique_authors=0,
        )

    @staticmethod
    async def get_genre_breakdown(
        user_id: int, year: Optional[int] = None, db=None
    ) -> GenreBreakdownResponse:
        target_year = year or date.today().year
        return GenreBreakdownResponse(genres=[], year=target_year)

    @staticmethod
    async def get_velocity(
        user_id: int, months: int = 12, db=None
    ) -> VelocityResponse:
        result_months = []
        today = date.today()
        for i in range(months - 1, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            result_months.append(
                MonthlyCount(
                    month=month_date.strftime("%b %Y"),
                    count=0,
                    year=month_date.year,
                    month_num=month_date.month,
                )
            )
        return VelocityResponse(months=result_months)

    @staticmethod
    async def get_heatmap(
        user_id: int, year: Optional[int] = None, db=None
    ) -> HeatmapResponse:
        target_year = year or date.today().year
        return HeatmapResponse(days=[], year=target_year, total_active_days=0)

    @staticmethod
    async def get_year_in_review(
        user_id: int, year: Optional[int] = None, db=None
    ) -> YearInReviewResponse:
        target_year = year or (date.today().year - 1)
        return YearInReviewResponse(
            year=target_year,
            total_books=0,
            total_authors=0,
            favorite_genre=None,
            longest_streak=0,
            busiest_month=None,
            total_pages_estimated=0,
            genres_explored=0,
            top_genres=[],
            monthly_breakdown=[],
        )
