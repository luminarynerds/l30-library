# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie content warning preference endpoints."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.indie_content_preference import IndieContentPreference
from ...models.user import User
from ..v1.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/content-preferences", tags=["indie-content-preferences"])


class PreferencesResponse(BaseModel):
    hidden_warnings: list[str]
    flagged_warnings: list[str]


class PreferencesUpdate(BaseModel):
    hidden_warnings: list[str] = []
    flagged_warnings: list[str] = []


@router.get("", response_model=PreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get content warning preferences. Returns empty lists if none set."""
    stmt = select(IndieContentPreference).where(IndieContentPreference.user_id == user.id)
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()
    if not pref:
        return PreferencesResponse(hidden_warnings=[], flagged_warnings=[])
    return PreferencesResponse(
        hidden_warnings=pref.hidden_warnings or [],
        flagged_warnings=pref.flagged_warnings or [],
    )


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert content warning preferences."""
    stmt = pg_insert(IndieContentPreference).values(
        user_id=user.id,
        hidden_warnings=body.hidden_warnings,
        flagged_warnings=body.flagged_warnings,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        set_=dict(
            hidden_warnings=body.hidden_warnings,
            flagged_warnings=body.flagged_warnings,
        ),
    ).returning(IndieContentPreference)
    result = await db.execute(stmt)
    await db.commit()
    pref = result.scalar_one()
    return PreferencesResponse(
        hidden_warnings=pref.hidden_warnings or [],
        flagged_warnings=pref.flagged_warnings or [],
    )


@router.get("/categories", response_model=list[str])
async def list_warning_categories():
    """Get all known content warning categories from the indie catalog."""
    return sorted([
        "violence", "sexual content", "strong language", "drug use",
        "alcohol", "self-harm", "suicide", "abuse", "gore",
        "racism", "homophobia", "transphobia", "death",
        "animal cruelty", "eating disorders", "mental health",
        "religious themes", "political themes", "war",
    ])
