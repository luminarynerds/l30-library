# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger

from app.models.staff_schedule_fairness import (
    StaffShift, ShiftPreference, FairnessPolicy,
    FairnessShiftType, ShiftStatus, PreferenceType, FairnessPolicyType,
)
from app.models.fair_scheduling import (
    ScheduleGeneration, ScheduleExplanation, StaffSchedulingProfile,
    ScheduleGenerationStatus, ScheduleExplanationType,
    EmploymentType,
)
from app.models.user import User

logger = get_logger(__name__)


# =============================================================================
# DATA CLASSES FOR SOLVER
# =============================================================================

@dataclass
class ShiftSlot:
    slot_id: int
    branch_id: int
    shift_date: date
    shift_type: FairnessShiftType
    start_time: time
    end_time: time
    hours: float
    is_weekend: bool
    is_holiday: bool
    required_skills: List[str] = field(default_factory=list)
    min_staff: int = 1
    is_desirable: bool = False  # Morning shifts, holidays off, etc.


@dataclass
class StaffMember:
    staff_id: int
    name: str
    employment_type: EmploymentType
    skills: List[str]
    min_hours: float
    max_hours: float
    contracted_hours: float
    seniority_level: int
    max_consecutive_days: int
    min_hours_between_shifts: float
    max_weekend_shifts_per_month: int
    max_closing_shifts_per_week: int
    desirable_shift_score: float


@dataclass
class StaffAvailability:
    staff_id: int
    day_of_week: Optional[str]  # None = all days
    shift_type: Optional[FairnessShiftType]
    preference: PreferenceType
    start_time: Optional[time] = None
    end_time: Optional[time] = None


@dataclass
class Assignment:
    slot: ShiftSlot
    staff: StaffMember
    score: float
    explanation_type: ScheduleExplanationType
    explanation_text: str
    contributing_factors: List[Dict]


@dataclass
class SolverResult:
    status: ScheduleGenerationStatus
    assignments: List[Assignment]
    objective_value: float
    solve_time_seconds: float
    violations: List[Dict]
    constraint_summary: Dict
    fairness_score: float


class ConstraintScheduleSolver:

    def __init__(self, db: Session):
        self.db = db

    async def generate_schedule(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
        generated_by_id: int,
        config: Optional[Dict] = None,
    ) -> Tuple[ScheduleGeneration, SolverResult]:
        start_time = datetime.now()
        config = config or self._default_config()

        # Create generation record
        generation = ScheduleGeneration(
            branch_id=branch_id,
            generated_by_id=generated_by_id,
            period_start=period_start,
            period_end=period_end,
            status=ScheduleGenerationStatus.RUNNING,
            solver_config=config,
        )
        self.db.add(generation)
        await self.db.flush()

        try:
            # Phase 1: Load data
            slots = self._generate_shift_slots(branch_id, period_start, period_end, config)
            staff = self._load_staff(branch_id)
            availability = self._load_availability(
                [s.staff_id for s in staff], period_start, period_end
            )
            historical_fairness = self._load_historical_fairness(
                [s.staff_id for s in staff], branch_id
            )

            if not slots or not staff:
                generation.status = ScheduleGenerationStatus.INFEASIBLE
                generation.solve_time_seconds = (datetime.now() - start_time).total_seconds()
                await self.db.commit()
                return generation, SolverResult(
                    status=ScheduleGenerationStatus.INFEASIBLE,
                    assignments=[], objective_value=0, solve_time_seconds=0,
                    violations=[{"type": "no_data", "detail": "No slots or staff available"}],
                    constraint_summary={}, fairness_score=0,
                )

            # Phase 2: Solve
            result = self._solve(slots, staff, availability, historical_fairness, config)

            # Phase 3: Record results
            generation.status = result.status
            generation.objective_value = result.objective_value
            generation.solve_time_seconds = (datetime.now() - start_time).total_seconds()
            generation.total_shifts_assigned = len(result.assignments)
            generation.total_violations = len(result.violations)
            generation.fairness_score = result.fairness_score
            generation.constraint_summary = result.constraint_summary

            # Phase 4: Create shift records and explanations
            if result.status in (ScheduleGenerationStatus.OPTIMAL, ScheduleGenerationStatus.FEASIBLE):
                await self._create_shift_records(generation, result)

            await self.db.commit()
            return generation, result

        except Exception as e:
            logger.error(f"Schedule generation failed: {e}")
            generation.status = ScheduleGenerationStatus.FAILED
            generation.solve_time_seconds = (datetime.now() - start_time).total_seconds()
            await self.db.commit()
            raise

    def _default_config(self) -> Dict:
        return {
            "max_solve_time_seconds": 120,
            "preference_weight": 0.25,
            "fairness_weight": 0.35,
            "coverage_weight": 0.25,
            "fatigue_weight": 0.15,
            "min_staff_per_shift": 2,
            "shifts_per_day": [
                {"type": "opening", "start": "08:00", "end": "13:00", "hours": 5},
                {"type": "midday", "start": "10:00", "end": "15:00", "hours": 5},
                {"type": "closing", "start": "14:00", "end": "20:00", "hours": 6},
                {"type": "evening", "start": "16:00", "end": "21:00", "hours": 5},
            ],
            "skills_required": {
                "opening": ["opening_procedures"],
                "closing": ["closing_procedures"],
            },
            "desirable_shifts": ["opening", "midday"],
            "holiday_dates": [],
        }

    def _generate_shift_slots(
        self, branch_id: int, period_start: date, period_end: date, config: Dict
    ) -> List[ShiftSlot]:
        slots = []
        slot_id = 0
        current = period_start
        desirable_types = set(config.get("desirable_shifts", ["opening", "midday"]))
        holiday_dates = set(config.get("holiday_dates", []))
        skills_required = config.get("skills_required", {})

        while current <= period_end:
            is_weekend = current.weekday() >= 5
            is_holiday = str(current) in holiday_dates

            for shift_def in config.get("shifts_per_day", []):
                shift_type_str = shift_def["type"]
                try:
                    shift_type = FairnessShiftType(shift_type_str.upper()) if shift_type_str.upper() in FairnessShiftType.__members__ else FairnessShiftType.MIDDAY
                except (ValueError, KeyError):
                    shift_type = FairnessShiftType.MIDDAY

                start_parts = shift_def["start"].split(":")
                end_parts = shift_def["end"].split(":")

                slot = ShiftSlot(
                    slot_id=slot_id,
                    branch_id=branch_id,
                    shift_date=current,
                    shift_type=shift_type,
                    start_time=time(int(start_parts[0]), int(start_parts[1])),
                    end_time=time(int(end_parts[0]), int(end_parts[1])),
                    hours=shift_def["hours"],
                    is_weekend=is_weekend,
                    is_holiday=is_holiday,
                    required_skills=skills_required.get(shift_type_str, []),
                    min_staff=config.get("min_staff_per_shift", 2),
                    is_desirable=shift_type_str in desirable_types,
                )
                slots.append(slot)
                slot_id += 1

            current += timedelta(days=1)

        return slots

    def _load_staff(self, branch_id: int) -> List[StaffMember]:
        profiles = self.db.query(StaffSchedulingProfile).filter(
            and_(
                StaffSchedulingProfile.is_active == True,
                (StaffSchedulingProfile.branch_id == branch_id) |
                (StaffSchedulingProfile.branch_id.is_(None)),
            )
        ).all()

        staff = []
        for profile in profiles:
            user = self.db.query(User).filter(User.id == profile.staff_id).first()
            if not user:
                continue

            name = f"{user.first_name} {user.last_name}" if hasattr(user, 'first_name') else str(user.id)
            staff.append(StaffMember(
                staff_id=profile.staff_id,
                name=name,
                employment_type=profile.employment_type,
                skills=profile.skills or [],
                min_hours=profile.min_hours_per_week,
                max_hours=profile.max_hours_per_week,
                contracted_hours=profile.contracted_hours_per_week,
                seniority_level=profile.seniority_level,
                max_consecutive_days=profile.max_consecutive_days,
                min_hours_between_shifts=profile.min_hours_between_shifts,
                max_weekend_shifts_per_month=profile.max_weekend_shifts_per_month,
                max_closing_shifts_per_week=profile.max_closing_shifts_per_week,
                desirable_shift_score=profile.desirable_shift_score,
            ))

        return staff

    def _load_availability(
        self, staff_ids: List[int], period_start: date, period_end: date
    ) -> Dict[int, List[StaffAvailability]]:
        availability_map: Dict[int, List[StaffAvailability]] = {sid: [] for sid in staff_ids}

        prefs = self.db.query(ShiftPreference).filter(
            and_(
                ShiftPreference.staff_id.in_(staff_ids),
                ShiftPreference.effective_date <= period_end,
                (ShiftPreference.end_date.is_(None)) | (ShiftPreference.end_date >= period_start),
            )
        ).all()

        for pref in prefs:
            avail = StaffAvailability(
                staff_id=pref.staff_id,
                day_of_week=pref.day_of_week,
                shift_type=pref.shift_type,
                preference=pref.preference_type,
                start_time=pref.preferred_start_time,
                end_time=pref.preferred_end_time,
            )
            availability_map[pref.staff_id].append(avail)

        return availability_map

    def _load_historical_fairness(
        self, staff_ids: List[int], branch_id: int
    ) -> Dict[int, Dict]:
        from app.models.staff_schedule_fairness import ScheduleBalanceMetrics

        fairness: Dict[int, Dict] = {}
        for staff_id in staff_ids:
            metrics = self.db.query(ScheduleBalanceMetrics).filter(
                and_(
                    ScheduleBalanceMetrics.staff_id == staff_id,
                    ScheduleBalanceMetrics.branch_id == branch_id,
                )
            ).order_by(ScheduleBalanceMetrics.period_end.desc()).first()

            if metrics:
                fairness[staff_id] = {
                    "overall_score": metrics.overall_fairness_score,
                    "weekend_shifts": metrics.weekend_shifts,
                    "holiday_shifts": metrics.holiday_shifts,
                    "opening_shifts": metrics.opening_shifts,
                    "closing_shifts": metrics.closing_shifts,
                    "hours_vs_average": metrics.hours_vs_average,
                }
            else:
                fairness[staff_id] = {
                    "overall_score": 50.0,
                    "weekend_shifts": 0,
                    "holiday_shifts": 0,
                    "opening_shifts": 0,
                    "closing_shifts": 0,
                    "hours_vs_average": 0,
                }

        return fairness

    def _solve(
        self,
        slots: List[ShiftSlot],
        staff: List[StaffMember],
        availability: Dict[int, List[StaffAvailability]],
        historical_fairness: Dict[int, Dict],
        config: Dict,
    ) -> SolverResult:
        assignments: List[Assignment] = []
        violations: List[Dict] = []
        staff_hours: Dict[int, float] = {s.staff_id: 0.0 for s in staff}
        staff_days: Dict[int, Set[date]] = {s.staff_id: set() for s in staff}
        staff_last_shift: Dict[int, Optional[Tuple[date, time]]] = {s.staff_id: None for s in staff}
        staff_weekend_count: Dict[int, int] = {s.staff_id: 0 for s in staff}
        staff_closing_week: Dict[int, int] = {s.staff_id: 0 for s in staff}
        staff_desirable_count: Dict[int, int] = {s.staff_id: 0 for s in staff}

        pref_weight = config.get("preference_weight", 0.25)
        fair_weight = config.get("fairness_weight", 0.35)
        coverage_weight = config.get("coverage_weight", 0.25)
        fatigue_weight = config.get("fatigue_weight", 0.15)

        # Sort slots: harder to fill first (weekends, holidays, skills required)
        sorted_slots = sorted(slots, key=lambda s: (
            -len(s.required_skills),
            -s.is_holiday,
            -s.is_weekend,
            s.shift_date,
        ))

        for slot in sorted_slots:
            # For each slot, need min_staff assignments
            for _ in range(slot.min_staff):
                best_staff = None
                best_score = -float('inf')
                best_factors = []
                best_explanation_type = ScheduleExplanationType.COVERAGE_REQUIRED
                best_explanation_text = ""

                for s in staff:
                    # === HARD CONSTRAINTS ===
                    if not self._check_hard_constraints(
                        s, slot, staff_hours, staff_days, staff_last_shift,
                        staff_weekend_count, assignments, availability
                    ):
                        continue

                    # === SCORING ===
                    factors = []

                    # 1. Preference score
                    pref_score = self._compute_preference_score(
                        s, slot, availability.get(s.staff_id, [])
                    )
                    factors.append({
                        "factor": "preference_match",
                        "weight": pref_weight,
                        "score": pref_score,
                        "detail": self._preference_detail(s, slot, availability.get(s.staff_id, [])),
                    })

                    # 2. Fairness score (favor those who've been under-scheduled)
                    fair_score = self._compute_fairness_score(
                        s, slot, staff_hours, staff_weekend_count,
                        staff_desirable_count, historical_fairness
                    )
                    factors.append({
                        "factor": "fairness_balance",
                        "weight": fair_weight,
                        "score": fair_score,
                        "detail": self._fairness_detail(s, staff_hours, historical_fairness),
                    })

                    # 3. Coverage score (skill match, availability)
                    cov_score = self._compute_coverage_score(s, slot)
                    factors.append({
                        "factor": "skill_coverage",
                        "weight": coverage_weight,
                        "score": cov_score,
                        "detail": f"Skills: {', '.join(s.skills) or 'general'}",
                    })

                    # 4. Fatigue score (favor less tired staff)
                    fatigue_score = self._compute_fatigue_score(
                        s, slot, staff_hours, staff_days, staff_last_shift
                    )
                    factors.append({
                        "factor": "fatigue_prevention",
                        "weight": fatigue_weight,
                        "score": fatigue_score,
                        "detail": self._fatigue_detail(s, staff_hours, staff_days),
                    })

                    # Weighted total
                    total_score = (
                        pref_score * pref_weight
                        + fair_score * fair_weight
                        + cov_score * coverage_weight
                        + fatigue_score * fatigue_weight
                    )

                    if total_score > best_score:
                        best_score = total_score
                        best_staff = s
                        best_factors = factors
                        best_explanation_type = self._determine_explanation_type(factors)
                        best_explanation_text = self._build_explanation_text(
                            s, slot, factors, total_score
                        )

                if best_staff:
                    # Make assignment
                    assignment = Assignment(
                        slot=slot,
                        staff=best_staff,
                        score=best_score,
                        explanation_type=best_explanation_type,
                        explanation_text=best_explanation_text,
                        contributing_factors=best_factors,
                    )
                    assignments.append(assignment)

                    # Update tracking
                    staff_hours[best_staff.staff_id] += slot.hours
                    staff_days[best_staff.staff_id].add(slot.shift_date)
                    staff_last_shift[best_staff.staff_id] = (slot.shift_date, slot.end_time)
                    if slot.is_weekend:
                        staff_weekend_count[best_staff.staff_id] += 1
                    if slot.shift_type == FairnessShiftType.CLOSING:
                        staff_closing_week[best_staff.staff_id] += 1
                    if slot.is_desirable:
                        staff_desirable_count[best_staff.staff_id] += 1
                else:
                    violations.append({
                        "type": "uncovered_shift",
                        "slot_id": slot.slot_id,
                        "date": str(slot.shift_date),
                        "shift_type": slot.shift_type.value if hasattr(slot.shift_type, 'value') else str(slot.shift_type),
                        "detail": "No eligible staff found for this slot",
                    })

        # Calculate final metrics
        total_slots = sum(s.min_staff for s in slots)
        covered = len(assignments)
        coverage_rate = covered / max(total_slots, 1)

        fairness_score = self._calculate_overall_fairness(
            staff, staff_hours, staff_weekend_count, staff_desirable_count
        )

        preferences_honored = self._calculate_preference_honor_rate(
            assignments, availability
        )

        hard_met = total_slots - len([v for v in violations if v["type"] == "uncovered_shift"])

        constraint_summary = {
            "hard_constraints_met": hard_met,
            "hard_constraints_total": total_slots,
            "soft_constraints_met": int(fairness_score / 10),
            "soft_constraints_total": 10,
            "preferences_honored": round(preferences_honored, 2),
            "coverage_rate": round(coverage_rate, 2),
            "coverage_gaps": len([v for v in violations if v["type"] == "uncovered_shift"]),
            "total_hours_assigned": sum(staff_hours.values()),
            "staff_utilization": {
                s.staff_id: round(staff_hours[s.staff_id] / max(s.contracted_hours, 1), 2)
                for s in staff
            },
        }

        status = ScheduleGenerationStatus.OPTIMAL if not violations else ScheduleGenerationStatus.FEASIBLE
        if coverage_rate < 0.8:
            status = ScheduleGenerationStatus.INFEASIBLE

        objective_value = (
            coverage_rate * 0.4
            + fairness_score / 100 * 0.3
            + preferences_honored * 0.3
        )

        return SolverResult(
            status=status,
            assignments=assignments,
            objective_value=round(objective_value, 4),
            solve_time_seconds=0,  # Set by caller
            violations=violations,
            constraint_summary=constraint_summary,
            fairness_score=round(fairness_score, 1),
        )

    # =========================================================================
    # HARD CONSTRAINT CHECKS
    # =========================================================================

    def _check_hard_constraints(
        self,
        staff: StaffMember,
        slot: ShiftSlot,
        staff_hours: Dict[int, float],
        staff_days: Dict[int, Set[date]],
        staff_last_shift: Dict[int, Optional[Tuple[date, time]]],
        staff_weekend_count: Dict[int, int],
        assignments: List[Assignment],
        availability: Dict[int, List[StaffAvailability]],
    ) -> bool:
        sid = staff.staff_id

        # 1. Max hours check
        if staff_hours[sid] + slot.hours > staff.max_hours:
            return False

        # 2. Already assigned to this date+time overlap
        for a in assignments:
            if a.staff.staff_id == sid and a.slot.shift_date == slot.shift_date:
                if self._times_overlap(
                    a.slot.start_time, a.slot.end_time,
                    slot.start_time, slot.end_time
                ):
                    return False

        # 3. Max consecutive days
        consecutive = self._count_consecutive_days(staff_days[sid], slot.shift_date)
        if consecutive >= staff.max_consecutive_days:
            return False

        # 4. Clopening prevention (min hours between shifts)
        last = staff_last_shift[sid]
        if last:
            last_date, last_end = last
            if slot.shift_date == last_date + timedelta(days=1):
                # Calculate gap
                last_end_minutes = last_end.hour * 60 + last_end.minute
                slot_start_minutes = slot.start_time.hour * 60 + slot.start_time.minute
                gap_hours = (24 * 60 - last_end_minutes + slot_start_minutes) / 60
                if gap_hours < staff.min_hours_between_shifts:
                    return False

        # 5. Weekend limit
        if slot.is_weekend and staff_weekend_count[sid] >= staff.max_weekend_shifts_per_month:
            return False

        # 6. Unavailable preference (hard block)
        for avail in availability.get(sid, []):
            if avail.preference == PreferenceType.UNAVAILABLE:
                if self._availability_matches_slot(avail, slot):
                    return False

        # 7. Skill requirements
        for required_skill in slot.required_skills:
            if required_skill not in staff.skills:
                return False

        return True

    # =========================================================================
    # SCORING FUNCTIONS
    # =========================================================================

    def _compute_preference_score(
        self, staff: StaffMember, slot: ShiftSlot,
        avail_list: List[StaffAvailability]
    ) -> float:
        if not avail_list:
            return 0.5  # No preference = neutral

        best_match = 0.5
        for avail in avail_list:
            if self._availability_matches_slot(avail, slot):
                if avail.preference == PreferenceType.PREFERRED:
                    best_match = max(best_match, 1.0)
                elif avail.preference == PreferenceType.ACCEPTABLE:
                    best_match = max(best_match, 0.7)

        return best_match

    def _compute_fairness_score(
        self, staff: StaffMember, slot: ShiftSlot,
        staff_hours: Dict[int, float],
        staff_weekend_count: Dict[int, int],
        staff_desirable_count: Dict[int, int],
        historical: Dict[int, Dict],
    ) -> float:
        sid = staff.staff_id
        hist = historical.get(sid, {})

        # Hours balance: favor staff below their contracted hours
        hours_ratio = staff_hours[sid] / max(staff.contracted_hours, 1)
        hours_score = max(0, 1.0 - hours_ratio)  # Lower hours = higher score

        # Weekend balance: favor staff with fewer weekend shifts
        all_weekend = list(staff_weekend_count.values())
        avg_weekend = sum(all_weekend) / max(len(all_weekend), 1)
        weekend_score = 1.0 if staff_weekend_count[sid] <= avg_weekend else 0.5

        # Desirable shift equity: favor PT/FT staff with fewer desirable shifts
        desirable_scores = list(staff_desirable_count.values())
        avg_desirable = sum(desirable_scores) / max(len(desirable_scores), 1)
        if slot.is_desirable:
            desirable_score = 1.0 if staff_desirable_count[sid] <= avg_desirable else 0.3
        else:
            desirable_score = 0.5

        # Historical overall fairness: favor those with lower historical scores
        hist_score = 1.0 - (hist.get("overall_score", 50) / 100)

        return (hours_score * 0.35 + weekend_score * 0.25 +
                desirable_score * 0.25 + hist_score * 0.15)

    def _compute_coverage_score(self, staff: StaffMember, slot: ShiftSlot) -> float:
        if not slot.required_skills:
            return 0.7  # No skills required = decent match

        matched = sum(1 for s in slot.required_skills if s in staff.skills)
        total = len(slot.required_skills)
        return matched / total if total > 0 else 0.7

    def _compute_fatigue_score(
        self, staff: StaffMember, slot: ShiftSlot,
        staff_hours: Dict[int, float],
        staff_days: Dict[int, Set[date]],
        staff_last_shift: Dict[int, Optional[Tuple[date, time]]],
    ) -> float:
        sid = staff.staff_id

        # Consecutive days penalty
        consecutive = self._count_consecutive_days(staff_days[sid], slot.shift_date)
        consecutive_score = max(0, 1.0 - (consecutive / staff.max_consecutive_days))

        # Hours accumulation penalty
        hours_pct = staff_hours[sid] / max(staff.max_hours, 1)
        hours_score = max(0, 1.0 - hours_pct)

        # Turnaround time score
        turnaround_score = 1.0
        last = staff_last_shift[sid]
        if last:
            last_date, last_end = last
            if slot.shift_date == last_date + timedelta(days=1):
                last_end_minutes = last_end.hour * 60 + last_end.minute
                slot_start_minutes = slot.start_time.hour * 60 + slot.start_time.minute
                gap_hours = (24 * 60 - last_end_minutes + slot_start_minutes) / 60
                turnaround_score = min(1.0, gap_hours / 12.0)

        return consecutive_score * 0.4 + hours_score * 0.3 + turnaround_score * 0.3

    # =========================================================================
    # EXPLANATION BUILDERS
    # =========================================================================

    def _determine_explanation_type(self, factors: List[Dict]) -> ScheduleExplanationType:
        if not factors:
            return ScheduleExplanationType.COVERAGE_REQUIRED

        best = max(factors, key=lambda f: f["score"] * f["weight"])
        factor_map = {
            "preference_match": ScheduleExplanationType.PREFERENCE_HONORED,
            "fairness_balance": ScheduleExplanationType.FAIRNESS_BALANCE,
            "skill_coverage": ScheduleExplanationType.SKILL_MATCH,
            "fatigue_prevention": ScheduleExplanationType.COVERAGE_REQUIRED,
        }
        return factor_map.get(best["factor"], ScheduleExplanationType.COVERAGE_REQUIRED)

    def _build_explanation_text(
        self, staff: StaffMember, slot: ShiftSlot,
        factors: List[Dict], total_score: float
    ) -> str:
        parts = []
        sorted_factors = sorted(factors, key=lambda f: f["score"] * f["weight"], reverse=True)

        for f in sorted_factors[:3]:  # Top 3 factors
            if f["score"] >= 0.7:
                parts.append(f["detail"])

        shift_desc = f"{slot.shift_type.value if hasattr(slot.shift_type, 'value') else slot.shift_type} on {slot.shift_date}"

        if not parts:
            return f"Assigned to {shift_desc} for coverage balance (score: {total_score:.2f})"

        return f"Assigned to {shift_desc}: {'; '.join(parts)} (score: {total_score:.2f})"

    def _preference_detail(
        self, staff: StaffMember, slot: ShiftSlot, avail: List[StaffAvailability]
    ) -> str:
        for a in avail:
            if self._availability_matches_slot(a, slot):
                if a.preference == PreferenceType.PREFERRED:
                    return f"Matches preferred {slot.shift_type.value if hasattr(slot.shift_type, 'value') else slot.shift_type} shift"
                elif a.preference == PreferenceType.ACCEPTABLE:
                    return "Acceptable shift per preferences"
        return "No specific preference"

    def _fairness_detail(
        self, staff: StaffMember, staff_hours: Dict, historical: Dict
    ) -> str:
        hours = staff_hours.get(staff.staff_id, 0)
        hist = historical.get(staff.staff_id, {})
        hist_score = hist.get("overall_score", 50)
        return f"Current hours: {hours:.1f}/{staff.contracted_hours}h, historical fairness: {hist_score:.0f}/100"

    def _fatigue_detail(
        self, staff: StaffMember, staff_hours: Dict, staff_days: Dict
    ) -> str:
        hours = staff_hours.get(staff.staff_id, 0)
        days = len(staff_days.get(staff.staff_id, set()))
        return f"{days} days scheduled, {hours:.1f} hours accumulated"

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _times_overlap(self, start1: time, end1: time, start2: time, end2: time) -> bool:
        return start1 < end2 and start2 < end1

    def _count_consecutive_days(self, days: Set[date], new_date: date) -> int:
        count = 0
        check = new_date - timedelta(days=1)
        while check in days:
            count += 1
            check -= timedelta(days=1)
        return count

    def _availability_matches_slot(self, avail: StaffAvailability, slot: ShiftSlot) -> bool:
        # Day of week check
        if avail.day_of_week:
            day_name = slot.shift_date.strftime("%A").lower()
            if avail.day_of_week.lower() != day_name:
                return False

        # Shift type check
        if avail.shift_type and avail.shift_type != slot.shift_type:
            return False

        # Time range check
        if avail.start_time and slot.start_time < avail.start_time:
            return False
        if avail.end_time and slot.end_time > avail.end_time:
            return False

        return True

    def _calculate_overall_fairness(
        self,
        staff: List[StaffMember],
        staff_hours: Dict[int, float],
        staff_weekend_count: Dict[int, int],
        staff_desirable_count: Dict[int, int],
    ) -> float:
        if not staff:
            return 100.0

        # Hours variance
        hours_list = [staff_hours[s.staff_id] / max(s.contracted_hours, 1) for s in staff]
        hours_avg = sum(hours_list) / len(hours_list) if hours_list else 0
        hours_variance = sum((h - hours_avg) ** 2 for h in hours_list) / max(len(hours_list), 1)
        hours_fairness = max(0, 100 - hours_variance * 100)

        # Weekend variance
        weekend_list = list(staff_weekend_count.values())
        weekend_avg = sum(weekend_list) / max(len(weekend_list), 1)
        weekend_variance = sum((w - weekend_avg) ** 2 for w in weekend_list) / max(len(weekend_list), 1)
        weekend_fairness = max(0, 100 - weekend_variance * 20)

        # Desirable shift variance
        desirable_list = list(staff_desirable_count.values())
        desirable_avg = sum(desirable_list) / max(len(desirable_list), 1)
        desirable_variance = sum((d - desirable_avg) ** 2 for d in desirable_list) / max(len(desirable_list), 1)
        desirable_fairness = max(0, 100 - desirable_variance * 20)

        return hours_fairness * 0.4 + weekend_fairness * 0.3 + desirable_fairness * 0.3

    def _calculate_preference_honor_rate(
        self, assignments: List[Assignment],
        availability: Dict[int, List[StaffAvailability]]
    ) -> float:
        if not assignments:
            return 1.0

        honored = 0
        for a in assignments:
            avails = availability.get(a.staff.staff_id, [])
            for av in avails:
                if av.preference == PreferenceType.PREFERRED:
                    if self._availability_matches_slot(av, a.slot):
                        honored += 1
                        break

        return honored / len(assignments)

    async def _create_shift_records(
        self, generation: ScheduleGeneration, result: SolverResult
    ) -> None:
        for assignment in result.assignments:
            slot = assignment.slot
            staff = assignment.staff

            shift = StaffShift(
                branch_id=slot.branch_id,
                staff_id=staff.staff_id,
                shift_date=slot.shift_date,
                shift_type=slot.shift_type,
                status=ShiftStatus.ASSIGNED,
                scheduled_start=slot.start_time,
                scheduled_end=slot.end_time,
                scheduled_hours=slot.hours,
                is_overtime=False,
                is_holiday=slot.is_holiday,
                is_weekend=slot.is_weekend,
                notes=f"Auto-generated by schedule solver (gen #{generation.id})",
            )
            self.db.add(shift)
            await self.db.flush()

            explanation = ScheduleExplanation(
                generation_id=generation.id,
                shift_id=shift.id,
                staff_id=staff.staff_id,
                explanation_type=assignment.explanation_type,
                explanation_text=assignment.explanation_text,
                contributing_factors=assignment.contributing_factors,
                fairness_impact=assignment.score,
            )
            self.db.add(explanation)
