# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test collection_memory_annual endpoint.

Uses the same in-memory User override pattern as
test_challenge_rationale_integration.py to dodge the conftest's
test_staff cross-loop flake. The materialized view aggregates over
ALL rows in acquisition_rationales, so assertions use >= for
seeded counts (other tests may also have seeded rationales).

The conftest builds the test schema with Base.metadata.create_all
(not alembic), so it doesn't know about the matview. We create it
inline here, idempotently, so the test is self-contained.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import (
    AcquisitionRationale,
    BehaviorTag,
    SignalType,
    WeedingCondition,
)
from app.models.catalog import CatalogItem
from app.models.user import User, UserRole


MATVIEW_DDL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS collection_memory_annual AS
SELECT
    date_trunc('year', ar.created_at)::date AS year_acquired,
    ar.primary_use_case_slug,
    ar.weeding_condition,
    COUNT(*) AS item_count,
    COUNT(*) FILTER (
        WHERE array_length(ar.anticipated_challenge_reasons, 1) > 0
    ) AS anticipated_count,
    COUNT(*) FILTER (WHERE ar.patron_visible) AS patron_visible_count
FROM acquisition_rationales ar
GROUP BY 1, 2, 3
WITH NO DATA;
"""


@pytest.fixture
async def ensure_matview(test_db: AsyncSession):
    """Create the matview in the test DB if absent.

    Postgres-only; SQLite fallback skips the matview-backed tests.
    """
    bind = test_db.get_bind()
    if not bind.dialect.name.startswith("postgres"):
        pytest.skip("materialized view is Postgres-only")
    await test_db.execute(text(MATVIEW_DDL))
    await test_db.commit()


def _make_in_memory_staff() -> User:
    return User(
        id=None,
        email=f"in-memory-staff-cm-{uuid.uuid4().hex[:8]}@example.test",
        first_name="In",
        last_name="Memory",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )


@pytest.fixture
async def staff_overridden_client(client: AsyncClient, test_db: AsyncSession):
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    staff = _make_in_memory_staff()
    test_db.add(staff)
    await test_db.commit()
    await test_db.refresh(staff)
    detached = User(
        id=staff.id,
        email=staff.email,
        first_name=staff.first_name,
        last_name=staff.last_name,
        role=staff.role,
        is_active=True,
        email_verified=True,
    )

    async def override_get_current_user():
        return detached

    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def _seed_tag(test_db: AsyncSession, slug: str) -> None:
    from sqlalchemy import select

    existing = await test_db.execute(
        select(BehaviorTag).where(BehaviorTag.slug == slug)
    )
    if existing.scalar_one_or_none() is not None:
        return
    test_db.add(BehaviorTag(slug=slug, label=slug, category="life_stage"))
    await test_db.flush()


async def _seed_item(test_db: AsyncSession, title: str) -> CatalogItem:
    item = CatalogItem(title=title, author="A", item_type="book")
    test_db.add(item)
    await test_db.flush()
    return item


@pytest.mark.asyncio
async def test_collection_memory_returns_aggregated_rows(
    ensure_matview,
    test_db: AsyncSession,
    staff_overridden_client: AsyncClient,
):
    await _seed_tag(test_db, "new_parent")

    items = []
    for i in range(3):
        items.append(await _seed_item(test_db, f"CMTest-{uuid.uuid4().hex[:6]}-{i}"))

    weedings = [
        WeedingCondition.CURRENT_5YR,
        WeedingCondition.CURRENT_5YR,
        WeedingCondition.FOUNDATIONAL_INDEFINITE,
    ]
    for it, weeding in zip(items, weedings):
        test_db.add(AcquisitionRationale(
            catalog_item_id=it.id,
            signal_type=SignalType.GAP_IN_COLLECTION,
            primary_use_case_slug="new_parent",
            weeding_condition=weeding,
        ))
    await test_db.commit()

    resp = await staff_overridden_client.get(
        "/api/v1/staff/collection-memory/annual"
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["rows"]


    # Note: prod DB stores enum lowercase (current_5yr); the test DB schema is
    # built via Base.metadata.create_all which writes uppercase Python names.
    # The endpoint is identical in both, so we compare case-insensitively.
    cur5 = [
        r for r in rows
        if r["primary_use_case_slug"] == "new_parent"
        and r["weeding_condition"].lower() == "current_5yr"
    ]
    fnd = [
        r for r in rows
        if r["primary_use_case_slug"] == "new_parent"
        and r["weeding_condition"].lower() == "foundational_indefinite"
    ]
    assert any(r["item_count"] >= 2 for r in cur5), \
        f"expected at least one current_5yr row with item_count>=2, got {cur5}"
    assert any(r["item_count"] >= 1 for r in fnd), \
        f"expected at least one foundational_indefinite row with item_count>=1, got {fnd}"


@pytest.mark.asyncio
async def test_collection_memory_requires_staff(client: AsyncClient):
    resp = await client.get("/api/v1/staff/collection-memory/annual")
    assert resp.status_code in (401, 403), resp.text
