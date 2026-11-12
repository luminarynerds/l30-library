"""Unit tests for GET /fair-scheduling/me/shifts.

Mocks the AsyncSession so we can verify the endpoint's mapping/flagging logic
without standing up a full DB. Mirrors the style of test_patron_account_endpoints.
"""

import pytest
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.user import User, UserRole
from app.models.staff_schedule_fairness import (
    FairnessShiftType,
    ShiftStatus,
    StaffShift,
)


def _make_user(user_id: int = 1) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = UserRole.STAFF
    user.is_active = True
    return user


def _make_shift(
    shift_id: int,
    staff_id: int,
    shift_date_value: date,
    start: time = time(9, 0),
    end: time = time(17, 0),
    shift_type: FairnessShiftType = FairnessShiftType.MIDDAY,
    status: ShiftStatus = ShiftStatus.ASSIGNED,
    is_holiday: bool = False,
    is_weekend: bool = False,
) -> MagicMock:
    shift = MagicMock(spec=StaffShift)
    shift.id = shift_id
    shift.staff_id = staff_id
    shift.branch_id = 7
    shift.shift_date = shift_date_value
    shift.scheduled_start = start
    shift.scheduled_end = end
    shift.shift_type = shift_type
    shift.status = status
    shift.scheduled_hours = 8.0
    shift.is_holiday = is_holiday
    shift.is_weekend = is_weekend
    return shift


def _make_db(shifts: list, swap_keys: list = None, callout_shift_ids: list = None) -> AsyncMock:
    """Build an AsyncMock db whose three execute() calls return the given rows.

    Order matches the endpoint:
      1. shifts query  -> .scalars().all() == shifts
      2. swaps query   -> .all() == swap_keys (list of (date, time) tuples)
      3. callouts query -> .all() == callout_shift_ids (list of (id,) tuples)
    """
    swap_keys = swap_keys or []
    callout_shift_ids = callout_shift_ids or []

    shifts_result = MagicMock()
    shifts_result.scalars.return_value.all.return_value = shifts

    swap_result = MagicMock()
    swap_result.all.return_value = swap_keys

    callout_result = MagicMock()
    callout_result.all.return_value = callout_shift_ids

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[shifts_result, swap_result, callout_result])
    return db


@pytest.mark.asyncio
async def test_returns_empty_when_no_shifts():
    """No shifts in the window -> empty list, swap/callout queries are skipped."""
    from app.api.v1.fair_scheduling import get_my_shifts

    user = _make_user()
    db = AsyncMock()
    shifts_result = MagicMock()
    shifts_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=shifts_result)

    response = await get_my_shifts(
        days_ahead=14, include_today=True, current_user=user, db=db
    )

    assert response.shifts == []
    assert response.range_start == date.today()
    assert response.range_end == date.today() + timedelta(days=14)
    # When there are no shifts, the endpoint short-circuits before the swap/callout queries
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_maps_shifts_and_flags_off_by_default():
    """Maps StaffShift attributes and leaves has_open_swap/callout false when no matches."""
    from app.api.v1.fair_scheduling import get_my_shifts

    user = _make_user(user_id=42)
    today = date.today()
    shift = _make_shift(
        shift_id=101,
        staff_id=42,
        shift_date_value=today,
        start=time(9, 0),
        end=time(17, 0),
        shift_type=FairnessShiftType.OPENING,
        status=ShiftStatus.ASSIGNED,
        is_weekend=False,
    )
    db = _make_db(shifts=[shift], swap_keys=[], callout_shift_ids=[])

    response = await get_my_shifts(
        days_ahead=14, include_today=True, current_user=user, db=db
    )

    assert len(response.shifts) == 1
    out = response.shifts[0]
    assert out.shift_id == 101
    assert out.branch_id == 7
    assert out.shift_date == today
    assert out.shift_type == "opening"  # enum.value
    assert out.status == "assigned"
    assert out.scheduled_start == time(9, 0)
    assert out.scheduled_end == time(17, 0)
    assert out.scheduled_hours == 8.0
    assert out.has_open_swap is False
    assert out.has_open_callout is False


@pytest.mark.asyncio
async def test_open_swap_listing_flips_has_open_swap():
    """A swap listing keyed by (shift_date, scheduled_start, scheduled_end)
    sets has_open_swap=True. The key is a 3-tuple (end_time was added to
    reduce false positives on same-day/same-start split shifts -- see
    app/api/v1/fair_scheduling.py)."""
    from app.api.v1.fair_scheduling import get_my_shifts

    user = _make_user(user_id=42)
    today = date.today()
    shift = _make_shift(
        shift_id=101,
        staff_id=42,
        shift_date_value=today,
        start=time(13, 0),
        end=time(17, 0),
    )
    db = _make_db(
        shifts=[shift],
        swap_keys=[(today, time(13, 0), time(17, 0))],
        callout_shift_ids=[],
    )

    response = await get_my_shifts(
        days_ahead=14, include_today=True, current_user=user, db=db
    )

    assert response.shifts[0].has_open_swap is True
    assert response.shifts[0].has_open_callout is False


@pytest.mark.asyncio
async def test_open_callout_flips_has_open_callout():
    """A callout request matched by original_shift_id sets has_open_callout=True."""
    from app.api.v1.fair_scheduling import get_my_shifts

    user = _make_user(user_id=42)
    today = date.today()
    shift = _make_shift(shift_id=202, staff_id=42, shift_date_value=today)
    db = _make_db(
        shifts=[shift],
        swap_keys=[],
        callout_shift_ids=[(202,)],
    )

    response = await get_my_shifts(
        days_ahead=14, include_today=True, current_user=user, db=db
    )

    assert response.shifts[0].has_open_swap is False
    assert response.shifts[0].has_open_callout is True


@pytest.mark.asyncio
async def test_include_today_false_starts_range_tomorrow():
    """include_today=False bumps range_start to tomorrow."""
    from app.api.v1.fair_scheduling import get_my_shifts

    user = _make_user()
    db = AsyncMock()
    shifts_result = MagicMock()
    shifts_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=shifts_result)

    response = await get_my_shifts(
        days_ahead=7, include_today=False, current_user=user, db=db
    )

    assert response.range_start == date.today() + timedelta(days=1)
    assert response.range_end == date.today() + timedelta(days=7)
