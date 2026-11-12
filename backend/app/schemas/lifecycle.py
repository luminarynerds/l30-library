# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas._base import StrictInputSchema

from ..models.lifecycle import LifecycleEventType


class LifecycleEventCreate(StrictInputSchema):

    item_copy_id: int
    event_type: LifecycleEventType
    description: Optional[str] = None
    metadata: dict = {}
    related_checkout_id: Optional[int] = None
    related_po_id: Optional[int] = None
    related_audit_id: Optional[int] = None
    related_weeding_id: Optional[int] = None


class LifecycleEventResponse(BaseModel):

    id: int
    item_copy_id: int
    event_type: LifecycleEventType
    description: Optional[str] = None
    metadata: dict
    performed_by_id: Optional[int] = None
    related_checkout_id: Optional[int] = None
    related_po_id: Optional[int] = None
    related_audit_id: Optional[int] = None
    related_weeding_id: Optional[int] = None
    created_at: datetime | None = None
    # Include performer details for convenience
    performed_by_name: Optional[str] = None
    performed_by_email: Optional[str] = None

    # Include item copy details for convenience
    item_copy_barcode: Optional[str] = None
    item_title: Optional[str] = None
    item_author: Optional[str] = None

    class Config:
        from_attributes = True


class LifecycleTimelineResponse(BaseModel):

    item_copy_id: int
    item_copy_barcode: Optional[str] = None
    item_title: Optional[str] = None
    item_author: Optional[str] = None
    events: list[LifecycleEventResponse]
    total_events: int
