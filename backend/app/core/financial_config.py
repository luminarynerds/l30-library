# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from enum import StrEnum
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal


class DamageLevel(StrEnum):
    NONE = "none"           # 0% charge
    MINOR = "minor"         # 25% charge
    MODERATE = "moderate"   # 50% charge
    MAJOR = "major"         # 50% charge (same as moderate in the audit)
    DESTROYED = "destroyed" # 100% charge


@dataclass
class FineTier:
    tier_number: int
    daily_rate: float
    min_days: int
    max_days: int

    def __str__(self) -> str:
        return f"Tier {self.tier_number}: ${self.daily_rate:.2f}/day (days {self.min_days}-{self.max_days})"


@dataclass
class SMSConfiguration:
    cost_per_segment_cents: int
    max_segments_per_message: int

    def get_max_message_cost_cents(self) -> int:
        return self.cost_per_segment_cents * self.max_segments_per_message

    def get_max_message_cost_dollars(self) -> float:
        return self.get_max_message_cost_cents() / 100.0


@dataclass
class DamageCharges:
    none_damage: float
    minor_damage: float
    moderate_damage: float
    major_damage: float
    destroyed: float

    def get_charge_percentage(self, damage_level: DamageLevel) -> float:
        charge_map = {
            DamageLevel.NONE: self.none_damage,
            DamageLevel.MINOR: self.minor_damage,
            DamageLevel.MODERATE: self.moderate_damage,
            DamageLevel.MAJOR: self.major_damage,
            DamageLevel.DESTROYED: self.destroyed,
        }
        return charge_map.get(damage_level, 0.0)

    def get_charge_amount(self, damage_level: DamageLevel, replacement_cost: float) -> float:
        percentage = self.get_charge_percentage(damage_level)
        return replacement_cost * percentage


class FinancialConfig:

    # Fine Configuration
    FINE_BASE_DAILY_RATE = float(os.getenv("FINE_BASE_DAILY_RATE", "0.25"))
    FINE_MAX_PER_USER = float(os.getenv("FINE_MAX_PER_USER", "25.00"))

    # Fine Tier Configuration
    # Tier 1: Days 1-7 at $0.25/day
    FINE_TIER_1_RATE = float(os.getenv("FINE_TIER_1_RATE", "0.25"))
    FINE_TIER_1_MAX_DAYS = int(os.getenv("FINE_TIER_1_MAX_DAYS", "7"))

    # Tier 2: Days 8-14 at $0.50/day
    FINE_TIER_2_RATE = float(os.getenv("FINE_TIER_2_RATE", "0.50"))
    FINE_TIER_2_MAX_DAYS = int(os.getenv("FINE_TIER_2_MAX_DAYS", "14"))

    # Tier 3: Days 15+ at $1.00/day
    FINE_TIER_3_RATE = float(os.getenv("FINE_TIER_3_RATE", "1.00"))

    # Item Replacement and Damage Configuration
    # Default cost to replace a lost item
    ITEM_REPLACEMENT_COST = float(os.getenv("ITEM_REPLACEMENT_COST", "25.00"))

    # Damage charges as percentages of replacement cost
    # 0% = no charge, 25% = 25% of replacement cost, etc.
    DAMAGE_CHARGE_NONE = float(os.getenv("DAMAGE_CHARGE_NONE", "0.0"))
    DAMAGE_CHARGE_MINOR = float(os.getenv("DAMAGE_CHARGE_MINOR", "0.25"))
    DAMAGE_CHARGE_MODERATE = float(os.getenv("DAMAGE_CHARGE_MODERATE", "0.50"))
    DAMAGE_CHARGE_MAJOR = float(os.getenv("DAMAGE_CHARGE_MAJOR", "0.50"))
    DAMAGE_CHARGE_DESTROYED = float(os.getenv("DAMAGE_CHARGE_DESTROYED", "1.00"))

    # Processing and Administrative Fees
    PROCESSING_FEE = float(os.getenv("PROCESSING_FEE", "5.00"))

    # Claim Limits
    MAX_CLAIMS_PER_YEAR = int(os.getenv("MAX_CLAIMS_PER_YEAR", "3"))

    # SMS/Notification Configuration
    SMS_COST_PER_SEGMENT_CENTS = int(os.getenv("SMS_COST_PER_SEGMENT_CENTS", "1"))
    SMS_MAX_SEGMENTS_PER_MESSAGE = int(os.getenv("SMS_MAX_SEGMENTS_PER_MESSAGE", "3"))

    @classmethod
    def get_fine_tiers(cls) -> list[FineTier]:
        return [
            FineTier(
                tier_number=1,
                daily_rate=cls.FINE_TIER_1_RATE,
                min_days=1,
                max_days=cls.FINE_TIER_1_MAX_DAYS,
            ),
            FineTier(
                tier_number=2,
                daily_rate=cls.FINE_TIER_2_RATE,
                min_days=cls.FINE_TIER_1_MAX_DAYS + 1,
                max_days=cls.FINE_TIER_2_MAX_DAYS,
            ),
            FineTier(
                tier_number=3,
                daily_rate=cls.FINE_TIER_3_RATE,
                min_days=cls.FINE_TIER_2_MAX_DAYS + 1,
                max_days=999,  # No upper limit, continues indefinitely
            ),
        ]

    @classmethod
    def get_fine_tier_for_days_overdue(cls, days_overdue: int) -> FineTier:
        if days_overdue < 1:
            raise ValueError("Days overdue must be at least 1")

        tiers = cls.get_fine_tiers()
        for tier in tiers:
            if tier.min_days <= days_overdue <= tier.max_days:
                return tier

        # Default to the highest tier (should not reach here in normal operation)
        return tiers[-1]

    @classmethod
    def calculate_fine_for_days(cls, days_overdue: int) -> float:
        if days_overdue < 1:
            return 0.0

        total_fine = 0.0
        days_processed = 0
        tiers = cls.get_fine_tiers()

        for tier in tiers:
            if days_processed >= days_overdue:
                break

            # Calculate how many days of this tier apply
            days_in_tier = min(
                tier.max_days - days_processed,
                days_overdue - days_processed,
            )

            # Add the fine for this tier
            total_fine += days_in_tier * tier.daily_rate
            days_processed += days_in_tier

        # Cap the fine at the maximum allowed per user
        return min(total_fine, cls.FINE_MAX_PER_USER)

    @classmethod
    def get_damage_charges(cls) -> DamageCharges:
        return DamageCharges(
            none_damage=cls.DAMAGE_CHARGE_NONE,
            minor_damage=cls.DAMAGE_CHARGE_MINOR,
            moderate_damage=cls.DAMAGE_CHARGE_MODERATE,
            major_damage=cls.DAMAGE_CHARGE_MAJOR,
            destroyed=cls.DAMAGE_CHARGE_DESTROYED,
        )

    @classmethod
    def get_damage_charge_amount(
        cls, damage_level: DamageLevel, replacement_cost: Optional[float] = None
    ) -> float:
        if replacement_cost is None:
            replacement_cost = cls.ITEM_REPLACEMENT_COST

        charges = cls.get_damage_charges()
        return charges.get_charge_amount(damage_level, replacement_cost)

    @classmethod
    def get_sms_config(cls) -> SMSConfiguration:
        return SMSConfiguration(
            cost_per_segment_cents=cls.SMS_COST_PER_SEGMENT_CENTS,
            max_segments_per_message=cls.SMS_MAX_SEGMENTS_PER_MESSAGE,
        )

    @classmethod
    def get_config_summary(cls) -> dict:
        sms_config = cls.get_sms_config()
        damage_charges = cls.get_damage_charges()
        fine_tiers = cls.get_fine_tiers()

        return {
            "fines": {
                "base_daily_rate": cls.FINE_BASE_DAILY_RATE,
                "max_per_user": cls.FINE_MAX_PER_USER,
                "tiers": [
                    {
                        "tier": tier.tier_number,
                        "daily_rate": tier.daily_rate,
                        "min_days": tier.min_days,
                        "max_days": tier.max_days,
                    }
                    for tier in fine_tiers
                ],
            },
            "replacement_and_damage": {
                "default_replacement_cost": cls.ITEM_REPLACEMENT_COST,
                "damage_charges": {
                    "none": damage_charges.none_damage,
                    "minor": damage_charges.minor_damage,
                    "moderate": damage_charges.moderate_damage,
                    "major": damage_charges.major_damage,
                    "destroyed": damage_charges.destroyed,
                },
            },
            "fees": {
                "processing_fee": cls.PROCESSING_FEE,
            },
            "claims": {
                "max_per_year": cls.MAX_CLAIMS_PER_YEAR,
            },
            "sms": {
                "cost_per_segment_cents": sms_config.cost_per_segment_cents,
                "max_segments_per_message": sms_config.max_segments_per_message,
                "max_message_cost_dollars": sms_config.get_max_message_cost_dollars(),
            },
        }


# Initialize a module-level instance for convenience
config = FinancialConfig()
