# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.event import Event
from ..models.event_marketing import (
    ArchiveStatus,
    DistributionChannel,
    DistributionStatus,
    EventDistribution,
    EventFeedback,
    EventFlyer,
    EventGraphic,
    EventMarketingCampaign,
    EventRegistrationSource,
    FlyerSize,
    GraphicFormat,
    SocialMediaConfig,
)
from ..models.event_registration import EventRegistration, EventRegistrationStatus

logger = get_logger(__name__)

# Graphic dimensions by format
GRAPHIC_DIMENSIONS = {
    GraphicFormat.FACEBOOK_POST.value: (1200, 630),
    GraphicFormat.INSTAGRAM_SQUARE.value: (1080, 1080),
    GraphicFormat.INSTAGRAM_STORY.value: (1080, 1920),
    GraphicFormat.NEXTDOOR_POST.value: (1200, 900),
    GraphicFormat.EMAIL_HEADER.value: (600, 200),
    GraphicFormat.WEBSITE_BANNER.value: (1920, 600),
}


class EventMarketingService:

    # =========================================================================
    # Campaign CRUD
    # =========================================================================

    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        event_id: int,
        campaign_name: str,
        channels: list[str],
        created_by_id: int | None = None,
        **kwargs,
    ) -> EventMarketingCampaign:
        # Verify event exists
        result = await db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Check for existing campaign
        existing = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.event_id == event_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Campaign already exists for event {event_id}")

        campaign = EventMarketingCampaign(
            event_id=event_id,
            campaign_name=campaign_name,
            channels={ch: True for ch in channels},
            created_by_id=created_by_id,
            **kwargs,
        )
        db.add(campaign)
        await db.flush()

        # Auto-create distribution records for each channel
        for channel in channels:
            if channel == DistributionChannel.COMMUNITY_CALENDAR.value:
                continue  # Calendars are added individually
            distribution = EventDistribution(
                campaign_id=campaign.id,
                channel=channel,
                status=DistributionStatus.PENDING.value,
            )
            db.add(distribution)

        await db.flush()
        await db.refresh(campaign)

        logger.info(
            f"Marketing campaign created for event {event_id}: {campaign_name}"
        )
        return campaign

    @staticmethod
    async def get_campaign(
        db: AsyncSession, campaign_id: int
    ) -> EventMarketingCampaign | None:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_campaign_by_event(
        db: AsyncSession, event_id: int
    ) -> EventMarketingCampaign | None:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.event_id == event_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_campaign(
        db: AsyncSession,
        campaign_id: int,
        **kwargs,
    ) -> EventMarketingCampaign:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        for field, value in kwargs.items():
            if hasattr(campaign, field) and value is not None:
                if field == 'channels' and isinstance(value, list):
                    value = {ch: True for ch in value}
                setattr(campaign, field, value)

        await db.flush()
        await db.refresh(campaign)
        return campaign

    @staticmethod
    async def list_campaigns(
        db: AsyncSession,
        archive_status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[EventMarketingCampaign], int]:
        query = select(EventMarketingCampaign)
        count_query = select(func.count(EventMarketingCampaign.id))

        if archive_status:
            query = query.where(
                EventMarketingCampaign.archive_status == archive_status
            )
            count_query = count_query.where(
                EventMarketingCampaign.archive_status == archive_status
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.order_by(
            EventMarketingCampaign.created_at.desc()
        ).offset(offset).limit(per_page)

        result = await db.execute(query)
        campaigns = result.scalars().all()
        return list(campaigns), total

    # =========================================================================
    # Distribution / Posting
    # =========================================================================

    @staticmethod
    async def distribute_to_channel(
        db: AsyncSession,
        campaign_id: int,
        channel: str,
        schedule_at: datetime | None = None,
    ) -> EventDistribution:
        # Get the campaign with event
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Get or create distribution record
        dist_result = await db.execute(
            select(EventDistribution).where(
                EventDistribution.campaign_id == campaign_id,
                EventDistribution.channel == channel,
            )
        )
        distribution = dist_result.scalar_one_or_none()

        if not distribution:
            distribution = EventDistribution(
                campaign_id=campaign_id,
                channel=channel,
            )
            db.add(distribution)

        if schedule_at:
            distribution.status = DistributionStatus.SCHEDULED.value
            distribution.scheduled_at = schedule_at
        else:
            # Post immediately via platform integration
            try:
                await EventMarketingService._post_to_platform(
                    db, campaign, distribution, channel
                )
                distribution.status = DistributionStatus.POSTED.value
                distribution.posted_at = datetime.now(timezone.utc)
            except Exception as e:  # noqa: BLE001 -- channel failure must not block other channels and must be recorded for retry
                distribution.status = DistributionStatus.FAILED.value
                distribution.failed_at = datetime.now(timezone.utc)
                distribution.failure_reason = str(e)
                distribution.retry_count += 1
                logger.error(
                    f"Failed to post to {channel} for campaign {campaign_id}: {e}"
                )

        await db.flush()
        await db.refresh(distribution)
        return distribution

    @staticmethod
    async def distribute_all(
        db: AsyncSession,
        campaign_id: int,
        schedule_at: datetime | None = None,
    ) -> list[EventDistribution]:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        distributions = []
        for channel in campaign.channels:
            dist = await EventMarketingService.distribute_to_channel(
                db, campaign_id, channel, schedule_at
            )
            distributions.append(dist)

        return distributions

    @staticmethod
    async def _post_to_platform(
        db: AsyncSession,
        campaign: EventMarketingCampaign,
        distribution: EventDistribution,
        channel: str,
    ) -> None:
        # Get event details
        event_result = await db.execute(
            select(Event).where(Event.id == campaign.event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        # Check platform config
        config_result = await db.execute(
            select(SocialMediaConfig).where(
                SocialMediaConfig.platform == channel,
                SocialMediaConfig.is_active == True,
            )
        )
        config = config_result.scalar_one_or_none()

        if channel == DistributionChannel.WEBSITE.value:
            # Website posting is handled by making the event published
            event.is_published = True
            distribution.status = DistributionStatus.POSTED.value
            distribution.posted_at = datetime.now(timezone.utc)
            distribution.platform_url = f"/events/{event.id}"
        elif channel in (
            DistributionChannel.FACEBOOK.value,
            DistributionChannel.INSTAGRAM.value,
            DistributionChannel.NEXTDOOR.value,
        ):
            if not config:
                # Mark as pending manual posting
                distribution.status = DistributionStatus.PENDING.value
                distribution.failure_reason = (
                    f"{channel} API not configured. Post manually or configure API credentials."
                )
                return

            # Generate post content
            post_content = EventMarketingService._generate_social_post(
                event, campaign, config
            )
            distribution.platform_response = {
                "generated_content": post_content,
                "ready_for_api": True,
            }
            # In production: call platform API here
            distribution.status = DistributionStatus.POSTED.value
            distribution.posted_at = datetime.now(timezone.utc)
        elif channel == DistributionChannel.EMAIL.value:
            distribution.status = DistributionStatus.PENDING.value
        elif channel == DistributionChannel.PRINT_FLYER.value:
            distribution.status = DistributionStatus.PENDING.value

    @staticmethod
    def _generate_social_post(
        event: Event,
        campaign: EventMarketingCampaign,
        config: SocialMediaConfig | None = None,
    ) -> dict:
        # Build post text
        title = event.title
        description = campaign.short_description or event.description or ""
        if len(description) > 280:
            description = description[:277] + "..."

        # Build hashtags
        hashtags = list(campaign.hashtags or [])
        if config and config.default_hashtags:
            hashtags.extend(config.default_hashtags)
        hashtag_str = " ".join(f"#{h}" for h in hashtags) if hashtags else ""

        # Format date
        date_str = event.start_time.strftime("%B %d, %Y at %I:%M %p") if event.start_time else ""

        # Location
        location = event.location or "Library"
        if event.is_virtual:
            location = "Virtual Event"

        post_text = f"{title}\n\n{description}\n\n"
        post_text += f"When: {date_str}\n"
        post_text += f"Where: {location}\n"
        if event.registration_required:
            post_text += "\nRegistration required - link in bio!\n"
        if hashtag_str:
            post_text += f"\n{hashtag_str}"

        return {
            "text": post_text.strip(),
            "title": title,
            "date": date_str,
            "location": location,
            "image_url": event.image_url,
            "hashtags": hashtags,
        }

    @staticmethod
    async def get_distributions(
        db: AsyncSession, campaign_id: int
    ) -> list[EventDistribution]:
        result = await db.execute(
            select(EventDistribution)
            .where(EventDistribution.campaign_id == campaign_id)
            .order_by(EventDistribution.created_at)
        )
        return list(result.scalars().all())

    # =========================================================================
    # Community Calendar Submission
    # =========================================================================

    @staticmethod
    async def submit_to_calendar(
        db: AsyncSession,
        campaign_id: int,
        provider: str,
        additional_details: str | None = None,
    ) -> EventDistribution:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        event_result = await db.execute(
            select(Event).where(Event.id == campaign.event_id)
        )
        event = event_result.scalar_one_or_none()

        distribution = EventDistribution(
            campaign_id=campaign_id,
            channel=DistributionChannel.COMMUNITY_CALENDAR.value,
            calendar_provider=provider,
            status=DistributionStatus.POSTED.value,
            posted_at=datetime.now(timezone.utc),
            platform_response={
                "provider": provider,
                "event_title": event.title if event else "",
                "additional_details": additional_details,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
            submission_reference=f"CAL-{secrets.token_hex(4).upper()}",
        )
        db.add(distribution)
        await db.flush()
        await db.refresh(distribution)

        logger.info(
            f"Event submitted to {provider} calendar for campaign {campaign_id}"
        )
        return distribution

    # =========================================================================
    # Flyer Generation
    # =========================================================================

    @staticmethod
    async def generate_flyer(
        db: AsyncSession,
        campaign_id: int,
        generated_by_id: int | None = None,
        size: str = FlyerSize.LETTER.value,
        title: str | None = None,
        subtitle: str | None = None,
        body_text: str | None = None,
        template_name: str | None = None,
        color_scheme: dict | None = None,
        include_logo: bool = True,
        include_map: bool = False,
    ) -> EventFlyer:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        event_result = await db.execute(
            select(Event).where(Event.id == campaign.event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        # Create a tracking link for the QR code
        tracking_source = EventRegistrationSource(
            campaign_id=campaign_id,
            source="flyer",
            medium="qr_code",
            campaign_tag=f"flyer-{size}",
        )
        db.add(tracking_source)
        await db.flush()

        # Build QR code URL with tracking
        base_url = campaign.registration_base_url or f"/events/{event.id}"
        qr_url = f"{base_url}?utm_source=flyer&utm_medium=qr_code&ref={tracking_source.tracking_token}"

        # Generate QR code data (base64 encoded SVG/PNG)
        qr_data = EventMarketingService._generate_qr_code_data(qr_url)

        flyer = EventFlyer(
            campaign_id=campaign_id,
            size=size,
            title=title or event.title,
            subtitle=subtitle or campaign.short_description,
            body_text=body_text or event.description,
            qr_code_url=qr_url,
            qr_code_data=qr_data,
            template_name=template_name,
            color_scheme=color_scheme,
            include_logo=include_logo,
            include_map=include_map,
            generated_by_id=generated_by_id,
        )
        db.add(flyer)
        await db.flush()
        await db.refresh(flyer)

        logger.info(
            f"Flyer generated for campaign {campaign_id}, size={size}"
        )
        return flyer

    @staticmethod
    def _generate_qr_code_data(url: str) -> str:
        try:
            import qrcode
            import qrcode.image.svg
            import io

            factory = qrcode.image.svg.SvgPathImage
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(image_factory=factory)
            stream = io.BytesIO()
            img.save(stream)
            import base64
            return base64.b64encode(stream.getvalue()).decode("utf-8")
        except ImportError:
            # Fallback: return the URL as data (QR library not installed)
            return f"qr_placeholder:{url}"

    @staticmethod
    async def get_flyers(
        db: AsyncSession, campaign_id: int
    ) -> list[EventFlyer]:
        result = await db.execute(
            select(EventFlyer)
            .where(EventFlyer.campaign_id == campaign_id)
            .order_by(EventFlyer.created_at.desc())
        )
        return list(result.scalars().all())

    # =========================================================================
    # Shareable Graphics
    # =========================================================================

    @staticmethod
    async def generate_graphic(
        db: AsyncSession,
        campaign_id: int,
        format: str,
        title: str | None = None,
        template_name: str | None = None,
        color_scheme: dict | None = None,
        background_image_url: str | None = None,
    ) -> EventGraphic:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        event_result = await db.execute(
            select(Event).where(Event.id == campaign.event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        # Get dimensions for format
        width, height = GRAPHIC_DIMENSIONS.get(format, (1200, 630))

        graphic = EventGraphic(
            campaign_id=campaign_id,
            format=format,
            title=title or event.title,
            width=width,
            height=height,
            template_name=template_name,
            color_scheme=color_scheme,
            background_image_url=background_image_url or event.image_url,
        )

        # In production: use Pillow/reportlab to generate actual image
        # For now, store configuration for frontend rendering
        graphic.image_url = f"/api/v1/event-marketing/campaigns/{campaign_id}/graphics/{format}/render"

        db.add(graphic)
        await db.flush()
        await db.refresh(graphic)

        logger.info(
            f"Graphic generated for campaign {campaign_id}, format={format}"
        )
        return graphic

    @staticmethod
    async def generate_all_graphics(
        db: AsyncSession,
        campaign_id: int,
    ) -> list[EventGraphic]:
        formats = [
            GraphicFormat.FACEBOOK_POST.value,
            GraphicFormat.INSTAGRAM_SQUARE.value,
            GraphicFormat.INSTAGRAM_STORY.value,
            GraphicFormat.NEXTDOOR_POST.value,
            GraphicFormat.EMAIL_HEADER.value,
            GraphicFormat.WEBSITE_BANNER.value,
        ]
        graphics = []
        for fmt in formats:
            graphic = await EventMarketingService.generate_graphic(
                db, campaign_id, fmt
            )
            graphics.append(graphic)
        return graphics

    @staticmethod
    async def get_graphics(
        db: AsyncSession, campaign_id: int
    ) -> list[EventGraphic]:
        result = await db.execute(
            select(EventGraphic)
            .where(EventGraphic.campaign_id == campaign_id)
            .order_by(EventGraphic.created_at.desc())
        )
        return list(result.scalars().all())

    # =========================================================================
    # Email to Interested Patrons
    # =========================================================================

    @staticmethod
    async def send_event_email(
        db: AsyncSession,
        campaign_id: int,
        subject: str | None = None,
        preview_text: str | None = None,
        target_interest_ids: list[int] | None = None,
        target_all: bool = False,
    ) -> dict:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        event_result = await db.execute(
            select(Event).where(Event.id == campaign.event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        # Create tracking source for email
        tracking_source = EventRegistrationSource(
            campaign_id=campaign_id,
            source="email",
            medium="newsletter",
            campaign_tag=f"event-{event.id}-email",
        )
        db.add(tracking_source)
        await db.flush()

        # Count target recipients using existing subscriber infrastructure
        from ..models.marketing import (
            NewsletterSubscription,
            SubscriberInterest,
            SubscriptionStatus,
        )

        query = select(func.count(NewsletterSubscription.id)).where(
            NewsletterSubscription.status == SubscriptionStatus.ACTIVE
        )
        if target_interest_ids and not target_all:
            query = query.join(SubscriberInterest).where(
                SubscriberInterest.category_id.in_(target_interest_ids)
            )

        count_result = await db.execute(query)
        recipients_count = count_result.scalar() or 0

        # Update distribution record for email channel
        dist_result = await db.execute(
            select(EventDistribution).where(
                EventDistribution.campaign_id == campaign_id,
                EventDistribution.channel == DistributionChannel.EMAIL.value,
            )
        )
        distribution = dist_result.scalar_one_or_none()
        if distribution:
            distribution.status = DistributionStatus.POSTED.value
            distribution.posted_at = datetime.now(timezone.utc)
            distribution.platform_response = {
                "recipients_count": recipients_count,
                "subject": subject or f"Upcoming: {event.title}",
                "tracking_token": tracking_source.tracking_token,
            }

        logger.info(
            f"Event email queued for campaign {campaign_id}: "
            f"{recipients_count} recipients"
        )

        return {
            "campaign_id": campaign_id,
            "recipients_count": recipients_count,
            "status": "sent",
            "tracking_token": tracking_source.tracking_token,
        }

    # =========================================================================
    # Registration Source Tracking
    # =========================================================================

    @staticmethod
    async def create_tracking_link(
        db: AsyncSession,
        campaign_id: int,
        source: str,
        medium: str | None = None,
        campaign_tag: str | None = None,
        content: str | None = None,
    ) -> EventRegistrationSource:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        tracking = EventRegistrationSource(
            campaign_id=campaign_id,
            source=source,
            medium=medium,
            campaign_tag=campaign_tag,
            content=content,
        )
        db.add(tracking)
        await db.flush()
        await db.refresh(tracking)
        return tracking

    @staticmethod
    async def record_click(
        db: AsyncSession, tracking_token: str, referrer_url: str | None = None
    ) -> EventRegistrationSource | None:
        result = await db.execute(
            select(EventRegistrationSource).where(
                EventRegistrationSource.tracking_token == tracking_token
            )
        )
        tracking = result.scalar_one_or_none()
        if not tracking:
            return None

        tracking.click_count += 1
        if not tracking.first_clicked_at:
            tracking.first_clicked_at = datetime.now(timezone.utc)
        if referrer_url:
            tracking.referrer_url = referrer_url

        await db.flush()
        return tracking

    @staticmethod
    async def record_conversion(
        db: AsyncSession,
        tracking_token: str,
        registration_id: int,
    ) -> EventRegistrationSource | None:
        result = await db.execute(
            select(EventRegistrationSource).where(
                EventRegistrationSource.tracking_token == tracking_token
            )
        )
        tracking = result.scalar_one_or_none()
        if not tracking:
            return None

        tracking.registration_id = registration_id
        tracking.converted_at = datetime.now(timezone.utc)
        await db.flush()
        return tracking

    @staticmethod
    async def get_source_analytics(
        db: AsyncSession, campaign_id: int
    ) -> list[dict]:
        result = await db.execute(
            select(
                EventRegistrationSource.source,
                EventRegistrationSource.medium,
                func.sum(EventRegistrationSource.click_count).label("total_clicks"),
                func.count(EventRegistrationSource.converted_at).label("conversions"),
            )
            .where(EventRegistrationSource.campaign_id == campaign_id)
            .group_by(
                EventRegistrationSource.source,
                EventRegistrationSource.medium,
            )
        )

        analytics = []
        for row in result.all():
            total_clicks = row.total_clicks or 0
            conversions = row.conversions or 0
            analytics.append({
                "source": row.source,
                "medium": row.medium,
                "total_clicks": total_clicks,
                "total_conversions": conversions,
                "conversion_rate": (
                    round(conversions / total_clicks * 100, 1)
                    if total_clicks > 0
                    else 0.0
                ),
            })
        return analytics

    # =========================================================================
    # Campaign Analytics
    # =========================================================================

    @staticmethod
    async def get_campaign_analytics(
        db: AsyncSession, campaign_id: int
    ) -> dict:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Distribution stats
        dist_result = await db.execute(
            select(EventDistribution).where(
                EventDistribution.campaign_id == campaign_id
            )
        )
        distributions = dist_result.scalars().all()

        total_impressions = sum(d.impressions for d in distributions)
        total_clicks = sum(d.clicks for d in distributions)
        successful = sum(
            1 for d in distributions
            if d.status == DistributionStatus.POSTED.value
        )
        failed = sum(
            1 for d in distributions
            if d.status == DistributionStatus.FAILED.value
        )

        # Registration stats
        reg_result = await db.execute(
            select(func.count(EventRegistration.id))
            .where(EventRegistration.event_id == campaign.event_id)
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
        )
        total_registrations = reg_result.scalar() or 0

        # Source analytics
        sources = await EventMarketingService.get_source_analytics(
            db, campaign_id
        )

        return {
            "campaign_id": campaign_id,
            "event_id": campaign.event_id,
            "campaign_name": campaign.campaign_name,
            "total_distributions": len(distributions),
            "successful_distributions": successful,
            "failed_distributions": failed,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_registrations": total_registrations,
            "sources": sources,
        }

    # =========================================================================
    # Post-Event: Auto-Archive and Feedback
    # =========================================================================

    @staticmethod
    async def archive_event(
        db: AsyncSession,
        campaign_id: int,
        request_feedback: bool = True,
        feedback_deadline_days: int = 14,
    ) -> EventMarketingCampaign:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        now = datetime.now(timezone.utc)
        campaign.archived_at = now

        if request_feedback:
            campaign.archive_status = ArchiveStatus.FEEDBACK_PENDING.value
            campaign.feedback_requested_at = now
            campaign.feedback_deadline = now + timedelta(
                days=feedback_deadline_days
            )
        else:
            campaign.archive_status = ArchiveStatus.ARCHIVED.value

        await db.flush()
        await db.refresh(campaign)

        logger.info(
            f"Campaign {campaign_id} archived, "
            f"feedback={'requested' if request_feedback else 'skipped'}"
        )
        return campaign

    @staticmethod
    async def auto_archive_past_events(db: AsyncSession) -> list[int]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(EventMarketingCampaign)
            .join(Event, EventMarketingCampaign.event_id == Event.id)
            .where(EventMarketingCampaign.archive_status == ArchiveStatus.ACTIVE.value)
            .where(Event.start_time < now - timedelta(hours=2))
        )
        campaigns = result.scalars().all()

        archived_ids = []
        for campaign in campaigns:
            campaign.archive_status = ArchiveStatus.FEEDBACK_PENDING.value
            campaign.archived_at = now
            campaign.feedback_requested_at = now
            campaign.feedback_deadline = now + timedelta(days=14)
            archived_ids.append(campaign.id)

        if archived_ids:
            await db.flush()
            logger.info(f"Auto-archived {len(archived_ids)} campaigns")

        return archived_ids

    @staticmethod
    async def submit_feedback(
        db: AsyncSession,
        campaign_id: int,
        overall_rating: int,
        patron_email: str | None = None,
        patron_name: str | None = None,
        is_anonymous: bool = False,
        **kwargs,
    ) -> EventFeedback:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        feedback = EventFeedback(
            campaign_id=campaign_id,
            event_id=campaign.event_id,
            overall_rating=overall_rating,
            patron_email=patron_email if not is_anonymous else None,
            patron_name=patron_name if not is_anonymous else None,
            is_anonymous=is_anonymous,
            **kwargs,
        )
        db.add(feedback)
        await db.flush()
        await db.refresh(feedback)

        logger.info(
            f"Feedback submitted for campaign {campaign_id}, "
            f"rating={overall_rating}"
        )
        return feedback

    @staticmethod
    async def get_feedback_summary(
        db: AsyncSession, campaign_id: int
    ) -> dict:
        result = await db.execute(
            select(EventMarketingCampaign).where(
                EventMarketingCampaign.id == campaign_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Aggregate ratings
        stats_result = await db.execute(
            select(
                func.count(EventFeedback.id),
                func.avg(EventFeedback.overall_rating),
            )
            .where(EventFeedback.campaign_id == campaign_id)
        )
        stats = stats_result.one()
        total = stats[0] or 0
        avg_rating = round(float(stats[1]), 1) if stats[1] else None

        # Would attend again / recommend percentages
        attend_result = await db.execute(
            select(
                func.count(EventFeedback.id).filter(
                    EventFeedback.would_attend_again == True
                ),
                func.count(EventFeedback.id).filter(
                    EventFeedback.would_attend_again.isnot(None)
                ),
            )
            .where(EventFeedback.campaign_id == campaign_id)
        )
        attend_row = attend_result.one()
        attend_pct = (
            round(attend_row[0] / attend_row[1] * 100, 1)
            if attend_row[1] > 0
            else None
        )

        recommend_result = await db.execute(
            select(
                func.count(EventFeedback.id).filter(
                    EventFeedback.would_recommend == True
                ),
                func.count(EventFeedback.id).filter(
                    EventFeedback.would_recommend.isnot(None)
                ),
            )
            .where(EventFeedback.campaign_id == campaign_id)
        )
        recommend_row = recommend_result.one()
        recommend_pct = (
            round(recommend_row[0] / recommend_row[1] * 100, 1)
            if recommend_row[1] > 0
            else None
        )

        # How heard about sources
        sources_result = await db.execute(
            select(
                EventFeedback.heard_from_source,
                func.count(EventFeedback.id),
            )
            .where(EventFeedback.campaign_id == campaign_id)
            .where(EventFeedback.heard_from_source.isnot(None))
            .group_by(EventFeedback.heard_from_source)
            .order_by(func.count(EventFeedback.id).desc())
            .limit(10)
        )
        top_sources = [
            {"source": row[0], "count": row[1]}
            for row in sources_result.all()
        ]

        # Recent comments
        comments_result = await db.execute(
            select(EventFeedback)
            .where(EventFeedback.campaign_id == campaign_id)
            .where(EventFeedback.what_liked.isnot(None))
            .order_by(EventFeedback.created_at.desc())
            .limit(5)
        )
        recent_comments = [
            {
                "rating": f.overall_rating,
                "what_liked": f.what_liked,
                "what_improve": f.what_improve,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in comments_result.scalars().all()
        ]

        return {
            "campaign_id": campaign_id,
            "event_id": campaign.event_id,
            "total_responses": total,
            "average_rating": avg_rating,
            "would_attend_again_pct": attend_pct,
            "would_recommend_pct": recommend_pct,
            "top_sources": top_sources,
            "recent_comments": recent_comments,
        }
