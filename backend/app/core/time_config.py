# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Optional, Tuple


class TimeUnit(Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    YEARS = "years"


class TimeConverter:

    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    DAYS_PER_YEAR = 365

    @staticmethod
    def to_minutes(value: int, unit: TimeUnit) -> int:
        if unit == TimeUnit.MINUTES:
            return value
        elif unit == TimeUnit.HOURS:
            return value * TimeConverter.MINUTES_PER_HOUR
        elif unit == TimeUnit.DAYS:
            return value * TimeConverter.HOURS_PER_DAY * TimeConverter.MINUTES_PER_HOUR
        elif unit == TimeUnit.YEARS:
            return value * TimeConverter.DAYS_PER_YEAR * TimeConverter.HOURS_PER_DAY * TimeConverter.MINUTES_PER_HOUR
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

    @staticmethod
    def from_minutes(minutes: int, target_unit: TimeUnit) -> int:
        if target_unit == TimeUnit.MINUTES:
            return minutes
        elif target_unit == TimeUnit.HOURS:
            return minutes // TimeConverter.MINUTES_PER_HOUR
        elif target_unit == TimeUnit.DAYS:
            return minutes // (TimeConverter.MINUTES_PER_HOUR * TimeConverter.HOURS_PER_DAY)
        elif target_unit == TimeUnit.YEARS:
            return minutes // (TimeConverter.MINUTES_PER_HOUR * TimeConverter.HOURS_PER_DAY * TimeConverter.DAYS_PER_YEAR)
        else:
            raise ValueError(f"Unsupported time unit: {target_unit}")


@dataclass
class AuthenticationTime:

    # Access tokens expire after 15 minutes - short window for maximum security
    # but frequent enough to minimize UX friction
    access_token_expire_minutes: int = field(default_factory=lambda: int(
        os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 15)))

    # Refresh tokens expire after 7 days - allows persistent sessions
    # without exposing long-lived access credentials
    refresh_token_expire_days: int = field(default_factory=lambda: int(
        os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7)))

    # Maximum of 5 login attempts before account lockout - prevents
    # brute force attacks while allowing for user typos
    max_login_attempts: int = field(default_factory=lambda: int(
        os.getenv('MAX_LOGIN_ATTEMPTS', 5)))

    # Lockout duration of 15 minutes - long enough to discourage brute force
    # but short enough to not permanently lock out legitimate users
    lockout_duration_minutes: int = field(default_factory=lambda: int(
        os.getenv('LOCKOUT_DURATION_MINUTES', 15)))

    # SMS verification codes expire after 10 minutes - enough time for users
    # to receive and enter code, but limits exposure window
    sms_verification_expiry_minutes: int = field(default_factory=lambda: int(
        os.getenv('SMS_VERIFICATION_EXPIRY_MINUTES', 10)))


@dataclass
class CirculationTime:

    # Standard loan period of 21 days (3 weeks) - common library standard
    # balances access duration with collection circulation needs
    loan_period_days: int = field(default_factory=lambda: int(
        os.getenv('LOAN_PERIOD_DAYS', 21)))

    # Holds expire after 7 days if not picked up - prevents indefinite
    # hold blocking while giving patrons reasonable pickup window
    hold_expiry_days: int = field(default_factory=lambda: int(
        os.getenv('HOLD_EXPIRY_DAYS', 7)))

    # 48-hour grace period before overdue notices - accounts for mail delivery
    # delays and gives patrons extra time to return items
    overdue_grace_hours: int = field(default_factory=lambda: int(
        os.getenv('OVERDUE_GRACE_HOURS', 48)))

    # Send overdue notices every 7 days - regular reminders without spam
    overdue_notice_interval_days: int = field(default_factory=lambda: int(
        os.getenv('OVERDUE_NOTICE_INTERVAL_DAYS', 7)))

    # Account suspension after 14 days overdue - strong incentive to return
    # items while being fair to patrons with temporary issues
    overdue_suspension_days: int = field(default_factory=lambda: int(
        os.getenv('OVERDUE_SUSPENSION_DAYS', 14)))

    # Items considered lost after 30 days overdue - allows time for return
    # while preventing indefinite "lost" status
    lost_item_threshold_days: int = field(default_factory=lambda: int(
        os.getenv('LOST_ITEM_THRESHOLD_DAYS', 30)))

    # Hold pickup window of 7 days - standard library practice matching
    # hold expiry window for consistency
    hold_pickup_days: int = field(default_factory=lambda: int(
        os.getenv('HOLD_PICKUP_DAYS', 7)))


@dataclass
class EquipmentTime:

    # Equipment maximum checkout of 7 days - shorter than books to ensure
    # availability for high-demand items
    equipment_max_checkout_days: int = field(default_factory=lambda: int(
        os.getenv('EQUIPMENT_MAX_CHECKOUT_DAYS', 7)))

    # Maintenance scheduled every 90 days - regular maintenance keeps
    # equipment operational and reliable
    equipment_maintenance_schedule_days: int = field(default_factory=lambda: int(
        os.getenv('EQUIPMENT_MAINTENANCE_SCHEDULE_DAYS', 90)))

    # Room advance booking up to 14 days - gives patrons planning time
    # while preventing too-far-in-advance reservations
    room_advance_booking_days: int = field(default_factory=lambda: int(
        os.getenv('ROOM_ADVANCE_BOOKING_DAYS', 14)))

    # Room checkout maximum of 7 days - similar to equipment to manage
    # facility access and ensure availability for other groups
    room_max_checkout_days: int = field(default_factory=lambda: int(
        os.getenv('ROOM_MAX_CHECKOUT_DAYS', 7)))

    # 15-minute grace period for room no-shows - accommodates minor delays
    # without being too lenient
    room_no_show_grace_minutes: int = field(default_factory=lambda: int(
        os.getenv('ROOM_NO_SHOW_GRACE_MINUTES', 15)))

    # Room reservation reminders 24 hours before - helps patrons remember
    # and prepare, reducing no-show rate
    room_reminder_hours_before: int = field(default_factory=lambda: int(
        os.getenv('ROOM_REMINDER_HOURS_BEFORE', 24)))


@dataclass
class HomeDeliveryTime:

    # HomeDelivery checkout of 28 days - longer than standard to accommodate
    # mobility challenges and delivery logistics
    home_delivery_default_checkout_days: int = field(default_factory=lambda: int(
        os.getenv('HOME_DELIVERY_DEFAULT_CHECKOUT_DAYS', 28)))

    # Delivery reminder 1 day before - gives patrons advance notice of
    # upcoming delivery window
    home_delivery_reminder_days: int = field(default_factory=lambda: int(
        os.getenv('HOME_DELIVERY_DELIVERY_REMINDER_DAYS', 1)))

    # 24-hour delay before feedback collection - allows time after delivery
    # for items to be reviewed before requesting feedback
    home_delivery_feedback_delay_hours: int = field(default_factory=lambda: int(
        os.getenv('HOME_DELIVERY_FEEDBACK_DELAY_HOURS', 24)))

    # Service time estimate of 10 minutes per stop - used for scheduling
    # multiple deliveries in a route
    home_delivery_service_time_minutes: int = field(default_factory=lambda: int(
        os.getenv('HOME_DELIVERY_SERVICE_TIME_MINUTES', 10)))


@dataclass
class DataManagementTime:

    # Job logs retained for 90 days - provides 3-month audit trail for
    # troubleshooting and compliance while managing storage
    job_log_retention_days: int = field(default_factory=lambda: int(
        os.getenv('JOB_LOG_RETENTION_DAYS', 90)))

    # Refresh tokens cleaned up after 30 days - removes old credentials
    # after grace period for cleanup
    refresh_token_cleanup_days: int = field(default_factory=lambda: int(
        os.getenv('REFRESH_TOKEN_CLEANUP_DAYS', 30)))

    # Consent tokens cleaned up after 30 days - ensures temporary access
    # grants don't accumulate
    consent_token_cleanup_days: int = field(default_factory=lambda: int(
        os.getenv('CONSENT_TOKEN_CLEANUP_DAYS', 30)))

    # Inactive accounts eligible for deletion after 3 years - allows
    # significant dormancy before purge while respecting user data
    inactive_account_years: int = field(default_factory=lambda: int(
        os.getenv('INACTIVE_ACCOUNT_YEARS', 3)))

    # Checkout history anonymized after 7 years - provides long retention
    # for statistics while eventually protecting privacy
    checkout_anonymize_years: int = field(default_factory=lambda: int(
        os.getenv('CHECKOUT_ANONYMIZE_YEARS', 7)))


@dataclass
class SMSConfiguration:

    # SMS verification code length - 6 digits is standard for security
    sms_verification_code_length: int = field(default_factory=lambda: int(
        os.getenv('SMS_VERIFICATION_CODE_LENGTH', 6)))

    # Quiet hours start at 9 PM (21:00) - respects user sleep patterns
    # in most time zones
    sms_dnd_start_hour: int = field(default_factory=lambda: int(
        os.getenv('SMS_DND_START_HOUR', 21)))

    # Quiet hours end at 8 AM (08:00) - reasonable morning wake time
    sms_dnd_end_hour: int = field(default_factory=lambda: int(
        os.getenv('SMS_DND_END_HOUR', 8)))

    # Maximum of 3 SMS segments per message - prevents excessive message
    # charges for users on metered plans (approx. 450 characters)
    sms_max_segments_per_message: int = field(default_factory=lambda: int(
        os.getenv('SMS_MAX_SEGMENTS_PER_MESSAGE', 3)))


@dataclass
class OtherServicesTime:

    # Claims review window of 30 days - allows patron time to submit,
    # staff time to investigate thoroughly
    claims_review_days: int = field(default_factory=lambda: int(
        os.getenv('CLAIMS_REVIEW_DAYS', 30)))

    # Certificate expiry warning 14 days before - provides adequate notice
    # for certificate renewal or replacement
    certificate_expiry_warning_days: int = field(default_factory=lambda: int(
        os.getenv('CERTIFICATE_EXPIRY_WARNING_DAYS', 14)))

    # Certificate critical expiry alert at 7 days - urgent reminder if
    # warning period was missed
    certificate_expiry_critical_days: int = field(default_factory=lambda: int(
        os.getenv('CERTIFICATE_EXPIRY_CRITICAL_DAYS', 7)))


class TimeConfig:

    def __init__(self):
        self.auth = AuthenticationTime()
        self.circulation = CirculationTime()
        self.equipment = EquipmentTime()
        self.home_delivery = HomeDeliveryTime()
        self.data_management = DataManagementTime()
        self.sms = SMSConfiguration()
        self.other_services = OtherServicesTime()

    def get_all_timings(self) -> dict:
        return {
            "authentication": self.auth.__dict__,
            "circulation": self.circulation.__dict__,
            "equipment": self.equipment.__dict__,
            "home-delivery": self.home_delivery.__dict__,
            "data_management": self.data_management.__dict__,
            "sms": self.sms.__dict__,
            "other_services": self.other_services.__dict__,
        }

    def is_during_sms_quiet_hours(self, check_time: Optional[datetime] = None) -> bool:
        if check_time is None:
            check_time = datetime.now()

        current_hour = check_time.hour
        start_hour = self.sms.sms_dnd_start_hour
        end_hour = self.sms.sms_dnd_end_hour

        # Handle case where quiet hours span midnight (e.g., 21:00 to 08:00)
        if start_hour > end_hour:
            return current_hour >= start_hour or current_hour < end_hour
        else:
            return start_hour <= current_hour < end_hour

    def is_valid_sms_quiet_hours_config(self) -> bool:
        start = self.sms.sms_dnd_start_hour
        end = self.sms.sms_dnd_end_hour
        return 0 <= start <= 23 and 0 <= end <= 23

    def get_sms_quiet_hours_window(self) -> Tuple[int, int]:
        return (self.sms.sms_dnd_start_hour, self.sms.sms_dnd_end_hour)

    def convert_time(self, value: int, from_unit: TimeUnit, to_unit: TimeUnit) -> int:
        minutes = TimeConverter.to_minutes(value, from_unit)
        return TimeConverter.from_minutes(minutes, to_unit)

    def get_access_token_expiry_in_hours(self) -> int:
        return TimeConverter.from_minutes(
            self.auth.access_token_expire_minutes,
            TimeUnit.HOURS
        )

    def get_refresh_token_expiry_in_hours(self) -> int:
        return TimeConverter.to_minutes(
            self.auth.refresh_token_expire_days,
            TimeUnit.DAYS
        ) // TimeConverter.MINUTES_PER_HOUR

    def get_loan_period_in_hours(self) -> int:
        return TimeConverter.to_minutes(
            self.circulation.loan_period_days,
            TimeUnit.DAYS
        ) // TimeConverter.MINUTES_PER_HOUR

    def validate_timing_constraints(self) -> dict:
        warnings = []

        # Access token should expire before refresh token
        access_minutes = self.auth.access_token_expire_minutes
        refresh_minutes = TimeConverter.to_minutes(
            self.auth.refresh_token_expire_days,
            TimeUnit.DAYS
        )
        if access_minutes >= refresh_minutes:
            warnings.append(
                "Access token expiry should be shorter than refresh token expiry"
            )

        # Lockout duration should be reasonable
        if self.auth.lockout_duration_minutes < 5:
            warnings.append(
                "Lockout duration is very short; consider at least 5 minutes"
            )

        # Overdue grace should be less than suspension threshold
        grace_minutes = TimeConverter.to_minutes(
            self.circulation.overdue_grace_hours,
            TimeUnit.HOURS
        )
        suspension_minutes = TimeConverter.to_minutes(
            self.circulation.overdue_suspension_days,
            TimeUnit.DAYS
        )
        if grace_minutes >= suspension_minutes:
            warnings.append(
                "Overdue grace period should be shorter than suspension threshold"
            )

        # Lost item threshold should be after suspension threshold
        lost_minutes = TimeConverter.to_minutes(
            self.circulation.lost_item_threshold_days,
            TimeUnit.DAYS
        )
        if lost_minutes <= suspension_minutes:
            warnings.append(
                "Lost item threshold should be after suspension threshold"
            )

        # SMS quiet hours should be valid
        if not self.is_valid_sms_quiet_hours_config():
            warnings.append(
                "SMS quiet hours configuration is invalid"
            )

        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings
        }


# Global instance for easy importing
time_config = TimeConfig()
