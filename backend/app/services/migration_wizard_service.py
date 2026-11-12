# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import csv as csv_mod
from app.core.logging import get_logger
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.circulation import Checkout
from app.models.inventory import ItemCopy
from app.models.migration_job import MigrationJob, MigrationJobStatus, MigrationSourceSystem
from app.models.user import User
from app.services.import_service import ImportService

logger = get_logger(__name__)


class MigrationWizardService:

    TEMP_DIR = Path("/tmp/lsc_migrations")

    @classmethod
    async def upload(
        cls,
        db: AsyncSession,
        content: bytes,
        filename: str,
        source_system: str,
        user_id: int,
    ) -> MigrationJob:
        # Save file
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        file_path = cls.TEMP_DIR / f"migration_{datetime.now().timestamp()}_{filename}"
        file_path.write_bytes(content)

        # Create job
        job = MigrationJob(
            status=MigrationJobStatus.ANALYZING,
            source_system=source_system,
            original_filename=filename,
            file_path=str(file_path),
            file_size_bytes=len(content),
            created_by_id=user_id,
        )
        db.add(job)
        await db.flush()
        job_id = job.id

        # Analyze in background (immediately for now, can be async task later)
        await cls.analyze(db, job)

        return job

    @classmethod
    async def analyze(cls, db: AsyncSession, job: MigrationJob) -> MigrationJob:
        try:
            content = Path(job.file_path).read_bytes()

            # Parse file and detect system
            if job.source_system == MigrationSourceSystem.SIRSI:
                rows, columns = cls._parse_sirsi_csv(content)
                suggested_mapping = cls._sirsi_field_mapping(columns)
                detected_system = "sirsi"
            elif job.source_system == MigrationSourceSystem.KOHA:
                rows, columns = cls._parse_koha_csv(content)
                suggested_mapping = cls._koha_field_mapping(columns)
                detected_system = "koha"
            else:
                # Generic CSV
                rows, columns = cls._parse_generic_csv(content)
                suggested_mapping = {}
                detected_system = "csv"

            sample_rows = rows[:5] if rows else []
            job.total_rows = len(rows)
            job.analysis_report = {
                "detected_columns": columns,
                "total_rows": len(rows),
                "sample_rows": sample_rows,
                "warnings": [],
                "suggested_mapping": suggested_mapping,
                "source_system_detected": detected_system,
            }
            job.status = MigrationJobStatus.READY

        except Exception as e:  # noqa: BLE001 — job-level boundary: record failure status across parser/IO/DB errors, never raise to caller
            job.status = MigrationJobStatus.FAILED
            job.error_log = {"analyze_error": str(e)}

        await db.commit()
        return job

    @classmethod
    async def get_job(cls, db: AsyncSession, job_id: int) -> Optional[MigrationJob]:
        result = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id))
        return result.scalar_one_or_none()

    @classmethod
    async def configure(
        cls,
        db: AsyncSession,
        job: MigrationJob,
        field_mapping: dict[str, str],
        options: dict[str, Any],
    ) -> MigrationJob:
        job.field_mapping = field_mapping
        job.options = options
        job.status = MigrationJobStatus.MAPPING
        await db.commit()
        return job

    @classmethod
    async def execute_dry_run(
        cls,
        db: AsyncSession,
        job: MigrationJob,
    ) -> MigrationJob:
        job.status = MigrationJobStatus.DRY_RUN

        try:
            content = Path(job.file_path).read_bytes()

            # Parse file with user's mapping
            if job.source_system == MigrationSourceSystem.SIRSI:
                rows, _ = cls._parse_sirsi_csv(content)
            elif job.source_system == MigrationSourceSystem.KOHA:
                rows, _ = cls._parse_koha_csv(content)
            else:
                rows, _ = cls._parse_generic_csv(content)

            # Simulate import
            would_create = 0
            would_update = 0
            would_skip = 0
            sample_records = []
            validation_errors = []

            for i, row in enumerate(rows[:100]):  # Sample first 100
                # Basic validation
                if not row or all(not v for v in row.values()):
                    would_skip += 1
                    continue

                # For demo: assume we'd create new records
                would_create += 1
                if len(sample_records) < 5:
                    sample_records.append(row)

            job.dry_run_report = {
                "would_create": would_create,
                "would_update": would_update,
                "would_skip": would_skip,
                "sample_records": sample_records,
                "warnings": [],
                "validation_errors": validation_errors,
            }

        except Exception as e:  # noqa: BLE001 — job-level boundary: record failure status across parser/IO/DB errors, never raise to caller
            job.status = MigrationJobStatus.FAILED
            job.error_log = {"dry_run_error": str(e)}

        await db.commit()
        return job

    # ── Record type detection from mapped fields ──────────────────────────

    # Keys that signal a particular record type (checked against mapped values)
    _PATRON_SIGNALS = {"email", "name", "first_name", "last_name", "patron_type"}
    _CATALOG_SIGNALS = {"title", "isbn", "author", "publisher", "item_type"}
    _HOLDING_SIGNALS = {"item_barcode", "catalog_id", "copy_number", "condition"}
    _CIRC_SIGNALS = {"checkout_date", "patron_barcode", "return_date"}

    @classmethod
    def _detect_record_type(cls, mapped_fields: set[str]) -> str:
        scores = {
            "circulation": len(mapped_fields & cls._CIRC_SIGNALS),
            "holding": len(mapped_fields & cls._HOLDING_SIGNALS),
            "catalog": len(mapped_fields & cls._CATALOG_SIGNALS),
            "patron": len(mapped_fields & cls._PATRON_SIGNALS),
        }
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            raise ValueError(
                f"Cannot determine record type from mapped fields: {mapped_fields}"
            )
        return best

    @classmethod
    def _apply_field_mapping(cls, row: dict[str, str], field_mapping: dict[str, str]) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for src_col, target_field in field_mapping.items():
            if target_field and src_col in row:
                mapped[target_field] = row[src_col]
        return mapped

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        job: MigrationJob,
    ) -> MigrationJob:
        job.status = MigrationJobStatus.RUNNING
        job.started_at = datetime.utcnow()

        try:
            content = Path(job.file_path).read_bytes()

            # Parse file
            if job.source_system == MigrationSourceSystem.SIRSI:
                rows, _ = cls._parse_sirsi_csv(content)
            elif job.source_system == MigrationSourceSystem.KOHA:
                rows, _ = cls._parse_koha_csv(content)
            else:
                rows, _ = cls._parse_generic_csv(content)

            # Determine record type from the field mapping
            field_mapping = job.field_mapping or {}
            mapped_target_fields = set(field_mapping.values())
            record_type = cls._detect_record_type(mapped_target_fields)

            # Track created records for rollback: list of {"id": ..., "table": ...}
            created_records: list[dict[str, Any]] = []
            created = 0
            failed = 0
            error_log: dict[str, str] = {}

            for i, row in enumerate(rows):
                try:
                    # Apply field mapping to remap source columns → target fields
                    mapped_row = cls._apply_field_mapping(row, field_mapping)

                    # Skip completely empty rows
                    if not mapped_row or all(not v.strip() for v in mapped_row.values()):
                        job.processed_rows = i + 1
                        continue

                    # Create the appropriate record
                    if record_type == "patron":
                        # Build full name if name not directly mapped
                        if "name" not in mapped_row:
                            parts = []
                            if mapped_row.get("first_name"):
                                parts.append(mapped_row["first_name"])
                            if mapped_row.get("last_name"):
                                parts.append(mapped_row["last_name"])
                            if parts:
                                mapped_row["name"] = " ".join(parts)
                        # _create_patron now returns (id, table, reset_token);
                        # wizard ignores the token. Wizard is broken (CRIT-1
                        # in the 2026-05-24 migration audit) and out of scope
                        # for the new-library plan.
                        record_id, table, _ = await ImportService._create_patron(db, mapped_row)
                    elif record_type == "catalog":
                        record_id, table = await ImportService._create_catalog_item(db, mapped_row)
                    elif record_type == "holding":
                        record_id, table = await ImportService._create_holding(db, mapped_row)
                    elif record_type == "circulation":
                        record_id, table = await ImportService._create_circulation(db, mapped_row)
                    else:
                        raise ValueError(f"Unknown record type: {record_type}")

                    created_records.append({"id": record_id, "table": table})
                    created += 1
                    job.processed_rows = i + 1

                except Exception as row_err:  # noqa: BLE001 — per-iteration boundary: one bad row must not crash entire migration
                    failed += 1
                    job.failed_rows = failed
                    error_log[f"row_{i}"] = str(row_err)
                    logger.warning(
                        "Migration row %d failed: %s", i, row_err,
                        extra={"job_id": job.id},
                    )
                    job.processed_rows = i + 1

            # Store error log
            if error_log:
                job.error_log = error_log

            # Store created record IDs for rollback support
            if not job.options:
                job.options = {}
            job.options["_created_records"] = created_records
            job.options["_record_type"] = record_type
            job.options["_created_count"] = created
            job.options["_failed_count"] = failed

            job.status = MigrationJobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.rollback_available_until = datetime.utcnow() + timedelta(hours=24)

            await db.commit()

        except Exception as e:  # noqa: BLE001 — job-level boundary: record failure status across parser/IO/DB errors, rollback + persist
            await db.rollback()
            job.status = MigrationJobStatus.FAILED
            job.completed_at = datetime.utcnow()
            if not job.error_log:
                job.error_log = {}
            job.error_log["execute_error"] = str(e)
            logger.error(
                "Migration job %d failed: %s", job.id, e,
                extra={"job_id": job.id},
            )
            # Re-attach and persist the failure status
            db.add(job)
            await db.commit()

        return job

    @classmethod
    async def rollback(
        cls,
        db: AsyncSession,
        job: MigrationJob,
    ) -> MigrationJob:
        if job.status != MigrationJobStatus.COMPLETED:
            raise ValueError("Can only rollback completed migrations")

        if job.rollback_available_until and datetime.utcnow() > job.rollback_available_until:
            raise ValueError("Rollback window has expired")

        table_model_map = {
            "users": User,
            "catalog_items": CatalogItem,
            "item_copies": ItemCopy,
            "checkouts": Checkout,
        }

        # Deletion order: circulation → holdings → catalog → patrons
        table_priority = {"checkouts": 0, "item_copies": 1, "catalog_items": 2, "users": 3}

        created_records = (job.options or {}).get("_created_records", [])
        if not created_records:
            job.status = MigrationJobStatus.ROLLED_BACK
            await db.commit()
            return job

        # Sort by priority so FKs are respected
        created_records_sorted = sorted(
            created_records,
            key=lambda r: table_priority.get(r.get("table", ""), 99),
        )

        rolled_back = 0
        rollback_errors: dict[str, str] = {}

        for rec in created_records_sorted:
            table_name = rec.get("table")
            record_id = rec.get("id")
            model_class = table_model_map.get(table_name)

            if not model_class or record_id is None:
                continue

            try:
                obj = await db.get(model_class, record_id)
                if obj is not None:
                    await db.delete(obj)
                rolled_back += 1
            except Exception as e:  # noqa: BLE001 — per-iteration boundary: one failed rollback must not block deleting remaining records
                rollback_errors[f"{table_name}_{record_id}"] = str(e)
                logger.warning(
                    "Rollback failed for %s id=%s: %s", table_name, record_id, e,
                    extra={"job_id": job.id},
                )

        job.status = MigrationJobStatus.ROLLED_BACK
        if rollback_errors:
            if not job.error_log:
                job.error_log = {}
            job.error_log["rollback_errors"] = rollback_errors

        # Update options to reflect rollback stats
        if not job.options:
            job.options = {}
        job.options["_rolled_back_count"] = rolled_back

        await db.commit()
        logger.info(
            "Migration job %d rolled back: %d records deleted",
            job.id, rolled_back,
        )
        return job

    # ── Parsers for different source systems ────────────────────────────────

    @staticmethod
    def _parse_sirsi_csv(content: bytes) -> tuple[list[dict[str, str]], list[str]]:
        text = content.decode("utf-8", errors="replace")
        reader = csv_mod.DictReader(io.StringIO(text))
        rows = list(reader) if reader.fieldnames else []
        columns = reader.fieldnames or []
        return rows, columns

    @staticmethod
    def _parse_koha_csv(content: bytes) -> tuple[list[dict[str, str]], list[str]]:
        # Decode with utf-8-sig to strip a leading BOM if present.
        text = content.decode("utf-8-sig", errors="replace")

        # Sniff delimiter from the first line; default to comma if Sniffer
        # can't decide (e.g. single-column files).
        first_line = text.split("\n", 1)[0]
        try:
            dialect = csv_mod.Sniffer().sniff(first_line, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except csv_mod.Error:
            delimiter = ","

        reader = csv_mod.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader) if reader.fieldnames else []
        columns = list(reader.fieldnames) if reader.fieldnames else []
        return rows, columns

    @staticmethod
    def _parse_generic_csv(content: bytes) -> tuple[list[dict[str, str]], list[str]]:
        text = content.decode("utf-8", errors="replace")
        reader = csv_mod.DictReader(io.StringIO(text))
        rows = list(reader) if reader.fieldnames else []
        columns = reader.fieldnames or []
        return rows, columns

    @staticmethod
    def _sirsi_field_mapping(columns: list[str]) -> dict[str, str]:
        mapping = {}
        sirsi_to_lsc = {
            "PATRON_ID": "barcode",
            "PATRON_NAME": "full_name",
            "PATRON_EMAIL": "email",
            "PATRON_PHONE": "phone",
            "PATRON_TYPE": "patron_type",
            "ITEM_ID": "barcode",
            "ITEM_TITLE": "title",
            "ITEM_AUTHOR": "author",
            "ITEM_ISBN": "isbn",
            "ITEM_TYPE": "item_type",
            "CHECKOUT_DATE": "checked_out_at",
            "DUE_DATE": "due_date",
        }
        for col in columns:
            for sirsi_col, lsc_field in sirsi_to_lsc.items():
                if sirsi_col.lower() in col.lower():
                    mapping[col] = lsc_field
                    break
        return mapping

    @staticmethod
    def _koha_field_mapping(columns: list[str]) -> dict[str, str]:
        mapping = {}
        koha_to_lsc = {
            "cardnumber": "barcode",
            "surname": "last_name",
            "firstname": "first_name",
            "email": "email",
            "phone": "phone",
            "categorycode": "patron_type",
            "biblionumber": "catalog_id",
            "title": "title",
            "author": "author",
            "isbn": "isbn",
            "itemtype": "item_type",
            "issuedate": "checked_out_at",
            "date_due": "due_date",
        }
        for col in columns:
            for koha_col, lsc_field in koha_to_lsc.items():
                if koha_col.lower() in col.lower():
                    mapping[col] = lsc_field
                    break
        return mapping
