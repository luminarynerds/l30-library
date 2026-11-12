# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.logging import get_logger

from app.models.fair_scheduling import LearnedPreference
from app.models.staff_schedule_fairness import (
    StaffShift, ShiftPreference, FairnessShiftType, ShiftStatus, PreferenceType,
)
from app.models.shift_swap import (
    ShiftSwapListing, ShiftSwapClaim,
    ShiftSwapListingType, ShiftSwapListingStatus,
)
from app.models.fair_scheduling import CalloutCoverageRequest

logger = get_logger(__name__)

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class PreferenceLearningService:

    def __init__(self, db: Session):
        self.db = db

    async def learn_preferences(
        self,
        staff_id: int,
        lookback_days: int = 180,
    ) -> List[LearnedPreference]:
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Gather evidence from multiple sources
        shift_patterns = self._analyze_shift_patterns(staff_id, start_date, end_date)
        swap_patterns = self._analyze_swap_patterns(staff_id, start_date, end_date)
        callout_patterns = self._analyze_callout_patterns(staff_id, start_date, end_date)
        explicit_prefs = self._load_explicit_preferences(staff_id)

        # Merge all evidence into learned preferences
        merged = self._merge_evidence(
            staff_id, shift_patterns, swap_patterns, callout_patterns,
            explicit_prefs, start_date, end_date
        )

        # Upsert learned preferences
        results = []
        for pref_data in merged:
            existing = self.db.query(LearnedPreference).filter(
                and_(
                    LearnedPreference.staff_id == staff_id,
                    LearnedPreference.preference_category == pref_data["category"],
                    LearnedPreference.preference_value == pref_data["value"],
                )
            ).first()

            if existing:
                existing.preference_strength = pref_data["strength"]
                existing.confidence = pref_data["confidence"]
                existing.evidence = pref_data["evidence"]
                existing.data_start_date = start_date
                existing.data_end_date = end_date
                existing.sample_size = pref_data["sample_size"]
                existing.calculated_at = datetime.now()
                results.append(existing)
            else:
                new_pref = LearnedPreference(
                    staff_id=staff_id,
                    preference_category=pref_data["category"],
                    preference_value=pref_data["value"],
                    preference_strength=pref_data["strength"],
                    confidence=pref_data["confidence"],
                    evidence=pref_data["evidence"],
                    data_start_date=start_date,
                    data_end_date=end_date,
                    sample_size=pref_data["sample_size"],
                )
                self.db.add(new_pref)
                results.append(new_pref)

        await self.db.commit()
        return results

    async def get_staff_preferences(self, staff_id: int) -> List[LearnedPreference]:
        return self.db.query(LearnedPreference).filter(
            LearnedPreference.staff_id == staff_id,
        ).order_by(
            LearnedPreference.confidence.desc()
        ).all()

    async def confirm_preference(
        self, staff_id: int, preference_id: int, confirmed: bool
    ) -> Optional[LearnedPreference]:
        pref = self.db.query(LearnedPreference).filter(
            and_(
                LearnedPreference.id == preference_id,
                LearnedPreference.staff_id == staff_id,
            )
        ).first()

        if pref:
            pref.is_confirmed = confirmed
            pref.confirmed_at = datetime.now()
            if confirmed:
                pref.confidence = min(1.0, pref.confidence + 0.2)
            else:
                pref.confidence = max(0.0, pref.confidence - 0.3)
            await self.db.commit()

        return pref

    def _analyze_shift_patterns(
        self, staff_id: int, start_date: date, end_date: date
    ) -> Dict:
        shifts = self.db.query(StaffShift).filter(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date >= start_date,
                StaffShift.shift_date <= end_date,
                StaffShift.status == ShiftStatus.COMPLETED,
            )
        ).all()

        patterns = {
            "day_counts": defaultdict(int),
            "shift_type_counts": defaultdict(int),
            "total_shifts": len(shifts),
        }

        for shift in shifts:
            day_name = DAY_NAMES[shift.shift_date.weekday()]
            patterns["day_counts"][day_name] += 1
            shift_type_val = shift.shift_type.value if hasattr(shift.shift_type, 'value') else str(shift.shift_type)
            patterns["shift_type_counts"][shift_type_val] += 1

        return patterns

    def _analyze_swap_patterns(
        self, staff_id: int, start_date: date, end_date: date
    ) -> Dict:
        # Shifts given away
        given_away = self.db.query(ShiftSwapListing).filter(
            and_(
                ShiftSwapListing.user_id == staff_id,
                ShiftSwapListing.listing_type == ShiftSwapListingType.giving_away,
                ShiftSwapListing.created_at >= start_date,
                ShiftSwapListing.status.in_([
                    ShiftSwapListingStatus.completed,
                    ShiftSwapListingStatus.claimed,
                ]),
            )
        ).all()

        # Shifts sought
        sought = self.db.query(ShiftSwapListing).filter(
            and_(
                ShiftSwapListing.user_id == staff_id,
                ShiftSwapListing.listing_type == ShiftSwapListingType.looking_for,
                ShiftSwapListing.created_at >= start_date,
            )
        ).all()

        # Claims made (seeking to take others' shifts)
        claims = self.db.query(ShiftSwapClaim).filter(
            and_(
                ShiftSwapClaim.claimer_id == staff_id,
                ShiftSwapClaim.created_at >= start_date,
            )
        ).all()

        patterns = {
            "given_away_days": defaultdict(int),
            "given_away_types": defaultdict(int),
            "sought_days": defaultdict(int),
            "sought_types": defaultdict(int),
            "total_given": len(given_away),
            "total_sought": len(sought),
            "total_claims": len(claims),
        }

        for listing in given_away:
            day_name = DAY_NAMES[listing.shift_date.weekday()]
            patterns["given_away_days"][day_name] += 1
            if listing.shift_type:
                patterns["given_away_types"][str(listing.shift_type)] += 1

        for listing in sought:
            day_name = DAY_NAMES[listing.shift_date.weekday()]
            patterns["sought_days"][day_name] += 1
            if listing.shift_type:
                patterns["sought_types"][str(listing.shift_type)] += 1

        return patterns

    def _analyze_callout_patterns(
        self, staff_id: int, start_date: date, end_date: date
    ) -> Dict:
        callouts = self.db.query(StaffShift).filter(
            and_(
                StaffShift.staff_id == staff_id,
                StaffShift.shift_date >= start_date,
                StaffShift.shift_date <= end_date,
                StaffShift.status == ShiftStatus.CALLED_OUT,
            )
        ).all()

        patterns = {
            "callout_days": defaultdict(int),
            "callout_types": defaultdict(int),
            "total_callouts": len(callouts),
        }

        for shift in callouts:
            day_name = DAY_NAMES[shift.shift_date.weekday()]
            patterns["callout_days"][day_name] += 1
            shift_type_val = shift.shift_type.value if hasattr(shift.shift_type, 'value') else str(shift.shift_type)
            patterns["callout_types"][shift_type_val] += 1

        return patterns

    def _load_explicit_preferences(self, staff_id: int) -> List[Dict]:
        prefs = self.db.query(ShiftPreference).filter(
            and_(
                ShiftPreference.staff_id == staff_id,
                (ShiftPreference.end_date.is_(None)) | (ShiftPreference.end_date >= date.today()),
            )
        ).all()

        return [
            {
                "day_of_week": p.day_of_week,
                "shift_type": p.shift_type.value if p.shift_type and hasattr(p.shift_type, 'value') else p.shift_type,
                "preference_type": p.preference_type.value if hasattr(p.preference_type, 'value') else str(p.preference_type),
            }
            for p in prefs
        ]

    def _merge_evidence(
        self, staff_id: int, shift_patterns: Dict, swap_patterns: Dict,
        callout_patterns: Dict, explicit_prefs: List[Dict],
        start_date: date, end_date: date
    ) -> List[Dict]:
        learned = []
        shift_patterns.get("total_shifts", 0)

        # --- Day of week preferences ---
        for day in DAY_NAMES:
            evidence = []
            strength = 0.0
            sample_size = 0

            # Swap evidence (strong signal)
            given = swap_patterns["given_away_days"].get(day, 0)
            sought = swap_patterns["sought_days"].get(day, 0)
            if given > 0:
                evidence.append({
                    "type": "swap_away", "count": given,
                    "detail": f"Traded away {given} {day} shifts"
                })
                strength -= given * 0.15
                sample_size += given
            if sought > 0:
                evidence.append({
                    "type": "swap_seek", "count": sought,
                    "detail": f"Sought {sought} {day} shifts"
                })
                strength += sought * 0.15
                sample_size += sought

            # Callout evidence (moderate signal)
            callouts = callout_patterns["callout_days"].get(day, 0)
            if callouts > 0:
                evidence.append({
                    "type": "callout", "count": callouts,
                    "detail": f"Called out on {callouts} {day}s"
                })
                strength -= callouts * 0.1
                sample_size += callouts

            # Explicit preference (strongest signal)
            for ep in explicit_prefs:
                if ep.get("day_of_week") and ep["day_of_week"].lower() == day:
                    ptype = ep["preference_type"]
                    if ptype == "preferred":
                        strength += 0.4
                    elif ptype == "unavailable":
                        strength -= 0.5
                    evidence.append({
                        "type": "explicit", "count": 1,
                        "detail": f"Stated {ptype} for {day}"
                    })
                    sample_size += 1

            if evidence:
                strength = max(-1.0, min(1.0, strength))
                confidence = min(1.0, sample_size / 10)
                learned.append({
                    "category": "day_of_week",
                    "value": day,
                    "strength": round(strength, 3),
                    "confidence": round(confidence, 3),
                    "evidence": evidence,
                    "sample_size": sample_size,
                })

        # --- Shift type preferences ---
        shift_types = ["opening", "closing", "midday", "evening", "full_day"]
        for stype in shift_types:
            evidence = []
            strength = 0.0
            sample_size = 0

            given = swap_patterns["given_away_types"].get(stype, 0)
            sought = swap_patterns["sought_types"].get(stype, 0)
            if given > 0:
                evidence.append({
                    "type": "swap_away", "count": given,
                    "detail": f"Traded away {given} {stype} shifts"
                })
                strength -= given * 0.15
                sample_size += given
            if sought > 0:
                evidence.append({
                    "type": "swap_seek", "count": sought,
                    "detail": f"Sought {sought} {stype} shifts"
                })
                strength += sought * 0.15
                sample_size += sought

            callouts = callout_patterns["callout_types"].get(stype, 0)
            if callouts > 0:
                evidence.append({
                    "type": "callout", "count": callouts,
                    "detail": f"Called out of {callouts} {stype} shifts"
                })
                strength -= callouts * 0.1
                sample_size += callouts

            for ep in explicit_prefs:
                if ep.get("shift_type") and ep["shift_type"] == stype:
                    ptype = ep["preference_type"]
                    if ptype == "preferred":
                        strength += 0.4
                    elif ptype == "unavailable":
                        strength -= 0.5
                    evidence.append({
                        "type": "explicit", "count": 1,
                        "detail": f"Stated {ptype} for {stype}"
                    })
                    sample_size += 1

            if evidence:
                strength = max(-1.0, min(1.0, strength))
                confidence = min(1.0, sample_size / 10)
                learned.append({
                    "category": "shift_type",
                    "value": stype,
                    "strength": round(strength, 3),
                    "confidence": round(confidence, 3),
                    "evidence": evidence,
                    "sample_size": sample_size,
                })

        return learned
