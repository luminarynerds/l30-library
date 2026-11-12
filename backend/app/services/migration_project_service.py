# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob, ImportJobStatus, ImportJobType
from app.models.migration_project import (
    CutoverStrategy,
    MigrationPhase,
    MigrationPhaseStatus,
    MigrationProject,
    MigrationProjectPhase,
    MigrationProjectStatus,
)
from app.services.import_service import ImportService

logger = get_logger(__name__)

# Phase ordering — each phase can only start when its predecessor is COMPLETED
PHASE_ORDER = list(MigrationPhase)

# Map migration phases to ImportJobType
PHASE_JOB_TYPE = {
    MigrationPhase.CATALOG: ImportJobType.MARC_RECORDS,
    MigrationPhase.HOLDINGS: ImportJobType.HOLDINGS,
    MigrationPhase.PATRONS: ImportJobType.PATRONS,
    MigrationPhase.ACTIVE_CIRCULATION: ImportJobType.CIRCULATION_HISTORY,
    MigrationPhase.HISTORICAL_DATA: ImportJobType.CIRCULATION_HISTORY,
}


class MigrationProjectService:

    # ── Project lifecycle ──────────────────────────────────────────────────

    @staticmethod
    async def create_project(
        db: AsyncSession,
        name: str,
        created_by_id: int,
        source_system_name: Optional[str] = None,
        source_system_type: Optional[str] = None,
        cutover_strategy: Optional[str] = None,
        estimated_catalog_size: Optional[int] = None,
        estimated_patron_count: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> MigrationProject:
        strategy = None
        if cutover_strategy:
            # Unknown strategy strings fall back to None.
            with contextlib.suppress(ValueError):
                strategy = CutoverStrategy(cutover_strategy)

        project = MigrationProject(
            name=name,
            status=MigrationProjectStatus.CREATED,
            cutover_strategy=strategy,
            source_system_name=source_system_name,
            source_system_type=source_system_type,
            estimated_catalog_size=estimated_catalog_size,
            estimated_patron_count=estimated_patron_count,
            notes=notes,
            created_by_id=created_by_id,
        )
        db.add(project)
        await db.flush()

        # Create all 6 phases — first is READY, rest are LOCKED
        for i, phase in enumerate(PHASE_ORDER):
            phase_status = (
                MigrationPhaseStatus.READY if i == 0
                else MigrationPhaseStatus.LOCKED
            )
            db.add(MigrationProjectPhase(
                project_id=project.id,
                phase=phase,
                status=phase_status,
            ))

        await db.flush()
        logger.info("Migration project created", extra={"project_id": project.id, "project_name": name})
        return project

    @staticmethod
    async def get_project(db: AsyncSession, project_id: int) -> Optional[MigrationProject]:
        result = await db.execute(
            select(MigrationProject).where(MigrationProject.id == project_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_project_with_phases(db: AsyncSession, project_id: int) -> Optional[dict]:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(MigrationProject)
            .options(selectinload(MigrationProject.phases))
            .where(MigrationProject.id == project_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_projects(
        db: AsyncSession, limit: int = 20, offset: int = 0
    ) -> tuple[list[MigrationProject], int]:
        from sqlalchemy import func
        from sqlalchemy.orm import selectinload
        count_result = await db.execute(
            select(func.count(MigrationProject.id))
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(MigrationProject)
            .options(selectinload(MigrationProject.phases))
            .order_by(MigrationProject.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all()), total

    # ── Phase operations ───────────────────────────────────────────────────

    @staticmethod
    async def get_phase(
        db: AsyncSession, project_id: int, phase_name: str
    ) -> Optional[MigrationProjectPhase]:
        try:
            phase_enum = MigrationPhase(phase_name)
        except ValueError:
            return None

        result = await db.execute(
            select(MigrationProjectPhase).where(
                MigrationProjectPhase.project_id == project_id,
                MigrationProjectPhase.phase == phase_enum,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _check_phase_gate(
        phases: list[MigrationProjectPhase], target_phase: MigrationPhase
    ) -> Optional[str]:
        target_idx = PHASE_ORDER.index(target_phase)

        if target_idx == 0:
            return None  # Assessment has no prerequisite

        # Find the preceding phase
        prev_phase_enum = PHASE_ORDER[target_idx - 1]
        prev_phase = next((p for p in phases if p.phase == prev_phase_enum), None)

        if not prev_phase:
            return f"Previous phase '{prev_phase_enum.value}' not found"

        if prev_phase.status != MigrationPhaseStatus.COMPLETED:
            return (
                f"Phase '{prev_phase_enum.value}' must be completed first "
                f"(current status: {prev_phase.status})"
            )

        return None

    @classmethod
    async def upload_phase_file(
        cls,
        db: AsyncSession,
        project_id: int,
        phase_name: str,
        file_content: bytes,
        filename: str,
        created_by_id: int,
        duplicate_action: str = "skip",
        error_threshold: float = 10.0,
    ) -> dict[str, Any]:
        project = await cls.get_project(db, project_id)
        if not project:
            raise ValueError("Migration project not found")

        phase = await cls.get_phase(db, project_id, phase_name)
        if not phase:
            raise ValueError(f"Phase '{phase_name}' not found")

        # Check gate
        all_phases_result = await db.execute(
            select(MigrationProjectPhase)
            .where(MigrationProjectPhase.project_id == project_id)
        )
        all_phases = list(all_phases_result.scalars().all())
        gate_error = cls._check_phase_gate(all_phases, phase.phase)
        if gate_error:
            raise ValueError(gate_error)

        if phase.status not in (
            MigrationPhaseStatus.READY,
            MigrationPhaseStatus.FAILED,
            MigrationPhaseStatus.ROLLED_BACK,
        ):
            raise ValueError(
                f"Phase '{phase_name}' is in status '{phase.status}' — "
                f"must be 'ready', 'failed', or 'rolled_back' to upload"
            )

        # Assessment phase is special — no ImportJob, just analysis
        if phase.phase == MigrationPhase.ASSESSMENT:
            return await cls._run_assessment(db, project, phase, file_content, filename)

        # For data phases, create an ImportJob via ImportService
        from app.models.import_job import DuplicateAction
        try:
            dup = DuplicateAction(duplicate_action)
        except ValueError:
            dup = DuplicateAction.SKIP

        job_type = PHASE_JOB_TYPE.get(phase.phase)
        if not job_type:
            raise ValueError(f"No import type mapped for phase '{phase_name}'")

        job = await ImportService.upload(
            db=db,
            file_content=file_content,
            filename=filename,
            job_type=job_type,
            duplicate_action=dup,
            error_threshold=error_threshold,
            created_by_id=created_by_id,
        )

        # Auto-validate
        job = await ImportService.validate(db, job)

        # Link to phase
        phase.import_job_id = job.id
        phase.status = MigrationPhaseStatus.VALIDATED
        phase.total_records = job.total_rows

        # Update project status
        if project.status == MigrationProjectStatus.CREATED:
            project.status = MigrationProjectStatus.IN_PROGRESS
            project.started_at = datetime.now(timezone.utc)

        await db.flush()

        return {
            "phase": phase_name,
            "status": str(phase.status),
            "import_job_id": job.id,
            "total_rows": job.total_rows,
            "error_rows": job.error_rows,
            "validation_report": job.validation_report,
        }

    @classmethod
    async def _run_assessment(
        cls,
        db: AsyncSession,
        project: MigrationProject,
        phase: MigrationProjectPhase,
        file_content: bytes,
        filename: str,
    ) -> dict[str, Any]:
        phase.status = MigrationPhaseStatus.EXECUTING
        await db.flush()

        try:
            from app.services.import_service import (
                ImportService, _detect_file_format, ImportFileFormat
            )

            file_format = _detect_file_format(filename)
            report: dict[str, Any] = {
                "filename": filename,
                "file_size_bytes": len(file_content),
                "file_format": file_format.value,
            }

            # Parse and analyze
            import os, tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                if file_format in (ImportFileFormat.MARC21, ImportFileFormat.MARCXML):
                    rows = ImportService._read_marc(tmp_path, file_format)
                    report["record_type"] = "marc"
                elif file_format == ImportFileFormat.CSV:
                    rows = ImportService._read_csv(tmp_path)
                    report["record_type"] = "csv"
                else:
                    rows = ImportService._read_json(tmp_path)
                    report["record_type"] = "json"
            finally:
                os.unlink(tmp_path)

            report["total_rows"] = len(rows)

            if rows:
                # Field coverage analysis
                all_fields = set()
                field_counts: dict[str, int] = {}
                for row in rows:
                    for k, v in row.items():
                        all_fields.add(k)
                        if v and str(v).strip():
                            field_counts[k] = field_counts.get(k, 0) + 1

                report["detected_fields"] = sorted(all_fields)
                report["field_coverage"] = {
                    k: round(count / len(rows) * 100, 1)
                    for k, count in sorted(field_counts.items())
                }
                report["sample_rows"] = rows[:5]

                # Data quality flags
                warnings = []
                titles_missing = len(rows) - field_counts.get("title", 0)
                if titles_missing > 0:
                    warnings.append(f"{titles_missing} records missing title")
                isbns = [r.get("isbn", "").strip() for r in rows if r.get("isbn", "").strip()]
                if len(isbns) != len(set(isbns)):
                    warnings.append("Duplicate ISBNs detected")
                report["warnings"] = warnings
                report["readiness_score"] = "good" if not warnings else "needs_review"
            else:
                report["warnings"] = ["No records found in file"]
                report["readiness_score"] = "failed"

            project.assessment_report = report
            phase.status = MigrationPhaseStatus.COMPLETED
            phase.total_records = report.get("total_rows", 0)
            phase.created_records = report.get("total_rows", 0)
            phase.completed_at = datetime.now(timezone.utc)

            # Unlock next phase
            await cls._unlock_next_phase(db, project.id, phase.phase)

            if project.status == MigrationProjectStatus.CREATED:
                project.status = MigrationProjectStatus.IN_PROGRESS
                project.started_at = datetime.now(timezone.utc)

            await db.flush()
            return {"phase": "assessment", "status": "completed", "report": report}

        except Exception as e:
            phase.status = MigrationPhaseStatus.FAILED
            phase.error_log = {"error": str(e)}
            await db.flush()
            raise

    @classmethod
    async def execute_phase(
        cls,
        db: AsyncSession,
        project_id: int,
        phase_name: str,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        phase = await cls.get_phase(db, project_id, phase_name)
        if not phase:
            raise ValueError(f"Phase '{phase_name}' not found")

        if phase.phase == MigrationPhase.ASSESSMENT:
            raise ValueError("Assessment phase does not have an execute step")

        if phase.status != MigrationPhaseStatus.VALIDATED:
            raise ValueError(
                f"Phase must be validated before execution "
                f"(current: {phase.status})"
            )

        if not phase.import_job_id:
            raise ValueError("No import job linked to this phase")

        job = await ImportService.get_job(db, phase.import_job_id)
        if not job:
            raise ValueError("Linked import job not found")

        phase.status = MigrationPhaseStatus.EXECUTING
        phase.started_at = datetime.now(timezone.utc)
        await db.flush()

        try:
            job = await ImportService.execute(db, job, batch_size=batch_size)

            phase.created_records = job.created_rows
            phase.error_records = job.error_rows
            phase.skipped_records = job.skipped_rows

            if job.status == ImportJobStatus.COMPLETED:
                phase.status = MigrationPhaseStatus.COMPLETED
                phase.completed_at = datetime.now(timezone.utc)
                await cls._unlock_next_phase(db, project_id, phase.phase)
            elif job.status == ImportJobStatus.ROLLED_BACK:
                phase.status = MigrationPhaseStatus.FAILED
                phase.error_log = {"reason": "Error threshold exceeded, auto-rolled back"}
            else:
                phase.status = MigrationPhaseStatus.FAILED
                phase.error_log = {"reason": f"Import ended with status: {job.status}"}

            # Check if all phases complete
            await cls._check_project_completion(db, project_id)

            await db.flush()

            return {
                "phase": phase_name,
                "status": str(phase.status),
                "created": job.created_rows,
                "updated": job.updated_rows,
                "skipped": job.skipped_rows,
                "errors": job.error_rows,
            }

        except Exception as e:
            phase.status = MigrationPhaseStatus.FAILED
            phase.error_log = {"error": str(e)}
            await db.flush()
            raise

    @classmethod
    async def dry_run_phase(
        cls,
        db: AsyncSession,
        project_id: int,
        phase_name: str,
    ) -> dict[str, Any]:
        phase = await cls.get_phase(db, project_id, phase_name)
        if not phase:
            raise ValueError(f"Phase '{phase_name}' not found")

        if phase.status != MigrationPhaseStatus.VALIDATED:
            raise ValueError(f"Phase must be validated (current: {phase.status})")

        if not phase.import_job_id:
            raise ValueError("No import job linked to this phase")

        job = await ImportService.get_job(db, phase.import_job_id)
        if not job:
            raise ValueError("Linked import job not found")

        report = await ImportService.dry_run(db, job)
        return {"phase": phase_name, **report}

    @classmethod
    async def rollback_phase(
        cls,
        db: AsyncSession,
        project_id: int,
        phase_name: str,
        rolled_back_by_id: Optional[int] = None,
    ) -> dict[str, Any]:
        phase = await cls.get_phase(db, project_id, phase_name)
        if not phase:
            raise ValueError(f"Phase '{phase_name}' not found")

        if phase.status not in (
            MigrationPhaseStatus.COMPLETED,
            MigrationPhaseStatus.FAILED,
            MigrationPhaseStatus.EXECUTING,
        ):
            raise ValueError(f"Cannot rollback phase in status '{phase.status}'")

        rolled_back_count = 0
        if phase.import_job_id:
            job = await ImportService.get_job(db, phase.import_job_id)
            if job and job.status in (
                ImportJobStatus.COMPLETED, ImportJobStatus.FAILED, ImportJobStatus.IMPORTING
            ):
                job, rolled_back_count = await ImportService.rollback(
                    db, job,
                    rolled_back_by_id=rolled_back_by_id,
                    reason=f"Phase '{phase_name}' rollback",
                )

        phase.status = MigrationPhaseStatus.ROLLED_BACK
        phase.error_log = phase.error_log or {}

        # Re-lock subsequent phases
        await cls._relock_subsequent_phases(db, project_id, phase.phase)

        await db.flush()

        return {
            "phase": phase_name,
            "status": "rolled_back",
            "records_rolled_back": rolled_back_count,
        }

    @classmethod
    async def get_report(
        cls, db: AsyncSession, project_id: int
    ) -> dict[str, Any]:
        project = await cls.get_project(db, project_id)
        if not project:
            raise ValueError("Migration project not found")

        phases_result = await db.execute(
            select(MigrationProjectPhase)
            .where(MigrationProjectPhase.project_id == project_id)
            .order_by(MigrationProjectPhase.id)
        )
        phases = list(phases_result.scalars().all())

        phase_summaries = []
        total_created = 0
        total_errors = 0
        for p in phases:
            phase_summaries.append({
                "phase": str(p.phase),
                "status": str(p.status),
                "total_records": p.total_records,
                "created_records": p.created_records,
                "error_records": p.error_records,
                "skipped_records": p.skipped_records,
                "started_at": p.started_at.isoformat() if p.started_at else None,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            })
            total_created += p.created_records
            total_errors += p.error_records

        return {
            "project_id": project.id,
            "project_name": project.name,
            "status": str(project.status),
            "source_system": project.source_system_name,
            "cutover_strategy": str(project.cutover_strategy) if project.cutover_strategy else None,
            "total_records_created": total_created,
            "total_errors": total_errors,
            "phases": phase_summaries,
            "assessment_report": project.assessment_report,
            "started_at": project.started_at.isoformat() if project.started_at else None,
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        }

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    async def _unlock_next_phase(
        db: AsyncSession, project_id: int, current_phase: MigrationPhase
    ) -> None:
        current_idx = PHASE_ORDER.index(current_phase)
        if current_idx + 1 >= len(PHASE_ORDER):
            return  # No more phases

        next_phase_enum = PHASE_ORDER[current_idx + 1]
        result = await db.execute(
            select(MigrationProjectPhase).where(
                MigrationProjectPhase.project_id == project_id,
                MigrationProjectPhase.phase == next_phase_enum,
            )
        )
        next_phase = result.scalar_one_or_none()
        if next_phase and next_phase.status == MigrationPhaseStatus.LOCKED:
            next_phase.status = MigrationPhaseStatus.READY

    @staticmethod
    async def _relock_subsequent_phases(
        db: AsyncSession, project_id: int, from_phase: MigrationPhase
    ) -> None:
        from_idx = PHASE_ORDER.index(from_phase)
        for phase_enum in PHASE_ORDER[from_idx + 1:]:
            result = await db.execute(
                select(MigrationProjectPhase).where(
                    MigrationProjectPhase.project_id == project_id,
                    MigrationProjectPhase.phase == phase_enum,
                )
            )
            phase = result.scalar_one_or_none()
            if phase and phase.status != MigrationPhaseStatus.LOCKED:
                phase.status = MigrationPhaseStatus.LOCKED

    @staticmethod
    async def _check_project_completion(
        db: AsyncSession, project_id: int
    ) -> None:
        result = await db.execute(
            select(MigrationProjectPhase)
            .where(MigrationProjectPhase.project_id == project_id)
        )
        phases = list(result.scalars().all())

        # Required phases (all except historical_data)
        required = [p for p in phases if p.phase != MigrationPhase.HISTORICAL_DATA]
        if all(p.status == MigrationPhaseStatus.COMPLETED for p in required):
            project_result = await db.execute(
                select(MigrationProject).where(MigrationProject.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            if project:
                project.status = MigrationProjectStatus.COMPLETED
                project.completed_at = datetime.now(timezone.utc)
