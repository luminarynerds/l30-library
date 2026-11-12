# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP-level tests for strategic KPI endpoints."""

import pytest
from datetime import datetime

from app.models.strategic import StrategicPlan


# ============ Fixtures ============


@pytest.fixture
async def _kpi_staff_user(test_db):
    """A dedicated staff user for KPI tests (unique email, no collision risk)."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="kpi_staff_tester@l30.test",
        password_hash=hash_password("password123"),
        first_name="KPI",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def _kpi_admin_user(test_db):
    """A dedicated admin user for KPI tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="kpi_admin_tester@l30.test",
        password_hash=hash_password("password123"),
        first_name="KPI",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def kpi_staff_client(test_db, _kpi_staff_user):
    """Async HTTP client authenticated as a staff user (KPI tests)."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return _kpi_staff_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def kpi_admin_client(test_db, _kpi_admin_user):
    """Async HTTP client authenticated as an admin user (KPI tests)."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return _kpi_admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def test_plan(test_db):
    plan = StrategicPlan(
        title="Test Plan for KPIs",
        description="Plan used by KPI router tests",
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2028, 12, 31),
        status="active",
    )
    test_db.add(plan)
    await test_db.commit()
    await test_db.refresh(plan)
    return plan


# ============ Tests ============


@pytest.mark.asyncio
async def test_create_kpi_201_and_appears_in_list(kpi_staff_client, test_plan):
    """POST creates KPI (201) and GET list returns it."""
    payload = {
        "name": "Monthly Circulation Count",
        "category": "circulation",
        "unit_of_measure": "checkouts",
        "target_value": "1000.00",
        "frequency": "monthly",
    }
    create_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json=payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()
    assert data["name"] == "Monthly Circulation Count"
    assert data["plan_id"] == test_plan.id
    assert data["category"] == "circulation"

    list_resp = await kpi_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis"
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()
    assert any(k["id"] == data["id"] for k in items)


@pytest.mark.asyncio
async def test_create_kpi_missing_plan_404(kpi_staff_client):
    """POST to nonexistent plan returns 404."""
    payload = {"name": "Orphan KPI"}
    resp = await kpi_staff_client.post(
        "/api/v1/strategic/plans/999999/kpis",
        json=payload,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_record_value_updates_current_value_and_creates_kpivalue(kpi_staff_client, test_plan):
    """POST value updates current_value on the KPI and creates a KPIValue row."""
    kpi_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json={"name": "Card Holders", "unit_of_measure": "patrons"},
    )
    assert kpi_resp.status_code == 201
    kpi_id = kpi_resp.json()["id"]

    val_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/kpis/{kpi_id}/values",
        json={"value": "450.00", "notes": "June count"},
    )
    assert val_resp.status_code == 201, val_resp.text
    val_data = val_resp.json()
    assert val_data["kpi_id"] == kpi_id
    assert float(val_data["value"]) == 450.0

    # KPI list should reflect current_value
    list_resp = await kpi_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis"
    )
    kpi = next(k for k in list_resp.json() if k["id"] == kpi_id)
    assert float(kpi["current_value"]) == 450.0


@pytest.mark.asyncio
async def test_record_value_below_threshold_creates_alert(kpi_staff_client, test_plan):
    """Recording a value below threshold_yellow creates a warning/critical alert visible in list."""
    kpi_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json={
            "name": "Program Attendance",
            "unit_of_measure": "attendees",
            "target_value": "100.00",
            "threshold_yellow": "50.00",
            "threshold_red": "20.00",
        },
    )
    assert kpi_resp.status_code == 201
    kpi_id = kpi_resp.json()["id"]

    # Record below threshold_yellow (but above threshold_red -> warning)
    val_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/kpis/{kpi_id}/values",
        json={"value": "30.00"},
    )
    assert val_resp.status_code == 201, val_resp.text

    list_resp = await kpi_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis"
    )
    kpi = next(k for k in list_resp.json() if k["id"] == kpi_id)
    assert len(kpi["alerts"]) >= 1
    severities = {a["severity"] for a in kpi["alerts"]}
    assert severities & {"warning", "critical"}


@pytest.mark.asyncio
async def test_acknowledge_alert_sets_fields(kpi_staff_client, test_plan):
    """POST acknowledge sets acknowledged=True, acknowledged_by_id, acknowledged_at."""
    kpi_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json={
            "name": "Alert Ack KPI",
            "target_value": "100.00",
            "threshold_yellow": "50.00",
        },
    )
    assert kpi_resp.status_code == 201
    kpi_id = kpi_resp.json()["id"]

    # Trigger an alert
    await kpi_staff_client.post(
        f"/api/v1/strategic/kpis/{kpi_id}/values",
        json={"value": "10.00"},
    )

    list_resp = await kpi_staff_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis"
    )
    kpi = next(k for k in list_resp.json() if k["id"] == kpi_id)
    assert len(kpi["alerts"]) >= 1
    alert_id = kpi["alerts"][0]["id"]

    ack_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/kpi-alerts/{alert_id}/acknowledge"
    )
    assert ack_resp.status_code == 200, ack_resp.text
    ack_data = ack_resp.json()
    assert ack_data["acknowledged"] is True
    assert ack_data["acknowledged_at"] is not None
    assert ack_data["acknowledged_by_id"] is not None


@pytest.mark.asyncio
async def test_delete_kpi_staff_forbidden(kpi_staff_client, test_plan):
    """Staff DELETE is forbidden (403)."""
    kpi_resp = await kpi_staff_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json={"name": "Staff Cannot Delete KPI"},
    )
    assert kpi_resp.status_code == 201
    kpi_id = kpi_resp.json()["id"]

    staff_del = await kpi_staff_client.delete(f"/api/v1/strategic/kpis/{kpi_id}")
    assert staff_del.status_code == 403, staff_del.text


@pytest.mark.asyncio
async def test_delete_kpi_admin_204(kpi_admin_client, test_plan):
    """Admin DELETE returns 204 and KPI is gone."""
    kpi_resp = await kpi_admin_client.post(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis",
        json={"name": "Admin Deletes KPI"},
    )
    assert kpi_resp.status_code == 201
    kpi_id = kpi_resp.json()["id"]

    admin_del = await kpi_admin_client.delete(f"/api/v1/strategic/kpis/{kpi_id}")
    assert admin_del.status_code == 204, admin_del.text

    list_resp = await kpi_admin_client.get(
        f"/api/v1/strategic/plans/{test_plan.id}/kpis"
    )
    ids = [k["id"] for k in list_resp.json()]
    assert kpi_id not in ids
