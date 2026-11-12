# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for SyntheticGenerationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source_entry(**kwargs):
    entry = MagicMock()
    entry.id = kwargs.get("id", 1)
    entry.title = kwargs.get("title", "Source entry")
    entry.content = kwargs.get("content", "Library hours are Mon-Fri 9am-8pm.")
    entry.persona_domain = kwargs.get("persona_domain", "public")
    entry.source_type = kwargs.get("source_type", "manual")
    entry.review_status = kwargs.get("review_status", "approved")
    return entry


def _make_db(scalar_side_effect=None):
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    if scalar_side_effect is not None:
        db.scalar = AsyncMock(side_effect=scalar_side_effect)
    else:
        db.scalar = AsyncMock(return_value=0)
    return db


def _make_service():
    from app.services.synthetic_generation_service import SyntheticGenerationService
    svc = SyntheticGenerationService()
    svc.qa_service = MagicMock()
    svc.qa_service.extract_from_text = AsyncMock(return_value=[])
    svc.pipeline = MagicMock()
    svc.pipeline.generate_and_store_embedding = AsyncMock(return_value=None)
    svc.pipeline.create_version = AsyncMock(return_value=MagicMock())
    return svc


# ---------------------------------------------------------------------------
# review_status is always pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthetic_entry_always_pending():
    svc = _make_service()
    qa_pairs = [{"question": "What are the hours", "answer": "Mon-Fri 9am-8pm."}]
    svc.qa_service.extract_from_text = AsyncMock(return_value=qa_pairs)

    db = _make_db(scalar_side_effect=[10, 3])

    captured = {}

    def _add(obj):
        obj.id = 99
        captured["entry"] = obj

    db.add.side_effect = _add

    source = _make_source_entry(persona_domain="public")
    entries = await svc.generate_from_entry(db, source)

    assert len(entries) == 1
    assert captured["entry"].review_status == "pending"


# ---------------------------------------------------------------------------
# source_type is always synthetic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthetic_entry_always_source_type_synthetic():
    svc = _make_service()
    qa_pairs = [{"question": "Can I renew online", "answer": "Yes, via the portal."}]
    svc.qa_service.extract_from_text = AsyncMock(return_value=qa_pairs)

    db = _make_db(scalar_side_effect=[10, 2])

    captured = {}

    def _add(obj):
        obj.id = 50
        captured["entry"] = obj

    db.add.side_effect = _add

    source = _make_source_entry(persona_domain="public")
    await svc.generate_from_entry(db, source)

    assert captured["entry"].source_type == "synthetic"


# ---------------------------------------------------------------------------
# Ratio check blocks at/above 40%
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_ratio_blocks_at_40_percent():
    svc = _make_service()

    # total=10, synthetic=4 => 4/10 = 0.40 => NOT < 0.4 => blocked
    db = _make_db(scalar_side_effect=[10, 4])

    result = await svc._check_ratio(db, "public")
    assert result is False


@pytest.mark.asyncio
async def test_check_ratio_blocks_above_40_percent():
    svc = _make_service()

    db = _make_db(scalar_side_effect=[10, 5])

    result = await svc._check_ratio(db, "public")
    assert result is False


# ---------------------------------------------------------------------------
# Ratio check allows below 40%
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_ratio_allows_below_40_percent():
    svc = _make_service()

    db = _make_db(scalar_side_effect=[10, 3])

    result = await svc._check_ratio(db, "public")
    assert result is True


@pytest.mark.asyncio
async def test_check_ratio_allows_when_no_approved_entries():
    svc = _make_service()

    db = _make_db(scalar_side_effect=[0, 0])

    result = await svc._check_ratio(db, "public")
    assert result is True


# ---------------------------------------------------------------------------
# generate_from_entry calls QA extraction and stores results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_from_entry_calls_qa_extraction():
    svc = _make_service()
    qa_pairs = [
        {"question": "Do you have 3D printers", "answer": "Yes, on the 2nd floor."},
        {"question": "How do I book one", "answer": "Book at the front desk."},
    ]
    svc.qa_service.extract_from_text = AsyncMock(return_value=qa_pairs)

    added = []
    db = _make_db(scalar_side_effect=[10, 2])

    def _add(obj):
        obj.id = len(added) + 1
        added.append(obj)

    db.add.side_effect = _add

    source = _make_source_entry(content="We have 3D printers on the 2nd floor.", persona_domain="public")
    entries = await svc.generate_from_entry(db, source)

    svc.qa_service.extract_from_text.assert_awaited_once_with(source.content)
    assert len(entries) == 2
    assert svc.pipeline.generate_and_store_embedding.await_count == 2
    assert svc.pipeline.create_version.await_count == 2
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_from_entry_returns_empty_when_ratio_exceeded():
    svc = _make_service()

    # total=10, synthetic=4 => exactly 40% => blocked
    db = _make_db(scalar_side_effect=[10, 4])

    source = _make_source_entry(persona_domain="public")
    entries = await svc.generate_from_entry(db, source)

    assert entries == []
    svc.qa_service.extract_from_text.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_from_entry_uses_shared_domain_when_none():
    svc = _make_service()
    svc.qa_service.extract_from_text = AsyncMock(return_value=[])

    db = _make_db(scalar_side_effect=[0, 0])

    source = _make_source_entry(persona_domain=None)
    await svc.generate_from_entry(db, source)

    db.scalar.assert_awaited()


# ---------------------------------------------------------------------------
# generate_batch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_batch_filters_approved_non_synthetic():
    svc = _make_service()
    svc.generate_from_entry = AsyncMock(return_value=[])

    source_entries = [_make_source_entry(id=i) for i in range(3)]
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = source_entries

    db = _make_db()
    db.execute = AsyncMock(return_value=execute_result)

    await svc.generate_batch(db, persona_domain="public", limit=10)

    db.execute.assert_awaited_once()
    assert svc.generate_from_entry.await_count == 3


@pytest.mark.asyncio
async def test_generate_batch_returns_all_generated_entries():
    svc = _make_service()

    fake_entries = [MagicMock(), MagicMock()]
    svc.generate_from_entry = AsyncMock(return_value=fake_entries)

    source_entries = [_make_source_entry(id=1), _make_source_entry(id=2)]
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = source_entries

    db = _make_db()
    db.execute = AsyncMock(return_value=execute_result)

    result = await svc.generate_batch(db)

    assert len(result) == 4  # 2 sources * 2 entries each
