# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Revenue Summary Schemas ====================


class RevenueByCategoryItem(BaseModel):
    count: int = Field(..., description="Number of fine payments")
    total: float = Field(..., description="Total amount collected")


class PeriodRange(BaseModel):
    start_date: str = Field(..., description="Report start date (ISO format)")
    end_date: str = Field(..., description="Report end date (ISO format)")


class MonthlyBreakdownItem(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    revenue: float = Field(..., description="Revenue for the month")


class RevenueSummaryResponse(BaseModel):
    total_revenue: float = Field(..., description="Total revenue collected")
    by_type: Dict[str, RevenueByCategoryItem] = Field(
        ..., description="Revenue breakdown by fine type"
    )
    monthly_breakdown: List[MonthlyBreakdownItem] = Field(
        ..., description="Monthly revenue breakdown"
    )
    period: PeriodRange = Field(..., description="Report period")


# ==================== Fine Trends Schemas ====================


class DailyDataPoint(BaseModel):
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    collected: float = Field(..., description="Amount collected on this date")
    outstanding: float = Field(..., description="Outstanding balance as of this date")


class FineTrendsResponse(BaseModel):
    daily_data: List[DailyDataPoint] = Field(
        ..., description="Daily collection and outstanding data"
    )
    total_collected: float = Field(..., description="Total collected in period")
    total_outstanding: float = Field(..., description="Total outstanding balance")
    collection_rate: float = Field(..., description="Collection rate (0-1)")
    period_days: int = Field(..., description="Number of days analyzed")


# ==================== Payment Methods Schemas ====================


class PaymentMethodDetail(BaseModel):
    count: int = Field(..., description="Number of payments using this method")
    total: float = Field(..., description="Total amount collected via this method")
    percentage: float = Field(..., description="Percentage of total collected")


class PaymentMethodsResponse(BaseModel):
    payment_methods: Dict[str, PaymentMethodDetail] = Field(
        ..., description="Breakdown by payment method"
    )
    total_collected: float = Field(..., description="Total amount collected")
    period: PeriodRange = Field(..., description="Report period")


# ==================== Waived Fines Schemas ====================


class WaivedFineDetail(BaseModel):
    id: int = Field(..., description="Fine ID")
    patron_id: Optional[int] = Field(None, description="Patron ID")
    fine_type: str = Field(..., description="Type of fine")
    amount: float = Field(..., description="Fine amount waived")
    waived_at: Optional[str] = Field(None, description="Date waived (ISO format)")
    waived_by_id: Optional[int] = Field(None, description="ID of staff who waived")
    notes: Optional[str] = Field(None, description="Reason for waiving")


class WaivedFinesSummary(BaseModel):
    total_waived_count: int = Field(..., description="Total waived fines in period")
    total_waived_amount: float = Field(..., description="Total amount waived")


# TODO(destyle): consolidate with backend/app/schemas/common.py:PaginationInfo when WaivedFinesResponse callers can migrate from {limit,offset,total} to {page,per_page,total,total_pages,has_next,has_previous} shape
class PaginationInfo(BaseModel):
    limit: int = Field(..., description="Records per page")
    offset: int = Field(..., description="Offset for current page")
    total: int = Field(..., description="Total records available")


class WaivedFinesResponse(BaseModel):
    fines: List[WaivedFineDetail] = Field(..., description="List of waived fines")
    summary: WaivedFinesSummary = Field(..., description="Summary statistics")
    pagination: PaginationInfo = Field(..., description="Pagination info")
    period: PeriodRange = Field(..., description="Report period")
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")


# ==================== Outstanding Balances Schemas ====================


class DelinquentAccount(BaseModel):
    patron_id: Optional[int] = Field(None, description="Patron ID")
    patron_name: Optional[str] = Field(None, description="Patron name")
    balance: float = Field(..., description="Remaining balance")
    days_overdue: int = Field(..., description="Days since fine created")


class OutstandingBalancesResponse(BaseModel):
    total_outstanding: float = Field(..., description="Total outstanding balance")
    by_age: Dict[str, float] = Field(..., description="Outstanding balance by age category")
    delinquent_accounts: List[DelinquentAccount] = Field(
        ..., description="Top delinquent accounts by balance"
    )


# ==================== Budget vs Actual Schemas ====================


class BudgetVsActualResponse(BaseModel):
    note: Optional[str] = Field(None, description="Additional notes")
    monthly_actual: Dict[str, float] = Field(
        ..., description="Actual revenue by month"
    )
    year: int = Field(..., description="Year analyzed")


# ==================== Export Response Schemas ====================


class ExportResponse(BaseModel):
    status: str = Field(..., description="Export status")
    format: str = Field(..., description="Export format (csv, json, etc)")
    report_type: str = Field(..., description="Type of report exported")
    generated_at: str = Field(..., description="Timestamp of export")


# ==================== Cache Clear Response ====================


class CacheClearResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Detailed message")
