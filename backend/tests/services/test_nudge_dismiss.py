# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for nudge dismissal persistence.

Bug: a nudge dismissed before its 'shown' event persisted (the toast fires
'shown' and 'dismissed' as two racing async requests) was silently dropped,
so /nudges/active kept returning it and the popup would not clear.
"""
import pytest
from sqlalchemy import select

from app.models.nudge import Nudge, PatronNudgeState
from app.services.nudge_service import (
    get_active_nudges_for_patron,
    record_nudge_event,
)


@pytest.fixture
async def toast_nudge(db):
    nudge = Nudge(
        slug="test-indie-toast",
        trigger_conditions=[],
        content_body="Check out indie ebooks!",
        delivery_type="toast",
        delivery_placement="global",
        priority=5,
    )
    db.add(nudge)
    await db.commit()
    await db.refresh(nudge)
    return nudge


async def test_dismiss_without_prior_shown_persists(db, test_patron, toast_nudge):
    # Fresh patron: the nudge is active.
    before = await get_active_nudges_for_patron(
        db=db, patron_id=test_patron.id, page_context="global"
    )
    assert any(n["id"] == toast_nudge.id for n in before)

    # Dismiss with NO prior 'shown' state row (the race condition).
    await record_nudge_event(
        db=db, patron_id=test_patron.id, nudge_id=toast_nudge.id, action="dismissed"
    )

    # A dismissed state row must now exist.
    state = (
        await db.execute(
            select(PatronNudgeState).where(
                PatronNudgeState.patron_id == test_patron.id,
                PatronNudgeState.nudge_id == toast_nudge.id,
            )
        )
    ).scalar_one_or_none()
    assert state is not None, "dismiss with no prior shown row was dropped"
    assert state.status == "dismissed"
    assert state.dismissed_at is not None

    # And the nudge must no longer be returned as active.
    after = await get_active_nudges_for_patron(
        db=db, patron_id=test_patron.id, page_context="global"
    )
    assert not any(n["id"] == toast_nudge.id for n in after)


async def test_dismiss_after_shown_still_persists(db, test_patron, toast_nudge):
    await record_nudge_event(
        db=db, patron_id=test_patron.id, nudge_id=toast_nudge.id, action="shown"
    )
    await record_nudge_event(
        db=db, patron_id=test_patron.id, nudge_id=toast_nudge.id, action="dismissed"
    )
    after = await get_active_nudges_for_patron(
        db=db, patron_id=test_patron.id, page_context="global"
    )
    assert not any(n["id"] == toast_nudge.id for n in after)


async def test_acted_on_without_prior_shown_persists(db, test_patron, toast_nudge):
    await record_nudge_event(
        db=db, patron_id=test_patron.id, nudge_id=toast_nudge.id, action="acted_on"
    )
    state = (
        await db.execute(
            select(PatronNudgeState).where(
                PatronNudgeState.patron_id == test_patron.id,
                PatronNudgeState.nudge_id == toast_nudge.id,
            )
        )
    ).scalar_one_or_none()
    assert state is not None
    assert state.status == "acted_on"
    after = await get_active_nudges_for_patron(
        db=db, patron_id=test_patron.id, page_context="global"
    )
    assert not any(n["id"] == toast_nudge.id for n in after)
