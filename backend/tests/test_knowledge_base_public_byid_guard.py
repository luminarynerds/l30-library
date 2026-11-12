# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security regression: public KB by-id / mark-helpful must not leak non-public entries.

Bug: GET /api/v1/knowledge/{id} and POST /{id}/helpful selected by id alone, while
the list endpoints filter entry_type to PUBLIC_ENTRY_TYPES. Seeded patron_chat capture
rows (entry_type NULL, review_status 'pending') were therefore fetchable by direct id
on the public, unauthenticated API. Both endpoints now require a public entry_type and
review_status == 'approved'.
"""
from __future__ import annotations

import pytest

from app.models.knowledge_base import KnowledgeEntry


async def _mk(db, *, entry_type, review_status) -> int:
    entry = KnowledgeEntry(
        category="Test",
        title="Test entry",
        content="Body",
        entry_type=entry_type,
        review_status=review_status,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry.id


@pytest.mark.asyncio
async def test_byid_hides_nonpublic_entry_type(public_client, db):
    eid = await _mk(db, entry_type="patron_chat", review_status="pending")
    resp = await public_client.get(f"/api/v1/knowledge/{eid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_byid_hides_pending_public_type(public_client, db):
    eid = await _mk(db, entry_type="faq", review_status="pending")
    resp = await public_client.get(f"/api/v1/knowledge/{eid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_byid_serves_approved_public_entry(public_client, db):
    eid = await _mk(db, entry_type="faq", review_status="approved")
    resp = await public_client.get(f"/api/v1/knowledge/{eid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == eid


@pytest.mark.asyncio
async def test_helpful_hides_nonpublic_entry(public_client, db):
    eid = await _mk(db, entry_type="patron_chat", review_status="pending")
    resp = await public_client.post(f"/api/v1/knowledge/{eid}/helpful")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_helpful_serves_approved_public_entry(public_client, db):
    eid = await _mk(db, entry_type="how-to", review_status="approved")
    resp = await public_client.post(f"/api/v1/knowledge/{eid}/helpful")
    assert resp.status_code == 204
