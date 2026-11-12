# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.catalog import CatalogItem
from ....services.lexile import parse_lexile
from ..dependencies import require_staff

router = APIRouter()


@router.post("/lexile/bulk-import")
async def bulk_import_lexile(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _staff=Depends(require_staff),
) -> dict:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    matched = updated = skipped_invalid = skipped_no_match = 0
    invalid_rows: list[dict] = []
    no_match_rows: list[str] = []

    for row in reader:
        isbn = (row.get("isbn") or "").strip()
        raw_lex = (row.get("lexile") or "").strip()
        if not isbn:
            continue
        try:
            canonical, numeric = parse_lexile(raw_lex)
        except ValueError as e:
            skipped_invalid += 1
            invalid_rows.append({"isbn": isbn, "lexile": raw_lex, "error": str(e)})
            continue

        item = (await db.scalars(select(CatalogItem).where(CatalogItem.isbn == isbn))).first()
        if item is None:
            skipped_no_match += 1
            no_match_rows.append(isbn)
            continue

        matched += 1
        item.lexile_measure = canonical
        item.lexile_number = numeric
        updated += 1

    await db.commit()
    return {
        "matched": matched,
        "updated": updated,
        "skipped_invalid": skipped_invalid,
        "skipped_no_match": skipped_no_match,
        "invalid_rows": invalid_rows[:50],
        "no_match_rows": no_match_rows[:50],
    }
