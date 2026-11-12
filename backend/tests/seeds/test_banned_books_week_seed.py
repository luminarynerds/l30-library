# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seeder for the Banned Books Week program and its cited booklist."""

import json
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.catalog import CatalogItem
from app.models.reading import ProgramBooklistItem, ReadingProgram
from app.seeds import banned_books_week
from app.seeds.banned_books_week import BOOKLIST, SEED_YEAR, seed_banned_books_week


@pytest.mark.asyncio
async def test_creates_the_program_with_fixture_dates(db_session, tmp_path, monkeypatch):
    # Point the seeder at a fixture whose dates are deliberately NOT the real
    # BBW 2026 Oct 4-10 dates. A seeder that silently hardcoded those real
    # dates instead of reading FIXTURE at seed time would still produce
    # Oct 4-10 here and fail this test; only a seeder that genuinely reads
    # the (patched) FIXTURE picks up these values. (Spec review finding 3:
    # comparing against the real fixture's own values doesn't discriminate,
    # since a hardcoded seeder happens to equal them today.)
    alt_fixture = tmp_path / "banned_books_week.json"
    alt_fixture.write_text(
        json.dumps(
            {
                str(SEED_YEAR): {
                    "start": "2027-03-15",
                    "end": "2027-03-21",
                    "theme": "A Deliberately Different Theme",
                    "freedom_read_day": "2027-03-21",
                }
            }
        )
    )
    monkeypatch.setattr(banned_books_week, "FIXTURE", alt_fixture)

    await seed_banned_books_week(db_session)

    program = (
        await db_session.execute(
            select(ReadingProgram).where(ReadingProgram.name.ilike("%Banned Books Week%"))
        )
    ).scalar_one()

    assert program.start_date == date(2027, 3, 15)
    assert program.end_date == date(2027, 3, 21)
    assert program.program_type.value == "special"


@pytest.mark.asyncio
async def test_is_idempotent(db_session):
    first = await seed_banned_books_week(db_session)
    programs_after_first = (
        await db_session.execute(select(func.count()).select_from(ReadingProgram))
    ).scalar_one()
    booklist_after_first = (
        await db_session.execute(select(func.count()).select_from(ProgramBooklistItem))
    ).scalar_one()

    second = await seed_banned_books_week(db_session)

    assert second["program_created"] == 0
    assert second["booklist_added"] == 0
    assert (
        await db_session.execute(select(func.count()).select_from(ReadingProgram))
    ).scalar_one() == programs_after_first
    assert (
        await db_session.execute(select(func.count()).select_from(ProgramBooklistItem))
    ).scalar_one() == booklist_after_first
    assert first["program_created"] == 1


@pytest.mark.asyncio
async def test_idempotent_with_partial_booklist_and_duplicate_titled_editions(db_session):
    # Two CatalogItem rows share a title (e.g. a hardcover and a large-print
    # edition of the same book) -- title carries no unique constraint. If the
    # catalog lookup in the seeder isn't ordered deterministically, a second
    # run could resolve the title to a *different* row than the first run
    # picked, inserting a second booklist entry for the same book and
    # breaking idempotency without ever tripping the
    # (program_id, catalog_item_id) unique constraint, since the two rows
    # have different ids.
    #
    # NOTE (spec review finding 2): this behavioral test alone does not
    # prove the ordering fix works -- rows inserted fresh in the same
    # session/transaction come back from Postgres in heap order, which
    # happens to equal id order, so it passes whether or not the lookup
    # query is actually ordered. Kept for behavioral coverage of the
    # partial-booklist path; see
    # test_catalog_lookup_query_is_ordered_for_deterministic_limit_1 below
    # for the test that actually discriminates ordered from unordered.
    db_session.add_all(
        [
            CatalogItem(title="Uncle Tom's Cabin", item_type="book"),
            CatalogItem(title="Uncle Tom's Cabin", item_type="book"),
            CatalogItem(title="Ulysses", item_type="book"),
        ]
    )
    await db_session.flush()

    first = await seed_banned_books_week(db_session)
    assert first["booklist_added"] == 2  # Uncle Tom's Cabin (once) + Ulysses
    assert first["titles_missing"] == len(BOOKLIST) - 2

    booklist_after_first = (
        await db_session.execute(select(func.count()).select_from(ProgramBooklistItem))
    ).scalar_one()

    second = await seed_banned_books_week(db_session)

    assert second["program_created"] == 0
    assert second["booklist_added"] == 0
    assert second["titles_missing"] == len(BOOKLIST) - 2
    assert (
        await db_session.execute(select(func.count()).select_from(ProgramBooklistItem))
    ).scalar_one() == booklist_after_first


@pytest.mark.asyncio
async def test_catalog_lookup_query_is_ordered_for_deterministic_limit_1(db_session, monkeypatch):
    # CatalogItem.title carries no unique constraint, so a title can match
    # more than one edition, and an unordered LIMIT 1 has no guaranteed
    # stable row order across runs. A black-box, result-order-dependent test
    # can't reliably prove this is fixed (see the note on the test above),
    # so inspect the actual query the seeder issues instead of trusting
    # which row comes back.
    captured = []
    original_execute = db_session.execute

    async def spy_execute(statement, *args, **kwargs):
        captured.append(statement)
        return await original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", spy_execute)

    await seed_banned_books_week(db_session)

    catalog_lookup_sql = [str(stmt) for stmt in captured if "FROM catalog_items" in str(stmt)]
    assert catalog_lookup_sql, "seeder never queried catalog_items"
    for sql in catalog_lookup_sql:
        assert "ORDER BY" in sql.upper(), f"CatalogItem lookup has no ORDER BY: {sql}"


@pytest.mark.asyncio
async def test_skips_titles_absent_from_this_catalog(db_session):
    db_session.add(CatalogItem(title="Adventures of Huckleberry Finn", item_type="book"))
    await db_session.flush()

    result = await seed_banned_books_week(db_session)

    assert result["booklist_added"] == 1
    assert result["titles_missing"] == len(BOOKLIST) - 1


async def test_booklist_is_not_empty():
    # Without this, the citation test below passes vacuously on an empty
    # list and the seeder ships with nothing in it.
    assert len(BOOKLIST) >= 1, "Task 4 produced no citable titles; do not ship an empty booklist"


@pytest.mark.asyncio
async def test_every_booklist_entry_carries_a_citation():
    for entry in BOOKLIST:
        assert entry["note"].strip(), f"{entry['title']} has an empty note"
        assert "http" in entry["note"], f"{entry['title']} has no source URL"
        assert len(entry["note"]) <= 500, f"{entry['title']} note exceeds the column"
