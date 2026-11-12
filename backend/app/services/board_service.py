# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.error_codes import ErrorCode
from ..core.exceptions import (
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.board import (
    BoardMember, BoardMeeting, AgendaItem, BoardMinutes,
    BoardVote, BoardVoteCast, MeetingActionItem
)
from ..models.user import User

logger = get_logger(__name__)


async def create_board_member(
    member_data: dict,
    db: AsyncSession,
) -> BoardMember:
    db_member = BoardMember(**member_data)
    db.add(db_member)
    await db.commit()
    await db.refresh(db_member)
    return db_member


async def update_board_member(
    member_id: int,
    member_data: dict,
    db: AsyncSession,
) -> BoardMember:
    result = await db.execute(select(BoardMember).where(BoardMember.id == member_id))
    db_member = result.scalar_one_or_none()
    if not db_member:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Board member not found")

    for key, value in member_data.items():
        if value is not None:
            setattr(db_member, key, value)
    db_member.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_member)
    return db_member


async def create_meeting(
    meeting_data: dict,
    created_by_id: int,
    db: AsyncSession,
) -> BoardMeeting:
    db_meeting = BoardMeeting(**meeting_data, created_by_id=created_by_id)
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    return db_meeting


async def update_meeting(
    meeting_id: int,
    meeting_data: dict,
    db: AsyncSession,
) -> BoardMeeting:
    result = await db.execute(select(BoardMeeting).where(BoardMeeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")

    for key, value in meeting_data.items():
        if value is not None:
            setattr(db_meeting, key, value)
    db_meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_meeting)
    return db_meeting


async def cancel_meeting(
    meeting_id: int,
    reason: str,
    db: AsyncSession,
) -> dict:
    result = await db.execute(select(BoardMeeting).where(BoardMeeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")

    db_meeting.is_cancelled = True
    db_meeting.cancellation_reason = reason
    db_meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Meeting cancelled"}


async def add_agenda_item(
    meeting_id: int,
    item_data: dict,
    created_by_id: int,
    db: AsyncSession,
) -> AgendaItem:
    # Verify meeting exists and is not cancelled
    meeting_result = await db.execute(
        select(BoardMeeting).where(BoardMeeting.id == meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")
    if meeting.is_cancelled:
        raise BusinessLogicError(
            code=ErrorCode.OPERATION_NOT_ALLOWED, message="Cannot add agenda items to a cancelled meeting"
        )

    db_item = AgendaItem(
        **item_data, meeting_id=meeting_id, created_by_id=created_by_id
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def create_minutes(
    meeting_id: int,
    minutes_data: dict,
    created_by_id: int,
    db: AsyncSession,
) -> BoardMinutes:
    # Verify meeting exists and is not cancelled
    meeting_result = await db.execute(
        select(BoardMeeting).where(BoardMeeting.id == meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")
    if meeting.is_cancelled:
        raise BusinessLogicError(
            code=ErrorCode.OPERATION_NOT_ALLOWED, message="Cannot create minutes for a cancelled meeting"
        )

    # Check if minutes already exist for this meeting
    existing_result = await db.execute(
        select(BoardMinutes).where(BoardMinutes.meeting_id == meeting_id)
    )
    existing_minutes = existing_result.scalar_one_or_none()

    if existing_minutes:
        # Update existing
        for key, value in minutes_data.items():
            if value is not None:
                setattr(existing_minutes, key, value)
        existing_minutes.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_minutes)
        return existing_minutes
    else:
        # Create new
        db_minutes = BoardMinutes(
            **minutes_data, meeting_id=meeting_id, created_by_id=created_by_id
        )
        db.add(db_minutes)
        await db.commit()
        await db.refresh(db_minutes)
        return db_minutes


async def approve_minutes(
    minutes_id: int,
    approved_by_id: int,
    db: AsyncSession,
) -> BoardMinutes:
    result = await db.execute(select(BoardMinutes).where(BoardMinutes.id == minutes_id))
    db_minutes = result.scalar_one_or_none()
    if not db_minutes:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Minutes not found")

    db_minutes.approved = True
    db_minutes.approved_at = datetime.now(timezone.utc)
    db_minutes.approved_by_id = approved_by_id
    await db.commit()
    await db.refresh(db_minutes)
    return db_minutes


async def record_vote(
    meeting_id: int,
    vote_data: dict,
    cast_by_id: int,
    db: AsyncSession,
) -> BoardVoteCast:
    # Verify meeting exists
    meeting_result = await db.execute(
        select(BoardMeeting).where(BoardMeeting.id == meeting_id)
    )
    if not meeting_result.scalar_one_or_none():
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")

    # Verify vote exists
    vote_id = vote_data.get("vote_id")
    vote_result = await db.execute(select(BoardVote).where(BoardVote.id == vote_id))
    if not vote_result.scalar_one_or_none():
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Vote not found")

    db_cast = BoardVoteCast(
        **vote_data, board_member_id=cast_by_id
    )
    db.add(db_cast)
    await db.commit()
    await db.refresh(db_cast)
    return db_cast


async def create_action_item(
    meeting_id: int,
    item_data: dict,
    created_by_id: int,
    db: AsyncSession,
) -> MeetingActionItem:
    # Verify meeting exists
    meeting_result = await db.execute(
        select(BoardMeeting).where(BoardMeeting.id == meeting_id)
    )
    if not meeting_result.scalar_one_or_none():
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Meeting not found")

    db_item = MeetingActionItem(
        **item_data, meeting_id=meeting_id, created_by_id=created_by_id
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item
