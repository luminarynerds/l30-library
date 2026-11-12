# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconciliation endpoint (Phase 4.2): stored snapshot vs live source, with drift."""
from datetime import date

import pytest

from app.models.annual_report import AnnualReport, ReportStatus

API = "/api/v1/annual-reports"


async def test_reconciliation_reports_drift_vs_live_source(staff_client, test_db):
    from app.models.usage_statistics import VisitStatistics

    # Live source now shows 12 visits; the report was generated with a snapshot of 10.
    test_db.add(
        VisitStatistics(
            period_start=date(2024, 7, 1),
            period_end=date(2025, 6, 30),
            period_type="annual",
            total_visits=12,
        )
    )
    report = AnnualReport(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        status=ReportStatus.GENERATED,
        total_library_visits=10,
    )
    test_db.add(report)
    await test_db.commit()
    await test_db.refresh(report)

    resp = await staff_client.get(f"{API}/{report.id}/reconciliation")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    fields = {f["field"]: f for f in body["fields"]}
    visits = fields["total_library_visits"]
    assert visits["report_value"] == 10
    assert visits["live_source_value"] == 12
    assert visits["drift"] == 2


async def test_reconciliation_unknown_report_404(staff_client, test_db):
    resp = await staff_client.get(f"{API}/999999/reconciliation")
    assert resp.status_code == 404


async def test_reconciliation_healthy_path_on_postgres(staff_client, test_db):
    """Exercise the healthy-Postgres reconciliation path.

    The handler's per-section ``await db.rollback()`` exists to recover from a
    SQLite-only COALESCE-enum poison cascade; on Postgres there is no poison, so
    the recovery branch runs cleanly. The SQLite-fallback test above never proves
    the endpoint works on real Postgres. This test skips off Postgres and, when
    run against l30_test, confirms every reconcilable section computes and the
    rollbacks leave the session usable.
    """
    if test_db.bind.dialect.name != "postgresql":
        pytest.skip("Postgres-only: exercises the healthy-PG reconciliation path")

    from app.models.usage_statistics import VisitStatistics

    test_db.add(
        VisitStatistics(
            period_start=date(2024, 7, 1),
            period_end=date(2025, 6, 30),
            period_type="annual",
            total_visits=42,
        )
    )
    report = AnnualReport(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        status=ReportStatus.GENERATED,
        total_library_visits=40,
    )
    test_db.add(report)
    await test_db.commit()
    await test_db.refresh(report)

    resp = await staff_client.get(f"{API}/{report.id}/reconciliation")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    field_names = {f["field"] for f in body["fields"]}
    # All reconcilable sections (circulation, program, visits) ran without the
    # rollback leaving the session poisoned.
    assert "total_library_visits" in field_names
    assert "total_circulation" in field_names
    visits = next(f for f in body["fields"] if f["field"] == "total_library_visits")
    assert visits["report_value"] == 40
    assert visits["live_source_value"] == 42
    assert visits["drift"] == 2
