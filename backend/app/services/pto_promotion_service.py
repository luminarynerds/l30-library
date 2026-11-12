# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pto import (
    PTORequest, PTORequestStatus, PTOType, PTOBalance, PTOReminder, PTOVacationCelebration
)
from app.models.user import User
from app.core.datetime_utils import utc_now


class PTOPromotionService:

    # Positive messaging templates
    PROMOTION_MESSAGES = {
        "balance_available": "You have {days:.1f} {pto_type} days available. Time off helps you come back stronger!",
        "encourage_planning": "Plan ahead! Taking time off in advance ensures smooth coverage and lets you truly disconnect.",
        "coverage_manageable": "Your team has you covered. Our collaborative approach means coverage is manageable—go rest!",
        "no_guilt": "Taking time off is not a luxury—it's essential. You've earned it, and we want you to use it.",
        "return_refreshed": "A well-rested team member brings fresh perspectives. Return refreshed, not buried.",
        "time_off_strength": "Time off isn't weakness. It shows strength: taking care of yourself so you can do your best work.",
        "upcoming_expiry": "Only {days:.1f} days left this year! Plan a break before the year ends and return refreshed.",
        "urgency_positive": "You have {days:.1f} {pto_type} days to use. It's time to prioritize rest and recharge.",
    }

    @staticmethod
    async def send_balance_reminder(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType = PTOType.VACATION,
    ) -> Optional[PTOReminder]:
        from app.services.pto_service import PTOService

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        if available_days <= 0:
            return None

        message_key = "balance_available" if available_days > 3 else "urgency_positive"
        message = PTOPromotionService.PROMOTION_MESSAGES[message_key].format(
            days=available_days,
            pto_type=pto_type.value,
        )

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type="balance_available",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def send_planning_encouragement(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType = PTOType.VACATION,
    ) -> Optional[PTOReminder]:
        from app.services.pto_service import PTOService

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        if available_days <= 0:
            return None

        message = PTOPromotionService.PROMOTION_MESSAGES["encourage_planning"]

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type="planning_encouragement",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def send_coverage_manageable_message(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType = PTOType.VACATION,
    ) -> Optional[PTOReminder]:
        from app.services.pto_service import PTOService

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        if available_days <= 0:
            return None

        message = PTOPromotionService.PROMOTION_MESSAGES["coverage_manageable"]

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type="coverage_manageable",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def send_no_guilt_message(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType = PTOType.VACATION,
    ) -> Optional[PTOReminder]:
        from app.services.pto_service import PTOService

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        if available_days <= 0:
            return None

        message = PTOPromotionService.PROMOTION_MESSAGES["no_guilt"]

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type="no_guilt",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def send_time_off_strength_message(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType = PTOType.VACATION,
    ) -> Optional[PTOReminder]:
        from app.services.pto_service import PTOService

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        if available_days <= 0:
            return None

        message = PTOPromotionService.PROMOTION_MESSAGES["time_off_strength"]

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type="time_off_strength",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def prepare_pre_vacation_triage(
        db: AsyncSession,
        request_id: int,
    ) -> Dict:
        request = (await db.execute(
            select(PTORequest).where(PTORequest.id == request_id)
        )).scalars().first()

        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        days_until = (request.start_date - date.today()).days

        return {
            "pto_request_id": request_id,
            "user_id": request.user_id,
            "days_until_vacation": days_until,
            "vacation_start": request.start_date,
            "vacation_end": request.end_date,
            "duration_days": request.number_of_days,
            "triage_checklist": [
                {
                    "task": "Review and delegate critical items",
                    "priority": "high",
                    "description": "Ensure all urgent tasks are delegated or completed",
                },
                {
                    "task": "Update status for ongoing projects",
                    "priority": "high",
                    "description": "Brief your team on project status",
                },
                {
                    "task": "Set auto-responder and Out of Office",
                    "priority": "medium",
                    "description": "Configure email and system notifications",
                },
                {
                    "task": "Handoff meeting with coverage manager",
                    "priority": "high",
                    "description": "Discuss coverage plan and delegation notes",
                },
                {
                    "task": "Document key processes or decisions",
                    "priority": "medium",
                    "description": "Leave knowledge for team while you're away",
                },
            ],
            "message": "You're taking well-deserved time off! Here's your pre-vacation checklist to ensure smooth coverage and a truly restful break.",
        }

    @staticmethod
    async def enable_auto_delegation(
        db: AsyncSession,
        request_id: int,
        delegation_notes: Optional[str] = None,
    ) -> PTORequest:
        request = (await db.execute(
            select(PTORequest).where(PTORequest.id == request_id)
        )).scalars().first()

        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        request.auto_delegate = True
        if delegation_notes:
            request.delegation_notes = delegation_notes

        db.add(request)
        await db.flush()
        await db.refresh(request)
        return request

    @staticmethod
    async def get_gradual_return_plan(
        db: AsyncSession,
        request_id: int,
    ) -> Dict:
        request = (await db.execute(
            select(PTORequest).where(PTORequest.id == request_id)
        )).scalars().first()

        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        if not request.gradual_return_enabled:
            return {"enabled": False, "message": "Gradual return disabled"}

        end_date = request.end_date
        return_date = request.return_inbox_date or end_date + timedelta(days=1)

        return {
            "enabled": True,
            "vacation_end": end_date,
            "return_date": return_date,
            "message": PTOPromotionService.PROMOTION_MESSAGES["return_refreshed"],
            "phases": [
                {
                    "phase": 1,
                    "date": return_date,
                    "focus": "Critical/urgent items only",
                    "percentage": 10,
                    "description": "First day back: Only review items marked urgent or critical. Take it easy!",
                },
                {
                    "phase": 2,
                    "date": return_date + timedelta(days=1),
                    "focus": "Important items + critical follow-ups",
                    "percentage": 40,
                    "description": "Second day: Start addressing important items and critical follow-ups from your time away.",
                },
                {
                    "phase": 3,
                    "date": return_date + timedelta(days=2),
                    "focus": "Everything else, resume normal flow",
                    "percentage": 100,
                    "description": "Third day+: Fully resume normal email and communication flow.",
                },
            ],
        }

    @staticmethod
    async def create_celebration_notification(
        db: AsyncSession,
        request_id: int,
    ) -> Dict:
        request = (await db.execute(
            select(PTORequest).where(PTORequest.id == request_id)
        )).scalars().first()

        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        user = request.user

        return {
            "pto_request_id": request_id,
            "user_id": request.user_id,
            "user_name": user.name if hasattr(user, 'name') else f"User {user.id}",
            "vacation_start": request.start_date,
            "vacation_end": request.end_date,
            "duration_days": request.number_of_days,
            "celebration_message": (
                f"Celebrate {user.name if hasattr(user, 'name') else 'Team Member'}! "
                f"They're taking well-deserved time off to return refreshed and recharged. "
                f"Coverage is managed and they'll be back stronger! 🎉"
            ),
            "welcome_back_message": (
                f"Welcome back {user.name if hasattr(user, 'name') else 'Team Member'}! "
                f"We're thrilled to see you refreshed. Take it at your own pace as you ease back in."
            ),
            "team_message": (
                f"Our colleague is taking time off from {request.start_date} to {request.end_date}. "
                f"Let's ensure they have a truly restful break and are fully covered while away."
            ),
        }

    @staticmethod
    async def send_return_welcome_message(
        db: AsyncSession,
        request_id: int,
    ) -> Optional[PTOReminder]:
        request = (await db.execute(
            select(PTORequest).where(PTORequest.id == request_id)
        )).scalars().first()

        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        user = request.user
        user_name = user.name if hasattr(user, 'name') else f"User {user.id}"

        message = (
            f"Welcome back {user_name}! We hope you had a wonderful and restful break. "
            f"Remember: return at your own pace. We have your back with the gradual inbox return system. "
            f"You return refreshed, not buried!"
        )

        reminder = PTOReminder(
            user_id=request.user_id,
            pto_type=request.pto_type,
            days_available=0,
            reminder_type="welcome_back",
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def send_batch_promotion_reminders(
        db: AsyncSession,
        days_threshold: int = 10,
    ) -> List[PTOReminder]:
        from app.services.pto_service import PTOService

        current_year = date.today().year
        reminders = []

        # Get all users with significant available PTO
        stmt = select(PTOBalance).where(PTOBalance.year == current_year)
        result = await db.execute(stmt)
        balances = result.scalars().all()

        for balance in balances:
            available = balance.accrued_days - balance.used_days - balance.pending_days

            if available >= days_threshold:
                # Send reminder
                reminder = await PTOPromotionService.send_balance_reminder(
                    db=db,
                    user_id=balance.user_id,
                    pto_type=balance.pto_type,
                )
                if reminder:
                    reminders.append(reminder)

        await db.flush()
        return reminders

    @staticmethod
    async def get_promotion_dashboard(
        db: AsyncSession,
        user_id: int,
    ) -> Dict:
        from app.services.pto_service import PTOService

        stmt = select(PTOBalance).where(PTOBalance.user_id == user_id)
        result = await db.execute(stmt)
        balances = result.scalars().all()

        promotion_data = {
            "user_id": user_id,
            "pto_balances": [],
            "upcoming_vacation": None,
            "reminders": [],
            "promotion_message": "",
        }

        total_available = 0

        for balance in balances:
            available = balance.accrued_days - balance.used_days - balance.pending_days
            total_available += available

            promotion_data["pto_balances"].append({
                "pto_type": str(balance.pto_type),
                "available_days": available,
                "accrued_days": balance.accrued_days,
                "used_days": balance.used_days,
                "pending_days": balance.pending_days,
            })

        # Get upcoming approved PTO
        stmt = select(PTORequest).where(
            and_(
                PTORequest.user_id == user_id,
                PTORequest.status == PTORequestStatus.APPROVED,
                PTORequest.start_date >= date.today(),
            )
        ).order_by(PTORequest.start_date).limit(1)
        result = await db.execute(stmt)
        upcoming = result.scalars().first()

        if upcoming:
            promotion_data["upcoming_vacation"] = {
                "start_date": upcoming.start_date,
                "end_date": upcoming.end_date,
                "days": upcoming.number_of_days,
                "type": str(upcoming.pto_type),
            }

        # Get recent reminders
        stmt = select(PTOReminder).where(
            PTOReminder.user_id == user_id
        ).order_by(PTOReminder.sent_at.desc()).limit(5)
        result = await db.execute(stmt)
        recent_reminders = result.scalars().all()

        promotion_data["reminders"] = [
            {
                "type": r.reminder_type,
                "message": r.message,
                "sent_at": r.sent_at,
                "read_at": r.read_at,
            }
            for r in recent_reminders
        ]

        # Generate promotion message based on situation
        if total_available > 5:
            promotion_data["promotion_message"] = (
                f"You have {total_available:.1f} days to use! "
                f"Time off isn't weakness—it's essential for your wellbeing and performance. "
                f"Start planning your well-deserved break!"
            )
        elif total_available > 0:
            promotion_data["promotion_message"] = (
                f"You still have {total_available:.1f} days available. "
                f"Don't let them expire! A well-rested team member brings fresh perspectives."
            )
        else:
            promotion_data["promotion_message"] = (
                "You've used your PTO well this year. Remember for next year: "
                "Taking time off is not a luxury—it’s taking care of yourself so you can do your best work."
            )

        return promotion_data
