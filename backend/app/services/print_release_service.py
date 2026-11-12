# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.print import PrintJob, PrintJobStatus, Printer, PrintReleaseStation
from app.services import account_service

logger = get_logger(__name__)


async def release_job(
    db: AsyncSession,
    job_id: int,
    patron_id: int,
    payment_method: Optional[str] = "account_balance",
) -> PrintJob:
    result = await db.execute(
        select(PrintJob).where(PrintJob.id == job_id, PrintJob.user_id == patron_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    if job.status not in (PrintJobStatus.submitted, PrintJobStatus.held):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be released from status '{job.status}'"
        )

    # Process payment
    if payment_method == "account_balance":
        await account_service.charge(
            db, patron_id,
            amount=Decimal(str(job.cost)),
            description=f"Print job: {job.job_name}",
            reference_type="print_job",
            reference_id=job.id,
        )
        job.payment_method = "account_balance"
        job.payment_processed = True
        job.payment_amount_charged = job.cost
        job.account_balance_used = job.cost

    job.status = PrintJobStatus.queued
    job.release_timestamp = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)

    logger.info(f"Print job {job.id} released for patron {patron_id}")
    return job
