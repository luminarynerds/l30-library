# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Signage Service Layer

Tests core signage functionality:
- Display management
- Content creation and approval
- Scheduling
- Emergency messages
- Analytics
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    SignageDisplay,
    SignageContent,
    SignageTemplate,
    SignageSchedule,
    SignageEmergencyMessage,
)
from app.services.signage_service import (
    SignageService,
    SignageContentService,
    SignageTemplateService,
    SignageScheduleService,
    SignageEmergencyService,
    SignageAnalyticsService,
)


# Test Fixtures
@pytest.fixture
async def db(test_db):
    """Use the standard Postgres test database.

    This file used to spin up its own in-memory sqlite engine with a curated
    table subset to dodge Postgres-only column types elsewhere in the schema.
    That workaround broke once `users` itself gained a JSONB column
    (last_name_prefix_hash) -- sqlite can't render JSONB even for a table
    this file only needs for FKs. Riding the shared postgres test_db fixture
    sidesteps dialect-compatibility entirely.
    """
    return test_db


class TestSignageService:
    """Test display management functionality."""

    @pytest.mark.asyncio
    async def test_create_display(self, db: AsyncSession):
        """Test creating a new display."""
        service = SignageService(db)

        display = await service.create_display(
            name="Test Display",
            location_description="Test Location",
            display_type="wall_mounted",
        )

        assert display.id is not None
        assert display.name == "Test Display"
        assert display.status == "active"

    @pytest.mark.asyncio
    async def test_list_displays(self, db: AsyncSession):
        """Test listing displays with filtering."""
        service = SignageService(db)

        # Create test displays
        for i in range(5):
            await service.create_display(
                name=f"Display {i}",
                location_description=f"Location {i}",
                display_type="wall_mounted" if i % 2 == 0 else "kiosk",
            )

        # List all
        displays, total = await service.list_displays()
        assert total == 5
        assert len(displays) == 5

        # Filter by type
        displays, total = await service.list_displays(display_type="kiosk")
        assert total == 2

    @pytest.mark.asyncio
    async def test_update_display_status(self, db: AsyncSession):
        """Test updating display status."""
        service = SignageService(db)

        display = await service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        updated = await service.update_display_status(display.id, "offline")

        assert updated.status == "offline"
        assert updated.is_online == False

    @pytest.mark.asyncio
    async def test_record_heartbeat(self, db: AsyncSession):
        """Test recording display heartbeat."""
        service = SignageService(db)

        display = await service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        # Record heartbeat
        updated = await service.record_heartbeat(display.id)

        assert updated.is_online == True
        assert updated.last_heartbeat is not None


class TestSignageContentService:
    """Test content management and approval workflow."""

    @pytest.mark.asyncio
    async def test_create_content(self, db: AsyncSession):
        """Test creating content."""
        service = SignageContentService(db)

        content = await service.create_content(
            title="Test Content",
            content_type="announcement",
            html_content="<h1>Test</h1>",
        )

        assert content.id is not None
        assert content.title == "Test Content"
        assert content.approval_status == "draft"

    @pytest.mark.asyncio
    async def test_approval_workflow(self, db: AsyncSession, test_staff):
        """Test content approval workflow."""
        service = SignageContentService(db)

        content = await service.create_content(
            title="Test Content",
            content_type="announcement",
            html_content="<h1>Test</h1>",
        )

        # Submit for approval
        submitted = await service.submit_for_approval(content.id)
        assert submitted.approval_status == "pending_review"

        # Approve
        approved = await service.approve_content(content.id, reviewer_id=test_staff.id)
        assert approved.approval_status == "approved"
        assert approved.reviewed_by_user_id == test_staff.id

    @pytest.mark.asyncio
    async def test_reject_content(self, db: AsyncSession, test_staff):
        """Test rejecting content with reason."""
        service = SignageContentService(db)

        content = await service.create_content(
            title="Test Content",
            content_type="announcement",
        )

        await service.submit_for_approval(content.id)

        rejected = await service.reject_content(
            content.id, reviewer_id=test_staff.id, reason="Spelling errors"
        )

        assert rejected.approval_status == "rejected"
        assert rejected.rejection_reason == "Spelling errors"

    @pytest.mark.asyncio
    async def test_cannot_delete_scheduled_content(self, db: AsyncSession, test_staff):
        """Test that scheduled content cannot be deleted."""
        content_service = SignageContentService(db)
        display_service = SignageService(db)
        schedule_service = SignageScheduleService(db)

        # Create content and display
        content = await content_service.create_content(title="Test", content_type="announcement")
        display = await display_service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        # Approve and schedule
        await content_service.approve_content(content.id, reviewer_id=test_staff.id)
        await schedule_service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now(),
        )

        # Try to delete - should fail
        deleted = await content_service.delete_content(content.id)
        assert deleted == False


class TestSignageScheduleService:
    """Test scheduling functionality."""

    @pytest.mark.asyncio
    async def test_schedule_content(self, db: AsyncSession):
        """Test scheduling content on display."""
        service = SignageScheduleService(db)
        content_service = SignageContentService(db)
        display_service = SignageService(db)

        # Create prerequisites
        content = await content_service.create_content(title="Test", content_type="announcement")
        display = await display_service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        # Schedule
        schedule = await service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now(),
            schedule_type="one_time",
        )

        assert schedule.id is not None
        assert schedule.display_id == display.id
        assert schedule.is_active == True

    @pytest.mark.asyncio
    async def test_get_active_content(self, db: AsyncSession, test_staff):
        """Test getting currently active content for display."""
        service = SignageScheduleService(db)
        content_service = SignageContentService(db)
        display_service = SignageService(db)

        # Create and schedule content
        content = await content_service.create_content(title="Test", content_type="announcement")
        display = await display_service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        # Approve before scheduling: resolver only returns approved content.
        await content_service.approve_content(content.id, reviewer_id=test_staff.id)

        await service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now() - timedelta(minutes=5),
        )

        # Get active content
        active = await service.get_active_content_for_display(display.id)

        assert active is not None
        assert active.id == content.id

    @pytest.mark.asyncio
    async def test_emergency_overrides_scheduled_content(self, db: AsyncSession, test_staff):
        """An active emergency message wins over any scheduled content."""
        schedule_service = SignageScheduleService(db)
        content_service = SignageContentService(db)
        display_service = SignageService(db)
        emergency_service = SignageEmergencyService(db)

        display = await display_service.create_display(
            name="Lobby", location_description="Lobby", display_type="wall_mounted"
        )
        content = await content_service.create_content(
            title="Regular Hours", content_type="hours", html_content="<p>9-5</p>"
        )
        await content_service.approve_content(content.id, reviewer_id=test_staff.id)
        await schedule_service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now() - timedelta(minutes=5),
        )

        await emergency_service.create_emergency_message(
            message_title="CLOSING EARLY",
            message_content="Severe weather. Closing at 2pm.",
            display_id=display.id,
        )

        active = await schedule_service.get_active_content_for_display(display.id)

        assert active is not None
        assert active.title == "CLOSING EARLY"
        assert active.html_content == "Severe weather. Closing at 2pm."

    @pytest.mark.asyncio
    async def test_unapproved_scheduled_content_is_skipped(self, db: AsyncSession):
        """Scheduled content that is not approved must not be served."""
        schedule_service = SignageScheduleService(db)
        content_service = SignageContentService(db)
        display_service = SignageService(db)

        display = await display_service.create_display(
            name="Kiosk", location_description="Kiosk", display_type="kiosk"
        )
        content = await content_service.create_content(
            title="Draft Content",
            content_type="announcement",
            html_content="<p>not ready</p>",
        )
        # Leave in draft (default) -- do NOT approve.
        await schedule_service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now() - timedelta(minutes=5),
        )

        active = await schedule_service.get_active_content_for_display(display.id)

        assert active is None

    @pytest.mark.asyncio
    async def test_deactivate_expired_schedules(self, db: AsyncSession):
        """Test automatic deactivation of expired schedules."""
        service = SignageScheduleService(db)
        content_service = SignageContentService(db)
        display_service = SignageService(db)

        # Create expired schedule
        content = await content_service.create_content(title="Test", content_type="announcement")
        display = await display_service.create_display(
            name="Test Display",
            location_description="Location",
            display_type="wall_mounted",
        )

        await service.schedule_content(
            display_id=display.id,
            content_id=content.id,
            start_datetime=datetime.now() - timedelta(days=1),
            end_datetime=datetime.now() - timedelta(hours=1),
        )

        # Deactivate expired
        count = await service.deactivate_expired_schedules()

        assert count == 1


class TestSignageEmergencyService:
    """Test emergency message functionality."""

    @pytest.mark.asyncio
    async def test_create_emergency_message(self, db: AsyncSession):
        """Test creating emergency message."""
        service = SignageEmergencyService(db)

        message = await service.create_emergency_message(
            message_title="CLOSURE",
            message_content="Library is closed",
            applies_to_all=True,
        )

        assert message.id is not None
        assert message.is_active == True
        assert message.applies_to_all_displays == True

    @pytest.mark.asyncio
    async def test_get_active_emergency_messages(self, db: AsyncSession):
        """Test retrieving active emergency messages."""
        service = SignageEmergencyService(db)

        # Create messages
        await service.create_emergency_message(
            message_title="CLOSURE",
            message_content="Library is closed",
            applies_to_all=True,
        )

        # Get active messages
        messages = await service.get_active_emergency_messages()

        assert len(messages) == 1
        assert messages[0].message_title == "CLOSURE"

    @pytest.mark.asyncio
    async def test_deactivate_emergency(self, db: AsyncSession):
        """Test deactivating emergency message."""
        service = SignageEmergencyService(db)

        message = await service.create_emergency_message(
            message_title="CLOSURE", message_content="Library is closed", applies_to_all=True
        )

        deactivated = await service.deactivate_emergency_message(message.id)

        assert deactivated.is_active == False
        assert deactivated.deactivated_at is not None


class TestSignageAnalyticsService:
    """Test analytics tracking and reporting."""

    @pytest.mark.asyncio
    async def test_record_event(self, db: AsyncSession):
        """Test recording analytics event."""
        service = SignageAnalyticsService(db)
        display_service = SignageService(db)
        content_service = SignageContentService(db)

        display = await display_service.create_display(
            name="Analytics Display", location_description="Lobby", display_type="wall_mounted"
        )
        content = await content_service.create_content(
            title="Analytics Content", content_type="announcement"
        )

        event = await service.record_event(
            display_id=display.id, content_id=content.id, event_type="view_start"
        )

        assert event.id is not None
        assert event.event_type == "view_start"

    @pytest.mark.asyncio
    async def test_get_display_analytics(self, db: AsyncSession):
        """Test getting display analytics summary."""
        service = SignageAnalyticsService(db)
        display_service = SignageService(db)
        content_service = SignageContentService(db)

        display = await display_service.create_display(
            name="Analytics Display", location_description="Lobby", display_type="wall_mounted"
        )
        content = await content_service.create_content(
            title="Analytics Content", content_type="announcement"
        )

        # One complete view (start + end), plus one interaction.
        await service.record_event(
            display_id=display.id, content_id=content.id, event_type="view_start"
        )
        await service.record_event(
            display_id=display.id, content_id=content.id, event_type="view_end"
        )
        await service.record_event(
            display_id=display.id, content_id=content.id, event_type="interaction"
        )

        analytics = await service.get_display_analytics(display_id=display.id)

        assert analytics["display_id"] == display.id
        # view_end closes the view view_start opened -- one view, not two.
        assert analytics["total_views"] == 1
        assert analytics["total_interactions"] == 1


# Performance Tests
class TestSignagePerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_bulk_display_creation(self, db: AsyncSession):
        """Test creating many displays efficiently."""
        service = SignageService(db)

        # Create 100 displays
        for i in range(100):
            await service.create_display(
                name=f"Display {i}",
                location_description=f"Location {i}",
                display_type="wall_mounted",
            )

        displays, total = await service.list_displays(limit=100)

        assert total == 100
        assert len(displays) == 100

    @pytest.mark.asyncio
    async def test_content_filtering_performance(self, db: AsyncSession):
        """Test filtering content performance."""
        service = SignageContentService(db)

        # Create 50 content items
        for i in range(50):
            await service.create_content(
                title=f"Content {i}",
                content_type="announcement" if i % 2 == 0 else "promotion",
            )

        # Filter by type
        content, total = await service.list_content(content_type="announcement", limit=100)

        assert total == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
