# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date
from typing import Optional


# Age group boundaries
_AGE_GROUPS = [
    ("juvenile", 0, 12),
    ("teen", 13, 17),
    ("adult", 18, 64),
    ("senior", 65, None),
]


def classify_age_group(date_of_birth: Optional[date]) -> Optional[str]:
    if date_of_birth is None:
        return None

    today = date.today()
    age = today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )

    for group_name, min_age, max_age in _AGE_GROUPS:
        if max_age is None:
            if age >= min_age:
                return group_name
        elif min_age <= age <= max_age:
            return group_name

    return "adult"


def _get_group_config(user, features) -> Optional[dict]:
    if features is None:
        return None

    limits = getattr(features, "age_group_limits", None)
    if limits is None:
        return None

    dob = getattr(user, "date_of_birth", None)
    group = classify_age_group(dob)
    if group is None:
        return None

    # limits may be a dict (from JSONB) or a Pydantic model
    if isinstance(limits, dict):
        return limits.get(group)
    return getattr(limits, group, None)


def get_age_group_checkout_limit(user, features) -> Optional[int]:
    config = _get_group_config(user, features)
    if config is None:
        return None
    if isinstance(config, dict):
        return config.get("max_checkouts")
    return getattr(config, "max_checkouts", None)


def get_age_group_hold_limit(user, features) -> Optional[int]:
    config = _get_group_config(user, features)
    if config is None:
        return None
    if isinstance(config, dict):
        return config.get("max_holds")
    return getattr(config, "max_holds", None)


def get_age_group_checkout_duration(user, features) -> Optional[int]:
    config = _get_group_config(user, features)
    if config is None:
        return None
    if isinstance(config, dict):
        return config.get("checkout_duration_days")
    return getattr(config, "checkout_duration_days", None)
