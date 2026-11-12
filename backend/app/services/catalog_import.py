# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import contextlib
import csv
import io
from app.core.logging import get_logger
import uuid
from pathlib import Path

import pymarc
from sqlalchemy import select

from ..api.v1.catalog.import_schemas import ImportPreviewRecord, ImportResult
from ..models.subject import CatalogItemSubject, Subject
from .catalog_subjects import parse_subjects_field

_MAX_MARCXML_BYTES = 25 * 1024 * 1024


def _reject_xml_bombs(content: bytes) -> None:
    """Reject oversized or DTD/entity-bearing MARCXML.

    MARCXML has no legitimate DTD or entity declarations, so their presence
    signals an XXE or entity-expansion (billion-laughs) attack. Size is also
    capped to bound expansion blast radius.
    """
    if len(content) > _MAX_MARCXML_BYTES:
        raise ValueError("MARCXML input exceeds the size limit")
    if b"<!DOCTYPE" in content or b"<!ENTITY" in content:
        raise ValueError("MARCXML with DTD or entity declarations is not allowed")

logger = get_logger(__name__)

IMPORT_DIR = Path("/app/media/imports")

# MARC leader position 6 -> ItemType value
_MARC_TYPE_MAP = {
    "a": "book",
    "g": "dvd",
    "i": "audiobook",
    "j": "cd",
}


def save_upload(content: bytes, filename: str) -> str:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower().lstrip(".")
    upload_id = str(uuid.uuid4())
    dest = IMPORT_DIR / f"{upload_id}.{ext}"
    dest.write_bytes(content)
    return upload_id


def detect_format(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".mrc":
        return "marc21"
    if ext == ".xml":
        return "marcxml"
    if ext == ".csv":
        return "csv"
    raise ValueError(f"Unsupported file extension: {ext}")


def _clean_title(title: str | None) -> str:
    if not title:
        return ""
    return title.rstrip(" /").strip()


def _marc_item_type(record: pymarc.Record) -> str | None:
    try:
        leader_06 = record.leader[6]
        return _MARC_TYPE_MAP.get(leader_06)
    except (IndexError, TypeError):
        return None


def _marc_year(record: pymarc.Record) -> str | None:
    try:
        field_008 = record["008"]
        if field_008 and field_008.data and len(field_008.data) >= 11:
            year = field_008.data[7:11].strip()
            if year.isdigit():
                return year
    except (KeyError, AttributeError):
        pass
    return None


def _record_to_preview(record: pymarc.Record) -> ImportPreviewRecord:
    return ImportPreviewRecord(
        title=_clean_title(record.title),
        author=record.author,
        isbn=record.isbn(),
        item_type=_marc_item_type(record),
        year=_marc_year(record),
    )


def parse_marc21_preview(content: bytes, limit: int = 20) -> tuple[int, list[ImportPreviewRecord]]:
    # Honor MARC leader byte 9 for character encoding (UTF-8 vs MARC-8).
    # See marc_batch_service.execute_import for the full rationale.
    reader = pymarc.MARCReader(io.BytesIO(content), to_unicode=True)
    records = []
    total = 0
    for record in reader:
        if record is None:
            continue
        total += 1
        if len(records) < limit:
            records.append(_record_to_preview(record))
    return total, records


def parse_marcxml_preview(content: bytes, limit: int = 20) -> tuple[int, list[ImportPreviewRecord]]:
    _reject_xml_bombs(content)
    all_records = pymarc.parse_xml_to_array(io.BytesIO(content))
    total = len(all_records)
    preview = [_record_to_preview(r) for r in all_records[:limit]]
    return total, preview


def parse_csv_preview(
    content: bytes, limit: int = 20
) -> tuple[int, list[ImportPreviewRecord], list[str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = list(reader)
    total = len(rows)
    preview = []
    for row in rows[:limit]:
        preview.append(
            ImportPreviewRecord(
                title=row.get("title", "") or "",
                author=row.get("author") or None,
                isbn=row.get("isbn") or None,
                item_type=row.get("item_type") or None,
                year=row.get("year") or None,
            )
        )
    return total, preview, list(headers)


def _find_upload_file(upload_id: str) -> Path | None:
    if not IMPORT_DIR.exists():
        return None
    for path in IMPORT_DIR.iterdir():
        if path.stem == upload_id:
            return path
    return None


async def _attach_subjects(db, item, subjects_raw: str | None) -> None:
    labels = parse_subjects_field(subjects_raw)
    if not labels:
        return
    for position, label in enumerate(labels):
        existing = await db.execute(select(Subject).where(Subject.label == label))
        subject = existing.scalar_one_or_none()
        if subject is None:
            subject = Subject(label=label, slug=label.lower().strip())
            db.add(subject)
            await db.flush()
        link_exists = await db.execute(
            select(CatalogItemSubject).where(
                CatalogItemSubject.catalog_item_id == item.id,
                CatalogItemSubject.subject_id == subject.id,
            )
        )
        if link_exists.scalar_one_or_none() is None:
            db.add(CatalogItemSubject(
                catalog_item_id=item.id,
                subject_id=subject.id,
                position=position,
            ))


async def run_import(
    upload_id: str,
    fmt: str,
    field_mapping,
    skip_invalid: bool,
    db,
) -> ImportResult:
    from ..models.catalog import CatalogItem, ItemStatus, ItemType

    path = _find_upload_file(upload_id)
    if not path:
        raise FileNotFoundError(f"Upload not found: {upload_id}")

    content = path.read_bytes()

    if fmt == "marc21":
        _total, preview_records = parse_marc21_preview(content, limit=10**9)
        raw_records = _marc21_to_dicts(content)
    elif fmt == "marcxml":
        raw_records = _marcxml_to_dicts(content)
    else:
        raw_records = _csv_to_dicts(content, field_mapping)

    imported = 0
    skipped = 0
    duplicates_merged = 0
    errors: list[str] = []

    from sqlalchemy import select

    items_to_add: list[CatalogItem] = []

    for i, rec in enumerate(raw_records):
        try:
            title = rec.get("title", "").strip()
            if not title:
                if skip_invalid:
                    skipped += 1
                    continue
                errors.append(f"Record {i}: missing title")
                skipped += 1
                continue

            isbn = rec.get("isbn") or None
            if isbn:
                isbn = isbn.strip() or None

            # Duplicate check by ISBN
            if isbn:
                result = await db.execute(
                    select(CatalogItem).where(CatalogItem.isbn == isbn).limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    duplicates_merged += 1
                    continue

            raw_type = rec.get("item_type") or "book"
            try:
                item_type = ItemType(raw_type.lower())
            except ValueError:
                item_type = ItemType.book

            raw_year = rec.get("year") or None
            pub_year: int | None = None
            if raw_year:
                with contextlib.suppress(ValueError):
                    pub_year = int(raw_year)

            new_item = CatalogItem(
                title=title[:500],
                author=(rec.get("author") or None),
                isbn=isbn,
                item_type=item_type,
                status=ItemStatus.available,
                publication_year=pub_year,
                publisher=(rec.get("publisher") or None),
                description=(rec.get("description") or None),
                subjects=(rec.get("subjects") or None),
            )
            # Stash the raw subjects string on a transient attribute so the
            # post-commit normalization loop can parse it without re-walking
            # raw_records (which is offset by skipped rows + ISBN dedup hits).
            new_item._subjects_raw_for_import = rec.get("subjects")  # type: ignore[attr-defined]
            items_to_add.append(new_item)
            imported += 1
        except Exception as exc:
            if skip_invalid:
                skipped += 1
                errors.append(f"Record {i}: {exc}")
            else:
                raise

    if items_to_add:
        db.add_all(items_to_add)
        await db.commit()

        # Normalize subjects into Subject / CatalogItemSubject. The legacy
        # text column items_to_add[*].subjects is preserved for back-compat;
        # read paths increasingly use the join table. parse_subjects_field
        # handles the three production shapes (comma, semicolon, array literal).
        for item in items_to_add:
            await _attach_subjects(
                db, item, getattr(item, "_subjects_raw_for_import", None),
            )
        await db.commit()

        # Sync each newly-imported catalog row into the BIBFRAME graph.
        # Bulk import previously committed without this call, leaving
        # rich-MARC ingests invisible to the linked-data layer. Per-item
        # failures are logged and skipped so a single bad row doesn't
        # break the import; the catalog row still landed.
        from .catalog_bibframe_sync import CatalogBibframeSync
        for item in items_to_add:
            try:
                await CatalogBibframeSync.create_from_catalog(db, item)
            except Exception as exc:  # noqa: BLE001 -- per-item boundary: one BIBFRAME sync failure must not block bulk catalog import
                import logging
                get_logger(__name__).warning(
                    "BIBFRAME sync failed for imported catalog_item %s: %s",
                    item.id, exc, exc_info=True,
                )
        await db.commit()

    return ImportResult(
        imported=imported,
        skipped=skipped,
        duplicates_merged=duplicates_merged,
        errors=errors,
    )


def _marc21_to_dicts(content: bytes) -> list[dict]:
    # Honor MARC leader byte 9 for character encoding (UTF-8 vs MARC-8).
    reader = pymarc.MARCReader(io.BytesIO(content), to_unicode=True)
    out = []
    for record in reader:
        if record is None:
            continue
        out.append({
            "title": _clean_title(record.title),
            "author": record.author,
            "isbn": record.isbn(),
            "item_type": _marc_item_type(record),
            "year": _marc_year(record),
        })
    return out


def _marcxml_to_dicts(content: bytes) -> list[dict]:
    _reject_xml_bombs(content)
    records = pymarc.parse_xml_to_array(io.BytesIO(content))
    return [
        {
            "title": _clean_title(r.title),
            "author": r.author,
            "isbn": r.isbn(),
            "item_type": _marc_item_type(r),
            "year": _marc_year(r),
        }
        for r in records
    ]


def _csv_to_dicts(content: bytes, field_mapping) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        if field_mapping:
            mapped: dict = {}
            for field, col in field_mapping.model_dump(exclude_none=True).items():
                mapped[field] = row.get(col, "")
            out.append(mapped)
        else:
            out.append(dict(row))
    return out
