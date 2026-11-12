# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unified Reports API.

Provides a single set of endpoints for generating, exporting, and tracking
reports via the consolidated ReportFactory. All report types (circulation,
financial, patron activity, collection, compliance) use the same interface.

Existing domain-specific endpoints (financial_reports.py, reports.py, etc.)
remain functional for backwards compatibility; this module adds the new
unified multi-format export and async generation capabilities.
"""

import csv
import io
import json
from app.core.logging import get_logger
import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...core.cache import get_redis
from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.report_audit import ReportGenerationLog
from ...models.user import User
from ...services import operations_audit_service as ops_audit
from ...services.reports.base import OutputFormat, ReportFilters
from ...services.reports.factory import ReportFactory, ReportType
from .auth import get_current_user
from .dependencies import check_staff_access

router = APIRouter(prefix="/unified-reports", tags=["unified-reports"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Content-type mapping
# ---------------------------------------------------------------------------

_CONTENT_TYPES = {
    OutputFormat.JSON: "application/json",
    OutputFormat.CSV: "text/csv",
    OutputFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    OutputFormat.PDF: "application/pdf",
}

_FILE_EXTENSIONS = {
    OutputFormat.JSON: "json",
    OutputFormat.CSV: "csv",
    OutputFormat.EXCEL: "xlsx",
    OutputFormat.PDF: "pdf",
}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AuditLogEntry(BaseModel):
    id: int
    report_type: str
    format: str
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    generated_by_id: Optional[int] = None
    generated_by_email: Optional[str] = None
    generated_at: str
    duration_ms: Optional[int] = None
    record_count: Optional[int] = None
    cache_hit: bool

class AuditLogResponse(BaseModel):
    items: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Helper: build factory from request deps
# ---------------------------------------------------------------------------

async def _get_factory(db: AsyncSession) -> ReportFactory:
    redis = None
    try:
        redis = await get_redis()
    except Exception:  # noqa: BLE001  # Redis optional — report caching disabled if unavailable
        logger.debug("Redis not available; report caching disabled")
    return ReportFactory(db, redis)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/types")
async def list_report_types(
    current_user: User = Depends(get_current_user),
):
    """List all available report types and output formats."""
    return {
        "report_types": [t.value for t in ReportType],
        "output_formats": [f.value for f in OutputFormat],
    }


@router.get("/generate/{report_type}")
@limiter.limit("10/minute")
async def generate_report(
    request: Request,
    report_type: ReportType = Path(..., description="Report type"),
    format: OutputFormat = Query(OutputFormat.JSON, description="Output format"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year (for compliance)"),
    state_code: Optional[str] = Query(None, description="State code (for compliance)"),
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    cache_ttl: Optional[int] = Query(None, description="Override cache TTL (seconds)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a report synchronously and return it in the requested format.

    Supported report types: circulation, financial, patron_activity, collection, compliance.
    Supported formats: json, csv, excel, pdf.

    **Access**: Staff only
    """
    check_staff_access(current_user)

    try:
        start = _parse_date(start_date) if start_date else None
        end = _parse_date(end_date) if end_date else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
        ) from None

    filters = ReportFilters(
        start_date=start,
        end_date=end,
        fiscal_year=fiscal_year,
        state_code=state_code,
        branch_id=branch_id,
    )

    factory = await _get_factory(db)

    t0 = time.monotonic()
    try:
        result_bytes, cache_hit = await factory.generate_with_meta(
            report_type,
            filters,
            format,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
    except Exception as e:
        logger.error("Report generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate {report_type.value} report",
        ) from e
    duration_ms = int((time.monotonic() - t0) * 1000)

    record_count = _extract_record_count(result_bytes, format)

    await _audit_report_generated(
        db,
        user=current_user,
        report_type=report_type,
        output=format,
        filters=filters,
        duration_ms=duration_ms,
        record_count=record_count,
        cache_hit=cache_hit,
    )

    content_type = _CONTENT_TYPES[format]
    ext = _FILE_EXTENSIONS[format]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type.value}_report_{timestamp}.{ext}"
    cache_header = {
        "X-Cache-Hit": "1" if cache_hit else "0",
        "Access-Control-Expose-Headers": "X-Cache-Hit, Content-Disposition",
    }

    if format == OutputFormat.JSON:
        return Response(content=result_bytes, media_type=content_type, headers=cache_header)

    return Response(
        content=result_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            **cache_header,
        },
    )


@router.post("/generate-async/{report_type}")
@limiter.limit("5/minute")
async def generate_report_async(
    request: Request,
    report_type: ReportType = Path(..., description="Report type"),
    format: OutputFormat = Query(OutputFormat.JSON, description="Output format"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year (for compliance)"),
    state_code: Optional[str] = Query(None, description="State code (for compliance)"),
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start async report generation and return a tracking ID.

    Use ``GET /unified-reports/progress/{report_id}`` to poll progress.
    Use ``GET /unified-reports/result/{report_id}`` to download when complete.

    **Access**: Staff only
    """
    check_staff_access(current_user)

    try:
        start = _parse_date(start_date) if start_date else None
        end = _parse_date(end_date) if end_date else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format.",
        ) from None

    filters = ReportFilters(
        start_date=start,
        end_date=end,
        fiscal_year=fiscal_year,
        state_code=state_code,
        branch_id=branch_id,
    )

    factory = await _get_factory(db)
    report_id = await factory.generate_async(report_type, filters, format)

    await _audit_report_generated(
        db,
        user=current_user,
        report_type=report_type,
        output=format,
        filters=filters,
        duration_ms=None,
        record_count=None,
        cache_hit=False,
    )

    return {
        "report_id": report_id,
        "report_type": report_type.value,
        "format": format.value,
        "status": "pending",
        "progress_url": f"/api/v1/unified-reports/progress/{report_id}",
        "result_url": f"/api/v1/unified-reports/result/{report_id}",
    }


@router.get("/progress/{report_id}")
async def get_report_progress(
    report_id: str = Path(..., description="Report tracking ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get progress for an async report generation."""
    check_staff_access(current_user)

    factory = await _get_factory(db)
    progress = await factory.get_progress(report_id)

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    return progress


@router.get("/result/{report_id}")
async def get_report_result(
    report_id: str = Path(..., description="Report tracking ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the completed async report."""
    check_staff_access(current_user)

    factory = await _get_factory(db)

    progress = await factory.get_progress(report_id)
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    if progress.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report not ready. Status: {progress.get('status')}",
        )

    result = await factory.get_async_result(report_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report result expired or not available",
        )

    return Response(
        content=result,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}"'},
    )


@router.post("/cache/invalidate")
@limiter.limit("5/minute")
async def invalidate_report_cache(
    request: Request,
    report_type: Optional[ReportType] = Query(None, description="Specific type to invalidate (or all)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear cached reports."""
    check_staff_access(current_user)

    factory = await _get_factory(db)
    count = await factory.invalidate_cache(report_type)

    return {
        "status": "success",
        "invalidated": count,
        "scope": report_type.value if report_type else "all",
    }


@router.delete("/cache/{report_type}")
@limiter.limit("10/minute")
async def delete_report_cache(
    request: Request,
    report_type: ReportType = Path(..., description="Report type cache to clear"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear cached reports for a specific type. Used by the frontend Refresh button."""
    check_staff_access(current_user)

    factory = await _get_factory(db)
    count = await factory.invalidate_cache(report_type)

    return {
        "status": "success",
        "invalidated": count,
        "scope": report_type.value,
    }


# ---------------------------------------------------------------------------
# Report audit log endpoint
# ---------------------------------------------------------------------------

@router.get("/audit-log", response_model=AuditLogResponse)
async def get_report_audit_log(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    start_date: Optional[str] = Query(None, description="Filter: generated on or after (ISO)"),
    end_date: Optional[str] = Query(None, description="Filter: generated on or before (ISO)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("generated_at", description="Sort column: generated_at|duration_ms|record_count"),
    sort_order: str = Query("desc", description="Sort direction: asc|desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated report generation audit log entries (newest first).

    **Access**: Staff only
    """
    check_staff_access(current_user)

    base = select(ReportGenerationLog).options(
        joinedload(ReportGenerationLog.generated_by)
    )
    count_base = select(sa_func.count(ReportGenerationLog.id))

    if report_type:
        base = base.where(ReportGenerationLog.report_type == report_type)
        count_base = count_base.where(ReportGenerationLog.report_type == report_type)

    if start_date:
        try:
            dt = _parse_date(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date") from None
        base = base.where(ReportGenerationLog.generated_at >= dt)
        count_base = count_base.where(ReportGenerationLog.generated_at >= dt)

    if end_date:
        try:
            dt = _parse_date(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date") from None
        base = base.where(ReportGenerationLog.generated_at <= dt)
        count_base = count_base.where(ReportGenerationLog.generated_at <= dt)

    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    query = base.order_by(_report_sort_clause(sort_by, sort_order)).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.unique().scalars().all()

    items = [
        AuditLogEntry(
            id=row.id,
            report_type=row.report_type,
            format=row.format,
            date_range_start=row.date_range_start.isoformat() if row.date_range_start else None,
            date_range_end=row.date_range_end.isoformat() if row.date_range_end else None,
            generated_by_id=row.generated_by_id,
            generated_by_email=row.generated_by.email if row.generated_by else None,
            generated_at=row.generated_at.isoformat(),
            duration_ms=row.duration_ms,
            record_count=row.record_count,
            cache_hit=row.cache_hit,
        )
        for row in rows
    ]

    return AuditLogResponse(items=items, total=total, limit=limit, offset=offset)


_REPORT_SORT_COLUMNS = {
    "generated_at": ReportGenerationLog.generated_at,
    "duration_ms": ReportGenerationLog.duration_ms,
    "record_count": ReportGenerationLog.record_count,
}


def _report_sort_clause(sort_by: str, sort_order: str):
    column = _REPORT_SORT_COLUMNS.get(sort_by, ReportGenerationLog.generated_at)
    return column.asc() if sort_order == "asc" else column.desc()


@router.get("/audit-log/export")
async def export_report_audit_log(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    start_date: Optional[str] = Query(None, description="Filter: generated on or after (ISO)"),
    end_date: Optional[str] = Query(None, description="Filter: generated on or before (ISO)"),
    sort_by: str = Query("generated_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the report generation audit log as CSV (max 5000 rows).

    **Access**: Staff only
    """
    check_staff_access(current_user)

    base = select(ReportGenerationLog).options(
        joinedload(ReportGenerationLog.generated_by)
    )
    if report_type:
        base = base.where(ReportGenerationLog.report_type == report_type)
    if start_date:
        try:
            dt = _parse_date(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date") from None
        base = base.where(ReportGenerationLog.generated_at >= dt)
    if end_date:
        try:
            dt = _parse_date(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date") from None
        base = base.where(ReportGenerationLog.generated_at <= dt)

    query = base.order_by(_report_sort_clause(sort_by, sort_order)).limit(5000)
    result = await db.execute(query)
    rows = result.unique().scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Report Type", "Format", "Date Range Start", "Date Range End",
        "Generated By", "Generated At", "Duration (ms)", "Records", "Cache",
    ])
    for row in rows:
        writer.writerow([
            row.report_type,
            row.format,
            row.date_range_start.isoformat() if row.date_range_start else "",
            row.date_range_end.isoformat() if row.date_range_end else "",
            row.generated_by.email if row.generated_by else "",
            row.generated_at.isoformat(),
            row.duration_ms if row.duration_ms is not None else "",
            row.record_count if row.record_count is not None else "",
            "hit" if row.cache_hit else "fresh",
        ])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report-audit-log.csv"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_record_count(data: bytes, fmt: OutputFormat) -> Optional[int]:
    if fmt != OutputFormat.JSON:
        return None
    try:
        parsed = json.loads(data)
        if isinstance(parsed, list):
            return len(parsed)
        if isinstance(parsed, dict):
            for key in ("items", "rows", "records", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    return len(parsed[key])
            if "total" in parsed and isinstance(parsed["total"], int):
                return parsed["total"]
    except Exception:  # noqa: BLE001  # count helper — return None on any parse failure
        pass
    return None


async def _audit_report_generated(
    db: AsyncSession,
    *,
    user: User,
    report_type: ReportType,
    output: OutputFormat,
    filters: ReportFilters,
    duration_ms: Optional[int] = None,
    record_count: Optional[int] = None,
    cache_hit: bool = False,
) -> None:
    # Write to dedicated report generation log
    try:
        log_entry = ReportGenerationLog(
            report_type=report_type.value,
            format=output.value,
            date_range_start=filters.start_date,
            date_range_end=filters.end_date,
            generated_by_id=user.id,
            duration_ms=duration_ms,
            record_count=record_count,
            cache_hit=cache_hit,
        )
        db.add(log_entry)
        await db.commit()
    except Exception:
        logger.exception("Failed to write report generation log entry")
        await db.rollback()

    # Also write to operations audit log (existing behaviour, skip for cache hits)
    if not cache_hit:
        from ...models.operations_audit_log import OperationType

        details = {
            "report_type": report_type.value,
            "output": output.value,
            "start_date": filters.start_date.isoformat() if filters.start_date else None,
            "end_date": filters.end_date.isoformat() if filters.end_date else None,
            "branch_id": filters.branch_id,
            "fiscal_year": filters.fiscal_year,
            "state_code": filters.state_code,
        }
        try:
            await ops_audit.log_system_operation(
                db,
                operation_type=OperationType.SYSTEM_REPORT_GENERATED,
                details=details,
                staff=user,
            )
        except Exception:
            logger.exception("Failed to audit-log report generation")
