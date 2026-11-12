# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date

# Federal COPPA threshold: operators must obtain verifiable parental
# consent before collecting personal information from children under 13.
COPPA_AGE_THRESHOLD = 13


def calculate_age(date_of_birth: date) -> int:
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def is_under_coppa_age(date_of_birth: date) -> bool:
    return calculate_age(date_of_birth) < COPPA_AGE_THRESHOLD
