# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Financial Reports API Endpoints

Provides comprehensive financial reporting and analytics including:
- Revenue summary by category
- Fine collection trends
- Payment method analysis
- Waived fine tracking
- Outstanding balance aging reports
- Budget vs actual analysis
- Export capabilities (CSV, JSON)
"""

from app.core.logging import get_logger
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import Request, APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from ...schemas.financial_reports import (
    RevenueSummaryResponse,
    FineTrendsResponse,
    PaymentMethodsResponse,
    WaivedFinesResponse,
    OutstandingBalancesResponse,
    BudgetVsActualResponse,
    ExportResponse,
)
from ...services.financial_reports_service import FinancialReportsService
from .dependencies import require_admin
from .auth import get_current_user

router = APIRouter(prefix="/financial", tags=["financial-reports"])
logger = get_logger(__name__)


def _build_export_trust_headers(
    report_type: str,
    export_format: str,
    generated_at: datetime,
    payload_bytes: bytes,
) -> dict[str, str]:
    return {
        "X-Report-Type": report_type,
        "X-Report-Format": export_format,
        "X-Report-Generated-At": generated_at.isoformat(),
        "X-Report-SHA256": hashlib.sha256(payload_bytes).hexdigest(),
    }


@router.get("/reports/revenue-summary", response_model=RevenueSummaryResponse)
@limiter.limit("10/minute")
async def get_revenue_summary(
     request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    use_cache: bool = Query(True, description="Use cached results"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> RevenueSummaryResponse:
    """
    Get revenue summary with breakdown by fine type.

    Returns total revenue, count by type, and monthly breakdown.

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        # Parse dates if provided
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        service = FinancialReportsService(db)
        data = await service.get_revenue_summary(start, end, use_cache)

        return RevenueSummaryResponse(**data)
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD).",
        ) from e
    except Exception as e:
        logger.error(f"Error getting revenue summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate revenue summary",
        ) from e


@router.get("/reports/fine-trends", response_model=FineTrendsResponse)
@limiter.limit("10/minute")
async def get_fine_trends(
    request: Request,
    days: int = Query(90, ge=1, le=365, description="Number of days to analyze"),
    use_cache: bool = Query(True, description="Use cached results"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FineTrendsResponse:
    """
    Get fine collection trends over specified period.

    Returns daily collection data and outstanding balance trends.

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_fine_trends(days, use_cache)
        return FineTrendsResponse(**data)
    except Exception as e:
        logger.error(f"Error getting fine trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate fine trends",
        ) from e


@router.get("/reports/payment-methods", response_model=PaymentMethodsResponse)
@limiter.limit("10/minute")
async def get_payment_methods(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    use_cache: bool = Query(True, description="Use cached results"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PaymentMethodsResponse:
    """
    Get payment method usage analysis.

    Returns breakdown of fine payments by method (cash, card, check, online, etc.)
    with counts and percentages.

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        service = FinancialReportsService(db)
        data = await service.get_payment_methods(start, end, use_cache)
        return PaymentMethodsResponse(**data)
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD).",
        ) from e
    except Exception as e:
        logger.error(f"Error getting payment methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate payment methods report",
        ) from e


@router.get("/reports/waived-fines", response_model=WaivedFinesResponse)
@limiter.limit("10/minute")
async def get_waived_fines(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WaivedFinesResponse:
    """
    Get waived and adjusted fines report.

    Returns detailed list of waived fines with information about who waived them
    and why (from notes).

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        service = FinancialReportsService(db)
        data = await service.get_waived_fines(start, end, limit, offset)

        # Check for test/automated waivers that may skew totals
        fines_data = data.get("fines", [])
        test_waivers = [
            f for f in fines_data
            if f.get("notes") and (
                "test" in f["notes"].lower() or "automated" in f["notes"].lower()
            )
        ]
        warnings = []
        if test_waivers:
            warnings.append(
                f"{len(test_waivers)} fines appear to be from automated testing and may skew totals."
            )

        data["warnings"] = warnings
        return WaivedFinesResponse(**data)
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD).",
        ) from e
    except Exception as e:
        logger.error(f"Error getting waived fines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate waived fines report",
        ) from e


@router.get("/reports/outstanding-balances", response_model=OutstandingBalancesResponse)
@limiter.limit("10/minute")
async def get_outstanding_balances(
    request: Request,
    minimum_balance: float = Query(
        0.01,
        ge=0,
        description="Minimum balance to include (filters out amounts < this)",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OutstandingBalancesResponse:
    """
    Get aging report for outstanding fine balances.

    Categorizes unpaid fines by age:
    - Current (0-30 days)
    - 31-60 days
    - 61-90 days
    - 90+ days

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_outstanding_balances(
            Decimal(str(minimum_balance)), limit, offset
        )
        return OutstandingBalancesResponse(**data)
    except Exception as e:
        logger.error(f"Error getting outstanding balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate outstanding balances report",
        ) from e


@router.get("/reports/budget-vs-actual", response_model=BudgetVsActualResponse)
@limiter.limit("10/minute")
async def get_budget_vs_actual(
    request: Request,
    year: Optional[int] = Query(None, description="Year to analyze"),
    use_cache: bool = Query(True, description="Use cached results"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BudgetVsActualResponse:
    """
    Get budget vs actual revenue analysis.

    Returns monthly actual revenue data. Budget data can be configured
    in the database when budget tracking is implemented.

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_budget_vs_actual(year, use_cache)
        return BudgetVsActualResponse(**data)
    except Exception as e:
        logger.error(f"Error getting budget vs actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate budget vs actual report",
        ) from e


@router.get("/reports/export/{report_type}")
@limiter.limit("5/minute")
async def export_report(
    request: Request,
    report_type: str = Path(..., description="Type of report to export"),
    format: str = Query("csv", pattern="^(csv|json|pdf|excel)$", description="Export format (csv, json, pdf, excel)"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export financial report in CSV, JSON, PDF, or Excel format.

    Supported report types:
    - revenue_summary
    - payment_methods
    - outstanding_balances
    - fine_trends

    **Access**: Admin only

    **Rate limit**: 5 requests/minute
    """
    valid_reports = [
        "revenue_summary",
        "payment_methods",
        "outstanding_balances",
        "fine_trends",
    ]

    if report_type not in valid_reports:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Valid options: {', '.join(valid_reports)}",
        )

    try:

        start = None
        end = None
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        generated_at = datetime.now(timezone.utc)

        # For PDF and Excel, delegate to the unified ReportFactory
        if format in ("pdf", "excel"):
            from ...services.reports.base import OutputFormat, ReportFilters
            from ...services.reports.factory import ReportFactory, ReportType

            output_fmt = OutputFormat.PDF if format == "pdf" else OutputFormat.EXCEL
            filters = ReportFilters(start_date=start, end_date=end)
            factory = ReportFactory(db)
            result_bytes = await factory.generate(
                ReportType.FINANCIAL, filters, output_fmt, use_cache=False,
            )

            ext = "pdf" if format == "pdf" else "xlsx"
            media = "application/pdf" if format == "pdf" else (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"financial_{report_type}_{generated_at.strftime('%Y%m%d_%H%M%S')}.{ext}"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                **_build_export_trust_headers(report_type, format, generated_at, result_bytes),
            }
            return StreamingResponse(
                iter([result_bytes]),
                media_type=media,
                headers=headers,
            )

        # Legacy CSV/JSON paths preserved for backwards compatibility
        service = FinancialReportsService(db)

        if format == "csv":
            csv_content = await service.export_to_csv(report_type, start, end)
            csv_bytes = csv_content.encode("utf-8")
            filename = f"{report_type}_{generated_at.strftime('%Y%m%d_%H%M%S')}.csv"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                **_build_export_trust_headers(report_type, format, generated_at, csv_bytes),
            }

            return StreamingResponse(
                iter([csv_content]),
                media_type="text/csv",
                headers=headers,
            )
        else:  # JSON format
            if report_type == "revenue_summary":
                data = await service.get_revenue_summary(start, end, use_cache=False)
            elif report_type == "payment_methods":
                data = await service.get_payment_methods(start, end, use_cache=False)
            elif report_type == "outstanding_balances":
                data = await service.get_outstanding_balances(limit=10000)
            else:  # fine_trends
                data = await service.get_fine_trends(90, use_cache=False)

            canonical_json = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
            return {
                "report_type": report_type,
                "generated_at": generated_at.isoformat(),
                "data": data,
                "trust": {
                    "sha256": hashlib.sha256(canonical_json).hexdigest(),
                    "hash_scope": "data",
                },
            }

    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD).",
        ) from e
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export report",
        ) from e


@router.post("/cache/clear")
@limiter.limit("5/minute")
async def clear_cache(
    request: Request,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Clear the financial reports cache.

    This forces fresh data generation on next report request.

    **Access**: Admin only

    **Rate limit**: 5 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        await service.clear_cache()
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache",
        ) from e


@router.get("/board/dashboard-summary")
@limiter.limit("10/minute")
async def get_board_dashboard_summary(
    request: Request,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get comprehensive board treasurer dashboard summary.

    Returns key metrics including:
    - Total revenue collected
    - Outstanding balances
    - Collection rate
    - Budget status
    - Fund allocations
    - Acquisition spending

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)

        # Get all required data in parallel
        revenue = await service.get_revenue_summary(None, None, use_cache=True)
        trends = await service.get_fine_trends(90, use_cache=True)
        balances = await service.get_outstanding_balances(Decimal("0.01"))
        budget = await service.get_budget_vs_actual(None, use_cache=True)

        return {
            "total_revenue": revenue.get("total_revenue", 0),
            "total_collected": trends.get("total_collected", 0),
            "total_outstanding": trends.get("total_outstanding", 0),
            "collection_rate": trends.get("collection_rate", 0),
            "collection_rate_percentage": (trends.get("collection_rate", 0) * 100),
            "outstanding_balance": balances.get("total_outstanding", 0),
            "delinquent_count": len(balances.get("delinquent_accounts", [])),
            "budget_variance": budget.get("variance_percentage", 0),
            "budget_variance_percentage": (budget.get("variance_percentage", 0) * 100),
        }
    except Exception as e:
        logger.error(f"Error getting board dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard summary",
        ) from e


@router.get("/board/funds")
@limiter.limit("10/minute")
async def get_board_funds(
    request: Request,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get board fund balances and allocations.

    Returns information about:
    - Available funds
    - Fund allocations
    - Spending by fund
    - Fund balances

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_fund_overview()
        return data
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting board funds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get fund information",
        ) from e


@router.get("/board/acquisition-spending")
@limiter.limit("10/minute")
async def get_acquisition_spending(
    request: Request,
    year: Optional[int] = Query(None, description="Year to analyze"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get acquisition spending analysis by category and vendor.

    Returns:
    - Total spending by category
    - Top vendors
    - Spending trends
    - Budget utilization

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_acquisition_spending(year)
        return data
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting acquisition spending: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get acquisition spending data",
        ) from e


@router.get("/board/financial-health")
@limiter.limit("10/minute")
async def get_financial_health(
    request: Request,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get overall financial health metrics.

    Returns health indicators including:
    - Cash flow status
    - Liquidity ratios
    - Days sales outstanding
    - Collection effectiveness
    - Fund utilization rates

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        data = await service.get_financial_health_metrics()

        # Build contextual recommendations based on health indicators
        recommendations = []
        health_score = data.get("overall_health_score", 0)
        if health_score < 50:
            recommendations.append(
                "Collection effectiveness is below 50%. Consider reviewing fine policies or implementing payment plans."
            )

        delinquency_data = data.get("delinquency_status", {})
        accounts_90_plus = delinquency_data.get("accounts_90_plus_days", 0)
        if accounts_90_plus > 0:
            recommendations.append(
                f"{accounts_90_plus} accounts are 90+ days delinquent. Consider sending to collections or writing off."
            )

        cash_flow = data.get("cash_flow_status", {})
        collected_total = cash_flow.get("collected", 0)
        outstanding_total = cash_flow.get("outstanding", 0)
        if outstanding_total > collected_total and collected_total > 0:
            recommendations.append(
                "Outstanding balance exceeds collected amount. Review collection procedures."
            )

        data["recommendations"] = recommendations
        return data
    except Exception as e:
        logger.error(f"Error getting financial health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get financial health metrics",
        ) from e


@router.post("/board/reports/monthly/generate")
@limiter.limit("5/minute")
async def generate_monthly_report(
    request: Request,
    year: int = Query(..., ge=2000, le=2100, description="Year for the report"),
    month: int = Query(..., ge=1, le=12, description="Month for the report (1-12)"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate a comprehensive monthly financial report.

    Creates a monthly report including:
    - Revenue and collections summary
    - Budget vs actual analysis
    - Fund utilization
    - Acquisition spending
    - Delinquency report
    - Key metrics and health indicators

    **Access**: Admin only

    **Rate limit**: 5 requests/minute
    """
    try:
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12",
            )

        service = FinancialReportsService(db)
        report_id = await service.generate_monthly_report(year, month)

        return {
            "status": "success",
            "report_id": report_id,
            "year": year,
            "month": month,
            "message": f"Monthly report for {year}-{month:02d} generated successfully",
        }
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate monthly report",
        ) from e


@router.get("/board/reports/monthly")
@limiter.limit("10/minute")
async def list_monthly_reports(
    request: Request,
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by year"),
    limit: int = Query(12, ge=1, le=120, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List available monthly financial reports.

    Returns list of generated monthly reports with metadata including:
    - Report ID and date
    - Year and month
    - File size and download link
    - Generation timestamp

    **Access**: Admin only

    **Rate limit**: 10 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        reports = await service.list_monthly_reports(year, limit, offset)
        return {
            "reports": reports,
            "total_count": len(reports),
            "limit": limit,
            "offset": offset,
        }
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error listing monthly reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list monthly reports",
        ) from e


@router.get("/board/reports/monthly/{report_id}/download")
@limiter.limit("5/minute")
async def download_monthly_report(
    request: Request,
    report_id: str = Path(..., description="ID of the report to download"),
    format: str = Query("pdf", pattern="^(pdf|csv|json)$", description="Download format"),
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Download a monthly financial report.

    Downloads the report in the specified format (PDF, CSV, or JSON).

    **Access**: Admin only

    **Rate limit**: 5 requests/minute
    """
    try:
        service = FinancialReportsService(db)
        content = await service.get_monthly_report(report_id, format)

        if format == "pdf":
            return StreamingResponse(
                iter([content]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=monthly_report_{report_id}.pdf"},
            )
        elif format == "csv":
            return StreamingResponse(
                iter([content]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=monthly_report_{report_id}.csv"},
            )
        else:  # JSON
            return content
    except ValueError as e:
        logger.warning(f"Invalid report format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report format",
        ) from e
    except Exception as e:
        logger.error(f"Error downloading monthly report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download monthly report",
        ) from e
