# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for ban-tracker + acquisition_rationale enrichment.

Task 11 of the L30 Acquisition Rationale plan: the staff ban-reports
endpoints must surface, per row, whether the ban's reason_category was
already documented as an anticipated challenge in the linked catalog
item's acquisition rationale. The frontend uses those three booleans /
slug to render an at-a-glance "defense ready" vs "re-evaluate" badge.

Uses the in-memory staff override pattern (same as Task 10's
``test_challenge_rationale_integration.py``) to sidestep the conftest
``test_staff`` cross-loop flake. The override builds a User instance
purely in Python so ``current_user.role`` never roundtrips DB.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import (
    AcquisitionRationale,
    BehaviorTag,
    SignalType,
    WeedingCondition,
)
from app.models.ban_tracker import BanReport, BanSource, BanType
from app.models.catalog import CatalogItem
from app.models.user import User, UserRole


def _make_in_memory_staff() -> User:
    """Build a User instance that exists only in Python.

    No session binding -> no lazy DB fetch when the route reads .role.
    """
    return User(
        id=999_011,
        email="ban-staff@example.test",
        first_name="Ban",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )


@pytest.fixture
async def staff_overridden_client(client: AsyncClient, test_db: AsyncSession):
    """Wrap the unauthenticated ``client`` fixture with an in-memory staff
    override for ``get_current_user``. Cleaned up after the test.

    Persists a staff user via ``test_db`` so FK constraints elsewhere are
    happy, but hands the route a detached in-memory copy so attribute
    access on .role never crosses event loops.
    """
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    staff = _make_in_memory_staff()
    staff.id = None
    staff.email = f"ban-staff-{uuid.uuid4().hex[:8]}@example.test"
    test_db.add(staff)
    await test_db.commit()
    await test_db.refresh(staff)
    staff_id = staff.id
    staff_role = staff.role

    detached = User(
        id=staff_id,
        email=staff.email,
        first_name=staff.first_name,
        last_name=staff.last_name,
        role=staff_role,
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


async def _seed_tag(test_db: AsyncSession, slug: str = "identity_exploration") -> None:
    """Idempotent seed -- tolerates leftover rows from prior tests."""
    from sqlalchemy import select

    existing = await test_db.execute(
        select(BehaviorTag).where(BehaviorTag.slug == slug)
    )
    if existing.scalar_one_or_none() is not None:
        return
    test_db.add(BehaviorTag(slug=slug, label=slug, category="life_stage"))
    await test_db.flush()


async def _seed_scenario(
    test_db: AsyncSession,
    *,
    anticipated_reasons: list[str] | None = None,
    ban_reason: str = "lgbtq_content",
    with_rationale: bool = True,
    with_catalog_link: bool = True,
) -> BanReport:
    """Seed an item, optional rationale, and a ban_report.

    When ``with_catalog_link`` is False, the ban_report still references
    the seeded catalog_item via FK because the model requires a real
    integer id; instead, we pass ``catalog_match_id=None`` directly on
    the BanReport row to simulate an unmatched report.
    """
    item = CatalogItem(title="Sample Title", author="A", item_type="book")
    test_db.add(item)
    await test_db.flush()
    if with_rationale:
        await _seed_tag(test_db)
        test_db.add(AcquisitionRationale(
            catalog_item_id=item.id,
            signal_type=SignalType.GAP_IN_COLLECTION,
            primary_use_case_slug="identity_exploration",
            weeding_condition=WeedingCondition.SIGNAL_PERSISTENCE,
            anticipated_challenge_reasons=anticipated_reasons or [],
        ))
        await test_db.flush()
    report = BanReport(
        catalog_match_id=item.id if with_catalog_link else None,
        title="Sample Title",
        author="A",
        state="OH",
        ban_type=BanType.BANNED,
        source=BanSource.NEWS,
        reason_category=ban_reason,
    )
    test_db.add(report)
    await test_db.flush()
    return report


@pytest.mark.asyncio
async def test_ban_listing_marks_anticipated_when_reason_matches(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Ban reason that IS in the rationale's anticipated list -> anticipated=True."""
    await _seed_scenario(
        test_db,
        anticipated_reasons=["lgbtq_content"],
        ban_reason="lgbtq_content",
    )
    await test_db.commit()

    resp = await staff_overridden_client.get("/api/v1/ban-tracker/reports")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    items = body["items"]
    matching = next(
        (r for r in items if r.get("reason_category") == "lgbtq_content"),
        None,
    )
    assert matching is not None, f"no matching row in {items!r}"
    assert matching["rationale_present"] is True
    assert matching["rationale_anticipated"] is True
    assert matching["rationale_primary_use_case"] == "identity_exploration"


@pytest.mark.asyncio
async def test_ban_listing_marks_unanticipated_when_reason_not_in_rationale(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Ban reason NOT in the rationale's anticipated list -> anticipated=False."""
    await _seed_scenario(
        test_db,
        anticipated_reasons=["sexual_content"],
        ban_reason="lgbtq_content",
    )
    await test_db.commit()

    resp = await staff_overridden_client.get("/api/v1/ban-tracker/reports")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    matching = next(
        (r for r in items if r.get("reason_category") == "lgbtq_content"),
        None,
    )
    assert matching is not None
    assert matching["rationale_present"] is True
    assert matching["rationale_anticipated"] is False
    assert matching["rationale_primary_use_case"] == "identity_exploration"


@pytest.mark.asyncio
async def test_ban_listing_flags_no_rationale_when_missing(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Catalog match exists but no rationale on file -> all three defaults."""
    await _seed_scenario(
        test_db,
        with_rationale=False,
        ban_reason="violence",
    )
    await test_db.commit()

    resp = await staff_overridden_client.get("/api/v1/ban-tracker/reports")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    matching = next(
        (r for r in items if r.get("reason_category") == "violence"),
        None,
    )
    assert matching is not None
    assert matching["rationale_present"] is False
    assert matching["rationale_anticipated"] is False
    assert matching["rationale_primary_use_case"] is None


@pytest.mark.asyncio
async def test_ban_listing_no_catalog_match_yields_default_rationale_fields(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """No catalog_match_id -> rationale fields stay at their defaults."""
    await _seed_scenario(
        test_db,
        with_catalog_link=False,
        ban_reason="political_viewpoint",
    )
    await test_db.commit()

    resp = await staff_overridden_client.get("/api/v1/ban-tracker/reports")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    matching = next(
        (r for r in items if r.get("reason_category") == "political_viewpoint"),
        None,
    )
    assert matching is not None
    assert matching["catalog_match_id"] is None
    assert matching["rationale_present"] is False
    assert matching["rationale_anticipated"] is False
    assert matching["rationale_primary_use_case"] is None


@pytest.mark.asyncio
async def test_single_ban_report_get_enriched(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """GET /reports/{id} returns the same enrichment as the list."""
    report = await _seed_scenario(
        test_db,
        anticipated_reasons=["lgbtq_content"],
        ban_reason="lgbtq_content",
    )
    await test_db.commit()

    resp = await staff_overridden_client.get(
        f"/api/v1/ban-tracker/reports/{report.id}",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rationale_present"] is True
    assert body["rationale_anticipated"] is True
    assert body["rationale_primary_use_case"] == "identity_exploration"
