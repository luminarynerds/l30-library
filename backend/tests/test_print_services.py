# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for print_cost_service and print_release_service.

Tests cover:
- Cost calculation for black & white and color printing
- Duplex / double-sided discounts
- Bulk discounts
- Minimum charge enforcement
- Print job release with payment
- Error cases: job not found, wrong owner, insufficient funds
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.print import PrintJob, PrintJobStatus, PrintPricing
from app.services import print_cost_service, print_release_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pricing(**overrides) -> MagicMock:
    """Return a MagicMock mimicking a PrintPricing row."""
    pricing = MagicMock(spec=PrintPricing)
    pricing.blackwhite_price_per_page = overrides.get(
        "bw_price", Decimal("0.10")
    )
    pricing.color_price_per_page = overrides.get(
        "color_price", Decimal("0.50")
    )
    pricing.minimum_charge = overrides.get("min_charge", Decimal("0.25"))
    pricing.double_sided_discount_percentage = overrides.get(
        "duplex_discount", 0
    )
    pricing.discount_percentage_for_bulk = overrides.get("bulk_discount", 0)
    pricing.bulk_threshold_pages = overrides.get("bulk_threshold", 100)
    return pricing


def _make_print_job(
    job_id: int = 1,
    user_id: int = 1,
    status: PrintJobStatus = PrintJobStatus.held,
    cost: Decimal = Decimal("1.00"),
    job_name: str = "test.pdf",
    **overrides,
) -> MagicMock:
    """Return a MagicMock mimicking a PrintJob row."""
    job = MagicMock(spec=PrintJob)
    job.id = job_id
    job.user_id = user_id
    job.status = status
    job.cost = cost
    job.job_name = job_name
    job.payment_method = None
    job.payment_processed = False
    job.payment_amount_charged = None
    job.account_balance_used = Decimal("0.00")
    job.release_timestamp = None
    for k, v in overrides.items():
        setattr(job, k, v)
    return job


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# print_cost_service.calculate_cost
# ===========================================================================


class TestCalculateCost:
    """Tests for print_cost_service.calculate_cost."""

    @pytest.mark.asyncio
    async def test_calculate_cost_bw_single_sided(self):
        """Black & white, single-sided (double_sided=False): simple per-page calc."""
        db = _mock_db()
        pricing = _make_pricing(bw_price=Decimal("0.10"), min_charge=Decimal("0.25"))

        with patch.object(
            print_cost_service, "get_active_pricing", return_value=pricing
        ):
            result = await print_cost_service.calculate_cost(
                db, pages=10, copies=1, color_mode="blackwhite", double_sided=False
            )

        assert result["pages"] == 10
        assert result["copies"] == 1
        assert result["color_mode"] == "blackwhite"
        assert result["double_sided"] is False
        assert result["cost_per_page"] == Decimal("0.10")
        assert result["subtotal"] == Decimal("1.00")
        assert result["discount"] == Decimal("0.00")
        assert result["total"] == Decimal("1.00")

    @pytest.mark.asyncio
    async def test_calculate_cost_color_duplex(self):
        """Color printing with duplex discount applied."""
        db = _mock_db()
        pricing = _make_pricing(
            color_price=Decimal("0.50"),
            duplex_discount=10,  # 10% discount for double-sided
            min_charge=Decimal("0.25"),
        )

        with patch.object(
            print_cost_service, "get_active_pricing", return_value=pricing
        ):
            result = await print_cost_service.calculate_cost(
                db, pages=10, copies=1, color_mode="color", double_sided=True
            )

        # subtotal = 0.50 * 10 = 5.00
        assert result["subtotal"] == Decimal("5.00")
        assert result["cost_per_page"] == Decimal("0.50")
        # discount = 5.00 * 10 / 100 = 0.50
        assert result["discount"] == Decimal("0.50")
        # total = 5.00 - 0.50 = 4.50
        assert result["total"] == Decimal("4.50")

    @pytest.mark.asyncio
    async def test_calculate_cost_with_bulk_discount(self):
        """Bulk discount kicks in when total_pages >= threshold."""
        db = _mock_db()
        pricing = _make_pricing(
            bw_price=Decimal("0.10"),
            bulk_discount=20,  # 20% bulk discount
            bulk_threshold=100,
            min_charge=Decimal("0.25"),
        )

        with patch.object(
            print_cost_service, "get_active_pricing", return_value=pricing
        ):
            result = await print_cost_service.calculate_cost(
                db, pages=50, copies=3, color_mode="blackwhite", double_sided=False
            )

        # total_pages = 50 * 3 = 150 (>= 100 threshold)
        # subtotal = 0.10 * 150 = 15.00
        assert result["subtotal"] == Decimal("15.00")
        # bulk discount = 15.00 * 20 / 100 = 3.00
        assert result["discount"] == Decimal("3.00")
        # total = 15.00 - 3.00 = 12.00
        assert result["total"] == Decimal("12.00")

    @pytest.mark.asyncio
    async def test_calculate_cost_minimum_charge(self):
        """When the computed total falls below the minimum charge, the minimum is used."""
        db = _mock_db()
        pricing = _make_pricing(
            bw_price=Decimal("0.10"),
            min_charge=Decimal("0.25"),
            duplex_discount=50,  # Very aggressive discount to force below minimum
        )

        with patch.object(
            print_cost_service, "get_active_pricing", return_value=pricing
        ):
            result = await print_cost_service.calculate_cost(
                db, pages=1, copies=1, color_mode="blackwhite", double_sided=True
            )

        # subtotal = 0.10 * 1 = 0.10
        # duplex discount = 0.10 * 50 / 100 = 0.05
        # computed total = 0.10 - 0.05 = 0.05, which is < 0.25 minimum
        assert result["total"] == Decimal("0.25")


# ===========================================================================
# print_release_service.release_job
# ===========================================================================


class TestReleaseJob:
    """Tests for print_release_service.release_job."""

    @pytest.mark.asyncio
    async def test_release_job_success(self):
        """Releasing a held job charges the account and sets status to queued."""
        db = _mock_db()
        job = _make_print_job(
            job_id=10,
            user_id=1,
            status=PrintJobStatus.held,
            cost=Decimal("2.50"),
        )

        # Mock: db.execute returns the job for the SELECT
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        # Patch account_service.charge so we don't need a real account
        with patch(
            "app.services.print_release_service.account_service.charge",
            new_callable=AsyncMock,
        ) as mock_charge:
            _ = await print_release_service.release_job(
                db, job_id=10, patron_id=1, payment_method="account_balance"
            )

        # account_service.charge should have been called with correct args
        mock_charge.assert_awaited_once_with(
            db,
            1,
            amount=Decimal("2.50"),
            description="Print job: test.pdf",
            reference_type="print_job",
            reference_id=10,
        )

        # Job should have been updated
        assert job.status == PrintJobStatus.queued
        assert job.payment_method == "account_balance"
        assert job.payment_processed is True
        assert job.payment_amount_charged == Decimal("2.50")
        assert job.release_timestamp is not None

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_release_job_not_found(self):
        """Releasing a non-existent job raises HTTP 404."""
        db = _mock_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await print_release_service.release_job(
                db, job_id=999, patron_id=1
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_release_job_wrong_owner(self):
        """If the SELECT filters by patron_id, a job owned by someone else returns None -> 404."""
        db = _mock_db()

        # The query filters by PrintJob.user_id == patron_id, so a mismatch
        # means scalar_one_or_none returns None.
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await print_release_service.release_job(
                db, job_id=10, patron_id=999  # wrong patron
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_release_job_already_completed(self):
        """Attempting to release a completed job raises HTTP 400."""
        db = _mock_db()
        job = _make_print_job(
            job_id=10,
            user_id=1,
            status=PrintJobStatus.completed,
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await print_release_service.release_job(
                db, job_id=10, patron_id=1
            )

        assert exc_info.value.status_code == 400
        assert "cannot be released" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_release_job_insufficient_funds(self):
        """When account_service.charge raises 402, release_job propagates it."""
        db = _mock_db()
        job = _make_print_job(
            job_id=10,
            user_id=1,
            status=PrintJobStatus.held,
            cost=Decimal("50.00"),
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = job
        db.execute.return_value = result_mock

        with patch(
            "app.services.print_release_service.account_service.charge",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=402, detail="Insufficient funds"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await print_release_service.release_job(
                    db, job_id=10, patron_id=1, payment_method="account_balance"
                )

        assert exc_info.value.status_code == 402
