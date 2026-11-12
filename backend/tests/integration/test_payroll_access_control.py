# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Payroll routes expose pay PII and must require admin, not plain staff."""
import uuid

import pytest

# Unique email per test: the shared conftest test_staff/test_admin fixtures
# reuse fixed emails, which UniqueViolates across parametrized cases whenever
# the test_db teardown's best-effort cleanup aborts on Postgres.
PASSWORD = "PayrollTest123!"


async def _create_user(test_db, role_name: str):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=f"payroll-{role_name}-{uuid.uuid4().hex[:12]}@example.com",
        password_hash=hash_password(PASSWORD),
        first_name="Payroll",
        last_name=role_name.capitalize(),
        role=UserRole[role_name.upper()],
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _login(client, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
async def admin_token(client, test_db):
    user = await _create_user(test_db, "admin")
    return await _login(client, user.email)


@pytest.fixture
async def staff_token(client, test_db):
    user = await _create_user(test_db, "staff")
    return await _login(client, user.email)


PAYROLL_ROUTES = [
    ("post", "/api/v1/fair-scheduling/payroll/generate"),
    ("post", "/api/v1/fair-scheduling/payroll/export"),
    ("get", "/api/v1/fair-scheduling/payroll/summary"),
    ("post", "/api/v1/fair-scheduling/payroll/approve"),
    ("get", "/api/v1/fair-scheduling/payroll/policy"),
    ("put", "/api/v1/fair-scheduling/payroll/policy"),
]
PARAMS = {"pay_period_start": "2026-06-01", "pay_period_end": "2026-06-14"}


@pytest.mark.parametrize("method,path", PAYROLL_ROUTES)
async def test_staff_token_is_forbidden_from_payroll(client, staff_token, method, path):
    headers = {"Authorization": f"Bearer {staff_token}"}
    resp = await getattr(client, method)(path, params=PARAMS, headers=headers)
    assert resp.status_code == 403, f"{path}: {resp.status_code} {resp.text}"
    # HTTPExceptions are wrapped as {"error": {"code", "message", ...}}.
    assert "admin" in resp.json()["error"]["message"].lower()


@pytest.mark.parametrize("method,path", PAYROLL_ROUTES)
async def test_admin_token_reaches_payroll(client, admin_token, method, path):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await getattr(client, method)(path, params=PARAMS, headers=headers)
    assert resp.status_code not in (401, 403), f"{path}: {resp.status_code} {resp.text}"


# Scheduling profiles hold the OT threshold payroll reads; writes are the
# same pay-manipulation class as the payroll routes above.
PROFILE_BODY = {
    "employment_type": "part_time",
    "contracted_hours_per_week": 20.0,
    "min_hours_per_week": 10.0,
    "max_hours_per_week": 25.0,
}


async def test_staff_token_cannot_write_scheduling_profiles(client, staff_token, test_db):
    target = await _create_user(test_db, "staff")
    headers = {"Authorization": f"Bearer {staff_token}"}

    resp = await client.post(
        "/api/v1/fair-scheduling/profiles",
        json={**PROFILE_BODY, "staff_id": target.id},
        headers=headers,
    )
    assert resp.status_code == 403, f"POST profiles: {resp.status_code} {resp.text}"
    assert "admin" in resp.json()["error"]["message"].lower()

    resp = await client.put(
        f"/api/v1/fair-scheduling/profiles/{target.id}",
        json={"max_hours_per_week": 60.0},
        headers=headers,
    )
    assert resp.status_code == 403, f"PUT profiles: {resp.status_code} {resp.text}"
    assert "admin" in resp.json()["error"]["message"].lower()


async def test_admin_token_can_write_scheduling_profiles_and_staff_can_read(
    client, admin_token, staff_token, test_db
):
    target = await _create_user(test_db, "staff")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.post(
        "/api/v1/fair-scheduling/profiles",
        json={**PROFILE_BODY, "staff_id": target.id},
        headers=admin_headers,
    )
    assert resp.status_code not in (401, 403), f"POST profiles: {resp.status_code} {resp.text}"

    resp = await client.put(
        f"/api/v1/fair-scheduling/profiles/{target.id}",
        json={"max_hours_per_week": 24.0},
        headers=admin_headers,
    )
    assert resp.status_code not in (401, 403), f"PUT profiles: {resp.status_code} {resp.text}"

    # Reads stay staff-accessible (scheduling views consume them).
    resp = await client.get(
        f"/api/v1/fair-scheduling/profiles/{target.id}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code not in (401, 403), f"GET profiles: {resp.status_code} {resp.text}"


# The single payroll_policy row drives generation multipliers, so policy
# writes are the same pay-manipulation class as the payroll routes above.

async def test_admin_get_lazy_creates_default_policy(client, admin_token, test_db):
    from sqlalchemy import delete
    from app.models.fair_scheduling import PayrollPolicy

    await test_db.execute(delete(PayrollPolicy))
    await test_db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/v1/fair-scheduling/payroll/policy", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["overtime_multiplier"] == 1.5
    assert body["holiday_multiplier"] == 2.0
    assert body["weekend_differential"] == 1.1
    assert body["evening_differential"] == 1.15
    assert body["default_ot_threshold_hours"] == 40.0
    assert body["evening_start_local"] == "18:00:00"
    assert body["updated_by_id"] is None


async def test_admin_partial_update_stamps_audit(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.put(
        "/api/v1/fair-scheduling/payroll/policy",
        json={"overtime_multiplier": 1.75},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["overtime_multiplier"] == 1.75
    # Partial update: untouched fields keep their values.
    assert body["holiday_multiplier"] == 2.0
    assert body["updated_by_id"] is not None
    assert body["updated_at"] is not None


@pytest.mark.parametrize("body", [
    {"overtime_multiplier": 0.99},
    {"overtime_multiplier": 3.01},
    {"holiday_multiplier": 5.0},
    {"weekend_differential": 2.5},
    {"evening_differential": 0.5},
    {"default_ot_threshold_hours": 19.9},
    {"default_ot_threshold_hours": 60.1},
    {"evening_start_local": "15:59:00"},
    {"evening_start_local": "22:01:00"},
    {"not_a_policy_field": 1.5},
])
async def test_policy_rejects_out_of_bounds_and_unknown_fields(client, admin_token, body):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.put(
        "/api/v1/fair-scheduling/payroll/policy", json=body, headers=headers,
    )
    assert resp.status_code == 422, f"{body}: {resp.status_code} {resp.text}"
