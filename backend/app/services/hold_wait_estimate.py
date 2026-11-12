# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold queue wait-time estimate computation.

Formula (PENDING holds only):
    cycles = ceil(position / copies)          # how many full loan cycles before patron's turn
    estimated_wait_days = cycles * loan_period_days
    estimated_wait_weeks = ceil(estimated_wait_days / 7)

Caps at 52 weeks; returns None for ready holds, unknown positions, or absurd
estimates (which are more dishonest than helpful).
"""
from math import ceil

_MAX_WEEKS = 52


def compute_hold_wait_estimate(
    *,
    position: int | None,
    copies: int,
    loan_period_days: int,
    is_ready: bool = False,
) -> dict[str, int] | None:
    """Return {"estimated_wait_days": int, "estimated_wait_weeks": int} or None.

    None means "we can't give a useful estimate" — callers should omit the field
    rather than show a confusing 0 or a capped message.
    """
    if is_ready:
        return None
    if not position or position <= 0:
        return None

    effective_copies = max(copies, 1)  # zero-copy titles circulate as one virtual copy

    cycles = ceil(position / effective_copies)
    wait_days = cycles * loan_period_days
    wait_weeks = ceil(wait_days / 7)

    if wait_weeks > _MAX_WEEKS:
        return None

    return {"estimated_wait_days": wait_days, "estimated_wait_weeks": wait_weeks}
