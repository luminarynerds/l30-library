# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Communication API Endpoints

Staff-only endpoints for managing:
- Patron notes (internal staff notes)
- Patron messages (email/SMS communication history)
"""
from app.core.logging import get_logger
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.email import send_email
from ...core.shortcuts import get_or_404
from ...models.patron_communication import (
    MessageChannel,
    MessageType,
    NoteCategory,
    NotePriority,
    PatronMessage,
    PatronNote,
    NoteAudit,
    NoteTemplate,
    PatronPreference,
)
from ...models.user import User, UserRole
from .dependencies import require_staff, is_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/patrons", tags=["patron-communication"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PatronNoteCreate(BaseModel):

    content: str = Field(..., min_length=1, max_length=10000)
    category: NoteCategory = NoteCategory.GENERAL
    priority: NotePriority = NotePriority.NORMAL
    is_branch_shared: bool = False
    visible_to_branch_ids: Optional[str] = None
    template_id: Optional[int] = None  # If using a template


class PatronNoteUpdate(BaseModel):

    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    category: Optional[NoteCategory] = None
    priority: Optional[NotePriority] = None
    is_branch_shared: Optional[bool] = None
    visible_to_branch_ids: Optional[str] = None
    change_reason: Optional[str] = None  # Reason for the change (for audit)


class PatronNoteResponse(BaseModel):

    id: int
    patron_id: int
    author_id: Optional[int]
    author_name: Optional[str]
    category: str
    content: str
    priority: str
    is_branch_shared: bool
    visible_to_branch_ids: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NoteAuditResponse(BaseModel):

    id: int
    note_id: int
    action: str
    changed_by_id: Optional[int]
    changed_by_name: Optional[str]
    previous_content: Optional[str]
    new_content: Optional[str]
    previous_priority: Optional[str]
    new_priority: Optional[str]
    previous_category: Optional[str]
    new_category: Optional[str]
    change_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NoteTemplateResponse(BaseModel):

    id: int
    title: str
    description: Optional[str]
    content_template: str
    category: str
    priority: str
    usage_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NoteTemplateCreate(BaseModel):

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    content_template: str = Field(..., min_length=1, max_length=5000)
    category: NoteCategory = NoteCategory.GENERAL
    priority: NotePriority = NotePriority.NORMAL


class PatronPreferenceResponse(BaseModel):

    id: int
    patron_id: int
    prefers_large_print: bool
    prefers_audio_format: bool
    prefers_braille: bool
    handle_fragile_items_with_care: bool
    limited_mobility_assistance_needed: bool
    needs_extra_time_checkout: bool
    preference_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PatronPreferenceUpdate(BaseModel):

    prefers_large_print: Optional[bool] = None
    prefers_audio_format: Optional[bool] = None
    prefers_braille: Optional[bool] = None
    handle_fragile_items_with_care: Optional[bool] = None
    limited_mobility_assistance_needed: Optional[bool] = None
    needs_extra_time_checkout: Optional[bool] = None
    preference_notes: Optional[str] = None


class PatronNoteListResponse(BaseModel):

    notes: List[PatronNoteResponse]
    total: int


class PatronMessageCreate(BaseModel):

    message_type: MessageType = MessageType.CUSTOM
    channel: MessageChannel = MessageChannel.EMAIL
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=50000)


class PatronMessageResponse(BaseModel):

    id: int
    patron_id: int
    sender_id: Optional[int]
    sender_name: Optional[str]
    message_type: str
    channel: str
    subject: str
    body: str
    recipient_email: Optional[str]
    recipient_phone: Optional[str]
    sent_at: datetime
    delivered: bool
    delivery_error: Optional[str]

    class Config:
        from_attributes = True


class PatronMessageListResponse(BaseModel):

    messages: List[PatronMessageResponse]
    total: int


class MessageTemplateResponse(BaseModel):

    id: str
    name: str
    subject: str
    body: str# =============================================================================
# Message Templates
# =============================================================================

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")

MESSAGE_TEMPLATES = {
    MessageType.OVERDUE_NOTICE: {
        "name": "Overdue Notice",
        "subject": "Library Items Overdue - Action Required",
        "body": """Dear {patron_name},

This is a reminder that you have library items that are currently overdue.

Please return these items as soon as possible to avoid additional late fees.

If you have any questions or need to renew your items, please contact us at the library or visit your account online.

Thank you,
""" + _LIBRARY_NAME,
    },
    MessageType.HOLD_READY: {
        "name": "Hold Ready for Pickup",
        "subject": "Your Library Hold is Ready for Pickup",
        "body": """Dear {patron_name},

Great news! An item you placed on hold is now ready for pickup at the library.

Please pick up your item within 7 days to avoid it being returned to the shelf.

If you are unable to pick up your hold, please contact us or cancel the hold through your account.

Thank you,
""" + _LIBRARY_NAME,
    },
    MessageType.FINE_REMINDER: {
        "name": "Fine Reminder",
        "subject": "Outstanding Library Fines - Reminder",
        "body": """Dear {patron_name},

This is a reminder that you have an outstanding fine balance of {fine_amount} on your library account.

To continue enjoying full library privileges, please pay your fines at your earliest convenience.

You can pay in person at the library or contact us to discuss payment options.

Thank you,
""" + _LIBRARY_NAME,
    },
    MessageType.ACCOUNT_BLOCKED: {
        "name": "Account Blocked Notice",
        "subject": "Your Library Account Has Been Blocked",
        "body": """Dear {patron_name},

Your library account has been temporarily blocked.

This may be due to overdue materials, outstanding fines, or other account issues.

Please contact the library to resolve this matter and restore your borrowing privileges.

Thank you,
""" + _LIBRARY_NAME,
    },
    MessageType.WELCOME_NEW_PATRON: {
        "name": "Welcome New Patron",
        "subject": f"Welcome to {_LIBRARY_NAME}!",
        "body": f"""Dear {{patron_name}},

Welcome to {_LIBRARY_NAME}! We're excited to have you as a new patron.

With your library card, you can:
- Borrow books, audiobooks, and other materials
- Access our digital resources and e-books
- Attend library programs and events
- Use our computers and WiFi

Visit us to explore all that your library has to offer!

Thank you,
""" + _LIBRARY_NAME,
    },
}


# =============================================================================
# Message Templates
# =============================================================================


class MessageTemplateResponse(BaseModel):
    id: str
    name: str
    subject: str
    body: str


@router.get("/messages/templates", response_model=List[MessageTemplateResponse])
async def get_message_templates(
    current_user: User = Depends(require_staff),
):
    """Return predefined message templates for staff to use when messaging patrons."""
    return [
        {
            "id": "overdue_notice",
            "name": "Overdue Notice",
            "subject": "Overdue Item Reminder",
            "body": "This is a friendly reminder that you have one or more items past their due date. Please return them at your earliest convenience to avoid additional fees.",
        },
        {
            "id": "hold_ready",
            "name": "Hold Ready for Pickup",
            "subject": "Your Hold is Ready",
            "body": "Great news! An item you placed on hold is now available for pickup. Please visit the circulation desk within 7 days to collect your item.",
        },
        {
            "id": "fine_reminder",
            "name": "Fine Reminder",
            "subject": "Outstanding Balance Reminder",
            "body": "Our records indicate you have an outstanding balance on your library account. Please visit the circulation desk or pay online to resolve your balance.",
        },
        {
            "id": "account_blocked",
            "name": "Account Blocked Notice",
            "subject": "Library Account Status Update",
            "body": "Your library account has been temporarily restricted. Please contact the circulation desk to resolve this issue and restore full access to library services.",
        },
        {
            "id": "welcome_new_patron",
            "name": "Welcome New Patron",
            "subject": "Welcome to the Library!",
            "body": "Welcome to our library! We are excited to have you as a member. Your library card gives you access to our full collection, events, and digital resources. Visit us anytime!",
        },
    ]





# =============================================================================
# Note Endpoints
# =============================================================================


@router.get("/{patron_id}/notes", response_model=PatronNoteListResponse)
async def get_patron_notes(
    patron_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[NoteCategory] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all notes for a patron.

    Staff only - notes are internal and not visible to patrons.
    """
    # Verify patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # Build query
    query = select(PatronNote).where(
        and_(PatronNote.patron_id == patron_id, PatronNote.is_deleted == False)
    )

    if category:
        query = query.where(PatronNote.category == category)

    # Get total count
    count_result = await db.execute(
        select(PatronNote.id).where(
            and_(PatronNote.patron_id == patron_id, PatronNote.is_deleted == False)
        )
    )
    total = len(count_result.all())

    # Get notes with pagination
    query = query.order_by(PatronNote.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    notes = result.scalars().all()

    # Fetch author names
    author_ids = [n.author_id for n in notes if n.author_id]
    authors = {}
    if author_ids:
        author_result = await db.execute(
            select(User).where(User.id.in_(author_ids))
        )
        for author in author_result.scalars().all():
            authors[author.id] = f"{author.first_name} {author.last_name}"

    return PatronNoteListResponse(
        notes=[
            PatronNoteResponse(
                id=note.id,
                patron_id=note.patron_id,
                author_id=note.author_id,
                author_name=authors.get(note.author_id) if note.author_id else None,
                category=note.category.value,
                content=note.content,
                priority=note.priority.value,
                is_branch_shared=note.is_branch_shared,
                visible_to_branch_ids=note.visible_to_branch_ids,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
            for note in notes
        ],
        total=total,
    )


@router.post("/{patron_id}/notes", response_model=PatronNoteResponse, status_code=201)
async def create_patron_note(
    patron_id: int,
    note_in: PatronNoteCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new note for a patron.

    Staff only - notes are internal and not visible to patrons.
    """
    # Verify patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # If using a template, prepend template content
    content = note_in.content
    if note_in.template_id:
        template_result = await db.execute(
            select(NoteTemplate).where(
                and_(NoteTemplate.id == note_in.template_id, NoteTemplate.is_active == True)
            )
        )
        template = template_result.scalar_one_or_none()
        if template:
            # Update template usage stats
            template.usage_count = (template.usage_count or 0) + 1
            template.last_used_at = datetime.now(timezone.utc)
            db.add(template)

    # Create note
    note = PatronNote(
        patron_id=patron_id,
        author_id=staff_user.id,
        category=note_in.category,
        content=content,
        priority=note_in.priority,
        is_branch_shared=note_in.is_branch_shared,
        visible_to_branch_ids=note_in.visible_to_branch_ids,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # Create audit entry
    audit = NoteAudit(
        note_id=note.id,
        action="created",
        changed_by_id=staff_user.id,
        new_content=note.content,
        new_category=note.category.value,
        new_priority=note.priority.value,
    )
    db.add(audit)
    await db.commit()

    return PatronNoteResponse(
        id=note.id,
        patron_id=note.patron_id,
        author_id=note.author_id,
        author_name=f"{staff_user.first_name} {staff_user.last_name}",
        category=note.category.value,
        content=note.content,
        priority=note.priority.value,
        is_branch_shared=note.is_branch_shared,
        visible_to_branch_ids=note.visible_to_branch_ids,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put("/{patron_id}/notes/{note_id}", response_model=PatronNoteResponse)
async def update_patron_note(
    patron_id: int,
    note_id: int,
    note_in: PatronNoteUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing patron note.

    Staff only - only the author or admin can edit notes.
    """
    # Get note
    result = await db.execute(
        select(PatronNote).where(
            and_(
                PatronNote.id == note_id,
                PatronNote.patron_id == patron_id,
                PatronNote.is_deleted == False,
            )
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Check if user can edit (author or admin)
    if note.author_id != staff_user.id and not is_admin(staff_user):
        raise HTTPException(
            status_code=403, detail="Only the author or an admin can edit this note"
        )

    # Track changes for audit
    previous_content = note.content
    previous_category = note.category.value if note.category else None
    previous_priority = note.priority.value if note.priority else None

    # Update fields
    if note_in.content is not None:
        note.content = note_in.content
    if note_in.category is not None:
        note.category = note_in.category
    if note_in.priority is not None:
        note.priority = note_in.priority
    if note_in.is_branch_shared is not None:
        note.is_branch_shared = note_in.is_branch_shared
    if note_in.visible_to_branch_ids is not None:
        note.visible_to_branch_ids = note_in.visible_to_branch_ids

    await db.commit()
    await db.refresh(note)

    # Create audit entry
    audit = NoteAudit(
        note_id=note.id,
        action="updated",
        changed_by_id=staff_user.id,
        previous_content=previous_content,
        new_content=note.content,
        previous_category=previous_category,
        new_category=note.category.value,
        previous_priority=previous_priority,
        new_priority=note.priority.value,
        change_reason=note_in.change_reason,
    )
    db.add(audit)
    await db.commit()

    # Get author name
    author_name = None
    if note.author_id:
        author_result = await db.execute(
            select(User).where(User.id == note.author_id)
        )
        author = author_result.scalar_one_or_none()
        if author:
            author_name = f"{author.first_name} {author.last_name}"

    return PatronNoteResponse(
        id=note.id,
        patron_id=note.patron_id,
        author_id=note.author_id,
        author_name=author_name,
        category=note.category.value,
        content=note.content,
        priority=note.priority.value,
        is_branch_shared=note.is_branch_shared,
        visible_to_branch_ids=note.visible_to_branch_ids,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/{patron_id}/notes/{note_id}", status_code=204)
async def delete_patron_note(
    patron_id: int,
    note_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a patron note (soft delete).

    Staff only - only the author or admin can delete notes.
    """
    # Get note
    result = await db.execute(
        select(PatronNote).where(
            and_(
                PatronNote.id == note_id,
                PatronNote.patron_id == patron_id,
                PatronNote.is_deleted == False,
            )
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Check if user can delete (author or admin)
    if note.author_id != staff_user.id and not is_admin(staff_user):
        raise HTTPException(
            status_code=403, detail="Only the author or an admin can delete this note"
        )

    # Soft delete
    note.soft_delete(user_id=staff_user.id)

    await db.commit()

    # Create audit entry
    audit = NoteAudit(
        note_id=note.id,
        action="deleted",
        changed_by_id=staff_user.id,
    )
    db.add(audit)
    await db.commit()

    return None


@router.get("/{patron_id}/notes/{note_id}/audit")
async def get_note_audit_trail(
    patron_id: int,
    note_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get audit trail for a specific note.

    Shows all changes made to the note (created, updated, deleted).
    """
    # Verify note exists
    note_result = await db.execute(
        select(PatronNote).where(
            and_(
                PatronNote.id == note_id,
                PatronNote.patron_id == patron_id,
            )
        )
    )
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get audit entries
    query = select(NoteAudit).where(NoteAudit.note_id == note_id)
    count_result = await db.execute(select(NoteAudit.id).where(NoteAudit.note_id == note_id))
    total = len(count_result.all())

    query = query.order_by(NoteAudit.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    audits = result.scalars().all()

    # Fetch changed_by names
    changed_by_ids = [a.changed_by_id for a in audits if a.changed_by_id]
    changed_by_map = {}
    if changed_by_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(changed_by_ids))
        )
        for user in user_result.scalars().all():
            changed_by_map[user.id] = f"{user.first_name} {user.last_name}"

    return {
        "audits": [
            NoteAuditResponse(
                id=audit.id,
                note_id=audit.note_id,
                action=audit.action,
                changed_by_id=audit.changed_by_id,
                changed_by_name=changed_by_map.get(audit.changed_by_id),
                previous_content=audit.previous_content,
                new_content=audit.new_content,
                previous_priority=audit.previous_priority,
                new_priority=audit.new_priority,
                previous_category=audit.previous_category,
                new_category=audit.new_category,
                change_reason=audit.change_reason,
                created_at=audit.created_at,
            )
            for audit in audits
        ],
        "total": total,
    }


# =============================================================================
# Note Template Endpoints
# =============================================================================


# =============================================================================
# Patron Preference Endpoints
# =============================================================================


@router.get("/{patron_id}/preferences", response_model=PatronPreferenceResponse)
async def get_patron_preferences(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get accessibility and handling preferences for a patron.

    Includes flags like large print preference, fragile item handling, etc.
    """
    # Verify patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get or create preferences
    result = await db.execute(
        select(PatronPreference).where(PatronPreference.patron_id == patron_id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create empty preferences for new patrons
        prefs = PatronPreference(patron_id=patron_id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return PatronPreferenceResponse(
        id=prefs.id,
        patron_id=prefs.patron_id,
        prefers_large_print=prefs.prefers_large_print,
        prefers_audio_format=prefs.prefers_audio_format,
        prefers_braille=prefs.prefers_braille,
        handle_fragile_items_with_care=prefs.handle_fragile_items_with_care,
        limited_mobility_assistance_needed=prefs.limited_mobility_assistance_needed,
        needs_extra_time_checkout=prefs.needs_extra_time_checkout,
        preference_notes=prefs.preference_notes,
        created_at=prefs.created_at,
        updated_at=prefs.updated_at,
    )


@router.put("/{patron_id}/preferences", response_model=PatronPreferenceResponse)
async def update_patron_preferences(
    patron_id: int,
    prefs_in: PatronPreferenceUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update patron accessibility and handling preferences.

    These preferences help staff provide better service by flagging:
    - Large print preference
    - Fragile items requiring careful handling
    - Limited mobility assistance needs
    - Extra time needed during checkout
    """
    # Verify patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get or create preferences
    result = await db.execute(
        select(PatronPreference).where(PatronPreference.patron_id == patron_id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = PatronPreference(patron_id=patron_id)
        db.add(prefs)

    # Update fields
    if prefs_in.prefers_large_print is not None:
        prefs.prefers_large_print = prefs_in.prefers_large_print
    if prefs_in.prefers_audio_format is not None:
        prefs.prefers_audio_format = prefs_in.prefers_audio_format
    if prefs_in.prefers_braille is not None:
        prefs.prefers_braille = prefs_in.prefers_braille
    if prefs_in.handle_fragile_items_with_care is not None:
        prefs.handle_fragile_items_with_care = prefs_in.handle_fragile_items_with_care
    if prefs_in.limited_mobility_assistance_needed is not None:
        prefs.limited_mobility_assistance_needed = prefs_in.limited_mobility_assistance_needed
    if prefs_in.needs_extra_time_checkout is not None:
        prefs.needs_extra_time_checkout = prefs_in.needs_extra_time_checkout
    if prefs_in.preference_notes is not None:
        prefs.preference_notes = prefs_in.preference_notes

    prefs.set_by_id = staff_user.id
    await db.commit()
    await db.refresh(prefs)

    return PatronPreferenceResponse(
        id=prefs.id,
        patron_id=prefs.patron_id,
        prefers_large_print=prefs.prefers_large_print,
        prefers_audio_format=prefs.prefers_audio_format,
        prefers_braille=prefs.prefers_braille,
        handle_fragile_items_with_care=prefs.handle_fragile_items_with_care,
        limited_mobility_assistance_needed=prefs.limited_mobility_assistance_needed,
        needs_extra_time_checkout=prefs.needs_extra_time_checkout,
        preference_notes=prefs.preference_notes,
        created_at=prefs.created_at,
        updated_at=prefs.updated_at,
    )


# =============================================================================
# Message Endpoints
# =============================================================================


@router.get("/{patron_id}/messages", response_model=PatronMessageListResponse)
async def get_patron_messages(
    patron_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    message_type: Optional[MessageType] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get message history for a patron.

    Staff only.
    """
    # Verify patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # Build query
    query = select(PatronMessage).where(PatronMessage.patron_id == patron_id)

    if message_type:
        query = query.where(PatronMessage.message_type == message_type)

    # Get total count
    count_query = select(PatronMessage.id).where(PatronMessage.patron_id == patron_id)
    if message_type:
        count_query = count_query.where(PatronMessage.message_type == message_type)
    count_result = await db.execute(count_query)
    total = len(count_result.all())

    # Get messages with pagination
    query = query.order_by(PatronMessage.sent_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()

    # Fetch sender names
    sender_ids = [m.sender_id for m in messages if m.sender_id]
    senders = {}
    if sender_ids:
        sender_result = await db.execute(
            select(User).where(User.id.in_(sender_ids))
        )
        for sender in sender_result.scalars().all():
            senders[sender.id] = f"{sender.first_name} {sender.last_name}"

    return PatronMessageListResponse(
        messages=[
            PatronMessageResponse(
                id=msg.id,
                patron_id=msg.patron_id,
                sender_id=msg.sender_id,
                sender_name=senders.get(msg.sender_id) if msg.sender_id else None,
                message_type=msg.message_type.value,
                channel=msg.channel.value,
                subject=msg.subject,
                body=msg.body,
                recipient_email=msg.recipient_email,
                recipient_phone=msg.recipient_phone,
                sent_at=msg.sent_at,
                delivered=msg.delivered,
                delivery_error=msg.delivery_error,
            )
            for msg in messages
        ],
        total=total,
    )


@router.post("/{patron_id}/messages", response_model=PatronMessageResponse, status_code=201)
async def send_patron_message(
    patron_id: int,
    message_in: PatronMessageCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to a patron and record it in history.

    This endpoint:
    1. Records the message in the database
    2. In a real implementation, would trigger actual email/SMS sending

    Staff only.
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Validate channel requirements
    if message_in.channel == MessageChannel.EMAIL and not patron.email:
        raise HTTPException(
            status_code=400, detail="Patron does not have an email address"
        )
    if message_in.channel == MessageChannel.SMS and not patron.phone:
        raise HTTPException(
            status_code=400, detail="Patron does not have a phone number"
        )

    # Replace template variables in subject and body
    patron_name = f"{patron.first_name} {patron.last_name}"
    subject = message_in.subject.replace("{patron_name}", patron_name)
    body = message_in.body.replace("{patron_name}", patron_name)

    # For fine amount, we would need to fetch actual fine balance
    # For now, use a placeholder if the variable exists
    if "{fine_amount}" in body:
        body = body.replace("{fine_amount}", "$0.00")

    # Create message record
    message = PatronMessage(
        patron_id=patron_id,
        sender_id=staff_user.id,
        message_type=message_in.message_type,
        channel=message_in.channel,
        subject=subject,
        body=body,
        recipient_email=patron.email if message_in.channel == MessageChannel.EMAIL else None,
        recipient_phone=patron.phone if message_in.channel == MessageChannel.SMS else None,
        delivered=False,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Actually send the message via the appropriate channel
    if message_in.channel == MessageChannel.EMAIL and patron.email:
        try:
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2C1810;">{subject}</h2>
                <div style="color: #5C4F3D; white-space: pre-wrap;">{body}</div>
                <hr style="border: none; border-top: 1px solid #E5E0D8; margin: 30px 0;">
                <p style="color: #8B7B6A; font-size: 12px;">
                    {_LIBRARY_NAME}<br>
                    This message was sent by a staff member. Please do not reply to this email.
                </p>
            </div>
            """
            success = await send_email(
                to_email=patron.email,
                subject=subject,
                html_content=html_body,
                patron_id=patron_id,
                notification_type="staff_message",
            )
            if success:
                message.delivered = True
            else:
                message.delivery_error = "Email delivery failed"
                logger.warning(f"Failed to send email to patron {patron_id}")
        except Exception as e:  # noqa: BLE001  # email send — record delivery_error and continue
            message.delivery_error = str(e)[:500]
            logger.error(f"Email send error for patron {patron_id}: {e}")
    elif message_in.channel == MessageChannel.SMS and patron.phone:
        # SMS delivery requires an SMS provider (none wired)
        # Record the message and mark as not yet delivered
        from ...core.config import get_settings as _get_settings
        _settings = _get_settings()
        if getattr(_settings, "sms_enabled", False):
            message.delivery_error = "SMS provider not yet configured"
            logger.warning(f"SMS send skipped for patron {patron_id}: no provider configured")
        else:
            message.delivery_error = "SMS notifications are not enabled"
            logger.info(f"SMS disabled - message to patron {patron_id} recorded but not sent")

    await db.commit()
    await db.refresh(message)

    return PatronMessageResponse(
        id=message.id,
        patron_id=message.patron_id,
        sender_id=message.sender_id,
        sender_name=f"{staff_user.first_name} {staff_user.last_name}",
        message_type=str(message.message_type),
        channel=str(message.channel),
        subject=message.subject,
        body=message.body,
        recipient_email=message.recipient_email,
        recipient_phone=message.recipient_phone,
        sent_at=message.sent_at,
        delivered=message.delivered,
        delivery_error=message.delivery_error,
    )


