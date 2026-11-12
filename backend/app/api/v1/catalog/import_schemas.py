# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel


class ImportPreviewRecord(BaseModel):
    title: str
    author: str | None = None
    isbn: str | None = None
    item_type: str | None = None
    year: str | None = None


class ImportPreviewResponse(BaseModel):
    upload_id: str
    total_records: int
    preview: list[ImportPreviewRecord]
    format: str


class CsvFieldMapping(BaseModel):
    title: str
    author: str | None = None
    isbn: str | None = None
    item_type: str | None = None
    year: str | None = None


class ImportRequest(BaseModel):
    upload_id: str
    field_mapping: CsvFieldMapping | None = None
    skip_invalid: bool = True


class ImportResult(BaseModel):
    imported: int
    skipped: int
    duplicates_merged: int
    errors: list[str]


class CsvHeadersResponse(BaseModel):
    upload_id: str
    headers: list[str]
