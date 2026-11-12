# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Digital Resource Service Status API

Returns operational status of external digital resource services.
Currently returns mock data; will be replaced with real health checks
when vendor APIs support it.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/digital-resources",
    tags=["Digital Resources"],
)


class ServiceStatus(BaseModel):
    name: str
    status: Literal["operational", "degraded", "down"]
    last_checked: str


class ServiceStatusResponse(BaseModel):
    services: List[ServiceStatus]


def _mock_statuses() -> List[ServiceStatus]:
    now = datetime.now(timezone.utc)
    services = [
        ("MetisLibrary", "operational", now - timedelta(minutes=2)),
        ("Palace Project", "operational", now - timedelta(minutes=5)),
        ("Project Gutenberg", "operational", now - timedelta(minutes=3)),
        ("Freegal Music", "operational", now - timedelta(minutes=4)),
        ("PressReader", "operational", now - timedelta(minutes=1)),
        ("Consumer Reports", "operational", now - timedelta(minutes=6)),
        ("Mango Languages", "operational", now - timedelta(minutes=2)),
        ("Ancestry Library Edition", "operational", now - timedelta(minutes=7)),
    ]
    return [
        ServiceStatus(name=name, status=status, last_checked=checked.isoformat())
        for name, status, checked in services
    ]


@router.get("/status", response_model=ServiceStatusResponse)
async def get_digital_resource_status() -> ServiceStatusResponse:
    """Public endpoint returning current status of digital resource services."""
    return ServiceStatusResponse(services=_mock_statuses())
