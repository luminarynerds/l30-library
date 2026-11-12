# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""GDPR Article 20 - Data Portability (Export) Endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.audit_log import AuditAction, AuditLog
from ....models.circulation import Checkout, Hold
from ....models.event_registration import EventRegistration
from ....models.favorite import Favorite
from ....models.fine import Fine
from ....models.reading import ReadingLog
from ....models.reading_list import ReadingList
from ....models.ai_agents import AgentConversation
from ....models.ebook_checkout_log import EbookCheckoutLog
from ....models.user import User
from ....models.privacy_ledger import ConsentRecord, DataCorrectionLog, DataSharingLog
from ..auth import get_current_user

from .schemas import DataExportResponse, EnhancedDataExportResponse
from .helpers import create_audit_log

router = APIRouter()


@router.get("/export", response_model=DataExportResponse)
async def export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all personal data (GDPR Article 20 - Right to Data Portability).

    Returns a comprehensive JSON export of all user data including:
    - Profile information
    - Checkout history
    - Hold history
    - Fine history
    - Reading logs
    - Favorites
    - Reading lists
    - Event registrations
    """
    # Profile data
    profile = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "address": current_user.address,
        "library_card": current_user.library_card,
        "role": str(current_user.role),
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        "email_verified": current_user.email_verified,
        "track_reading_history": current_user.track_reading_history,
        "aggregate_recommendations_opt_out": current_user.aggregate_recommendations_opt_out,
        "language_preference": current_user.language_preference,
        "accessibility_needs": current_user.accessibility_needs,
        "preferred_contact_method": current_user.preferred_contact_method,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }

    # Checkout history
    checkouts_result = await db.execute(
        select(Checkout).where(Checkout.user_id == current_user.id)
    )
    checkouts = [
        {
            "id": c.id,
            "item_id": c.item_id,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "checked_out_at": c.checked_out_at.isoformat() if c.checked_out_at else None,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "returned_at": c.returned_at.isoformat() if c.returned_at else None,
            "renewal_count": c.renewal_count,
        }
        for c in checkouts_result.scalars().all()
    ]

    # Holds
    holds_result = await db.execute(
        select(Hold).where(Hold.user_id == current_user.id)
    )
    holds = [
        {
            "id": h.id,
            "item_id": h.item_id,
            "status": h.status.value if hasattr(h.status, 'value') else str(h.status),
            "position": h.position,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in holds_result.scalars().all()
    ]

    # Fines
    fines_result = await db.execute(
        select(Fine).where(Fine.user_id == current_user.id)
    )
    fines = [
        {
            "id": f.id,
            "amount": str(f.amount),
            "amount_paid": str(f.amount_paid),
            "fine_type": f.fine_type.value if hasattr(f.fine_type, 'value') else str(f.fine_type),
            "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
            "description": f.description,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in fines_result.scalars().all()
    ]

    # Reading history (only if enabled)
    reading_history = []
    if current_user.track_reading_history:
        reading_result = await db.execute(
            select(ReadingLog).where(ReadingLog.user_id == current_user.id)
        )
        reading_history = [
            {
                "id": r.id,
                "minutes": r.minutes,
                "book_title": r.book_title,
                "book_author": r.book_author,
                "reading_date": r.reading_date.isoformat() if r.reading_date else None,
                "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            }
            for r in reading_result.scalars().all()
        ]

    # Favorites
    favorites_result = await db.execute(
        select(Favorite).where(Favorite.user_id == current_user.id)
    )
    favorites = [
        {
            "id": f.id,
            "catalog_item_id": f.catalog_item_id,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in favorites_result.scalars().all()
    ]

    # Reading lists
    lists_result = await db.execute(
        select(ReadingList).where(ReadingList.user_id == current_user.id)
    )
    reading_lists = [
        {
            "id": rl.id,
            "name": rl.name,
            "description": rl.description,
            "is_public": rl.is_public,
            "created_at": rl.created_at.isoformat() if rl.created_at else None,
        }
        for rl in lists_result.scalars().all()
    ]

    # Event registrations
    events_result = await db.execute(
        select(EventRegistration).where(EventRegistration.patron_email == current_user.email)
    )
    event_registrations = [
        {
            "id": e.id,
            "event_id": e.event_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "registered_at": e.registered_at.isoformat() if e.registered_at else None,
        }
        for e in events_result.scalars().all()
    ]

    # AI conversation logs
    ai_conversations_result = await db.execute(
        select(AgentConversation).where(AgentConversation.user_id == current_user.id)
    )
    ai_conversations = [
        {
            "id": c.id,
            "agent_id": c.agent_id,
            "session_id": c.session_id,
            "user_message": c.user_message,
            "agent_response": c.agent_response,
            "detected_intent": c.detected_intent,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in ai_conversations_result.scalars().all()
    ]

    # Ebook checkout logs
    ebook_checkouts_result = await db.execute(
        select(EbookCheckoutLog).where(EbookCheckoutLog.user_id == current_user.id)
    )
    ebook_checkouts = [
        {
            "id": e.id,
            "source": e.source,
            "ebook_title": e.ebook_title,
            "ebook_author": e.ebook_author,
            "action": e.action,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
        }
        for e in ebook_checkouts_result.scalars().all()
    ]

    # Privacy change history (audit logs related to privacy changes)
    privacy_change_actions = [
        AuditAction.PRIVACY_CHANGE_READING_LIST,
        AuditAction.PRIVACY_CHANGE_FAVORITES,
        AuditAction.PRIVACY_CHANGE_GENERIC,
    ]
    privacy_audit_result = await db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == current_user.id,
            AuditLog.action.in_(privacy_change_actions),
        ).order_by(AuditLog.created_at.desc())
    )
    privacy_change_history = []
    for audit in privacy_audit_result.scalars().all():
        details = audit.details or {}
        privacy_change_history.append({
            "id": audit.id,
            "resource_type": details.get("resource_type", "unknown"),
            "resource_id": details.get("resource_id"),
            "old_privacy": details.get("old_privacy", "unknown"),
            "new_privacy": details.get("new_privacy", "unknown"),
            "changed_at": details.get("changed_at", audit.created_at.isoformat() if audit.created_at else None),
        })

    # Create audit log for data export
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DATA_EXPORTED,
        target_user_id=current_user.id,
        details={"export_type": "full", "record_counts": {
            "checkouts": len(checkouts),
            "holds": len(holds),
            "fines": len(fines),
            "reading_history": len(reading_history),
            "favorites": len(favorites),
            "reading_lists": len(reading_lists),
            "event_registrations": len(event_registrations),
            "ai_conversations": len(ai_conversations),
            "ebook_checkouts": len(ebook_checkouts),
            "privacy_change_history": len(privacy_change_history),
        }},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    await db.commit()

    return DataExportResponse(
        profile=profile,
        checkouts=checkouts,
        holds=holds,
        fines=fines,
        reading_history=reading_history,
        favorites=favorites,
        reading_lists=reading_lists,
        event_registrations=event_registrations,
        ai_conversations=ai_conversations,
        ebook_checkouts=ebook_checkouts,
        privacy_change_history=privacy_change_history,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/export/complete", response_model=EnhancedDataExportResponse)
async def export_complete_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enhanced data export including consent records, data sharing log,
    corrections, and full audit trail.

    This is the comprehensive "show me all data you have on me" endpoint
    that satisfies data subject access requests.
    """
    # Profile data (same as basic export)
    profile = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "address": current_user.address,
        "address_line1": current_user.address_line1,
        "address_line2": current_user.address_line2,
        "city": current_user.city,
        "state": current_user.state,
        "zip_code": current_user.zip_code,
        "library_card": current_user.library_card,
        "role": str(current_user.role),
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        "email_verified": current_user.email_verified,
        "track_reading_history": current_user.track_reading_history,
        "aggregate_recommendations_opt_out": current_user.aggregate_recommendations_opt_out,
        "discreet_receipts": current_user.discreet_receipts,
        "allow_staff_access_to_history": current_user.allow_staff_access_to_history,
        "notification_frequency": current_user.notification_frequency,
        "language_preference": current_user.language_preference,
        "accessibility_needs": current_user.accessibility_needs,
        "preferred_contact_method": current_user.preferred_contact_method,
        "patron_type": current_user.patron_type,
        "notice_preference": str(current_user.notice_preference) if current_user.notice_preference else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "deletion_requested_at": current_user.deletion_requested_at.isoformat() if current_user.deletion_requested_at else None,
        "deletion_scheduled_for": current_user.deletion_scheduled_for.isoformat() if current_user.deletion_scheduled_for else None,
    }

    # Checkout history
    checkouts_result = await db.execute(
        select(Checkout).where(Checkout.user_id == current_user.id)
    )
    checkouts = [
        {
            "id": c.id,
            "item_id": c.item_id,
            "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
            "checked_out_at": c.checked_out_at.isoformat() if c.checked_out_at else None,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "returned_at": c.returned_at.isoformat() if c.returned_at else None,
            "renewal_count": c.renewal_count,
        }
        for c in checkouts_result.scalars().all()
    ]

    # Holds
    holds_result = await db.execute(
        select(Hold).where(Hold.user_id == current_user.id)
    )
    holds = [
        {
            "id": h.id,
            "item_id": h.item_id,
            "status": h.status.value if hasattr(h.status, 'value') else str(h.status),
            "position": h.position,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in holds_result.scalars().all()
    ]

    # Fines
    fines_result = await db.execute(
        select(Fine).where(Fine.user_id == current_user.id)
    )
    fines = [
        {
            "id": f.id,
            "amount": str(f.amount),
            "amount_paid": str(f.amount_paid),
            "fine_type": f.fine_type.value if hasattr(f.fine_type, 'value') else str(f.fine_type),
            "status": f.status.value if hasattr(f.status, 'value') else str(f.status),
            "description": f.description,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in fines_result.scalars().all()
    ]

    # Reading history
    reading_history = []
    if current_user.track_reading_history:
        reading_result = await db.execute(
            select(ReadingLog).where(ReadingLog.user_id == current_user.id)
        )
        reading_history = [
            {
                "id": r.id,
                "minutes": r.minutes,
                "book_title": r.book_title,
                "book_author": r.book_author,
                "reading_date": r.reading_date.isoformat() if r.reading_date else None,
                "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            }
            for r in reading_result.scalars().all()
        ]

    # Favorites
    favorites_result = await db.execute(
        select(Favorite).where(Favorite.user_id == current_user.id)
    )
    favorites = [
        {
            "id": f.id,
            "catalog_item_id": f.catalog_item_id,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in favorites_result.scalars().all()
    ]

    # Reading lists
    lists_result = await db.execute(
        select(ReadingList).where(ReadingList.user_id == current_user.id)
    )
    reading_lists = [
        {
            "id": rl.id,
            "name": rl.name,
            "description": rl.description,
            "is_public": rl.is_public,
            "created_at": rl.created_at.isoformat() if rl.created_at else None,
        }
        for rl in lists_result.scalars().all()
    ]

    # Event registrations
    events_result = await db.execute(
        select(EventRegistration).where(EventRegistration.patron_email == current_user.email)
    )
    event_registrations = [
        {
            "id": e.id,
            "event_id": e.event_id,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "registered_at": e.registered_at.isoformat() if e.registered_at else None,
        }
        for e in events_result.scalars().all()
    ]

    # AI conversation logs
    ai_conversations_result = await db.execute(
        select(AgentConversation).where(AgentConversation.user_id == current_user.id)
    )
    ai_conversations = [
        {
            "id": c.id,
            "agent_id": c.agent_id,
            "session_id": c.session_id,
            "user_message": c.user_message,
            "agent_response": c.agent_response,
            "conversation_context": c.conversation_context,
            "detected_intent": c.detected_intent,
            "helpful": c.helpful,
            "feedback_note": c.feedback_note,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in ai_conversations_result.scalars().all()
    ]

    # Ebook checkout logs
    ebook_checkouts_result = await db.execute(
        select(EbookCheckoutLog).where(EbookCheckoutLog.user_id == current_user.id)
    )
    ebook_checkouts = [
        {
            "id": e.id,
            "source": e.source,
            "source_ref_id": e.source_ref_id,
            "ebook_title": e.ebook_title,
            "ebook_author": e.ebook_author,
            "action": e.action,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
            "metadata": e.metadata_,
        }
        for e in ebook_checkouts_result.scalars().all()
    ]

    # Privacy change history
    privacy_change_actions = [
        AuditAction.PRIVACY_CHANGE_READING_LIST,
        AuditAction.PRIVACY_CHANGE_FAVORITES,
        AuditAction.PRIVACY_CHANGE_GENERIC,
        AuditAction.PRIVACY_SETTING_CHANGED,
    ]
    privacy_audit_result = await db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == current_user.id,
            AuditLog.action.in_(privacy_change_actions),
        ).order_by(AuditLog.created_at.desc())
    )
    privacy_change_history = []
    for audit in privacy_audit_result.scalars().all():
        details = audit.details or {}
        privacy_change_history.append({
            "id": audit.id,
            "action": audit.action.value if hasattr(audit.action, 'value') else str(audit.action),
            "details": details,
            "changed_at": audit.created_at.isoformat() if audit.created_at else None,
        })

    # Consent records
    consent_result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == current_user.id)
        .order_by(ConsentRecord.created_at.desc())
    )
    consent_records = [
        {
            "id": r.id,
            "consent_type": r.consent_type.value if hasattr(r.consent_type, 'value') else str(r.consent_type),
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "method": r.method.value if hasattr(r.method, 'value') else str(r.method),
            "policy_version": r.policy_version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in consent_result.scalars().all()
    ]

    # Data sharing log
    sharing_result = await db.execute(
        select(DataSharingLog)
        .where(DataSharingLog.user_id == current_user.id)
        .order_by(DataSharingLog.created_at.desc())
    )
    data_sharing_log = [
        {
            "id": r.id,
            "recipient_name": r.recipient_name,
            "purpose": r.purpose.value if hasattr(r.purpose, 'value') else str(r.purpose),
            "data_categories": r.data_categories,
            "legal_basis": r.legal_basis,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in sharing_result.scalars().all()
    ]

    # Data corrections
    corrections_result = await db.execute(
        select(DataCorrectionLog)
        .where(DataCorrectionLog.user_id == current_user.id)
        .order_by(DataCorrectionLog.created_at.desc())
    )
    data_corrections = [
        {
            "id": r.id,
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "reason": r.reason,
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in corrections_result.scalars().all()
    ]

    # Full audit trail (all actions affecting this user)
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.target_user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
    )
    audit_trail = [
        {
            "id": a.id,
            "action": a.action.value if hasattr(a.action, 'value') else str(a.action),
            "details": a.details,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in audit_result.scalars().all()
    ]

    # Log that this comprehensive export was performed
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DATA_EXPORTED,
        target_user_id=current_user.id,
        details={
            "export_type": "complete",
            "record_counts": {
                "checkouts": len(checkouts),
                "holds": len(holds),
                "fines": len(fines),
                "reading_history": len(reading_history),
                "favorites": len(favorites),
                "reading_lists": len(reading_lists),
                "event_registrations": len(event_registrations),
                "consent_records": len(consent_records),
                "data_sharing_log": len(data_sharing_log),
                "data_corrections": len(data_corrections),
                "ai_conversations": len(ai_conversations),
                "ebook_checkouts": len(ebook_checkouts),
                "audit_trail": len(audit_trail),
            },
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    await db.commit()

    return EnhancedDataExportResponse(
        profile=profile,
        checkouts=checkouts,
        holds=holds,
        fines=fines,
        reading_history=reading_history,
        favorites=favorites,
        reading_lists=reading_lists,
        event_registrations=event_registrations,
        ai_conversations=ai_conversations,
        ebook_checkouts=ebook_checkouts,
        privacy_change_history=privacy_change_history,
        consent_records=consent_records,
        data_sharing_log=data_sharing_log,
        data_corrections=data_corrections,
        audit_trail=audit_trail,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )
