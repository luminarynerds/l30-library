# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the env-or-DB resolver in email_safeguard_config."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _settings(daily=500, alert=100, dedup=24):
    s = MagicMock()
    s.email_daily_send_cap = daily
    s.email_alert_threshold = alert
    s.email_dedup_window_hours = dedup
    return s


def _patch_db(value):
    """Patch _get_db_value to return ``value`` for whichever field is asked."""
    return patch(
        "app.core.email_safeguard_config._get_db_value",
        new=AsyncMock(return_value=value),
    )


@pytest.mark.unit
class TestEnvWinsWhenSet:
    @pytest.mark.asyncio
    async def test_daily_cap_env_wins_when_differs_from_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(daily=900),
        ), _patch_db(50):
            from app.core.email_safeguard_config import get_daily_send_cap
            assert await get_daily_send_cap() == 900

    @pytest.mark.asyncio
    async def test_alert_threshold_env_wins_when_differs_from_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(alert=250),
        ), _patch_db(50):
            from app.core.email_safeguard_config import get_alert_threshold
            assert await get_alert_threshold() == 250

    @pytest.mark.asyncio
    async def test_dedup_window_env_wins_when_differs_from_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(dedup=72),
        ), _patch_db(6):
            from app.core.email_safeguard_config import get_dedup_window_hours
            assert await get_dedup_window_hours() == 72


@pytest.mark.unit
class TestDbWinsWhenEnvIsDefault:
    @pytest.mark.asyncio
    async def test_daily_cap_db_wins_when_env_is_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(daily=500),
        ), _patch_db(750):
            from app.core.email_safeguard_config import get_daily_send_cap
            assert await get_daily_send_cap() == 750

    @pytest.mark.asyncio
    async def test_alert_threshold_db_wins_when_env_is_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(alert=100),
        ), _patch_db(75):
            from app.core.email_safeguard_config import get_alert_threshold
            assert await get_alert_threshold() == 75

    @pytest.mark.asyncio
    async def test_dedup_window_db_wins_when_env_is_default(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(dedup=24),
        ), _patch_db(6):
            from app.core.email_safeguard_config import get_dedup_window_hours
            assert await get_dedup_window_hours() == 6


@pytest.mark.unit
class TestFallsBackToEnvDefault:
    @pytest.mark.asyncio
    async def test_daily_cap_falls_back_when_db_returns_none(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(daily=500),
        ), _patch_db(None):
            from app.core.email_safeguard_config import get_daily_send_cap
            assert await get_daily_send_cap() == 500

    @pytest.mark.asyncio
    async def test_alert_threshold_falls_back_when_db_returns_none(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(alert=100),
        ), _patch_db(None):
            from app.core.email_safeguard_config import get_alert_threshold
            assert await get_alert_threshold() == 100

    @pytest.mark.asyncio
    async def test_dedup_window_falls_back_when_db_returns_none(self):
        with patch(
            "app.core.email_safeguard_config.get_settings",
            return_value=_settings(dedup=24),
        ), _patch_db(None):
            from app.core.email_safeguard_config import get_dedup_window_hours
            assert await get_dedup_window_hours() == 24


@pytest.mark.unit
class TestGetDbValueGuards:
    """Direct tests of _get_db_value's defensive parsing."""

    @pytest.mark.asyncio
    async def test_returns_none_when_row_missing(self):
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_configuration_not_dict(self):
        row = MagicMock(configuration=None)
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_email_marketing_subobject_missing(self):
        row = MagicMock(configuration={"other_section": {}})
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_field_is_zero_or_null(self):
        row = MagicMock(configuration={"email_marketing": {"email_daily_send_cap": 0}})
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_field_is_non_coercible(self):
        row = MagicMock(
            configuration={"email_marketing": {"email_daily_send_cap": "not-a-number"}}
        )
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") is None

    @pytest.mark.asyncio
    async def test_returns_int_when_field_present_as_int(self):
        row = MagicMock(
            configuration={"email_marketing": {"email_daily_send_cap": 750}}
        )
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") == 750

    @pytest.mark.asyncio
    async def test_returns_int_when_field_present_as_string_digits(self):
        row = MagicMock(
            configuration={"email_marketing": {"email_daily_send_cap": "750"}}
        )
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=row)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.core.email_safeguard_config.get_async_session",
            return_value=mock_session,
        ):
            from app.core.email_safeguard_config import _get_db_value
            assert await _get_db_value("email_daily_send_cap") == 750
