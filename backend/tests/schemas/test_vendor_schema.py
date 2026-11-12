# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Vendor schemas — code/website/discount_percentage fields.

Regression for the acquisition vendor create form, which collected these fields
in the frontend but had no backend column or schema field, so every create POST
422'd on the strict (extra="forbid") VendorCreate schema.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.acquisition import VendorCreate, VendorResponse, VendorUpdate


class TestVendorCreateFields:
    def test_accepts_code_website_discount(self):
        v = VendorCreate(
            name="Acme",
            code="ACME01",
            website="https://acme.example",
            discount_percentage=12.5,
        )
        assert v.code == "ACME01"
        assert v.website == "https://acme.example"
        assert v.discount_percentage == Decimal("12.5")

    def test_new_fields_optional(self):
        v = VendorCreate(name="Acme")
        assert v.code is None
        assert v.website is None
        assert v.discount_percentage is None

    def test_still_rejects_unknown_field(self):
        with pytest.raises(ValidationError):
            VendorCreate(name="Acme", bogus_field="x")


class TestVendorUpdateFields:
    def test_accepts_new_fields(self):
        v = VendorUpdate(code="C2", website="https://x.example", discount_percentage=5)
        assert v.code == "C2"
        assert v.website == "https://x.example"
        assert v.discount_percentage == Decimal("5")


class TestVendorResponseFields:
    def test_exposes_new_fields(self):
        for field in ("code", "website", "discount_percentage"):
            assert field in VendorResponse.model_fields
