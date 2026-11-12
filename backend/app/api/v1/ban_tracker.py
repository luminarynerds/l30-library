# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for the Book Ban Tracker & Advocacy Hub."""

import csv
import io
from app.core.logging import get_logger
from datetime import date, datetime, time, timezone
from email.utils import format_datetime
from html import escape as html_escape
from math import ceil
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.ban_tracker import AdvocacyLetterTemplate, BanReport, BanSource, BanType
from ...models.user import User, UserRole
from ...schemas.ban_tracker import (
    BanAlertResponse,
    BanReportCreate,
    BanReportPublicResponse,
    BanReportResponse,
    BanReportStats,
    BanReportTimelineBucket,
    BanReportTimelineResponse,
    BanReportUpdate,
    CivicLookupResponse,
    MostBannedBook,
    PublicBanReportSubmission,
    RepresentativeInfo,
    LetterTemplateCreate,
    LetterTemplateResponse,
    LetterTemplateUpdate,
    PaginatedBanReports,
    PaginatedPublicBanReports,
)
from ...services.acquisition_rationale_service import RationaleService
from ...services.ban_tracker_service import BanAlertService, BanTrackerService
from ...services.civic_api_service import CivicApiService
from ...services.pen_america_sync_service import PenAmericaSyncService
from .auth import get_current_user
from .dependencies import is_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/ban-tracker", tags=["ban-tracker"])
advocacy_router = APIRouter(prefix="/advocacy", tags=["advocacy"])


def _ensure_staff(current_user: User) -> None:
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required",
        )


async def _serialize_with_rationale(
    report: BanReport, rat_svc: RationaleService,
) -> BanReportResponse:
    base = BanReportResponse.model_validate(report)
    if report.catalog_match_id is None:
        return base
    rationale = await rat_svc.get_by_catalog_item(report.catalog_match_id)
    if rationale is None:
        return base
    anticipated = bool(
        report.reason_category
        and report.reason_category
        in (rationale.anticipated_challenge_reasons or [])
    )
    return base.model_copy(update={
        "rationale_present": True,
        "rationale_anticipated": anticipated,
        "rationale_primary_use_case": rationale.primary_use_case_slug,
    })


async def _serialize_reports_with_rationale(
    reports: list[BanReport], db: AsyncSession,
) -> list[BanReportResponse]:
    rat_svc = RationaleService(db)
    return [await _serialize_with_rationale(r, rat_svc) for r in reports]


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("/public/reports", response_model=PaginatedPublicBanReports)
async def list_public_reports(
    state: str | None = Query(None, description="Filter by US state code (2-letter)"),
    ban_type: str | None = Query(None, description="Filter by ban type"),
    reason_category: str | None = Query(None, description="Filter by reason category"),
    source: str | None = Query(None, description="Filter by source (PEN_AMERICA, ALA, STAFF_ENTRY, NEWS)"),
    search: str | None = Query(None, description="Search by title or author"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List ban reports publicly (sanitized view)."""
    reports, total = await BanTrackerService.list_reports(
        db,
        state=state,
        ban_type=ban_type,
        source=source,
        reason_category=reason_category,
        search=search,
        page=page,
        per_page=per_page,
    )

    public_items = [
        BanReportPublicResponse(
            id=r.id,
            title=r.title,
            author=r.author,
            state=r.state,
            district=r.district,
            ban_type=r.ban_type.value if hasattr(r.ban_type, "value") else r.ban_type,
            reason_category=r.reason_category,
            source=r.source.value if hasattr(r.source, "value") else r.source,
            source_url=r.source_url,
            date_reported=r.date_reported,
            date_enacted=r.date_enacted,
            has_in_catalog=r.catalog_match_id is not None,
            catalog_item_id=r.catalog_match_id,
            cover_url=r.catalog_match.cover_url if r.catalog_match else None,
        )
        for r in reports
    ]

    return PaginatedPublicBanReports(
        items=public_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/public/catalog-matches", response_model=list[BanReportPublicResponse])
async def list_public_catalog_matches(
    db: AsyncSession = Depends(get_db),
):
    """List all ban reports that match items in the library catalog (public)."""
    reports = await BanTrackerService.get_all_catalog_matches(db)
    return [
        BanReportPublicResponse(
            id=r.id,
            title=r.title,
            author=r.author,
            state=r.state,
            district=r.district,
            ban_type=r.ban_type.value if hasattr(r.ban_type, "value") else r.ban_type,
            reason_category=r.reason_category,
            source=r.source.value if hasattr(r.source, "value") else r.source,
            source_url=r.source_url,
            date_reported=r.date_reported,
            date_enacted=r.date_enacted,
            has_in_catalog=True,
            catalog_item_id=r.catalog_match_id,
            cover_url=r.catalog_match.cover_url if r.catalog_match else None,
        )
        for r in reports
    ]


@router.get("/public/stats", response_model=BanReportStats)
async def get_public_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get public aggregate statistics for ban reports."""
    stats = await BanTrackerService.get_statistics(db)
    return BanReportStats(**stats)


@router.get("/public/most-banned", response_model=list[MostBannedBook])
async def get_most_banned(
    limit: int = Query(10, ge=1, le=50, description="Number of top books to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get the most frequently banned/challenged books, aggregated by title+author."""
    rows = await BanTrackerService.get_most_banned(db, limit=limit)
    return [MostBannedBook(**r) for r in rows]


# Hard cap on export row count for memory/transfer safety. If the filtered
# result set exceeds this, only the first EXPORT_ROW_CAP rows are returned
# and an `X-Truncated: true` response header is set.
EXPORT_ROW_CAP = 10000

_BAN_TYPE_LABELS = {
    "challenged": "Challenged",
    "restricted": "Restricted",
    "banned": "Banned",
    "pending": "Pending",
}


async def _filtered_export_rows(
    db: AsyncSession,
    state: str | None,
    ban_type: str | None,
    reason_category: str | None,
    source: str | None,
    search: str | None,
) -> tuple[list[BanReport], bool]:
    query = select(BanReport)
    if state:
        query = query.where(BanReport.state == state)
    if ban_type:
        query = query.where(BanReport.ban_type == ban_type)
    if source:
        query = query.where(BanReport.source == source)
    if reason_category:
        query = query.where(BanReport.reason_category == reason_category)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            BanReport.title.ilike(pattern) | BanReport.author.ilike(pattern)
        )
    query = query.order_by(BanReport.created_at.desc(), BanReport.id.desc())
    # Fetch one extra row to detect truncation.
    result = await db.execute(query.limit(EXPORT_ROW_CAP + 1))
    rows = list(result.scalars().all())
    truncated = len(rows) > EXPORT_ROW_CAP
    return rows[:EXPORT_ROW_CAP], truncated


_CSV_COLUMNS = [
    "id",
    "title",
    "author",
    "state",
    "ban_type",
    "reason_category",
    "district",
    "institution",
    "source",
    "source_url",
    "date_reported",
    "has_in_catalog",
]


@router.get("/public/reports.csv")
async def export_public_reports_csv(
    state: str | None = Query(None),
    ban_type: str | None = Query(None),
    reason_category: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Stream filtered ban reports as RFC 4180 CSV (10k row cap)."""
    rows, truncated = await _filtered_export_rows(
        db, state, ban_type, reason_category, source, search,
    )

    def _gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_CSV_COLUMNS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for r in rows:
            ban_type_val = r.ban_type.value if hasattr(r.ban_type, "value") else r.ban_type
            source_val = r.source.value if hasattr(r.source, "value") else r.source
            writer.writerow([
                r.id,
                r.title or "",
                r.author or "",
                r.state or "",
                ban_type_val or "",
                r.reason_category or "",
                r.district or "",
                r.institution or "",
                source_val or "",
                r.source_url or "",
                r.date_reported.isoformat() if r.date_reported else "",
                "true" if r.catalog_match_id is not None else "false",
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"ban-reports-{date.today().isoformat()}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if truncated:
        headers["X-Truncated"] = "true"
    return StreamingResponse(
        _gen(),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


def _rss_pub_date(d: date | None) -> str | None:
    if d is None:
        return None
    dt = datetime.combine(d, time.min, tzinfo=timezone.utc)
    return format_datetime(dt)


def _filter_summary(
    state: str | None,
    ban_type: str | None,
    reason_category: str | None,
    source: str | None,
    search: str | None,
) -> str:
    parts = []
    if state:
        parts.append(f"state={state}")
    if ban_type:
        parts.append(f"ban_type={ban_type}")
    if reason_category:
        parts.append(f"reason_category={reason_category}")
    if source:
        parts.append(f"source={source}")
    if search:
        parts.append(f"search={search}")
    return ", ".join(parts) if parts else "no filters applied"


@router.get("/public/reports.rss")
async def export_public_reports_rss(
    request: Request,
    state: str | None = Query(None),
    ban_type: str | None = Query(None),
    reason_category: str | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return filtered ban reports as an RSS 2.0 feed (10k row cap)."""
    rows, truncated = await _filtered_export_rows(
        db, state, ban_type, reason_category, source, search,
    )

    # Build the public tracker URL from the inbound request so we honor the
    # caller's scheme + host (works behind the reverse proxy and in dev).
    base = f"{request.url.scheme}://{request.url.netloc}"
    tracker_qs_parts = []
    if state:
        tracker_qs_parts.append(f"state={state}")
    if ban_type:
        tracker_qs_parts.append(f"ban_type={ban_type}")
    if reason_category:
        tracker_qs_parts.append(f"reason={reason_category}")
    if source:
        tracker_qs_parts.append(f"source={source}")
    if search:
        tracker_qs_parts.append(f"q={search}")
    tracker_url = f"{base}/ban-tracker"
    if tracker_qs_parts:
        tracker_url = f"{tracker_url}?{'&'.join(tracker_qs_parts)}"

    rss = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "L30 Ban Tracker — Filtered Reports"
    SubElement(channel, "link").text = tracker_url
    SubElement(channel, "description").text = (
        f"Ban reports filtered by {_filter_summary(state, ban_type, reason_category, source, search)}."
    )

    for r in rows:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = html_escape(f"{r.title} by {r.author}")
        link = r.source_url or tracker_url
        SubElement(item, "link").text = link
        ban_type_val = r.ban_type.value if hasattr(r.ban_type, "value") else (r.ban_type or "")
        ban_type_label = _BAN_TYPE_LABELS.get(ban_type_val, str(ban_type_val) or "Report")
        state_label = r.state or "—"
        reason_label = r.reason_category or "—"
        district_label = r.district or "—"
        SubElement(item, "description").text = html_escape(
            f"{ban_type_label} in {state_label}. Reason: {reason_label}. District: {district_label}."
        )
        pub = _rss_pub_date(r.date_reported)
        if pub:
            SubElement(item, "pubDate").text = pub
        guid = SubElement(item, "guid", attrib={"isPermaLink": "false"})
        guid.text = f"l30-ban-{r.id}"

    body = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="utf-8")
    headers: dict[str, str] = {}
    if truncated:
        headers["X-Truncated"] = "true"
    return Response(
        content=body,
        media_type="application/rss+xml; charset=utf-8",
        headers=headers,
    )
@router.get("/public/timeline", response_model=BanReportTimelineResponse)
async def get_public_timeline(
    state: str | None = Query(None, description="Filter by US state code (2-letter)"),
    ban_type: str | None = Query(None, description="Filter by ban type"),
    reason_category: str | None = Query(None, description="Filter by reason category"),
    source: str | None = Query(None, description="Filter by source"),
    db: AsyncSession = Depends(get_db),
):
    """Monthly counts of ban reports, grouped by ban_type.

    Empty months between the earliest and latest matching report are
    backfilled with zeros so the chart shows a continuous timeline.
    """
    month_col = func.date_trunc("month", BanReport.date_reported).label("month")
    stmt = (
        select(month_col, BanReport.ban_type, func.count().label("n"))
        .where(BanReport.date_reported.is_not(None))
        .group_by(month_col, BanReport.ban_type)
        .order_by(month_col)
    )
    if state:
        stmt = stmt.where(BanReport.state == state.upper())
    if ban_type:
        stmt = stmt.where(BanReport.ban_type == ban_type.lower())
    if reason_category:
        stmt = stmt.where(BanReport.reason_category == reason_category)
    if source:
        stmt = stmt.where(BanReport.source == source.lower())

    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        return BanReportTimelineResponse(buckets=[])

    # Pivot into {month_key: {ban_type: count}}
    pivoted: dict[str, dict[str, int]] = {}
    months_seen: list[datetime] = []
    for month_dt, bt, n in rows:
        key = month_dt.strftime("%Y-%m")
        if key not in pivoted:
            pivoted[key] = {"banned": 0, "restricted": 0, "challenged": 0, "pending": 0}
            months_seen.append(month_dt)
        bt_val = bt.value if hasattr(bt, "value") else str(bt)
        bt_val = bt_val.lower()
        if bt_val in pivoted[key]:
            pivoted[key][bt_val] = int(n)

    # Fill empty months between earliest and latest
    earliest = min(months_seen)
    latest = max(months_seen)
    buckets: list[BanReportTimelineBucket] = []
    cursor = earliest.replace(day=1)
    end = latest.replace(day=1)
    while cursor <= end:
        key = cursor.strftime("%Y-%m")
        counts = pivoted.get(key, {"banned": 0, "restricted": 0, "challenged": 0, "pending": 0})
        buckets.append(BanReportTimelineBucket(month=key, **counts))
        # advance one month
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    return BanReportTimelineResponse(buckets=buckets)


@router.post("/public/submit", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def submit_public_ban_report(  # noqa: role-check -- patron submission, Turnstile-gated, queued for staff review
    submission: PublicBanReportSubmission,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Anonymous patron ban-report submission. Turnstile-gated.

    The row is always stored with ``ban_type='pending'`` regardless of the
    submitted classification — staff verify it in the compliance dashboard
    before it appears in the public tracker. The patron's classification is
    preserved by prefixing the notes field.
    """
    client_ip = request.client.host if request.client else None
    if not await verify_turnstile(submission.turnstile_token, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    notes_prefix = f"Patron-submitted classification: {submission.ban_type}. "
    combined_notes = notes_prefix + (submission.notes or "")

    report = BanReport(
        title=submission.title,
        author=submission.author,
        state=submission.state,
        district=submission.district,
        institution=submission.institution,
        ban_type=BanType.PENDING,
        reason_category=submission.reason_category,
        source=BanSource.STAFF_ENTRY,
        source_url=str(submission.source_url) if submission.source_url else None,
        date_reported=date.today(),
        notes=combined_notes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {"status": "pending_review", "id": report.id}


# ============================================================================
# Staff Endpoints
# ============================================================================


@router.get("/reports/stats", response_model=BanReportStats)
async def get_report_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detailed ban report stats (staff only)."""
    _ensure_staff(current_user)
    stats = await BanTrackerService.get_statistics(db)
    return BanReportStats(**stats)


@router.get("/reports/matches", response_model=PaginatedBanReports)
async def list_catalog_matched_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List ban reports that have a catalog match (staff only)."""
    _ensure_staff(current_user)
    reports, total = await BanTrackerService.get_catalog_matches(
        db,
        page=page,
        per_page=per_page,
    )
    return PaginatedBanReports(
        items=await _serialize_reports_with_rationale(reports, db),
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/reports", response_model=PaginatedBanReports)
async def list_reports(
    state: str | None = Query(None),
    ban_type: str | None = Query(None),
    source: str | None = Query(None),
    reason_category: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all ban reports with full detail (staff only)."""
    _ensure_staff(current_user)
    reports, total = await BanTrackerService.list_reports(
        db,
        state=state,
        ban_type=ban_type,
        source=source,
        reason_category=reason_category,
        search=search,
        page=page,
        per_page=per_page,
    )
    return PaginatedBanReports(
        items=await _serialize_reports_with_rationale(reports, db),
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 1,
    )


@router.post("/reports", response_model=BanReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: BanReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual ban report entry (staff only)."""
    _ensure_staff(current_user)
    data = report_data.model_dump()
    data["created_by_id"] = current_user.id
    report = await BanTrackerService.create_report(db, data)
    return BanReportResponse.model_validate(report)


@router.get("/reports/{report_id}", response_model=BanReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single ban report (staff only)."""
    _ensure_staff(current_user)
    report = await BanTrackerService.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ban report not found")
    return await _serialize_with_rationale(report, RationaleService(db))


@router.put("/reports/{report_id}", response_model=BanReportResponse)
async def update_report(
    report_id: int,
    update_data: BanReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a ban report (staff only)."""
    _ensure_staff(current_user)
    report = await BanTrackerService.update_report(
        db, report_id, update_data.model_dump(exclude_unset=True)
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ban report not found")
    return BanReportResponse.model_validate(report)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a ban report (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete reports",
        )
    success = await BanTrackerService.delete_report(db, report_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ban report not found")


# ============================================================================
# Alert Endpoints
# ============================================================================


@router.get("/alerts", response_model=list[BanAlertResponse])
async def get_my_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unseen ban alerts for the current user."""
    alerts = await BanAlertService.get_unseen_alerts(db, current_user.id)
    return [BanAlertResponse.model_validate(a) for a in alerts]


@router.get("/alerts/count")
async def get_alert_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get count of unseen ban alerts for the current user."""
    count = await BanAlertService.get_unseen_count(db, current_user.id)
    return {"count": count}


@router.post("/alerts/{alert_id}/seen", response_model=BanAlertResponse)
async def mark_alert_seen(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single ban alert as seen."""
    alert = await BanAlertService.mark_seen(db, alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return BanAlertResponse.model_validate(alert)


@router.post("/alerts/mark-all-seen")
async def mark_all_alerts_seen(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark all unseen alerts as seen for the current user."""
    count = await BanAlertService.mark_all_seen(db, current_user.id)
    return {"marked_seen": count}


# ============================================================================
# Sync Endpoints
# ============================================================================


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger a manual PEN America data sync (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    result = await BanTrackerService.trigger_pen_america_sync(db)
    return result


@router.post("/sync/csv")
async def upload_csv_sync(
    file: UploadFile = File(..., description="CSV file exported from PEN America's index"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a PEN America CSV file to import ban reports (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted",
        )
    contents = await file.read()
    csv_text = contents.decode("utf-8-sig")
    result = await PenAmericaSyncService.sync_from_csv(db, csv_text)
    return result


@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get status of the last PEN America sync (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    status_info = await BanTrackerService.get_sync_status(db)
    return status_info


# ============================================================================
# Advocacy Router - Public Endpoints
# ============================================================================


@advocacy_router.get("/reps", response_model=CivicLookupResponse)
async def lookup_reps(
    address: str = Query(..., description="Street address for representative lookup"),
):
    officials, not_configured = await CivicApiService.lookup_reps(address)
    return CivicLookupResponse(
        address=address,
        officials=[RepresentativeInfo(**o) for o in officials],
        not_configured=not_configured,
    )


@advocacy_router.get("/letter-templates", response_model=list[LetterTemplateResponse])
async def list_letter_templates(
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AdvocacyLetterTemplate)
        .where(AdvocacyLetterTemplate.is_active == True)  # noqa: E712
        .order_by(AdvocacyLetterTemplate.id)
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [LetterTemplateResponse.model_validate(t) for t in templates]


@advocacy_router.get("/letter-templates/{template_id}", response_model=LetterTemplateResponse)
async def get_letter_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AdvocacyLetterTemplate).where(AdvocacyLetterTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Letter template not found",
        )
    return LetterTemplateResponse.model_validate(template)


# ============================================================================
# Advocacy Router - Staff Endpoints
# ============================================================================


@advocacy_router.post(
    "/letter-templates",
    response_model=LetterTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_letter_template(
    template_data: LetterTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)
    template = AdvocacyLetterTemplate(**template_data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return LetterTemplateResponse.model_validate(template)


@advocacy_router.put("/letter-templates/{template_id}", response_model=LetterTemplateResponse)
async def update_letter_template(
    template_id: int,
    update_data: LetterTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)
    stmt = select(AdvocacyLetterTemplate).where(AdvocacyLetterTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Letter template not found",
        )
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return LetterTemplateResponse.model_validate(template)


@advocacy_router.delete("/letter-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_letter_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_staff(current_user)
    stmt = select(AdvocacyLetterTemplate).where(AdvocacyLetterTemplate.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Letter template not found",
        )
    await db.delete(template)
    await db.commit()
