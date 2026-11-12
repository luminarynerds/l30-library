# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Third-party electronic circulation manual-entry endpoint (PLS e-circ)."""
from app.models.annual_report import AnnualReport, ReportStatus

API = "/api/v1/annual-reports"

# Seed known non-zero native figures so "native preserved" assertions are not
# vacuous (native ebook = 100, total = 150 i.e. 100 elec + 50 physical native).
NATIVE_ELEC = 100
NATIVE_PHYS = 50
NATIVE_TOTAL = NATIVE_ELEC + NATIVE_PHYS  # 150


async def _make_report(test_db) -> AnnualReport:
    report = AnnualReport(
        fiscal_year=2025,
        state_code="OH",
        library_name="Little Schitt Creek Library",
        status=ReportStatus.GENERATED,
        electronic_circulation=NATIVE_ELEC,
        physical_circulation=NATIVE_PHYS,
        total_circulation=NATIVE_TOTAL,
    )
    test_db.add(report)
    await test_db.commit()
    await test_db.refresh(report)
    return report


async def test_patch_ecirc_persists_and_folds_into_pls_figures(staff_client, test_db):
    report = await _make_report(test_db)
    by_platform = {"overdrive": 1200, "hoopla": 300}
    tp = 1500

    resp = await staff_client.patch(
        f"{API}/{report.id}/electronic-circulation",
        json={"by_platform": by_platform},
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(report)
    assert report.third_party_electronic_circulation == tp
    assert report.electronic_circulation_by_platform == by_platform
    # Reported electronic = native ebook + third-party platform circulation.
    assert report.electronic_circulation == NATIVE_ELEC + tp
    # Total circulation includes the third-party amount.
    assert report.total_circulation == NATIVE_TOTAL + tp
    # Physical is untouched — third-party circulation is electronic, not physical.
    assert report.physical_circulation == NATIVE_PHYS

    body = resp.json()
    assert body["third_party_electronic_circulation"] == tp
    assert body["electronic_circulation"] == NATIVE_ELEC + tp
    assert body["total_circulation"] == NATIVE_TOTAL + tp


async def test_patch_ecirc_idempotent_on_repeat(staff_client, test_db):
    report = await _make_report(test_db)
    payload = {"by_platform": {"overdrive": 1200, "hoopla": 300}}

    r1 = await staff_client.patch(f"{API}/{report.id}/electronic-circulation", json=payload)
    assert r1.status_code == 200, r1.text
    r2 = await staff_client.patch(f"{API}/{report.id}/electronic-circulation", json=payload)
    assert r2.status_code == 200, r2.text

    await test_db.refresh(report)
    # Calling twice with the same payload yields the same totals (no double count).
    assert report.third_party_electronic_circulation == 1500
    assert report.electronic_circulation == NATIVE_ELEC + 1500
    assert report.total_circulation == NATIVE_TOTAL + 1500
    assert report.physical_circulation == NATIVE_PHYS


async def test_patch_ecirc_replaces_not_accumulates(staff_client, test_db):
    """A second PATCH with a different payload replaces rather than adds onto it."""
    report = await _make_report(test_db)

    r1 = await staff_client.patch(
        f"{API}/{report.id}/electronic-circulation",
        json={"by_platform": {"overdrive": 1200, "hoopla": 300}},  # 1500
    )
    assert r1.status_code == 200, r1.text

    r2 = await staff_client.patch(
        f"{API}/{report.id}/electronic-circulation",
        json={"by_platform": {"overdrive": 500}},  # 500
    )
    assert r2.status_code == 200, r2.text

    await test_db.refresh(report)
    assert report.third_party_electronic_circulation == 500
    assert report.electronic_circulation_by_platform == {"overdrive": 500}
    assert report.electronic_circulation == NATIVE_ELEC + 500
    assert report.total_circulation == NATIVE_TOTAL + 500


async def test_patch_ecirc_rejects_extra_fields(staff_client, test_db):
    report = await _make_report(test_db)
    resp = await staff_client.patch(
        f"{API}/{report.id}/electronic-circulation",
        json={"by_platform": {"overdrive": 100}, "sneaky": 1},
    )
    assert resp.status_code == 422


async def test_patch_ecirc_rejects_negative_count(staff_client, test_db):
    report = await _make_report(test_db)
    resp = await staff_client.patch(
        f"{API}/{report.id}/electronic-circulation",
        json={"by_platform": {"overdrive": -5}},
    )
    assert resp.status_code == 422


async def test_patch_ecirc_unknown_report_404(staff_client, test_db):
    resp = await staff_client.patch(
        f"{API}/999999/electronic-circulation",
        json={"by_platform": {"overdrive": 100}},
    )
    assert resp.status_code == 404
