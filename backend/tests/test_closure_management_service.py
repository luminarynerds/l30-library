# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Focused tests for ClosureManagementService behavior and edge cases."""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.multi_branch import Branch, BranchClosure, LibrarySystem
from app.services.closure_management_service import ClosureManagementService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        # Some closure workflows issue a list-shaped query (e.g. holds for
        # notification fan-out) after the initial single-row lookup this
        # stub is normally set up for. Default to "no rows" so those
        # incidental queries don't blow up tests that only care about the
        # single-row result.
        return _ScalarsResult([])


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    return ClosureManagementService(mock_db)


@pytest.fixture
def sample_branch():
    system = LibrarySystem(id=1, code="TEST", name="Test System", timezone="America/New_York")
    return Branch(id=1, code="MAIN", name="Main Library", library_system=system)


@pytest.fixture
def sample_closure():
    return BranchClosure(
        id=1,
        branch_id=1,
        start_date=date.today(),
        end_date=date.today(),
        reason="Emergency Closure",
        created_by_id=1,
    )


@pytest.mark.asyncio
async def test_close_today_raises_when_branch_missing(service, mock_db):
    mock_db.execute.return_value = _ScalarResult(None)

    with pytest.raises(ValueError, match="Branch 999 not found"):
        await service.close_today(branch_id=999, reason="Emergency", created_by_id=1)


@pytest.mark.asyncio
async def test_close_today_full_workflow_sets_completion_flags(service, mock_db, sample_branch):
    mock_db.execute.return_value = _ScalarResult(sample_branch)

    closure = await service.close_today(
        branch_id=1,
        reason="Emergency",
        created_by_id=9,
        send_notifications=True,
        cancel_events=True,
        reschedule_programs=True,
        update_external_services=True,
        notify_partner_organizations=True,
    )

    assert closure.patrons_with_holds_notified is True
    assert closure.staff_notified is True
    assert closure.events_canceled is True
    assert closure.programs_rescheduled is True
    assert closure.website_updated is True
    assert closure.phone_message_updated is True
    assert closure.social_media_updated is True
    assert closure.google_maps_updated is True
    assert closure.apple_maps_updated is True
    assert closure.partner_organizations_notified is True
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_closure_ignores_non_updatable_fields(service, mock_db, sample_closure):
    mock_db.execute.return_value = _ScalarResult(sample_closure)

    updated = await service.update_closure(
        closure_id=1,
        updated_by_id=22,
        website_updated=True,
        branch_id=999,  # should be ignored
        created_by_id=999,  # should be ignored
    )

    assert updated.website_updated is True
    assert updated.branch_id == 1
    assert updated.created_by_id == 1
    assert updated.updated_by_id == 22
    assert isinstance(updated.updated_at, datetime)


@pytest.mark.asyncio
async def test_get_patrons_with_holds_maps_missing_user_and_item(service, mock_db, sample_closure):
    hold_with_data = SimpleNamespace(
        user_id=11,
        user=SimpleNamespace(full_name="Ana", email="ana@example.org"),
        item=SimpleNamespace(title="Dune"),
        created_at=datetime(2025, 1, 5, 10, 30, tzinfo=timezone.utc),
    )
    hold_with_missing_relations = SimpleNamespace(
        user_id=12,
        user=None,
        item=None,
        created_at=None,
    )
    mock_db.execute.side_effect = [
        _ScalarResult(sample_closure),
        _ScalarsResult([hold_with_data, hold_with_missing_relations]),
    ]

    patrons = await service.get_patrons_with_holds(1)

    assert patrons == [
        {
            "patron_id": 11,
            "patron_name": "Ana",
            "patron_email": "ana@example.org",
            "item_title": "Dune",
            "hold_placed_at": "2025-01-05T10:30:00+00:00",
        },
        {
            "patron_id": 12,
            "patron_name": "Unknown",
            "patron_email": None,
            "item_title": "Unknown",
            "hold_placed_at": None,
        },
    ]


@pytest.mark.asyncio
async def test_update_external_services_only_toggles_requested_channels(service, mock_db, sample_closure):
    mock_db.execute.return_value = _ScalarResult(sample_closure)

    updated = await service.update_external_services(
        closure_id=1,
        updated_by_id=8,
        website=True,
        social_media=True,
        apple_maps=True,
    )

    assert updated.website_updated is True
    assert updated.social_media_updated is True
    assert updated.apple_maps_updated is True
    assert updated.phone_message_updated is not True
    assert updated.google_maps_updated is not True
    assert updated.updated_by_id == 8


@pytest.mark.asyncio
async def test_get_closure_completion_status_requires_all_flags_for_all_complete(service):
    closure = BranchClosure(
        id=1,
        branch_id=1,
        start_date=date.today(),
        end_date=date.today(),
        reason="Weather",
        created_by_id=1,
        patrons_with_holds_notified=True,
        staff_notified=True,
        partner_organizations_notified=True,
        website_updated=True,
        phone_message_updated=True,
        social_media_updated=True,
        google_maps_updated=True,
        apple_maps_updated=False,
        events_canceled=True,
        programs_rescheduled=True,
    )

    with patch.object(service, "get_closure_status", new=AsyncMock(return_value={"closure": closure})):
        completion = await service.get_closure_completion_status(1)

    assert completion["maps_updated"] is False
    assert completion["all_complete"] is False


@pytest.mark.asyncio
async def test_get_affected_events_returns_empty_when_branch_not_found(service, mock_db, sample_closure):
    mock_db.execute.side_effect = [
        _ScalarResult(sample_closure),
        _ScalarResult(None),
        _ScalarsResult([]),
    ]

    events = await service.get_affected_events(1)

    assert events == []


@pytest.mark.asyncio
async def test_get_active_closures_coerces_query_result_to_list(service, mock_db, sample_closure):
    mock_db.execute.return_value = _ScalarsResult([sample_closure])

    active = await service.get_active_closures(branch_id=1)

    assert isinstance(active, list)
    assert active == [sample_closure]
