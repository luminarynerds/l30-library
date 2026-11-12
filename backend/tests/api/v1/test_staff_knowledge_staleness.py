# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from datetime import datetime, timedelta, timezone
from app.models.knowledge_base import StaffKnowledgeArticle


@pytest.mark.asyncio
async def test_list_articles_exposes_last_verified_at(staff_client, db_session, test_staff):
    art = StaffKnowledgeArticle(
        title="Closing procedures",
        content="Lock all doors and set alarm before leaving.",
        content_type="procedure",
        category="Operations",
        created_by_id=test_staff.id,
        last_verified_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    db_session.add(art)
    await db_session.commit()

    resp = await staff_client.get("/api/v1/staff-knowledge/articles", params={"limit": 50})
    assert resp.status_code == 200
    rows = resp.json()
    row = next((r for r in rows if r["title"] == "Closing procedures"), None)
    assert row is not None, "Article not found in response"
    assert "last_verified_at" in row
    assert row["last_verified_at"] is not None
