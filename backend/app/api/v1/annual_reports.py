# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
State Annual Reports API.

Provides endpoints for generating, retrieving, validating, and exporting
state-required annual reports with pre-populated statistical data.

Features:
- Automatic data aggregation from all library modules
- State-specific data requirements and validation
- Multi-format export (PDF, Excel, XML)
- Year-over-year comparison functionality
- Audit trail and change tracking
"""

import io
import json
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import xml.etree.ElementTree as ET
from xml.dom import minidom

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.annual_report import AnnualReport, ReportStatus
from ...models.user import User
from ...schemas.annual_report_finance import FinanceEntry, FinanceEntryResponse
from ...schemas.annual_report_ecirc import (
    ElectronicCirculationEntry,
    ElectronicCirculationResponse,
)
from ...services.annual_report_service import AnnualReportService
from ...services.annual_report_validation import sums_match, validate
from .auth import get_current_user
from .dependencies import check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/annual-reports", tags=["annual-reports"])


def _status_str(s) -> str:
    return s.value if hasattr(s, 'value') else str(s) if s else "draft"


def _money(value) -> float:
    """Quantize a money value to cents and return it as a JSON number.

    JSONB finance breakdowns are display values read as numbers by the
    exporters/frontend; storing ``float(Decimal)`` directly can drift pennies on
    large budgets, so quantize to two decimal places before the float cast.
    """
    return float(Decimal(str(value)).quantize(Decimal("0.01")))


# ==========================================
# Schema Classes
# ==========================================

class AnnualReportBase(BaseModel):

    fiscal_year: int = Field(..., ge=2000, le=2099)
    state_code: str = Field(..., min_length=2, max_length=2)
    library_name: str = Field(..., min_length=1)
    library_id: Optional[str] = None


class AnnualReportCreate(AnnualReportBase):
    pass



class AnnualReportResponse(AnnualReportBase):

    id: int
    status: str
    is_validated: bool
    total_checkouts: Optional[int]
    total_registered_patrons: Optional[int]
    total_programs_offered: Optional[int]
    generated_at: str
    last_modified_at: Optional[str] = None


class ReportListItem(BaseModel):

    id: int
    fiscal_year: int
    state_code: str
    library_name: str
    status: str
    is_validated: bool
    generated_at: str
    submitted_to_state_at: Optional[str] = None


class ReportListResponse(BaseModel):

    reports: List[ReportListItem]
    count: int


# ==========================================
# REPORT GENERATION
# ==========================================

@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate Annual Report",
    description="Generate a comprehensive annual report for a fiscal year with all statistical fields pre-populated.",
    response_model=AnnualReportResponse,
)
@limiter.limit("10/hour")
async def generate_annual_report(
    request: Request,
    fiscal_year: int = Query(..., ge=2000, le=2099, description="Fiscal year (e.g., 2025)"),
    state_code: str = Query(..., min_length=2, max_length=2, description="State code (e.g., CA, TX)"),
    library_name: str = Query(..., min_length=1, description="Library name"),
    library_id: Optional[str] = Query(None, description="Optional state library ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnualReportResponse:
    """
    Generate a comprehensive state annual report.

    Aggregates data from all library modules:
    - Circulation statistics (checkouts, renewals, holds)
    - Patron registration and demographics
    - Program attendance and events
    - Collection size and acquisitions
    - Financial figures from budget module
    - Staff FTE calculations
    - Hours open calculations
    - Building square footage
    - Technology counts
    - Visitor statistics and reference questions

    Returns pre-populated report with all statistical fields calculated.
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)

        # Generate the report
        report = await service.generate_annual_report(
            fiscal_year=fiscal_year,
            state_code=state_code,
            library_name=library_name,
            library_id=library_id,
            user_id=current_user.id,
        )

        logger.info(f"Annual report generated: ID {report.id}, FY{fiscal_year}, {state_code}")

        return {
            "id": report.id,
            "fiscal_year": report.fiscal_year,
            "state_code": report.state_code,
            "library_name": report.library_name,
            "status": _status_str(report.status),
            "is_validated": report.is_validated,
            "total_checkouts": report.total_checkouts,
            "total_registered_patrons": report.total_registered_patrons,
            "total_programs_offered": report.total_programs_offered,
            "generated_at": report.generated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate annual report",
        ) from e


# ==========================================
# REPORT RETRIEVAL
# ==========================================

@router.get(
    "/{report_id}",
    summary="Get Annual Report",
    description="Retrieve a specific annual report by ID.",
)
@limiter.limit("30/minute")
async def get_annual_report(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Retrieve a specific annual report with all data fields.

    Returns complete report including:
    - All statistical fields
    - Validation status and errors
    - Year-over-year comparisons
    - Export file paths
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        report = await service.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        return {
            "id": report.id,
            "fiscal_year": report.fiscal_year,
            "state_code": report.state_code,
            "library_name": report.library_name,
            "library_id": report.library_id,
            "status": _status_str(report.status),
            "is_validated": report.is_validated,
            "validation_errors": report.validation_errors,
            # Circulation
            "total_checkouts": report.total_checkouts,
            "total_renewals": report.total_renewals,
            "total_returns": report.total_returns,
            "checkouts_by_item_type": report.checkouts_by_item_type,
            "total_holds_placed": report.total_holds_placed,
            "total_holds_filled": report.total_holds_filled,
            "collection_turnover_rate": float(report.collection_turnover_rate) if report.collection_turnover_rate else None,
            # Patron
            "total_registered_patrons": report.total_registered_patrons,
            "active_patrons": report.active_patrons,
            "new_patrons_registered": report.new_patrons_registered,
            "patrons_by_age_group": report.patrons_by_age_group,
            "resident_patrons": report.resident_patrons,
            "non_resident_patrons": report.non_resident_patrons,
            # Collection
            "total_items_owned": report.total_items_owned,
            "total_titles_owned": report.total_titles_owned,
            "items_by_format": report.items_by_format,
            "items_added_during_year": report.items_added_during_year,
            "items_withdrawn_during_year": report.items_withdrawn_during_year,
            "electronic_titles": report.electronic_titles,
            "total_collection_value": float(report.total_collection_value) if report.total_collection_value else None,
            # Programs
            "total_programs_offered": report.total_programs_offered,
            "total_program_attendance": report.total_program_attendance,
            "avg_attendance_per_program": float(report.avg_attendance_per_program) if report.avg_attendance_per_program else None,
            # Facility
            "total_hours_open_per_year": report.total_hours_open_per_year,
            "days_open_per_week": report.days_open_per_week,
            "building_square_footage": report.building_square_footage,
            "number_of_locations": report.number_of_locations,
            # Technology
            "public_computer_stations": report.public_computer_stations,
            "wifi_enabled": report.wifi_enabled,
            # Financial
            "total_operating_revenue": float(report.total_operating_revenue) if report.total_operating_revenue else None,
            "total_operating_expenditure": float(report.total_operating_expenditure) if report.total_operating_expenditure else None,
            "personnel_expenditure": float(report.personnel_expenditure) if report.personnel_expenditure else None,
            # Staff
            "total_staff_fte": float(report.total_staff_fte) if report.total_staff_fte else None,
            # Visitor
            "total_library_visits": report.total_library_visits,
            "reference_questions_answered": report.reference_questions_answered,
            # Year-over-year
            "checkout_growth_percent": float(report.checkout_growth_percent) if report.checkout_growth_percent else None,
            "patron_growth_percent": float(report.patron_growth_percent) if report.patron_growth_percent else None,
            "visit_growth_percent": float(report.visit_growth_percent) if report.visit_growth_percent else None,
            # Website traffic (Umami)
            "website_traffic": (report.additional_metrics or {}).get("website_traffic"),
            "generated_at": report.generated_at.isoformat(),
            "last_modified_at": report.last_modified_at.isoformat() if report.last_modified_at else None,
            "submitted_to_state_at": report.submitted_to_state_at.isoformat() if report.submitted_to_state_at else None,
            "submission_status": report.submission_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve annual report",
        ) from e


# ==========================================
# REPORT LISTING
# ==========================================

@router.get(
    "",
    summary="List Annual Reports",
    description="List annual reports with optional filtering by fiscal year or state code.",
    response_model=ReportListResponse,
)
@limiter.limit("30/minute")
async def list_annual_reports(
    request: Request,
    fiscal_year: Optional[int] = Query(None, description="Filter by fiscal year"),
    state_code: Optional[str] = Query(None, description="Filter by state code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    """
    List annual reports.

    Optional filters:
    - `fiscal_year`: Filter by fiscal year
    - `state_code`: Filter by state code
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        reports = await service.list_reports(
            fiscal_year=fiscal_year,
            state_code=state_code,
        )

        return {
            "reports": [
                {
                    "id": r.id,
                    "fiscal_year": r.fiscal_year,
                    "state_code": r.state_code,
                    "library_name": r.library_name,
                    "status": _status_str(r.status),
                    "is_validated": r.is_validated,
                    "generated_at": r.generated_at.isoformat(),
                    "submitted_to_state_at": r.submitted_to_state_at.isoformat() if r.submitted_to_state_at else None,
                }
                for r in reports
            ],
            "count": len(reports),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing annual reports: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list annual reports",
        ) from e


# ==========================================
# VALIDATION
# ==========================================

@router.post(
    "/{report_id}/validate",
    summary="Validate Annual Report",
    description="Validate an annual report against state-specific data requirements.",
)
@limiter.limit("30/minute")
async def validate_annual_report(
    request: Request,
    report_id: int,
    state_code: Optional[str] = Query(None, description="Override state code for validation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate an annual report.

    Checks all required fields against state-specific validation rules.
    Returns validation status and any errors.
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        is_valid, errors = await service.validate_report(report_id, state_code)

        return {
            "report_id": report_id,
            "is_valid": is_valid,
            "errors": errors,
            "error_count": len(errors),
        }

    except Exception as e:
        logger.error(f"Error validating annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate annual report",
        ) from e


# ==========================================
# DIRECTOR FINANCE ENTRY
# ==========================================

@router.patch(
    "/{report_id}/finance",
    summary="Enter Director Finance",
    description="Manually enter PLS finance (operating revenue/expenditure + capital). "
    "Lines must reconcile to their totals; tags the report's finance as director-entered.",
    response_model=FinanceEntryResponse,
)
@limiter.limit("30/minute")
async def enter_annual_report_finance(
    request: Request,
    report_id: int,
    payload: FinanceEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinanceEntryResponse:
    """Persist director-entered finance, tagging the financial data source manual."""
    try:
        check_staff_access(current_user)

        report = await db.get(AnnualReport, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        rev = payload.revenue
        exp = payload.expenditure

        # Lines must reconcile to their totals (same arithmetic the validator uses).
        if not sums_match(
            payload.total_operating_revenue,
            [rev.local, rev.state, rev.federal, rev.other],
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Revenue lines do not sum to total operating revenue.",
            )
        if not sums_match(
            payload.total_operating_expenditure,
            [exp.salaries, exp.benefits, exp.print, exp.electronic, exp.other],
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expenditure lines do not sum to total operating expenditure.",
            )

        # Capital revenue lines (when supplied) must reconcile to capital outlay.
        if payload.capital_revenue is not None:
            cap = payload.capital_revenue
            if not sums_match(
                payload.capital_outlay,
                [cap.local, cap.state, cap.federal, cap.other],
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Capital revenue lines do not sum to capital outlay.",
                )

        # JSONB columns hold display breakdowns; the Numeric columns are authoritative.
        # Quantize each breakdown value to cents so large budgets don't float-drift
        # pennies; kept as JSON numbers (exporters/frontend read them as numbers).
        report.total_operating_revenue = payload.total_operating_revenue
        report.revenue_by_source = {
            "local": _money(rev.local),
            "state": _money(rev.state),
            "federal": _money(rev.federal),
            "other": _money(rev.other),
        }
        report.total_operating_expenditure = payload.total_operating_expenditure
        report.expenditure_by_category = {
            "salaries": _money(exp.salaries),
            "benefits": _money(exp.benefits),
            "print": _money(exp.print),
            "electronic": _money(exp.electronic),
            "other": _money(exp.other),
        }
        # Roll the PLS lines into the columns the report/exports already display.
        report.personnel_expenditure = exp.salaries + exp.benefits
        report.collection_expenditure = exp.print + exp.electronic
        report.other_expenditure = exp.other

        report.capital_outlay = payload.capital_outlay
        if payload.capital_revenue is not None:
            cap = payload.capital_revenue
            report.capital_revenue = {
                "local": _money(cap.local),
                "state": _money(cap.state),
                "federal": _money(cap.federal),
                "other": _money(cap.other),
            }

        # First-class, audited provenance columns (the PLS completeness gate).
        report.finance_source = "manual"
        report.finance_entered_at = datetime.now(timezone.utc)
        report.finance_entered_by_id = current_user.id

        # Keep the legacy JSONB tag for display back-compat (reassign so
        # SQLAlchemy tracks the JSONB change).
        data_sources = dict(report.data_sources or {})
        data_sources["financial"] = "manual"
        report.data_sources = data_sources

        report.last_modified_by_id = current_user.id

        await db.flush()
        logger.info(f"Finance entered for annual report {report_id} by user {current_user.id}")

        return FinanceEntryResponse(
            report_id=report.id,
            total_operating_revenue=report.total_operating_revenue,
            total_operating_expenditure=report.total_operating_expenditure,
            capital_outlay=report.capital_outlay,
            data_source="manual",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error entering finance for annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enter annual report finance",
        ) from e


@router.patch(
    "/{report_id}/electronic-circulation",
    summary="Enter Third-Party Electronic Circulation",
    description="Manually enter third-party e-platform circulation (OverDrive/Libby, "
    "Hoopla, e-audio, ...) per platform. The total is folded into the PLS-reported "
    "electronic_circulation and total_circulation. Idempotent: repeated calls replace "
    "rather than accumulate.",
    response_model=ElectronicCirculationResponse,
)
@limiter.limit("30/minute")
async def enter_annual_report_electronic_circulation(
    request: Request,
    report_id: int,
    payload: ElectronicCirculationEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ElectronicCirculationResponse:
    """Persist third-party e-circ and fold it into the PLS electronic/total figures."""
    try:
        check_staff_access(current_user)

        report = await db.get(AnnualReport, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        by_platform = dict(payload.by_platform)
        new_tp = sum(by_platform.values())

        # Recover the native (non-third-party) figures by subtracting the prior
        # third-party amount, so repeated PATCHes replace rather than accumulate.
        prior_tp = report.third_party_electronic_circulation or 0
        native_electronic = (report.electronic_circulation or 0) - prior_tp
        native_total = (report.total_circulation or 0) - prior_tp

        report.third_party_electronic_circulation = new_tp
        report.electronic_circulation_by_platform = by_platform
        # PLS electronic = native ebook checkouts + third-party platform circulation.
        report.electronic_circulation = native_electronic + new_tp
        # Total circulation includes the third-party amount. Physical is untouched —
        # third-party circulation is electronic, not physical.
        report.total_circulation = native_total + new_tp

        report.last_modified_by_id = current_user.id

        await db.flush()
        logger.info(
            f"Third-party e-circ entered for annual report {report_id} "
            f"by user {current_user.id}"
        )

        return ElectronicCirculationResponse(
            report_id=report.id,
            third_party_electronic_circulation=report.third_party_electronic_circulation,
            electronic_circulation_by_platform=by_platform,
            electronic_circulation=report.electronic_circulation,
            total_circulation=report.total_circulation,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error entering electronic circulation for annual report: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enter annual report electronic circulation",
        ) from e


# ==========================================
# CERTIFICATION
# ==========================================

@router.post(
    "/{report_id}/certify",
    summary="Certify Annual Report",
    description="Certify a report for submission. Blocked (409) while PLS validation "
    "errors remain; on success transitions status to validated and records the certifier.",
)
@limiter.limit("30/minute")
async def certify_annual_report(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gate submission on PLS validation; certify and stamp the certifier when clean."""
    try:
        check_staff_access(current_user)

        report = await db.get(AnnualReport, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        errors = validate(report)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Report cannot be certified until validation passes.",
                    "error_count": len(errors),
                    "errors": [e.to_dict() for e in errors],
                },
            )

        report.is_validated = True
        report.validation_errors = None
        report.validated_by_id = current_user.id
        report.validated_at = datetime.now(timezone.utc)
        report.status = ReportStatus.VALIDATED

        await db.flush()
        logger.info(f"Annual report {report_id} certified by user {current_user.id}")

        return {
            "report_id": report.id,
            "status": _status_str(report.status),
            "is_validated": True,
            "validated_by_id": report.validated_by_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error certifying annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to certify annual report",
        ) from e


# ==========================================
# RECONCILIATION
# ==========================================

# Stored report column -> (live source method key, field within that source dict).
_RECONCILIATION_FIELDS = [
    ("total_checkouts", "circulation", "total_checkouts"),
    ("total_renewals", "circulation", "total_renewals"),
    ("total_circulation", "circulation", "total_circulation"),
    ("total_program_attendance", "program", "total_program_attendance"),
    ("total_library_visits", "visits", "total_library_visits"),
    ("reference_questions_answered", "visits", "reference_questions_answered"),
]


@router.get(
    "/{report_id}/reconciliation",
    summary="Reconcile Annual Report",
    description="Re-run each reconcilable field's source query live over the report's "
    "fiscal year and report drift between the stored snapshot and the current value.",
)
@limiter.limit("30/minute")
async def reconcile_annual_report(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Diff stored report values against freshly-computed live source values."""
    try:
        check_staff_access(current_user)

        report = await db.get(AnnualReport, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        fiscal_year = report.fiscal_year
        fiscal_start = date(fiscal_year - 1, 7, 1)
        fiscal_end = date(fiscal_year, 6, 30)
        today = date.today()
        if fiscal_end > today:
            fiscal_end = today

        # Snapshot stored values up front; the per-section rollbacks below expire
        # the ORM object.
        stored = {field: getattr(report, field) for field, _, _ in _RECONCILIATION_FIELDS}

        service = AnnualReportService(db)
        # Each source method is read-only and self-contained. Roll back after each so
        # an aborted section (e.g. a section that errors on its own data) cannot poison
        # the next section's query.
        sources: dict = {}
        sources["circulation"] = await service._get_circulation_data(fiscal_start, fiscal_end)
        await db.rollback()
        sources["program"] = await service._get_program_data(fiscal_start, fiscal_end)
        await db.rollback()
        sources["visits"] = await service._get_visitor_data(fiscal_start, fiscal_end)
        await db.rollback()

        fields = []
        for field, source, key in _RECONCILIATION_FIELDS:
            report_value = stored.get(field)
            live_value = (sources.get(source) or {}).get(key)
            drift = None
            if live_value is not None:
                drift = live_value - (report_value or 0)
            fields.append(
                {
                    "field": field,
                    "report_value": report_value,
                    "live_source_value": live_value,
                    "drift": drift,
                }
            )

        return {"report_id": report_id, "fields": fields}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconciling annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reconcile annual report",
        ) from e


# ==========================================
# EXPORT
# ==========================================

@router.get(
    "/{report_id}/export/excel",
    summary="Export as Excel",
    description="Export annual report in Excel format.",
)
@limiter.limit("20/hour")
async def export_annual_report_excel(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export annual report in Excel format.

    Includes all statistical data formatted for state submission.
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        report = await service.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"FY {report.fiscal_year}"

        # Define styles
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        section_font = Font(bold=True, size=11)
        border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # Title section
        ws.merge_cells('A1:B1')
        title_cell = ws['A1']
        title_cell.value = f"Annual Report - {report.library_name}"
        title_cell.font = Font(bold=True, size=14)
        title_cell.fill = header_fill
        title_cell.font = header_font
        title_cell.alignment = Alignment(horizontal='center')

        ws.merge_cells('A2:B2')
        subtitle_cell = ws['A2']
        subtitle_cell.value = f"Fiscal Year {report.fiscal_year} - {report.state_code}"
        subtitle_cell.font = Font(bold=True, size=11)
        subtitle_cell.alignment = Alignment(horizontal='center')

        row = 4

        # Helper function to add section
        def add_section(title, data_dict):
            nonlocal row
            ws.merge_cells(f'A{row}:B{row}')
            section_cell = ws[f'A{row}']
            section_cell.value = title
            section_cell.font = section_font
            section_cell.fill = section_fill
            row += 1

            for label, value in data_dict.items():
                ws[f'A{row}'] = label
                ws[f'B{row}'] = value if value is not None else 0
                ws[f'A{row}'].border = border
                ws[f'B{row}'].border = border
                row += 1
            row += 1

        # Add all sections
        add_section("Circulation Statistics", {
            "Total Checkouts": report.total_checkouts,
            "Total Renewals": report.total_renewals,
            "Total Returns": report.total_returns,
            "Total Holds Placed": report.total_holds_placed,
            "Total Holds Filled": report.total_holds_filled,
            "Items Loaned to Other Libraries": report.items_loaned_to_other_libraries,
            "Items Borrowed from Other Libraries": report.items_borrowed_from_other_libraries,
        })

        add_section("Patron Statistics", {
            "Total Registered Patrons": report.total_registered_patrons,
            "Active Patrons": report.active_patrons,
            "New Patrons Registered": report.new_patrons_registered,
            "Resident Patrons": report.resident_patrons,
            "Non-Resident Patrons": report.non_resident_patrons,
        })

        add_section("Collection Statistics", {
            "Total Items Owned": report.total_items_owned,
            "Total Titles Owned": report.total_titles_owned,
            "Items Added During Year": report.items_added_during_year,
            "Items Withdrawn During Year": report.items_withdrawn_during_year,
        })

        cap_rev = report.capital_revenue or {}
        add_section("Financial Statistics", {
            "Capital Outlay": report.capital_outlay,
            "Capital Revenue - Local": cap_rev.get("local"),
            "Capital Revenue - State": cap_rev.get("state"),
            "Capital Revenue - Federal": cap_rev.get("federal"),
            "Capital Revenue - Other": cap_rev.get("other"),
        })

        # Column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 20

        # Create in-memory file
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        filename = f"annual_report_{report.fiscal_year}_{report.state_code}.xlsx"

        return Response(
            content=excel_file.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting annual report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export annual report",
        ) from e


@router.get(
    "/{report_id}/export/pdf",
    summary="Export as PDF",
    description="Export annual report in PDF format.",
)
@limiter.limit("20/hour")
async def export_annual_report_pdf(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export annual report in PDF format.

    Includes all statistical data with professional formatting.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        check_staff_access(current_user)

        service = AnnualReportService(db)
        report = await service.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        # Create PDF in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#366092'),
            spaceAfter=12,
            alignment=1  # Center
        )

        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#366092'),
            spaceBefore=12,
            spaceAfter=6
        )

        # Title
        elements.append(Paragraph(f"Annual Report - {report.library_name}", title_style))
        elements.append(Paragraph(f"Fiscal Year {report.fiscal_year} - {report.state_code}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Helper function to add section
        def add_section(title, data):
            elements.append(Paragraph(title, section_style))

            table_data = [[k, str(v if v is not None else 0)] for k, v in data.items()]

            t = Table(table_data, colWidths=[4*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.2*inch))

        # Add sections
        add_section("Circulation Statistics", {
            "Total Checkouts": report.total_checkouts,
            "Total Renewals": report.total_renewals,
            "Total Returns": report.total_returns,
            "Total Holds Placed": report.total_holds_placed,
            "Total Holds Filled": report.total_holds_filled,
            "Items Loaned to Other Libraries": report.items_loaned_to_other_libraries,
            "Items Borrowed from Other Libraries": report.items_borrowed_from_other_libraries,
            "In-House Use Count": report.in_house_use_count,
        })

        add_section("Patron Statistics", {
            "Total Registered Patrons": report.total_registered_patrons,
            "Active Patrons": report.active_patrons,
            "New Patrons Registered": report.new_patrons_registered,
            "Patrons Renewed Library Cards": report.patrons_renewed_library_cards,
            "Resident Patrons": report.resident_patrons,
            "Non-Resident Patrons": report.non_resident_patrons,
        })

        add_section("Collection Statistics", {
            "Total Items Owned": report.total_items_owned,
            "Total Titles Owned": report.total_titles_owned,
            "Items Added During Year": report.items_added_during_year,
            "Items Withdrawn During Year": report.items_withdrawn_during_year,
        })

        cap_rev = report.capital_revenue or {}
        add_section("Financial Statistics", {
            "Capital Outlay": report.capital_outlay,
            "Capital Revenue - Local": cap_rev.get("local"),
            "Capital Revenue - State": cap_rev.get("state"),
            "Capital Revenue - Federal": cap_rev.get("federal"),
            "Capital Revenue - Other": cap_rev.get("other"),
        })

        # Build PDF
        doc.build(elements)
        pdf_buffer.seek(0)

        filename = f"annual_report_{report.fiscal_year}_{report.state_code}.pdf"

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting annual report to PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export annual report",
        ) from e


@router.get(
    "/{report_id}/export/xml",
    summary="Export as XML",
    description="Export annual report in XML format for state submission.",
)
@limiter.limit("20/hour")
async def export_annual_report_xml(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export annual report in XML format.

    Formatted according to state library requirements.
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        report = await service.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        # Create XML structure
        root = ET.Element("AnnualReport")

        # Report metadata
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "FiscalYear").text = str(report.fiscal_year)
        ET.SubElement(metadata, "StateCode").text = report.state_code
        ET.SubElement(metadata, "LibraryID").text = report.library_id or ""
        ET.SubElement(metadata, "LibraryName").text = report.library_name
        ET.SubElement(metadata, "LibraryType").text = report.library_type or ""
        ET.SubElement(metadata, "Status").text = _status_str(report.status)

        # Circulation statistics
        circulation = ET.SubElement(root, "CirculationStatistics")
        ET.SubElement(circulation, "TotalCheckouts").text = str(report.total_checkouts or 0)
        ET.SubElement(circulation, "TotalRenewals").text = str(report.total_renewals or 0)
        ET.SubElement(circulation, "TotalReturns").text = str(report.total_returns or 0)
        ET.SubElement(circulation, "TotalHoldsPlaced").text = str(report.total_holds_placed or 0)
        ET.SubElement(circulation, "TotalHoldsFilled").text = str(report.total_holds_filled or 0)
        ET.SubElement(circulation, "AvgHoldWaitDays").text = str(report.avg_hold_wait_days or 0)
        ET.SubElement(circulation, "ItemsLoanedToOtherLibraries").text = str(report.items_loaned_to_other_libraries or 0)
        ET.SubElement(circulation, "ItemsBorrowedFromOtherLibraries").text = str(report.items_borrowed_from_other_libraries or 0)
        ET.SubElement(circulation, "InHouseUseCount").text = str(report.in_house_use_count or 0)

        # Patron statistics
        patron = ET.SubElement(root, "PatronStatistics")
        ET.SubElement(patron, "TotalRegisteredPatrons").text = str(report.total_registered_patrons or 0)
        ET.SubElement(patron, "ActivePatrons").text = str(report.active_patrons or 0)
        ET.SubElement(patron, "NewPatronsRegistered").text = str(report.new_patrons_registered or 0)
        ET.SubElement(patron, "PatronsRenewedLibraryCards").text = str(report.patrons_renewed_library_cards or 0)
        ET.SubElement(patron, "ResidentPatrons").text = str(report.resident_patrons or 0)
        ET.SubElement(patron, "NonResidentPatrons").text = str(report.non_resident_patrons or 0)

        # Collection statistics
        collection = ET.SubElement(root, "CollectionStatistics")
        ET.SubElement(collection, "TotalItemsOwned").text = str(report.total_items_owned or 0)
        ET.SubElement(collection, "TotalTitlesOwned").text = str(report.total_titles_owned or 0)
        ET.SubElement(collection, "ItemsAddedDuringYear").text = str(report.items_added_during_year or 0)
        ET.SubElement(collection, "ItemsWithdrawnDuringYear").text = str(report.items_withdrawn_during_year or 0)

        # Financial statistics
        cap_rev = report.capital_revenue or {}
        financial = ET.SubElement(root, "FinancialStatistics")
        ET.SubElement(financial, "CapitalOutlay").text = str(report.capital_outlay or 0)
        capital_revenue = ET.SubElement(financial, "CapitalRevenue")
        ET.SubElement(capital_revenue, "Local").text = str(cap_rev.get("local") or 0)
        ET.SubElement(capital_revenue, "State").text = str(cap_rev.get("state") or 0)
        ET.SubElement(capital_revenue, "Federal").text = str(cap_rev.get("federal") or 0)
        ET.SubElement(capital_revenue, "Other").text = str(cap_rev.get("other") or 0)

        # Format XML with indentation
        xml_string = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

        filename = f"annual_report_{report.fiscal_year}_{report.state_code}.xml"

        return Response(
            content=xml_string,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting annual report to XML: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export annual report",
        ) from e


# ==========================================
# COMPARISON
# ==========================================

@router.get(
    "/{report_id}/comparison",
    summary="Year-over-Year Comparison",
    description="Get year-over-year comparison data for an annual report.",
)
@limiter.limit("30/minute")
async def get_yoy_comparison(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get year-over-year comparison metrics.

    Shows growth percentages and changes in key metrics compared to prior year.
    """
    try:
        check_staff_access(current_user)

        service = AnnualReportService(db)
        report = await service.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annual report not found",
            )

        return {
            "report_id": report_id,
            "current_year": {
                "total_checkouts": report.total_checkouts,
                "total_patrons": report.total_registered_patrons,
                "total_visits": report.total_library_visits,
                "total_programs": report.total_programs_offered,
                "total_expenditure": float(report.total_operating_expenditure) if report.total_operating_expenditure else None,
            },
            "prior_year": {
                "total_checkouts": report.prior_year_total_checkouts,
                "total_patrons": report.prior_year_total_patrons,
                "total_visits": report.prior_year_total_visits,
                "total_programs": report.prior_year_total_programs,
                "total_expenditure": float(report.prior_year_total_expenditure) if report.prior_year_total_expenditure else None,
            },
            "growth_percent": {
                "checkouts": float(report.checkout_growth_percent) if report.checkout_growth_percent else None,
                "patrons": float(report.patron_growth_percent) if report.patron_growth_percent else None,
                "visits": float(report.visit_growth_percent) if report.visit_growth_percent else None,
                "programs": float(report.program_growth_percent) if report.program_growth_percent else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting year-over-year comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get year-over-year comparison",
        ) from e
