# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding Reports API

Routes:
  GET  /dashboard
  GET  /reports/weekly-summary
  POST /sessions/{session_id}/family-snapshot/reveal
  GET  /sessions/{session_id}/family-snapshot
  GET  /patrons/{patron_id}/consent/family-snapshot
  POST /patrons/{patron_id}/consent/family-snapshot
"""
import contextlib
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.parent_onboarding import (
    ParentOnboardingDashboard,
)
from ....schemas.family_snapshot import (
    FamilySnapshotResponse,
    PatronConsentDecision,
    PatronConsentRead,
    PatronConsentStatusResponse,
)
from ....services import pii_access_log_service
from ....services import family_snapshot_service
from ....services import parent_onboarding_report_service
from ....services.parent_onboarding import (
    ParentOnboardingDashboardService,
    ParentOnboardingSessionService,
)
from ..auth import get_current_user
from ..dependencies import require_staff

router = APIRouter()


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/dashboard", response_model=ParentOnboardingDashboard)
async def get_dashboard(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get parent onboarding dashboard metrics (staff-only)."""
    metrics = await ParentOnboardingDashboardService.get_dashboard(db)
    return ParentOnboardingDashboard(**metrics)


# ============================================================================
# Weekly Summary Export (CSV)
# ============================================================================


@router.get(
    "/reports/weekly-summary",
    summary="Anonymized 7-day rollup of parent-onboarding activity (CSV)",
)
async def get_weekly_summary_report(
    format: str = Query(..., description="Output format: 'csv' (PDF deferred)"),
    end_date: Optional[date] = Query(
        None,
        description=(
            "End of the reporting window (exclusive). Defaults to today "
            "in the server timezone. The report covers [end_date - 7, end_date)."
        ),
    ),
    coordinator_id: Optional[str] = Query(
        None,
        description=(
            "Restrict the report to one coordinator's activity. "
            "Pass an integer user id or the literal string 'me' to use the "
            "requester's id. Omit for a whole-team report."
        ),
    ),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the anonymized weekly summary report.

    Staff-role gated. No feature flag (gated by the parent-onboarding
    module flag at the router level).

    PDF is intentionally rejected with 422 until weasyprint is added to
    the backend image; the spec defers PDF to v1.1.
    """
    if format not in {"csv", "pdf"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="format must be 'csv' or 'pdf'",
        )
    if format == "pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF export is not yet available; use format=csv",
        )

    today = datetime.now(timezone.utc).date()
    effective_end_date = end_date or today
    if effective_end_date > today + timedelta(days=1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must not be more than one day in the future",
        )

    coordinator: Optional[User] = None
    resolved_coordinator_id: Optional[int] = None
    if coordinator_id is not None and coordinator_id != "":
        if coordinator_id == "me":
            coordinator = current_user
            resolved_coordinator_id = current_user.id
        else:
            try:
                coord_int = int(coordinator_id)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="coordinator_id must be an integer or 'me'",
                ) from None
            coord_row = (
                await db.execute(select(User).where(User.id == coord_int))
            ).scalar_one_or_none()
            if coord_row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="coordinator not found",
                )
            coordinator = coord_row
            resolved_coordinator_id = coord_int

    summary = await parent_onboarding_report_service.compute_weekly_summary(
        db,
        end_date=effective_end_date,
        coordinator=coordinator,
    )

    csv_body = parent_onboarding_report_service.render_csv(summary)
    filename = parent_onboarding_report_service.filename_for(summary, "csv")

    await parent_onboarding_report_service.write_export_audit_log(
        db,
        user_id=current_user.id,
        fmt="csv",
        start_date=summary.start_date,
        end_date=summary.end_date,
        coordinator_id=resolved_coordinator_id,
        row_count=len(summary.activity),
    )

    return StreamingResponse(
        iter([csv_body]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ============================================================================
# Family Snapshot pane (read-only, consent-gated)
#
# NOTE: literal sub-route /sessions/{session_id}/family-snapshot/reveal
# is declared BEFORE the plain GET so FastAPI's registration order is correct.
# ============================================================================


@router.post(
    "/sessions/{session_id}/family-snapshot/reveal",
    response_model=FamilySnapshotResponse,
)
async def reveal_session_family_snapshot(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the full (un-redacted) family-snapshot payload.

    Requires an active ``family_snapshot`` consent on the patron. Writes
    a ``pii_access_log`` row with ``action="reveal"``.
    """
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    consent = await family_snapshot_service.get_consent_status(
        db, session.patron_id
    )
    if consent.consent_status != "granted":
        raise HTTPException(
            status_code=403,
            detail="Patron has not consented to family-snapshot data sharing.",
        )

    payload = await family_snapshot_service.build_family_snapshot(
        db, session=session, reveal=True
    )

    await pii_access_log_service.log_access(
        db,
        user_id=current_user.id,
        patron_id=session.patron_id,
        subject_type="parent_onboarding.family_snapshot.reveal",
        subject_id=session.id,
        action="reveal",
        user_role=current_user.role,
        reason="staff_reveal",
    )

    await db.commit()
    return payload


@router.get(
    "/sessions/{session_id}/family-snapshot",
    response_model=FamilySnapshotResponse,
)
async def get_session_family_snapshot(
    session_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Return the redacted family-snapshot for a parent-onboarding session."""
    session = await ParentOnboardingSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    payload = await family_snapshot_service.build_family_snapshot(
        db, session=session, reveal=False
    )

    await pii_access_log_service.log_access(
        db,
        user_id=current_user.id,
        patron_id=session.patron_id,
        subject_type="parent_onboarding.family_snapshot",
        subject_id=session.id,
        action="read",
        user_role=current_user.role,
        reason="staff_view",
    )

    await db.commit()
    return payload


@router.get(
    "/patrons/{patron_id}/consent/family-snapshot",
    response_model=PatronConsentStatusResponse,
)
async def get_patron_family_snapshot_consent(
    patron_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight read for the consent state on a patron."""
    return await family_snapshot_service.get_consent_status(db, patron_id)


@router.post(
    "/patrons/{patron_id}/consent/family-snapshot",
    response_model=PatronConsentRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_patron_family_snapshot_consent(
    patron_id: int,
    data: PatronConsentDecision,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record (or revoke) a patron's family-snapshot consent."""
    patron_stmt = select(User).where(User.id == patron_id)
    patron = (await db.execute(patron_stmt)).scalar_one_or_none()
    if patron is None:
        raise HTTPException(status_code=404, detail="Patron not found")

    row = await family_snapshot_service.record_consent(
        db,
        patron_id=patron_id,
        granted=data.granted,
        recorded_by_staff_id=current_user.id,
        notes=data.notes,
    )

    await pii_access_log_service.log_access(
        db,
        user_id=current_user.id,
        patron_id=patron_id,
        subject_type="patron_consent.family_snapshot",
        subject_id=row.id,
        action="read",
        user_role=current_user.role,
        reason="record_consent",
    )

    await db.commit()
    return PatronConsentRead.model_validate(row)
