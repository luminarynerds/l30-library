# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SMS Notification API Endpoints

Provides endpoints for:
- Phone verification (opt-in workflow)
- SMS notification preferences
- Staff ad-hoc SMS sending
- SMS statistics and cost tracking
"""
from app.core.logging import get_logger
from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...core.sms import (
    normalize_phone_number,
    validate_phone_number,
    SMSValidationError,
    SMS_VERIFICATION_EXPIRY_MINUTES,
)
from ...models.notification import NotificationPreferences
from ...models.sms import (
    DoNotDisturbHours,
    SMSCostRecord,
    SMSDeliveryStatus,
    SMSNotificationType,
    SMSOptOut,
    SMSQueue,
)
from ...models.user import User, UserRole
from ...services.sms_service import sms_service
from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/sms", tags=["sms"])
logger = get_logger(__name__)
settings = get_settings()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class PhoneVerificationRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not validate_phone_number(v):
            raise ValueError("Invalid phone number format")
        return v


class VerifyCodeRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    verification_code: str = Field(..., min_length=4, max_length=10)


class SMSPreferencesUpdate(BaseModel):
    sms_notifications_enabled: Optional[bool] = None
    sms_checkout_receipt: Optional[bool] = None
    sms_due_date_reminder: Optional[bool] = None
    sms_overdue_notice: Optional[bool] = None
    sms_hold_ready: Optional[bool] = None
    sms_hold_expiring: Optional[bool] = None
    sms_hold_cancelled: Optional[bool] = None
    sms_fine_notice: Optional[bool] = None
    sms_event_reminder: Optional[bool] = None
    sms_due_date_reminder_days: Optional[int] = Field(None, ge=1, le=7)
    sms_event_reminder_hours: Optional[int] = Field(None, ge=1, le=72)


class DNDHoursRequest(BaseModel):
    start_hour: int = Field(..., ge=0, le=23)
    start_minute: int = Field(0, ge=0, le=59)
    end_hour: int = Field(..., ge=0, le=23)
    end_minute: int = Field(0, ge=0, le=59)
    timezone: str = Field(default="America/New_York")
    active_days: list[int] = Field(default=[0, 1, 2, 3, 4, 5, 6])
    is_enabled: bool = True


class SendAdHocSMSRequest(BaseModel):
    patron_id: int
    message: str = Field(..., min_length=1, max_length=480)


class BulkSMSRequest(BaseModel):
    patron_ids: list[int] = Field(..., min_items=1, max_items=100)
    message: str = Field(..., min_length=1, max_length=480)


# ============================================================================
# Phone Verification Endpoints
# ============================================================================

@router.post("/verify/initiate")
async def initiate_phone_verification(
    request: PhoneVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate phone verification by sending a verification code via SMS.

    The user must verify their phone before SMS notifications can be enabled.
    """
    try:
        await sms_service.initiate_phone_verification(
            user_id=current_user.id,
            phone_number=request.phone_number,
            db=db,
        )

        return {
            "ok": True,
            "message": "Verification code sent",
            "phone_number": normalize_phone_number(request.phone_number)[-4:],
            "expires_in_minutes": SMS_VERIFICATION_EXPIRY_MINUTES,
        }

    except SMSValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Phone verification error")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None


@router.post("/verify/confirm")
async def confirm_phone_verification(
    request: VerifyCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm phone verification with the code received via SMS.

    On success, SMS notifications will be enabled for this phone number.
    """
    try:
        success = await sms_service.verify_phone(
            user_id=current_user.id,
            phone_number=request.phone_number,
            code=request.verification_code,
            db=db,
        )

        if success:
            return {
                "ok": True,
                "message": "Phone verified successfully",
                "sms_enabled": True,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification code"
            )

    except SMSValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/verify/resend")
async def resend_verification_code(
    request: PhoneVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resend a phone verification code."""
    return await initiate_phone_verification(request, current_user, db)


# ============================================================================
# SMS Preferences Endpoints
# ============================================================================

@router.get("/preferences")
async def get_sms_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's SMS notification preferences."""
    prefs = await sms_service.get_sms_preferences(current_user.id, db)

    if not prefs:
        # Create default preferences
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    # Get DND config
    dnd = await sms_service.get_dnd_config(current_user.id, db)

    return {
        "sms_notifications_enabled": prefs.sms_notifications_enabled,
        "phone_number": prefs.sms_phone_number[-4:] if prefs.sms_phone_number else None,
        "phone_verified": prefs.sms_phone_verified,
        "phone_verified_at": prefs.sms_phone_verified_at,
        "preferences": {
            "checkout_receipt": prefs.sms_checkout_receipt,
            "due_date_reminder": prefs.sms_due_date_reminder,
            "overdue_notice": prefs.sms_overdue_notice,
            "hold_ready": prefs.sms_hold_ready,
            "hold_expiring": prefs.sms_hold_expiring,
            "hold_cancelled": prefs.sms_hold_cancelled,
            "fine_notice": prefs.sms_fine_notice,
            "event_reminder": prefs.sms_event_reminder,
        },
        "timing": {
            "due_date_reminder_days": prefs.sms_due_date_reminder_days,
            "event_reminder_hours": prefs.sms_event_reminder_hours,
        },
        "do_not_disturb": {
            "enabled": dnd.is_enabled if dnd else False,
            "start_time": f"{dnd.start_time.hour:02d}:{dnd.start_time.minute:02d}" if dnd else None,
            "end_time": f"{dnd.end_time.hour:02d}:{dnd.end_time.minute:02d}" if dnd else None,
            "timezone": dnd.timezone if dnd else None,
            "active_days": dnd.active_days if dnd else None,
        } if dnd else None,
    }


@router.put("/preferences")
async def update_sms_preferences(
    preferences: SMSPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update SMS notification preferences."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)

    # Check if trying to enable SMS without verified phone
    if preferences.sms_notifications_enabled and not prefs.sms_phone_verified:
        raise HTTPException(
            status_code=400,
            detail="Phone must be verified before enabling SMS notifications"
        )

    # Update fields
    update_data = preferences.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)

    return {
        "ok": True,
        "message": "SMS preferences updated",
    }


@router.delete("/phone")
async def remove_verified_phone(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove verified phone and disable SMS notifications."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if prefs:
        prefs.sms_phone_number = None
        prefs.sms_phone_verified = False
        prefs.sms_phone_verified_at = None
        prefs.sms_notifications_enabled = False
        await db.commit()

    return {"ok": True, "message": "Phone number removed"}


# ============================================================================
# Do Not Disturb Endpoints
# ============================================================================

@router.put("/dnd")
async def update_dnd_hours(
    request: DNDHoursRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update Do Not Disturb hours for the current user."""
    result = await db.execute(
        select(DoNotDisturbHours).where(
            DoNotDisturbHours.user_id == current_user.id
        )
    )
    dnd = result.scalar_one_or_none()

    if not dnd:
        dnd = DoNotDisturbHours(user_id=current_user.id)
        db.add(dnd)

    dnd.start_time = time(request.start_hour, request.start_minute)
    dnd.end_time = time(request.end_hour, request.end_minute)
    dnd.timezone = request.timezone
    dnd.active_days = request.active_days
    dnd.is_enabled = request.is_enabled

    await db.commit()

    return {
        "ok": True,
        "message": "Do Not Disturb hours updated",
    }


@router.delete("/dnd")
async def disable_dnd_hours(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable Do Not Disturb hours for the current user."""
    result = await db.execute(
        select(DoNotDisturbHours).where(
            DoNotDisturbHours.user_id == current_user.id
        )
    )
    dnd = result.scalar_one_or_none()

    if dnd:
        dnd.is_enabled = False
        await db.commit()

    return {"ok": True, "message": "Do Not Disturb disabled"}


# ============================================================================
# Staff Endpoints
# ============================================================================

@router.post("/staff/send")
async def staff_send_sms(
    request: SendAdHocSMSRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Send an ad-hoc SMS to a patron (staff only).

    The patron must have SMS enabled and a verified phone number.
    """
    # Get patron's SMS preferences
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == request.patron_id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs or not prefs.sms_phone_verified or not prefs.sms_phone_number:
        raise HTTPException(
            status_code=400,
            detail="Patron does not have a verified phone number"
        )

    # Check opt-out status
    if await sms_service.is_phone_opted_out(prefs.sms_phone_number, db):
        raise HTTPException(
            status_code=400,
            detail="Patron has opted out of SMS notifications"
        )

    try:
        sms = await sms_service.queue_sms(
            user_id=request.patron_id,
            phone_number=prefs.sms_phone_number,
            notification_type=SMSNotificationType.AD_HOC,
            message=request.message,
            context_data={"staff_id": staff_user.id, "staff_name": staff_user.full_name},
            initiated_by_user_id=staff_user.id,
            db=db,
            check_dnd=True,
        )

        # Send immediately
        success, error = await sms_service.send_queued_sms(sms.id, db)

        return {
            "ok": success,
            "message": "SMS sent" if success else f"Failed: {error}",
            "sms_id": sms.id,
            "status": str(sms.status),
        }

    except Exception:
        logger.exception("Staff SMS send error")
        raise InternalServerError(code=ErrorCode.EXTERNAL_SERVICE_ERROR) from None


@router.post("/staff/bulk")
async def staff_bulk_sms(
    request: BulkSMSRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Send SMS to multiple patrons (staff only).

    Only sends to patrons with verified phone numbers who haven't opted out.
    """
    sent = 0
    failed = 0
    skipped = 0
    errors = []

    for patron_id in request.patron_ids:
        result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == patron_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs or not prefs.sms_phone_verified or not prefs.sms_phone_number:
            skipped += 1
            continue

        if await sms_service.is_phone_opted_out(prefs.sms_phone_number, db):
            skipped += 1
            continue

        try:
            sms = await sms_service.queue_sms(
                user_id=patron_id,
                phone_number=prefs.sms_phone_number,
                notification_type=SMSNotificationType.AD_HOC,
                message=request.message,
                context_data={"staff_id": staff_user.id, "bulk": True},
                initiated_by_user_id=staff_user.id,
                db=db,
                check_dnd=True,
            )

            success, error = await sms_service.send_queued_sms(sms.id, db)
            if success:
                sent += 1
            else:
                failed += 1
                errors.append({"patron_id": patron_id, "error": error})

        except Exception as e:  # noqa: BLE001  # per-patron SMS send — record failure and continue
            failed += 1
            errors.append({"patron_id": patron_id, "error": str(e)})

    return {
        "ok": True,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "errors": errors[:10] if errors else [],  # Limit error details
    }


@router.get("/staff/queue")
async def get_sms_queue(
    status: Optional[str] = Query(None),
    notification_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS queue status (staff only)."""
    query = select(SMSQueue)

    if status:
        try:
            status_enum = SMSDeliveryStatus(status)
            query = query.where(SMSQueue.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status") from None

    if notification_type:
        try:
            type_enum = SMSNotificationType(notification_type)
            query = query.where(SMSQueue.notification_type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid notification type") from None

    query = query.order_by(SMSQueue.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Get total count
    count_query = select(func.count(SMSQueue.id))
    if status:
        count_query = count_query.where(SMSQueue.status == SMSDeliveryStatus(status))
    if notification_type:
        count_query = count_query.where(SMSQueue.notification_type == SMSNotificationType(notification_type))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "items": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "recipient_phone": m.recipient_phone[-4:],
                "notification_type": str(m.notification_type),
                "status": str(m.status),
                "message_preview": m.message_body[:50] + "..." if len(m.message_body) > 50 else m.message_body,
                "segments": m.message_segments,
                "scheduled_for": m.scheduled_for.isoformat() if m.scheduled_for else None,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "retry_count": m.retry_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/staff/stats")
async def get_sms_stats(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS statistics (staff only)."""
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month

    # Aggregate stats
    query = select(SMSCostRecord).where(
        and_(
            SMSCostRecord.year == year,
            SMSCostRecord.month == month,
        )
    )

    result = await db.execute(query)
    records = result.scalars().all()

    total_sent = sum(r.messages_sent for r in records)
    total_delivered = sum(r.messages_delivered for r in records)
    total_failed = sum(r.messages_failed for r in records)
    total_segments = sum(r.total_segments for r in records)
    total_cost_cents = sum(r.total_cost_cents for r in records)

    # Group by notification type
    by_type = {}
    for r in records:
        type_name = str(r.notification_type)
        if type_name not in by_type:
            by_type[type_name] = {
                "sent": 0,
                "delivered": 0,
                "failed": 0,
                "segments": 0,
                "cost_cents": 0,
            }
        by_type[type_name]["sent"] += r.messages_sent
        by_type[type_name]["delivered"] += r.messages_delivered
        by_type[type_name]["failed"] += r.messages_failed
        by_type[type_name]["segments"] += r.total_segments
        by_type[type_name]["cost_cents"] += r.total_cost_cents

    # Get unique patrons with SMS enabled
    patrons_query = select(func.count(NotificationPreferences.id)).where(
        and_(
            NotificationPreferences.sms_notifications_enabled == True,
            NotificationPreferences.sms_phone_verified == True,
        )
    )
    patrons_result = await db.execute(patrons_query)
    sms_enabled_count = patrons_result.scalar()

    # Get opt-out count
    opt_out_query = select(func.count(SMSOptOut.id)).where(SMSOptOut.is_active == True)
    opt_out_result = await db.execute(opt_out_query)
    opt_out_count = opt_out_result.scalar()

    return {
        "period": {"year": year, "month": month},
        "summary": {
            "total_sent": total_sent,
            "total_delivered": total_delivered,
            "total_failed": total_failed,
            "total_segments": total_segments,
            "total_cost_cents": total_cost_cents,
            "total_cost_dollars": round(total_cost_cents / 100, 2),
            "delivery_rate": round(total_delivered / total_sent * 100, 1) if total_sent > 0 else 0,
        },
        "by_notification_type": by_type,
        "subscribers": {
            "sms_enabled": sms_enabled_count,
            "opted_out": opt_out_count,
        },
    }


@router.get("/staff/patron/{patron_id}/history")
async def get_patron_sms_history(
    patron_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get SMS history for a specific patron (staff only)."""
    result = await db.execute(
        select(SMSQueue)
        .where(SMSQueue.user_id == patron_id)
        .order_by(SMSQueue.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Get stats
    stats = await sms_service.get_user_sms_stats(patron_id, db)

    return {
        "patron_id": patron_id,
        "stats": stats,
        "messages": [
            {
                "id": m.id,
                "notification_type": str(m.notification_type),
                "status": str(m.status),
                "message_body": m.message_body,
                "segments": m.message_segments,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
                "failure_reason": m.failure_reason,
                "cost_cents": m.cost_cents,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


# ============================================================================
# Global DND Configuration (Admin)
# ============================================================================

@router.get("/admin/dnd/global")
async def get_global_dnd(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get global Do Not Disturb configuration."""
    result = await db.execute(
        select(DoNotDisturbHours).where(DoNotDisturbHours.user_id.is_(None))
    )
    dnd = result.scalar_one_or_none()

    if not dnd:
        return {
            "is_configured": False,
            "config": None,
        }

    return {
        "is_configured": True,
        "config": {
            "start_time": f"{dnd.start_time.hour:02d}:{dnd.start_time.minute:02d}",
            "end_time": f"{dnd.end_time.hour:02d}:{dnd.end_time.minute:02d}",
            "timezone": dnd.timezone,
            "active_days": dnd.active_days,
            "is_enabled": dnd.is_enabled,
        },
    }


@router.put("/admin/dnd/global")
async def set_global_dnd(
    request: DNDHoursRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Set global Do Not Disturb configuration (admin only)."""
    if staff_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(DoNotDisturbHours).where(DoNotDisturbHours.user_id.is_(None))
    )
    dnd = result.scalar_one_or_none()

    if not dnd:
        dnd = DoNotDisturbHours(user_id=None)
        db.add(dnd)

    dnd.start_time = time(request.start_hour, request.start_minute)
    dnd.end_time = time(request.end_hour, request.end_minute)
    dnd.timezone = request.timezone
    dnd.active_days = request.active_days
    dnd.is_enabled = request.is_enabled

    await db.commit()

    return {
        "ok": True,
        "message": "Global DND configuration updated",
    }


@router.get("/dnd")
async def get_dnd(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /dnd information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")

