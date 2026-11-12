# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.focus_time import (
    FocusTimeBlock,
    FocusTimeApproval,
    FocusTimeOverride,
    ApprovalStatus,
    FocusTimeStatus,
)
from ..models.user import User
from ..models.notification import Notification, NotificationType, NotificationStatus
from ..core.datetime_utils import utc_now


class FocusTimeNotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify_focus_time_approved(
        self,
        focus_block: FocusTimeBlock,
        manager: User,
        decision_comment: Optional[str] = None,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        if not staff_member:
            return

        # Create notification
        subject = f"✓ Focus Time Approved: {focus_block.work_type.replace('_', ' ').title()}"
        body = f"""
Your focus time has been approved by {manager.full_name or manager.email}.

**Block Details:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Start: {focus_block.start_time.strftime('%a, %b %d at %I:%M %p')}
- End: {focus_block.end_time.strftime('%I:%M %p')}
"""
        if decision_comment:
            body += f"\n**Manager Comment:** {decision_comment}"

        body += """
Your focus time is now protected. Non-urgent requests will be routed to available staff.
In case of emergency, your backup contact will be reached first.
"""
        # Send via email/notification system
        await self._send_notification(
            user_id=staff_member.id,
            subject=subject,
            body=body,
            notification_type="focus_time_approved",
            category="focus_time",
        )

    async def notify_focus_time_rejected(
        self,
        focus_block: FocusTimeBlock,
        manager: User,
        decision_comment: str,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        if not staff_member:
            return

        subject = "⚠ Focus Time Request Declined"
        body = f"""
Your focus time request has been declined by {manager.full_name or manager.email}.

**Block Details:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Requested: {focus_block.start_time.strftime('%a, %b %d at %I:%M %p')} - {focus_block.end_time.strftime('%I:%M %p')}

**Reason:** {decision_comment}

Feel free to schedule a different time or reach out to discuss.
"""
        await self._send_notification(
            user_id=staff_member.id,
            subject=subject,
            body=body,
            notification_type="focus_time_rejected",
            category="focus_time",
        )

    async def notify_focus_time_pending_approval(
        self,
        focus_block: FocusTimeBlock,
        manager: User,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        if not staff_member:
            return

        subject = f"📋 Focus Time Approval Needed: {staff_member.full_name or staff_member.email}"
        body = f"""
{staff_member.full_name or staff_member.email} has requested focus time.

**Block Details:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Start: {focus_block.start_time.strftime('%a, %b %d at %I:%M %p')}
- Duration: {(focus_block.end_time - focus_block.start_time).total_seconds() / 3600:.1f} hours
- Description: {focus_block.description or 'None provided'}

Please review and approve or reject this request to help your team protect their deep work time.
"""
        await self._send_notification(
            user_id=manager.id,
            subject=subject,
            body=body,
            notification_type="focus_time_approval_requested",
            category="focus_time",
        )

    async def notify_focus_time_upcoming(
        self,
        focus_block: FocusTimeBlock,
        minutes_before: int = 15,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        if not staff_member:
            return

        subject = "⏰ Focus Time Starting Soon"
        body = f"""
Your focus time starts in {minutes_before} minutes.

**Block Details:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Start: {focus_block.start_time.strftime('%I:%M %p')}
- End: {focus_block.end_time.strftime('%I:%M %p')}

Get ready to focus! Your status will be marked as unavailable. Non-urgent requests will be routed elsewhere.
"""
        await self._send_notification(
            user_id=staff_member.id,
            subject=subject,
            body=body,
            notification_type="focus_time_reminder",
            category="focus_time",
        )

    async def notify_focus_time_override(
        self,
        focus_block: FocusTimeBlock,
        override: FocusTimeOverride,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        if not staff_member:
            return

        override_person = await self.db.get(User, override.overridden_by_id)

        subject = "🚨 Focus Time Interrupted - Emergency"
        body = f"""
Your focus time has been interrupted due to an emergency.

**Emergency Details:**
- Reason: {override.reason.replace('_', ' ').title()}
- Urgency Level: {override.urgency_level}/5
- Initiated By: {override_person.full_name if override_person else 'Staff'}
- Details: {override.description}

This interruption has been logged. Your interruption metrics may be affected.
Your focus time block status has been updated to reflect the interruption.

Thank you for your understanding during this emergency.
"""
        await self._send_notification(
            user_id=staff_member.id,
            subject=subject,
            body=body,
            notification_type="focus_time_override",
            category="focus_time",
        )

    async def notify_manager_of_override(
        self,
        focus_block: FocusTimeBlock,
        override: FocusTimeOverride,
        manager: User,
    ) -> None:
        staff_member = await self.db.get(User, focus_block.user_id)
        override_person = await self.db.get(User, override.overridden_by_id)

        if not staff_member:
            return

        subject = f"🚨 Emergency Override - {staff_member.full_name or staff_member.email}"
        body = f"""
{staff_member.full_name or staff_member.email}'s focus time has been interrupted by an emergency override.

**Focus Block:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Time: {focus_block.start_time.strftime('%a, %b %d at %I:%M %p')}

**Override Details:**
- Reason: {override.reason.replace('_', ' ').title()}
- Urgency: Level {override.urgency_level}/5
- Initiated By: {override_person.full_name if override_person else 'Unknown'}
- Description: {override.description}

{"[ESCALATED] This override requires management attention." if override.requires_escalation else ""}

This interruption has been logged for workload and focus time analysis.
"""
        await self._send_notification(
            user_id=manager.id,
            subject=subject,
            body=body,
            notification_type="focus_time_override_logged",
            category="focus_time",
        )

    async def notify_route_query_to_backup(
        self,
        focus_block: FocusTimeBlock,
        original_recipient: User,
    ) -> None:
        if not focus_block.backup_contact_id:
            return

        backup_contact = await self.db.get(User, focus_block.backup_contact_id)
        if not backup_contact:
            return

        subject = f"Query Routed - {original_recipient.full_name or original_recipient.email} in Focus Time"
        body = f"""
A query or request has been routed to you because {original_recipient.full_name or original_recipient.email} is currently in protected focus time.

**Focus Time Details:**
- Work Type: {focus_block.work_type.replace('_', ' ').title()}
- Available at: {focus_block.end_time.strftime('%I:%M %p')}
- Duration: {(focus_block.end_time - datetime.now()).total_seconds() / 60:.0f} minutes remaining

Please handle this request or note that you can follow up after their focus time ends.
"""
        await self._send_notification(
            user_id=backup_contact.id,
            subject=subject,
            body=body,
            notification_type="focus_time_query_routed",
            category="focus_time",
        )

    async def batch_notification_summary(
        self,
        user_id: int,
        period_minutes: int = 60,
    ) -> None:
        staff_member = await self.db.get(User, user_id)
        if not staff_member:
            return

        # In a real system, this would aggregate pending notifications
        # For now, this is a placeholder for the batching mechanism

        subject = "📬 Notification Summary - End of Focus Time"
        body = """
Your focus time has ended. Here's a summary of what happened while you were focused:

**During Your Focus Time:**
- Messages/Requests Received: [Count]
- Queries Routed to Backup: [Count]
- Urgent Alerts: [Count]

You can now catch up on non-urgent messages at your convenience.
"""
        await self._send_notification(
            user_id=user_id,
            subject=subject,
            body=body,
            notification_type="focus_time_batch_summary",
            category="focus_time",
        )

    async def _send_notification(
        self,
        user_id: int,
        subject: str,
        body: str,
        notification_type: str,
        category: str,
    ) -> None:
        notification_map = {
            "focus_time_approved": NotificationType.EVENT_UPDATED,
            "focus_time_rejected": NotificationType.EVENT_CANCELLED,
            "focus_time_approval_requested": NotificationType.EVENT_REMINDER,
            "focus_time_reminder": NotificationType.EVENT_REMINDER,
            "focus_time_override": NotificationType.PANIC_ALERT,
            "focus_time_override_logged": NotificationType.EVENT_UPDATED,
            "focus_time_query_routed": NotificationType.EVENT_REMINDER,
            "focus_time_batch_summary": NotificationType.EVENT_UPDATED,
        }

        notification = Notification(
            user_id=user_id,
            notification_type=notification_map.get(notification_type, NotificationType.EVENT_REMINDER),
            status=NotificationStatus.PENDING,
            subject=subject,
            message=body,
            context_data={
                "category": category,
                "focus_time_notification_type": notification_type,
            },
        )
        self.db.add(notification)
        await self.db.commit()
