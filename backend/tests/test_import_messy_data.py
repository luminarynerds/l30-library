# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Messy-data import stress harness.

Drives realistic legacy-ILS dirty data through the real ImportService pipeline
and records where it breaks.
"""

import os

import pytest

from tests.test_data.messy.manifest import load_manifest, RowSpec
from app.services.import_service import ImportJobType

MESSY_DIR = os.path.dirname(__file__) + "/test_data/messy"


def test_manifest_loader_roundtrip(tmp_path):
    import json

    p = tmp_path / "m.manifest.json"
    p.write_text(
        json.dumps(
            {
                "job_type": "patrons",
                "rows": [
                    {"row": 1, "defect_class": "valid", "expected_outcome": "valid"},
                    {"row": 2, "defect_class": "empty_required_email", "expected_outcome": "error"},
                ],
            }
        )
    )
    m = load_manifest(str(p))
    assert m.job_type == "patrons"
    assert len(m.rows) == 2
    assert isinstance(m.rows[0], RowSpec)
    assert m.rows[0].expected_outcome == "valid"
    assert m.rows[1].defect_class == "empty_required_email"
    assert m.expected_for(2) == "error"


def test_manifest_loader_rejects_invalid_outcome(tmp_path):
    import json

    p = tmp_path / "bad.manifest.json"
    p.write_text(
        json.dumps(
            {
                "job_type": "patrons",
                "rows": [{"row": 1, "defect_class": "x", "expected_outcome": "NOPE"}],
            }
        )
    )
    try:
        load_manifest(str(p))
    except AssertionError as e:
        assert "NOPE" in str(e)
    else:
        raise AssertionError("expected load_manifest to reject invalid outcome")


def test_generator_is_deterministic():
    """Re-running the generator must produce byte-identical committed files."""
    import glob
    import filecmp
    import tempfile

    from tests.test_data.messy import generate as gen

    committed = {
        os.path.basename(p): p
        for p in glob.glob(os.path.join(MESSY_DIR, "messy_*"))
        if p.endswith((".csv", ".manifest.json"))
    }
    assert committed, "no committed fixtures found; run the generator first"

    with tempfile.TemporaryDirectory() as tmp:
        orig_here = gen.HERE
        try:
            gen.HERE = tmp
            gen.generate_all()
        finally:
            gen.HERE = orig_here

        for name, committed_path in committed.items():
            fresh_path = os.path.join(tmp, name)
            assert os.path.exists(fresh_path), f"generator did not emit {name}"
            assert filecmp.cmp(committed_path, fresh_path, shallow=False), (
                f"{name} differs from committed copy — regenerate and commit"
            )


def _read(name: str) -> bytes:
    with open(os.path.join(MESSY_DIR, name), "rb") as f:
        return f.read()


def _assert_known_good_survived(results):
    """Every manifest row whose expected outcome is 'valid' must be observed
    as 'valid' (created/updated). This is the harness's hard guarantee: it can
    tell good rows from bad. Mismatches on non-'valid' rows are findings, not
    harness failures, and are captured in the report."""
    for r in results:
        if r.expected == "valid":
            assert r.observed == "valid", (
                f"known-good row {r.row} of {r.file} did not survive: "
                f"observed={r.observed} status={r.record_status} detail={r.detail}"
            )


@pytest.mark.asyncio
async def test_messy_patrons(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_patrons.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_patrons.csv"),
        filename="messy_patrons.csv",
        job_type=ImportJobType.PATRONS,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


@pytest.mark.asyncio
async def test_messy_catalog(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_catalog.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_catalog.csv"),
        filename="messy_catalog.csv",
        job_type=ImportJobType.CATALOG_ITEMS,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


async def _seed_patron(db, barcode: str):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email=f"{barcode.lower()}@seed.example.com",
        password_hash=hash_password("SeedPassword123!"),
        first_name="Seed",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card=barcode,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_catalog_item(db, *, title="Seed Book", isbn=None):
    from app.models.catalog import CatalogItem, ItemStatus, CatalogingStatus

    item = CatalogItem(
        title=title,
        author="Seed Author",
        isbn=isbn,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _seed_item_copy(db, *, catalog_item_id, barcode, copy_number=1):
    from app.models.inventory import ItemCopy

    copy = ItemCopy(
        catalog_item_id=catalog_item_id,
        barcode=barcode,
        copy_number=copy_number,
        condition="good",
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return copy


async def _ensure_system_settings(db):
    """Seed a LibrarySystem + its SystemSettings row.

    circulation_policy.resolve() (reached when a circ row has no explicit
    due_date) raises RuntimeError if no system_settings row exists. Prod always
    has one; the empty test DB does not. This is harness setup, not a bug.

    get_default_library_system_id returns None on an empty DB (it does NOT
    auto-create), so we create the LibrarySystem first when absent.
    """
    from app.services.setup_service import get_default_library_system_id
    from app.models.multi_branch import LibrarySystem, SystemSettings
    from sqlalchemy import select

    sys_id = await get_default_library_system_id(db)
    if sys_id is None:
        ls = LibrarySystem(
            name="Harness Test Library",
            code="HARN",
            is_active=True,
        )
        db.add(ls)
        await db.commit()
        await db.refresh(ls)
        sys_id = ls.id

    existing = await db.execute(
        select(SystemSettings.library_system_id).where(SystemSettings.library_system_id == sys_id)
    )
    if existing.scalar_one_or_none() is None:
        db.add(SystemSettings(library_system_id=sys_id))
        await db.commit()
    return sys_id


@pytest.mark.asyncio
async def test_messy_holdings(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    parent = await _seed_catalog_item(test_db, title="Holdings Parent")
    raw = _read("messy_holdings.csv").decode("utf-8")
    content = raw.replace("__CATALOG_ID__", str(parent.id)).encode("utf-8")

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_holdings.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=content,
        filename="messy_holdings.csv",
        job_type=ImportJobType.HOLDINGS,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


@pytest.mark.asyncio
async def test_messy_holdings_orphan_crash(test_db):
    """Holdings with a numeric-but-nonexistent catalog_id: characterize whether
    the job crashes (uncaught IntegrityError) or fails the row gracefully."""
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_holdings_orphan.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_holdings_orphan.csv"),
        filename="messy_holdings_orphan.csv",
        job_type=ImportJobType.HOLDINGS,
        manifest=manifest,
        expect_crash=True,
    )
    # Document whichever happened; both are valuable signal.
    assert results[0].observed in {"orphan_fk", "valid", "error"}


@pytest.mark.asyncio
async def test_messy_circulation(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    await _ensure_system_settings(test_db)
    await _seed_patron(test_db, "L30-CIRC-0001")
    parent = await _seed_catalog_item(test_db, title="Circ Parent")
    await _seed_item_copy(test_db, catalog_item_id=parent.id, barcode="COPY-CIRC-001")

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_circulation.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_circulation.csv"),
        filename="messy_circulation.csv",
        job_type=ImportJobType.CIRCULATION_HISTORY,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


@pytest.mark.asyncio
async def test_messy_circulation_orphan(test_db):
    """Circ orphans raise ValueError -> caught -> FAILED (graceful, no crash)."""
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    await _ensure_system_settings(test_db)
    await _seed_patron(test_db, "L30-CIRC-0001")
    parent = await _seed_catalog_item(test_db, title="Circ Parent")
    await _seed_item_copy(test_db, catalog_item_id=parent.id, barcode="COPY-CIRC-001")

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_circulation_orphan.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_circulation_orphan.csv"),
        filename="messy_circulation_orphan.csv",
        job_type=ImportJobType.CIRCULATION_HISTORY,
        manifest=manifest,
    )
    # Orphan rows should be FAILED (observed "error"), not crash the job.
    for r in results:
        assert r.observed in {"error", "orphan_fk"}, (
            f"circ orphan row {r.row} unexpectedly observed {r.observed}"
        )


@pytest.mark.asyncio
async def test_messy_fines(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    await _seed_patron(test_db, "L30-FINE-0001")

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_fines.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_fines.csv"),
        filename="messy_fines.csv",
        job_type=ImportJobType.FINES,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


@pytest.mark.asyncio
async def test_messy_holds(test_db):
    from tests.test_data.messy.harness import drive_pipeline
    from tests.test_data.messy.manifest import load_manifest

    await _seed_patron(test_db, "L30-HOLD-0001")
    await _seed_catalog_item(test_db, title="The Great Gatsby", isbn="9780743273565")

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_holds.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_holds.csv"),
        filename="messy_holds.csv",
        job_type=ImportJobType.HOLDS,
        manifest=manifest,
    )
    _assert_known_good_survived(results)


# -- Characterization tests for the three headline hypotheses --------------
# These encode CURRENT behavior (confirmed empirically). Green now; turn RED
# if the pipeline's handling changes -- at which point update the report
# narrative.


def test_hypothesis_ambiguous_date_parses_us_style():
    """02/03/2024 is ambiguous. _parse_date tries %m/%d/%Y before %d/%m/%Y,
    so it silently resolves to Feb 3 (US), never Mar 2 (EU). Documents the
    silent-coercion risk for any library whose legacy data is DD/MM/YYYY."""
    from app.services.import_service import _parse_date
    from tests.test_data.messy.harness import OUTCOMES

    result = _parse_date("02/03/2024")
    assert result is not None
    is_us = result.month == 2 and result.day == 3
    OUTCOMES.append(
        {
            "job_type": "circulation_history",
            "file": "(unit)",
            "row": 0,
            "defect_class": "ambiguous_date",
            "expected": "us_or_flagged",
            "observed": "us_silent" if is_us else "other",
            "record_status": None,
            "matched": False,
            "detail": f"02/03/2024 -> {result.date().isoformat()} (US-style, no warning)",
        }
    )
    assert is_us, "behavior changed -- update the report narrative"


@pytest.mark.asyncio
async def test_hypothesis_near_duplicate_catalog_detected(test_db):
    """Row 7 of messy_catalog (same title, author missing a period) -- record
    whether the title-exact + fuzzy-author check catches it as a duplicate."""
    from tests.test_data.messy.harness import drive_pipeline, OUTCOMES
    from tests.test_data.messy.manifest import load_manifest

    manifest = load_manifest(os.path.join(MESSY_DIR, "messy_catalog.manifest.json"))
    results = await drive_pipeline(
        test_db,
        file_content=_read("messy_catalog.csv"),
        filename="messy_catalog.csv",
        job_type=ImportJobType.CATALOG_ITEMS,
        manifest=manifest,
    )
    near_dup = next(r for r in results if r.row == 7)
    OUTCOMES.append(
        {
            "job_type": "catalog_items",
            "file": "(hypothesis)",
            "row": 7,
            "defect_class": "near_duplicate_title_author",
            "expected": "duplicate",
            "observed": near_dup.observed,
            "record_status": near_dup.record_status,
            "matched": near_dup.observed == "duplicate",
            "detail": "near-dup detection verdict",
        }
    )
    # Record-only: whether caught or not is a headline finding, not a hard fail.
    assert near_dup.observed in {"duplicate", "valid"}


@pytest.mark.asyncio
async def test_hypothesis_holdings_orphan_graceful(test_db):
    """The holdings orphan path used to raise an uncaught IntegrityError
    instead of landing the row in FAILED (the spec's central
    'narrow-except' constraint). That's been fixed -- narrative updated per
    this test's own former assertion message: the row now fails gracefully
    (ImportRecordStatus.FAILED) without crashing the whole job, matching
    test_messy_circulation_orphan's orphan-FK handling and the report
    classifier's `exp == "orphan_fk" and obs == "error"` -> "ok" rule."""
    import sqlalchemy.exc
    from sqlalchemy import select
    from app.models.import_job import ImportJobType as JT, ImportRecord, ImportRecordStatus
    from app.services.import_service import ImportService, DuplicateAction
    from tests.test_data.messy.harness import OUTCOMES, _ensure_creator

    content = _read("messy_holdings_orphan.csv")
    creator_id = await _ensure_creator(test_db)
    job = await ImportService.upload(
        db=test_db,
        file_content=content,
        filename="messy_holdings_orphan.csv",
        job_type=JT.HOLDINGS,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=creator_id,
    )
    job = await ImportService.validate(test_db, job)
    crashed = False
    detail = ""
    try:
        job = await ImportService.execute(test_db, job)
    except sqlalchemy.exc.IntegrityError as exc:
        crashed = True
        detail = f"IntegrityError: {str(exc).splitlines()[0]}"
        await test_db.rollback()
    except Exception as exc:  # noqa: BLE001
        detail = f"unexpected {type(exc).__name__}: {exc}"
        await test_db.rollback()

    record_status = None
    if not crashed:
        recs = (
            (
                await test_db.execute(
                    select(ImportRecord)
                    .where(ImportRecord.import_job_id == job.id)
                    .order_by(ImportRecord.row_number)
                )
            )
            .scalars()
            .all()
        )
        record_status = recs[0].status if recs else None

    OUTCOMES.append(
        {
            "job_type": "holdings",
            "file": "(hypothesis)",
            "row": 1,
            "defect_class": "orphan_catalog_id",
            "expected": "orphan_fk",
            "observed": "crash" if crashed else "error",
            "record_status": record_status,
            "matched": not crashed,
            "detail": detail,
        }
    )
    assert not crashed, f"holdings orphan crashed the job: {detail}"
    assert record_status == ImportRecordStatus.FAILED, (
        f"orphan holdings row should FAIL gracefully; got {record_status}"
    )


@pytest.fixture(scope="session", autouse=True)
def _write_messy_report():
    """After the whole module runs, drain OUTCOMES into report.md + report.json.

    Classification per row:
      - ok      : observed matched the manifest expectation.
      - SILENT  : observed 'valid' but the manifest expected a problem ->
                  SILENTLY ACCEPTED bad data (the dangerous case).
      - CRASH   : observed crash/orphan_fk where a graceful result was wanted.
      - MISMATCH: any other expected/observed divergence worth a human look.
    """
    yield
    import json
    from tests.test_data.messy.harness import OUTCOMES

    if not OUTCOMES:
        return

    def classify(o):
        exp, obs = o["expected"], o["observed"]
        if o.get("matched"):
            return "ok"
        # An orphan-FK row that lands in "error" (row FAILED gracefully) is the
        # DESIRED outcome, not a divergence — contrast the holdings orphan which
        # crashes the whole job. Treat graceful orphan handling as ok.
        if exp == "orphan_fk" and obs == "error":
            return "ok"
        if obs == "valid" and exp in {"error", "duplicate", "orphan_fk"}:
            return "SILENT"
        if obs in {"crash", "orphan_fk"} and exp not in {"orphan_fk"}:
            return "CRASH"
        return "MISMATCH"

    # Dedup: some hypothesis tests re-drive a file already covered by a job-type
    # test, so identical row verdicts can appear twice in OUTCOMES.
    seen = set()
    rows = []
    for o in OUTCOMES:
        key = (o["job_type"], o["file"], o["row"], o["defect_class"], o["expected"], o["observed"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(o)
    for o in rows:
        o["classification"] = classify(o)

    counts = {}
    for o in rows:
        counts[o["classification"]] = counts.get(o["classification"], 0) + 1

    json_path = os.path.join(MESSY_DIR, "report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": counts, "rows": rows}, f, indent=2, ensure_ascii=False)
        f.write(chr(10))

    lines = ["# Messy-Data Import -- Where It Breaks", ""]
    lines.append(
        "Generated by `tests/test_import_messy_data.py`. "
        "Each row is one seeded defect driven through the real pipeline."
    )
    lines.append("")
    lines.append("## Summary")
    for k in ("ok", "SILENT", "CRASH", "MISMATCH"):
        if k in counts:
            lines.append(f"- **{k}**: {counts[k]}")
    lines.append("")
    lines.append("## Findings (non-OK rows)")
    lines.append("")
    lines.append("| class | type | file | row | defect | expected | observed | detail |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for o in rows:
        if o["classification"] == "ok":
            continue
        detail = (o.get("detail") or "").replace("|", chr(92) + "|")[:120]
        lines.append(
            f"| {o['classification']} | {o['job_type']} | {o['file']} | "
            f"{o['row']} | {o['defect_class']} | {o['expected']} | "
            f"{o['observed']} | {detail} |"
        )
    md_path = os.path.join(MESSY_DIR, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(chr(10).join(lines) + chr(10))


async def _seed_staff(db, email):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    staff = User(
        email=email,
        password_hash=hash_password("StaffPass123!"),
        first_name="Imp",
        last_name="Orter",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(staff)
    await db.flush()
    return staff.id


@pytest.mark.asyncio
async def test_circ_import_two_copies_same_title_both_active_import(test_db):
    """Two ACTIVE checkouts of two DIFFERENT copies of the same title must BOTH
    import (#1427).

    Circulation uniqueness is per physical copy (ix_active_item_copy_checkout);
    the old title-level index ix_active_item_checkout was dropped 2026-06-09.
    This is the realistic multi-copy case: two copies of one popular title both
    out to (here) the same patron in the source ILS — the importer preserves the
    source system's historical truth.
    """
    from sqlalchemy import select

    from app.models.import_job import ImportRecord, ImportRecordStatus
    from app.services.import_service import (
        ImportService,
        ImportJobType,
        DuplicateAction,
    )

    await _ensure_system_settings(test_db)
    await _seed_patron(test_db, "L30-DUP-0001")
    parent = await _seed_catalog_item(test_db, title="Popular Title")
    await _seed_item_copy(test_db, catalog_item_id=parent.id, barcode="COPY-DUP-001", copy_number=1)
    await _seed_item_copy(test_db, catalog_item_id=parent.id, barcode="COPY-DUP-002", copy_number=2)
    importer_id = await _seed_staff(test_db, "dup-importer@seed.example.com")

    csv_content = (
        "patron_barcode,item_barcode,checkout_date,return_date\n"
        "L30-DUP-0001,COPY-DUP-001,2024-01-15,\n"
        "L30-DUP-0001,COPY-DUP-002,2024-01-16,\n"
    ).encode("utf-8")

    job = await ImportService.upload(
        db=test_db,
        file_content=csv_content,
        filename="dup_active.csv",
        job_type=ImportJobType.CIRCULATION_HISTORY,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=importer_id,
    )
    job = await ImportService.validate(test_db, job)
    job = await ImportService.execute(test_db, job)

    recs = (
        (
            await test_db.execute(
                select(ImportRecord)
                .where(ImportRecord.import_job_id == job.id)
                .order_by(ImportRecord.row_number)
            )
        )
        .scalars()
        .all()
    )
    status_by_row = {r.row_number: r.status for r in recs}

    assert status_by_row.get(1) == ImportRecordStatus.CREATED, (
        f"first copy's active checkout should import; got {status_by_row.get(1)}"
    )
    assert status_by_row.get(2) == ImportRecordStatus.CREATED, (
        f"second copy's active checkout should ALSO import — uniqueness is "
        f"per-copy, not per-title (#1427); got {status_by_row.get(2)}"
    )


@pytest.mark.asyncio
async def test_circ_import_same_copy_twice_active_fails_gracefully(test_db):
    """Two ACTIVE checkouts of the SAME physical copy must not crash the job.

    ix_active_item_copy_checkout is UNIQUE on item_copy_id WHERE
    status='active'. A second active checkout of one copy would raise an
    uncaught IntegrityError and poison the batch; the importer must reject
    that row (FAILED) and continue.
    """
    from sqlalchemy import select

    from app.models.import_job import ImportRecord, ImportRecordStatus
    from app.services.import_service import (
        ImportService,
        ImportJobType,
        DuplicateAction,
    )

    await _ensure_system_settings(test_db)
    await _seed_patron(test_db, "L30-DUP-0002")
    await _seed_patron(test_db, "L30-DUP-0003")
    parent = await _seed_catalog_item(test_db, title="Single Copy Title")
    await _seed_item_copy(test_db, catalog_item_id=parent.id, barcode="COPY-DUP-010", copy_number=1)
    importer_id = await _seed_staff(test_db, "dup-copy-importer@seed.example.com")

    csv_content = (
        "patron_barcode,item_barcode,checkout_date,return_date\n"
        "L30-DUP-0002,COPY-DUP-010,2024-01-15,\n"
        "L30-DUP-0003,COPY-DUP-010,2024-01-16,\n"
    ).encode("utf-8")

    job = await ImportService.upload(
        db=test_db,
        file_content=csv_content,
        filename="dup_copy_active.csv",
        job_type=ImportJobType.CIRCULATION_HISTORY,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=importer_id,
    )
    job = await ImportService.validate(test_db, job)
    # Must NOT raise. A whole-job crash here is the bug under test.
    job = await ImportService.execute(test_db, job)

    recs = (
        (
            await test_db.execute(
                select(ImportRecord)
                .where(ImportRecord.import_job_id == job.id)
                .order_by(ImportRecord.row_number)
            )
        )
        .scalars()
        .all()
    )
    status_by_row = {r.row_number: r.status for r in recs}

    assert status_by_row.get(1) == ImportRecordStatus.CREATED, (
        f"first active checkout of the copy should import; got {status_by_row.get(1)}"
    )
    assert status_by_row.get(2) == ImportRecordStatus.FAILED, (
        f"second active checkout of the SAME copy should FAIL gracefully, not "
        f"crash the job; got {status_by_row.get(2)}"
    )
