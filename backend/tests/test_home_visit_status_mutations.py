# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for home-visit status-mutation methods.

These exercise HomeVisitService.confirm/mark_complete/cancel/reschedule
directly. They follow the pattern established by
``test_parent_connection_groups_enrollment_service.py`` -- service tests
avoid the FastAPI client + httpx + dependency_overrides path because
that path hits a known broken pytest-asyncio + SessionMaker fixture
ordering bug on the L30 backend.

Endpoint-layer coverage (role gates, response shape) is exercised by
the OpenAPI schema + the corresponding frontend mutation tests at
PR review time; the contract is documented in the route docstrings
and request-schema fields.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

# Pre-import PatronCategory: User.patron_category_id has an FK to
# patron_categories, and the model is not loaded by app.models.__init__.
# Without this, test_db's create_all blows up with NoReferencedTableError.
# This is a pre-existing infra bug from PR #1215; we paper over it here.
from app.models import patron_category as _patron_category  # noqa: F401
from app.models.parent_onboarding import (
    HomeVisitPurpose,
    HomeVisitStatus,
    HomeVisitStatusHistory,
    ParentHomeVisit,
)
from app.services.parent_onboarding import (
    HomeVisitService,
    InvalidHomeVisitTransitionError,
)


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


async def _mk_user(test_db, *, email: str, role) -> int:
    from app.core.security import hash_password
    from app.models.user import User

    u = User(
        email=email,
        password_hash=hash_password("Password123!"),
        first_name="First",
        last_name="Last",
        role=role,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


async def _mk_visit(
    test_db,
    *,
    patron,
    visitor,
    status: HomeVisitStatus = HomeVisitStatus.scheduled,
    scheduled_date: date | None = None,
) -> ParentHomeVisit:
    visit = ParentHomeVisit(
        patron_id=patron.id,
        visitor_id=visitor.id,
        purpose=HomeVisitPurpose.intake.value,
        status=status.value,
        scheduled_date=scheduled_date or date(2026, 6, 1),
        scheduled_time="10:00",
        address="123 Main St",
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)
    return visit


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_scheduled_visit_transitions_to_confirmed(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff1@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p1@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(test_db, patron=patron, visitor=staff)

    updated = await HomeVisitService.confirm_visit(
        test_db, visit, changed_by=staff, reason="Spoke with patron"
    )
    await test_db.commit()

    assert updated.status == HomeVisitStatus.confirmed.value

    # Audit row written with correct transition.
    rows = (
        await test_db.execute(
            select(HomeVisitStatusHistory).where(
                HomeVisitStatusHistory.visit_id == visit.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].from_status == HomeVisitStatus.scheduled.value
    assert rows[0].to_status == HomeVisitStatus.confirmed.value
    assert rows[0].changed_by_id == staff.id
    assert rows[0].reason == "Spoke with patron"


@pytest.mark.asyncio
async def test_confirm_already_confirmed_raises_invalid_transition(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff2@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p2@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(
        test_db, patron=patron, visitor=staff, status=HomeVisitStatus.confirmed
    )

    with pytest.raises(InvalidHomeVisitTransitionError):
        await HomeVisitService.confirm_visit(test_db, visit, changed_by=staff)


# ---------------------------------------------------------------------------
# Mark complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_complete_captures_outcomes_and_resources(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff3@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p3@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(
        test_db, patron=patron, visitor=staff, status=HomeVisitStatus.confirmed
    )

    updated = await HomeVisitService.mark_complete(
        test_db,
        visit,
        changed_by=staff,
        outcomes="Family received intake packet and signed up for WIC.",
        resources_delivered=["Books / reading materials", "Information packet"],
        follow_up_needed=True,
        follow_up_date=date(2026, 7, 1),
        follow_up_notes="Check on WIC application status",
        referrals=["WIC office"],
    )
    await test_db.commit()

    assert updated.status == HomeVisitStatus.completed.value
    assert updated.actual_end is not None
    assert updated.outcomes.startswith("Family received")
    assert updated.resources_delivered == [
        "Books / reading materials",
        "Information packet",
    ]
    assert updated.follow_up_needed is True
    assert updated.follow_up_date == date(2026, 7, 1)

    rows = (
        await test_db.execute(
            select(HomeVisitStatusHistory).where(
                HomeVisitStatusHistory.visit_id == visit.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    md = rows[0].metadata_json
    assert md["outcomes"].startswith("Family received")
    assert md["referrals"] == ["WIC office"]
    assert md["follow_up_notes"] == "Check on WIC application status"


@pytest.mark.asyncio
async def test_mark_complete_clears_follow_up_date_when_not_needed(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff4@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p4@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(test_db, patron=patron, visitor=staff)

    updated = await HomeVisitService.mark_complete(
        test_db,
        visit,
        changed_by=staff,
        outcomes="Everything good.",
        resources_delivered=[],
        follow_up_needed=False,
        follow_up_date=date(2026, 7, 1),  # provided but should be ignored
    )
    await test_db.commit()

    assert updated.follow_up_needed is False
    # follow_up_date is cleared when follow_up_needed is False so the UI
    # cannot show stale "follow-up scheduled for X" on a closed visit.
    assert updated.follow_up_date is None


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_visit_with_reason(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff5@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p5@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(test_db, patron=patron, visitor=staff)

    updated = await HomeVisitService.cancel_visit(
        test_db,
        visit,
        changed_by=staff,
        cancelled_reason="Family canceled",
        notify_acknowledged=True,
    )
    await test_db.commit()

    assert updated.status == HomeVisitStatus.cancelled.value
    assert updated.cancelled_reason == "Family canceled"

    rows = (
        await test_db.execute(
            select(HomeVisitStatusHistory).where(
                HomeVisitStatusHistory.visit_id == visit.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].reason == "Family canceled"
    assert rows[0].metadata_json == {"notify_acknowledged": True}


@pytest.mark.asyncio
async def test_cancel_completed_visit_raises(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff6@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p6@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(
        test_db, patron=patron, visitor=staff, status=HomeVisitStatus.completed
    )

    with pytest.raises(InvalidHomeVisitTransitionError):
        await HomeVisitService.cancel_visit(
            test_db, visit, changed_by=staff, cancelled_reason="x"
        )


# ---------------------------------------------------------------------------
# Reschedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reschedule_creates_new_visit_and_backlinks(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff7@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p7@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(
        test_db, patron=patron, visitor=staff, status=HomeVisitStatus.scheduled
    )

    original, replacement = await HomeVisitService.reschedule_visit(
        test_db,
        visit,
        changed_by=staff,
        new_scheduled_date=date(2026, 6, 15),
        new_scheduled_time="14:00",
        duration_minutes=90,
        reason="Family needs evening slot",
    )
    await test_db.commit()

    # Original is rescheduled and links forward.
    assert original.status == HomeVisitStatus.rescheduled.value
    assert original.rescheduled_to_id == replacement.id

    # Replacement is scheduled and carries the new date/time + same patron/visitor.
    assert replacement.status == HomeVisitStatus.scheduled.value
    assert replacement.scheduled_date == date(2026, 6, 15)
    assert replacement.scheduled_time == "14:00"
    assert replacement.patron_id == patron.id
    assert replacement.visitor_id == staff.id
    assert replacement.address == visit.address

    # Both visits have history rows (original = transition, replacement = creation).
    orig_history = (
        await test_db.execute(
            select(HomeVisitStatusHistory).where(
                HomeVisitStatusHistory.visit_id == original.id
            )
        )
    ).scalars().all()
    repl_history = (
        await test_db.execute(
            select(HomeVisitStatusHistory).where(
                HomeVisitStatusHistory.visit_id == replacement.id
            )
        )
    ).scalars().all()
    assert len(orig_history) == 1
    assert orig_history[0].metadata_json["replacement_visit_id"] == replacement.id
    assert len(repl_history) == 1
    assert repl_history[0].from_status is None
    assert repl_history[0].to_status == HomeVisitStatus.scheduled.value


@pytest.mark.asyncio
async def test_reschedule_completed_visit_raises(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff8@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p8@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(
        test_db, patron=patron, visitor=staff, status=HomeVisitStatus.completed
    )

    with pytest.raises(InvalidHomeVisitTransitionError):
        await HomeVisitService.reschedule_visit(
            test_db,
            visit,
            changed_by=staff,
            new_scheduled_date=date(2026, 6, 15),
            reason="x",
        )


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_conflicts_returns_same_visitor_same_date(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff9@x.com", role=UserRole.STAFF)
    patron_a = await _mk_user(test_db, email="pa@x.com", role=UserRole.PATRON)
    patron_b = await _mk_user(test_db, email="pb@x.com", role=UserRole.PATRON)
    target_date = date(2026, 6, 20)
    other_date = date(2026, 6, 21)

    a = await _mk_visit(
        test_db, patron=patron_a, visitor=staff, scheduled_date=target_date
    )
    b = await _mk_visit(
        test_db, patron=patron_b, visitor=staff, scheduled_date=target_date
    )
    # Should NOT match: other date.
    await _mk_visit(
        test_db, patron=patron_a, visitor=staff, scheduled_date=other_date
    )
    # Should NOT match: cancelled visits are excluded.
    cancelled = await _mk_visit(
        test_db,
        patron=patron_a,
        visitor=staff,
        scheduled_date=target_date,
        status=HomeVisitStatus.cancelled,
    )
    cancelled.cancelled_reason = "n/a"
    await test_db.commit()

    conflicts = await HomeVisitService.check_conflicts(
        test_db,
        visitor_id=staff.id,
        scheduled_date=target_date,
    )
    ids = {v.id for v in conflicts}
    assert a.id in ids
    assert b.id in ids
    assert cancelled.id not in ids


@pytest.mark.asyncio
async def test_check_conflicts_respects_exclude_visit_id(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff10@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p10@x.com", role=UserRole.PATRON)
    target_date = date(2026, 6, 25)

    a = await _mk_visit(
        test_db, patron=patron, visitor=staff, scheduled_date=target_date
    )

    conflicts = await HomeVisitService.check_conflicts(
        test_db,
        visitor_id=staff.id,
        scheduled_date=target_date,
        exclude_visit_id=a.id,
    )
    assert conflicts == []


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_history_returns_rows_newest_first(test_db):
    from app.models.user import UserRole

    staff = await _mk_user(test_db, email="staff11@x.com", role=UserRole.STAFF)
    patron = await _mk_user(test_db, email="p11@x.com", role=UserRole.PATRON)
    visit = await _mk_visit(test_db, patron=patron, visitor=staff)

    await HomeVisitService.confirm_visit(test_db, visit, changed_by=staff)
    await test_db.commit()
    await HomeVisitService.mark_complete(
        test_db,
        visit,
        changed_by=staff,
        outcomes="Done.",
        resources_delivered=[],
    )
    await test_db.commit()

    rows, total = await HomeVisitService.get_history(test_db, visit.id)
    assert total == 2
    # Newest first: completed transition is rows[0].
    assert rows[0].to_status == HomeVisitStatus.completed.value
    assert rows[1].to_status == HomeVisitStatus.confirmed.value
