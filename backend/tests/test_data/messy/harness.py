# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Driver + outcome collector for the messy-data import harness.

drive_pipeline() runs upload -> validate -> dry_run -> execute -> rollback for
one dirty file and returns a per-row result list reconciled against the
manifest. Every reconciled row is also appended to the module-level OUTCOMES
collector, which the report fixture drains at session end.
"""

from dataclasses import dataclass, asdict
from typing import Optional

from sqlalchemy import select

from app.models.import_job import ImportRecord, ImportRecordStatus
from app.services.import_service import ImportService, DuplicateAction

# Module-level collector. Tests append; the report fixture reads + clears.
OUTCOMES: list[dict] = []

# Distinct so it never collides with fixture patron emails (no false dup).
_CREATOR_EMAIL = "_harness_import_creator@seed.invalid"

# Map a post-pipeline ImportRecord.status to a coarse observed outcome bucket
# comparable with manifest expected_outcome values. (The enum has no ERROR;
# validation rejects bad rows as INVALID, execute failures land in FAILED.)
_STATUS_TO_OUTCOME = {
    ImportRecordStatus.CREATED: "valid",
    ImportRecordStatus.UPDATED: "valid",
    ImportRecordStatus.WARNING: "valid",   # warning rows still import
    ImportRecordStatus.VALID: "valid",
    ImportRecordStatus.SKIPPED: "duplicate",
    ImportRecordStatus.INVALID: "error",   # validation rejected the row
    ImportRecordStatus.FAILED: "error",    # creation raised during execute
}


@dataclass
class RowResult:
    job_type: str
    file: str
    row: int
    defect_class: str
    expected: str
    observed: str
    record_status: Optional[str]
    matched: bool
    detail: str


async def _ensure_creator(db) -> int:
    """Return the id of a staff user to own import jobs, creating it if absent.

    ImportJob.created_by_id is a FK to users.id; an empty test DB has no users,
    so a literal id like 1 violates the FK. The harness seeds this owner before
    driving any import and passes its real id.
    """
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    existing = await db.execute(
        select(User.id).where(User.email == _CREATOR_EMAIL)
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found

    user = User(
        email=_CREATOR_EMAIL,
        password_hash=hash_password("harness-not-a-real-login"),
        first_name="Harness",
        last_name="Creator",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user.id


async def _records_by_row(db, job_id) -> dict[int, ImportRecord]:
    result = await db.execute(
        select(ImportRecord)
        .where(ImportRecord.import_job_id == job_id)
        .order_by(ImportRecord.row_number)
    )
    return {rec.row_number: rec for rec in result.scalars().all()}


def _reconcile_executed_job(recs, *, job_type, filename, manifest) -> list[RowResult]:
    """Build RowResults for an already-executed job by reading each row's
    ImportRecord status. `recs` is the {row_number: ImportRecord} map."""
    results: list[RowResult] = []
    for spec in manifest.rows:
        rec = recs.get(spec.row)
        if rec is None:
            observed, status_name, detail = "error", None, "no ImportRecord for row"
        else:
            status_name = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
            observed = _STATUS_TO_OUTCOME.get(rec.status, "error")
            if rec.status == ImportRecordStatus.SKIPPED and getattr(rec, "is_duplicate", False):
                observed = "duplicate"
            errs = rec.errors or []
            detail = "; ".join(e.get("message", "") for e in errs) if errs else ""
        results.append(RowResult(
            job_type=job_type,
            file=filename,
            row=spec.row,
            defect_class=spec.defect_class,
            expected=spec.expected_outcome,
            observed=observed,
            record_status=status_name,
            matched=(observed == spec.expected_outcome),
            detail=detail,
        ))
    return results


async def drive_pipeline(
    db,
    *,
    file_content: bytes,
    filename: str,
    job_type,
    manifest,
    duplicate_action=DuplicateAction.SKIP,
    error_threshold: float = 100.0,   # never auto-rollback; we want full visibility
    expect_crash: bool = False,
) -> list[RowResult]:
    """Run the full pipeline for one file; reconcile rows; record OUTCOMES.

    error_threshold defaults to 100.0 so the service never auto-rolls-back on
    high error rates -- the harness needs every row's verdict, not an aborted job.

    If expect_crash is True, execute() MAY raise an uncaught DB error (e.g. a
    holdings orphan IntegrityError). If it does, we catch it, recover the
    session with a rollback, and record every manifest row as observed
    "orphan_fk". If it does NOT crash, we fall through to the same real per-row
    reconciliation the normal path uses -- never blanket-labeling rows "valid".
    """
    created_by_id = await _ensure_creator(db)

    job = await ImportService.upload(
        db=db,
        file_content=file_content,
        filename=filename,
        job_type=job_type,
        duplicate_action=duplicate_action,
        error_threshold=error_threshold,
        created_by_id=created_by_id,
    )
    job = await ImportService.validate(db, job)
    await ImportService.dry_run(db, job)

    if expect_crash:
        try:
            await ImportService.execute(db, job)
        except Exception as exc:  # noqa: BLE001 - we are characterizing crashes
            crash_detail = f"{type(exc).__name__}: {exc}"
            try:
                await db.rollback()   # recover the poisoned session for teardown
            except Exception as rb_exc:  # noqa: BLE001
                crash_detail += (
                    f" | recovery rollback also failed: "
                    f"{type(rb_exc).__name__}: {rb_exc}"
                )
            results = [
                RowResult(
                    job_type=manifest.job_type,
                    file=filename,
                    row=spec.row,
                    defect_class=spec.defect_class,
                    expected=spec.expected_outcome,
                    observed="orphan_fk",
                    record_status=None,
                    matched=(spec.expected_outcome == "orphan_fk"),
                    detail=crash_detail,
                )
                for spec in manifest.rows
            ]
            OUTCOMES.extend(asdict(r) for r in results)
            return results
        # No crash: fall through to real reconciliation (do not execute again).
    else:
        job = await ImportService.execute(db, job)

    recs = await _records_by_row(db, job.id)
    results = _reconcile_executed_job(
        recs, job_type=manifest.job_type, filename=filename, manifest=manifest
    )

    # Rollback the real import so the DB returns to pre-execute state.
    await ImportService.rollback(db, job)

    OUTCOMES.extend(asdict(r) for r in results)
    return results
