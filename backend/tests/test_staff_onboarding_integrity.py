# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for staff-onboarding integrity fixes.

Bug: `PATCH /onboarding/{id}` would update fields (including `status`) without
recalculating `progress_percentage`. A row could be left as
`status=completed` with `progress_percentage=0`, breaking any reporting or
dashboard that joins on those columns.

Fix: the PATCH handler now invokes `StaffOnboardingService.update_progress`
after applying field updates. This test asserts the post-fix invariant by
constructing a half-finished onboarding, marking only the row status as
`completed` via the service path that mirrors the PATCH semantics, and
confirming the percentage was recalculated from the actual checklist
completion state.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import delete, select

from app.models.onboarding import (
    CheckInMeeting,
    OnboardingChecklistItemStatus,
    PreArrivalChecklistItem,
    StaffOnboarding,
)
from app.services.onboarding_service import (
    PreArrivalChecklistService,
    StaffOnboardingService,
)


@pytest.fixture
async def admin_client(test_db, test_admin):
    """Async HTTP client authenticated as an admin user.

    PATCH /api/v1/onboarding/{id} is gated to admin/director/super_admin
    (app/api/v1/onboarding.py: require_role(ADMIN, DIRECTOR, SUPER_ADMIN) --
    "Matches StaffOnboardingPage's MANAGER_ROLES gate"), so the plain
    conftest.py `staff_client` (role=STAFF) can never call it. Mirrors
    staff_client's own pattern, just with an admin-role user.
    """
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_admin

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


@pytest.mark.asyncio
async def test_patch_recalculates_progress_when_status_changes(
    admin_client, db_session, test_staff
):
    """PATCH /onboarding/{id} must recalculate progress; revert fails red."""
    onboarding = await StaffOnboardingService.create_onboarding(
        db=db_session,
        user_id=test_staff.id,
        department="Circulation",
        position="Asst",
        start_date=date.today(),
        expected_completion_date=date.today() + timedelta(days=90),
    )

    # Seed 5 pre-arrival items and complete ALL of them. Real progress
    # should be 100%. NOTE: we deliberately use 0% and 100% endpoints
    # because PR #1030 ships an independent fix to update_progress's
    # integer-divide ordering -- using mid-range ratios here would
    # cross-couple this regression test to that PR's merge order.
    # 100% vs 0% is unaffected by the divide-order bug.
    for i in range(5):
        await PreArrivalChecklistService.create_item(
            db=db_session,
            onboarding_id=onboarding.id,
            title=f"Task {i}",
            category="paperwork",
        )

    # Drop auto-seeded check-in meetings so the bucket count is exactly
    # the 5 pre-arrival items.
    await db_session.execute(
        delete(CheckInMeeting).where(CheckInMeeting.onboarding_id == onboarding.id)
    )
    await db_session.commit()

    items = (
        await db_session.execute(
            select(PreArrivalChecklistItem)
            .where(PreArrivalChecklistItem.onboarding_id == onboarding.id)
            .order_by(PreArrivalChecklistItem.id)
        )
    ).scalars().all()
    for item in items:
        item.status = OnboardingChecklistItemStatus.completed
    # Stamp a stale percentage so a PATCH that fails to recalculate
    # is observable: pre-fix code commits the field changes and walks
    # away, leaving this 0 in place.
    onboarding_row = await StaffOnboardingService.get_onboarding(
        db_session, onboarding.id
    )
    onboarding_row.progress_percentage = 0
    await db_session.commit()

    # Hit the real PATCH endpoint with only a status field.
    response = await admin_client.patch(
        f"/api/v1/onboarding/{onboarding.id}",
        json={"status": "completed"},
    )
    assert response.status_code == 200, response.text

    reloaded = (
        await db_session.execute(
            select(StaffOnboarding).where(StaffOnboarding.id == onboarding.id)
        )
    ).scalar_one()
    await db_session.refresh(reloaded)
    assert reloaded.status == "completed"
    # Post-fix: PATCH calls update_progress. With 5/5 complete the result
    # is 100. Pre-fix: 0 (the stale value) survives.
    assert reloaded.progress_percentage == 100, (
        f"PATCH should have recalculated progress to 100% (5/5 complete), "
        f"got {reloaded.progress_percentage}% -- status/progress out of sync"
    )
