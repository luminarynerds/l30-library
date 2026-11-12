# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for hold queue wait-time estimate logic.

Tests the pure math in compute_hold_wait_estimate() — no DB, no fixtures.
Formula: estimated_wait_days = ceil(position / copies) * loan_period_days
         estimated_wait_weeks = ceil(estimated_wait_days / 7)
"""
import pytest
from math import ceil

from app.services.hold_wait_estimate import compute_hold_wait_estimate


def test_position1_3copies_21d_gives_1week():
    """Position 1 of 3 copies, 21-day loan → ceil(1/3)=1 cycle × 21d = 21d → 3 weeks."""
    result = compute_hold_wait_estimate(position=1, copies=3, loan_period_days=21)
    assert result is not None
    assert result["estimated_wait_days"] == 21
    assert result["estimated_wait_weeks"] == 3


def test_position5_2copies_14d_gives_6weeks():
    """Position 5 of 2 copies, 14-day loan → ceil(5/2)=3 cycles × 14d = 42d → ceil(42/7)=6 weeks."""
    result = compute_hold_wait_estimate(position=5, copies=2, loan_period_days=14)
    assert result is not None
    assert result["estimated_wait_days"] == 42
    assert result["estimated_wait_weeks"] == 6


def test_position1_1copy_21d_gives_3weeks():
    """Position 1, single copy, 21-day loan → 1 cycle × 21d = 21d → 3 weeks."""
    result = compute_hold_wait_estimate(position=1, copies=1, loan_period_days=21)
    assert result is not None
    assert result["estimated_wait_days"] == 21
    assert result["estimated_wait_weeks"] == 3


def test_ready_hold_returns_none():
    """Ready holds have no wait — return None."""
    result = compute_hold_wait_estimate(position=None, copies=2, loan_period_days=21, is_ready=True)
    assert result is None


def test_position_none_returns_none():
    """Unknown position → None."""
    result = compute_hold_wait_estimate(position=None, copies=2, loan_period_days=21)
    assert result is None


def test_position_zero_returns_none():
    """Position 0 is pathological → None."""
    result = compute_hold_wait_estimate(position=0, copies=2, loan_period_days=21)
    assert result is None


def test_zero_copies_treated_as_one():
    """Zero copies (zero-copy title per #1545) → treated as 1 virtual copy."""
    result = compute_hold_wait_estimate(position=1, copies=0, loan_period_days=21)
    assert result is not None
    assert result["estimated_wait_days"] == 21
    assert result["estimated_wait_weeks"] == 3


def test_absurd_wait_over_one_year_returns_none():
    """Wait > 52 weeks (e.g. position 100, 1 copy, 21d) → null (too uncertain)."""
    # 100 cycles × 21d = 2100d → 300 weeks → capped
    result = compute_hold_wait_estimate(position=100, copies=1, loan_period_days=21)
    assert result is None


def test_fractional_cycles_round_up():
    """position=3, copies=2 → ceil(3/2)=2 cycles × 21d = 42d → 6 weeks."""
    result = compute_hold_wait_estimate(position=3, copies=2, loan_period_days=21)
    assert result is not None
    assert result["estimated_wait_days"] == 42
    assert result["estimated_wait_weeks"] == 6


def test_fractional_weeks_round_up():
    """10d wait → ceil(10/7)=2 weeks (round up to be conservative)."""
    result = compute_hold_wait_estimate(position=1, copies=1, loan_period_days=10)
    assert result is not None
    assert result["estimated_wait_days"] == 10
    assert result["estimated_wait_weeks"] == 2


def test_exactly_52_weeks_included():
    """364 days = exactly 52 weeks → included (not capped)."""
    # We need position/copies/loan_period_days = 364d
    # 4 copies, 91-day loan, position=1 → 1 cycle × 91d = 91d → 13 weeks → fine
    # Let's use: 1 copy, 7-day loan, position=52 → 52 × 7 = 364d → 52 weeks
    result = compute_hold_wait_estimate(position=52, copies=1, loan_period_days=7)
    assert result is not None
    assert result["estimated_wait_weeks"] == 52


def test_53_weeks_returns_none():
    """371 days > 52 weeks → capped → None."""
    result = compute_hold_wait_estimate(position=53, copies=1, loan_period_days=7)
    assert result is None
