# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""GET /staff/presence/me must not persist a phantom AVAILABLE row."""
from sqlalchemy import select

from app.models.staff_presence import StaffPresence


async def test_get_presence_does_not_create_row(staff_client, test_db, test_staff):
    resp = await staff_client.get("/api/v1/staff/presence/me")
    assert resp.status_code == 200
    # A staffer who has not clocked in reads as off_duty...
    assert resp.json()["status"] == "off_duty"
    # ...and no presence row was written by the read.
    rows = (await test_db.execute(
        select(StaffPresence).where(StaffPresence.staff_id == test_staff.id)
    )).scalars().all()
    assert rows == [], "GET /me must not persist a presence row"
