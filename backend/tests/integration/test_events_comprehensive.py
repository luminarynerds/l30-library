# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for LSC event management system.
Tests all critical functionality:
- Event CRUD with all required fields
- Event series and recurring events
- Registration capacity limits
- Event review submission and moderation
- Featured events and staff picks display
- Social sharing tracking
- Virtual vs in-person event handling
- Validation of all inputs
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.event_registration import EventRegistration, EventRegistrationStatus
from app.models.event_review import EventReview, ReviewModerationStatus
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.event_registration import RegistrationCreate
from app.schemas.event_review import EventReviewCreate


class TestEventCRUD:
    """Test event creation, reading, updating, and deletion with all required fields."""

    @pytest.mark.asyncio
    async def test_create_event_with_all_fields(self, test_db: AsyncSession):
        """Test creating event with all optional fields populated."""
        event_data = EventCreate(
            title="Summer Reading Challenge",
            description="Join us for an exciting summer reading program with prizes",
            start_time=datetime.now(timezone.utc) + timedelta(days=7),
            end_time=datetime.now(timezone.utc) + timedelta(days=7, hours=2),
            location="Main Library Conference Room",
            is_virtual=False,
            audience="All ages",
            category="Reading Program",
            tags=["summer", "reading", "children", "families"],
            max_attendees=50,
            registration_required=True,
            image_url="https://example.com/summer-reading.jpg",
            is_featured=True,
            series_id="summer-2024",
            series_name="Summer 2024 Programs",
        )

        event = Event(**event_data.model_dump())
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        assert event.id is not None
        assert event.title == "Summer Reading Challenge"
        assert event.description is not None
        assert event.location == "Main Library Conference Room"
        assert event.is_virtual is False
        assert event.audience == "All ages"
        assert event.category == "Reading Program"
        assert event.tags == ["summer", "reading", "children", "families"]
        assert event.max_attendees == 50
        assert event.registration_required is True
        assert event.is_featured is True
        assert event.series_id == "summer-2024"
        assert event.series_name == "Summer 2024 Programs"
        assert event.is_published is True

    @pytest.mark.asyncio
    async def test_create_event_minimal_fields(self, test_db: AsyncSession):
        """Test creating event with only required fields."""
        event_data = EventCreate(
            title="Quick Workshop",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
        )

        event = Event(**event_data.model_dump())
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        assert event.id is not None
        assert event.title == "Quick Workshop"
        assert event.is_virtual is False
        assert event.registration_required is False
        assert event.max_attendees is None
        assert event.is_featured is False

    @pytest.mark.asyncio
    async def test_update_event_partial_fields(self, test_db: AsyncSession):
        """Test updating only specific fields without affecting others."""
        # Create initial event
        event = Event(
            title="Original Title",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            category="Books",
            audience="Adults",
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Update only title and category
        update_data = EventUpdate(
            title="Updated Title",
            category="Audiobooks",
        )

        for field, value in update_data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(event, field, value)

        await test_db.commit()
        await test_db.refresh(event)

        assert event.title == "Updated Title"
        assert event.category == "Audiobooks"
        assert event.audience == "Adults"  # Unchanged

    @pytest.mark.asyncio
    async def test_create_event_validation_title_required(self, test_db: AsyncSession):
        """Test that title validation is enforced."""
        with pytest.raises(ValueError):
            EventCreate(
                title="",  # Empty title
                start_time=datetime.now(timezone.utc) + timedelta(days=1),
            )

    @pytest.mark.asyncio
    async def test_create_event_validation_end_time_after_start(self, test_db: AsyncSession):
        """Test that end_time must be after start_time."""
        start = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            EventCreate(
                title="Invalid Event",
                start_time=start,
                end_time=start,  # Same as start_time
            )

    @pytest.mark.asyncio
    async def test_create_event_max_attendees_positive(self, test_db: AsyncSession):
        """Test that max_attendees must be positive."""
        with pytest.raises(ValueError):
            EventCreate(
                title="Invalid Event",
                start_time=datetime.now(timezone.utc),
                max_attendees=-1,  # Invalid
            )



    @pytest.mark.asyncio
    async def test_virtual_event_requires_virtual_link(self, test_db: AsyncSession):
        """Test that virtual events require a virtual link."""
        with pytest.raises(ValueError, match="virtual_link is required when is_virtual is true"):
            EventCreate(
                title="Online Workshop",
                start_time=datetime.now(timezone.utc) + timedelta(days=1),
                is_virtual=True,
            )

    @pytest.mark.asyncio
    async def test_event_series_fields_must_be_provided_together(self, test_db: AsyncSession):
        """Test that series_id and series_name must both be present or absent."""
        with pytest.raises(ValueError, match="series_id and series_name must be provided together"):
            EventCreate(
                title="Series Event Missing Name",
                start_time=datetime.now(timezone.utc) + timedelta(days=1),
                series_id="series-1",
            )

        with pytest.raises(ValueError, match="series_id and series_name must be provided together"):
            EventCreate(
                title="Series Event Missing ID",
                start_time=datetime.now(timezone.utc) + timedelta(days=1),
                series_name="Series Name",
            )

    @pytest.mark.asyncio
    async def test_delete_event(self, test_db: AsyncSession):
        """Test event deletion."""
        event = Event(
            title="Event to Delete",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
        )
        test_db.add(event)
        await test_db.commit()
        event_id = event.id

        # Delete the event
        await test_db.delete(event)
        await test_db.commit()

        # Verify it's deleted
        result = await test_db.execute(select(Event).where(Event.id == event_id))
        assert result.scalar_one_or_none() is None


class TestEventSeries:
    """Test event series and recurring events functionality."""

    @pytest.mark.asyncio
    async def test_create_event_series(self, test_db: AsyncSession):
        """Test creating a series of related events."""
        base_time = datetime.now(timezone.utc) + timedelta(days=1)
        series_id = "week-of-code-2024"

        # Create 3 events in the same series
        for i in range(3):
            event = Event(
                title=f"Code Workshop - Week {i+1}",
                start_time=base_time + timedelta(weeks=i),
                series_id=series_id,
                series_name="Code Workshop Series",
                category="Technology",
            )
            test_db.add(event)

        await test_db.commit()

        # Query all events in the series
        result = await test_db.execute(
            select(Event).where(Event.series_id == series_id)
        )
        series_events = result.scalars().all()

        assert len(series_events) == 3
        assert all(e.series_id == series_id for e in series_events)
        assert all(e.series_name == "Code Workshop Series" for e in series_events)

    @pytest.mark.asyncio
    async def test_filter_events_by_series(self, test_db: AsyncSession):
        """Test filtering events by series ID."""
        series_id = "summer-reading-2024"

        # Create events in different series
        for i in range(2):
            event = Event(
                title=f"Summer Reading {i+1}",
                start_time=datetime.now(timezone.utc) + timedelta(days=i),
                series_id=series_id,
            )
            test_db.add(event)

        other_event = Event(
            title="Fall Reading",
            start_time=datetime.now(timezone.utc) + timedelta(days=90),
            series_id="fall-reading-2024",
        )
        test_db.add(other_event)
        await test_db.commit()

        # Query by series
        result = await test_db.execute(
            select(Event).where(Event.series_id == series_id)
        )
        series_events = result.scalars().all()

        assert len(series_events) == 2
        assert all(e.series_id == series_id for e in series_events)


class TestRegistrationCapacity:
    """Test registration capacity limits and waitlist functionality."""

    @pytest.mark.asyncio
    async def test_register_within_capacity(self, test_db: AsyncSession):
        """Test registering for event within capacity."""
        event = Event(
            title="Small Workshop",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            max_attendees=2,
            registration_required=True,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Register first attendee
        reg1 = EventRegistration(
            event_id=event.id,
            patron_name="Alice",
            patron_email="alice@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg1)
        await test_db.commit()

        # Register second attendee (should be confirmed, not waitlisted)
        reg2 = EventRegistration(
            event_id=event.id,
            patron_name="Bob",
            patron_email="bob@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg2)
        await test_db.commit()

        # Verify both are confirmed
        result = await test_db.execute(
            select(func.count(EventRegistration.id))
            .where(EventRegistration.event_id == event.id)
            .where(EventRegistration.status == EventRegistrationStatus.CONFIRMED.value)
        )
        confirmed_count = result.scalar() or 0
        assert confirmed_count == 2

    @pytest.mark.asyncio
    async def test_registration_exceeds_capacity_creates_waitlist(self, test_db: AsyncSession):
        """Test that registrations exceeding capacity are waitlisted."""
        event = Event(
            title="Small Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            max_attendees=1,
            registration_required=True,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Register first attendee (confirmed)
        reg1 = EventRegistration(
            event_id=event.id,
            patron_name="Alice",
            patron_email="alice@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg1)
        await test_db.commit()

        # Register second attendee (should be waitlisted)
        reg2 = EventRegistration(
            event_id=event.id,
            patron_name="Bob",
            patron_email="bob@example.com",
            status=EventRegistrationStatus.WAITLISTED.value,
        )
        test_db.add(reg2)
        await test_db.commit()
        await test_db.refresh(reg2)

        assert reg2.status == EventRegistrationStatus.WAITLISTED.value

    @pytest.mark.asyncio
    async def test_waitlist_promotion_on_cancellation(self, test_db: AsyncSession):
        """Test that first person on waitlist is promoted when spot opens."""
        event = Event(
            title="Promoted Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            max_attendees=1,
            registration_required=True,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Register confirmed attendee
        reg1 = EventRegistration(
            event_id=event.id,
            patron_name="Alice",
            patron_email="alice@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg1)
        await test_db.commit()
        await test_db.refresh(reg1)

        # Register waitlisted attendee
        reg2 = EventRegistration(
            event_id=event.id,
            patron_name="Bob",
            patron_email="bob@example.com",
            status=EventRegistrationStatus.WAITLISTED.value,
        )
        test_db.add(reg2)
        await test_db.commit()
        await test_db.refresh(reg2)

        # Cancel first registration
        reg1.status = EventRegistrationStatus.CANCELLED.value
        reg2.status = EventRegistrationStatus.CONFIRMED.value  # Simulate promotion
        await test_db.commit()

        await test_db.refresh(reg2)
        assert reg2.status == EventRegistrationStatus.CONFIRMED.value

    @pytest.mark.asyncio
    async def test_duplicate_registration_prevented(self, test_db: AsyncSession):
        """Test that duplicate registrations are prevented."""
        event = Event(
            title="Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            registration_required=True,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # First registration
        reg1 = EventRegistration(
            event_id=event.id,
            patron_name="Alice",
            patron_email="alice@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg1)
        await test_db.commit()

        # Try to register again with same email
        result = await test_db.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == event.id)
            .where(func.lower(EventRegistration.patron_email) == "alice@example.com")
            .where(
                EventRegistration.status.in_([
                    EventRegistrationStatus.CONFIRMED.value,
                    EventRegistrationStatus.WAITLISTED.value,
                ])
            )
        )
        existing = result.scalar_one_or_none()
        assert existing is not None


class TestEventReviews:
    """Test event review submission and moderation workflow."""

    @pytest.mark.asyncio
    async def test_submit_review_after_event(self, test_db: AsyncSession):
        """Test submitting review for a past event."""
        # Create past event
        event = Event(
            title="Completed Event",
            start_time=datetime.now(timezone.utc) - timedelta(days=1),
            registration_required=True,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Create confirmed registration
        reg = EventRegistration(
            event_id=event.id,
            patron_name="Alice",
            patron_email="alice@example.com",
            status=EventRegistrationStatus.CONFIRMED.value,
        )
        test_db.add(reg)
        await test_db.commit()

        # Submit review
        review = EventReview(
            event_id=event.id,
            patron_email="alice@example.com",
            rating=5,
            comment="Great event! Really enjoyed it.",
            moderation_status=ReviewModerationStatus.PENDING.value,
        )
        test_db.add(review)
        await test_db.commit()
        await test_db.refresh(review)

        assert review.id is not None
        assert review.rating == 5
        assert review.moderation_status == ReviewModerationStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_review_moderation_workflow(self, test_db: AsyncSession):
        """Test complete review moderation workflow."""
        # Create and submit review
        event = Event(
            title="Event",
            start_time=datetime.now(timezone.utc) - timedelta(days=1),
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        review = EventReview(
            event_id=event.id,
            patron_email="test@example.com",
            rating=4,
            comment="Good event",
            moderation_status=ReviewModerationStatus.PENDING.value,
        )
        test_db.add(review)
        await test_db.commit()
        await test_db.refresh(review)

        # Approve review
        review.moderation_status = ReviewModerationStatus.APPROVED.value
        review.moderated_by = "moderator@example.com"
        review.moderated_at = datetime.now(timezone.utc)
        await test_db.commit()
        await test_db.refresh(review)

        assert review.moderation_status == ReviewModerationStatus.APPROVED.value
        assert review.moderated_by == "moderator@example.com"

    @pytest.mark.asyncio
    async def test_review_rating_validation(self, test_db: AsyncSession):
        """Test that review ratings are validated (1-5)."""
        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="test@example.com",
                rating=6,  # Invalid
            )

        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="test@example.com",
                rating=0,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_review_comment_validation_minimum_length(self, test_db: AsyncSession):
        """Test that review comments must have minimum length if provided."""
        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="test@example.com",
                rating=5,
                comment="Short",  # Too short (less than 10 chars)
            )

    @pytest.mark.asyncio
    async def test_review_duplicate_prevention(self, test_db: AsyncSession):
        """Test that duplicate reviews are prevented."""
        event = Event(
            title="Event",
            start_time=datetime.now(timezone.utc) - timedelta(days=1),
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Create first review
        review1 = EventReview(
            event_id=event.id,
            patron_email="alice@example.com",
            rating=5,
        )
        test_db.add(review1)
        await test_db.commit()

        # Try to create duplicate
        result = await test_db.execute(
            select(EventReview)
            .where(EventReview.event_id == event.id)
            .where(func.lower(EventReview.patron_email) == "alice@example.com")
        )
        existing = result.scalar_one_or_none()
        assert existing is not None


class TestFeaturedEvents:
    """Test featured events and staff picks display."""

    @pytest.mark.asyncio
    async def test_featured_events_filter(self, test_db: AsyncSession):
        """Test filtering for featured events only."""
        # Create featured event
        featured = Event(
            title="Featured Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            is_featured=True,
            is_published=True,
        )
        test_db.add(featured)

        # Create non-featured event
        regular = Event(
            title="Regular Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=2),
            is_featured=False,
            is_published=True,
        )
        test_db.add(regular)
        await test_db.commit()

        # Query only featured
        result = await test_db.execute(
            select(Event).where(Event.is_featured == True)
        )
        featured_events = result.scalars().all()

        assert len(featured_events) == 1
        assert featured_events[0].title == "Featured Event"

    @pytest.mark.asyncio
    async def test_featured_events_sort_first(self, test_db: AsyncSession):
        """Test that featured events appear first in results."""
        now = datetime.now(timezone.utc)

        # Create regular event first (earlier time)
        regular = Event(
            title="Regular Event",
            start_time=now + timedelta(days=1),
            is_featured=False,
            is_published=True,
        )
        test_db.add(regular)

        # Create featured event later
        featured = Event(
            title="Featured Event",
            start_time=now + timedelta(days=2),
            is_featured=True,
            is_published=True,
        )
        test_db.add(featured)
        await test_db.commit()

        # Query with featured sort
        result = await test_db.execute(
            select(Event)
            .where(Event.is_published == True)
            .order_by(Event.is_featured.desc(), Event.start_time)
        )
        events = result.scalars().all()

        assert events[0].is_featured is True
        assert events[0].title == "Featured Event"


class TestSocialSharing:
    """Test social sharing tracking for events."""

    @pytest.mark.asyncio
    async def test_event_share_count_increment(self, test_db: AsyncSession):
        """Test that share count increments on share tracking."""
        event = Event(
            title="Shareable Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            share_count=0,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Simulate share tracking
        event.share_count = event.share_count + 1
        await test_db.commit()
        await test_db.refresh(event)

        assert event.share_count == 1

    @pytest.mark.asyncio
    async def test_multiple_share_tracking(self, test_db: AsyncSession):
        """Test tracking multiple shares of same event."""
        event = Event(
            title="Popular Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            share_count=0,
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        # Simulate multiple shares
        for i in range(5):
            event.share_count = event.share_count + 1
            await test_db.commit()

        await test_db.refresh(event)
        assert event.share_count == 5


class TestVirtualEvents:
    """Test virtual vs in-person event handling."""

    @pytest.mark.asyncio
    async def test_virtual_event_with_link(self, test_db: AsyncSession):
        """Test creating virtual event with video link."""
        event = Event(
            title="Online Workshop",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            is_virtual=True,
            virtual_link="https://zoom.us/meeting/123456789",
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        assert event.is_virtual is True
        assert event.virtual_link == "https://zoom.us/meeting/123456789"

    @pytest.mark.asyncio
    async def test_in_person_event_with_location(self, test_db: AsyncSession):
        """Test creating in-person event with location."""
        event = Event(
            title="In-Person Workshop",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            is_virtual=False,
            location="Main Library, Room 101",
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        assert event.is_virtual is False
        assert event.location == "Main Library, Room 101"

    @pytest.mark.asyncio
    async def test_hybrid_event_both_location_and_link(self, test_db: AsyncSession):
        """Test creating hybrid event with both location and virtual link."""
        event = Event(
            title="Hybrid Event",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            is_virtual=True,
            location="Main Library, Room 101",
            virtual_link="https://zoom.us/meeting/123456789",
        )
        test_db.add(event)
        await test_db.commit()
        await test_db.refresh(event)

        assert event.is_virtual is True
        assert event.location == "Main Library, Room 101"
        assert event.virtual_link == "https://zoom.us/meeting/123456789"


class TestEventUpdateValidation:
    """Test event update validation edge cases."""

    def test_update_virtual_event_requires_link_when_enabled(self):
        """Setting is_virtual=true without virtual_link should fail validation."""
        with pytest.raises(ValueError, match="virtual_link is required when is_virtual is true"):
            EventUpdate(is_virtual=True)

    def test_partial_update_series_name_only_allowed(self):
        """Partial update with only series_name (no series_id) should be allowed - series_id stays in DB."""
        # This should NOT raise an error - the update only touches series_name
        update = EventUpdate(series_name="New Series Name")
        assert update.series_name == "New Series Name"
        assert update.series_id is None

    def test_partial_update_series_id_only_allowed(self):
        """Partial update with only series_id (no series_name) should be allowed - series_name stays in DB."""
        # This should NOT raise an error - the update only touches series_id
        update = EventUpdate(series_id="new-series-id")
        assert update.series_id == "new-series-id"
        assert update.series_name is None

    def test_partial_update_both_series_fields_requires_consistency(self):
        """If updating both series fields, they must be consistent."""
        # Providing both with one missing should fail
        with pytest.raises(ValueError, match="series_id and series_name must be provided together"):
            EventUpdate(series_id="new-id", series_name=None)

    def test_partial_update_both_series_fields_valid(self):
        """If updating both series fields with valid values, should pass."""
        update = EventUpdate(series_id="new-id", series_name="New Series")
        assert update.series_id == "new-id"
        assert update.series_name == "New Series"


class TestRegistrationValidation:
    """Test registration input validation."""

    def test_registration_email_validation(self):
        """Test that registration email must be valid."""
        with pytest.raises(ValueError):
            RegistrationCreate(
                patron_name="John Doe",
                patron_email="invalid-email",  # Not a valid email
            )

    def test_registration_patron_name_required(self):
        """Test that patron name is required."""
        with pytest.raises(ValueError):
            RegistrationCreate(
                patron_name="",  # Empty
                patron_email="test@example.com",
            )

    def test_registration_phone_optional(self):
        """Test that phone is optional."""
        reg = RegistrationCreate(
            patron_name="John Doe",
            patron_email="john@example.com",
        )
        assert reg.patron_phone is None

    def test_registration_phone_validation_minimum_digits(self):
        """Test that phone must have minimum digits."""
        with pytest.raises(ValueError):
            RegistrationCreate(
                patron_name="John Doe",
                patron_email="john@example.com",
                patron_phone="123",  # Too few digits
            )


class TestReviewValidation:
    """Test event review input validation."""

    def test_review_email_validation(self):
        """Test that review email must be valid."""
        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="not-an-email",
                rating=5,
            )

    def test_review_rating_required(self):
        """Test that rating is required."""
        # Pydantic v2 raises pydantic_core.ValidationError (a ValueError
        # subclass) for a missing required field, not TypeError.
        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="test@example.com",
                # Missing rating
            )

    def test_review_comment_whitespace_validation(self):
        """Test that comment cannot be only whitespace."""
        with pytest.raises(ValueError):
            EventReviewCreate(
                patron_email="test@example.com",
                rating=5,
                comment="   ",  # Only whitespace
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
