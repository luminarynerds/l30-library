# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET /api/v1/tech-support/facilities.

The facilities endpoint backs the Tech Support page's Computer Lab + printer
facts, which previously lived as hardcoded JSX literals. Covers:
- Seeded rows return grouped by kind.
- is_active=False rows are excluded.
- Rows are ordered by sort_order within a group.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tech_support import TechFacility, TechFacilityKind

pytestmark = pytest.mark.asyncio

FACILITIES_URL = "/api/v1/tech-support/facilities"


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Dispose the shared L30 test engine pool between tests.

    Same workaround as test_book_challenges_public.py — the pool keeps
    connections alive across event loops, so each test must reset it.
    """
    yield
    import tests.conftest as tc
    if tc._engine is not None:
        try:
            await tc._engine.dispose()
        except Exception:
            pass
        tc._engine = None
        tc._session_factory = None


async def _seed(test_db: AsyncSession, facilities):
    for f in facilities:
        test_db.add(f)
    await test_db.commit()


async def test_facilities_returns_seeded_rows_grouped_by_kind(
    client: AsyncClient, test_db: AsyncSession
):
    """Active rows are returned grouped under their kind."""
    await _seed(test_db, [
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="Computers available", value="12", sort_order=1),
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="WiFi", value="Free throughout building", sort_order=2),
        TechFacility(kind=TechFacilityKind.printer,
                     label="Second Floor Reference Area",
                     value="B&W printing only.", sort_order=1),
    ])

    resp = await client.get(FACILITIES_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    by_kind = {section["kind"]: section for section in data}
    assert set(by_kind) == {"computer_lab", "printer"}

    lab = by_kind["computer_lab"]["facilities"]
    assert [f["label"] for f in lab] == ["Computers available", "WiFi"]
    assert lab[0]["value"] == "12"
    assert "id" in lab[0]

    printer = by_kind["printer"]["facilities"]
    assert len(printer) == 1
    assert printer[0]["label"] == "Second Floor Reference Area"


async def test_facilities_excludes_inactive_rows(
    client: AsyncClient, test_db: AsyncSession
):
    """Rows with is_active=False are filtered out."""
    await _seed(test_db, [
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="Visible stat", value="12", sort_order=1,
                     is_active=True),
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="Retired stat", value="old", sort_order=2,
                     is_active=False),
    ])

    resp = await client.get(FACILITIES_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    labels = [f["label"] for s in data for f in s["facilities"]]
    assert "Visible stat" in labels
    assert "Retired stat" not in labels


async def test_facilities_ordered_by_sort_order(
    client: AsyncClient, test_db: AsyncSession
):
    """Facilities within a kind are ordered by sort_order ascending."""
    await _seed(test_db, [
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="Third", value="c", sort_order=30),
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="First", value="a", sort_order=10),
        TechFacility(kind=TechFacilityKind.computer_lab,
                     label="Second", value="b", sort_order=20),
    ])

    resp = await client.get(FACILITIES_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    lab = next(s for s in data if s["kind"] == "computer_lab")["facilities"]
    assert [f["label"] for f in lab] == ["First", "Second", "Third"]


async def test_facilities_empty_when_no_rows(
    client: AsyncClient, test_db: AsyncSession
):
    """No seeded rows → empty list, not an error."""
    resp = await client.get(FACILITIES_URL)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
