# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board governance API - thin aggregator router.

This module creates the main board router and includes all domain-specific
sub-routers. Each sub-router handles a specific area of board governance:

- members.py     - Board member management
- meetings.py    - Meeting CRUD, scheduling, agenda, attendance, briefs
- minutes.py     - Minute taking, approval workflow
- voting.py      - Vote creation, casting, open/close, tally
- documents.py   - Document management, publish/archive lifecycle
- attendance.py  - Extended attendance tracking with audit logging
- action_items.py - Action item tracking and status management
- notices.py     - Public meeting notice generation and compliance
- motions.py     - Motions and resolutions
- committees.py  - Committee management
- public.py      - Unauthenticated notice-gated public transparency API
- reports.py     - Board report generation (PDF, PowerPoint)
- pdf_exports.py - PDF export endpoints for agendas, minutes, notices, packets
- retention.py   - Records retention schedules and legal holds
- coi_disclosures.py - Conflict of interest disclosure management

All URL paths are preserved from the original monolithic router.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.board import BoardMinutes
from ....schemas.board import BoardMinutesResponse
from ....services.organization_features_service import OrganizationFeaturesService

# Import all sub-routers
from . import (
    audit_logs,
    action_items,
    attendance,
    coi_disclosures,
    committees,
    dashboard,
    documents,
    meetings,
    members,
    minutes,
    motions,
    notices,
    pdf_exports,
    public,
    public_comments,
    recusals,
    reports,
    retention,
    voting,
)

async def require_board_features_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "board_features_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board features are not enabled",
        )


# The main board router aggregates all sub-routers.
# Sub-routers define their own prefixes (e.g., /board/meetings, /board/votes),
# so this router has no prefix. The registry mounts it at /api/v1, producing
# final paths like /api/v1/board/meetings/...
router = APIRouter(
    tags=["board"],
    dependencies=[Depends(require_board_features_enabled)],
)

# ============ Top-level Board Routes ============
# Routes that don't fit into a specific sub-domain are defined here.


@router.get("/board/minutes", response_model=List[BoardMinutesResponse])
async def get_approved_minutes(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get approved meeting minutes (public)."""
    query = (
        select(BoardMinutes)
        .where(BoardMinutes.approved == True)
        .order_by(BoardMinutes.approved_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


# ============ Include Sub-Routers ============
# Each sub-router has its own prefix (e.g., /board/meetings, /board/votes),
# so they are included without additional prefix.

# Core board management
router.include_router(members.router)
router.include_router(meetings.router)
router.include_router(minutes.router)
router.include_router(voting.router)
router.include_router(documents.router)

# Extended attendance tracking (audit-logged endpoints)
router.include_router(attendance.router)

# Governance workflow
router.include_router(action_items.router)
router.include_router(notices.router)
router.include_router(motions.router)
router.include_router(committees.router)
router.include_router(public_comments.router)
router.include_router(public.router)

# Reports and PDF exports
router.include_router(reports.router)
router.include_router(pdf_exports.router)

# Audit trail access
router.include_router(recusals.router)
router.include_router(audit_logs.router)

# Records retention and COI
router.include_router(retention.router)
router.include_router(coi_disclosures.router)

# Dashboard
router.include_router(dashboard.router)
