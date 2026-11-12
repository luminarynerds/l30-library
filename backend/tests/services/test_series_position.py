# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from app.services.series_position import parse_series_position


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Bare integers (the graphic-novel cluster in prod)
        ("1", 1),
        ("2", 2),
        ("42", 42),
        ("  7  ", 7),
        # Common freeform prefixes
        ("Book 1", 1),
        ("Book 4", 4),
        ("Vol. 3", 3),
        ("vol 3", 3),
        ("v.12", 12),
        ("#2", 2),
        ("no. 7", 7),
        ("Issue 28", 28),  # the periodical cluster in prod
        ("Issue 100", 100),
        ("Part 5", 5),
    ],
)
def test_parses_common_formats(raw, expected):
    assert parse_series_position(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "Omnibus",
        "Suppl.",
        "Index",
        "2.5",        # in-between novella -- ambiguous, refuse
        "1-3",        # omnibus range -- ambiguous, refuse
        "1 - 3",
        "vol. 1-2",
    ],
)
def test_returns_none_when_unparseable_or_ambiguous(raw):
    assert parse_series_position(raw) is None


def test_first_integer_wins_for_prefixed_value():
    # "Issue 28" -> 28, not some later number; first run only.
    assert parse_series_position("Issue 28 of 99") == 28


def test_absurd_values_rejected():
    assert parse_series_position("999999999") is None
