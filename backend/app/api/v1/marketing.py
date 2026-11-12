# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Marketing Communication API Endpoints

Handles:
- Newsletter subscription (signup, confirmation, unsubscribe)
- Interest-based mailing lists
- New arrival alerts by category
- Email preference management
- Unsubscribe processing (CAN-SPAM compliance)
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.email import (
    send_newsletter_double_optin_email,
    send_newsletter_welcome_email,
    send_interest_confirmation_email,
)
from ...core.logging import get_logger
from ...models.marketing import (
    EmailUnsubscribeToken,
    InterestCategory,
    MarketingConsentSource,
    NewArrivalAlert,
    NewsletterFrequency,
    NewsletterSubscription,
    SubscriberInterest,
    SubscriptionStatus,
    UnsubscribeReason,
)
from ...models.user import User
from ...services.unsubscribe_service import unsubscribe_service
from .auth import get_current_user, get_optional_user
from .dependencies import is_admin

router = APIRouter(prefix="/marketing", tags=["marketing"])
settings = get_settings()
logger = get_logger(__name__)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class NewsletterSignupRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    frequency: NewsletterFrequency = NewsletterFrequency.WEEKLY
    interest_ids: Optional[list[int]] = None
    consent_source: MarketingConsentSource = MarketingConsentSource.NEWSLETTER_FORM


class NewsletterConfirmRequest(BaseModel):
    token: str


class InterestUpdateRequest(BaseModel):
    interest_ids: list[int]


class NewArrivalAlertRequest(BaseModel):
    category_id: Optional[int] = None
    search_query: Optional[str] = Field(None, max_length=500)
    author_name: Optional[str] = Field(None, max_length=255)
    series_name: Optional[str] = Field(None, max_length=255)
    delivery_method: str = Field(default="email", pattern="^(email|sms|both)$")
    frequency: NewsletterFrequency = NewsletterFrequency.WEEKLY


class UnsubscribeRequest(BaseModel):
    token: str
    reason: Optional[UnsubscribeReason] = None
    feedback: Optional[str] = Field(None, max_length=1000)


class PreferencesUpdateRequest(BaseModel):
    token: str
    newsletter_enabled: Optional[bool] = None
    frequency: Optional[NewsletterFrequency] = None
    interest_ids: Optional[list[int]] = None


class InterestCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    parent_id: Optional[int]

    class Config:
        from_attributes = True


class NewsletterSubscriptionResponse(BaseModel):
    email: str
    status: str
    frequency: str
    confirmed: bool
    interests: list[InterestCategoryResponse]


# =============================================================================
# Newsletter Subscription Endpoints
# =============================================================================


@router.post("/newsletter/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_to_newsletter(  # noqa: role-check -- public newsletter subscribe (double opt-in)
    request: Request,
    signup: NewsletterSignupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Subscribe to the newsletter.

    Implements double opt-in for GDPR compliance:
    1. Creates pending subscription
    2. Sends confirmation email
    3. Subscription becomes active when confirmed

    If user is logged in, links subscription to their account.
    """
    email = signup.email.lower()

    # Check if already subscribed
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.email == email
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status == SubscriptionStatus.ACTIVE:
            return {
                "message": "You're already subscribed to our newsletter",
                "status": "already_subscribed",
            }
        elif existing.status == SubscriptionStatus.UNSUBSCRIBED:
            # Allow re-subscription
            existing.status = SubscriptionStatus.ACTIVE
            existing.unsubscribed_at = None
            existing.unsubscribe_reason = None
            existing.double_optin_token = secrets.token_urlsafe(32)
            existing.double_optin_sent_at = datetime.now(timezone.utc)
            existing.double_optin_confirmed_at = None
            existing.consent_given = True
            existing.consent_date = datetime.now(timezone.utc)
            existing.consent_source = signup.consent_source

            await db.commit()

            # Send double opt-in email
            await send_newsletter_double_optin_email(
                to_email=email,
                first_name=existing.first_name or "",
                confirmation_token=existing.double_optin_token,
            )

            return {
                "message": "We've sent a confirmation email. Please check your inbox.",
                "status": "confirmation_sent",
            }

    # Get client IP for consent tracking
    client_ip = request.client.host if request.client else None

    # Create new subscription
    subscription = NewsletterSubscription(
        user_id=current_user.id if current_user else None,
        email=email,
        first_name=signup.first_name or (current_user.first_name if current_user else None),
        last_name=signup.last_name or (current_user.last_name if current_user else None),
        status=SubscriptionStatus.ACTIVE,
        frequency=signup.frequency,
        consent_given=True,
        consent_date=datetime.now(timezone.utc),
        consent_source=signup.consent_source,
        consent_ip_address=client_ip,
        double_optin_token=secrets.token_urlsafe(32),
        double_optin_sent_at=datetime.now(timezone.utc),
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    # Add interests if provided
    if signup.interest_ids:
        for interest_id in signup.interest_ids:
            interest = SubscriberInterest(
                subscription_id=subscription.id,
                category_id=interest_id,
            )
            db.add(interest)
        await db.commit()

    # Send double opt-in email
    await send_newsletter_double_optin_email(
        to_email=email,
        first_name=subscription.first_name or "",
        confirmation_token=subscription.double_optin_token,
    )

    logger.info(
        "Newsletter signup initiated",
        extra={"email": email[:3] + "***", "source": str(signup.consent_source)},
    )

    return {
        "message": "We've sent a confirmation email. Please check your inbox to complete your subscription.",
        "status": "confirmation_sent",
    }


@router.post("/newsletter/confirm")
async def confirm_newsletter_subscription(  # noqa: role-check -- public newsletter confirmation via email token
    confirm: NewsletterConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm newsletter subscription (double opt-in).

    Completes the subscription process and sends welcome email.
    """
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.double_optin_token == confirm.token
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired confirmation token",
        )

    if subscription.double_optin_confirmed_at:
        return {
            "message": "Your subscription is already confirmed",
            "status": "already_confirmed",
        }

    # Check token age (7 days max)
    if subscription.double_optin_sent_at:
        token_age = datetime.now(timezone.utc) - subscription.double_optin_sent_at
        if token_age > timedelta(days=7):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation token has expired. Please sign up again.",
            )

    # Confirm subscription
    subscription.double_optin_confirmed_at = datetime.now(timezone.utc)
    subscription.double_optin_token = None  # Clear token after use
    await db.commit()

    # Generate unsubscribe URLs
    unsubscribe_token = await unsubscribe_service.generate_unsubscribe_token(
        db=db,
        email=subscription.email,
        email_type="newsletter",
        user_id=subscription.user_id,
    )
    unsubscribe_url = unsubscribe_service.generate_unsubscribe_url(unsubscribe_token)
    preferences_url = unsubscribe_service.generate_preferences_url(unsubscribe_token)

    # Send welcome email
    await send_newsletter_welcome_email(
        to_email=subscription.email,
        first_name=subscription.first_name or "",
        unsubscribe_url=unsubscribe_url,
        preferences_url=preferences_url,
    )

    logger.info(
        "Newsletter subscription confirmed",
        extra={"email": subscription.email[:3] + "***"},
    )

    return {
        "message": "Welcome! Your subscription is now active.",
        "status": "confirmed",
    }


@router.get("/newsletter/status")
async def get_newsletter_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's newsletter subscription status."""
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        # Check by email
        result = await db.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == current_user.email.lower()
            )
        )
        subscription = result.scalar_one_or_none()

    if not subscription:
        return {
            "subscribed": False,
            "status": None,
        }

    # Get interests
    interests_result = await db.execute(
        select(InterestCategory)
        .join(SubscriberInterest)
        .where(SubscriberInterest.subscription_id == subscription.id)
    )
    interests = interests_result.scalars().all()

    return {
        "subscribed": subscription.is_active,
        "status": str(subscription.status),
        "frequency": str(subscription.frequency),
        "confirmed": subscription.is_confirmed,
        "interests": [
            InterestCategoryResponse.model_validate(i) for i in interests
        ],
    }


@router.delete("/newsletter/unsubscribe")
async def unsubscribe_from_newsletter(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unsubscribe current user from newsletter."""
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        result = await db.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == current_user.email.lower()
            )
        )
        subscription = result.scalar_one_or_none()

    if subscription:
        subscription.status = SubscriptionStatus.UNSUBSCRIBED
        subscription.unsubscribed_at = datetime.now(timezone.utc)
        await db.commit()

    return {"message": "You have been unsubscribed from the newsletter"}


# =============================================================================
# Interest Categories Endpoints
# =============================================================================


@router.get("/interests", response_model=list[InterestCategoryResponse])
async def list_interest_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all available interest categories."""
    result = await db.execute(
        select(InterestCategory)
        .where(InterestCategory.is_active == True)
        .order_by(InterestCategory.display_order, InterestCategory.name)
        .offset(skip)
        .limit(limit)
    )
    categories = result.scalars().all()

    return [InterestCategoryResponse.model_validate(c) for c in categories]


@router.get("/interests/mine")
async def get_my_interests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscribed interests."""
    # Find subscription
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return {"interests": []}

    # Get interests
    interests_result = await db.execute(
        select(InterestCategory)
        .join(SubscriberInterest)
        .where(SubscriberInterest.subscription_id == subscription.id)
    )
    interests = interests_result.scalars().all()

    return {
        "interests": [
            InterestCategoryResponse.model_validate(i) for i in interests
        ]
    }


@router.put("/interests/mine")
async def update_my_interests(
    request: InterestUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's interest subscriptions."""
    # Find or create subscription
    result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        # Create subscription linked to user
        subscription = NewsletterSubscription(
            user_id=current_user.id,
            email=current_user.email.lower(),
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            status=SubscriptionStatus.ACTIVE,
            consent_given=True,
            consent_date=datetime.now(timezone.utc),
            consent_source=MarketingConsentSource.ACCOUNT_SETTINGS,
            double_optin_confirmed_at=datetime.now(timezone.utc),  # Skip double opt-in for authenticated users
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

    # Remove existing interests
    await db.execute(
        delete(SubscriberInterest).where(
            SubscriberInterest.subscription_id == subscription.id
        )
    )

    # Add new interests
    interest_names = []
    for interest_id in request.interest_ids:
        # Verify interest exists
        cat_result = await db.execute(
            select(InterestCategory).where(
                InterestCategory.id == interest_id,
                InterestCategory.is_active == True,
            )
        )
        category = cat_result.scalar_one_or_none()
        if category:
            interest = SubscriberInterest(
                subscription_id=subscription.id,
                category_id=interest_id,
            )
            db.add(interest)
            interest_names.append(category.name)

    await db.commit()

    # Send confirmation email
    if interest_names:
        unsubscribe_token = await unsubscribe_service.generate_unsubscribe_token(
            db=db,
            email=subscription.email,
            email_type="newsletter",
            user_id=subscription.user_id,
        )
        unsubscribe_url = unsubscribe_service.generate_unsubscribe_url(unsubscribe_token)
        preferences_url = unsubscribe_service.generate_preferences_url(unsubscribe_token)

        await send_interest_confirmation_email(
            to_email=subscription.email,
            first_name=subscription.first_name or "",
            interests=interest_names,
            unsubscribe_url=unsubscribe_url,
            preferences_url=preferences_url,
        )

    return {
        "message": "Your interests have been updated",
        "interests": interest_names,
    }


# =============================================================================
# New Arrival Alerts Endpoints
# =============================================================================


@router.get("/alerts")
async def list_my_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's new arrival alerts."""
    result = await db.execute(
        select(NewArrivalAlert)
        .where(
            NewArrivalAlert.user_id == current_user.id,
            NewArrivalAlert.is_active == True,
        )
        .order_by(NewArrivalAlert.id.desc())
        .limit(200)
    )
    alerts = result.scalars().all()

    alerts_data = []
    for alert in alerts:
        category_name = None
        if alert.category_id:
            cat_result = await db.execute(
                select(InterestCategory).where(InterestCategory.id == alert.category_id)
            )
            category = cat_result.scalar_one_or_none()
            category_name = category.name if category else None

        alerts_data.append({
            "id": alert.id,
            "category_id": alert.category_id,
            "category_name": category_name,
            "search_query": alert.search_query,
            "author_name": alert.author_name,
            "series_name": alert.series_name,
            "delivery_method": alert.delivery_method,
            "frequency": str(alert.frequency),
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        })

    return {"alerts": alerts_data}


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
async def create_arrival_alert(
    alert_request: NewArrivalAlertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new arrival alert."""
    # Must have at least one filter criteria
    if not any([
        alert_request.category_id,
        alert_request.search_query,
        alert_request.author_name,
        alert_request.series_name,
    ]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter criteria is required (category, search query, author, or series)",
        )

    # Verify category exists if provided
    if alert_request.category_id:
        cat_result = await db.execute(
            select(InterestCategory).where(
                InterestCategory.id == alert_request.category_id,
                InterestCategory.is_active == True,
            )
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

    alert = NewArrivalAlert(
        user_id=current_user.id,
        category_id=alert_request.category_id,
        search_query=alert_request.search_query,
        author_name=alert_request.author_name,
        series_name=alert_request.series_name,
        delivery_method=alert_request.delivery_method,
        frequency=alert_request.frequency,
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {
        "message": "Alert created successfully",
        "alert_id": alert.id,
    }


@router.get("/alerts/{alert_id}")
async def get_arrival_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a new arrival alert."""
    result = await db.execute(
        select(NewArrivalAlert).where(
            NewArrivalAlert.id == alert_id,
            NewArrivalAlert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return {
        "id": alert.id,
        "category_id": alert.category_id,
        "search_query": alert.search_query,
        "author_name": alert.author_name,
        "series_name": alert.series_name,
        "delivery_method": alert.delivery_method,
        "frequency": alert.frequency,
        "is_active": alert.is_active,
        "created_at": alert.created_at,
    }


@router.delete("/alerts/{alert_id}")
async def delete_arrival_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a new arrival alert."""
    result = await db.execute(
        select(NewArrivalAlert).where(
            NewArrivalAlert.id == alert_id,
            NewArrivalAlert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    alert.is_active = False
    await db.commit()

    return {"message": "Alert deleted successfully"}


# =============================================================================
# Unsubscribe Endpoints (Public - Token-based)
# =============================================================================


@router.post("/unsubscribe")
async def process_unsubscribe(  # noqa: role-check -- public CAN-SPAM unsubscribe via email token
    unsubscribe_req: UnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process an unsubscribe request.

    This is the one-click unsubscribe endpoint for CAN-SPAM compliance.
    It works without authentication using the token from the email.
    """
    result = await unsubscribe_service.process_unsubscribe(
        db=db,
        token=unsubscribe_req.token,
        reason=unsubscribe_req.reason,
        feedback=unsubscribe_req.feedback,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to process unsubscribe request"),
        )

    return result


@router.get("/unsubscribe")
async def one_click_unsubscribe(
    token: str = Query(..., description="Unsubscribe token from email"),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click unsubscribe (GET endpoint for email clients).

    Some email clients support one-click unsubscribe via GET request.
    This endpoint handles that case.
    """
    result = await unsubscribe_service.process_unsubscribe(
        db=db,
        token=token,
        reason=UnsubscribeReason.ONE_CLICK,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to process unsubscribe request"),
        )

    return {
        "message": "You have been successfully unsubscribed",
        **result,
    }


@router.get("/preferences")
async def get_preferences_by_token(
    token: str = Query(..., description="Token from email"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get email preferences using a token.

    This allows users to view and manage their preferences
    directly from email links without logging in.
    """
    preferences = await unsubscribe_service.get_subscription_status(db, token)

    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired token",
        )

    # Get available interest categories
    cats_result = await db.execute(
        select(InterestCategory)
        .where(InterestCategory.is_active == True)
        .order_by(InterestCategory.display_order, InterestCategory.name)
    )
    categories = cats_result.scalars().all()

    return {
        **preferences,
        "available_interests": [
            InterestCategoryResponse.model_validate(c) for c in categories
        ],
    }


@router.put("/preferences")
async def update_preferences_by_token(  # noqa: role-check -- token-gated email preference update
    prefs: PreferencesUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update email preferences using a token.

    Allows users to manage preferences from email links.
    """
    # Verify token
    result = await db.execute(
        select(EmailUnsubscribeToken).where(
            EmailUnsubscribeToken.token == prefs.token
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired token",
        )

    email = token_record.email

    # Find subscription
    sub_result = await db.execute(
        select(NewsletterSubscription).where(
            NewsletterSubscription.email == email.lower()
        )
    )
    subscription = sub_result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Update subscription
    if prefs.newsletter_enabled is not None:
        if prefs.newsletter_enabled:
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.unsubscribed_at = None
        else:
            subscription.status = SubscriptionStatus.UNSUBSCRIBED
            subscription.unsubscribed_at = datetime.now(timezone.utc)

    if prefs.frequency:
        subscription.frequency = prefs.frequency

    # Update interests if provided
    if prefs.interest_ids is not None:
        # Remove existing
        await db.execute(
            delete(SubscriberInterest).where(
                SubscriberInterest.subscription_id == subscription.id
            )
        )

        # Add new
        for interest_id in prefs.interest_ids:
            interest = SubscriberInterest(
                subscription_id=subscription.id,
                category_id=interest_id,
            )
            db.add(interest)

    await db.commit()

    return {"message": "Preferences updated successfully"}


# =============================================================================
# Admin Endpoints (for staff to manage categories)
# =============================================================================


@router.get("/admin/interests", response_model=list[InterestCategoryResponse])
async def get_admin_interests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all interest categories (admin only)."""
    from ...models.user import UserRole

    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    result = await db.execute(
        select(InterestCategory)
        .order_by(InterestCategory.name)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/admin/interests", status_code=status.HTTP_201_CREATED)
async def create_interest_category(
    name: str,
    slug: str,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new interest category (admin only)."""
    from ...models.user import UserRole

    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Check for duplicate slug
    existing = await db.execute(
        select(InterestCategory).where(InterestCategory.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An interest category with this slug already exists",
        )

    category = InterestCategory(
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        color=color,
        parent_id=parent_id,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return InterestCategoryResponse.model_validate(category)


@router.get("/admin/analytics")
async def get_marketing_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get marketing analytics (admin only)."""
    from sqlalchemy import func

    from ...models.user import UserRole

    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total and active subscribers
    total_result = await db.execute(
        select(func.count()).select_from(NewsletterSubscription)
    )
    total_subscribers = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count())
        .select_from(NewsletterSubscription)
        .where(NewsletterSubscription.status == SubscriptionStatus.ACTIVE)
    )
    active_subscribers = active_result.scalar() or 0

    # New subscribers this month
    new_this_month_result = await db.execute(
        select(func.count())
        .select_from(NewsletterSubscription)
        .where(NewsletterSubscription.created_at >= month_start)
    )
    new_subscribers_this_month = new_this_month_result.scalar() or 0

    # Unsubscribed this month
    unsub_this_month_result = await db.execute(
        select(func.count())
        .select_from(NewsletterSubscription)
        .where(
            and_(
                NewsletterSubscription.status == SubscriptionStatus.UNSUBSCRIBED,
                NewsletterSubscription.updated_at >= month_start,
            )
        )
    )
    unsubscribed_this_month = unsub_this_month_result.scalar() or 0

    # Growth rate (avoid division by zero)
    prev_total = total_subscribers - new_subscribers_this_month + unsubscribed_this_month
    subscriber_growth_rate = (
        ((new_subscribers_this_month - unsubscribed_this_month) / prev_total * 100)
        if prev_total > 0
        else 0.0
    )

    # Subscribers by frequency
    freq_result = await db.execute(
        select(
            NewsletterSubscription.frequency,
            func.count(),
        )
        .where(NewsletterSubscription.status == SubscriptionStatus.ACTIVE)
        .group_by(NewsletterSubscription.frequency)
    )
    subscribers_by_frequency = {row[0].value: row[1] for row in freq_result.all()}

    # Subscribers by interest
    interest_result = await db.execute(
        select(
            InterestCategory.name,
            func.count(SubscriberInterest.id),
        )
        .join(SubscriberInterest, SubscriberInterest.category_id == InterestCategory.id)
        .group_by(InterestCategory.name)
        .order_by(func.count(SubscriberInterest.id).desc())
    )
    subscribers_by_interest = [
        {"interest": row[0], "count": row[1]} for row in interest_result.all()
    ]

    # Subscriber trend (daily counts over the period)
    trend_result = await db.execute(
        select(
            func.date(NewsletterSubscription.created_at).label("date"),
            func.count(),
        )
        .where(NewsletterSubscription.created_at >= start_date)
        .group_by(func.date(NewsletterSubscription.created_at))
        .order_by(func.date(NewsletterSubscription.created_at))
    )
    subscriber_trend = [
        {"date": str(row[0]), "count": row[1]} for row in trend_result.all()
    ]

    return {
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "new_subscribers_this_month": new_subscribers_this_month,
        "unsubscribed_this_month": unsubscribed_this_month,
        "subscriber_growth_rate": round(subscriber_growth_rate, 2),
        "average_open_rate": 0.0,
        "average_click_rate": 0.0,
        "subscribers_by_frequency": subscribers_by_frequency,
        "subscribers_by_interest": subscribers_by_interest,
        "subscriber_trend": subscriber_trend,
    }
