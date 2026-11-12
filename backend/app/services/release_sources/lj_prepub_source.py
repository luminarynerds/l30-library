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

# Required columns (order varies month to month; "Series" is optional). Key on names, never positions.
_REQUIRED_HEADERS = {
    "Title", "Author", "EAN", "Publisher Name", "PubDate",
    "List Price", "BISAC Category Description",
}
_TIMEOUT = 20.0


def _sheet_csv_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


class LJPrepubSource:

    source = ReleaseSource.LJ_PREPUB.value

    async def fetch_from_sheet_id(self, sheet_id: str) -> list[EditorialTitle]:
        """Staff supplies the month's Google Sheet id (found while logged into LJ);
        the CSV export itself needs no auth, which keeps L30 from scraping LJ's site."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_sheet_csv_url(sheet_id))
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"LJ Prepub sheet fetch failed for {sheet_id}: {e}")
            return []
        return self._parse_csv(resp.text)

    def _parse_csv(self, text: str) -> list[EditorialTitle]:
        reader = csv.DictReader(io.StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = _REQUIRED_HEADERS - headers
        if missing:
            raise ValueError(f"LJ Prepub sheet headers changed; missing: {sorted(missing)}")

        titles: list[EditorialTitle] = []
        for row in reader:
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            pub_date = parse_us_date(row.get("PubDate"))
            titles.append(
                EditorialTitle(
                    source=self.source,
                    source_url="https://www.libraryjournal.com/section/prepub",
                    title=title,
                    author_name=normalize_author_name(row.get("Author")),
                    isbn_13=clean_isbn13(row.get("EAN")),
                    release_date=pub_date,
                    is_date_exact=pub_date is not None,
                    publisher=(row.get("Publisher Name") or "").strip() or None,
                    genre=(row.get("BISAC Category Description") or "").strip() or None,
                    list_price=_parse_price(row.get("List Price")),
                    age_rating="adult",
                    is_featured=False,
                )
            )
        return titles


def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(str(raw).replace("$", "").strip())
    except ValueError:
        return None
