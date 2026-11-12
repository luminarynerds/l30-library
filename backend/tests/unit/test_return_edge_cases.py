# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Return edge-case coverage for LSC circulation check-in flows."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.book_drop import CheckInResultStatus, ExceptionType, SortDestination
from app.models.circulation import CheckoutStatus
from app.services.book_drop_service import BookDropService


@pytest.mark.unit
class TestReturnEdgeCases:
    """Ensure return/check-in edge cases are handled without crashing."""

    @staticmethod
    def _service_with_session() -> tuple[BookDropService, SimpleNamespace]:
        db = MagicMock()
        db.add = MagicMock()
        service = BookDropService(db)
        session = SimpleNamespace(
            id=1,
            session_code="CKI-EDGE",
            use_backdating=False,
            backdate_to=None,
            branch_location="MAIN",
            book_drop=SimpleNamespace(exempt_overnight_fines=True),
            total_items=0,
            successful_checkins=0,
            holds_trapped=0,
            transits_created=0,
            exceptions_count=0,
        )
        return service, session

    @pytest.mark.asyncio
    async def test_return_item_never_checked_out(self):
        service, session = self._service_with_session()
        service._find_item_by_barcode = AsyncMock(return_value=SimpleNamespace(id=10, catalog_item_id=100))
        service._find_active_checkout = AsyncMock(return_value=None)
        service._handle_not_checked_out = AsyncMock()
        service._update_session_stats = AsyncMock()

        result = await service.process_checkin(session, "BC-NEVER-OUT", staff=SimpleNamespace(id=99))

        assert result.status == CheckInResultStatus.NOT_CHECKED_OUT
        service._handle_not_checked_out.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_return_checked_out_at_different_branch_routes_transit(self):
        service, session = self._service_with_session()
        result = SimpleNamespace(sort_destination=None, destination_branch=None)

        needs_transit = await service._check_for_transit(
            result=result,
            item_copy=SimpleNamespace(location="EAST BRANCH", catalog_item=SimpleNamespace(status=None)),
            current_branch="MAIN",
        )

        assert needs_transit is True
        assert result.sort_destination == SortDestination.TRANSIT

    @pytest.mark.asyncio
    async def test_return_item_marked_lost_records_lost_exception(self):
        service, _ = self._service_with_session()
        service.db.execute = AsyncMock(side_effect=[MagicMock(scalars=lambda: MagicMock(all=lambda: []))])

        exceptions = await service._check_for_exceptions(
            checkout=SimpleNamespace(
                status=CheckoutStatus.lost,
                id=44,
                user=SimpleNamespace(id=1, is_active=True, first_name="A", last_name="B"),
            ),
            item_copy=SimpleNamespace(notes=None, condition=None, id=2),
        )

        assert any(e["type"] == ExceptionType.LOST_ITEM_RETURNED for e in exceptions)

    @pytest.mark.asyncio
    async def test_return_item_marked_missing_is_graceful_success_path(self):
        service, _ = self._service_with_session()
        result = SimpleNamespace(
            status=None,
            sort_destination=None,
            exception_type=None,
            exception_message=None,
            item_copy_id=1,
        )
        service.db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        await service._determine_final_status(result, hold=None, needs_transit=False, exceptions=[])

        assert result.status == CheckInResultStatus.SUCCESS
        assert result.sort_destination == SortDestination.RESHELVE

    @pytest.mark.asyncio
    async def test_return_with_damage_noticed_sets_condition_issue(self):
        service, _ = self._service_with_session()
        result = SimpleNamespace(
            condition_checked=False,
            condition_status=None,
            condition_notes=None,
            status=CheckInResultStatus.SUCCESS,
            sort_destination=SortDestination.RESHELVE,
            exception_type=None,
            exception_message=None,
        )

        await service._record_condition_check(
            result=result,
            item_copy=SimpleNamespace(condition="good"),
            condition_status="damaged",
            condition_notes="Cover torn on return",
            staff=SimpleNamespace(id=1),
        )

        assert result.status == CheckInResultStatus.CONDITION_ISSUE
        assert result.exception_type == ExceptionType.DAMAGED_ITEM

    @pytest.mark.asyncio
    async def test_return_that_triggers_hold_for_next_patron(self):
        service, _ = self._service_with_session()
        hold = SimpleNamespace(id=12, user_id=7, status=None, notified_at=None, expires_at=None)
        hold_result = MagicMock(scalar_one_or_none=lambda: hold)
        service.db.execute = AsyncMock(return_value=hold_result)

        result = SimpleNamespace(hold_id=None, hold_patron_id=None, sort_destination=None)
        trapped = await service._check_and_trap_hold(
            result=result,
            item_copy=SimpleNamespace(id=2, catalog_item_id=55, catalog_item=SimpleNamespace(status=None)),
        )

        assert trapped is hold
        assert result.sort_destination == SortDestination.HOLD_SHELF

    @pytest.mark.asyncio
    async def test_return_that_completes_ill_return_routes_transit(self):
        service, _ = self._service_with_session()
        result = SimpleNamespace(sort_destination=None, destination_branch=None)

        transit = await service._check_for_transit(
            result=result,
            item_copy=SimpleNamespace(location="ILL-HUB", catalog_item=SimpleNamespace(status=None)),
            current_branch="MAIN",
        )

        assert transit is True
        assert result.destination_branch == "ILL-HUB"

    @pytest.mark.asyncio
    async def test_return_same_day_not_overdue(self):
        service, _ = self._service_with_session()
        result = SimpleNamespace(
            effective_checkin_time=datetime.now(timezone.utc),
            was_overdue=False,
            overdue_days=0,
            fine_amount=None,
            fine_waived_by_backdate=False,
        )
        checkout = SimpleNamespace(due_date=datetime.now(timezone.utc) + timedelta(days=14), user_id=1, id=1, item_id=1)

        service._create_fine = AsyncMock()
        await service._process_overdue_and_fines(result, checkout, item_copy=SimpleNamespace(), exempt_overnight_fines=True)

        assert result.was_overdue is False
        service._create_fine.assert_not_called()

    @pytest.mark.asyncio
    async def test_return_after_offline_backdated_uses_override_time(self):
        service, session = self._service_with_session()
        backdated = datetime(2026, 1, 30, 8, 15, tzinfo=timezone.utc)

        service._find_item_by_barcode = AsyncMock(return_value=None)
        service._update_session_stats = AsyncMock()

        result = await service.process_checkin(
            session,
            "BC-OFFLINE",
            staff=SimpleNamespace(id=2),
            override_backdate=backdated,
        )

        assert result.effective_checkin_time == backdated
        assert result.status == CheckInResultStatus.ITEM_NOT_FOUND

    @pytest.mark.asyncio
    async def test_return_wrong_barcode_scan(self):
        service, session = self._service_with_session()
        service._find_item_by_barcode = AsyncMock(return_value=None)
        service._update_session_stats = AsyncMock()

        result = await service.process_checkin(session, "WRONG-BC", staff=SimpleNamespace(id=3))

        assert result.status == CheckInResultStatus.ITEM_NOT_FOUND
        assert result.exception_type == ExceptionType.OTHER

    @pytest.mark.asyncio
    async def test_return_item_recalled_treated_as_hold_ready_path(self):
        """Recall behavior maps to hold-trap routing in current implementation."""
        result = SimpleNamespace(
            status=None,
            sort_destination=None,
            exception_type=None,
            exception_message=None,
        )

        service, _ = self._service_with_session()
        await service._determine_final_status(
            result=result,
            hold=SimpleNamespace(id=501),
            needs_transit=False,
            exceptions=[],
        )

        assert result.status == CheckInResultStatus.HOLD_TRAPPED
        assert result.sort_destination == SortDestination.HOLD_SHELF

    @pytest.mark.asyncio
    async def test_bulk_book_drop_return_100_items_updates_counters(self):
        service, session = self._service_with_session()

        for _ in range(100):
            await service._update_session_stats(
                session,
                SimpleNamespace(status=CheckInResultStatus.SUCCESS),
            )

        assert session.total_items == 100
        assert session.successful_checkins == 100
