# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin endpoints for library-system data extraction (offboarding).

Lets a library admin download a portable archive of their data — the
"leaving L30" flow. Read-only by design: nothing here mutates data.

The actual wipe of a library system's data is deliberately NOT in this
module. Deletion is an ops-team operation, requested via support after a
successful export has been verified. The frontend surfaces this clearly.
"""

from app.core.logging import get_logger
from app.core.config import get_settings
import hashlib
import io
import json as _json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

import pyzipper
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import inspect as sa_inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, Hold
from ...models.fine import Fine, FinePaymentHistory
from ...models.inventory import ItemCopy
from ...models.multi_branch import Branch, BranchItemCopy, LibrarySystem, Region
from ...models.user import User
from ...services import operations_audit_service as ops_audit
from ...models.operations_audit_log import OperationType
from .dependencies import require_admin, require_director_or_super_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/data-export", tags=["admin-data-export"])


# --- Schemas ---

class TableCount(BaseModel):
    table: str
    rows: int


class ExportManifest(BaseModel):
    library_system_id: int
    library_system_name: str
    library_system_code: str
    generated_at: datetime
    counts: list[TableCount]
    notes: list[str]
    sha256: Optional[str] = None


class LibrarySystemSummary(BaseModel):
    id: int
    code: str
    name: str
    legal_name: Optional[str]
    email: Optional[str]
    website: Optional[str]
    is_active: bool


class LibrarySystemExport(BaseModel):
    generated_at: datetime
    schema_version: str
    library_system: LibrarySystemSummary
    regions: list[dict]
    branches: list[dict]
    manifest: ExportManifest
    wipe_instructions: str


class BundleRequest(BaseModel):
    passphrase: str = Field(min_length=12)


# --- Helpers ---

# The 10 data tables the bundle exports (whole-table, no WHERE scoping).
# Matches _BUNDLE_FILE_ORDER minus library_system.json and manifest.json.
# Order here determines manifest order.
_EXPORT_TABLES: list[str] = [
    "users",
    "regions",
    "branches",
    "catalog_items",
    "item_copies",
    "branch_item_copies",
    "checkouts",
    "holds",
    "fines",
    "fine_payment_history",
]

def _wipe_instructions() -> str:
    support_email = get_settings().support_email
    return (
        "To permanently delete this library system's data from L30 after a "
        f"verified export: email {support_email} from an admin account with "
        "the downloaded archive's manifest hash. Deletion is irreversible and "
        "is scheduled for a 7-day cooling-off period."
    )


_WIPE_INSTRUCTIONS = _wipe_instructions()


# --- SQL identifier safety -----------------------------------------------
#
# Table names cannot be parameterized by the DB driver -- they have to be
# interpolated as identifiers. Defense in depth so that even if the list of
# tables is widened to include user-influenced values later, the surface is
# hard to abuse:
#
#   1. Regex format check  -- reject anything outside [A-Za-z_][A-Za-z0-9_]*
#   2. Allowlist check     -- value must appear in the live DB schema, fetched
#                             via SQLAlchemy inspect() and cached per process
#   3. Identifier quoting  -- wrap the validated name in double quotes when
#                             building the SQL string
#
# Fields the export must never emit (auth secrets, tokens). String names so
# the comparison happens against SQLAlchemy column names.
_EXCLUDE_FIELDS: frozenset[str] = frozenset({
    "password",
    "password_hash",
    "token",
    "secret",
    "api_key",
    "refresh_token",
    "totp_secret",
    "recovery_codes",
    "reset_token",
    "verification_token",
    "invite_token",
    "magic_link_token",
    "parental_consent_token",
    "recovery_email_token",
})

_TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Lazily populated cache of valid table names from the live DB schema.
_known_tables_cache: Optional[frozenset[str]] = None


# Stable file ordering for the bundle, used to compute a deterministic content
# hash regardless of dict insertion order.
_BUNDLE_FILE_ORDER = [
    "library_system.json", "regions.json", "branches.json",
    "catalog_items.json", "item_copies.json", "branch_item_copies.json",
    "users.json", "checkouts.json", "holds.json", "fines.json",
    "fine_payment_history.json",
]


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Decimal):
        return str(obj)
    return str(obj)


def _row_to_dict(row) -> dict:
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in _EXCLUDE_FIELDS
    }


def _canonical_sha256(files: dict[str, bytes]) -> str:
    unknown = set(files) - {"manifest.json"} - set(_BUNDLE_FILE_ORDER)
    if unknown:
        raise ValueError(f"files not in _BUNDLE_FILE_ORDER (excluded from hash): {sorted(unknown)}")
    h = hashlib.sha256()
    for name in _BUNDLE_FILE_ORDER:
        if name in files:
            h.update(name.encode())
            h.update(files[name])
    return h.hexdigest()


def _serialize_rows(rows) -> bytes:
    return _json.dumps(
        [_row_to_dict(r) for r in rows], default=_json_default, ensure_ascii=False
    ).encode("utf-8")


def _build_encrypted_zip(files: dict[str, bytes], passphrase: str) -> io.BytesIO:
    buf = io.BytesIO()
    with pyzipper.AESZipFile(
        buf, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(passphrase.encode("utf-8"))
        for name, data in files.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf


async def _get_known_tables(db: AsyncSession) -> frozenset[str]:
    global _known_tables_cache
    if _known_tables_cache is None:
        names = await db.run_sync(
            lambda sync_session: sa_inspect(sync_session.connection()).get_table_names()
        )
        _known_tables_cache = frozenset(names)
    return _known_tables_cache


async def _safe_table_identifier(db: AsyncSession, table: str) -> str:
    if not isinstance(table, str) or not _TABLE_NAME_PATTERN.match(table):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table identifier",
        )
    if table not in await _get_known_tables(db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown table identifier",
        )
    # PostgreSQL quoted identifiers; embedded quotes are rejected by the
    # regex above so this concatenation is safe.
    return f'"{table}"'


async def _resolve_system(db: AsyncSession, current_user: User) -> LibrarySystem:
    """Resolve the caller's library system for export.

    Prefer the user's attached system when it still exists. Otherwise, in a
    single-system deployment, fall back to the sole active system. This
    tolerates legacy accounts whose home_library_system_id points at a system
    that was reseeded under a new id (the surviving row, not the stale id).
    """
    sid = current_user.home_library_system_id
    if sid is not None:
        attached = (await db.execute(
            select(LibrarySystem).where(LibrarySystem.id == sid)
        )).scalar_one_or_none()
        if attached is not None:
            return attached

    actives = (await db.execute(
        select(LibrarySystem).where(LibrarySystem.is_active.is_(True))
    )).scalars().all()
    if len(actives) == 1:
        return actives[0]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Library system not found",
    )


async def _build_manifest(db: AsyncSession, system: LibrarySystem) -> ExportManifest:
    counts: list[TableCount] = []
    for table in _EXPORT_TABLES:
        try:
            quoted = await _safe_table_identifier(db, table)
            # Run each count inside a SAVEPOINT so a failure on one table
            # cannot abort the surrounding transaction and poison every later count.
            async with db.begin_nested():
                row = await db.execute(
                    text(f'SELECT COUNT(*) FROM {quoted}')
                )
                counts.append(TableCount(table=table, rows=int(row.scalar() or 0)))
        except HTTPException:
            # A bad identifier is a programmer error, not a runtime data
            # problem -- surface it in the manifest as -1 like other failures.
            logger.warning("manifest count refused unsafe table %s", table)
            counts.append(TableCount(table=table, rows=-1))
        except Exception as exc:  # noqa: BLE001  # manifest count — record -1 on any failure
            logger.warning("manifest count failed for %s: %s", table, exc)
            counts.append(TableCount(table=table, rows=-1))

    notes = [
        "Counts are whole-table totals for this single-system deployment.",
        "Full data (with PII) is exported via POST /admin/data-export/bundle as an encrypted ZIP.",
    ]
    return ExportManifest(
        library_system_id=system.id,
        library_system_name=system.name,
        library_system_code=system.code,
        generated_at=datetime.now(timezone.utc),
        counts=counts,
        notes=notes,
    )


# --- Endpoints ---

@router.get("/manifest", response_model=ExportManifest)
async def get_export_manifest(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Preview what a full export of the caller's library system will contain."""
    system = await _resolve_system(db, current_user)
    return await _build_manifest(db, system)


@router.post("/library-system", response_model=LibrarySystemExport)
async def export_library_system(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Generate a JSON export of the caller's library system metadata.

    Scaffold: returns the system record, regions, branches, and a manifest.
    Heavy sections (items, patrons, circulation) are exposed via follow-up
    streaming endpoints (to be added).
    """
    system = await _resolve_system(db, current_user)

    regions = (await db.execute(
        select(Region).where(Region.library_system_id == system.id)
    )).scalars().all()
    branches = (await db.execute(
        select(Branch).where(Branch.library_system_id == system.id)
    )).scalars().all()

    manifest = await _build_manifest(db, system)

    await ops_audit.log_system_operation(
        db,
        operation_type=OperationType.SYSTEM_BULK_OPERATION,
        reason="library_system_data_export",
        details={
            "library_system_id": system.id,
            "library_system_code": system.code,
            "initiated_by_user_id": current_user.id,
            "manifest_counts": [c.model_dump() for c in manifest.counts],
        },
    )
    await db.flush()

    return LibrarySystemExport(
        generated_at=datetime.now(timezone.utc),
        schema_version="1.0",
        library_system=LibrarySystemSummary(
            id=system.id,
            code=system.code,
            name=system.name,
            legal_name=system.legal_name,
            email=system.email,
            website=system.website,
            is_active=system.is_active,
        ),
        regions=[_row_to_dict(r) for r in regions],
        branches=[_row_to_dict(b) for b in branches],
        manifest=manifest,
        wipe_instructions=_WIPE_INSTRUCTIONS,
    )


@router.post("/bundle")
async def export_bundle(
    body: BundleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_super_admin),
):
    """Stream an AES-encrypted ZIP of the library's full data (whole-DB)."""
    system = await _resolve_system(db, current_user)

    # The pull below (_all) is unscoped by design and is only correct on a
    # single-system deployment. With multiple active systems it would hand one
    # system's director every other system's patron PII, so refuse rather than
    # silently over-export. Per-system scoping is a larger change deferred until
    # L30 actually runs multi-tenant. See security-findings.md #5.
    active_system_ids = (await db.execute(
        select(LibrarySystem.id).where(LibrarySystem.is_active.is_(True))
    )).scalars().all()
    if len(active_system_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Full-bundle export is only supported on single-system "
                "deployments. Multiple active library systems are configured; "
                "per-system export scoping is required before this can run."
            ),
        )

    async def _all(model):
        return (await db.execute(select(model))).scalars().all()

    files: dict[str, bytes] = {
        "library_system.json": _serialize_rows([system]),
        "regions.json": _serialize_rows(await _all(Region)),
        "branches.json": _serialize_rows(await _all(Branch)),
        "catalog_items.json": _serialize_rows(await _all(CatalogItem)),
        "item_copies.json": _serialize_rows(await _all(ItemCopy)),
        "branch_item_copies.json": _serialize_rows(await _all(BranchItemCopy)),
        "users.json": _serialize_rows(await _all(User)),
        "checkouts.json": _serialize_rows(await _all(Checkout)),
        "holds.json": _serialize_rows(await _all(Hold)),
        "fines.json": _serialize_rows(await _all(Fine)),
        "fine_payment_history.json": _serialize_rows(await _all(FinePaymentHistory)),
    }
    sha = _canonical_sha256(files)
    manifest = await _build_manifest(db, system)
    files["manifest.json"] = _json.dumps(
        {**manifest.model_dump(mode="json"), "sha256": sha}, default=_json_default
    ).encode("utf-8")

    await ops_audit.log_system_operation(
        db,
        operation_type=OperationType.SYSTEM_BULK_OPERATION,
        reason="library_system_data_export_bundle",
        details={
            "initiated_by_user_id": current_user.id,
            "sha256": sha,
            "encrypted": True,
            "datasets": list(files.keys()),
        },
    )
    await db.flush()

    buf = _build_encrypted_zip(files, body.passphrase)
    code = system.code or "library-system"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Return the full in-memory archive as a plain Response rather than a
    # StreamingResponse: the bundle is built entirely in memory, and streaming
    # a BytesIO through L30's BaseHTTPMiddleware stack drops the body (empty
    # response in prod). getvalue() ships the bytes intact.
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="l30-export-{code}-{stamp}.zip"',
            "X-Export-SHA256": sha,
            "Access-Control-Expose-Headers": "X-Export-SHA256, Content-Disposition",
        },
    )


# --- Manual data-retention trigger ---------------------------------------
#
# The retention sweep (event-registration / attendance PII anonymization +
# the rest of the daily 3 AM jobs) runs automatically. This endpoint lets
# an admin force a run on demand — useful after changing retention env
# vars, or to test the policy on staging without waiting for the cron.
# Note: retention runs use their own DB session via AsyncSessionLocal so
# the caller's request session is untouched.

retention_router = APIRouter(prefix="/admin/retention", tags=["admin-retention"])


class RetentionRunResponse(BaseModel):
    started_at: datetime
    completed_at: datetime
    results: dict


@retention_router.post("/run-now", response_model=RetentionRunResponse)
async def trigger_retention_run_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from ...core.database import AsyncSessionLocal
    from ...services.data_retention_service import run_all_retention_jobs

    started = datetime.now(timezone.utc)
    logger.info(
        "Manual retention run triggered by user_id=%s", current_user.id
    )

    async with AsyncSessionLocal() as session:
        results = await run_all_retention_jobs(session)

    completed = datetime.now(timezone.utc)

    # Best-effort audit on the request session.
    try:
        await ops_audit.log_system_operation(
            db,
            operation_type=OperationType.SYSTEM_BULK_OPERATION,
            reason="manual_retention_run",
            details={
                "initiated_by_user_id": current_user.id,
                "results": {
                    k: (v if isinstance(v, (int, dict)) else str(v))
                    for k, v in results.items()
                },
            },
            staff=current_user,
        )
        await db.flush()
    except Exception as exc:  # pragma: no cover - audit is best-effort here  # noqa: BLE001  # audit log best-effort
        logger.warning("Manual retention audit log failed: %s", exc)

    return RetentionRunResponse(
        started_at=started,
        completed_at=completed,
        results=results,
    )
