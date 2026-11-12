# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strategic planning - File attachment operations endpoints."""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.file_validation import validate_file_type, validate_file_size
from app.models.user import User
from app.schemas.strategic import AttachmentResponse
from app.services import strategic_service as svc
from ..auth import get_current_user
from .common import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/strategic", tags=["strategic-attachments"])


@router.post("/goals/{goal_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(
    goal_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an attachment to a goal (staff/admin)."""
    await require_staff(current_user)
    content = await file.read()

    # Magic-byte validation: reject files whose content doesn't match an allowed type
    content_start = content[:16]
    detected_mime = validate_file_type(content_start, file.filename or "attachment")
    if detected_mime is None:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Accepted types: PDF, EPUB, PNG, JPEG, GIF, WebP"
        )

    # Size validation
    if not validate_file_size(len(content), 'document'):
        raise HTTPException(
            status_code=400,
            detail="File too large for document category"
        )

    logger.info(
        "Upload audit: user_id=%s filename=%s size=%s mime=%s goal_id=%s timestamp=%s",
        current_user.id,
        file.filename,
        len(content),
        detected_mime,
        goal_id,
        datetime.now(timezone.utc).isoformat(),
    )

    attachment = await svc.upload_attachment(
        goal_id, file.filename, file.content_type, content, current_user.id, db
    )
    return AttachmentResponse.model_validate(attachment)


@router.get("/goals/{goal_id}/attachments", response_model=List[AttachmentResponse])
async def list_attachments(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List attachments for a goal."""
    attachments = await svc.list_attachments(goal_id, db)
    return [AttachmentResponse.model_validate(a) for a in attachments]


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an attachment (staff/admin)."""
    await require_staff(current_user)
    return await svc.get_attachment_by_id(attachment_id, db)


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an attachment (staff/admin)."""
    await require_staff(current_user)
    await svc.delete_attachment(attachment_id, db)
    return {"message": "Attachment deleted"}
