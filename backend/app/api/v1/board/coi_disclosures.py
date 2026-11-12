# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board COI (Conflict of Interest) disclosure API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.audit_log import audit_log_event
from ....models.board import BoardMember
from ....models.board.coi_disclosure import BoardCOIDisclosure, COI_CATEGORIES
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import COIDisclosureCreate, COIDisclosureResponse, COIComplianceStatus
from ..auth import get_current_user

router = APIRouter(prefix="/board/coi-disclosures", tags=["board-coi"])


@router.post("", response_model=COIDisclosureResponse, status_code=201)
async def submit_disclosure(
    body: COIDisclosureCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a COI disclosure (board members only)."""
    member_result = await db.execute(
        select(BoardMember).where(
            and_(BoardMember.user_id == current_user.id, BoardMember.is_current == True)
        )
    )
    board_member = member_result.scalar_one_or_none()
    if not board_member:
        raise HTTPException(status_code=403, detail="Only current board members can submit disclosures")

    # Validate categories
    for cat in (body.categories or []):
        if cat not in COI_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category: {cat}")

    # Supersede previous current disclosures for this member
    prev_result = await db.execute(
        select(BoardCOIDisclosure).where(
            and_(
                BoardCOIDisclosure.board_member_id == board_member.id,
                BoardCOIDisclosure.is_current == True,
            )
        )
    )
    previous = prev_result.scalars().all()

    disclosure = BoardCOIDisclosure(
        board_member_id=board_member.id,
        fiscal_year=body.fiscal_year,
        disclosure_text=body.disclosure_text,
        categories=body.categories or [],
        keywords=[k.lower() for k in (body.keywords or [])],
        attestation_statement=body.attestation_statement,
    )
    db.add(disclosure)
    await db.flush()

    for prev in previous:
        prev.is_current = False
        prev.superseded_by_id = disclosure.id
        prev.superseded_at = datetime.now(timezone.utc)
        db.add(BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.COI_DISCLOSURE_SUPERSEDED,
            entity_type="BoardCOIDisclosure",
            entity_id=prev.id,
            details={"superseded_by": disclosure.id, "member_name": board_member.full_name},
        ))

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.COI_DISCLOSURE_SUBMITTED,
        entity_type="BoardCOIDisclosure",
        entity_id=disclosure.id,
        details={
            "fiscal_year": body.fiscal_year,
            "categories": body.categories,
            "member_name": board_member.full_name,
        },
    ))
    await db.commit()
    await db.refresh(disclosure)

    audit_log_event(
        event_type="BOARD_COI_DISCLOSURE_SUBMITTED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"disclosure_id": disclosure.id, "entity_type": "BoardCOIDisclosure", "fiscal_year": body.fiscal_year, "member_name": board_member.full_name},
    )

    return disclosure


@router.get("/compliance", response_model=COIComplianceStatus)
async def check_compliance(
    fiscal_year: str = Query(..., max_length=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check COI compliance for a fiscal year (director/admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Director or admin access required")

    members_result = await db.execute(
        select(BoardMember).where(BoardMember.is_current == True)
    )
    current_members = members_result.scalars().all()

    filed_result = await db.execute(
        select(BoardCOIDisclosure.board_member_id).where(
            and_(
                BoardCOIDisclosure.fiscal_year == fiscal_year,
                BoardCOIDisclosure.is_current == True,
            )
        ).distinct()
    )
    filed_ids = {row for row in filed_result.scalars().all()}

    filed = []
    not_filed = []
    for m in current_members:
        entry = {"id": m.id, "full_name": m.full_name}
        if m.id in filed_ids:
            filed.append(entry)
        else:
            not_filed.append(entry)

    return COIComplianceStatus(
        fiscal_year=fiscal_year,
        total_members=len(current_members),
        filed_count=len(filed),
        not_filed_count=len(not_filed),
        filed=filed,
        not_filed=not_filed,
    )


@router.get("/{disclosure_id}", response_model=COIDisclosureResponse)
async def get_disclosure(
    disclosure_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single COI disclosure."""
    disclosure = await get_or_404(db, BoardCOIDisclosure, disclosure_id, "Disclosure not found")

    # Members can see own; director/admin/legal can see all
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]:
        member_result = await db.execute(
            select(BoardMember).where(
                and_(BoardMember.user_id == current_user.id, BoardMember.is_current == True)
            )
        )
        board_member = member_result.scalar_one_or_none()
        if not board_member or disclosure.board_member_id != board_member.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return disclosure


@router.get("", response_model=List[COIDisclosureResponse])
async def list_disclosures(
    board_member_id: Optional[int] = Query(None),
    fiscal_year: Optional[str] = Query(None, max_length=10),
    current_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List COI disclosures. Members see own; director/admin/legal see all."""
    is_privileged = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]

    query = select(BoardCOIDisclosure)
    filters = []

    if not is_privileged:
        # Non-privileged: restrict to own disclosures
        member_result = await db.execute(
            select(BoardMember).where(
                and_(BoardMember.user_id == current_user.id, BoardMember.is_current == True)
            )
        )
        board_member = member_result.scalar_one_or_none()
        if not board_member:
            return []
        filters.append(BoardCOIDisclosure.board_member_id == board_member.id)
    elif board_member_id is not None:
        filters.append(BoardCOIDisclosure.board_member_id == board_member_id)

    if fiscal_year:
        filters.append(BoardCOIDisclosure.fiscal_year == fiscal_year)
    if current_only:
        filters.append(BoardCOIDisclosure.is_current == True)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(BoardCOIDisclosure.attested_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
