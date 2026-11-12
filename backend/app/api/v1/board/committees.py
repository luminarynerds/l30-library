# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board committee management API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.audit_log import audit_log_event
from ....models.board import Committee, CommitteeMember, BoardMember, BoardMeeting, BoardDocument
from ....models.user import User, UserRole
from ....schemas.board import (
    CommitteeCreate, CommitteeUpdate, CommitteeResponse, CommitteeWithMembersResponse, CommitteeMemberNested,
    CommitteeMemberCreate, CommitteeMemberUpdate, CommitteeMemberRemove, CommitteeMemberResponse,
)
from ..auth import get_current_user
from ..dependencies import is_admin

router = APIRouter(prefix="/board/committees", tags=["board-committees"])


# ============ Public Committee Endpoints ============


@router.get("", response_model=List[CommitteeResponse])
async def get_committees(
    include_inactive: bool = Query(False, description="Include inactive/dissolved committees"),
    committee_type: Optional[str] = Query(None, description="Filter by committee type"),
    db: AsyncSession = Depends(get_db),
):
    """Get list of board committees (public endpoint for active committees)."""
    query = select(Committee).where(Committee.is_public == True)

    if not include_inactive:
        query = query.where(Committee.status == "active")

    if committee_type:
        query = query.where(Committee.committee_type == committee_type)

    query = query.order_by(Committee.name)

    result = await db.execute(query)
    return result.scalars().all()



@router.get("/with-members", response_model=List[CommitteeWithMembersResponse])
async def get_committees_with_members(
    include_inactive: bool = Query(False, description="Include inactive/dissolved committees"),
    db: AsyncSession = Depends(get_db),
):
    """Get all committees with their members eagerly loaded (single query)."""
    query = select(Committee).where(Committee.is_public == True)

    if not include_inactive:
        query = query.where(Committee.status == "active")

    query = query.options(
        selectinload(Committee.members).selectinload(CommitteeMember.board_member)
    ).order_by(Committee.name)

    result = await db.execute(query)
    committees = result.scalars().all()

    response = []
    for committee in committees:
        members_nested = [
            CommitteeMemberNested(
                id=cm.id,
                board_member_id=cm.board_member_id,
                board_member_name=cm.board_member.full_name,
                board_member_position=cm.board_member.position or "member",
                role=cm.role,
                is_active=cm.is_active,
            )
            for cm in committee.members
            if cm.board_member is not None
        ]
        committee_dict = CommitteeResponse.model_validate(committee).model_dump()
        committee_dict["members"] = members_nested
        response.append(committee_dict)

    return response


@router.get("/{committee_id}", response_model=CommitteeResponse)
async def get_committee(committee_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific committee."""
    committee = await get_or_404(db, Committee, committee_id, "Committee not found")

    # Only return if public or user is authenticated
    if not committee.is_public:
        raise HTTPException(status_code=404, detail="Committee not found")

    return committee


@router.get("/{committee_id}/members", response_model=List[CommitteeMemberResponse])
async def get_committee_members(
    committee_id: int,
    include_inactive: bool = Query(False, description="Include former members"),
    db: AsyncSession = Depends(get_db),
):
    """Get members of a committee."""
    # Verify committee exists and is public
    committee_result = await db.execute(
        select(Committee).where(Committee.id == committee_id)
    )
    committee = committee_result.scalar_one_or_none()
    if not committee or not committee.is_public:
        raise HTTPException(status_code=404, detail="Committee not found")

    query = select(CommitteeMember).where(CommitteeMember.committee_id == committee_id)

    if not include_inactive:
        query = query.where(CommitteeMember.is_active == True)

    query = query.order_by(CommitteeMember.role, CommitteeMember.appointed_date)

    result = await db.execute(query)
    return result.scalars().all()


# ============ Authenticated Committee Endpoints ============


@router.post("", response_model=CommitteeResponse, status_code=status.HTTP_201_CREATED)
async def create_committee(
    committee: CommitteeCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new committee (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate parent committee if provided
    if committee.parent_committee_id:
        parent_result = await db.execute(
            select(Committee).where(Committee.id == committee.parent_committee_id)
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Parent committee not found")

    db_committee = Committee(
        **committee.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(db_committee)
    await db.commit()
    await db.refresh(db_committee)
    audit_log_event(
        event_type="BOARD_COMMITTEE_CREATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"committee_id": db_committee.id, "entity_type": "Committee", "name": db_committee.name},
    )
    return db_committee


@router.put("/{committee_id}", response_model=CommitteeResponse)
async def update_committee(
    committee_id: int,
    committee: CommitteeUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a committee (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    db_committee = await get_or_404(db, Committee, committee_id, "Committee not found")

    for key, value in committee.model_dump(exclude_unset=True).items():
        setattr(db_committee, key, value)

    db_committee.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_committee)
    audit_log_event(
        event_type="BOARD_COMMITTEE_UPDATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"committee_id": committee_id, "entity_type": "Committee", "updated_fields": list(committee.model_dump(exclude_unset=True).keys())},
    )
    return db_committee


@router.post("/{committee_id}/dissolve")
async def dissolve_committee(
    committee_id: int,
    request: Request,
    reason: str = Query(..., description="Reason for dissolution"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dissolve a committee (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    db_committee = await get_or_404(db, Committee, committee_id, "Committee not found")

    if db_committee.status == "dissolved":
        raise HTTPException(status_code=400, detail="Committee is already dissolved")

    db_committee.status = "dissolved"
    db_committee.dissolution_date = datetime.now(timezone.utc)
    db_committee.dissolution_reason = reason
    db_committee.updated_at = datetime.now(timezone.utc)

    # Deactivate all members
    members_result = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee_id,
            CommitteeMember.is_active == True
        )
    )
    for member in members_result.scalars().all():
        member.is_active = False
        member.removed_date = datetime.now(timezone.utc)
        member.removal_reason = "Committee dissolved"
        member.removed_by_id = current_user.id

    await db.commit()
    audit_log_event(
        event_type="BOARD_COMMITTEE_DISSOLVED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"committee_id": committee_id, "entity_type": "Committee", "name": db_committee.name, "reason": reason},
    )
    return {"message": "Committee dissolved", "dissolution_date": db_committee.dissolution_date}


@router.delete("/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_committee(
    committee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a committee (super admin only). Use dissolve for normal cases."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin access required")

    db_committee = await get_or_404(db, Committee, committee_id, "Committee not found")

    audit_log_event(
        event_type="BOARD_COMMITTEE_DELETED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"committee_id": committee_id, "entity_type": "Committee", "name": db_committee.name},
    )
    await db.delete(db_committee)
    await db.commit()


# ============ Committee Member Endpoints ============


@router.post("/{committee_id}/members", response_model=CommitteeMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_committee_member(
    committee_id: int,
    member: CommitteeMemberCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to a committee (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Verify committee exists and is active
    committee = await get_or_404(db, Committee, committee_id, "Committee not found")
    if committee.status != "active":
        raise HTTPException(status_code=400, detail="Cannot add members to inactive/dissolved committee")

    # Verify board member exists
    board_member_result = await db.execute(
        select(BoardMember).where(BoardMember.id == member.board_member_id)
    )
    if not board_member_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Board member not found")

    # Check if already a member
    existing_result = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee_id,
            CommitteeMember.board_member_id == member.board_member_id,
            CommitteeMember.is_active == True
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Board member is already on this committee")

    # Check max members
    if committee.max_members:
        current_count_result = await db.execute(
            select(CommitteeMember).where(
                CommitteeMember.committee_id == committee_id,
                CommitteeMember.is_active == True
            )
        )
        current_count = len(current_count_result.scalars().all())
        if current_count >= committee.max_members:
            raise HTTPException(
                status_code=400,
                detail=f"Committee has reached maximum of {committee.max_members} members"
            )

    # If assigning chair role, check if there's already a chair
    if member.role == "chair":
        existing_chair_result = await db.execute(
            select(CommitteeMember).where(
                CommitteeMember.committee_id == committee_id,
                CommitteeMember.role == "chair",
                CommitteeMember.is_active == True
            )
        )
        if existing_chair_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Committee already has a chair. Remove current chair first."
            )

    db_member = CommitteeMember(
        committee_id=committee_id,
        board_member_id=member.board_member_id,
        role=member.role,
        appointed_date=member.appointed_date,
        term_end_date=member.term_end_date,
        appointment_notes=member.appointment_notes,
        created_by_id=current_user.id,
    )
    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)
    audit_log_event(
        event_type="BOARD_COMMITTEE_MEMBER_ADDED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"committee_id": committee_id, "entity_type": "CommitteeMember", "member_id": db_member.id, "board_member_id": member.board_member_id, "role": member.role},
    )
    return db_member


@router.put("/{committee_id}/members/{member_id}", response_model=CommitteeMemberResponse)
async def update_committee_member(
    committee_id: int,
    member_id: int,
    member: CommitteeMemberUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a committee member (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.id == member_id,
            CommitteeMember.committee_id == committee_id
        )
    )
    db_member = result.scalar_one_or_none()
    if not db_member:
        raise HTTPException(status_code=404, detail="Committee member not found")

    # If changing to chair, check if there's already a chair
    if member.role == "chair" and db_member.role != "chair":
        existing_chair_result = await db.execute(
            select(CommitteeMember).where(
                CommitteeMember.committee_id == committee_id,
                CommitteeMember.role == "chair",
                CommitteeMember.is_active == True,
                CommitteeMember.id != member_id
            )
        )
        if existing_chair_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Committee already has a chair. Remove current chair first."
            )

    for key, value in member.model_dump(exclude_unset=True).items():
        setattr(db_member, key, value)

    db_member.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_member)
    audit_log_event(
        event_type="BOARD_COMMITTEE_MEMBER_UPDATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"committee_id": committee_id, "entity_type": "CommitteeMember", "member_id": member_id, "updated_fields": list(member.model_dump(exclude_unset=True).keys())},
    )
    return db_member


@router.post("/{committee_id}/members/{member_id}/remove")
async def remove_committee_member(
    committee_id: int,
    member_id: int,
    removal: CommitteeMemberRemove,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from a committee (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(CommitteeMember).where(
            CommitteeMember.id == member_id,
            CommitteeMember.committee_id == committee_id
        )
    )
    db_member = result.scalar_one_or_none()
    if not db_member:
        raise HTTPException(status_code=404, detail="Committee member not found")

    if not db_member.is_active:
        raise HTTPException(status_code=400, detail="Member is already inactive")

    db_member.is_active = False
    db_member.removed_date = datetime.now(timezone.utc)
    db_member.removal_reason = removal.removal_reason
    db_member.removed_by_id = current_user.id
    db_member.updated_at = datetime.now(timezone.utc)

    await db.commit()
    audit_log_event(
        event_type="BOARD_COMMITTEE_MEMBER_REMOVED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"committee_id": committee_id, "entity_type": "CommitteeMember", "member_id": member_id, "reason": removal.removal_reason},
    )
    return {"message": "Committee member removed"}


# ============ Committee Meetings & Documents ============


@router.get("/{committee_id}/meetings")
async def get_committee_meetings(
    committee_id: int,
    upcoming_only: bool = Query(False, description="Only return upcoming meetings"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get meetings for a specific committee."""
    # Verify committee exists
    committee_result = await db.execute(
        select(Committee).where(Committee.id == committee_id)
    )
    if not committee_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Committee not found")

    query = select(BoardMeeting).where(
        BoardMeeting.committee_id == committee_id,
        BoardMeeting.is_cancelled == False
    )

    if upcoming_only:
        query = query.where(BoardMeeting.scheduled_date >= datetime.now(timezone.utc))
        query = query.order_by(BoardMeeting.scheduled_date.asc())
    else:
        query = query.order_by(BoardMeeting.scheduled_date.desc())

    query = query.limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{committee_id}/documents")
async def get_committee_documents(
    committee_id: int,
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get documents for a specific committee."""
    # Verify committee exists and is public
    await get_or_404(db, Committee, committee_id, "Committee not found")

    query = select(BoardDocument).where(
        BoardDocument.committee_id == committee_id,
        BoardDocument.is_public == True,
        BoardDocument.status == "published"
    )

    if document_type:
        query = query.where(BoardDocument.document_type == document_type)

    query = query.order_by(BoardDocument.published_date.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
