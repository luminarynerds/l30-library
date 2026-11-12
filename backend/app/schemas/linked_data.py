# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Work List Response Schemas
# ============================================================================


class WorkListContributor(BaseModel):
    id: int
    name: str


class WorkListSubject(BaseModel):
    id: int
    label: str


class WorkListItem(BaseModel):
    id: int
    uri: str
    title: str
    subtitle: Optional[str] = None
    work_type: Optional[str] = None
    language: Optional[str] = None
    contributors: List[WorkListContributor] = Field(default_factory=list)
    subjects: List[WorkListSubject] = Field(default_factory=list)
    created_at: Optional[str] = None


class WorksListResponse(BaseModel):
    items: List[WorkListItem]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "uri": "http://example.org/works/1",
                        "title": "The Great Gatsby",
                        "subtitle": None,
                        "work_type": "text",
                        "language": "eng",
                        "contributors": [{"id": 1, "name": "F. Scott Fitzgerald"}],
                        "subjects": [{"id": 1, "label": "American literature"}],
                        "created_at": "2026-01-15T10:30:00"
                    }
                ],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "pages": 5
            }
        }


# ============================================================================
# Instance List Response Schemas
# ============================================================================


class InstanceListItem(BaseModel):
    id: int
    uri: str
    title: str
    isbn_13: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    work_id: Optional[int] = None
    work_title: Optional[str] = None


class InstancesListResponse(BaseModel):
    items: List[InstanceListItem]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "uri": "http://example.org/instances/1",
                        "title": "The Great Gatsby",
                        "isbn_13": "978-0743273565",
                        "publisher": "Scribner",
                        "publication_year": 2004,
                        "work_id": 1,
                        "work_title": "The Great Gatsby"
                    }
                ],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "pages": 3
            }
        }


# ============================================================================
# Item List Response Schemas
# ============================================================================


class ItemListItem(BaseModel):
    id: int
    uri: str
    barcode: Optional[str] = None
    call_number: Optional[str] = None
    branch: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    instance_id: Optional[int] = None
    instance_title: Optional[str] = None


class ItemsListResponse(BaseModel):
    items: List[ItemListItem]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "uri": "http://example.org/items/1",
                        "barcode": "31234567890123",
                        "call_number": "PS3511.I9 G7 2004",
                        "branch": "Main Library",
                        "location": "Fiction",
                        "status": "available",
                        "instance_id": 1,
                        "instance_title": "The Great Gatsby"
                    }
                ],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "pages": 2
            }
        }


# ============================================================================
# LOC Import Response Schemas
# ============================================================================


class LocImportWorkInfo(BaseModel):
    id: int
    uri: Optional[str] = None
    title: str


class LocImportInstanceInfo(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None


class LocImportResponse(BaseModel):
    work: LocImportWorkInfo
    instances: List[LocImportInstanceInfo] = Field(default_factory=list)
    contributors_count: int = 0
    subjects_count: int = 0
    warnings: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "work": {
                    "id": 1,
                    "uri": "http://id.loc.gov/resources/works/12345",
                    "title": "The Great Gatsby"
                },
                "instances": [
                    {
                        "id": 1,
                        "title": "The Great Gatsby",
                        "isbn": "978-0743273565"
                    }
                ],
                "contributors_count": 1,
                "subjects_count": 3,
                "warnings": []
            }
        }
