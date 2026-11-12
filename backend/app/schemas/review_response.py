# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# Validation-Sync Report
# Frontend files that consume this schema's constraints:
#   - frontend/src/pages/StaffReviewResponsesPage.tsx  (content min_length/maxLength)
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime
from pydantic import BaseModel, Field
from ._base import StrictInputSchema


class ReviewResponseBase(BaseModel):
    content: str = Field(..., min_length=10, max_length=2000,
                        description="Response content from author or staff")


class EventReviewResponseCreate(ReviewResponseBase, StrictInputSchema):
    pass


class EventReviewResponseUpdate(StrictInputSchema):
    content: str = Field(..., min_length=10, max_length=2000)


class EventReviewResponseResponse(ReviewResponseBase):
    id: int
    review_id: int
    author_id: int
    author_name: str | None
    author_email: str | None
    is_staff_response: bool
    moderation_status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True



class ReviewResponseApprovalRequest(StrictInputSchema):
    approved: bool
    reason: str | None = None
