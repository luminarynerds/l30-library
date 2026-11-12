# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Event Marketing Automation API Endpoints

Provides REST endpoints for:
- Creating and managing marketing campaigns
- Distributing events to channels
- Generating print flyers with QR codes
- Creating shareable graphics
- Tracking registration sources
- Collecting post-event feedback
"""
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.user import User
from ...schemas.event_marketing import (
    ArchiveRequest,
    CalendarSubmissionRequest,
    CampaignAnalytics,
    DistributeRequest,
    EventEmailRequest,
    EventEmailResponse,
    EventMarketingCampaignCreate,
    EventMarketingCampaignResponse,
    EventMarketingCampaignUpdate,
    FeedbackResponse,
    FeedbackSubmitRequest,
    FeedbackSummary,
    FlyerGenerateRequest,
    FlyerResponse,
    GraphicGenerateRequest,
    GraphicResponse,
    SocialMediaConfigResponse,
    SocialMediaConfigUpdate,
    TrackingLinkCreateRequest,
    TrackingLinkResponse,
)
from ...services.event_marketing_service import EventMarketingService
from .dependencies import require_staff

router = APIRouter(prefix="/event-marketing", tags=["event-marketing"])
logger = get_logger(__name__)


# =============================================================================
# Campaign Management
# =============================================================================


@router.post("/campaigns", response_model=EventMarketingCampaignResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_campaign(
    request: Request,
    campaign: EventMarketingCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> EventMarketingCampaignResponse:
    """Create a marketing campaign for an event."""
    try:
        result = await EventMarketingService.create_campaign(
            db=db,
            created_by_id=current_user.id,
            **campaign.model_dump(),
        )
        await db.commit()
        return EventMarketingCampaignResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns", response_model=dict)
@limiter.limit("60/minute")
async def list_campaigns(
    request: Request,
    archive_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """List marketing campaigns."""
    campaigns, total = await EventMarketingService.list_campaigns(
        db=db,
        archive_status=archive_status,
        page=page,
        per_page=per_page,
    )
    return {
        "data": [
            EventMarketingCampaignResponse.model_validate(c) for c in campaigns
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }


@router.get("/campaigns/{campaign_id}", response_model=EventMarketingCampaignResponse)
@limiter.limit("60/minute")
async def get_campaign(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> EventMarketingCampaignResponse:
    """Get a campaign by ID."""
    campaign = await EventMarketingService.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return EventMarketingCampaignResponse.model_validate(campaign)


@router.put("/campaigns/{campaign_id}", response_model=EventMarketingCampaignResponse)
@limiter.limit("20/minute")
async def update_campaign(
    request: Request,
    campaign_id: int,
    update: EventMarketingCampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> EventMarketingCampaignResponse:
    """Update a campaign."""
    try:
        result = await EventMarketingService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            **update.model_dump(exclude_unset=True),
        )
        await db.commit()
        return EventMarketingCampaignResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Distribution / Posting
# =============================================================================


@router.post("/campaigns/{campaign_id}/distribute", response_model=dict)
@limiter.limit("10/minute")
async def distribute_campaign(
    request: Request,
    campaign_id: int,
    dist_req: DistributeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Distribute an event to marketing channels."""
    try:
        if dist_req.channels:
            distributions = []
            for channel in dist_req.channels:
                dist = await EventMarketingService.distribute_to_channel(
                    db=db,
                    campaign_id=campaign_id,
                    channel=channel,
                    schedule_at=dist_req.schedule_at,
                )
                distributions.append(dist)
        else:
            distributions = await EventMarketingService.distribute_all(
                db=db,
                campaign_id=campaign_id,
                schedule_at=dist_req.schedule_at,
            )

        await db.commit()
        return {
            "message": "Distribution initiated",
            "channels_count": len(distributions),
            "status": "success",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns/{campaign_id}/distributions", response_model=dict)
@limiter.limit("60/minute")
async def get_distributions(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Get all distributions for a campaign."""
    distributions = await EventMarketingService.get_distributions(db, campaign_id)
    return {
        "distributions": [
            {
                "id": d.id,
                "channel": d.channel,
                "status": d.status,
                "posted_at": d.posted_at,
                "impressions": d.impressions,
                "clicks": d.clicks,
            }
            for d in distributions
        ]
    }


@router.post("/campaigns/{campaign_id}/calendars", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def submit_to_calendar(
    request: Request,
    campaign_id: int,
    cal_req: CalendarSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Submit an event to a community calendar."""
    try:
        distribution = await EventMarketingService.submit_to_calendar(
            db=db,
            campaign_id=campaign_id,
            provider=cal_req.provider,
            additional_details=cal_req.additional_details,
        )
        await db.commit()
        return {
            "message": f"Event submitted to {cal_req.provider}",
            "submission_reference": distribution.submission_reference,
            "status": "success",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Print Flyers
# =============================================================================


@router.post("/campaigns/{campaign_id}/flyers", response_model=FlyerResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def generate_flyer(
    request: Request,
    campaign_id: int,
    flyer_req: FlyerGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> FlyerResponse:
    """Generate a print flyer with QR code."""
    try:
        result = await EventMarketingService.generate_flyer(
            db=db,
            campaign_id=campaign_id,
            generated_by_id=current_user.id,
            **flyer_req.model_dump(),
        )
        await db.commit()
        return FlyerResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns/{campaign_id}/flyers", response_model=dict)
@limiter.limit("60/minute")
async def list_flyers(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Get all flyers for a campaign."""
    flyers = await EventMarketingService.get_flyers(db, campaign_id)
    return {
        "flyers": [FlyerResponse.model_validate(f) for f in flyers]
    }


# =============================================================================
# Shareable Graphics
# =============================================================================


@router.post("/campaigns/{campaign_id}/graphics", response_model=GraphicResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def generate_graphic(
    request: Request,
    campaign_id: int,
    graphic_req: GraphicGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> GraphicResponse:
    """Generate a shareable graphic."""
    try:
        result = await EventMarketingService.generate_graphic(
            db=db,
            campaign_id=campaign_id,
            **graphic_req.model_dump(),
        )
        await db.commit()
        return GraphicResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/campaigns/{campaign_id}/graphics/generate-all", response_model=dict)
@limiter.limit("10/minute")
async def generate_all_graphics(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Generate graphics for all standard formats."""
    try:
        graphics = await EventMarketingService.generate_all_graphics(
            db=db,
            campaign_id=campaign_id,
        )
        await db.commit()
        return {
            "message": "All graphics generated",
            "count": len(graphics),
            "graphics": [GraphicResponse.model_validate(g) for g in graphics],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns/{campaign_id}/graphics", response_model=dict)
@limiter.limit("60/minute")
async def list_graphics(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Get all graphics for a campaign."""
    graphics = await EventMarketingService.get_graphics(db, campaign_id)
    return {
        "graphics": [GraphicResponse.model_validate(g) for g in graphics]
    }


# =============================================================================
# Email to Patrons
# =============================================================================


@router.post("/campaigns/{campaign_id}/send-email", response_model=EventEmailResponse)
@limiter.limit("10/minute")
async def send_event_email(
    request: Request,
    campaign_id: int,
    email_req: EventEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> EventEmailResponse:
    """Send event email to interested patrons."""
    try:
        result = await EventMarketingService.send_event_email(
            db=db,
            campaign_id=campaign_id,
            subject=email_req.subject,
            preview_text=email_req.preview_text,
            target_interest_ids=email_req.target_interests,
            target_all=email_req.target_all_subscribers,
        )
        await db.commit()
        return EventEmailResponse(
            campaign_id=campaign_id,
            recipients_count=result["recipients_count"],
            scheduled_at=email_req.send_at,
            status=result["status"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Registration Source Tracking
# =============================================================================


@router.post("/campaigns/{campaign_id}/tracking-links", response_model=TrackingLinkResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_tracking_link(
    request: Request,
    campaign_id: int,
    track_req: TrackingLinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> TrackingLinkResponse:
    """Create a tracking link for a channel."""
    try:
        result = await EventMarketingService.create_tracking_link(
            db=db,
            campaign_id=campaign_id,
            **track_req.model_dump(),
        )
        await db.commit()

        # Build full registration URL with tracking token
        registration_url = f"/events/{{event_id}}/register?ref={result.tracking_token}"

        response = TrackingLinkResponse.model_validate(result)
        response.registration_url = registration_url
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns/{campaign_id}/analytics", response_model=CampaignAnalytics)
@limiter.limit("60/minute")
async def get_campaign_analytics(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> CampaignAnalytics:
    """Get campaign analytics including registration sources."""
    try:
        analytics = await EventMarketingService.get_campaign_analytics(
            db=db,
            campaign_id=campaign_id,
        )
        return CampaignAnalytics(**analytics)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Post-Event: Archive and Feedback
# =============================================================================


@router.post("/campaigns/{campaign_id}/archive", response_model=EventMarketingCampaignResponse)
@limiter.limit("10/minute")
async def archive_campaign(
    request: Request,
    campaign_id: int,
    archive_req: ArchiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> EventMarketingCampaignResponse:
    """Archive an event and optionally request feedback."""
    try:
        result = await EventMarketingService.archive_event(
            db=db,
            campaign_id=campaign_id,
            request_feedback=archive_req.request_feedback,
            feedback_deadline_days=archive_req.feedback_deadline_days,
        )
        await db.commit()
        return EventMarketingCampaignResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/campaigns/{campaign_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def submit_feedback(  # noqa: role-check -- public post-event feedback, rate-limited
    request: Request,
    campaign_id: int,
    feedback: FeedbackSubmitRequest,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit post-event feedback (public endpoint)."""
    try:
        result = await EventMarketingService.submit_feedback(
            db=db,
            campaign_id=campaign_id,
            overall_rating=feedback.overall_rating,
            patron_email=feedback.patron_email,
            patron_name=feedback.patron_name,
            is_anonymous=feedback.is_anonymous,
            would_attend_again=feedback.would_attend_again,
            would_recommend=feedback.would_recommend,
            what_liked=feedback.what_liked,
            what_improve=feedback.what_improve,
            suggestions=feedback.suggestions,
            heard_from_source=feedback.heard_from_source,
        )
        await db.commit()
        return FeedbackResponse.model_validate(result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/campaigns/{campaign_id}/feedback/summary", response_model=FeedbackSummary)
@limiter.limit("60/minute")
async def get_feedback_summary(
    request: Request,
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> FeedbackSummary:
    """Get feedback summary for a campaign."""
    try:
        summary = await EventMarketingService.get_feedback_summary(
            db=db,
            campaign_id=campaign_id,
        )
        return FeedbackSummary(**summary)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Social Media Configuration (Admin)
# =============================================================================


@router.get("/social-media-config/{platform}", response_model=SocialMediaConfigResponse)
@limiter.limit("60/minute")
async def get_social_media_config(
    request: Request,
    platform: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SocialMediaConfigResponse:
    """Get social media configuration for a platform."""
    from ...models.event_marketing import SocialMediaConfig

    result = await db.execute(
        select(SocialMediaConfig).where(SocialMediaConfig.platform == platform)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not configured")

    response_data = SocialMediaConfigResponse.model_validate(config).model_dump()
    response_data["has_api_key"] = bool(config.api_key)
    response_data["has_access_token"] = bool(config.access_token)
    return response_data


@router.put("/social-media-config/{platform}", response_model=SocialMediaConfigResponse)
@limiter.limit("10/minute")
async def update_social_media_config(
    request: Request,
    platform: str,
    config_update: SocialMediaConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SocialMediaConfigResponse:
    """Update social media platform configuration."""
    from ...models.event_marketing import SocialMediaConfig

    result = await db.execute(
        select(SocialMediaConfig).where(SocialMediaConfig.platform == platform)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = SocialMediaConfig(platform=platform)
        db.add(config)

    for field, value in config_update.model_dump(exclude_unset=True).items():
        if hasattr(config, field) and value is not None:
            setattr(config, field, value)

    config.configured_by_id = current_user.id
    await db.flush()
    await db.commit()
    await db.refresh(config)

    response_data = SocialMediaConfigResponse.model_validate(config).model_dump()
    response_data["has_api_key"] = bool(config.api_key)
    response_data["has_access_token"] = bool(config.access_token)
    return response_data


# Fix missing import
from sqlalchemy import select
