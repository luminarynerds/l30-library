# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron digital resource usage summary.

Real vendor integrations (Freegal, Palace, MetisLib) are not wired up yet,
so this returns an empty summary. The UI panel hides itself when empty.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...models.user import User
from .dependencies import get_current_user

router = APIRouter(prefix="/patron/digital-activity", tags=["patron-digital-activity"])


class ActiveCheckout(BaseModel):
    service: str
    title: str
    due_date: str


class DownloadQuota(BaseModel):
    service: str
    used: int
    limit: int
    period: str


class RecentService(BaseModel):
    service: str
    last_used: str


class DigitalActivitySummary(BaseModel):
    active_checkouts: list[ActiveCheckout]
    download_quotas: list[DownloadQuota]
    recent_services: list[RecentService]


@router.get("", response_model=DigitalActivitySummary)
async def get_digital_activity(
    current_user: User = Depends(get_current_user),
):
    """Return the current patron's digital resource usage summary."""
    return DigitalActivitySummary(
        active_checkouts=[],
        download_quotas=[],
        recent_services=[],
    )
