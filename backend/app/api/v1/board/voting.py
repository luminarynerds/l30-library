# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board voting API endpoints - vote management and tally."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import BoardMember, BoardVote, BoardVoteCast, BoardRecusalDeclaration
from ....models.board.coi_disclosure import BoardCOIDisclosure
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....core.audit_log import audit_log_event
from ....models.user import User, UserRole
from ....schemas.board import BoardVoteCreate, BoardVoteResponse, VoteCastCreate, VoteCastResponse
from ..auth import get_current_user

router = APIRouter(prefix="/board/votes", tags=["voting"])


@router.post("", response_model=BoardVoteResponse)
async def create_vote(
    vote: BoardVoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new board vote (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_vote = BoardVote(
        **vote.model_dump(), status="upcoming", created_by_id=current_user.id
    )
    db.add(db_vote)
    await db.flush()

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.VOTE_CREATED,
        entity_type="BoardVote",
        entity_id=db_vote.id,
        meeting_id=db_vote.meeting_id,
        details={"title": db_vote.title, "vote_type": db_vote.vote_type},
    ))
    await db.commit()
    await db.refresh(db_vote)
    return db_vote


@router.get("", response_model=List[BoardVoteResponse])
async def get_votes(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get board votes (authenticated users)."""
    query = select(BoardVote)
    if status:
        query = query.where(BoardVote.status == status)
    query = query.order_by(BoardVote.closes_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{vote_id}/cast", response_model=VoteCastResponse)
async def cast_vote(
    vote_id: int,
    vote_cast: VoteCastCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cast a vote (board members only)."""
    # Verify user is a current board member
    member_result = await db.execute(
        select(BoardMember).where(
            and_(
                BoardMember.user_id == current_user.id,
                BoardMember.is_current == True,
            )
        )
    )
    board_member = member_result.scalar_one_or_none()
    if not board_member:
        raise HTTPException(
            status_code=403, detail="Only current board members can vote"
        )

    # Check for active recusal declaration on this vote
    recusal_result = await db.execute(
        select(BoardRecusalDeclaration).where(
            and_(
                BoardRecusalDeclaration.board_member_id == board_member.id,
                BoardRecusalDeclaration.vote_id == vote_id,
                BoardRecusalDeclaration.is_active == True,
            )
        )
    )
    if recusal_result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="You have declared a recusal for this vote and cannot cast a ballot",
        )

    # Check vote exists and is open
    db_vote = await get_or_404(db, BoardVote, vote_id, "Vote not found")
    if db_vote.locked_at is not None:
        raise HTTPException(status_code=409, detail="Vote is locked")
    if db_vote.status != "open":
        raise HTTPException(status_code=400, detail="Vote is not open")

    # Check if already voted
    result = await db.execute(
        select(BoardVoteCast).where(
            and_(
                BoardVoteCast.vote_id == vote_id,
                BoardVoteCast.board_member_id == current_user.id,
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already voted")

    db_cast = BoardVoteCast(
        vote_id=vote_id,
        board_member_id=current_user.id,
        choice=vote_cast.choice,
        comment=vote_cast.comment,
    )
    db.add(db_cast)
    await db.flush()

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.VOTE_CAST,
        entity_type="BoardVoteCast",
        entity_id=db_cast.id,
        meeting_id=db_vote.meeting_id,
        details={"vote_id": vote_id, "choice": vote_cast.choice},
    ))
    audit_log_event(
        event_type="BOARD_VOTE_CAST",
        user_id=current_user.id,
        severity="INFO",
        details={"vote_id": vote_id, "choice": vote_cast.choice, "meeting_id": db_vote.meeting_id},
    )
    await db.commit()
    await db.refresh(db_cast)

    # COI overlap advisory check
    coi_warning = None
    coi_result = await db.execute(
        select(BoardCOIDisclosure).where(
            and_(
                BoardCOIDisclosure.board_member_id == board_member.id,
                BoardCOIDisclosure.is_current == True,
            )
        )
    )
    active_coi = coi_result.scalars().all()
    if active_coi:
        vote_text = f"{db_vote.title} {db_vote.description}".lower()
        for coi in active_coi:
            for keyword in (coi.keywords or []):
                if keyword.lower() in vote_text:
                    coi_warning = f"Your COI disclosure mentions '{keyword}' which appears in this vote. Consider whether recusal is appropriate."
                    db.add(BoardAuditLog(
                        user_id=current_user.id,
                        action=BoardAuditAction.COI_OVERLAP_DETECTED,
                        entity_type="BoardVoteCast",
                        entity_id=db_cast.id,
                        meeting_id=db_vote.meeting_id,
                        details={"keyword": keyword, "vote_id": vote_id, "member_name": board_member.full_name},
                    ))
                    await db.commit()
                    break
            if coi_warning:
                break

    response = VoteCastResponse.model_validate(db_cast)
    response.coi_warning = coi_warning
    return response


@router.post("/{vote_id}/open")
async def open_vote(
    vote_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open a vote for voting (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_vote = await get_or_404(db, BoardVote, vote_id, "Vote not found")

    # Validate vote state - can only open from upcoming
    if db_vote.status != "upcoming":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot open vote with status '{db_vote.status}'. Only upcoming votes can be opened.",
        )

    # Enforce vote timing - cannot open before opens_at
    if db_vote.opens_at:
        # Ensure opens_at is timezone-aware for proper comparison
        opens_at_aware = db_vote.opens_at if db_vote.opens_at.tzinfo else db_vote.opens_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < opens_at_aware:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot open vote before scheduled time: {db_vote.opens_at}",
            )

    # Pre-check: enough eligible voters for quorum after recusals?
    total_members_result = await db.execute(
        select(func.count(BoardMember.id)).where(BoardMember.is_current == True)
    )
    total_current_members = total_members_result.scalar()

    recused_count_result = await db.execute(
        select(func.count(BoardRecusalDeclaration.id)).where(
            and_(
                BoardRecusalDeclaration.vote_id == vote_id,
                BoardRecusalDeclaration.is_active == True,
            )
        )
    )
    recused_count = recused_count_result.scalar()

    eligible_voters = total_current_members - recused_count
    if eligible_voters < db_vote.quorum_required:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot open vote: {eligible_voters} eligible voters after {recused_count} recusals, but quorum requires {db_vote.quorum_required}",
        )

    db_vote.status = "open"

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.VOTE_OPENED,
        entity_type="BoardVote",
        entity_id=vote_id,
        meeting_id=db_vote.meeting_id,
        details={"title": db_vote.title, "eligible_voters": eligible_voters, "recused": recused_count},
    ))
    await db.commit()
    return {"message": "Vote opened"}


@router.post("/{vote_id}/close")
async def close_vote(
    vote_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close a vote and tally results (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_vote = await get_or_404(db, BoardVote, vote_id, "Vote not found")

    # Validate vote state - must be open to close
    if db_vote.status != "open":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close vote with status '{db_vote.status}'. Vote must be open.",
        )

    # Tally votes
    result = await db.execute(
        select(BoardVoteCast).where(BoardVoteCast.vote_id == vote_id)
    )
    votes_cast = result.scalars().all()

    yes_count = sum(1 for v in votes_cast if v.choice == "yes")
    no_count = sum(1 for v in votes_cast if v.choice == "no")
    abstain_count = sum(1 for v in votes_cast if v.choice == "abstain")
    recusal_count = sum(1 for v in votes_cast if v.choice == "recusal")

    db_vote.status = "closed"
    db_vote.final_tally_yes = yes_count
    db_vote.final_tally_no = no_count
    db_vote.final_tally_abstain = abstain_count
    db_vote.final_tally_recusal = recusal_count
    db_vote.closed_by_id = current_user.id
    db_vote.closed_at_actual = datetime.now(timezone.utc)

    # Determine if passed based on vote type
    # Quorum counts all participants (including abstentions) - members who are present
    members_participating = yes_count + no_count + abstain_count
    # Voting total excludes abstentions for pass/fail calculation
    voting_total = yes_count + no_count

    if members_participating >= db_vote.quorum_required:
        if db_vote.vote_type == "simple_majority":
            db_vote.passed = yes_count > no_count
        elif db_vote.vote_type == "two_thirds":
            # Use integer math to avoid floating point issues: yes >= 2/3 * total
            # Equivalent to: yes * 3 >= total * 2
            db_vote.passed = (yes_count * 3) >= (voting_total * 2) if voting_total > 0 else False
        elif db_vote.vote_type == "unanimous":
            db_vote.passed = no_count == 0 and yes_count > 0
        else:
            # Default to simple majority for unknown vote types
            db_vote.passed = yes_count > no_count
    else:
        db_vote.passed = False  # Failed quorum

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.VOTE_CLOSED,
        entity_type="BoardVote",
        entity_id=vote_id,
        meeting_id=db_vote.meeting_id,
        details={
            "title": db_vote.title,
            "passed": db_vote.passed,
            "yes": yes_count, "no": no_count,
            "abstain": abstain_count, "recusal": recusal_count,
            "quorum_met": members_participating >= db_vote.quorum_required,
        },
    ))
    audit_log_event(
        event_type="BOARD_VOTE_CLOSED",
        user_id=current_user.id,
        severity="INFO",
        details={
            "vote_id": vote_id, "passed": db_vote.passed,
            "yes": yes_count, "no": no_count,
            "abstain": abstain_count, "recusal": recusal_count,
        },
    )
    await db.commit()
    return {
        "message": "Vote closed",
        "passed": db_vote.passed,
        "quorum_met": members_participating >= db_vote.quorum_required,
        "members_participating": members_participating,
        "yes": yes_count,
        "no": no_count,
        "abstain": abstain_count,
        "recusal": recusal_count,
    }


@router.delete("/{vote_id}")
async def delete_vote(
    vote_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a vote (admin only). Cannot delete closed votes."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    db_vote = await get_or_404(db, BoardVote, vote_id, "Vote not found")

    if db_vote.locked_at is not None:
        raise HTTPException(status_code=409, detail="Vote is locked")
    if db_vote.status == "closed":
        raise HTTPException(
            status_code=400, detail="Cannot delete a closed vote. Results must be preserved."
        )

    db.add(BoardAuditLog(
        user_id=current_user.id,
        action=BoardAuditAction.VOTE_DELETED,
        entity_type="BoardVote",
        entity_id=vote_id,
        meeting_id=db_vote.meeting_id,
        details={"title": db_vote.title, "status": db_vote.status},
    ))
    await db.delete(db_vote)
    await db.commit()
    return {"message": "Vote deleted"}
