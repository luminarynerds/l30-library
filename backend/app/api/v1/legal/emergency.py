# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for emergency legal resources.

This module handles emergency legal resources including
hotlines, crisis centers, and emergency filing information.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....schemas.legal import (
    EmergencyResourceResponse, EmergencyResourceListResponse,
)
from ....services import legal_service

router = APIRouter(prefix="/legal", tags=["legal-resources"])


# ============================================================================
# Emergency Resources
# ============================================================================

@router.get("/emergency", response_model=EmergencyResourceListResponse)
async def list_emergency_resources(
    situation: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List emergency legal resources.

    Includes hotlines, crisis centers, and emergency filing information.
    """
    resources = await legal_service.list_emergency_resources(
        db, situation=situation, is_featured=is_featured
    )
    return {
        "resources": [_emergency_to_response(r) for r in resources],
        "total": len(resources)
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _emergency_to_response(resource) -> dict:
    return {
        "id": resource.id,
        "name": resource.name,
        "resource_type": resource.resource_type,
        "situation": resource.situation,
        "phone": resource.phone,
        "phone_toll_free": resource.phone_toll_free,
        "text_number": resource.text_number,
        "website": resource.website,
        "description": resource.description,
        "when_to_call": resource.when_to_call,
        "is_24_7": resource.is_24_7,
        "hours_description": resource.hours_description,
        "languages_available": resource.languages_available or ["English"],
        "is_featured": resource.is_featured
    }
