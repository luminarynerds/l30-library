# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from app.core.logging import get_logger

from app.models.fair_scheduling import (
    CalloutCoverageRequest, CalloutStatus, CalloutUrgency,
    StaffSchedulingProfile, StaffFatigueRecord, FatigueLevel,
)
from app.models.staff_schedule_fairness import (
    StaffShift, FairnessShiftType, ShiftStatus,
)
from app.models.shift_swap import (
    StaffPreferenceProfile, SwapperReliabilityScore,
)
from app.models.user import User

logger = get_logger(__name__)


class CalloutCoverageService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_callout(
        self,
        branch_id: int,
        shift_id: int,
        callout_staff_id: int,
        callout_reason: Optional[str] = None,
        handled_by_id: Optional[int] = None,
    ) -> CalloutCoverageRequest:
        # Get the original shift
        result = await self.db.execute(
            select(StaffShift).where(StaffShift.id == shift_id)
        )
        shift = result.scalar_one_or_none()
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")

        # Mark original shift as called out
        shift.status = ShiftStatus.CALLED_OUT

        # Determine urgency
        now = datetime.now()
        shift_datetime = datetime.combine(shift.shift_date, shift.scheduled_start)
        hours_until = (shift_datetime - now).total_seconds() / 3600
        urgency = self._determine_urgency(hours_until)

        request = CalloutCoverageRequest(
            branch_id=branch_id,
            original_shift_id=shift_id,
            callout_staff_id=callout_staff_id,
            callout_reason=callout_reason,
            callout_time=now,
            shift_date=shift.shift_date,
            shift_start=shift.scheduled_start,
            shift_end=shift.scheduled_end,
            status=CalloutStatus.SEARCHING,
            urgency=urgency,
            handled_by_id=handled_by_id,
        )
        self.db.add(request)
        await self.db.flush()

        # Auto-search for candidates
        candidates = await self._find_candidates(request)
        request.staff_contacted = candidates
        request.staff_contacted_count = len(candidates)
        request.auto_match_attempted = True

        await self.db.commit()
        return request

    async def get_coverage_candidates(
        self, request_id: int
    ) -> List[Dict]:
        result = await self.db.execute(
            select(CalloutCoverageRequest).where(CalloutCoverageRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Coverage request {request_id} not found")

        return await self._find_candidates(request)

    async def assign_coverage(
        self, request_id: int, covering_staff_id: int, notes: Optional[str] = None
    ) -> CalloutCoverageRequest:
        result = await self.db.execute(
            select(CalloutCoverageRequest).where(CalloutCoverageRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Coverage request {request_id} not found")

        # Create new shift for covering staff
        covering_shift = StaffShift(
            branch_id=request.branch_id,
            staff_id=covering_staff_id,
            shift_date=request.shift_date,
            shift_type=FairnessShiftType.MIDDAY,  # Will inherit from original
            status=ShiftStatus.ASSIGNED,
            scheduled_start=request.shift_start,
            scheduled_end=request.shift_end,
            scheduled_hours=self._calculate_hours(request.shift_start, request.shift_end),
            is_overtime=False,
            is_holiday=False,
            is_weekend=request.shift_date.weekday() >= 5,
            notes=f"Callout coverage for request #{request.id}",
        )

        # Copy shift type from original
        orig_result = await self.db.execute(
            select(StaffShift).where(StaffShift.id == request.original_shift_id)
        )
        original = orig_result.scalar_one_or_none()
        if original:
            covering_shift.shift_type = original.shift_type
            covering_shift.is_holiday = original.is_holiday

        self.db.add(covering_shift)
        await self.db.flush()

        # Update request
        request.covering_staff_id = covering_staff_id
        request.covering_shift_id = covering_shift.id
        request.status = CalloutStatus.COVERED
        request.resolved_at = datetime.now()
        request.resolution_notes = notes

        await self.db.commit()
        return request

    async def get_open_requests(
        self, branch_id: Optional[int] = None
    ) -> List[CalloutCoverageRequest]:
        stmt = select(CalloutCoverageRequest).where(
            CalloutCoverageRequest.status.in_([CalloutStatus.OPEN, CalloutStatus.SEARCHING])
        )
        if branch_id:
            stmt = stmt.where(CalloutCoverageRequest.branch_id == branch_id)
        stmt = stmt.order_by(CalloutCoverageRequest.callout_time.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_staff_response(
        self, request_id: int, staff_id: int, response: str, reason: Optional[str] = None
    ) -> CalloutCoverageRequest:
        result = await self.db.execute(
            select(CalloutCoverageRequest).where(CalloutCoverageRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Coverage request {request_id} not found")

        contacted = request.staff_contacted or []
        for entry in contacted:
            if entry.get("staff_id") == staff_id:
                entry["response"] = response
                entry["reason"] = reason
                entry["responded_at"] = datetime.now().isoformat()
                break

        request.staff_contacted = contacted

        if response == "accepted":
            return await self.assign_coverage(request_id, staff_id)

        await self.db.commit()
        return request

    async def _find_candidates(self, request: CalloutCoverageRequest) -> List[Dict]:
        candidates = []

        # Get all active staff at this branch (excluding the caller-out)
        profiles_result = await self.db.execute(
            select(StaffSchedulingProfile).where(
                and_(
                    StaffSchedulingProfile.is_active == True,
                    StaffSchedulingProfile.staff_id != request.callout_staff_id,
                    (StaffSchedulingProfile.branch_id == request.branch_id) |
                    (StaffSchedulingProfile.branch_id.is_(None)),
                )
            )
        )
        profiles = profiles_result.scalars().all()

        for profile in profiles:
            staff_id = profile.staff_id

            # Check if already working this shift
            existing_result = await self.db.execute(
                select(StaffShift).where(
                    and_(
                        StaffShift.staff_id == staff_id,
                        StaffShift.shift_date == request.shift_date,
                        StaffShift.status.in_([ShiftStatus.ASSIGNED, ShiftStatus.CONFIRMED]),
                    )
                ).limit(1)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                continue

            # Check skills (from original shift requirements)
            for skill in (profile.skills or []):
                pass  # Skills match is permissive; any staff can fill basic shifts

            # Score this candidate
            score = 0.0
            factors = []

            # 1. Wants extra hours (strongest signal)
            pref_result = await self.db.execute(
                select(StaffPreferenceProfile).where(
                    StaffPreferenceProfile.user_id == staff_id
                )
            )
            pref_profile = pref_result.scalar_one_or_none()
            if pref_profile and pref_profile.wants_extra_hours:
                score += 30
                factors.append("wants_extra_hours")

            # 2. Reliability score
            rel_result = await self.db.execute(
                select(SwapperReliabilityScore).where(
                    SwapperReliabilityScore.user_id == staff_id
                )
            )
            reliability = rel_result.scalar_one_or_none()
            if reliability:
                score += reliability.reliability_score * 0.2
                factors.append(f"reliability:{reliability.reliability_score:.0f}")

            # 3. Fatigue level (prefer less fatigued staff)
            fatigue_result = await self.db.execute(
                select(StaffFatigueRecord).where(
                    and_(
                        StaffFatigueRecord.staff_id == staff_id,
                        StaffFatigueRecord.record_date == date.today(),
                    )
                )
            )
            fatigue = fatigue_result.scalar_one_or_none()
            if fatigue:
                fatigue_penalty = {
                    FatigueLevel.LOW: 0,
                    FatigueLevel.MODERATE: -10,
                    FatigueLevel.HIGH: -25,
                    FatigueLevel.CRITICAL: -50,
                }
                penalty = fatigue_penalty.get(fatigue.fatigue_level, 0)
                score += penalty
                factors.append(f"fatigue:{fatigue.fatigue_level}")
            else:
                score += 10  # No fatigue data = assume rested
                factors.append("fatigue:unknown")

            # 4. Hours headroom
            hours_result = await self.db.execute(
                select(func.sum(StaffShift.scheduled_hours)).where(
                    and_(
                        StaffShift.staff_id == staff_id,
                        StaffShift.shift_date >= request.shift_date - timedelta(days=request.shift_date.weekday()),
                        StaffShift.shift_date <= request.shift_date,
                        StaffShift.status != ShiftStatus.CANCELLED,
                    )
                )
            )
            weekly_hours = hours_result.scalar() or 0

            headroom = profile.max_hours_per_week - weekly_hours
            shift_hours = self._calculate_hours(request.shift_start, request.shift_end)
            if headroom >= shift_hours:
                score += 15
                factors.append(f"headroom:{headroom:.1f}h")
            elif headroom > 0:
                score += 5
                factors.append(f"tight_headroom:{headroom:.1f}h")
            else:
                continue  # Would exceed max hours

            user_result = await self.db.execute(
                select(User).where(User.id == staff_id)
            )
            user = user_result.scalar_one_or_none()
            name = f"{user.first_name} {user.last_name}" if user and hasattr(user, 'first_name') else f"Staff #{staff_id}"

            candidates.append({
                "staff_id": staff_id,
                "name": name,
                "score": round(score, 1),
                "factors": factors,
                "employment_type": str(profile.employment_type),
                "weekly_hours": round(weekly_hours, 1),
                "headroom": round(headroom, 1),
                "contacted_at": None,
                "response": "pending",
            })

        # Sort by score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    def _determine_urgency(self, hours_until_shift: float) -> CalloutUrgency:
        if hours_until_shift < 4:
            return CalloutUrgency.EMERGENCY
        elif hours_until_shift < 24:
            return CalloutUrgency.HIGH
        elif hours_until_shift < 48:
            return CalloutUrgency.MEDIUM
        return CalloutUrgency.LOW

    def _calculate_hours(self, start: time, end: time) -> float:
        start_min = start.hour * 60 + start.minute
        end_min = end.hour * 60 + end.minute
        if end_min <= start_min:
            end_min += 24 * 60
        return (end_min - start_min) / 60
