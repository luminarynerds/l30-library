# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for OverflowPurchaseService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.overflow_purchase import OverflowPurchase, OverflowPurchaseStatus


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.stripe_secret_key = "sk_test_123"
    settings.overflow_purchase_enabled = True
    settings.overflow_purchase_price_cents = 1499
    settings.library_kickback_percent = 15
    settings.trusted_hosts = "l30.org"
    return settings


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    @patch("app.services.overflow_purchase_service.stripe")
    @patch("app.services.overflow_purchase_service.get_settings")
    async def test_creates_session(self, mock_get_settings, mock_stripe, mock_db, mock_settings):
        mock_get_settings.return_value = mock_settings
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            id="cs_test_123", url="https://checkout.stripe.com/test"
        )

        from app.services.overflow_purchase_service import OverflowPurchaseService
        service = OverflowPurchaseService(mock_db)
        result = await service.create_checkout_session(
            user_id=1, metislib_ebook_id=42,
            ebook_title="Test Book", ebook_author="Author",
            success_url="https://example.com/ok",
            cancel_url="https://example.com/no",
        )

        assert result["session_id"] == "cs_test_123"
        assert result["checkout_url"] == "https://checkout.stripe.com/test"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.overflow_purchase_service.get_settings")
    async def test_raises_when_disabled(self, mock_get_settings, mock_db, mock_settings):
        mock_settings.overflow_purchase_enabled = False
        mock_get_settings.return_value = mock_settings

        from app.services.overflow_purchase_service import OverflowPurchaseService
        service = OverflowPurchaseService(mock_db)

        with pytest.raises(ValueError, match="currently disabled"):
            await service.create_checkout_session(
                user_id=1, metislib_ebook_id=42,
                ebook_title="Test", ebook_author="Author",
                success_url="https://x.com/ok", cancel_url="https://x.com/no",
            )


class TestHandleSessionExpired:
    @pytest.mark.asyncio
    @patch("app.services.overflow_purchase_service.get_settings")
    async def test_marks_pending_as_cancelled(self, mock_get_settings, mock_db, mock_settings):
        mock_get_settings.return_value = mock_settings
        purchase = MagicMock(spec=OverflowPurchase)
        purchase.status = OverflowPurchaseStatus.PENDING
        purchase.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = purchase
        mock_db.execute.return_value = mock_result

        from app.services.overflow_purchase_service import OverflowPurchaseService
        service = OverflowPurchaseService(mock_db)
        await service.handle_session_expired("cs_test_expired")

        assert purchase.status == OverflowPurchaseStatus.CANCELLED
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.overflow_purchase_service.get_settings")
    async def test_skips_completed_purchase(self, mock_get_settings, mock_db, mock_settings):
        mock_get_settings.return_value = mock_settings
        purchase = MagicMock(spec=OverflowPurchase)
        purchase.status = OverflowPurchaseStatus.COMPLETED
        purchase.id = 2

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = purchase
        mock_db.execute.return_value = mock_result

        from app.services.overflow_purchase_service import OverflowPurchaseService
        service = OverflowPurchaseService(mock_db)
        await service.handle_session_expired("cs_test_completed")

        assert purchase.status == OverflowPurchaseStatus.COMPLETED


class TestHandlePaymentSuccess:
    @pytest.mark.asyncio
    @patch("app.services.overflow_purchase_service.get_settings")
    async def test_idempotent_already_completed(self, mock_get_settings, mock_db, mock_settings):
        mock_get_settings.return_value = mock_settings
        purchase = MagicMock(spec=OverflowPurchase)
        purchase.status = OverflowPurchaseStatus.COMPLETED
        purchase.id = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = purchase
        mock_db.execute.return_value = mock_result

        from app.services.overflow_purchase_service import OverflowPurchaseService
        service = OverflowPurchaseService(mock_db)
        result = await service.handle_payment_success("cs_test_done", "pi_test_done")

        assert result == purchase
        assert result.status == OverflowPurchaseStatus.COMPLETED
