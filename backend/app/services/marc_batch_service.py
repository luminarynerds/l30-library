# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from app.core.logging import get_logger
from datetime import datetime, timezone

from pymarc import MARCReader
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marc_batch import MarcBatchJob, MarcBatchJobType, MarcBatchJobStatus
from app.models.catalog import CatalogItem, ItemType, ItemStatus
from app.services.catalog_marc_service import catalog_marc_service

logger = get_logger(__name__)


class MarcBatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def parse_upload(
        self, file_content: bytes, file_name: str, file_format: str, user_id: int,
    ) -> tuple[MarcBatchJob, list[dict]]:
        job = MarcBatchJob(
            job_type=MarcBatchJobType.import_job,
            status=MarcBatchJobStatus.pending,
            file_name=file_name,
            file_format=file_format,
            created_by_id=user_id,
        )
        self.db.add(job)
        await self.db.flush()

        records = []
        if file_format == "marc21":
            # force_utf8=False (default) lets pymarc inspect MARC leader byte 9
            # to choose the encoding: 'a' decodes as UTF-8, ' ' (space) decodes
            # as MARC-8 via pymarc.marc8_to_unicode. Hard-coding force_utf8=True
            # silently corrupts MARC-8 input from older Polaris/Sierra/Koha/
            # Evergreen exports, replacing diacritics and non-Roman scripts
            # with U+FFFD.
            reader = MARCReader(io.BytesIO(file_content), to_unicode=True)
        else:
            # For MARCXML, pymarc handles it differently
            from pymarc import parse_xml_to_array
            reader = parse_xml_to_array(io.BytesIO(file_content))

        for idx, record in enumerate(reader):
            if record is None:
                continue
            title = record.title() if hasattr(record, "title") else str(record.get("245", ""))
            author = record.author() if hasattr(record, "author") else str(record.get("100", ""))
            isbn = record.isbn() if hasattr(record, "isbn") else None
            lccn = str(record.get("010", "")).strip() if record.get("010") else None
            publisher = str(record.get("260", {}).get("b", "")) if record.get("260") else None
            year = str(record.get("260", {}).get("c", "")) if record.get("260") else None

            # Check for existing match by ISBN
            match_id = None
            match_title = None
            if isbn:
                existing = await self.db.execute(
                    select(CatalogItem.id, CatalogItem.title).where(CatalogItem.isbn == isbn).limit(1)
                )
                row = existing.first()
                if row:
                    match_id = row.id
                    match_title = row.title

            records.append({
                "index": idx,
                "title": title,
                "author": author,
                "isbn": isbn,
                "lccn": lccn,
                "publisher": publisher,
                "year": year,
                "match_found": match_id is not None,
                "matched_item_id": match_id,
                "matched_item_title": match_title,
                "action": "merge" if match_id else "import",
            })

        job.total_records = len(records)
        await self.db.flush()
        await self.db.refresh(job)
        return job, records

    async def execute_import(
        self, job_id: int, decisions: list[dict],
    ) -> MarcBatchJob:
        result = await self.db.execute(
            select(MarcBatchJob).where(MarcBatchJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = MarcBatchJobStatus.processing
        created = 0
        updated = 0
        skipped = 0
        errors = []

        for decision in decisions:
            try:
                if decision["action"] == "skip":
                    skipped += 1
                elif decision["action"] == "import":
                    # Create new CatalogItem from MARC data
                    item = CatalogItem(
                        title=decision.get("title", "Unknown"),
                        author=decision.get("author"),
                        isbn=decision.get("isbn"),
                        publisher=decision.get("publisher"),
                        publication_year=self._extract_year(decision.get("year")),
                        item_type=ItemType.book,
                        status=ItemStatus.in_processing,
                    )
                    self.db.add(item)
                    created += 1
                elif decision["action"] == "merge":
                    if decision.get("matched_item_id"):
                        item_result = await self.db.execute(
                            select(CatalogItem).where(CatalogItem.id == decision["matched_item_id"])
                        )
                        item = item_result.scalar_one_or_none()
                        if item:
                            # Fill in missing fields only
                            if not item.publisher and decision.get("publisher"):
                                item.publisher = decision["publisher"]
                            if not item.publication_year and decision.get("year"):
                                item.publication_year = self._extract_year(decision["year"])
                            updated += 1
            except Exception as e:  # noqa: BLE001 -- per-record boundary: one MARC record failure must not crash batch import
                errors.append({"index": decision.get("index", -1), "error": str(e)})
                logger.warning(f"MARC import error at index {decision.get('index')}: {e}")

        job.processed = created + updated + skipped
        job.created_count = created
        job.updated_count = updated
        job.skipped = skipped
        job.errors = errors
        job.status = MarcBatchJobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def generate_export(
        self, *, file_format: str, user_id: int,
        item_type: str | None = None, date_from: datetime | None = None,
        date_to: datetime | None = None, incremental_since: datetime | None = None,
        catalog_item_id: int | None = None,
        catalog_item_ids: list[int] | None = None,
    ) -> tuple[MarcBatchJob, bytes]:
        job = MarcBatchJob(
            job_type=MarcBatchJobType.export_job,
            status=MarcBatchJobStatus.processing,
            file_format=file_format,
            created_by_id=user_id,
            filter_criteria={
                "item_type": item_type,
                "date_from": str(date_from) if date_from else None,
                "date_to": str(date_to) if date_to else None,
                "incremental_since": str(incremental_since) if incremental_since else None,
                "catalog_item_id": catalog_item_id,
                "catalog_item_ids": catalog_item_ids,
            },
        )
        self.db.add(job)
        await self.db.flush()

        query = select(CatalogItem).where(CatalogItem.status != ItemStatus.withdrawn)
        if catalog_item_id is not None:
            query = query.where(CatalogItem.id == catalog_item_id)
        elif catalog_item_ids:
            query = query.where(CatalogItem.id.in_(catalog_item_ids))
        else:
            if item_type:
                query = query.where(CatalogItem.item_type == item_type)
            if date_from:
                query = query.where(CatalogItem.created_at >= date_from)
            if date_to:
                query = query.where(CatalogItem.created_at <= date_to)
            if incremental_since:
                query = query.where(CatalogItem.updated_at >= incremental_since)

        result = await self.db.execute(query.order_by(CatalogItem.id))
        items = list(result.scalars().all())

        records = [catalog_marc_service.create_marc_record(item) for item in items]
        if file_format == "marcxml":
            file_bytes = catalog_marc_service.export_marcxml_batch(records).encode("utf-8")
        else:
            file_bytes = catalog_marc_service.export_marc21_batch(records)

        job.total_records = len(items)
        job.processed = len(items)
        job.status = MarcBatchJobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        job.file_name = f"export_{job.id}.{'xml' if file_format == 'marcxml' else 'mrc'}"
        await self.db.flush()
        await self.db.refresh(job)
        return job, file_bytes

    async def list_jobs(
        self, *, page: int = 1, per_page: int = 20,
        job_type: str | None = None,
    ) -> tuple[list[MarcBatchJob], int]:
        query = select(MarcBatchJob)
        count_query = select(func.count(MarcBatchJob.id))
        if job_type:
            query = query.where(MarcBatchJob.job_type == job_type)
            count_query = count_query.where(MarcBatchJob.job_type == job_type)
        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(MarcBatchJob.created_at.desc()).offset(offset).limit(per_page)
        )
        return list(result.scalars().all()), total

    @staticmethod
    def _extract_year(year_str: str | None) -> int | None:
        if not year_str:
            return None
        import re
        match = re.search(r"(\d{4})", year_str)
        return int(match.group(1)) if match else None
