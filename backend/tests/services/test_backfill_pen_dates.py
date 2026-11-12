# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the one-off PEN America date backfill.

The backfill exists because PenAmericaSyncService._deduplicate skips records
whose (title, author, state, district) already exists and never updates them.
Fixing the date parser therefore does nothing for the 10,046 rows already
imported with a NULL date; only this backfill repairs them.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.models.ban_tracker import BanReport, BanSource, BanType
from scripts.backfill_pen_dates import backfill

_CSV = (
    "PEN America Index of School Book Bans,,,,\n"
    "Bans recorded during the listed school years.,,,,\n"
    "Title,Author,State,District,Date of Challenge/Removal,Ban Status\n"
    "Gender Queer,Maia Kobabe,FL,Escambia County,August 2023,Banned\n"
    "The Bluest Eye,Toni Morrison,TX,Katy ISD,Fall 2023,Banned\n"
    "Looking for Alaska,John Green,FL,Clay County,October 2023,Banned\n"
)


async def _make_report(session, title, author, state, district, when=None):
    report = BanReport(
        title=title,
        author=author,
        state=state,
        district=district,
        source=BanSource.PEN_AMERICA,
        ban_type=BanType.BANNED,
        date_reported=when,
    )
    session.add(report)
    await session.flush()
    return report


def _records():
    from app.services.pen_america_sync_service import parse_csv_records

    return parse_csv_records(_CSV)


@pytest.mark.asyncio
async def test_dry_run_changes_nothing(db_session):
    report = await _make_report(db_session, "Gender Queer", "Maia Kobabe", "FL", "Escambia County")
    stats = await backfill(db_session, _records(), apply=False)

    assert stats["matched_null_rows"] == 1
    assert stats["updated"] == 0
    await db_session.refresh(report)
    assert report.date_reported is None


@pytest.mark.asyncio
async def test_apply_sets_first_of_month(db_session):
    report = await _make_report(db_session, "Gender Queer", "Maia Kobabe", "FL", "Escambia County")
    stats = await backfill(db_session, _records(), apply=True)

    assert stats["updated"] == 1
    await db_session.refresh(report)
    assert report.date_reported == date(2023, 8, 1)


@pytest.mark.asyncio
async def test_season_worded_row_is_left_null(db_session):
    report = await _make_report(db_session, "The Bluest Eye", "Toni Morrison", "TX", "Katy ISD")
    await backfill(db_session, _records(), apply=True)

    await db_session.refresh(report)
    assert report.date_reported is None


@pytest.mark.asyncio
async def test_existing_date_is_never_overwritten(db_session):
    original = date(2019, 5, 17)
    report = await _make_report(
        db_session,
        "Gender Queer",
        "Maia Kobabe",
        "FL",
        "Escambia County",
        when=original,
    )
    stats = await backfill(db_session, _records(), apply=True)

    assert stats["already_dated"] == 1
    assert stats["updated"] == 0
    await db_session.refresh(report)
    assert report.date_reported == original


@pytest.mark.asyncio
async def test_non_pen_rows_are_not_touched(db_session):
    report = BanReport(
        title="Gender Queer",
        author="Maia Kobabe",
        state="FL",
        district="Escambia County",
        source=BanSource.NEWS,
        ban_type=BanType.BANNED,
        date_reported=None,
    )
    db_session.add(report)
    await db_session.flush()

    await backfill(db_session, _records(), apply=True)

    await db_session.refresh(report)
    assert report.date_reported is None


@pytest.mark.asyncio
async def test_running_twice_is_idempotent(db_session):
    report = await _make_report(db_session, "Gender Queer", "Maia Kobabe", "FL", "Escambia County")
    first = await backfill(db_session, _records(), apply=True)
    second = await backfill(db_session, _records(), apply=True)

    assert first["updated"] == 1
    assert second["updated"] == 0
    await db_session.refresh(report)
    assert report.date_reported == date(2023, 8, 1)


@pytest.mark.asyncio
async def test_unmatched_sheet_rows_are_counted_not_inserted(db_session):
    """The backfill updates; it must never create rows."""
    before = len((await db_session.execute(select(BanReport.id))).all())
    stats = await backfill(db_session, _records(), apply=True)
    after = len((await db_session.execute(select(BanReport.id))).all())

    assert before == after
    assert stats["no_match"] == 2  # the two month-dated rows with no DB match


@pytest.mark.asyncio
async def test_touched_records_every_row_it_would_write(db_session):
    """The id log must be complete on a dry run, or it cannot reverse an apply."""
    report = await _make_report(db_session, "Gender Queer", "Maia Kobabe", "FL", "Escambia County")
    touched: list[tuple[int, str]] = []
    await backfill(db_session, _records(), apply=False, touched=touched)

    assert touched == [(report.id, "2023-08-01")]


def test_compat_shim_fires_only_on_an_unpatched_parser(monkeypatch):
    """The shim must be a no-op once the real fix is deployed."""
    import app.services.pen_america_sync_service as pen_svc

    from scripts.backfill_pen_dates import _install_month_precision_compat

    # Current tree carries the fix, so the shim must decline to install.
    assert _install_month_precision_compat() is False

    # Simulate the pre-fix parser: day-precision only.
    def _old_parse(raw: str):
        for fmt in ("%Y-%m-%d", "%B %d, %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None

    monkeypatch.setattr(pen_svc, "_parse_date", _old_parse)
    assert pen_svc._parse_date("August 2023") is None

    assert _install_month_precision_compat() is True
    assert pen_svc._parse_date("August 2023") == date(2023, 8, 1)
    # Day-precision must survive the wrapping.
    assert pen_svc._parse_date("2023-08-15") == date(2023, 8, 15)
    # And a season still names no month.
    assert pen_svc._parse_date("Fall 2023") is None
