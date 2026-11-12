# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal
from datetime import datetime, timezone

# From time_config - circulation time values
from .time_config import TimeConfig
# From financial_config - fine rate values
from .financial_config import FinancialConfig
from app.core.datetime_utils import utc_now


# Loan period configuration (From time_config.circulation)
_time_config = TimeConfig()
LOAN_PERIOD_DAYS = _time_config.circulation.loan_period_days
"""Default loan period in days for checkouts."""

# Hold configuration (From time_config.circulation)
HOLD_EXPIRY_DAYS = _time_config.circulation.hold_expiry_days
"""Default number of days a hold remains ready before expiring."""

# Fine configuration (From financial_config)
OVERDUE_FINE_PER_DAY = Decimal(str(FinancialConfig.FINE_BASE_DAILY_RATE))
"""Daily fine amount for overdue items."""

# Grace period (From time_config.circulation)
OVERDUE_GRACE_HOURS = _time_config.circulation.overdue_grace_hours
"""Grace period in hours before overdue fines start accruing. From time_config configuration."""


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
