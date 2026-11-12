# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, text

from app.models.focus_time import FocusTimeApproval, FocusTimeBlock, FocusTimeStatus, ApprovalStatus
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.services.focus_time_notifications import FocusTimeNotificationService


@pytest.fixture
async def notification_enum_labels(test_db):
    # Test-DB workaround: shift_swap.ShiftSwapNotificationType claims the same PG
    # type name "notificationtype" (create_type=False) and wins the fresh-DB
    # creation race, so the test enum lacks notification.py's labels. Prod's enum
    # is the union of both families, so this aligns the harness with prod.
    for label in ("event_updated", "event_cancelled", "event_reminder", "panic_alert"):
        await test_db.execute(text(f"ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{label}'"))
    await test_db.commit()


@pytest.mark.asyncio
async def test_notify_focus_time_approved_persists_notification(test_db, notification_enum_labels):
    staff = User(
        email="focus.staff@example.com",
        password_hash="x",
        first_name="Focus",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    manager = User(
        email="focus.manager@example.com",
        password_hash="x",
        first_name="Focus",
        last_name="Manager",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add_all([staff, manager])
    await test_db.commit()
    await test_db.refresh(staff)
    await test_db.refresh(manager)

    block = FocusTimeBlock(
        organization_id=1,
        user_id=staff.id,
        work_type="cataloging",
        start_time=datetime.utcnow() + timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=2),
        status=FocusTimeStatus.APPROVED,
    )
    test_db.add(block)
    await test_db.commit()
    await test_db.refresh(block)

    service = FocusTimeNotificationService(test_db)
    await service.notify_focus_time_approved(block, manager)

    result = await test_db.execute(
        select(Notification).where(Notification.user_id == staff.id)
    )
    notification = result.scalars().first()
    assert notification is not None
    assert "Focus Time Approved" in (notification.subject or "")


@pytest.mark.asyncio
async def test_approve_endpoint_creates_notification(test_db, notification_enum_labels):
    """Approving via the router endpoint persists a notification for the staff member."""
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    staff = User(
        email="router.focus.staff@example.com",
        password_hash="x",
        first_name="Router",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    manager = User(
        email="router.focus.manager@example.com",
        password_hash="x",
        first_name="Router",
        last_name="Manager",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add_all([staff, manager])
    await test_db.commit()
    await test_db.refresh(staff)
    await test_db.refresh(manager)

    block = FocusTimeBlock(
        organization_id=1,
        user_id=staff.id,
        work_type="cataloging",
        start_time=datetime.utcnow() + timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=2),
        status=FocusTimeStatus.PENDING_APPROVAL,
        requires_approval=True,
    )
    test_db.add(block)
    await test_db.commit()
    await test_db.refresh(block)

    approval = FocusTimeApproval(
        focus_block_id=block.id,
        status=ApprovalStatus.PENDING,
    )
    test_db.add(approval)
    await test_db.commit()
    await test_db.refresh(approval)

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return manager

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/staff/focus-time/approvals/{approval.id}/approve",
                params={"decision_comment": "Looks good"},
            )
        assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    result = await test_db.execute(
        select(Notification).where(Notification.user_id == staff.id)
    )
    notification = result.scalars().first()
    assert notification is not None
    assert "Focus Time Approved" in (notification.subject or "")
    assert notification.context_data.get("focus_time_notification_type") == "focus_time_approved"
