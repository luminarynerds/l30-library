# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for end_of_day_service.py production bugs.

These tests pin the post-fix state for:
  - HoldStatus.READY (does not exist; enum is lowercase)
  - Checkout.created_at (column does not exist; it's checked_out_at)
  - CheckoutStatus.ACTIVE / RETURNED (lowercase only)
  - FineStatus.UNPAID (lowercase only)

Each EOD task method must execute without AttributeError on the buggy
references. POST /api/v1/end_of_day/sessions triggers these paths.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.end_of_day_service import EndOfDayService


def _mock_db_with_scalar(scalar_value=0):
    """Build an AsyncMock AsyncSession whose db.execute(...).scalar() returns scalar_value."""
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=scalar_value)
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value.all = MagicMock(return_value=[])
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_session = MagicMock(branch_id=1)
    mock_db.get = AsyncMock(return_value=mock_session)
    return mock_db


@pytest.mark.asyncio
async def test_process_holds_uses_lowercase_hold_status():
    """_process_holds must not AttributeError on HoldStatus.READY (enum is .ready)."""
    mock_db = _mock_db_with_scalar(0)
    result = await EndOfDayService._process_holds(mock_db, session_id=1)
    assert result["holds_ready"] == 0


@pytest.mark.asyncio
async def test_send_overdue_notices_uses_lowercase_checkout_status():
    """_send_overdue_notices must not AttributeError on CheckoutStatus.ACTIVE."""
    mock_db = _mock_db_with_scalar(0)
    result = await EndOfDayService._send_overdue_notices(mock_db, session_id=1)
    assert "overdue_count" in result or "message" in result


@pytest.mark.asyncio
async def test_statistics_summary_uses_correct_checkout_column_and_enums():
    """_statistics_summary must use Checkout.checked_out_at (not created_at) and
    lowercase enum members for CheckoutStatus.returned and FineStatus.unpaid."""
    mock_db = _mock_db_with_scalar(0)
    result = await EndOfDayService._statistics_summary(mock_db, session_id=1)
    assert "total_checkouts" in result or "message" in result


@pytest.mark.asyncio
async def test_holds_pull_list_uses_lowercase_hold_status():
    """_holds_pull_list must not AttributeError on HoldStatus.READY."""
    mock_db = _mock_db_with_scalar(0)
    result = await EndOfDayService._holds_pull_list(mock_db, session_id=1)
    assert result.get("holds_count") == 0
