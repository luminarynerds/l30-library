# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Certification gate (Phase 4.3): certify is blocked until PLS validation passes."""
from decimal import Decimal

from app.models.annual_report import AnnualReport, ReportStatus

API = "/api/v1/annual-reports"


async def _make_report(test_db, **overrides) -> AnnualReport:
    defaults = dict(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        status=ReportStatus.GENERATED,
    )
    defaults.update(overrides)
    report = AnnualReport(**defaults)
    test_db.add(report)
    await test_db.commit()
    await test_db.refresh(report)
    return report


async def _make_valid_report(test_db) -> AnnualReport:
    return await _make_report(
        test_db,
        data_sources={"financial": "manual"},
        total_operating_revenue=Decimal("100"),
        revenue_by_source={"local": 60, "state": 30, "federal": 10},
        total_circulation=100,
        electronic_circulation=40,
        physical_circulation=60,
        childrens_circulation=20,
        total_program_attendance=100,
        program_attendance_by_audience={"children": 50, "adult": 50},
        total_staff_fte=Decimal("10"),
        librarian_fte=Decimal("4"),
        library_technician_fte=Decimal("3"),
        other_staff_fte=Decimal("3"),
    )


async def test_certify_blocked_while_validation_fails(staff_client, test_db):
    report = await _make_report(test_db)  # finance not entered -> invalid

    resp = await staff_client.post(f"{API}/{report.id}/certify")
    assert resp.status_code == 409, resp.text
    # App reshapes HTTPException to {"error": {"code", "message": <detail>, ...}}.
    body = resp.json()
    assert body["error"]["message"]["error_count"] >= 1

    await test_db.refresh(report)
    assert _status_value(report.status) == "generated"
    assert report.is_validated is False


async def test_certify_succeeds_when_valid(staff_client, test_db, test_staff):
    report = await _make_valid_report(test_db)

    resp = await staff_client.post(f"{API}/{report.id}/certify")
    assert resp.status_code == 200, resp.text

    await test_db.refresh(report)
    assert _status_value(report.status) == "validated"
    assert report.is_validated is True
    assert report.validated_by_id == test_staff.id
    assert report.validated_at is not None


async def test_certify_unknown_report_404(staff_client, test_db):
    resp = await staff_client.post(f"{API}/999999/certify")
    assert resp.status_code == 404


def _status_value(s) -> str:
    return s.value if hasattr(s, "value") else str(s)
