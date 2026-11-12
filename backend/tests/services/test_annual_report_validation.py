# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PLS submission-grade validation rules (Phase 4.1)."""
from decimal import Decimal

import pytest

from app.models.annual_report import AnnualReport
from app.services.annual_report_validation import (
    ValidationError,
    sums_match,
    validate,
)


def _report(**overrides) -> AnnualReport:
    """A report that passes every rule; override one field per test to break a rule."""
    defaults = dict(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        finance_source="manual",
        total_operating_revenue=Decimal("100.00"),
        revenue_by_source={"local": 60, "state": 30, "federal": 10},
        total_operating_expenditure=Decimal("100.00"),
        expenditure_by_category={"salaries": 50, "benefits": 20, "print": 20, "electronic": 10},
        total_circulation=100,
        electronic_circulation=40,
        physical_circulation=60,
        childrens_circulation=20,
        total_program_attendance=100,
        program_attendance_by_audience={"children": 50, "adult": 50},
        total_staff_fte=Decimal("10.00"),
        librarian_fte=Decimal("4.00"),
        library_technician_fte=Decimal("3.00"),
        other_staff_fte=Decimal("3.00"),
    )
    defaults.update(overrides)
    return AnnualReport(**defaults)


def test_sums_match_within_tolerance():
    assert sums_match(Decimal("100.00"), [Decimal("60"), Decimal("40")]) is True
    assert sums_match(Decimal("100.00"), [Decimal("60"), Decimal("39.99")]) is True  # within 0.01
    assert sums_match(Decimal("100.00"), [Decimal("60"), Decimal("30")]) is False


def test_clean_report_has_no_errors():
    assert validate(_report()) == []


def test_finance_not_entered_flagged_even_when_zeroed():
    # de-fabbed report: totals default to 0, financial source not "manual"
    r = _report(
        finance_source=None,
        data_sources={"financial": "budget funds + fines"},
        total_operating_revenue=Decimal("0"),
        total_operating_expenditure=Decimal("0"),
        revenue_by_source=None,
        expenditure_by_category=None,
    )
    errs = validate(r)
    assert any(e.field == "financial" for e in errs)


def test_finance_entered_via_legacy_jsonb_tag_fallback():
    # Reports created before finance_source existed still pass via the legacy tag.
    r = _report(finance_source=None, data_sources={"financial": "manual"})
    assert not any(e.field == "financial" for e in validate(r))


def test_finance_entered_via_first_class_column_without_jsonb_tag():
    # New path: first-class column set, no legacy JSONB financial key.
    r = _report(finance_source="manual", data_sources=None)
    assert not any(e.field == "financial" for e in validate(r))


def test_childrens_circulation_cannot_exceed_total():
    errs = validate(_report(childrens_circulation=120))
    assert any(e.field == "childrens_circulation" for e in errs)


def test_electronic_plus_physical_must_equal_total_circulation():
    errs = validate(_report(electronic_circulation=40, physical_circulation=50))  # 90 != 100
    assert any(e.field == "circulation_split" for e in errs)


def test_audience_attendance_must_sum_to_total():
    errs = validate(_report(program_attendance_by_audience={"children": 50, "adult": 30}))  # 80 != 100
    assert any(e.field == "program_attendance_by_audience" for e in errs)


def test_revenue_lines_must_match_total():
    errs = validate(_report(revenue_by_source={"local": 60, "state": 30}))  # 90 != 100
    assert any(e.field == "revenue_by_source" for e in errs)


def test_fte_components_must_match_total():
    errs = validate(_report(other_staff_fte=Decimal("1.00")))  # 4+3+1=8 != 10
    assert any(e.field == "total_staff_fte" for e in errs)


def test_capital_revenue_must_match_capital_outlay():
    errs = validate(_report(
        capital_outlay=Decimal("10.00"),
        capital_revenue={"local": 4, "state": 0, "federal": 0, "other": 0},  # 4 != 10
    ))
    assert any(e.field == "capital_revenue" for e in errs)


def test_capital_revenue_matching_outlay_passes():
    errs = validate(_report(
        capital_outlay=Decimal("10.00"),
        capital_revenue={"local": 6, "state": 4, "federal": 0, "other": 0},  # 10 == 10
    ))
    assert not any(e.field == "capital_revenue" for e in errs)


def test_capital_rule_skipped_when_outlay_absent():
    # capital_revenue present but no outlay: rule must NOT fire (fires only when both present).
    errs = validate(_report(
        capital_outlay=None,
        capital_revenue={"local": 4, "state": 0, "federal": 0, "other": 0},
    ))
    assert not any(e.field == "capital_revenue" for e in errs)


def test_validation_error_serializes():
    e = ValidationError(field="financial", message="not entered")
    assert e.to_dict() == {"field": "financial", "message": "not entered"}


def test_none_inputs_skip_arithmetic_rules_but_not_completeness():
    # Fully empty auto report: only completeness should fire, no crashes.
    r = _report(
        finance_source=None,
        data_sources=None,
        total_operating_revenue=None,
        revenue_by_source=None,
        expenditure_by_category=None,
        total_circulation=None,
        electronic_circulation=None,
        physical_circulation=None,
        childrens_circulation=None,
        total_program_attendance=None,
        program_attendance_by_audience=None,
        total_staff_fte=None,
        librarian_fte=None,
        library_technician_fte=None,
        other_staff_fte=None,
    )
    errs = validate(r)
    assert [e.field for e in errs] == ["financial"]
