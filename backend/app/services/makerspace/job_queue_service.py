# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.makerspace import (
    MakerspaceJob,
    ResourceStatus,
    JobStatus,
    JobPriority,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class JobQueueService(BaseMakerspaceService[MakerspaceJob]):
    model = MakerspaceJob

    @staticmethod
    def _generate_job_number() -> str:
        return f"JOB-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    @staticmethod
    async def get_jobs(
        db: AsyncSession,
        *,
        user_id: int | None = None,
        resource_id: int | None = None,
        status: JobStatus | None = None,
        priority: JobPriority | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[MakerspaceJob], int]:
        query = select(MakerspaceJob)
        count_query = select(func.count(MakerspaceJob.id))

        if user_id:
            query = query.where(MakerspaceJob.user_id == user_id)
            count_query = count_query.where(MakerspaceJob.user_id == user_id)

        if resource_id:
            query = query.where(MakerspaceJob.resource_id == resource_id)
            count_query = count_query.where(MakerspaceJob.resource_id == resource_id)

        if status:
            query = query.where(MakerspaceJob.status == status)
            count_query = count_query.where(MakerspaceJob.status == status)

        if priority:
            query = query.where(MakerspaceJob.priority == priority)
            count_query = count_query.where(MakerspaceJob.priority == priority)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = (
            query.options(selectinload(MakerspaceJob.resource), selectinload(MakerspaceJob.user))
            .offset(offset)
            .limit(per_page)
            .order_by(MakerspaceJob.created_at.desc())
        )

        result = await db.execute(query)
        jobs = list(result.scalars().all())

        return jobs, total

    @staticmethod
    async def get_queue(db: AsyncSession, resource_id: int | None = None) -> list[MakerspaceJob]:
        query = select(MakerspaceJob).where(
            MakerspaceJob.status.in_([JobStatus.approved, JobStatus.queued, JobStatus.in_progress])
        )

        if resource_id:
            query = query.where(MakerspaceJob.resource_id == resource_id)

        query = query.order_by(
            MakerspaceJob.priority.desc(),
            MakerspaceJob.queue_position.nullsfirst(),
            MakerspaceJob.created_at,
        )

        result = await db.execute(
            query.options(selectinload(MakerspaceJob.user), selectinload(MakerspaceJob.resource))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: int) -> MakerspaceJob | None:
        result = await db.execute(
            select(MakerspaceJob)
            .options(selectinload(MakerspaceJob.resource), selectinload(MakerspaceJob.user))
            .where(MakerspaceJob.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_job_number(db: AsyncSession, job_number: str) -> MakerspaceJob | None:
        result = await db.execute(
            select(MakerspaceJob)
            .options(selectinload(MakerspaceJob.resource), selectinload(MakerspaceJob.user))
            .where(MakerspaceJob.job_number == job_number)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def submit(
        db: AsyncSession, user_id: int, data: dict, file_info: dict | None = None
    ) -> MakerspaceJob:
        job = MakerspaceJob(
            job_number=JobQueueService._generate_job_number(),
            user_id=user_id,
            status=JobStatus.submitted,
            **data,
        )

        if file_info:
            job.file_name = file_info.get("file_name")
            job.file_path = file_info.get("file_path")
            job.file_size_bytes = file_info.get("file_size_bytes")
            job.file_format = file_info.get("file_format")

        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def review(
        db: AsyncSession,
        job: MakerspaceJob,
        reviewed_by_id: int,
        approved: bool,
        notes: str | None = None,
        rejection_reason: str | None = None,
        estimates: dict | None = None,
    ) -> MakerspaceJob:
        if job.status not in [JobStatus.submitted, JobStatus.pending_review]:
            raise ValueError(f"Cannot review job in {job.status} status")

        job.reviewed_by_id = reviewed_by_id
        job.reviewed_at = datetime.now(timezone.utc)
        job.review_notes = notes

        if approved:
            job.status = JobStatus.approved

            if estimates:
                job.estimated_print_time_minutes = estimates.get("print_time_minutes")
                job.estimated_material_grams = estimates.get("material_grams")
                # estimated_cost is NOT NULL. The caller always supplies a "cost" key,
                # so .get()'s default never fires -- a review that omits the cost would
                # send None and the UPDATE would violate the constraint.
                cost = estimates.get("cost")
                job.estimated_cost = Decimal("0.00") if cost is None else cost

            # Calculate queue position
            max_pos_result = await db.execute(
                select(func.max(MakerspaceJob.queue_position))
                .where(MakerspaceJob.resource_id == job.resource_id)
                .where(MakerspaceJob.status.in_([JobStatus.approved, JobStatus.queued]))
            )
            max_pos = max_pos_result.scalar() or 0
            job.queue_position = max_pos + 1
        else:
            job.status = JobStatus.rejected
            job.rejection_reason = rejection_reason

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def start_job(db: AsyncSession, job: MakerspaceJob) -> MakerspaceJob:
        if job.status not in [JobStatus.approved, JobStatus.queued]:
            raise ValueError(f"Cannot start job in {job.status} status")

        job.status = JobStatus.in_progress
        job.started_at = datetime.now(timezone.utc)

        # Update resource status
        if job.resource:
            job.resource.status = ResourceStatus.in_use

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def complete_job(
        db: AsyncSession,
        job: MakerspaceJob,
        actual_time_minutes: int,
        actual_material_grams: Decimal,
        consumables_used: list[dict] | None = None,
        notes: str | None = None,
    ) -> MakerspaceJob:
        # Import here to avoid circular imports
        from .consumable_service import ConsumableService

        if job.status != JobStatus.in_progress:
            raise ValueError(f"Cannot complete job in {job.status} status")

        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        job.actual_print_time_minutes = actual_time_minutes
        job.actual_material_grams = actual_material_grams

        if notes:
            job.staff_notes = (job.staff_notes or "") + f"\nCompleted: {notes}"

        # Calculate actual cost
        material_cost = Decimal("0.00")
        if consumables_used:
            for item in consumables_used:
                usage = await ConsumableService.record_usage(
                    db,
                    consumable_id=item["consumable_id"],
                    quantity=item["quantity_used"],
                    job_id=job.id,
                    resource_id=job.resource_id,
                )
                material_cost += usage.cost

        job.material_cost = material_cost

        # Calculate machine time cost
        if job.resource and job.actual_print_time_minutes:
            hours = Decimal(job.actual_print_time_minutes) / Decimal(60)
            job.machine_time_cost = job.resource.hourly_cost * hours

        job.actual_cost = job.material_cost + job.machine_time_cost

        # Update resource status
        if job.resource:
            job.resource.status = ResourceStatus.available

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def mark_ready_for_pickup(db: AsyncSession, job: MakerspaceJob) -> MakerspaceJob:
        if job.status != JobStatus.completed:
            raise ValueError(f"Cannot mark job as ready in {job.status} status")

        job.status = JobStatus.ready_pickup
        job.ready_for_pickup_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def mark_picked_up(
        db: AsyncSession, job: MakerspaceJob, picked_up_by_id: int | None = None
    ) -> MakerspaceJob:
        if job.status != JobStatus.ready_pickup:
            raise ValueError(f"Cannot mark as picked up: job is in {job.status} status")

        job.status = JobStatus.picked_up
        job.picked_up_at = datetime.now(timezone.utc)
        job.picked_up_by_id = picked_up_by_id

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def fail_job(db: AsyncSession, job: MakerspaceJob, failure_reason: str) -> MakerspaceJob:
        if job.status != JobStatus.in_progress:
            raise ValueError(f"Cannot fail job in {job.status} status")

        job.status = JobStatus.failed
        job.failed_at = datetime.now(timezone.utc)
        job.failure_reason = failure_reason

        # Update resource status
        if job.resource:
            job.resource.status = ResourceStatus.available

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def cancel_job(
        db: AsyncSession, job: MakerspaceJob, reason: str | None = None
    ) -> MakerspaceJob:
        if job.status in [JobStatus.completed, JobStatus.picked_up, JobStatus.cancelled]:
            raise ValueError(f"Cannot cancel job in {job.status} status")

        job.status = JobStatus.cancelled
        if reason:
            job.staff_notes = (job.staff_notes or "") + f"\nCancelled: {reason}"

        # Update resource status if was in progress
        if job.resource and job.resource.status == ResourceStatus.in_use:
            job.resource.status = ResourceStatus.available

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def reorder_queue(db: AsyncSession, job_ids: list[int]) -> list[MakerspaceJob]:
        jobs = []
        for position, job_id in enumerate(job_ids, start=1):
            result = await db.execute(select(MakerspaceJob).where(MakerspaceJob.id == job_id))
            job = result.scalar_one_or_none()
            if job and job.status in [JobStatus.approved, JobStatus.queued]:
                job.queue_position = position
                jobs.append(job)

        await db.commit()
        return jobs
