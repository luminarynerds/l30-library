# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round-trip integration tests for the MARC export writer.

These tests exercise ``MarcBatchService.generate_export`` end-to-end:
create a few ``CatalogItem`` rows, ask the service to emit MARC21 / MARCXML,
parse the bytes back via :mod:`pymarc`, and assert the resulting records
have the structural fields a downstream ILS expects (leader, 008, 245, 040,
852).

This file targets the NEW writer behavior (full leader + 008 + 040 + 852
emission). It is best merged after the writer-swap PR has landed.
"""

import io

import pytest
from pymarc import MARCReader, parse_xml_to_array

from app.models.catalog import CatalogItem, ItemStatus, ItemType
from app.services.marc_batch_service import MarcBatchService


def _result_bytes(result) -> bytes:
    """Pull file_bytes off the new dataclass-style return, with a tuple fallback."""
    file_bytes = getattr(result, "file_bytes", None)
    if file_bytes is None and isinstance(result, tuple):
        file_bytes = result[1]
    assert file_bytes is not None, "generate_export() did not return file bytes"
    return file_bytes


def _result_count(result) -> int | None:
    """Return reported record count if the result exposes one."""
    job = getattr(result, "job", None)
    if job is None and isinstance(result, tuple):
        job = result[0]
    if job is None:
        return None
    return getattr(job, "total_records", None)


async def _seed_items(db_session, test_staff) -> list[CatalogItem]:
    items = [
        CatalogItem(
            title="Round-Trip Export One",
            author="Writer, Alpha",
            isbn="9780000000001",
            publisher="Test Press",
            publication_year=2024,
            item_type=ItemType.book,
            status=ItemStatus.available,
            call_number="813.54 ALP",
            location="Adult Fiction",
        ),
        CatalogItem(
            title="Round-Trip Export Two",
            author="Writer, Beta",
            isbn="9780000000002",
            publisher="Test Press",
            publication_year=2025,
            item_type=ItemType.book,
            status=ItemStatus.available,
            call_number="F BET",
            location="New Books",
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    for item in items:
        await db_session.refresh(item)
    return items


@pytest.mark.integration
class TestMarcExportWriterRoundTrip:
    """Validate that exported MARC bytes parse cleanly and carry required fields."""

    async def test_marc21_round_trip(self, db_session, test_staff):
        items = await _seed_items(db_session, test_staff)

        svc = MarcBatchService(db_session)
        result = await svc.generate_export(
            file_format="marc21",
            user_id=test_staff.id,
        )
        await db_session.commit()

        data = _result_bytes(result)
        assert data, "MARC21 export returned empty bytes"

        reader = MARCReader(io.BytesIO(data), to_unicode=True, force_utf8=True)
        records = [r for r in reader if r is not None]

        assert len(records) >= len(items), (
            f"expected at least {len(items)} MARC records, got {len(records)}"
        )
        reported = _result_count(result)
        if reported is not None:
            assert reported == len(records), (
                f"job.total_records ({reported}) != parsed record count ({len(records)})"
            )

        # Locate our seeded records by ISBN so we are robust to other rows in the DB.
        seeded_isbns = {i.isbn for i in items}
        ours = [
            r for r in records
            if any(str(r.get("020", "")).find(isbn) >= 0 for isbn in seeded_isbns)
        ]
        assert ours, "none of the seeded ISBNs appeared in the export"

        sample = ours[0]
        assert sample.leader is not None
        assert len(str(sample.leader)) == 24, f"leader is {len(str(sample.leader))} chars"
        assert sample.get("008") is not None, "control field 008 missing"
        assert str(sample.get("008")), "control field 008 is empty"
        assert sample.title, "245 $a title is empty"
        assert sample.get_fields("040"), "no 040 cataloging-source field emitted"

        f852s = sample.get_fields("852")
        assert f852s, "no 852 holdings field emitted"
        subs = f852s[0]
        # location subfield $b or $a, call number subfield $h or $j -- accept either.
        assert any(
            subs.get_subfields("a") or subs.get_subfields("b")
        ), "852 has no location subfield"
        assert any(
            subs.get_subfields("h") or subs.get_subfields("j") or subs.get_subfields("k")
        ), "852 has no call-number subfield"

    async def test_marcxml_round_trip(self, db_session, test_staff):
        items = await _seed_items(db_session, test_staff)

        svc = MarcBatchService(db_session)
        result = await svc.generate_export(
            file_format="marcxml",
            user_id=test_staff.id,
        )
        await db_session.commit()

        data = _result_bytes(result)
        assert data, "MARCXML export returned empty bytes"
        assert b"<record" in data, "MARCXML output missing <record> element"

        records = parse_xml_to_array(io.BytesIO(data))
        records = [r for r in records if r is not None]
        assert len(records) >= len(items), (
            f"expected at least {len(items)} MARCXML records, got {len(records)}"
        )

        sample = records[0]
        assert sample.leader is not None
        assert len(str(sample.leader)) == 24
        assert sample.get("008") is not None
        assert sample.title

    async def test_single_record_export(self, db_session, test_staff):
        items = await _seed_items(db_session, test_staff)
        target = items[0]

        svc = MarcBatchService(db_session)
        result = await svc.generate_export(
            file_format="marc21",
            user_id=test_staff.id,
            catalog_item_id=target.id,
        )
        await db_session.commit()

        data = _result_bytes(result)
        reader = MARCReader(io.BytesIO(data), to_unicode=True, force_utf8=True)
        records = [r for r in reader if r is not None]
        assert len(records) == 1, (
            f"single-record export should return exactly 1 record, got {len(records)}"
        )
        assert target.isbn in str(records[0].get("020", "")), (
            "single-record export returned the wrong item"
        )
