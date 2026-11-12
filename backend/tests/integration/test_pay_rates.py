# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The pay-rate surface only deals in clock-capable staff, never patrons."""
from datetime import date
from decimal import Decimal

from app.core.security import hash_password
from app.models.staff_pay_rate import StaffPayRate
from app.models.user import User, UserRole
from app.services.pay_rate_service import PayRateService


def _user(email: str, role: UserRole) -> User:
    return User(
        email=email,
        password_hash=hash_password("ListPassword123!"),
        first_name=role.value.replace("_", " ").title(),
        last_name="Lister",
        role=role,
        is_active=True,
        email_verified=True,
    )


async def test_list_current_only_clock_capable_roles(test_db, test_patron, test_staff, test_admin):
    child = _user("child-rates@example.com", UserRole.CHILD)
    bookmobile = _user("bookmobile-rates@example.com", UserRole.BOOKMOBILE)
    test_db.add_all([child, bookmobile])
    await test_db.commit()

    rows = await PayRateService(test_db).list_current()

    listed = {u.id for u, _ in rows}
    assert {test_staff.id, test_admin.id, bookmobile.id} <= listed
    assert test_patron.id not in listed
    assert child.id not in listed


async def test_active_route_excludes_patrons_keeps_shape(admin_client, test_db, test_staff, test_patron):
    test_db.add(StaffPayRate(
        staff_id=test_staff.id, hourly_rate=Decimal("21.50"), effective_from=date(2026, 1, 1),
    ))
    await test_db.commit()

    resp = await admin_client.get("/api/v1/staff/pay-rates/active")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = [row["staff_id"] for row in body]
    assert test_staff.id in ids
    assert test_patron.id not in ids
    row = next(r for r in body if r["staff_id"] == test_staff.id)
    assert set(row) == {"staff_id", "staff_name", "role", "hourly_rate", "effective_from"}
    assert row["hourly_rate"] == 21.5
    assert row["role"] == "staff"
