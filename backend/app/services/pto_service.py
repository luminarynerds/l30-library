# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pto import (
    PTORequest, PTORequestStatus, PTOType, PTOBalance, PTOApproval, PTOReminder, PTOVacationCelebration
)
from app.models.user import User
from app.core.datetime_utils import utc_now


class PTOService:

    @staticmethod
    async def create_pto_request(
        db: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
        pto_type: PTOType,
        reason: Optional[str] = None,
        coverage_notes: Optional[str] = None,
        delegation_notes: Optional[str] = None,
        auto_delegate: bool = False,
        gradual_return_enabled: bool = True,
    ) -> PTORequest:
        request = PTORequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            pto_type=pto_type,
            reason=reason,
            coverage_notes=coverage_notes or "Coverage is manageable with team coordination",
            delegation_notes=delegation_notes,
            auto_delegate=auto_delegate,
            gradual_return_enabled=gradual_return_enabled,
            status=PTORequestStatus.SUBMITTED,
        )
        db.add(request)
        await db.flush()
        await db.refresh(request)
        return request

    @staticmethod
    async def approve_pto_request(
        db: AsyncSession,
        request_id: int,
        approver_id: int,
        coverage_assessment: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PTORequest:
        request = (await db.execute(select(PTORequest).where(PTORequest.id == request_id))).scalars().first()
        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        request.status = PTORequestStatus.APPROVED
        request.approved_by = approver_id
        request.approval_date = utc_now()

        # Create approval record
        approval = PTOApproval(
            pto_request_id=request_id,
            approver_id=approver_id,
            status=PTORequestStatus.APPROVED,
            coverage_assessment=coverage_assessment,
            notes=notes,
        )
        db.add(approval)

        # Update balance
        await PTOService._update_balance_with_approved_request(db, request)

        await db.flush()
        await db.refresh(request)
        return request

    @staticmethod
    async def deny_pto_request(
        db: AsyncSession,
        request_id: int,
        approver_id: int,
        denial_reason: str,
        notes: Optional[str] = None,
    ) -> PTORequest:
        request = (await db.execute(select(PTORequest).where(PTORequest.id == request_id))).scalars().first()
        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        request.status = PTORequestStatus.DENIED
        request.approved_by = approver_id
        request.denial_reason = denial_reason
        request.approval_date = utc_now()

        # Create denial record
        approval = PTOApproval(
            pto_request_id=request_id,
            approver_id=approver_id,
            status=PTORequestStatus.DENIED,
            notes=notes or denial_reason,
        )
        db.add(approval)

        await db.flush()
        await db.refresh(request)
        return request

    @staticmethod
    async def _update_balance_with_approved_request(db: AsyncSession, request: PTORequest):
        days = request.number_of_days
        balance = (await db.execute(select(PTOBalance).where(
            and_(
                PTOBalance.user_id == request.user_id,
                PTOBalance.pto_type == request.pto_type,
                PTOBalance.year == date.today().year,
            )
        ))).scalars().first()

        if balance:
            balance.used_days += days
            balance.pending_days = max(0, balance.pending_days - days)
            db.add(balance)

    @staticmethod
    async def get_user_pto_balance(db: AsyncSession, user_id: int, pto_type: PTOType, year: int = None) -> Optional[PTOBalance]:
        if year is None:
            year = date.today().year

        return (await db.execute(select(PTOBalance).where(
            and_(
                PTOBalance.user_id == user_id,
                PTOBalance.pto_type == pto_type,
                PTOBalance.year == year,
            )
        ))).scalars().first()

    @staticmethod
    async def initialize_pto_balance(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType,
        annual_allotment: float,
        year: int = None,
    ) -> PTOBalance:
        if year is None:
            year = date.today().year

        balance = PTOBalance(
            user_id=user_id,
            pto_type=pto_type,
            annual_allotment=annual_allotment,
            accrued_days=annual_allotment,
            year=year,
        )
        db.add(balance)
        await db.flush()
        await db.refresh(balance)
        return balance

    @staticmethod
    async def get_available_days(db: AsyncSession, user_id: int, pto_type: PTOType) -> float:
        balance = await PTOService.get_user_pto_balance(db, user_id, pto_type)
        if not balance:
            return 0.0

        available = balance.accrued_days - balance.used_days - balance.pending_days
        return max(0.0, available)

    @staticmethod
    async def generate_pto_reminder(
        db: AsyncSession,
        user_id: int,
        pto_type: PTOType,
        reminder_type: str,
    ) -> PTOReminder:
        balance = await PTOService.get_user_pto_balance(db, user_id, pto_type)
        if not balance:
            raise ValueError(f"No PTO balance found for user {user_id}")

        available_days = await PTOService.get_available_days(db, user_id, pto_type)

        # Create positive messaging based on reminder type
        if reminder_type == "balance_warning":
            if available_days > 0:
                message = f"You have {available_days:.1f} {pto_type.value} days to use before year-end. Start planning your time off!"
            else:
                message = "Consider planning vacation time to restore your well-being."
        elif reminder_type == "upcoming_expiry":
            message = f"Only {available_days:.1f} days remaining this year. Taking time off refreshes you-don't let it expire!"
        elif reminder_type == "encouragement":
            message = "Time off isn't weakness. You deserve rest. Plan some vacation time to come back refreshed!"
        else:
            message = f"You have {available_days:.1f} {pto_type.value} days available."

        reminder = PTOReminder(
            user_id=user_id,
            pto_type=pto_type,
            days_available=available_days,
            reminder_type=reminder_type,
            message=message,
        )
        db.add(reminder)
        await db.flush()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def create_vacation_celebration(
        db: AsyncSession,
        request_id: int,
    ) -> PTOVacationCelebration:
        request = (await db.execute(select(PTORequest).where(PTORequest.id == request_id))).scalars().first()
        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        user = request.user
        celebration_message = f"Celebrate {user.name}! They're taking well-deserved time off to return refreshed and recharged. Coverage is managed and they'll be back stronger! 🎉"
        welcome_back_message = f"Welcome back {user.name}! We're thrilled to see you refreshed. Take it at your own pace as you ease back in."

        celebration = PTOVacationCelebration(
            pto_request_id=request_id,
            celebration_message=celebration_message,
            welcome_back_message=welcome_back_message,
        )
        db.add(celebration)
        await db.flush()
        await db.refresh(celebration)
        return celebration

    @staticmethod
    async def get_pending_approvals(db: AsyncSession, manager_id: int = None) -> List[PTORequest]:
        stmt = select(PTORequest).where(PTORequest.status == PTORequestStatus.SUBMITTED)

        if manager_id:
            stmt = stmt.where(PTORequest.coverage_manager_assigned == manager_id)

        stmt = stmt.order_by(PTORequest.start_date)
        return (await db.execute(stmt)).scalars().all()

    @staticmethod
    async def get_upcoming_pto(db: AsyncSession, days_ahead: int = 30) -> List[PTORequest]:
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        return (await db.execute(select(PTORequest).where(
            and_(
                PTORequest.status == PTORequestStatus.APPROVED,
                PTORequest.start_date <= future_date,
                PTORequest.end_date >= today,
            )
        ).order_by(PTORequest.start_date))).scalars().all()

    @staticmethod
    async def get_gradual_inbox_return_schedule(db: AsyncSession, request_id: int) -> Dict:
        request = (await db.execute(select(PTORequest).where(PTORequest.id == request_id))).scalars().first()
        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        if not request.gradual_return_enabled:
            return {"enabled": False}

        end_date = request.end_date
        return_date = request.return_inbox_date or end_date + timedelta(days=1)

        # Stagger email/message return over 3 days
        schedule = {
            "enabled": True,
            "return_date": return_date,
            "phases": [
                {
                    "phase": 1,
                    "date": return_date,
                    "focus": "Critical/urgent items only",
                    "percentage": 10,
                },
                {
                    "phase": 2,
                    "date": return_date + timedelta(days=1),
                    "focus": "Important items + critical follow-ups",
                    "percentage": 40,
                },
                {
                    "phase": 3,
                    "date": return_date + timedelta(days=2),
                    "focus": "Everything else, resume normal flow",
                    "percentage": 100,
                },
            ],
        }
        return schedule

    @staticmethod
    async def get_delegation_handoff(db: AsyncSession, request_id: int) -> Dict:
        request = (await db.execute(select(PTORequest).where(PTORequest.id == request_id))).scalars().first()
        if not request:
            raise ValueError(f"PTO request {request_id} not found")

        return {
            "pto_request_id": request_id,
            "user_id": request.user_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "auto_delegate_enabled": request.auto_delegate,
            "delegation_notes": request.delegation_notes,
            "coverage_manager": request.coverage_manager_assigned,
            "coverage_notes": request.coverage_notes,
        }

    @staticmethod
    async def check_conflicts(
        db: AsyncSession,
        user_id: int,
        start_date: date,
        end_date: date,
        exclude_request_id: Optional[int] = None,
    ) -> List[PTORequest]:
        stmt = select(PTORequest).where(
            and_(
                PTORequest.user_id == user_id,
                PTORequest.status.in_([PTORequestStatus.APPROVED, PTORequestStatus.SUBMITTED]),
                PTORequest.start_date <= end_date,
                PTORequest.end_date >= start_date,
            )
        )

        if exclude_request_id:
            stmt = stmt.where(PTORequest.id != exclude_request_id)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def calculate_accrual(
        user_id: int,
        employee_type: str = "full_time",
        hire_date: Optional[date] = None,
    ) -> float:
        if employee_type == "full_time":
            return 20.0
        elif employee_type == "part_time":
            return 10.0
        elif employee_type == "temporary":
            return 0.0
        else:
            return 15.0  # Default

    @staticmethod
    async def monthly_accrual_job(db: AsyncSession):
        from app.models.pto import PTOBalance
        from dateutil.relativedelta import relativedelta

        current_date = date.today()
        current_year = current_date.year

        # Get all balances for current year
        stmt = select(PTOBalance).where(PTOBalance.year == current_year)
        result = await db.execute(stmt)
        balances = result.scalars().all()

        for balance in balances:
            # Calculate monthly accrual (annual / 12)
            monthly_accrual = balance.annual_allotment / 12.0
            balance.accrued_days += monthly_accrual
            balance.last_accrual_date = utc_now()
            db.add(balance)

        await db.commit()

    @staticmethod
    async def year_end_carryover_job(db: AsyncSession):
        from app.models.pto import PTOBalance

        current_year = date.today().year
        next_year = current_year + 1

        # Get all balances for current year
        stmt = select(PTOBalance).where(PTOBalance.year == current_year)
        result = await db.execute(stmt)
        balances = result.scalars().all()

        for balance in balances:
            available = balance.accrued_days - balance.used_days - balance.pending_days

            if available > 0:
                # Apply carryover limit
                carryover = min(available, balance.carryover_limit)

                # Create or update next year balance
                next_year_balance = (await db.execute(select(PTOBalance).where(
                    and_(
                        PTOBalance.user_id == balance.user_id,
                        PTOBalance.pto_type == balance.pto_type,
                        PTOBalance.year == next_year,
                    )
                ))).scalars().first()

                if next_year_balance:
                    next_year_balance.carryover_days = carryover
                else:
                    next_year_balance = PTOBalance(
                        user_id=balance.user_id,
                        pto_type=balance.pto_type,
                        annual_allotment=balance.annual_allotment,
                        carryover_days=carryover,
                        year=next_year,
                    )
                    db.add(next_year_balance)

        await db.commit()
