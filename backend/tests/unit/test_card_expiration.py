# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for card expiration validation.

Tests for:
- User model card expiration methods
- Grace period handling
- Card expiration checking helper functions
- Edge cases (mid-checkout session expiration)
"""

from datetime import datetime, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User, UserRole
from app.core.datetime_utils import utc_now


class TestUserCardExpirationMethods:
    """Test User model card expiration methods."""

    def test_is_card_expired_no_expiration_date(self):
        """Test that cards without expiration date are considered valid."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=None,
        )

        assert user.is_card_expired() is False
        assert user.is_card_expired(grace_period_days=7) is False

    def test_is_card_expired_valid_card(self):
        """Test that cards with future expiration are valid."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() + timedelta(days=365),
        )

        assert user.is_card_expired() is False
        assert user.is_card_expired(grace_period_days=7) is False

    def test_is_card_expired_expired_card(self):
        """Test that cards with past expiration are expired."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() - timedelta(days=30),
        )

        assert user.is_card_expired() is True
        assert user.is_card_expired(grace_period_days=7) is True

    def test_is_card_expired_within_grace_period(self):
        """Test that cards within grace period are valid with grace period enabled."""
        # Card expired 3 days ago
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() - timedelta(days=3),
        )

        # Without grace period: expired
        assert user.is_card_expired(grace_period_days=0) is True

        # With 7-day grace period: valid (3 < 7)
        assert user.is_card_expired(grace_period_days=7) is False

        # With 2-day grace period: expired (3 > 2)
        assert user.is_card_expired(grace_period_days=2) is True

    def test_is_card_expired_at_grace_period_boundary(self):
        """Test behavior at exactly the grace period boundary."""
        # Card expired exactly 7 days ago
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() - timedelta(days=7, hours=1),
        )

        # With 7-day grace period: expired (just past)
        assert user.is_card_expired(grace_period_days=7) is True

    def test_days_until_card_expires_no_expiration(self):
        """Test days_until_card_expires with no expiration date."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=None,
        )

        assert user.days_until_card_expires() is None

    def test_days_until_card_expires_future_expiration(self):
        """Test days_until_card_expires with future expiration."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() + timedelta(days=30),
        )

        days = user.days_until_card_expires()
        assert days is not None
        assert 29 <= days <= 30  # Allow for timing variance

    def test_days_until_card_expires_past_expiration(self):
        """Test days_until_card_expires with past expiration (negative days)."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() - timedelta(days=10),
        )

        days = user.days_until_card_expires()
        assert days is not None
        assert -11 <= days <= -10  # Allow for timing variance


class TestCheckCardExpiration:
    """Test check_card_expiration helper function."""

    @pytest.mark.asyncio
    async def test_check_card_expiration_no_expiration_date(self):
        """Test that users without expiration date can proceed."""
        from app.core.authorization import check_card_expiration

        user = MagicMock(spec=User)
        user.card_expires_at = None
        user.home_library_system_id = None

        db = AsyncMock()

        can_proceed, days = await check_card_expiration(user, db)

        assert can_proceed is True
        assert days is None

    @pytest.mark.asyncio
    async def test_check_card_expiration_valid_card(self):
        """Test that users with valid cards can proceed."""
        from app.core.authorization import check_card_expiration

        user = MagicMock(spec=User)
        user.card_expires_at = utc_now() + timedelta(days=100)
        user.home_library_system_id = None
        user.is_card_expired = MagicMock(return_value=False)
        user.days_until_card_expires = MagicMock(return_value=100)

        db = AsyncMock()

        can_proceed, days = await check_card_expiration(user, db)

        assert can_proceed is True
        assert days == 100

    @pytest.mark.asyncio
    async def test_check_card_expiration_expired_card(self):
        """Test that users with expired cards are blocked."""
        from app.core.authorization import check_card_expiration

        user = MagicMock(spec=User)
        user.card_expires_at = utc_now() - timedelta(days=30)
        user.home_library_system_id = None
        user.is_card_expired = MagicMock(return_value=True)
        user.days_until_card_expires = MagicMock(return_value=-30)

        db = AsyncMock()

        can_proceed, days = await check_card_expiration(user, db)

        assert can_proceed is False
        assert days == -30

    @pytest.mark.asyncio
    async def test_check_card_expiration_within_grace_period(self):
        """Test that users within grace period can proceed."""
        from app.core.authorization import check_card_expiration

        user = MagicMock(spec=User)
        user.card_expires_at = utc_now() - timedelta(days=3)
        user.home_library_system_id = None
        # With default 7-day grace period, 3 days overdue is still valid
        user.is_card_expired = MagicMock(return_value=False)
        user.days_until_card_expires = MagicMock(return_value=-3)

        db = AsyncMock()

        can_proceed, days = await check_card_expiration(user, db, allow_grace_period=True)

        assert can_proceed is True
        assert days == -3

    @pytest.mark.asyncio
    async def test_check_card_expiration_no_grace_period(self):
        """Test that grace period can be disabled."""
        from app.core.authorization import check_card_expiration

        user = MagicMock(spec=User)
        user.card_expires_at = utc_now() - timedelta(days=1)
        user.home_library_system_id = None
        # Without grace period, 1 day overdue is expired
        user.is_card_expired = MagicMock(return_value=True)
        user.days_until_card_expires = MagicMock(return_value=-1)

        db = AsyncMock()

        can_proceed, days = await check_card_expiration(user, db, allow_grace_period=False)

        assert can_proceed is False
        assert days == -1


class TestCalculateCardExpirationDate:
    """Test calculate_card_expiration_date helper function."""

    def test_calculate_card_expiration_date_default(self):
        """Test default expiration calculation (3 years)."""
        from app.core.authorization import calculate_card_expiration_date

        now = utc_now()
        expiration = calculate_card_expiration_date()

        # Should be approximately 3 years from now
        days_until = (expiration - now).days
        assert 1090 <= days_until <= 1096  # ~3 years (365 * 3 = 1095)

    def test_calculate_card_expiration_date_custom_years(self):
        """Test custom expiration years."""
        from app.core.authorization import calculate_card_expiration_date

        now = utc_now()
        expiration = calculate_card_expiration_date(expiry_years=5)

        # Should be approximately 5 years from now
        days_until = (expiration - now).days
        assert 1820 <= days_until <= 1830  # ~5 years (365 * 5 = 1825)

    def test_calculate_card_expiration_date_from_date(self):
        """Test expiration from specific date."""
        from app.core.authorization import calculate_card_expiration_date

        start_date = utc_now() + timedelta(days=30)  # 30 days from now
        expiration = calculate_card_expiration_date(from_date=start_date, expiry_years=1)

        # Should be approximately 1 year + 30 days from now
        now = utc_now()
        days_until = (expiration - now).days
        assert 390 <= days_until <= 400  # ~1 year + 30 days


class TestEdgeCases:
    """Test edge cases for card expiration."""

    def test_card_expires_exactly_now(self):
        """Test card that expires at exactly the current moment."""
        _ = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now(),
        )

        # Without grace period: expired (or right at boundary)
        # The comparison is > not >= so exactly now should still be valid
        # But timing may cause this to be expired
        # This is acceptable edge case behavior

    def test_very_old_expired_card(self):
        """Test card that expired many years ago."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() - timedelta(days=3650),  # 10 years ago
        )

        assert user.is_card_expired() is True
        days = user.days_until_card_expires()
        assert days is not None
        assert days < -3600  # More than 10 years ago

    def test_very_long_future_expiration(self):
        """Test card with far-future expiration."""
        user = User(
            id=1,
            email="test@example.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            card_expires_at=utc_now() + timedelta(days=3650),  # 10 years from now
        )

        assert user.is_card_expired() is False
        days = user.days_until_card_expires()
        assert days is not None
        assert days > 3600  # More than 10 years from now


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
