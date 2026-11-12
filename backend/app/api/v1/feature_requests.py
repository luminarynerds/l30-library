# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lightweight write-only feature-request collection endpoint.

Used by the AlternateFormatsRequestPage (and future similar
demand-collection surfaces) to log coordinator interest without
committing to a ship date. Logs to the standard logger; downstream
triage queries log/Sentry events.

Intentionally minimal: no database write, no email send, no
notification fan-out. The signal is the log line; promote to a
real schema only when demand justifies it.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from .auth import get_current_user_optional
from app.core.logging import get_logger
from app.models.user import User

router = APIRouter(prefix="/feature-requests", tags=["feature-requests"])
logger = get_logger("l30.feature_requests")


class FeatureRequest(BaseModel):
    feature: str = Field(..., min_length=1, max_length=128)
    lesson: Optional[str] = Field(None, max_length=512)
    email: EmailStr


@router.post("", status_code=201)
async def submit_feature_request(  # noqa: role-check (public form)
    body: FeatureRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Log a feature-request signal.

    Anonymous posts are accepted (no auth required) so the page can be
    reachable from anywhere the link lands. ``user_id`` is included in
    the log line when an authenticated session is present.
    """
    logger.info(
        "feature_request feature=%s lesson=%r email=%s user_id=%s",
        body.feature,
        body.lesson,
        body.email,
        getattr(user, "id", None),
    )
    return {"status": "received"}
