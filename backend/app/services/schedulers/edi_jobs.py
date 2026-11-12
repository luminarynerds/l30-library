# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from ...core.database import AsyncSessionLocal
from ...core.logging import get_logger
from ...models.job_failure import JobSeverity
from ..job_failure_service import JobExecutionContext

logger = get_logger(__name__)


async def poll_edi_inbound_messages() -> None:
    async with JobExecutionContext(
        job_id="edi_inbound_polling",
        job_name="EDI Inbound Message Polling",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from ..edi.edi_processor import EDIProcessor

            processor = EDIProcessor(db)
            results = await processor.process_inbound_messages()

            ctx.add_metric("vendors_processed", results["vendors_processed"])
            ctx.add_metric("files_processed", results["files_processed"])
            ctx.add_metric("transactions_created", results["transactions_created"])

            for error in results.get("errors", []):
                ctx.record_failure(
                    error=Exception(str(error)),
                    entity_type="edi_inbound",
                )

            if not results.get("errors"):
                ctx.record_success()

            logger.info(
                "EDI inbound polling completed",
                extra={
                    "vendors_processed": results["vendors_processed"],
                    "files_processed": results["files_processed"],
                    "transactions_created": results["transactions_created"],
                    "errors": len(results.get("errors", [])),
                },
            )


async def process_edi_retries() -> None:
    async with JobExecutionContext(
        job_id="edi_retry_processing",
        job_name="EDI Retry Processing",
        severity=JobSeverity.LOW,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            from ..edi.edi_processor import EDIProcessor

            processor = EDIProcessor(db)
            results = await processor.process_pending_retries()

            ctx.add_metric("processed", results["processed"])
            ctx.add_metric("succeeded", results["succeeded"])
            ctx.add_metric("failed", results["failed"])

            for error in results.get("errors", []):
                ctx.record_failure(
                    error=Exception(str(error.get("error", "Unknown error"))),
                    entity_type="edi_transaction",
                    entity_id=error.get("transaction_id"),
                )

            if not results.get("errors"):
                ctx.record_success()

            logger.info(
                "EDI retry processing completed",
                extra={
                    "processed": results["processed"],
                    "succeeded": results["succeeded"],
                    "failed": results["failed"],
                },
            )
