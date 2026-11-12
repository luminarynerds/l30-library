# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for PEN America challenge-date parsing.

PEN publishes the challenge date at MONTH granularity ("August 2023"), never
with a day. The parser originally accepted only day-precision formats, so every
PEN row landed with date_reported NULL -- 10,046 of 10,091 rows in production --
and the public monthly-trend chart plotted 45 events across 78 months.

The values below are the complete set of distinct date strings in PEN's live
2023-24 sheet, with their row counts, read on 2026-08-04.
"""

from datetime import date

import pytest

from app.services.pen_america_sync_service import _parse_date, parse_csv_records

# Every distinct date value in PEN's published 2023-24 sheet, and how many rows
# carry it. 10,033 of 10,046 dated rows use "Month YYYY"; 13 use a season word.
_PEN_MONTH_VALUES = {
    "June 2024": (date(2024, 6, 1), 3229),
    "August 2023": (date(2023, 8, 1), 2192),
    "October 2023": (date(2023, 10, 1), 1856),
    "December 2023": (date(2023, 12, 1), 729),
    "November 2023": (date(2023, 11, 1), 612),
    "September 2023": (date(2023, 9, 1), 321),
    "April 2024": (date(2024, 4, 1), 243),
    "February 2024": (date(2024, 2, 1), 230),
    "July 2023": (date(2023, 7, 1), 227),
    "March 2024": (date(2024, 3, 1), 181),
    "January 2024": (date(2024, 1, 1), 118),
    "May 2024": (date(2024, 5, 1), 95),
}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(raw, expected) for raw, (expected, _n) in _PEN_MONTH_VALUES.items()],
)
def test_month_precision_dates_parse_to_first_of_month(raw: str, expected: date) -> None:
    assert _parse_date(raw) == expected


def test_month_precision_covers_the_bulk_of_the_published_sheet() -> None:
    """Guards the claim the fix rests on: these values are not a rare edge case."""
    parsed_rows = sum(n for _d, n in _PEN_MONTH_VALUES.values())
    assert parsed_rows == 10_033


def test_abbreviated_month_precision_parses() -> None:
    # PEN has used several header and value spellings over the years.
    assert _parse_date("Aug 2023") == date(2023, 8, 1)


def test_season_worded_dates_are_left_unset() -> None:
    """A season names no month, so inventing one would fabricate precision.

    13 rows in the 2023-24 sheet read "Fall 2023". They stay NULL rather than
    silently becoming September.
    """
    assert _parse_date("Fall 2023") is None
    assert _parse_date("Spring 2024") is None


def test_day_precision_formats_still_parse() -> None:
    """Positive control: the formats that already worked must keep working."""
    assert _parse_date("2023-08-15") == date(2023, 8, 15)
    assert _parse_date("8/15/2023") == date(2023, 8, 15)
    assert _parse_date("August 15, 2023") == date(2023, 8, 15)


def test_empty_and_garbage_still_return_none() -> None:
    assert _parse_date("") is None
    assert _parse_date("   ") is None
    assert _parse_date("not a date") is None
    # A bare year names no month either.
    assert _parse_date("2023") is None


def test_parse_csv_records_populates_date_from_month_precision() -> None:
    """End-to-end through the CSV parser, using PEN's real date format.

    The pre-existing fixture in test_pen_america_sync_parser.py used
    "2023-09-01", a day-precision value PEN does not publish, which is why the
    parser gap survived having tests.
    """
    csv_text = (
        "PEN America Index of School Book Bans,,,,\n"
        "Bans recorded during the listed school years.,,,,\n"
        "Title,Author,State,Date of Challenge/Removal,Ban Status\n"
        "Gender Queer,Maia Kobabe,FL,August 2023,Banned\n"
        "The Bluest Eye,Toni Morrison,TX,Fall 2023,Banned\n"
    )
    by_title = {r["title"]: r for r in parse_csv_records(csv_text)}

    assert by_title["Gender Queer"]["date_reported"] == date(2023, 8, 1)
    # The season row parses as a record but carries no date.
    assert "date_reported" not in by_title["The Bluest Eye"]
