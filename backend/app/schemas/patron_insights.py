# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class InsightsSummary(BaseModel):
    total_books_this_year: int = 0
    total_books_all_time: int = 0
    avg_books_per_month: float = 0.0
    favorite_genre: Optional[str] = None
    current_streak_days: int = 0
    total_reading_minutes: int = 0
    unique_authors: int = 0


class GenreCount(BaseModel):
    genre: str
    count: int
    percentage: float


class GenreBreakdownResponse(BaseModel):
    genres: List[GenreCount] = []
    year: int


class MonthlyCount(BaseModel):
    month: str
    count: int
    year: int
    month_num: int


class VelocityResponse(BaseModel):
    months: List[MonthlyCount] = []


class DailyActivity(BaseModel):
    date: str
    count: int


class HeatmapResponse(BaseModel):
    days: List[DailyActivity] = []
    year: int
    total_active_days: int = 0


class YearInReviewResponse(BaseModel):
    year: int
    total_books: int = 0
    total_authors: int = 0
    favorite_genre: Optional[str] = None
    longest_streak: int = 0
    busiest_month: Optional[str] = None
    total_pages_estimated: int = 0
    genres_explored: int = 0
    top_genres: List[GenreCount] = []
    monthly_breakdown: List[MonthlyCount] = []
