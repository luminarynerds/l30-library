# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class CachedPatron(BaseModel):
    barcode: str
    id: int
    name: str
    photo_url: Optional[str] = None
    status: str
    checkout_count: int
    checkout_limit: int
    card_expiry: Optional[str] = None


class CachedItem(BaseModel):
    barcode: str
    id: int
    title: str
    author: str
    status: str
    branch_id: int
    call_number: Optional[str] = None
    media_type: str


class PrepareRouteResponse(BaseModel):
    patrons: List[CachedPatron]
    items: List[CachedItem]
    patron_count: int
    item_count: int
    generated_at: datetime


class DepartRequest(StrictInputSchema):
    branch_id: int
    items_cached: int = 0
    patrons_cached: int = 0


class DepartResponse(BaseModel):
    session_id: int
    offline_session_token: str
    status: str


class ReturnRequest(StrictInputSchema):
    session_id: int


class ReturnResponse(BaseModel):
    session_id: int
    status: str


class SyncOperation(BaseModel):
    client_op_id: str = Field(max_length=50)
    type: Literal["checkout", "checkin", "renew"]
    patron_barcode: Optional[str] = None
    item_barcode: str
    timestamp: str


class SyncRequest(StrictInputSchema):
    session_id: int
    operations: List[SyncOperation]


class SyncOperationResult(BaseModel):
    client_op_id: str
    status: Literal["synced", "conflict", "failed"]
    detail: Optional[str] = None


class SyncResponse(BaseModel):
    session_id: int
    results: List[SyncOperationResult]
    synced: int
    conflicts: int
    failed: int
