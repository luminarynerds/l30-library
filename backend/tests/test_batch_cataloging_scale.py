# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Batch cataloging workflow tests focused on scale and failure handling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pymarc import Field, MARCWriter, Record, Subfield
from sqlalchemy import delete, func, select

from app.api.v1.catalog.crud import bulk_update_catalog_items
from app.api.v1.catalog.search import export_catalog_marc_batch
from app.models.catalog import CatalogItem, ItemStatus
from app.models.import_job import DuplicateAction, ImportJobType, ImportJobStatus
from app.models.user import User, UserRole
from app.schemas.catalog import BulkUpdateRequest
from app.services.call_number_service import CallNumberService
from app.services.import_service import ImportService



def _build_marc_file(record_count: int) -> bytes:
    """Create MARC21 binary content for a configurable number of records."""
    from io import BytesIO

    stream = BytesIO()
    writer = MARCWriter(stream)

    for idx in range(record_count):
        record = Record(force_utf8=True)
        record.add_field(Field(tag="001", data=f"LSC{idx:06d}"))
        record.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield(code="a", value=f"Scale Test Title {idx}")]))
        record.add_field(Field(tag="100", indicators=["1", " "], subfields=[Subfield(code="a", value=f"Author {idx}")]))
        # A unique ISBN per record so duplicate detection uses the strong-signal
        # ISBN match instead of falling through to fuzzy title/author matching:
        # titles that differ only by a trailing index number ("Scale Test Title
        # 5" vs "...6") score above the fuzzy-match duplicate threshold, which
        # would wrongly treat these 50 distinct records as dupes of the first.
        record.add_field(Field(tag="020", indicators=[" ", " "], subfields=[Subfield(code="a", value=f"97800000{idx:05d}")]))
        record.add_field(Field(tag="650", indicators=[" ", "0"], subfields=[Subfield(code="a", value="Batch Cataloging")]))
        record.add_field(Field(tag="260", indicators=[" ", " "], subfields=[Subfield(code="c", value="2025")]))
        writer.write(record)

    # close_fh=False: MARCWriter.close() closes the underlying file handle by
    # default, which would make the BytesIO unreadable before we can pull the
    # bytes back out of it.
    writer.close(close_fh=False)
    return stream.getvalue()


async def _seed_catalog_items(test_db, total: int = 50) -> list[int]:
    items: list[CatalogItem] = []
    for idx in range(total):
        item = CatalogItem(
            title=f"Catalog Item {idx}",
            author=f"Staff Author {idx}",
            isbn=f"978000{idx:06d}",
            subjects="Old Heading",
            location="Stacks A",
            status=ItemStatus.available,
        )
        test_db.add(item)
        items.append(item)

    await test_db.commit()
    return [item.id for item in items if item.id is not None]


@pytest.mark.asyncio
async def test_batch_import_50_marc_records_progress_and_undo(test_db):
    """Validate 50-record MARC import with progress tracking and rollback."""
    marc_content = _build_marc_file(50)

    job = await ImportService.upload(
        db=test_db,
        file_content=marc_content,
        filename="batch_50_records.mrc",
        job_type=ImportJobType.MARC_RECORDS,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=5.0,
        created_by_id=None,
    )
    job = await ImportService.validate(test_db, job)
    job = await ImportService.execute(test_db, job, batch_size=25)

    assert job.status == ImportJobStatus.COMPLETED
    assert job.created_rows == 50
    assert job.total_rows == 50
    assert job.progress_percent == 100.0

    before_rollback = await test_db.execute(select(func.count(CatalogItem.id)))
    count_before = before_rollback.scalar_one()

    # rollback() returns (job, created_count, updated_count), not a 2-tuple.
    job, created_count, updated_count = await ImportService.rollback(
        test_db, job, reason="Undo test batch operation"
    )
    assert job.status == ImportJobStatus.ROLLED_BACK
    assert created_count == 50
    assert updated_count == 0

    after_rollback = await test_db.execute(select(func.count(CatalogItem.id)))
    count_after = after_rollback.scalar_one()
    assert count_after == count_before - 50


@pytest.mark.asyncio
async def test_bulk_updates_error_handling_and_withdrawn_cleanup(test_db):
    """Exercise batch subject/location/status updates and per-record failure handling."""
    item_ids = await _seed_catalog_items(test_db, total=10)
    mixed_ids = item_ids + [999999]

    bulk_result = await bulk_update_catalog_items(
        request=SimpleNamespace(),
        bulk_request=BulkUpdateRequest(
            item_ids=mixed_ids,
            updates={
                "subjects": "Science fiction--Catalogs",
                "location": "Stacks B",
                "status": ItemStatus.available.value,
            },
        ),
        db=test_db,
        current_user=User(
            email="staff@example.com",
            password_hash="x",
            first_name="Staff",
            last_name="User",
            role=UserRole.STAFF,
        ),
    )

    assert bulk_result.success_count == 10
    assert bulk_result.failure_count == 1
    assert bulk_result.errors[0]["id"] == 999999

    withdrawn_ids = item_ids[:4]
    withdrawn_result = await bulk_update_catalog_items(
        request=SimpleNamespace(),
        bulk_request=BulkUpdateRequest(
            item_ids=withdrawn_ids,
            updates={"status": ItemStatus.withdrawn.value},
        ),
        db=test_db,
        current_user=User(
            email="staff2@example.com",
            password_hash="x",
            first_name="Staff",
            last_name="Two",
            role=UserRole.STAFF,
        ),
    )
    assert withdrawn_result.success_count == 4

    delete_result = await test_db.execute(
        delete(CatalogItem).where(CatalogItem.status == ItemStatus.withdrawn)
    )
    await test_db.commit()
    assert (delete_result.rowcount or 0) == 4


@pytest.mark.asyncio
async def test_batch_genre_gap_export_and_spine_label_generation(test_db):
    """Verify current genre gap while covering batch MARC export and spine label generation."""
    item_ids = await _seed_catalog_items(test_db, total=50)

    with pytest.raises(HTTPException) as exc_info:
        await bulk_update_catalog_items(
            request=SimpleNamespace(),
            bulk_request=BulkUpdateRequest(
                item_ids=item_ids,
                updates={"music_genre": "Ambient"},
            ),
            db=test_db,
            current_user=User(
                email="staff3@example.com",
                password_hash="x",
                first_name="Staff",
                last_name="Three",
                role=UserRole.STAFF,
            ),
        )
    assert exc_info.value.status_code == 400
    assert "Invalid fields for bulk update" in exc_info.value.detail

    export_response = await export_catalog_marc_batch(
        request=SimpleNamespace(),
        format="binary",
        item_type=None,
        status=None,
        location="Stacks A",
        limit=50,
        db=test_db,
        current_user=User(
            email="staff4@example.com",
            password_hash="x",
            first_name="Staff",
            last_name="Four",
            role=UserRole.STAFF,
        ),
    )

    assert export_response.headers["Content-Disposition"].endswith("50-records.mrc")
    # The endpoint streams the export (StreamingResponse) rather than
    # buffering it in a single `.body`, so collect the chunks by hand.
    export_body = b"".join(
        [chunk async for chunk in export_response.body_iterator]
    )
    assert len(export_body) > 0

    labels = [
        CallNumberService.format_manga_spine_label(f"GN SERIES v.{idx}")
        for idx in range(1, 51)
    ]
    assert len(labels) == 50
    assert all(label for label in labels)
