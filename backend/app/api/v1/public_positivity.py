# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Public Positivity Submission Endpoint

Allows patrons to submit positive experiences without authentication.
Submissions go into a moderation queue before appearing on the joy board.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.positivity import PositivityEntry, PositivityEntryType
from ...schemas.positivity import PatronPositivitySubmission, PatronSubmissionResponse

router = APIRouter(prefix="/public/positivity", tags=["public-positivity"])


@router.post("", response_model=PatronSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_patron_positivity(
    submission: PatronPositivitySubmission,
    db: AsyncSession = Depends(get_db),
):
    """Submit a positive library experience (no auth required). Goes to moderation queue."""
    try:
        PositivityEntryType(submission.entry_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry type. Must be one of: {', '.join([t.value for t in PositivityEntryType])}",
        ) from None

    entry = PositivityEntry(
        organization_id=1,
        user_id=None,
        entry_type=submission.entry_type,
        text=submission.text,
        source="patron",
        patron_name=submission.patron_name,
        patron_email=submission.patron_email,
        moderation_status="pending",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return PatronSubmissionResponse(
        message="Thank you for sharing your experience! Our staff will review your submission.",
        id=entry.id,
    )
