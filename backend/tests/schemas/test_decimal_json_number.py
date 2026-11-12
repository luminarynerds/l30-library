# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""TDD: Decimal fields in Pydantic schemas must serialize as JSON numbers, not strings.

Phase 1 (mechanism) — no app imports, tests the _base.py MoneyDecimal type alias
in complete isolation so these run even if the branding/DB import chain is broken.

Phase 2 (real schemas) — imports actual money schemas. Requires branding fix + DB env.
Marked with @pytest.mark.integration so they can be skipped in CI if needed.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Annotated, Optional

import pytest
from pydantic import BaseModel, PlainSerializer


# ---------------------------------------------------------------------------
# Phase 1: mechanism in complete isolation (no app imports)
# ---------------------------------------------------------------------------

_MoneyDecimal = Annotated[Decimal, PlainSerializer(float, when_used="json")]


class _MoneyModel(BaseModel):
    amount: _MoneyDecimal
    optional_amount: Optional[_MoneyDecimal] = None


class TestMoneyDecimalMechanism:
    """Verify the Annotated[Decimal, PlainSerializer] mechanism works as expected."""

    def test_decimal_serializes_as_number_not_string(self):
        m = _MoneyModel(amount=Decimal("12.50"))
        data = json.loads(m.model_dump_json())
        assert isinstance(data["amount"], float), (
            f"Expected float, got {type(data['amount']).__name__}: {data['amount']!r}"
        )

    def test_decimal_value_preserved(self):
        m = _MoneyModel(amount=Decimal("12.50"))
        data = json.loads(m.model_dump_json())
        assert data["amount"] == pytest.approx(12.5)

    def test_python_side_stays_decimal(self):
        m = _MoneyModel(amount=Decimal("12.50"))
        assert isinstance(m.amount, Decimal)
        assert m.amount == Decimal("12.50")

    def test_none_serializes_as_null(self):
        m = _MoneyModel(amount=Decimal("1.00"), optional_amount=None)
        data = json.loads(m.model_dump_json())
        assert data["optional_amount"] is None

    def test_optional_with_value_serializes_as_number(self):
        m = _MoneyModel(amount=Decimal("5.00"), optional_amount=Decimal("2.50"))
        data = json.loads(m.model_dump_json())
        assert isinstance(data["optional_amount"], float)
        assert data["optional_amount"] == pytest.approx(2.5)

    def test_dict_mode_stays_decimal(self):
        """model_dump() (non-JSON) must keep Decimal for Python-side math."""
        m = _MoneyModel(amount=Decimal("5.00"))
        data = m.model_dump()
        assert isinstance(data["amount"], Decimal)

    def test_accepts_string_input(self):
        """Validation still accepts string "10.00" from incoming JSON."""
        m = _MoneyModel.model_validate({"amount": "10.00"})
        assert m.amount == Decimal("10.00")

    def test_accepts_int_input(self):
        m = _MoneyModel.model_validate({"amount": 5})
        assert m.amount == Decimal("5")

    def test_zero_serializes_as_zero_float(self):
        m = _MoneyModel(amount=Decimal("0.00"))
        data = json.loads(m.model_dump_json())
        assert data["amount"] == 0.0
        assert isinstance(data["amount"], float)


# ---------------------------------------------------------------------------
# Phase 2: real schema classes (requires working import chain)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRealSchemaDecimalAsNumber:
    """Spot-check actual money schemas emit numbers, not strings, in JSON."""

    def test_fine_base_amount_is_number(self):
        from app.schemas.fine import FineBase

        m = FineBase(amount=Decimal("5.00"))
        data = json.loads(m.model_dump_json())
        assert isinstance(data["amount"], (int, float)), (
            f"FineBase.amount serialized as {type(data['amount']).__name__}: {data['amount']!r}"
        )

    def test_fine_waiver_response_amounts_are_numbers(self):
        from datetime import datetime
        from app.schemas.fine import FineWaiverResponse
        from app.models.fine_waiver import FineWaiverStatus

        m = FineWaiverResponse(
            waiver_id=1,
            fine_id=1,
            amount_waived=Decimal("3.50"),
            remaining_balance=Decimal("1.50"),
            status=FineWaiverStatus.waived,
            waived_by=None,
            waived_at=None,
            reason="test",
        )
        data = json.loads(m.model_dump_json())
        assert isinstance(data["amount_waived"], (int, float))
        assert isinstance(data["remaining_balance"], (int, float))

    def test_fund_response_amounts_are_numbers(self):
        from app.schemas.acquisition import FundResponse
        from app.models.acquisition import FundStatus

        m = FundResponse(
            id=1,
            code="TEST",
            name="Test Fund",
            status=FundStatus.ACTIVE,
            fiscal_year=2026,
            allocated_amount=Decimal("1000.00"),
            encumbered_amount=Decimal("200.00"),
            spent_amount=Decimal("150.00"),
            available_amount=Decimal("650.00"),
        )
        data = json.loads(m.model_dump_json())
        for field in ("allocated_amount", "encumbered_amount", "spent_amount", "available_amount"):
            assert isinstance(data[field], (int, float)), (
                f"FundResponse.{field} serialized as {type(data[field]).__name__}: {data[field]!r}"
            )
