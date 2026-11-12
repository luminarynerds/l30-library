# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board motions and resolutions API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import (
    BoardMotion, BoardResolution, BoardMeeting, BoardMember, BoardVote, Committee
)
from ....models.user import User, UserRole
from ....schemas.board import (
    MotionCreate, MotionUpdate, MotionResponse, MotionSecond, MotionRefer, MotionTable, MotionWithdraw,
    ResolutionCreate, ResolutionUpdate, ResolutionResponse, ResolutionAdopt, ResolutionSupersede, ResolutionRescind,
)
from ..auth import get_current_user

router = APIRouter(prefix="/board", tags=["board-motions"])


# ============ Motion Endpoints ============


@router.get("/motions", response_model=List[MotionResponse])
async def list_all_motions(
    status: Optional[str] = Query(None, description="Filter by status"),
    meeting_id: Optional[int] = Query(None, description="Filter by meeting"),
    motion_type: Optional[str] = Query(None, description="Filter by type"),
    include_all: bool = Query(False, description="Include all statuses"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all motions across all meetings."""
    query = select(BoardMotion).options(
        selectinload(BoardMotion.moved_by),
        selectinload(BoardMotion.seconded_by),
    )

    if status and not include_all:
        query = query.where(BoardMotion.status == status)
    if meeting_id:
        query = query.where(BoardMotion.meeting_id == meeting_id)
    if motion_type:
        query = query.where(BoardMotion.motion_type == motion_type)

    query = query.order_by(BoardMotion.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/motions/{motion_id}", response_model=MotionResponse)
async def get_motion(
    motion_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single motion by ID."""
    result = await db.execute(
        select(BoardMotion)
        .where(BoardMotion.id == motion_id)
        .options(
            selectinload(BoardMotion.moved_by),
            selectinload(BoardMotion.seconded_by),
        )
    )
    motion = result.scalar_one_or_none()
    if not motion:
        raise HTTPException(status_code=404, detail="Motion not found")
    return motion


@router.get("/meetings/{meeting_id}/motions", response_model=List[MotionResponse])
async def get_meeting_motions(
    meeting_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get motions for a meeting (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Board member or staff access required")

    query = select(BoardMotion).where(BoardMotion.meeting_id == meeting_id)

    if status_filter:
        query = query.where(BoardMotion.status == status_filter)

    query = query.order_by(BoardMotion.moved_at)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/meetings/{meeting_id}/motions", response_model=MotionResponse, status_code=status.HTTP_201_CREATED)
async def create_motion(
    meeting_id: int,
    motion: MotionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new motion (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Verify meeting exists and is not cancelled
    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")
    if meeting.is_cancelled:
        raise HTTPException(status_code=400, detail="Cannot add motions to a cancelled meeting")

    # Verify mover is a board member
    mover_result = await db.execute(
        select(BoardMember).where(BoardMember.id == motion.moved_by_id)
    )
    if not mover_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Mover must be a board member")

    # Validate parent motion if this is an amendment
    if motion.parent_motion_id:
        parent_result = await db.execute(
            select(BoardMotion).where(BoardMotion.id == motion.parent_motion_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent motion not found")
        if parent.status not in ["pending", "seconded", "under_discussion"]:
            raise HTTPException(status_code=400, detail="Parent motion is not in a state that can be amended")

    db_motion = BoardMotion(
        meeting_id=meeting_id,
        motion_type=motion.motion_type,
        motion_number=motion.motion_number,
        title=motion.title,
        motion_text=motion.motion_text,
        rationale=motion.rationale,
        moved_by_id=motion.moved_by_id,
        parent_motion_id=motion.parent_motion_id,
        amended_text=motion.amended_text,
        status="pending",
        created_by_id=current_user.id,
    )
    db.add(db_motion)
    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/second", response_model=MotionResponse)
async def second_motion(
    motion_id: int,
    second: MotionSecond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Second a motion (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status != "pending":
        raise HTTPException(status_code=400, detail="Motion must be in pending status to be seconded")

    # Verify seconder is a board member and not the mover
    seconder_result = await db.execute(
        select(BoardMember).where(BoardMember.id == second.seconded_by_id)
    )
    if not seconder_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Seconder must be a board member")

    if second.seconded_by_id == db_motion.moved_by_id:
        raise HTTPException(status_code=400, detail="Seconder cannot be the same as mover")

    db_motion.seconded_by_id = second.seconded_by_id
    db_motion.seconded_at = datetime.now(timezone.utc)
    db_motion.status = "seconded"
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/open-discussion", response_model=MotionResponse)
async def open_motion_discussion(
    motion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open discussion on a motion (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status != "seconded":
        raise HTTPException(status_code=400, detail="Motion must be seconded before discussion")

    db_motion.status = "under_discussion"
    db_motion.discussion_opened_at = datetime.now(timezone.utc)
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/close-discussion", response_model=MotionResponse)
async def close_motion_discussion(
    motion_id: int,
    discussion_notes: Optional[str] = Query(None, description="Notes from discussion"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close discussion and call for vote (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status != "under_discussion":
        raise HTTPException(status_code=400, detail="Motion must be under discussion")

    db_motion.status = "called_to_vote"
    db_motion.discussion_closed_at = datetime.now(timezone.utc)
    db_motion.vote_called_at = datetime.now(timezone.utc)
    if discussion_notes:
        db_motion.discussion_notes = discussion_notes
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/record-outcome", response_model=MotionResponse)
async def record_motion_outcome(
    motion_id: int,
    passed: bool = Query(..., description="Whether the motion passed"),
    vote_id: Optional[int] = Query(None, description="ID of the associated vote record"),
    outcome_notes: Optional[str] = Query(None, description="Notes about the outcome"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record the outcome of a motion vote (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status != "called_to_vote":
        raise HTTPException(status_code=400, detail="Motion must be called to vote")

    db_motion.status = "passed" if passed else "failed"
    db_motion.vote_id = vote_id
    db_motion.outcome_recorded_at = datetime.now(timezone.utc)
    if outcome_notes:
        db_motion.outcome_notes = outcome_notes
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/table", response_model=MotionResponse)
async def table_motion(
    motion_id: int,
    table_data: MotionTable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Table a motion (postpone indefinitely) (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status in ["passed", "failed", "tabled", "withdrawn"]:
        raise HTTPException(status_code=400, detail="Motion is already resolved")

    db_motion.status = "tabled"
    db_motion.tabled_at = datetime.now(timezone.utc)
    db_motion.tabled_until = table_data.tabled_until
    db_motion.tabled_reason = table_data.tabled_reason
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/refer", response_model=MotionResponse)
async def refer_motion(
    motion_id: int,
    refer_data: MotionRefer,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refer a motion to committee (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status in ["passed", "failed", "tabled", "withdrawn", "referred"]:
        raise HTTPException(status_code=400, detail="Motion is already resolved or referred")

    # Verify committee exists
    committee_result = await db.execute(
        select(Committee).where(Committee.id == refer_data.referred_to_committee_id)
    )
    if not committee_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Committee not found")

    db_motion.status = "referred"
    db_motion.referred_to_committee_id = refer_data.referred_to_committee_id
    db_motion.referred_at = datetime.now(timezone.utc)
    db_motion.referred_notes = refer_data.referred_notes
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.post("/motions/{motion_id}/withdraw", response_model=MotionResponse)
async def withdraw_motion(
    motion_id: int,
    withdraw_data: MotionWithdraw,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a motion (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status in ["passed", "failed", "withdrawn"]:
        raise HTTPException(status_code=400, detail="Motion is already resolved")

    db_motion.status = "withdrawn"
    db_motion.withdrawn_at = datetime.now(timezone.utc)
    db_motion.withdrawn_reason = withdraw_data.withdrawn_reason
    db_motion.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.put("/motions/{motion_id}", response_model=MotionResponse)
async def update_motion(
    motion_id: int,
    motion: MotionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update motion details (staff/admin). Only before vote is called."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status in ["called_to_vote", "passed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot update motion after vote is called")

    for key, value in motion.model_dump(exclude_unset=True).items():
        setattr(db_motion, key, value)

    db_motion.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_motion)
    return db_motion


@router.delete("/motions/{motion_id}")
async def delete_motion(
    motion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a motion (admin only). Only pending/draft motions can be deleted."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_motion = await get_or_404(db, BoardMotion, motion_id, "Motion not found")

    if db_motion.status not in ["draft", "pending"]:
        raise HTTPException(
            status_code=400,
            detail="Only draft or pending motions can be deleted. Use withdraw instead."
        )

    await db.delete(db_motion)
    await db.commit()
    return {"message": "Motion deleted"}


# ============ Resolution Endpoints ============


@router.get("/resolutions", response_model=List[ResolutionResponse])
async def get_resolutions(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_public: bool = Query(True, description="Only return public resolutions"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get board resolutions (public endpoint for adopted resolutions)."""
    query = select(BoardResolution)

    if is_public:
        query = query.where(BoardResolution.is_public == True)

    if status_filter:
        query = query.where(BoardResolution.status == status_filter)
    elif is_public:
        # For public queries, only show adopted resolutions by default
        query = query.where(BoardResolution.status == "adopted")

    if category:
        query = query.where(BoardResolution.category == category)

    query = query.order_by(BoardResolution.adopted_date.desc().nullslast()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/resolutions/{resolution_id}", response_model=ResolutionResponse)
async def get_resolution(resolution_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific resolution."""
    resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if not resolution.is_public:
        raise HTTPException(status_code=404, detail="Resolution not found")

    return resolution


@router.post("/resolutions", response_model=ResolutionResponse, status_code=status.HTTP_201_CREATED)
async def create_resolution(
    resolution: ResolutionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new resolution (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Check for duplicate resolution number
    existing_result = await db.execute(
        select(BoardResolution).where(
            BoardResolution.resolution_number == resolution.resolution_number
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Resolution number already exists")

    db_resolution = BoardResolution(
        **resolution.model_dump(),
        status="draft",
        created_by_id=current_user.id,
    )
    db.add(db_resolution)
    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.put("/resolutions/{resolution_id}", response_model=ResolutionResponse)
async def update_resolution(
    resolution_id: int,
    resolution: ResolutionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a resolution (staff/admin). Only before adoption."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status in ["adopted", "superseded", "rescinded"]:
        raise HTTPException(status_code=400, detail="Cannot update adopted/resolved resolution")

    for key, value in resolution.model_dump(exclude_unset=True).items():
        setattr(db_resolution, key, value)

    db_resolution.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.post("/resolutions/{resolution_id}/propose", response_model=ResolutionResponse)
async def propose_resolution(
    resolution_id: int,
    proposed_by_id: int = Query(..., description="Board member proposing"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose a resolution for adoption (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status != "draft":
        raise HTTPException(status_code=400, detail="Resolution must be in draft status")

    # Verify proposer is a board member
    proposer_result = await db.execute(
        select(BoardMember).where(BoardMember.id == proposed_by_id)
    )
    if not proposer_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Proposer must be a board member")

    db_resolution.status = "proposed"
    db_resolution.proposed_by_id = proposed_by_id
    db_resolution.proposed_date = datetime.now(timezone.utc)
    db_resolution.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.post("/resolutions/{resolution_id}/adopt", response_model=ResolutionResponse)
async def adopt_resolution(
    resolution_id: int,
    adopt_data: ResolutionAdopt,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adopt a resolution (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status not in ["proposed", "under_review"]:
        raise HTTPException(status_code=400, detail="Resolution must be proposed or under review")

    # Verify vote exists and passed
    vote_result = await db.execute(
        select(BoardVote).where(BoardVote.id == adopt_data.adopted_vote_id)
    )
    vote = vote_result.scalar_one_or_none()
    if not vote:
        raise HTTPException(status_code=400, detail="Vote record not found")
    if vote.status != "closed" or not vote.passed:
        raise HTTPException(status_code=400, detail="Vote must be closed and passed to adopt resolution")

    db_resolution.status = "adopted"
    db_resolution.adopted_date = datetime.now(timezone.utc)
    db_resolution.adopted_vote_id = adopt_data.adopted_vote_id
    db_resolution.effective_date = adopt_data.effective_date or datetime.now(timezone.utc)
    db_resolution.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.post("/resolutions/{resolution_id}/publish", response_model=ResolutionResponse)
async def publish_resolution(
    resolution_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish an adopted resolution (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status != "adopted":
        raise HTTPException(status_code=400, detail="Resolution must be adopted before publishing")

    db_resolution.published_date = datetime.now(timezone.utc)
    db_resolution.published_by_id = current_user.id
    db_resolution.is_public = True
    db_resolution.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.post("/resolutions/{resolution_id}/supersede", response_model=ResolutionResponse)
async def supersede_resolution(
    resolution_id: int,
    supersede_data: ResolutionSupersede,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a resolution as superseding another (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get the new resolution
    new_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if new_resolution.status != "adopted":
        raise HTTPException(status_code=400, detail="New resolution must be adopted")

    # Get the old resolution
    old_result = await db.execute(
        select(BoardResolution).where(BoardResolution.id == supersede_data.supersedes_resolution_id)
    )
    old_resolution = old_result.scalar_one_or_none()
    if not old_resolution:
        raise HTTPException(status_code=400, detail="Resolution to supersede not found")

    if old_resolution.status != "adopted":
        raise HTTPException(status_code=400, detail="Can only supersede adopted resolutions")

    # Update both resolutions
    new_resolution.supersedes_resolution_id = supersede_data.supersedes_resolution_id
    new_resolution.updated_at = datetime.now(timezone.utc)

    old_resolution.status = "superseded"
    old_resolution.superseded_by_resolution_id = resolution_id
    old_resolution.superseded_date = datetime.now(timezone.utc)
    old_resolution.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(new_resolution)
    return new_resolution


@router.post("/resolutions/{resolution_id}/rescind", response_model=ResolutionResponse)
async def rescind_resolution(
    resolution_id: int,
    rescind_data: ResolutionRescind,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rescind a resolution (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status != "adopted":
        raise HTTPException(status_code=400, detail="Can only rescind adopted resolutions")

    # Verify the rescinding motion passed
    motion_result = await db.execute(
        select(BoardMotion).where(BoardMotion.id == rescind_data.rescinded_by_motion_id)
    )
    motion = motion_result.scalar_one_or_none()
    if not motion:
        raise HTTPException(status_code=400, detail="Rescinding motion not found")
    if motion.status != "passed":
        raise HTTPException(status_code=400, detail="Rescinding motion must have passed")

    db_resolution.status = "rescinded"
    db_resolution.rescinded_date = datetime.now(timezone.utc)
    db_resolution.rescinded_by_motion_id = rescind_data.rescinded_by_motion_id
    db_resolution.rescinded_reason = rescind_data.rescinded_reason
    db_resolution.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_resolution)
    return db_resolution


@router.delete("/resolutions/{resolution_id}")
async def delete_resolution(
    resolution_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resolution (admin only). Only draft resolutions can be deleted."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_resolution = await get_or_404(db, BoardResolution, resolution_id, "Resolution not found")

    if db_resolution.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft resolutions can be deleted. Use rescind for adopted resolutions."
        )

    await db.delete(db_resolution)
    await db.commit()
    return {"message": "Resolution deleted"}
