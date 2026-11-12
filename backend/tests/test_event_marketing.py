# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Event Marketing Automation API endpoints.

Covers:
- Campaign creation and management
- Multi-channel distribution
- Flyer and graphic generation
- Registration source tracking
- Post-event feedback collection
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.models.event import Event
from app.models.event_marketing import (
    EventMarketingCampaign,
    EventDistribution,
    EventFlyer,
    EventGraphic,
    EventRegistrationSource,
    EventFeedback,
)
from app.models.user import User, UserRole
from app.services.event_marketing_service import EventMarketingService


@pytest.fixture
async def staff_user(db: AsyncSession) -> User:
    """Create a staff user for testing."""
    user = User(
        email="staff@library.local",
        first_name="Staff",
        last_name="Member",
        role=UserRole.STAFF,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def test_event(db: AsyncSession) -> Event:
    """Create a test event."""
    event = Event(
        title="Summer Reading Kickoff",
        description="Join us for an exciting start to summer reading!",
        start_time=datetime.now(timezone.utc) + timedelta(days=7),
        end_time=datetime.now(timezone.utc) + timedelta(days=7, hours=2),
        location="Main Library - Auditorium",
        is_virtual=False,
        audience="All Ages",
        category="Reading Program",
        tags=["summer", "reading", "kickoff"],
        max_attendees=100,
        registration_required=True,
        image_url="https://library.local/images/event.jpg",
        is_published=True,
    )
    db.add(event)
    await db.flush()
    return event


class TestCampaignCreation:
    """Test marketing campaign creation and management."""

    async def test_create_campaign(self, db: AsyncSession, test_event: Event, staff_user: User):
        """Test creating a marketing campaign."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Summer Reading 2026",
            channels=["website", "facebook", "email"],
            created_by_id=staff_user.id,
            short_description="Get excited for summer reading!",
        )
        await db.flush()

        assert campaign.event_id == test_event.id
        assert campaign.campaign_name == "Summer Reading 2026"
        assert "website" in campaign.channels
        assert "facebook" in campaign.channels
        assert campaign.created_by_id == staff_user.id

    async def test_create_campaign_duplicate_event(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test that duplicate campaigns for same event are prevented."""
        await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="First Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        with pytest.raises(ValueError, match="Campaign already exists"):
            await EventMarketingService.create_campaign(
                db=db,
                event_id=test_event.id,
                campaign_name="Second Campaign",
                channels=["facebook"],
                created_by_id=staff_user.id,
            )

    async def test_get_campaign(self, db: AsyncSession, test_event: Event, staff_user: User):
        """Test retrieving a campaign."""
        created = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        retrieved = await EventMarketingService.get_campaign(db, created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.campaign_name == "Test Campaign"

    async def test_list_campaigns(self, db: AsyncSession, test_event: Event, staff_user: User):
        """Test listing campaigns."""
        await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Campaign 1",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        campaigns, total = await EventMarketingService.list_campaigns(db)
        assert total >= 1
        assert len(campaigns) >= 1


class TestDistribution:
    """Test event distribution to channels."""

    async def test_distribute_to_website(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test distribution to website channel."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        distribution = await EventMarketingService.distribute_to_channel(
            db=db,
            campaign_id=campaign.id,
            channel="website",
        )
        await db.flush()

        assert distribution.status == "posted"
        assert distribution.posted_at is not None
        assert test_event.is_published is True

    async def test_schedule_distribution(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test scheduling distribution for later."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["email"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        distribution = await EventMarketingService.distribute_to_channel(
            db=db,
            campaign_id=campaign.id,
            channel="email",
            schedule_at=future_time,
        )
        await db.flush()

        assert distribution.status == "scheduled"
        assert distribution.scheduled_at == future_time

    async def test_distribute_all_channels(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test distributing to all configured channels."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Multi-channel Campaign",
            channels=["website", "facebook", "email"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        distributions = await EventMarketingService.distribute_all(
            db=db,
            campaign_id=campaign.id,
        )
        await db.flush()

        assert len(distributions) == 3
        channels = [d.channel for d in distributions]
        assert "website" in channels
        assert "facebook" in channels
        assert "email" in channels


class TestFlyerGeneration:
    """Test print flyer generation with QR codes."""

    async def test_generate_flyer(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test generating a print flyer."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["print_flyer"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        flyer = await EventMarketingService.generate_flyer(
            db=db,
            campaign_id=campaign.id,
            generated_by_id=staff_user.id,
            size="letter",
            title="Summer Reading Kickoff",
        )
        await db.flush()

        assert flyer.campaign_id == campaign.id
        assert flyer.size == "letter"
        assert flyer.qr_code_url is not None
        assert flyer.qr_code_data is not None

    async def test_generate_flyer_sizes(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test generating flyers in different sizes."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["print_flyer"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        for size in ["letter", "half_letter", "poster", "bookmark"]:
            flyer = await EventMarketingService.generate_flyer(
                db=db,
                campaign_id=campaign.id,
                generated_by_id=staff_user.id,
                size=size,
            )
            await db.flush()
            assert flyer.size == size


class TestGraphicGeneration:
    """Test shareable graphics generation."""

    async def test_generate_graphic(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test generating a shareable graphic."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["facebook"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        graphic = await EventMarketingService.generate_graphic(
            db=db,
            campaign_id=campaign.id,
            format="facebook_post",
            title="Summer Reading Kickoff",
        )
        await db.flush()

        assert graphic.campaign_id == campaign.id
        assert graphic.format == "facebook_post"
        assert graphic.width == 1200
        assert graphic.height == 630

    async def test_generate_all_graphics(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test generating all standard graphics."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["facebook", "instagram"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        graphics = await EventMarketingService.generate_all_graphics(
            db=db,
            campaign_id=campaign.id,
        )
        await db.flush()

        assert len(graphics) == 6
        formats = [g.format for g in graphics]
        assert "facebook_post" in formats
        assert "instagram_square" in formats
        assert "instagram_story" in formats


class TestRegistrationTracking:
    """Test registration source tracking."""

    async def test_create_tracking_link(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test creating a tracking link."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["email"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        tracking = await EventMarketingService.create_tracking_link(
            db=db,
            campaign_id=campaign.id,
            source="email",
            medium="newsletter",
            campaign_tag="summer-2026",
        )
        await db.flush()

        assert tracking.campaign_id == campaign.id
        assert tracking.source == "email"
        assert tracking.medium == "newsletter"
        assert tracking.tracking_token is not None

    async def test_record_click(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test recording a click on a tracking link."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["email"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        tracking = await EventMarketingService.create_tracking_link(
            db=db,
            campaign_id=campaign.id,
            source="flyer",
            medium="qr_code",
        )
        await db.flush()

        await EventMarketingService.record_click(
            db=db,
            tracking_token=tracking.tracking_token,
        )
        await db.flush()

        assert tracking.click_count == 1
        assert tracking.first_clicked_at is not None

    async def test_get_source_analytics(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test getting source analytics."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["email", "facebook"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        # Create multiple tracking sources
        for i in range(3):
            await EventMarketingService.create_tracking_link(
                db=db,
                campaign_id=campaign.id,
                source="email",
                medium="newsletter",
            )
        await db.flush()

        analytics = await EventMarketingService.get_source_analytics(
            db=db,
            campaign_id=campaign.id,
        )

        assert len(analytics) > 0
        email_sources = [a for a in analytics if a["source"] == "email"]
        assert len(email_sources) > 0


class TestPostEventArchive:
    """Test post-event archiving and feedback."""

    async def test_archive_event(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test archiving an event."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        archived = await EventMarketingService.archive_event(
            db=db,
            campaign_id=campaign.id,
            request_feedback=True,
            feedback_deadline_days=14,
        )
        await db.flush()

        assert archived.archive_status == "feedback_pending"
        assert archived.archived_at is not None
        assert archived.feedback_requested_at is not None
        assert archived.feedback_deadline is not None

    async def test_submit_feedback(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test submitting post-event feedback."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        feedback = await EventMarketingService.submit_feedback(
            db=db,
            campaign_id=campaign.id,
            overall_rating=5,
            patron_email="patron@library.local",
            patron_name="Test Patron",
            would_attend_again=True,
            would_recommend=True,
            what_liked="Great event!",
        )
        await db.flush()

        assert feedback.campaign_id == campaign.id
        assert feedback.overall_rating == 5
        assert feedback.patron_email == "patron@library.local"
        assert feedback.is_anonymous is False

    async def test_submit_anonymous_feedback(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test submitting anonymous feedback."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        feedback = await EventMarketingService.submit_feedback(
            db=db,
            campaign_id=campaign.id,
            overall_rating=3,
            is_anonymous=True,
            what_improve="More time would be nice",
        )
        await db.flush()

        assert feedback.is_anonymous is True
        assert feedback.patron_email is None
        assert feedback.patron_name is None
        assert feedback.feedback_token is not None

    async def test_get_feedback_summary(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test getting feedback summary."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        # Submit multiple feedback responses
        for i in range(3):
            await EventMarketingService.submit_feedback(
                db=db,
                campaign_id=campaign.id,
                overall_rating=5 - i,
                would_attend_again=i < 2,
                would_recommend=i < 2,
                heard_from_source="email" if i % 2 == 0 else "facebook",
            )
        await db.flush()

        summary = await EventMarketingService.get_feedback_summary(
            db=db,
            campaign_id=campaign.id,
        )

        assert summary["total_responses"] == 3
        assert summary["average_rating"] is not None
        assert summary["would_attend_again_pct"] is not None
        assert summary["would_recommend_pct"] is not None


class TestCampaignAnalytics:
    """Test campaign analytics and reporting."""

    async def test_get_campaign_analytics(
        self, db: AsyncSession, test_event: Event, staff_user: User
    ):
        """Test getting campaign analytics."""
        campaign = await EventMarketingService.create_campaign(
            db=db,
            event_id=test_event.id,
            campaign_name="Test Campaign",
            channels=["website", "email"],
            created_by_id=staff_user.id,
        )
        await db.flush()

        analytics = await EventMarketingService.get_campaign_analytics(
            db=db,
            campaign_id=campaign.id,
        )

        assert analytics["campaign_id"] == campaign.id
        assert analytics["event_id"] == test_event.id
        assert analytics["total_distributions"] >= 0
        assert analytics["total_registrations"] >= 0
        assert isinstance(analytics["sources"], list)
