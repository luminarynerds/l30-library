# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from app.core.logging import get_logger
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.catalog import CatalogItem, ItemStatus, ItemType
from app.models.circulation_policy import CirculationPolicy
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.import_job import (
    DuplicateAction,
    ImportFileFormat,
    ImportJob,
    ImportJobStatus,
    ImportJobType,
    ImportRecord,
    ImportRecordStatus,
)
from app.models.inventory import ItemCopy
from app.models.user import User, UserRole, email_blind_hash

from .constants import (
    BARCODE_PATTERN,
    EMAIL_PATTERN,
    ISBN_PATTERN,
    REQUIRED_FIELDS,
)
from .helpers import _detect_file_format, _parse_date, _similarity
from . import readers, validators

logger = get_logger(__name__)
settings = get_settings()


class ImportService:
    # ── Stage 1: Upload ───────────────────────────────────────────────────

    @staticmethod
    async def upload(
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        job_type: ImportJobType,
        duplicate_action: DuplicateAction,
        error_threshold: float,
        created_by_id: int,
    ) -> ImportJob:
        file_format = _detect_file_format(filename)

        # Persist file to local uploads directory
        upload_dir = os.path.join(settings.storage_local_path, "imports", str(uuid.uuid4()))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

        job = ImportJob(
            job_type=job_type,
            file_format=file_format,
            status=ImportJobStatus.PENDING,
            source_filename=filename,
            source_file_path=file_path,
            file_size_bytes=len(file_content),
            duplicate_action=duplicate_action,
            error_threshold=error_threshold,
            created_by_id=created_by_id,
        )
        db.add(job)
        await db.flush()

        logger.info(
            "Import job created",
            extra={"job_id": job.id, "job_type": job_type.value, "filename": filename},
        )
        return job

    # ── Stage 2: Validate ─────────────────────────────────────────────────

    @staticmethod
    async def validate(db: AsyncSession, job: ImportJob) -> ImportJob:
        job.status = ImportJobStatus.VALIDATING
        await db.flush()

        rows = await ImportService._read_rows(job)
        job.total_rows = len(rows)

        errors: list[dict] = []
        warnings: list[dict] = []
        required = REQUIRED_FIELDS.get(job.job_type, set())

        # Apply column mapping if set
        if job.column_mapping:
            rows = [{job.column_mapping.get(k, k): v for k, v in row.items()} for row in rows]

        for idx, row in enumerate(rows, start=1):
            row_errors: list[dict] = []
            row_warnings: list[dict] = []

            # Required fields
            for field in required:
                val = row.get(field, "").strip() if row.get(field) else ""
                if not val:
                    row_errors.append(
                        {"field": field, "message": f"Required field '{field}' is missing"}
                    )

            # Type-specific validation
            if job.job_type == ImportJobType.PATRONS:
                row_errors, row_warnings = ImportService._validate_patron_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type in (ImportJobType.CATALOG_ITEMS, ImportJobType.MARC_RECORDS):
                row_errors, row_warnings = ImportService._validate_catalog_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type == ImportJobType.HOLDINGS:
                row_errors, row_warnings = ImportService._validate_holdings_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type == ImportJobType.CIRCULATION_HISTORY:
                row_errors, row_warnings = ImportService._validate_circ_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type == ImportJobType.FINES:
                row_errors, row_warnings = ImportService._validate_fines_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type == ImportJobType.HOLDS:
                row_errors, row_warnings = ImportService._validate_holds_row(
                    row, idx, row_errors, row_warnings
                )
            elif job.job_type == ImportJobType.POLICIES:
                row_errors, row_warnings = ImportService._validate_policies_row(
                    row, idx, row_errors, row_warnings
                )

            status = ImportRecordStatus.VALID
            if row_errors:
                status = ImportRecordStatus.INVALID
            elif row_warnings:
                status = ImportRecordStatus.WARNING

            record = ImportRecord(
                import_job_id=job.id,
                row_number=idx,
                status=status,
                source_data=row,
                errors=row_errors or None,
                warnings=row_warnings or None,
            )
            db.add(record)

            for e in row_errors:
                errors.append({"row": idx, **e, "severity": "error"})
            for w in row_warnings:
                warnings.append({"row": idx, **w, "severity": "warning"})

        error_count = len({e["row"] for e in errors})
        warning_count = len({w["row"] for w in warnings})

        job.error_rows = error_count
        job.validation_report = {"errors": errors, "warnings": warnings}
        job.status = ImportJobStatus.VALIDATED
        await db.flush()

        logger.info(
            "Import validation complete",
            extra={
                "job_id": job.id,
                "total": job.total_rows,
                "errors": error_count,
                "warnings": warning_count,
            },
        )
        return job

    # ── Stage 3: Preview ──────────────────────────────────────────────────

    @staticmethod
    async def preview(db: AsyncSession, job: ImportJob, limit: int = 20) -> list[ImportRecord]:
        result = await db.execute(
            select(ImportRecord)
            .where(ImportRecord.import_job_id == job.id)
            .order_by(ImportRecord.row_number)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Stage 3b: Update column mapping ───────────────────────────────────

    @staticmethod
    async def set_column_mapping(
        db: AsyncSession, job: ImportJob, mapping: dict[str, str]
    ) -> ImportJob:
        job.column_mapping = mapping
        # Remove old import records for re-validation
        await db.execute(delete(ImportRecord).where(ImportRecord.import_job_id == job.id))
        await db.flush()
        return await ImportService.validate(db, job)

    # ── Stage 4: Dry Run ──────────────────────────────────────────────────

    @staticmethod
    async def dry_run(db: AsyncSession, job: ImportJob) -> dict[str, Any]:
        job.status = ImportJobStatus.DRY_RUN
        await db.flush()

        result = await db.execute(
            select(ImportRecord)
            .where(
                ImportRecord.import_job_id == job.id,
                ImportRecord.status.in_(
                    [
                        ImportRecordStatus.VALID,
                        ImportRecordStatus.WARNING,
                    ]
                ),
            )
            .order_by(ImportRecord.row_number)
        )
        records = list(result.scalars().all())

        would_create = 0
        would_update = 0
        would_skip = 0
        duplicate_candidates = 0
        samples: list[dict] = []

        for rec in records:
            data = rec.source_data or {}
            dup_id, dup_score = await ImportService._check_duplicate(db, job.job_type, data)
            if dup_id is not None:
                rec.is_duplicate = True
                rec.duplicate_of_id = dup_id
                rec.duplicate_score = dup_score
                duplicate_candidates += 1

                if job.duplicate_action == DuplicateAction.SKIP:
                    would_skip += 1
                elif job.duplicate_action == DuplicateAction.MERGE:
                    would_update += 1
                else:
                    would_create += 1
            else:
                would_create += 1

            if len(samples) < 5:
                samples.append(
                    {
                        "row": rec.row_number,
                        "data": data,
                        "is_duplicate": rec.is_duplicate,
                        "duplicate_of_id": rec.duplicate_of_id,
                        "duplicate_score": rec.duplicate_score,
                    }
                )

        await db.flush()

        report = {
            "would_create": would_create,
            "would_update": would_update,
            "would_skip": would_skip,
            "duplicate_candidates": duplicate_candidates,
            "sample_records": samples,
        }
        job.dry_run_report = report
        job.status = ImportJobStatus.VALIDATED  # go back to validated
        await db.flush()
        return report

    # ── Stage 5: Execute ──────────────────────────────────────────────────

    @staticmethod
    async def execute(
        db: AsyncSession,
        job: ImportJob,
        batch_size: int = 100,
    ) -> ImportJob:
        job.status = ImportJobStatus.IMPORTING
        job.started_at = datetime.now(timezone.utc)
        job.processed_rows = 0
        job.created_rows = 0
        job.updated_rows = 0
        job.skipped_rows = 0
        job.error_rows = 0
        await db.flush()

        # Process valid/warning rows in batches. No offset: each processed
        # record flips its status away from VALID/WARNING, so the next batch
        # is simply whatever's left matching the filter. An offset here would
        # skip straight past the shrinking result set after the first batch
        # (e.g. batch_size=25 on 50 records: batch 1 processes rows 1-25 and
        # they leave the filter; batch 2's OFFSET 25 lands on a 25-row result
        # set and returns nothing, silently dropping rows 26-50).
        while True:
            result = await db.execute(
                select(ImportRecord)
                .where(
                    ImportRecord.import_job_id == job.id,
                    ImportRecord.status.in_(
                        [
                            ImportRecordStatus.VALID,
                            ImportRecordStatus.WARNING,
                        ]
                    ),
                )
                .order_by(ImportRecord.row_number)
                .limit(batch_size)
            )
            batch = list(result.scalars().all())
            if not batch:
                break

            for rec in batch:
                try:
                    created = await ImportService._import_record(db, job, rec)
                    if created == "created":
                        rec.status = ImportRecordStatus.CREATED
                        job.created_rows += 1
                    elif created == "updated":
                        rec.status = ImportRecordStatus.UPDATED
                        job.updated_rows += 1
                    else:
                        rec.status = ImportRecordStatus.SKIPPED
                        job.skipped_rows += 1
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    logger.warning(
                        "Import record failed",
                        extra={
                            "job_id": job.id,
                            "row": rec.row_number,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    rec.status = ImportRecordStatus.FAILED
                    rec.errors = [{"field": "_row", "message": str(exc)}]
                    job.error_rows += 1

                job.processed_rows += 1

            await db.flush()

            # Check error threshold
            if job.total_rows > 0 and job.error_percent > job.error_threshold:
                logger.warning(
                    "Error threshold exceeded, auto-rolling back",
                    extra={"job_id": job.id, "error_pct": job.error_percent},
                )
                job, _, _ = await ImportService.rollback(
                    db, job, reason="Error threshold exceeded during import"
                )
                return job

        job.status = ImportJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await db.flush()

        # #29: Emit import metrics for monitoring
        try:
            from ...core.metrics import increment

            fmt = job.job_type.value if hasattr(job.job_type, "value") else str(job.job_type)
            increment(
                "import_records_total", {"format": fmt, "status": "created"}, job.created_rows
            )
            increment(
                "import_records_total", {"format": fmt, "status": "updated"}, job.updated_rows
            )
            increment(
                "import_records_total", {"format": fmt, "status": "skipped"}, job.skipped_rows
            )
            increment("import_records_total", {"format": fmt, "status": "error"}, job.error_rows)
        except Exception:  # noqa: BLE001  # metrics emission must not break import completion
            logger.warning("Failed to emit import metrics", exc_info=True)

        logger.info(
            "Import completed",
            extra={
                "job_id": job.id,
                "created": job.created_rows,
                "updated": job.updated_rows,
                "skipped": job.skipped_rows,
                "errors": job.error_rows,
            },
        )
        return job

    # ── Stage 6: Rollback ─────────────────────────────────────────────────

    @staticmethod
    async def rollback(
        db: AsyncSession,
        job: ImportJob,
        rolled_back_by_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> tuple[ImportJob, int, int]:
        created_count = 0
        updated_count = 0

        result = await db.execute(
            select(ImportRecord).where(
                ImportRecord.import_job_id == job.id,
                ImportRecord.status.in_(
                    [
                        ImportRecordStatus.CREATED,
                        ImportRecordStatus.UPDATED,
                    ]
                ),
                ImportRecord.target_table.is_not(None),
                ImportRecord.target_id.is_not(None),
            )
        )
        records = list(result.scalars().all())

        # Group by table for batch deletion
        table_map = {
            "users": User,
            "catalog_items": CatalogItem,
            "item_copies": ItemCopy,
            "checkouts": Checkout,
            "fines": Fine,
            "holds": Hold,
            "circulation_policy": CirculationPolicy,
        }

        for rec in records:
            model_class = table_map.get(rec.target_table)
            if model_class and rec.status == ImportRecordStatus.CREATED:
                await db.execute(delete(model_class).where(model_class.id == rec.target_id))
                rec.status = ImportRecordStatus.ROLLED_BACK
                created_count += 1
            elif rec.status == ImportRecordStatus.UPDATED:
                # For updated records we can only mark them; full field-level
                # undo would require storing the old values (not implemented).
                rec.status = ImportRecordStatus.ROLLED_BACK
                updated_count += 1

        job.status = ImportJobStatus.ROLLED_BACK
        job.rolled_back_at = datetime.now(timezone.utc)
        job.rolled_back_by_id = rolled_back_by_id
        job.rollback_reason = reason or "Manual rollback"
        await db.flush()

        logger.info(
            "Import rolled back",
            extra={"job_id": job.id, "deleted": created_count, "marked_only": updated_count},
        )
        return job, created_count, updated_count

    # ── History ───────────────────────────────────────────────────────────

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        job_type: Optional[ImportJobType] = None,
    ) -> tuple[list[ImportJob], int]:
        query = select(ImportJob).order_by(ImportJob.id.desc())
        count_query = select(func.count(ImportJob.id))

        if job_type:
            query = query.where(ImportJob.job_type == job_type)
            count_query = count_query.where(ImportJob.job_type == job_type)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        result = await db.execute(query.offset(offset).limit(limit))
        jobs = list(result.scalars().all())
        return jobs, total

    @staticmethod
    async def get_job(db: AsyncSession, job_id: int) -> Optional[ImportJob]:
        result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
        return result.scalar_one_or_none()

    # ═══════════════════════════════════════════════════════════════════════
    # Private helpers
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    async def _read_rows(job: ImportJob) -> list[dict[str, str]]:
        return await readers.read_rows(job)

    @staticmethod
    def _read_csv(path: str) -> list[dict[str, str]]:
        return readers.read_csv(path)

    @staticmethod
    def _read_marc(path: str, fmt: ImportFileFormat) -> list[dict[str, str]]:
        return readers.read_marc(path, fmt)

    @staticmethod
    def _marc_to_dict(record) -> dict[str, str]:
        return readers.marc_to_dict(record)

    @staticmethod
    def _read_json(path: str) -> list[dict[str, str]]:
        return readers.read_json(path)

    @staticmethod
    def _validate_patron_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_patron_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_catalog_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_catalog_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_holdings_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_holdings_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_circ_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_circ_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_fines_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_fines_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_holds_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_holds_row(row, row_num, errors, warnings)

    @staticmethod
    def _validate_policies_row(
        row: dict, row_num: int, errors: list[dict], warnings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        return validators._validate_policies_row(row, row_num, errors, warnings)

    # ── Duplicate detection ───────────────────────────────────────────────

    @staticmethod
    async def _check_duplicate(
        db: AsyncSession, job_type: ImportJobType, data: dict
    ) -> tuple[Optional[int], Optional[float]]:
        if job_type == ImportJobType.PATRONS:
            email = data.get("email", "").strip()
            barcode = data.get("barcode", "").strip()

            if email:
                # Email is encrypted + case-insensitive identity; dedup via the
                # email_hash blind index (HMAC of the normalized lowercased email).
                result = await db.execute(
                    select(User.id).where(User.email_hash == email_blind_hash(email))
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

            if barcode:
                result = await db.execute(select(User.id).where(User.library_card == barcode))
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

        elif job_type in (ImportJobType.CATALOG_ITEMS, ImportJobType.MARC_RECORDS):
            isbn = data.get("isbn", "").strip()
            lccn = data.get("lccn", "").strip()
            oclc_number = data.get("oclc_number", "").strip()
            title = data.get("title", "").strip()
            author = data.get("author", "").strip()

            # OCLC# and LCCN are the strongest match signals -- they are
            # assigned per cataloging record and survive ISBN reissues
            # (paperback vs hardcover) and bound-with situations.
            if oclc_number:
                result = await db.execute(
                    select(CatalogItem.id).where(CatalogItem.oclc_number == oclc_number).limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

            if lccn:
                result = await db.execute(
                    select(CatalogItem.id).where(CatalogItem.lccn == lccn).limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

            if isbn:
                result = await db.execute(select(CatalogItem.id).where(CatalogItem.isbn == isbn))
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

            # Fuzzy title/author matching is a last resort for records that
            # carry no strong identifier at all. Falling through to it even
            # when an oclc_number/lccn/isbn was supplied (just not already in
            # the catalog) produces false positives: e.g. importing a batch
            # of distinctly-titled records that merely resemble each other
            # ("Scale Test Title 5" vs "...6") gets 49 of 50 wrongly flagged
            # as duplicates of the first, because a present-but-unmatched
            # strong identifier used to fall through to fuzzy scoring anyway.
            if title and author and not (oclc_number or lccn or isbn):
                result = await db.execute(
                    select(CatalogItem.id, CatalogItem.title, CatalogItem.author).limit(50)
                )
                for row in result.all():
                    title_sim = _similarity(title, row.title or "")
                    author_sim = _similarity(author, row.author or "")
                    combined = (title_sim * 0.6) + (author_sim * 0.4)
                    if combined >= 0.85:
                        return row.id, round(combined, 3)

        elif job_type == ImportJobType.HOLDINGS:
            barcode = data.get("item_barcode", "").strip()
            if barcode:
                result = await db.execute(select(ItemCopy.id).where(ItemCopy.barcode == barcode))
                existing = result.scalar_one_or_none()
                if existing:
                    return existing, 1.0

        elif job_type == ImportJobType.FINES:
            # Fines are generally unique per transaction, but detect exact
            # duplicates by patron + amount + reason on the same date.
            patron_barcode = data.get("patron_barcode", "").strip()
            amount = data.get("amount", "").strip()
            reason = data.get("reason", "").strip().lower()
            if patron_barcode and amount:
                patron_result = await db.execute(
                    select(User.id).where(User.library_card == patron_barcode)
                )
                patron_id = patron_result.scalar_one_or_none()
                if patron_id:
                    from decimal import Decimal, InvalidOperation

                    try:
                        amt = Decimal(amount)
                    except (InvalidOperation, ValueError, TypeError):
                        amt = None
                    if amt is not None:
                        fine_result = await db.execute(
                            select(Fine.id)
                            .where(
                                Fine.user_id == patron_id,
                                Fine.amount == amt,
                            )
                            .limit(1)
                        )
                        existing = fine_result.scalar_one_or_none()
                        if existing:
                            return existing, 0.9

        elif job_type == ImportJobType.HOLDS:
            # Detect duplicate active hold by patron + item
            patron_barcode = data.get("patron_barcode", "").strip()
            catalog_ref = data.get("catalog_reference", "").strip()
            if patron_barcode and catalog_ref:
                patron_result = await db.execute(
                    select(User.id).where(User.library_card == patron_barcode)
                )
                patron_id = patron_result.scalar_one_or_none()
                if patron_id:
                    # Resolve catalog item
                    item_id = await ImportService._resolve_catalog_reference(db, catalog_ref)
                    if item_id:
                        hold_result = await db.execute(
                            select(Hold.id)
                            .where(
                                Hold.user_id == patron_id,
                                Hold.item_id == item_id,
                                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
                            )
                            .limit(1)
                        )
                        existing = hold_result.scalar_one_or_none()
                        if existing:
                            return existing, 1.0

        elif job_type == ImportJobType.POLICIES:
            role_v = data.get("role", "").strip().lower()
            itype_v = data.get("item_type", "").strip().lower()
            bind_v = data.get("binding", "").strip().lower()
            try:
                from app.models.user import UserRole as _UR

                role = _UR(role_v) if role_v else None
            except ValueError:
                role = None
            try:
                from app.models.catalog import ItemType as _IT

                item_type = _IT(itype_v) if itype_v else None
            except ValueError:
                item_type = None
            try:
                from app.models.catalog import BookBinding as _BB

                binding = _BB(bind_v) if bind_v else None
            except ValueError:
                binding = None
            from app.services.setup_service import get_default_library_system_id

            lsid = await get_default_library_system_id(db)
            q = (
                select(CirculationPolicy.id)
                .where(
                    CirculationPolicy.library_system_id == lsid,
                    CirculationPolicy.role == role,
                    CirculationPolicy.item_type == item_type,
                    CirculationPolicy.binding == binding,
                    CirculationPolicy.collection_id.is_(None),
                    CirculationPolicy.active.is_(True),
                )
                .limit(1)
            )
            existing = (await db.execute(q)).scalar_one_or_none()
            if existing:
                return existing, 1.0

        return None, None

    # ── Record creation ───────────────────────────────────────────────────

    @staticmethod
    async def _import_record(db: AsyncSession, job: ImportJob, rec: ImportRecord) -> str:
        data = rec.source_data or {}

        # Check for duplicates
        dup_id, dup_score = await ImportService._check_duplicate(db, job.job_type, data)

        if dup_id is not None:
            if job.duplicate_action == DuplicateAction.SKIP:
                rec.is_duplicate = True
                rec.duplicate_of_id = dup_id
                rec.duplicate_score = dup_score
                return "skipped"
            elif job.duplicate_action == DuplicateAction.MERGE:
                await ImportService._merge_record(db, job.job_type, dup_id, data)
                rec.target_table = ImportService._target_table(job.job_type)
                rec.target_id = dup_id
                rec.is_duplicate = True
                rec.duplicate_of_id = dup_id
                rec.duplicate_score = dup_score
                return "updated"

        # Create new record
        obj_id, table = await ImportService._create_record(db, job.job_type, data)
        rec.target_table = table
        rec.target_id = obj_id
        return "created"

    @staticmethod
    def _target_table(job_type: ImportJobType) -> str:
        return {
            ImportJobType.PATRONS: "users",
            ImportJobType.CATALOG_ITEMS: "catalog_items",
            ImportJobType.MARC_RECORDS: "catalog_items",
            ImportJobType.HOLDINGS: "item_copies",
            ImportJobType.CIRCULATION_HISTORY: "checkouts",
            ImportJobType.FINES: "fines",
            ImportJobType.HOLDS: "holds",
            ImportJobType.POLICIES: "circulation_policy",
        }[job_type]

    @staticmethod
    async def _create_record(
        db: AsyncSession, job_type: ImportJobType, data: dict
    ) -> tuple[int, str]:
        if job_type == ImportJobType.PATRONS:
            # _create_patron returns (id, table, reset_token); the bulk-import
            # path does not email patrons (the go-live runbook sends welcome
            # links as a separate step), so the plaintext token is discarded
            # here and the 3-tuple is normalized to the (id, table) contract.
            user_id, table, _reset_token = await ImportService._create_patron(db, data)
            return user_id, table
        elif job_type in (ImportJobType.CATALOG_ITEMS, ImportJobType.MARC_RECORDS):
            return await ImportService._create_catalog_item(db, data)
        elif job_type == ImportJobType.HOLDINGS:
            return await ImportService._create_holding(db, data)
        elif job_type == ImportJobType.CIRCULATION_HISTORY:
            return await ImportService._create_circulation(db, data)
        elif job_type == ImportJobType.FINES:
            return await ImportService._create_fine(db, data)
        elif job_type == ImportJobType.HOLDS:
            return await ImportService._create_hold(db, data)
        elif job_type == ImportJobType.POLICIES:
            return await ImportService._create_policy(db, data)
        raise ValueError(f"Unsupported job type: {job_type}")

    @staticmethod
    async def _create_patron(db: AsyncSession, data: dict) -> tuple[int, str, str]:
        from app.core.security import (
            create_reset_token,
            generate_library_card,
            get_reset_token_expiry,
            hash_password,
            hash_reset_token,
        )
        import secrets

        name = data.get("name", "").strip()
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()

        if not first_name and not last_name and name:
            parts = name.split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        # Random password the patron will replace via the reset link. Kept
        # cryptographically random so the account is never reachable if the
        # welcome email is dropped.
        temp_password = secrets.token_urlsafe(32)

        patron_type_str = data.get("patron_type", "").strip().lower()
        try:
            role = UserRole(patron_type_str) if patron_type_str else UserRole.PATRON
        except ValueError:
            role = UserRole.PATRON

        reset_token = create_reset_token()

        user = User(
            email=data.get("email", "").strip(),
            password_hash=hash_password(temp_password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            email_verified=True,
            reset_token=hash_reset_token(reset_token),
            reset_token_expires=get_reset_token_expiry(),
            library_card=data.get("barcode", "").strip() or generate_library_card(),
            address=data.get("address", "").strip() or None,
        )
        # Route phone through set_phone() so the phone_hash blind index and
        # phone_last4 columns populate. User(phone=...) goes through the
        # EncryptedPIIField descriptor, which only encrypts and skips both
        # derived columns -- breaking search-by-phone for imported patrons.
        phone_val = data.get("phone", "").strip()
        if phone_val:
            user.set_phone(phone_val)
        # Resolve home_branch (Branch.code string from the import CSV) to
        # Branch.id. Missing/unknown codes log a warning and leave
        # home_branch_id=None -- mirrors how invalid patron_type falls back
        # to PATRON instead of failing the whole row.
        home_branch_code = data.get("home_branch", "").strip().upper()
        if home_branch_code:
            from app.models.multi_branch import Branch

            result = await db.execute(select(Branch.id).where(Branch.code == home_branch_code))
            branch_id = result.scalar_one_or_none()
            if branch_id is not None:
                user.home_branch_id = branch_id
            else:
                logger.warning(
                    "home_branch code %r did not resolve to a Branch; leaving home_branch_id=None for user %r",
                    home_branch_code,
                    data.get("email"),
                )
        # Resolve patron_category (PatronCategory.code, e.g. "STUDENT") to
        # PatronCategory.id. Missing/unknown codes log a warning and leave
        # patron_category_id=None -- mirrors the home_branch fallback.
        # Accept "categorycode" as an alias for Koha-export compatibility.
        category_code = (
            data.get("patron_category", "").strip() or data.get("categorycode", "").strip()
        ).upper()
        if category_code:
            from app.models.patron_category import PatronCategory

            result = await db.execute(
                select(PatronCategory.id).where(PatronCategory.code == category_code)
            )
            category_id = result.scalar_one_or_none()
            if category_id is not None:
                user.patron_category_id = category_id
            else:
                logger.warning(
                    "patron_category code %r did not resolve to a PatronCategory; "
                    "leaving patron_category_id=None for user %r",
                    category_code,
                    data.get("email"),
                )
        # Set home_library_system_id to the sole LibrarySystem in the
        # deployment. The import job carries no library_system field, and
        # threading created_by_id down through _create_record is a
        # non-minimal change; since L30 is one-system-per-deployment both
        # are equivalent.
        if user.home_library_system_id is None:
            from app.services.setup_service import get_default_library_system_id

            user.home_library_system_id = await get_default_library_system_id(db)

        db.add(user)
        await db.flush()
        return user.id, "users", reset_token

    @staticmethod
    async def _create_catalog_item(db: AsyncSession, data: dict) -> tuple[int, str]:
        item_type_raw = data.get("item_type", "book").strip()
        item_type_str = item_type_raw.lower()
        local_type = None
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            # Source ILS used a taxonomy outside L30's 13-value enum.
            # Collapse to 'other' and preserve the original label in
            # local_type so display + filter UIs don't lose semantics.
            item_type = ItemType.other
            local_type = item_type_raw or None

        pub_year = None
        if data.get("publication_year"):
            try:
                pub_year = int(data["publication_year"])
            except ValueError:
                logger.warning("Invalid publication_year value: %s", data["publication_year"])

        item = CatalogItem(
            title=data.get("title", "").strip(),
            author=data.get("author", "").strip() or None,
            isbn=data.get("isbn", "").strip() or None,
            lccn=data.get("lccn", "").strip() or None,
            oclc_number=data.get("oclc_number", "").strip() or None,
            publisher=data.get("publisher", "").strip() or None,
            publication_year=pub_year,
            item_type=item_type,
            local_type=local_type,
            status=ItemStatus.available,
            description=data.get("description", "").strip() or None,
            call_number=data.get("call_number", "").strip() or None,
            edition=data.get("edition", "").strip() or None,
            series_name=data.get("series_name", "").strip() or None,
        )
        db.add(item)
        await db.flush()
        return item.id, "catalog_items"

    @staticmethod
    async def _create_holding(db: AsyncSession, data: dict) -> tuple[int, str]:
        from app.models.inventory import ItemCondition

        condition_str = data.get("condition", "good").strip().lower()
        try:
            condition = ItemCondition(condition_str)
        except ValueError:
            condition = ItemCondition.GOOD

        catalog_id = int(data["catalog_id"])

        # Resolve the catalog item first. Without this check a bad
        # catalog_id reaches db.flush() below as a raw FK violation
        # (IntegrityError), which isn't in execute()'s per-row except
        # clause -- it escapes the row loop, poisons the transaction, and
        # crashes the whole job instead of rejecting this one row (mirrors
        # the patron/item-barcode existence checks in _create_circulation).
        catalog_exists = await db.execute(
            select(CatalogItem.id).where(CatalogItem.id == catalog_id)
        )
        if catalog_exists.scalar_one_or_none() is None:
            raise ValueError(f"Catalog item id '{catalog_id}' not found")

        copy_number = None
        if data.get("copy_number"):
            try:
                copy_number = int(data["copy_number"])
            except ValueError:
                logger.warning("Invalid copy_number value: %s", data["copy_number"])
        if copy_number is None:
            # No copy_number given: assign the next free one for this title so
            # multiple imported copies don't collide on the
            # (catalog_item_id, copy_number) unique constraint.
            result = await db.execute(
                select(func.max(ItemCopy.copy_number)).where(ItemCopy.catalog_item_id == catalog_id)
            )
            copy_number = (result.scalar_one_or_none() or 0) + 1

        replacement_cost = None
        if data.get("replacement_cost"):
            try:
                replacement_cost = float(data["replacement_cost"])
            except ValueError:
                logger.warning("Invalid replacement_cost value: %s", data["replacement_cost"])

        copy = ItemCopy(
            catalog_item_id=catalog_id,
            barcode=data.get("item_barcode", "").strip(),
            condition=condition,
            copy_number=copy_number,
            location=data.get("location", "").strip() or None,
            replacement_cost=replacement_cost,
        )
        db.add(copy)
        await db.flush()
        return copy.id, "item_copies"

    @staticmethod
    async def _create_circulation(db: AsyncSession, data: dict) -> tuple[int, str]:
        # Resolve patron by barcode
        patron_barcode = data.get("patron_barcode", "").strip()
        patron_result = await db.execute(select(User.id).where(User.library_card == patron_barcode))
        patron_id = patron_result.scalar_one_or_none()
        if patron_id is None:
            raise ValueError(f"Patron barcode '{patron_barcode}' not found")

        # Resolve item by barcode
        item_barcode = data.get("item_barcode", "").strip()
        item_result = await db.execute(
            select(ItemCopy.id, ItemCopy.catalog_item_id).where(ItemCopy.barcode == item_barcode)
        )
        item_row = item_result.one_or_none()
        if item_row is None:
            raise ValueError(f"Item barcode '{item_barcode}' not found")

        checkout_date = _parse_date(data.get("checkout_date", ""))
        if checkout_date is None:
            raise ValueError("Invalid checkout_date")

        return_date = None
        return_date_str = data.get("return_date", "").strip()
        if return_date_str:
            return_date = _parse_date(return_date_str)

        status = CheckoutStatus.returned if return_date else CheckoutStatus.active

        # Guard the copy-level active-checkout unique index
        # (ix_active_item_copy_checkout on item_copy_id WHERE status='active').
        # A second active checkout of the same physical copy would raise an
        # uncaught IntegrityError and crash the whole job, so reject this row
        # gracefully instead (mirrors checkout_service.create_checkout's live
        # guard). Uniqueness is per COPY, not per title: multiple copies of one
        # title may each carry an active checkout (#1427). The already-flushed
        # first row of a batch is visible to this query.
        if status == CheckoutStatus.active:
            existing_active = await db.execute(
                select(Checkout.id).where(
                    Checkout.item_copy_id == item_row.id,
                    Checkout.status == CheckoutStatus.active,
                )
            )
            if existing_active.scalar_one_or_none() is not None:
                raise ValueError(
                    f"Item copy '{item_barcode}' already has an active "
                    f"checkout; a physical copy can only be out to one "
                    f"patron at a time"
                )

        # due_date precedence: explicit input (preserves historical truth from
        # source ILS) > circulation_policy resolution. The previous code did
        # checkout_date.replace(day=min(day+21, 28)), which clipped the day-of-month
        # at 28 instead of adding days -- 2024-01-10 -> 2024-01-28 instead of 2024-01-31.
        from datetime import timedelta
        from app.services import circulation_policy

        due_date_str = data.get("due_date", "").strip()
        if due_date_str:
            due_date = _parse_date(due_date_str)
            if due_date is None:
                raise ValueError(f"Invalid due_date: '{due_date_str}'")
        else:
            user_row = await db.execute(select(User).where(User.id == patron_id))
            user = user_row.scalar_one()
            item_row_full = await db.execute(
                select(CatalogItem).where(CatalogItem.id == item_row.catalog_item_id)
            )
            catalog_item = item_row_full.scalar_one()
            loan_days = await circulation_policy.get_loan_period_days(user, catalog_item, db)
            due_date = checkout_date + timedelta(days=loan_days)

        checkout = Checkout(
            user_id=patron_id,
            item_id=item_row.catalog_item_id,
            item_copy_id=item_row.id,
            status=status,
            checked_out_at=checkout_date,
            due_date=due_date,
            returned_at=return_date,
        )
        db.add(checkout)

        # Increment total_checkouts on the catalog item
        await db.execute(
            update(CatalogItem)
            .where(CatalogItem.id == item_row.catalog_item_id)
            .values(total_checkouts=func.coalesce(CatalogItem.total_checkouts, 0) + 1)
        )

        await db.flush()
        return checkout.id, "checkouts"

    @staticmethod
    async def _resolve_catalog_reference(db: AsyncSession, catalog_ref: str) -> Optional[int]:
        catalog_ref = catalog_ref.strip()
        if not catalog_ref:
            return None

        # Try as numeric ID first. Only treat it as an id when it fits a
        # Postgres int4 (CatalogItem.id); a 13-digit ISBN parses as int but
        # overflows int4, so binding it to the id column raises before the
        # query runs. Out-of-range numerics fall through to the ISBN lookup.
        try:
            item_id = int(catalog_ref)
            if 1 <= item_id <= 2147483647:
                result = await db.execute(select(CatalogItem.id).where(CatalogItem.id == item_id))
                existing = result.scalar_one_or_none()
                if existing:
                    return existing
        except ValueError:
            pass

        # Try as ISBN
        result = await db.execute(select(CatalogItem.id).where(CatalogItem.isbn == catalog_ref))
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return None

    @staticmethod
    async def _create_fine(db: AsyncSession, data: dict) -> tuple[int, str]:
        from decimal import Decimal, InvalidOperation

        # Resolve patron by barcode
        patron_barcode = data.get("patron_barcode", "").strip()
        patron_result = await db.execute(select(User.id).where(User.library_card == patron_barcode))
        patron_id = patron_result.scalar_one_or_none()
        if patron_id is None:
            raise ValueError(f"Patron barcode '{patron_barcode}' not found")

        # Parse amount
        try:
            amount = Decimal(data.get("amount", "0").strip())
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"Invalid amount: '{data.get('amount')}'") from None

        # Resolve fine type from reason
        reason = data.get("reason", "other").strip()
        reason_lower = reason.lower()
        local_fine_type = None
        try:
            fine_type = FineType(reason_lower)
        except ValueError:
            fine_type = FineType.other
            local_fine_type = reason or None

        # Optionally resolve checkout via item barcode
        checkout_id = None
        item_barcode = data.get("item_barcode", "").strip()
        if item_barcode:
            item_result = await db.execute(
                select(ItemCopy.id, ItemCopy.catalog_item_id).where(
                    ItemCopy.barcode == item_barcode
                )
            )
            item_row = item_result.one_or_none()
            if item_row:
                # Find the most recent checkout for this patron + item copy
                checkout_result = await db.execute(
                    select(Checkout.id)
                    .where(
                        Checkout.user_id == patron_id,
                        Checkout.item_copy_id == item_row.id,
                    )
                    .order_by(Checkout.checked_out_at.desc())
                    .limit(1)
                )
                checkout_id = checkout_result.scalar_one_or_none()

        # Parse date_assessed
        description = data.get("description", "").strip() or None
        date_assessed_str = data.get("date_assessed", "").strip()

        fine = Fine(
            user_id=patron_id,
            checkout_id=checkout_id,
            fine_type=fine_type,
            local_fine_type=local_fine_type,
            status=FineStatus.unpaid,
            amount=amount,
            amount_paid=Decimal("0.00"),
            description=description,
        )
        db.add(fine)
        await db.flush()

        # If date_assessed is given, update created_at via raw update
        if date_assessed_str:
            parsed = _parse_date(date_assessed_str)
            if parsed:
                await db.execute(update(Fine).where(Fine.id == fine.id).values(created_at=parsed))
                await db.flush()

        return fine.id, "fines"

    @staticmethod
    async def _create_hold(db: AsyncSession, data: dict) -> tuple[int, str]:
        from app.models.multi_branch import Branch

        # Resolve patron by barcode
        patron_barcode = data.get("patron_barcode", "").strip()
        patron_result = await db.execute(select(User.id).where(User.library_card == patron_barcode))
        patron_id = patron_result.scalar_one_or_none()
        if patron_id is None:
            raise ValueError(f"Patron barcode '{patron_barcode}' not found")

        # Resolve catalog item by ISBN or numeric ID
        catalog_ref = data.get("catalog_reference", "").strip()
        item_id = await ImportService._resolve_catalog_reference(db, catalog_ref)
        if item_id is None:
            raise ValueError(f"Catalog reference '{catalog_ref}' not found")

        # Parse hold status
        hold_type = data.get("hold_type", "pending").strip().lower()
        try:
            status = HoldStatus(hold_type)
        except ValueError:
            status = HoldStatus.pending

        # Parse position
        position = 1
        pos_str = data.get("position_in_queue", "").strip()
        if pos_str:
            try:
                position = int(pos_str)
            except ValueError:
                logger.warning("Invalid position_in_queue: %s", pos_str)

        # Resolve pickup branch
        pickup_location_id = None
        pickup_branch = data.get("pickup_branch", "").strip()
        if pickup_branch:
            branch_result = await db.execute(
                select(Branch.id).where(Branch.code == pickup_branch.upper())
            )
            pickup_location_id = branch_result.scalar_one_or_none()

        hold = Hold(
            user_id=patron_id,
            item_id=item_id,
            pickup_location_id=pickup_location_id,
            status=status,
            position=position,
        )
        db.add(hold)
        await db.flush()

        # If hold_date is given, update created_at via raw update
        hold_date_str = data.get("hold_date", "").strip()
        if hold_date_str:
            parsed = _parse_date(hold_date_str)
            if parsed:
                await db.execute(update(Hold).where(Hold.id == hold.id).values(created_at=parsed))
                await db.flush()

        return hold.id, "holds"

    @staticmethod
    async def _create_policy(db: AsyncSession, data: dict) -> tuple[int, str]:
        from decimal import Decimal

        def _parse_int(v):
            s = str(v).strip() if v is not None else ""
            return int(s) if s else None

        def _parse_decimal(v):
            s = str(v).strip() if v is not None else ""
            return Decimal(s) if s else None

        def _parse_bool(v):
            return str(v).strip().lower() in {"1", "true", "yes", "y"} if v else None

        role_v = data.get("role", "").strip().lower()
        itype_v = data.get("item_type", "").strip().lower()
        bind_v = data.get("binding", "").strip().lower()
        active_v = data.get("active", "").strip().lower()

        try:
            role = UserRole(role_v) if role_v else None
        except ValueError:
            role = None
        try:
            item_type = ItemType(itype_v) if itype_v else None
        except ValueError:
            item_type = None
        try:
            from app.models.catalog import BookBinding

            binding = BookBinding(bind_v) if bind_v else None
        except ValueError:
            binding = None

        active = False if active_v == "false" else True
        from app.services.setup_service import get_default_library_system_id

        lsid = await get_default_library_system_id(db)

        # Skip-if-identical guard: do not create a duplicate row for the same
        # dimension set (library_system + role + item_type + binding + no collection).
        existing_q = (
            select(CirculationPolicy.id)
            .where(
                CirculationPolicy.library_system_id == lsid,
                CirculationPolicy.role == role,
                CirculationPolicy.item_type == item_type,
                CirculationPolicy.binding == binding,
                CirculationPolicy.collection_id.is_(None),
                CirculationPolicy.active.is_(True),
            )
            .limit(1)
        )
        existing_id = (await db.execute(existing_q)).scalar_one_or_none()
        if existing_id is not None:
            return existing_id, "circulation_policy"

        policy = CirculationPolicy(
            library_system_id=lsid,
            role=role,
            item_type=item_type,
            binding=binding,
            loan_period_days=_parse_int(data.get("loan_period_days")),
            max_renewals=_parse_int(data.get("max_renewals")),
            overdue_fine_per_day=_parse_decimal(data.get("overdue_fine_per_day")),
            max_fine=_parse_decimal(data.get("max_fine")),
            grace_period_days=_parse_int(data.get("grace_period_days")),
            hold_pickup_days=_parse_int(data.get("hold_pickup_days")),
            fine_free=_parse_bool(data.get("fine_free")),
            active=active,
        )
        db.add(policy)
        await db.flush()
        return policy.id, "circulation_policy"

    @staticmethod
    async def _merge_record(
        db: AsyncSession, job_type: ImportJobType, existing_id: int, data: dict
    ) -> None:
        if job_type == ImportJobType.PATRONS:
            updates = {}
            if data.get("phone", "").strip():
                updates["phone"] = data["phone"].strip()
            if data.get("address", "").strip():
                updates["address"] = data["address"].strip()
            if data.get("barcode", "").strip():
                updates["library_card"] = data["barcode"].strip()
            if updates:
                await db.execute(update(User).where(User.id == existing_id).values(**updates))

        elif job_type in (ImportJobType.CATALOG_ITEMS, ImportJobType.MARC_RECORDS):
            updates = {}
            if data.get("description", "").strip():
                updates["description"] = data["description"].strip()
            if data.get("call_number", "").strip():
                updates["call_number"] = data["call_number"].strip()
            if data.get("publisher", "").strip():
                updates["publisher"] = data["publisher"].strip()
            if updates:
                await db.execute(
                    update(CatalogItem).where(CatalogItem.id == existing_id).values(**updates)
                )

        await db.flush()
