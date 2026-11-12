# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET /api/v1/computers/lab-map.

The endpoint returns all is_active=True computers (mapped or not), exposing
status and (for in_use stations) the time the station is expected to free
up via the in-session reservation's end time. map_x / map_y are nullable.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.computer import (
    Computer,
    ComputerReservation,
    ComputerReservationStatus,
    ComputerStatus,
    ComputerType,
)


async def _make_mapped_available(test_db, number: str = "LM-A1"):
    c = Computer(
        name=f"LabMap-{number}",
        computer_number=number,
        computer_type=ComputerType.adult,
        status=ComputerStatus.available,
        is_active=True,
        map_x=0.2,
        map_y=0.3,
        map_floor="main",
    )
    test_db.add(c)
    await test_db.flush()
    return c


async def _make_mapped_busy(test_db, *, ends_in_min: int = 20, number: str = "LM-B1"):
    c = Computer(
        name=f"LabMap-{number}",
        computer_number=number,
        computer_type=ComputerType.adult,
        status=ComputerStatus.in_use,
        is_active=True,
        map_x=0.8,
        map_y=0.6,
        map_floor="main",
    )
    test_db.add(c)
    await test_db.flush()
    end = datetime.now(timezone.utc) + timedelta(minutes=ends_in_min)
    r = ComputerReservation(
        computer_id=c.id,
        patron_id=None,
        reserved_start_time=end - timedelta(minutes=40),
        reserved_end_time=end,
        status=ComputerReservationStatus.in_session,
        session_duration_minutes=40,
    )
    test_db.add(r)
    await test_db.flush()
    return c, end


@pytest.mark.asyncio
async def test_lab_map_returns_mapped_stations(client, test_db):
    """Both an available and an in-use mapped station should appear."""
    await _make_mapped_available(test_db)
    await _make_mapped_busy(test_db)
    await test_db.commit()

    resp = await client.get("/api/v1/computers/lab-map")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "stations" in body
    numbers = {s["computer_number"] for s in body["stations"]}
    assert {"LM-A1", "LM-B1"}.issubset(numbers)


@pytest.mark.asyncio
async def test_lab_map_available_at_null_when_available(client, test_db):
    """An available station should report available_at as null."""
    await _make_mapped_available(test_db, number="LM-A2")
    await test_db.commit()

    resp = await client.get("/api/v1/computers/lab-map")
    assert resp.status_code == 200, resp.text
    avail = next(
        s for s in resp.json()["stations"] if s["computer_number"] == "LM-A2"
    )
    assert avail["status"] == "available"
    assert avail["available_at"] is None


@pytest.mark.asyncio
async def test_lab_map_available_at_is_session_end_when_in_use(client, test_db):
    """An in-use station should report available_at equal to the in-session reservation's end (future)."""
    _, end = await _make_mapped_busy(test_db, number="LM-B2")
    await test_db.commit()

    resp = await client.get("/api/v1/computers/lab-map")
    assert resp.status_code == 200, resp.text
    busy = next(
        s for s in resp.json()["stations"] if s["computer_number"] == "LM-B2"
    )
    assert busy["status"] == "in_use"
    assert busy["available_at"] is not None
    parsed = datetime.fromisoformat(busy["available_at"].replace("Z", "+00:00"))
    assert parsed > datetime.now(timezone.utc)
    # Should match the reservation's end time within a small tolerance.
    assert abs((parsed - end).total_seconds()) < 5


@pytest.mark.asyncio
async def test_lab_map_includes_unmapped_active_computers(client, test_db):
    """All is_active=True computers appear regardless of map coords.

    Per the headline-first homepage redesign, the lab-map endpoint must return
    the entire active fleet (not just mapped stations) so the availability
    count is accurate before any station has been placed.
    """
    c = Computer(
        name="LabMap-UnmappedActive",
        computer_number="LM-UA1",
        computer_type=ComputerType.adult,
        status=ComputerStatus.available,
        is_active=True,
        # map_x and map_y left as None deliberately
    )
    test_db.add(c)
    await test_db.commit()

    resp = await client.get("/api/v1/computers/lab-map")
    assert resp.status_code == 200, resp.text
    numbers = {s["computer_number"] for s in resp.json()["stations"]}
    assert "LM-UA1" in numbers


from app.api.v1.auth import get_current_user
from app.main import app


@pytest.mark.asyncio
async def test_admin_patch_sets_map_position(client, test_db, test_admin):
    c = Computer(
        name="LabMap-PatchPos",
        computer_number="LM-PP1",
        computer_type=ComputerType.adult,
        status=ComputerStatus.available,
        is_active=True,
    )
    test_db.add(c)
    await test_db.commit()
    await test_db.refresh(c)

    app.dependency_overrides[get_current_user] = lambda: test_admin
    try:
        resp = await client.patch(
            f"/api/v1/admin/computers/{c.id}",
            json={"map_x": 0.42, "map_y": 0.17, "map_floor": "main"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    await test_db.refresh(c)
    assert c.map_x == pytest.approx(0.42)
    assert c.map_y == pytest.approx(0.17)
    assert c.map_floor == "main"


@pytest.mark.asyncio
async def test_lab_map_available_at_uses_extended_until(client, test_db):
    c, original_end = await _make_mapped_busy(test_db, ends_in_min=5, number="LM-EXT1")
    extended_end = original_end + timedelta(minutes=30)
    # update the existing reservation's extended_until
    from sqlalchemy import select as _sel
    res_row = (await test_db.execute(
        _sel(ComputerReservation).where(ComputerReservation.computer_id == c.id)
    )).scalars().first()
    res_row.extended_until = extended_end
    await test_db.commit()
    resp = await client.get("/api/v1/computers/lab-map")
    station = next(s for s in resp.json()["stations"] if s["computer_number"] == "LM-EXT1")
    parsed = datetime.fromisoformat(station["available_at"].replace("Z", "+00:00"))
    assert abs((parsed - extended_end).total_seconds()) < 5


@pytest.mark.asyncio
async def test_lab_map_includes_maintenance_station(client, test_db):
    c = Computer(
        name="LabMap-Maint", computer_number="LM-M1",
        computer_type=ComputerType.adult, status=ComputerStatus.maintenance,
        is_active=True, map_x=0.5, map_y=0.5, map_floor="main",
    )
    test_db.add(c)
    await test_db.commit()
    resp = await client.get("/api/v1/computers/lab-map")
    m = next(s for s in resp.json()["stations"] if s["computer_number"] == "LM-M1")
    assert m["status"] == "maintenance"
    assert m["available_at"] is None


@pytest.mark.asyncio
async def test_lab_map_coerces_unknown_status_to_offline(client, test_db):
    # The status column is a Postgres enum, but the model declares values_callable
    # over the Python enum, so out-of-band values must go in via raw SQL.
    c = Computer(
        name="LabMap-OOO", computer_number="LM-OOO1",
        computer_type=ComputerType.adult, status=ComputerStatus.maintenance,
        is_active=True, map_x=0.6, map_y=0.6, map_floor="main",
    )
    test_db.add(c)
    await test_db.commit()
    # Inject a non-canonical value at the DB level
    from sqlalchemy import text as _text
    try:
        await test_db.execute(
            _text("UPDATE computers SET status = 'out_of_order' WHERE computer_number = 'LM-OOO1'")
        )
        await test_db.commit()
    except Exception:
        pytest.skip("Postgres enum rejects out-of-band values; coerce is defensive-only")
    resp = await client.get("/api/v1/computers/lab-map")
    found = next((s for s in resp.json()["stations"] if s["computer_number"] == "LM-OOO1"), None)
    assert found is not None
    # Expect the endpoint to have coerced the non-canonical status to 'offline'
    assert found["status"] == "offline"
