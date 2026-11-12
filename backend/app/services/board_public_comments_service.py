# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.board.public_comment import (
    CommentStatus,
    PublicComment,
    PublicCommentPeriod,
)
from ..models.board_audit_log import BoardAuditAction
from .board_audit_service import BoardAuditService


class BoardPublicCommentsService:

    @staticmethod
    async def submit_comment(
        db: AsyncSession,
        comment: PublicComment,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicComment:
        db.add(comment)
        await db.flush()
        await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.PUBLIC_COMMENT_SUBMITTED,
            entity_type="PublicComment",
            entity_id=comment.id,
            meeting_id=comment.meeting_id,
            details={
                "comment_type": comment.comment_type,
                "commenter_name": comment.commenter_name,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.refresh(comment)
        return comment

    @staticmethod
    async def moderate(
        db: AsyncSession,
        comment: PublicComment,
        status_value: str,
        moderator_id: int,
        moderation_notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicComment:
        now = datetime.now(timezone.utc)
        comment.status = status_value
        comment.moderated_by_id = moderator_id
        comment.moderated_at = now
        comment.moderation_notes = moderation_notes
        if status_value == CommentStatus.REJECTED.value:
            comment.rejection_reason = rejection_reason
        comment.updated_at = now

        action = (
            BoardAuditAction.PUBLIC_COMMENT_APPROVED
            if status_value == CommentStatus.APPROVED.value
            else BoardAuditAction.PUBLIC_COMMENT_REJECTED
        )
        await BoardAuditService.log_action(
            db=db,
            action=action,
            entity_type="PublicComment",
            entity_id=comment.id,
            user_id=moderator_id,
            meeting_id=comment.meeting_id,
            details={
                "status": status_value,
                "moderation_notes": moderation_notes,
                "rejection_reason": rejection_reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.refresh(comment)
        return comment

    @staticmethod
    async def read_into_record(
        db: AsyncSession,
        comment: PublicComment,
        reader_id: int,
        reading_notes: Optional[str] = None,
        time_allocated_seconds: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicComment:
        now = datetime.now(timezone.utc)
        comment.status = CommentStatus.READ_INTO_RECORD.value
        comment.read_by_id = reader_id
        comment.read_at = now
        if reading_notes is not None:
            comment.reading_notes = reading_notes
        if time_allocated_seconds is not None:
            comment.time_allocated_seconds = time_allocated_seconds
        comment.updated_at = now

        await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.PUBLIC_COMMENT_READ_INTO_RECORD,
            entity_type="PublicComment",
            entity_id=comment.id,
            user_id=reader_id,
            meeting_id=comment.meeting_id,
            details={
                "reading_notes": reading_notes,
                "time_allocated_seconds": time_allocated_seconds,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.refresh(comment)
        return comment

    @staticmethod
    async def start_speaking(
        db: AsyncSession,
        comment: PublicComment,
    ) -> datetime:
        now = datetime.now(timezone.utc)
        comment.actual_start_time = now
        comment.updated_at = now
        await db.flush()
        return now

    @staticmethod
    async def stop_speaking(
        db: AsyncSession,
        comment: PublicComment,
    ) -> tuple[datetime, int]:
        now = datetime.now(timezone.utc)
        comment.actual_end_time = now
        comment.updated_at = now
        duration = 0
        if comment.actual_start_time:
            duration = int((now - comment.actual_start_time).total_seconds())
        await db.flush()
        return now, duration

    @staticmethod
    async def start_period(
        db: AsyncSession,
        period: PublicCommentPeriod,
    ) -> datetime:
        now = datetime.now(timezone.utc)
        period.actual_start_time = now
        period.updated_at = now
        await db.flush()
        return now

    @staticmethod
    async def end_period(
        db: AsyncSession,
        period: PublicCommentPeriod,
    ) -> datetime:
        now = datetime.now(timezone.utc)
        period.actual_end_time = now
        period.is_active = False
        period.updated_at = now
        await db.flush()
        return now
