# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import csv
import io

import httpx

from app.core.logging import get_logger
from app.models.release_tracker import ReleaseSource
from app.schemas.release_tracker import EditorialTitle

from .base import clean_isbn13, normalize_author_name, parse_us_date

logger = get_logger(__name__)

# LibraryReads' own intentionally-public archive sheet (pinned; resolved from bit.ly/LibraryReadsPublicArchive).
_SHEET_ID = "1sPZhPu2HFFngko2fD4k3n3D5HBqExZQnvaNzV41nOUM"
_GID = "775021022"
_CSV_URL = f"https://docs.google.com/spreadsheets/d/{_SHEET_ID}/export?format=csv&gid={_GID}"
_LINK_BACK = "https://libraryreads.org"
_TIMEOUT = 20.0

_EXPECTED_HEADERS = {
    "Month", "Author (Last, First)", "Title", "Publisher", "ISBN", "Pub Date",
    "Top Pick", "HoF", "Debut", "Bonus Pick", "Book Clubs", "Genre",
    "Annotation", "Nominator/Library",
}


class LibraryReadsSource:

    source = ReleaseSource.LIBRARYREADS.value

    async def fetch(self, month: str | None = None) -> list[EditorialTitle]:
        target = month or _current_month_key()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_CSV_URL)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"LibraryReads fetch failed: {e}")
            return []
        return self._parse_csv(resp.text, month=target)

    def _parse_csv(self, text: str, month: str) -> list[EditorialTitle]:
        reader = csv.DictReader(io.StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = _EXPECTED_HEADERS - headers
        if missing:
            raise ValueError(f"LibraryReads sheet headers changed; missing: {sorted(missing)}")

        titles: list[EditorialTitle] = []
        for row in reader:
            if (row.get("Month") or "").strip() != month:
                continue
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            titles.append(
                EditorialTitle(
                    source=self.source,
                    source_url=_LINK_BACK,
                    title=title,
                    author_name=normalize_author_name(row.get("Author (Last, First)")),
                    isbn_13=clean_isbn13(row.get("ISBN")),
                    release_date=parse_us_date(row.get("Pub Date")),
                    publisher=(row.get("Publisher") or "").strip() or None,
                    blurb=(row.get("Annotation") or "").strip() or None,
                    blurb_credit=(row.get("Nominator/Library") or "").strip() or None,
                    genre=(row.get("Genre") or "").strip() or None,
                    age_rating="adult",
                    is_featured=True,
                )
            )
        return titles


def _current_month_key() -> str:
    from datetime import date

    today = date.today()
    return f"{today.month}/{today.year}"
