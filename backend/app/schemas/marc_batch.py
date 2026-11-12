# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class MarcImportPreviewRecord(BaseModel):
    index: int
    title: str | None
    author: str | None
    isbn: str | None
    lccn: str | None
    publisher: str | None
    year: str | None
    match_found: bool = False
    matched_item_id: int | None = None
    matched_item_title: str | None = None
    action: str = "import"  # import, merge, skip


class MarcImportPreviewResponse(BaseModel):
    job_id: int
    file_name: str
    total_records: int
    records: list[MarcImportPreviewRecord]
    duplicate_count: int


class MarcImportDecision(BaseModel):
    index: int
    action: str  # import, merge, skip


class MarcImportExecuteRequest(StrictInputSchema):
    decisions: list[MarcImportDecision]


class MarcExportRequest(StrictInputSchema):
    format: str = "marc21"  # marc21, marcxml
    item_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    collection: str | None = None
    incremental_since: datetime | None = None
    catalog_item_id: int | None = None
    catalog_item_ids: list[int] | None = None


class MarcBatchJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    file_name: str | None
    file_format: str | None
    total_records: int
    processed: int
    created_count: int
    updated_count: int
    skipped: int
    errors: list[dict]
    completed_at: datetime | None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class MarcBatchJobListResponse(BaseModel):
    items: list[MarcBatchJobResponse]
    total: int
    page: int
    per_page: int
