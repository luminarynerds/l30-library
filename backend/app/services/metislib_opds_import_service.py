# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Import MetisLib's indie OPDS feed into L30-owned `indie_ebooks` rows.

Phase 1 of the indie-OPDS ownership migration: walk every feed page, upsert an
owned row per title (deduped by `metislib_ebook_id`), copy the EPUB bytes into
local storage, and pull `content_warnings` once. Idempotent and re-runnable.
No patron-facing surface reads these columns yet (that is Phase 2).
"""
import json
from pathlib import Path

from app.clients.metislib_opds_client import IndieFeedEntry, MetisLibOpdsClient, MetisLibOpdsClientError
from app.core.config import get_settings
from app.core.datetime_utils import utc_now
from app.core.logging import get_logger
from app.models.indie_ebook_borrow import IndieEbook
from app.services.metislib_client import get_metislib_client
from sqlalchemy import select

logger = get_logger(__name__)

_DEFAULT_COPIES = 5


class MetisLibOpdsImportError(Exception):
    pass


class MetisLibOpdsImporter:
    def __init__(self, db):
        self.db = db
        self.client = MetisLibOpdsClient()
        self._storage_dir = Path(get_settings().indie_ebook_storage_path)

    async def import_all(self) -> dict:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        stats = {"created": 0, "updated": 0, "files": 0, "errors": 0}
        page = 1
        first_page = True
        while True:
            entries, next_href = await self.client.fetch_indie_feed(page=page)
            if first_page and not entries:
                raise MetisLibOpdsImportError(
                    "indie OPDS feed returned no entries — feed may be empty or unreachable"
                )
            first_page = False
            for entry in entries:
                try:
                    await self._upsert(entry, stats)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"indie import {entry.metislib_ebook_id} failed: {exc}")
                    stats["errors"] += 1
            if not next_href:
                break
            page += 1
        await self.db.commit()
        return stats

    async def _upsert(self, entry: IndieFeedEntry, stats: dict) -> None:
        row = (
            await self.db.execute(
                select(IndieEbook).where(
                    IndieEbook.metislib_ebook_id == entry.metislib_ebook_id
                )
            )
        ).scalar_one_or_none()

        is_new = row is None
        if is_new:
            row = IndieEbook(metislib_ebook_id=entry.metislib_ebook_id)
            stats["created"] += 1
        else:
            stats["updated"] += 1

        if is_new or not row.copies_owned:
            copies_owned = entry.copies_total if entry.copies_total is not None else _DEFAULT_COPIES
            row.copies_owned = copies_owned
            row.copies_available = (
                entry.copies_available if entry.copies_available is not None else copies_owned
            )

        row.title = entry.title
        row.author_pen_name = entry.author_pen_name
        row.description = entry.description
        row.cover_url = entry.cover_url
        row.genre = entry.genre
        row.language = entry.language
        row.publication_year = entry.publication_year
        row.file_format = "epub"
        row.source_updated_at = entry.source_updated_at
        row.imported_at = utc_now()

        self.db.add(row)
        await self.db.flush()

        detail = await self._fetch_detail(entry.metislib_ebook_id)
        row.content_warnings = json.dumps(detail.get("content_warnings") or [])
        row.subjects = json.dumps(detail.get("subjects") or [])
        row.content_rating = detail.get("content_rating")
        row.word_count = detail.get("word_count")
        row.page_count = detail.get("page_count") or detail.get("page_count_estimate")
        row.isbn = detail.get("isbn")
        row.author_id = detail.get("author_id")

        dest = self._storage_dir / f"{entry.metislib_ebook_id}.epub"
        needs_fetch = not dest.exists() or dest.stat().st_size == 0
        if needs_fetch:
            try:
                epub_bytes = await self.client.fetch_ebook_bytes(entry.metislib_ebook_id)
            except MetisLibOpdsClientError as exc:
                logger.error(
                    f"EPUB fetch failed for {entry.metislib_ebook_id}: {exc.message}; "
                    "metadata row kept, file_path left NULL"
                )
                stats["errors"] += 1
                return
            if epub_bytes and epub_bytes[:2] == b"PK":
                dest.write_bytes(epub_bytes)
                row.file_path = str(dest)
                stats["files"] += 1
            else:
                logger.error(
                    f"EPUB for {entry.metislib_ebook_id} failed zip-magic check "
                    f"(got {epub_bytes[:4]!r}); skipping file write"
                )
                stats["errors"] += 1
        else:
            row.file_path = str(dest)

    async def _fetch_detail(self, metislib_ebook_id: int) -> dict:
        """Fetch the MetisLib detail dict once (content_warnings + static gap
        fields). Best-effort: any failure returns {} and never blocks import."""
        try:
            data = await get_metislib_client().get_ebook(
                metislib_ebook_id, entry_type="indie_ebook"
            )
            return data if isinstance(data, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"detail fetch failed for {metislib_ebook_id}: {exc}"
            )
            return {}
