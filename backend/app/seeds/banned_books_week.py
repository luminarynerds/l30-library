# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Seed the Banned Books Week program and its cited booklist.

Dates come from fixtures/banned_books_week.json, the same file the
frontend year table is tested against, so one annual edit updates the
page and the program together.

Titles resolve by title string, never by ID: catalog IDs are
instance-local and a forked library has different ones. A title this
catalog does not hold is skipped and counted, not an error.

Every entry's note carries a sourced challenge record. An entry without
one does not belong in this list; see
docs/banned-books-citations.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.reading import ProgramBooklistItem, ReadingProgram, ReadingProgramType

FIXTURE = Path(__file__).parent / "fixtures" / "banned_books_week.json"
SEED_YEAR = 2026
PROGRAM_NAME = f"Banned Books Week {SEED_YEAR}"

# Populated from Task 4's citation table
# (docs/banned-books-citations.md). Only the five titles graded [P] or [C]
# there are listed; the five graded [X] were checked and did not hold up,
# and are deliberately left out. Notes copied verbatim from that file.
BOOKLIST: list[dict[str, str]] = [
    {
        "title": "Adventures of Huckleberry Finn",
        "note": (
            "Removed from required reading in Duluth, MN public schools, Feb. 2018, "
            "after long-standing complaints about racial slurs in the text. "
            "Curriculum director Michael Cary said other novels could meet the same "
            "standards without students feeling humiliated or marginalized; copies "
            "stayed in school libraries for independent reading. Source: "
            "https://newscut.mprnews.org/2018/02/huck-finn-boo-tossed-off-duluth-schools-required-reading-list"
        ),
    },
    {
        "title": "The Wonderful Wizard of Oz",
        "note": (
            "Detroit Public Library director Ralph Ulveling told a 1957 state "
            'library conference the Oz series had "no value" and promoted '
            '"negativism," continuing a decades-old policy of not buying new '
            'copies for children\'s collections. He called it "selection," not '
            "banning, but the decision drew national controversy. Source: "
            "https://en.wikipedia.org/wiki/Ralph_Ulveling"
        ),
    },
    {
        "title": "Ulysses",
        "note": (
            "US Customs seized the Paris edition of Ulysses when Random House "
            "imported it in 1932 to force a test case against the US import ban. "
            "Federal judge John M. Woolsey ruled Dec. 6, 1933 that the novel was "
            "not obscene, lifting the ban. A customs seizure and federal obscenity "
            "ruling, not a library challenge. Source: "
            "https://www.courtlistener.com/opinion/2250768/united-states-v-one-book-called-ulysses/"
        ),
    },
    {
        "title": "Leaves of Grass",
        "note": (
            "Boston District Attorney Oliver Stevens threatened publisher James "
            "Osgood with obscenity prosecution in March 1882 over specific poems "
            "in Leaves of Grass. Whitman refused to cut them; Osgood dropped the "
            "book under the threat, and Whitman had it reprinted by a "
            "Philadelphia publisher instead. Source: "
            "https://whitmanarchive.org/item/encyclopedia_entry211"
        ),
    },
    {
        "title": "Uncle Tom's Cabin",
        "note": (
            "Rev. Samuel Green, a free Black preacher in Dorchester County, MD, "
            "was convicted at the April 1857 term for possessing a copy of Uncle "
            "Tom's Cabin and sentenced to 10 years in the Maryland Penitentiary. "
            "A criminal prosecution under antebellum MD law, not a library "
            "challenge. Source: "
            "https://stampedes.dickinson.edu/document/annapolis-md-gazette-sam-green-and-uncle-toms-cabin-september-2-1858"
        ),
    },
]


def _campaign(year: int = SEED_YEAR) -> dict[str, Any]:
    data = json.loads(FIXTURE.read_text())
    entry = data[str(year)]
    return {
        "start": date.fromisoformat(entry["start"]),
        "end": date.fromisoformat(entry["end"]),
        "theme": entry["theme"],
    }


async def seed_banned_books_week(db: AsyncSession) -> dict[str, int]:
    campaign = _campaign()

    program = (
        await db.execute(select(ReadingProgram).where(ReadingProgram.name == PROGRAM_NAME))
    ).scalar_one_or_none()

    program_created = 0
    if program is None:
        program = ReadingProgram(
            name=PROGRAM_NAME,
            description=(
                f'Read a challenged book with us. This year\'s theme is "{campaign["theme"]}"'
            ),
            program_type=ReadingProgramType.special,
            age_group="All Ages",
            start_date=campaign["start"],
            end_date=campaign["end"],
            is_active=True,
        )
        db.add(program)
        await db.flush()
        program_created = 1

    existing_item_ids = set(
        (
            await db.execute(
                select(ProgramBooklistItem.catalog_item_id).where(
                    ProgramBooklistItem.program_id == program.id
                )
            )
        )
        .scalars()
        .all()
    )

    added = 0
    missing = 0
    for order, entry in enumerate(BOOKLIST):
        # order_by(CatalogItem.id) makes the pick deterministic when a title
        # matches more than one edition (e.g. a hardcover and a large-print
        # CatalogItem row sharing the same title -- title carries no unique
        # constraint). Without it, an unordered LIMIT 1 could resolve to a
        # different row on a later run, inserting a second booklist entry
        # for the same book and breaking idempotency.
        item = (
            await db.execute(
                select(CatalogItem)
                .where(CatalogItem.title == entry["title"])
                .order_by(CatalogItem.id)
                .limit(1)
            )
        ).scalar_one_or_none()

        if item is None:
            missing += 1
            continue
        if item.id in existing_item_ids:
            continue

        db.add(
            ProgramBooklistItem(
                program_id=program.id,
                catalog_item_id=item.id,
                display_order=order,
                note=entry["note"],
            )
        )
        existing_item_ids.add(int(item.id))
        added += 1

    await db.commit()
    return {
        "program_created": program_created,
        "booklist_added": added,
        "titles_missing": missing,
    }
