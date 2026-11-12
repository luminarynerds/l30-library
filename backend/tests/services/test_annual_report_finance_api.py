# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Director finance manual-entry endpoint (Phase 3.2)."""
from app.models.annual_report import AnnualReport, ReportStatus

API = "/api/v1/annual-reports"


def _payload(**overrides) -> dict:
    p = {
        "total_operating_revenue": "100.00",
        "revenue": {"local": 60, "state": 30, "federal": 10, "other": 0},
        "total_operating_expenditure": "100.00",
        "expenditure": {"salaries": 50, "benefits": 20, "print": 20, "electronic": 10, "other": 0},
        "capital_outlay": "5.00",
        "capital_revenue": {"local": 5, "state": 0, "federal": 0, "other": 0},
    }
    p.update(overrides)
    return p


async def _make_report(test_db) -> AnnualReport:
    report = AnnualReport(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        status=ReportStatus.GENERATED,
    )
    test_db.add(report)
    await test_db.commit()
    await test_db.refresh(report)
    return report


async def test_patch_finance_persists_and_tags_manual(staff_client, test_db, test_staff):
    report = await _make_report(test_db)

    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=_payload())
    assert resp.status_code == 200, resp.text

    await test_db.refresh(report)
    assert float(report.total_operating_revenue) == 100.0
    assert float(report.total_operating_expenditure) == 100.0
    assert report.revenue_by_source == {"local": 60, "state": 30, "federal": 10, "other": 0}
    assert report.expenditure_by_category["salaries"] == 50
    assert float(report.capital_outlay) == 5.0
    assert report.capital_revenue == {"local": 5, "state": 0, "federal": 0, "other": 0}
    # personnel = salaries + benefits; collection = print + electronic
    assert float(report.personnel_expenditure) == 70.0
    assert float(report.collection_expenditure) == 30.0
    assert report.data_sources["financial"] == "manual"
    # First-class, audited provenance columns.
    assert report.finance_source == "manual"
    assert report.finance_entered_at is not None
    assert report.finance_entered_by_id == test_staff.id


async def test_patch_finance_rejects_extra_fields(staff_client, test_db):
    report = await _make_report(test_db)
    bad = _payload()
    bad["sneaky"] = 1
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=bad)
    assert resp.status_code == 422


async def test_patch_finance_rejects_revenue_sum_mismatch(staff_client, test_db):
    report = await _make_report(test_db)
    bad = _payload(revenue={"local": 60, "state": 30, "federal": 5, "other": 0})  # 95 != 100
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=bad)
    assert resp.status_code == 422


async def test_patch_finance_rejects_expenditure_sum_mismatch(staff_client, test_db):
    report = await _make_report(test_db)
    bad = _payload(
        expenditure={"salaries": 50, "benefits": 20, "print": 20, "electronic": 5, "other": 0}  # 95 != 100
    )
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=bad)
    assert resp.status_code == 422


async def test_patch_finance_unknown_report_404(staff_client, test_db):
    resp = await staff_client.patch(f"{API}/999999/finance", json=_payload())
    assert resp.status_code == 404


async def test_patch_finance_rejects_capital_sum_mismatch(staff_client, test_db):
    report = await _make_report(test_db)
    bad = _payload(
        capital_outlay="5.00",
        capital_revenue={"local": 3, "state": 0, "federal": 0, "other": 0},  # 3 != 5
    )
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=bad)
    assert resp.status_code == 422
    assert "capital" in resp.json()["error"]["message"].lower()


async def test_patch_finance_capital_match_persists(staff_client, test_db):
    report = await _make_report(test_db)
    good = _payload(
        capital_outlay="12.00",
        capital_revenue={"local": 7, "state": 5, "federal": 0, "other": 0},  # 12 == 12
    )
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=good)
    assert resp.status_code == 200, resp.text

    await test_db.refresh(report)
    assert float(report.capital_outlay) == 12.0
    assert report.capital_revenue == {"local": 7, "state": 5, "federal": 0, "other": 0}


async def test_patch_finance_quantizes_breakdown_to_cents(staff_client, test_db):
    # Inputs with sub-cent fractions that float-drift if stored as raw float():
    # 33.333... + 33.333... + 33.334 == 100.00 within the 0.01 tolerance, but the
    # stored breakdown values must be clean 2-decimal numbers, not 33.3333333.
    report = await _make_report(test_db)
    payload = _payload(
        total_operating_revenue="100.00",
        revenue={"local": "33.335", "state": "33.335", "federal": "33.33", "other": "0"},
    )
    resp = await staff_client.patch(f"{API}/{report.id}/finance", json=payload)
    assert resp.status_code == 200, resp.text

    await test_db.refresh(report)
    rev = report.revenue_by_source
    # Each value is exact to cents (no float drift), stored as JSON numbers.
    for v in rev.values():
        assert isinstance(v, float)
        assert round(v, 2) == v
    assert rev["local"] == 33.34  # 33.335 quantizes (ROUND_HALF_EVEN) to 33.34
    assert rev["federal"] == 33.33
