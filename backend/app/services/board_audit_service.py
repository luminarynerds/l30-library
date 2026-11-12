# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.board_audit_log import BoardAuditLog, BoardAuditAction


class BoardAuditService:

    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: BoardAuditAction,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        meeting_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> BoardAuditLog:
        audit_log = BoardAuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meeting_id=meeting_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        return audit_log

    @staticmethod
    async def log_meeting_created(
        db: AsyncSession,
        meeting_id: int,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MEETING_CREATED,
            entity_type="Meeting",
            entity_id=meeting_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_meeting_updated(
        db: AsyncSession,
        meeting_id: int,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        details = {
            "old_values": old_values or {},
            "new_values": new_values or {},
        }
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MEETING_UPDATED,
            entity_type="Meeting",
            entity_id=meeting_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_meeting_cancelled(
        db: AsyncSession,
        meeting_id: int,
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MEETING_CANCELLED,
            entity_type="Meeting",
            entity_id=meeting_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"reason": reason} if reason else {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_minutes_approved(
        db: AsyncSession,
        minutes_id: int,
        meeting_id: int,
        vote_result: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MINUTES_APPROVED,
            entity_type="Minutes",
            entity_id=minutes_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"vote_result": vote_result} if vote_result else {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_vote_created(
        db: AsyncSession,
        vote_id: int,
        meeting_id: Optional[int] = None,
        vote_type: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.VOTE_CREATED,
            entity_type="Vote",
            entity_id=vote_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"vote_type": vote_type} if vote_type else {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_vote_opened(
        db: AsyncSession,
        vote_id: int,
        meeting_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.VOTE_OPENED,
            entity_type="Vote",
            entity_id=vote_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"opened_at": datetime.now(timezone.utc).isoformat()},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_vote_closed(
        db: AsyncSession,
        vote_id: int,
        meeting_id: Optional[int] = None,
        passed: bool = False,
        yes_count: int = 0,
        no_count: int = 0,
        abstain_count: int = 0,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.VOTE_CLOSED,
            entity_type="Vote",
            entity_id=vote_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={
                "passed": passed,
                "yes_count": yes_count,
                "no_count": no_count,
                "abstain_count": abstain_count,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_vote_cast(
        db: AsyncSession,
        vote_id: int,
        meeting_id: Optional[int] = None,
        board_member_id: Optional[int] = None,
        choice: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.VOTE_CAST,
            entity_type="Vote",
            entity_id=vote_id,
            user_id=user_id or board_member_id,
            meeting_id=meeting_id,
            details={"choice": choice, "board_member_id": board_member_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_motion_created(
        db: AsyncSession,
        motion_id: int,
        meeting_id: int,
        motion_type: Optional[str] = None,
        mover_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MOTION_CREATED,
            entity_type="Motion",
            entity_id=motion_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"motion_type": motion_type, "mover_id": mover_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_motion_seconded(
        db: AsyncSession,
        motion_id: int,
        meeting_id: int,
        seconder_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.MOTION_SECONDED,
            entity_type="Motion",
            entity_id=motion_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"seconder_id": seconder_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_document_published(
        db: AsyncSession,
        document_id: int,
        document_type: Optional[str] = None,
        meeting_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.DOCUMENT_PUBLISHED,
            entity_type="Document",
            entity_id=document_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"document_type": document_type},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_action_item_created(
        db: AsyncSession,
        action_item_id: int,
        meeting_id: int,
        priority: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.ACTION_ITEM_CREATED,
            entity_type="ActionItem",
            entity_id=action_item_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"priority": priority, "assigned_to_id": assigned_to_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_action_item_status_changed(
        db: AsyncSession,
        action_item_id: int,
        meeting_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.ACTION_ITEM_STATUS_CHANGED,
            entity_type="ActionItem",
            entity_id=action_item_id,
            user_id=user_id,
            meeting_id=meeting_id,
            details={"old_status": old_status, "new_status": new_status},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_board_member_created(
        db: AsyncSession,
        board_member_id: int,
        member_name: Optional[str] = None,
        position: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.BOARD_MEMBER_CREATED,
            entity_type="BoardMember",
            entity_id=board_member_id,
            user_id=user_id,
            details={"member_name": member_name, "position": position},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_committee_created(
        db: AsyncSession,
        committee_id: int,
        committee_name: Optional[str] = None,
        committee_type: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.COMMITTEE_CREATED,
            entity_type="Committee",
            entity_id=committee_id,
            user_id=user_id,
            details={"committee_name": committee_name, "committee_type": committee_type},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_strategic_goal_created(
        db: AsyncSession,
        goal_id: int,
        goal_title: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BoardAuditLog:
        return await BoardAuditService.log_action(
            db=db,
            action=BoardAuditAction.STRATEGIC_GOAL_CREATED,
            entity_type="StrategicGoal",
            entity_id=goal_id,
            user_id=user_id,
            details={"goal_title": goal_title, "category": category},
            ip_address=ip_address,
            user_agent=user_agent,
        )
