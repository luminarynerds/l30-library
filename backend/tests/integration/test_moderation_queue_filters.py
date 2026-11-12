# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for moderation queue filtering functionality.

Tests filtering by:
- Content type (review_type)
- Flag severity (min_score, max_score, flag_type)
- Date range (date_from, date_to)
- Assigned moderator (resolved_by)
- Combined filters
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.models.content_flag import ContentFlag, FlagType, FlagStatus
from app.core.security import create_access_token, hash_password


def _error_detail(response):
    """HTTPException responses are wrapped by the global handler as
    {"error": {"message": ...}}, not FastAPI's default {"detail": ...}."""
    body = response.json()
    if "error" in body and isinstance(body["error"], dict):
        return body["error"].get("message", "")
    return body.get("detail", "")


# =============================================================================
# Fixtures
# =============================================================================
#
# db_session comes from tests/conftest.py's shared alias to the test_db
# fixture (real DELETE-all cleanup between tests). This file used to define
# its own db_session that only rolled back a session that had already
# .commit()'d (fixtures below call db_session.commit() directly), so
# committed rows like moderator@l30.org never got cleaned up and the second
# test in any run collided on ix_users_email_hash. Riding the shared
# fixture sidesteps that entirely, matching the pattern already applied in
# test_shift_swap_service.py.


@pytest.fixture
async def async_client(client):
    """Alias conftest's client fixture (already wired to db_session/test_db)."""
    yield client


@pytest.fixture
async def staff_user(db_session: AsyncSession) -> User:
    """Create a staff user for testing."""
    user = User(
        email="moderator@l30.org",
        password_hash=hash_password("TestPassword123!"),
        first_name="Staff",
        last_name="Moderator",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def second_staff_user(db_session: AsyncSession) -> User:
    """Create a second staff user for moderator filter testing."""
    user = User(
        email="moderator2@l30.org",
        password_hash=hash_password("TestPassword123!"),
        first_name="Second",
        last_name="Moderator",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def staff_user_token(staff_user: User) -> str:
    """Create an access token for the staff user."""
    return create_access_token(staff_user.id, email=staff_user.email)


@pytest.fixture
def second_staff_token(second_staff_user: User) -> str:
    """Create an access token for the second staff user."""
    return create_access_token(second_staff_user.id, email=second_staff_user.email)


@pytest.fixture
async def patron_user(db_session: AsyncSession) -> User:
    """Create a patron user for testing."""
    user = User(
        email="patron@l30.org",
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def patron_user_token(patron_user: User) -> str:
    """Create an access token for the patron user."""
    return create_access_token(patron_user.id, email=patron_user.email)


@pytest.fixture
async def sample_content_flags(
    db_session: AsyncSession, staff_user: User, second_staff_user: User
) -> list[ContentFlag]:
    """Create a diverse set of content flags for testing filters."""
    now = datetime.now(timezone.utc)

    flags = [
        # Event review spam - high severity, resolved by first moderator
        ContentFlag(
            review_id=1,
            review_type="event_review",
            flag_type=FlagType.SPAM,
            confidence_score=95,
            status=FlagStatus.RESOLVED,
            resolved_by=staff_user.email,
            resolved_at=now - timedelta(days=1),
            is_correct_flag=True,
            created_at=now - timedelta(days=5),
        ),
        # Event review hate speech - medium severity, pending
        ContentFlag(
            review_id=2,
            review_type="event_review",
            flag_type=FlagType.HATE_SPEECH,
            confidence_score=80,
            status=FlagStatus.PENDING,
            created_at=now - timedelta(days=3),
        ),
        # Indie review spam - high severity, resolved by second moderator
        ContentFlag(
            review_id=3,
            review_type="indie_review",
            flag_type=FlagType.SPAM,
            confidence_score=90,
            status=FlagStatus.FALSE_POSITIVE,
            resolved_by=second_staff_user.email,
            resolved_at=now - timedelta(days=2),
            is_correct_flag=False,
            created_at=now - timedelta(days=10),
        ),
        # Indie review excessive caps - low severity, pending
        ContentFlag(
            review_id=4,
            review_type="indie_review",
            flag_type=FlagType.EXCESSIVE_CAPS,
            confidence_score=72,
            status=FlagStatus.PENDING,
            created_at=now - timedelta(days=1),
        ),
        # Event review off-topic - borderline severity, pending
        ContentFlag(
            review_id=6,
            review_type="event_review",
            flag_type=FlagType.OFF_TOPIC,
            confidence_score=71,
            status=FlagStatus.PENDING,
            created_at=now - timedelta(hours=6),
        ),
        # Indie review duplicate - very high severity, false negative
        ContentFlag(
            review_id=7,
            review_type="indie_review",
            flag_type=FlagType.DUPLICATE,
            confidence_score=98,
            status=FlagStatus.FALSE_NEGATIVE,
            resolved_by=second_staff_user.email,
            resolved_at=now - timedelta(hours=1),
            is_correct_flag=False,
            created_at=now - timedelta(days=15),
        ),
        # Old event review - created long ago
        ContentFlag(
            review_id=8,
            review_type="event_review",
            flag_type=FlagType.SPAM,
            confidence_score=88,
            status=FlagStatus.PENDING,
            created_at=now - timedelta(days=30),
        ),
    ]

    for flag in flags:
        db_session.add(flag)

    await db_session.commit()

    for flag in flags:
        await db_session.refresh(flag)

    return flags


# =============================================================================
# Test Content Type Filtering
# =============================================================================


@pytest.mark.asyncio
class TestContentTypeFiltering:
    """Test filtering moderation queue by content type (review_type)."""

    async def test_filter_by_event_review_type(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags by event_review content type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=event_review&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4  # 4 event reviews in sample data
        for item in data["items"]:
            assert item["review_type"] == "event_review"

    async def test_filter_by_indie_review_type(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags by indie_review content type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=indie_review&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # 3 indie reviews in sample data
        for item in data["items"]:
            assert item["review_type"] == "indie_review"

    async def test_filter_by_nonexistent_type_returns_empty(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering by non-existent review type returns empty results."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=nonexistent_type&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# =============================================================================
# Test Flag Severity Filtering
# =============================================================================


@pytest.mark.asyncio
class TestFlagSeverityFiltering:
    """Test filtering moderation queue by flag severity (confidence score)."""

    async def test_filter_by_high_severity(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags with high severity (score >= 90)."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?min_score=90", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should include flags with scores 95, 90, 98
        assert data["total"] == 3
        for item in data["items"]:
            assert item["confidence_score"] >= 90

    async def test_filter_by_medium_severity(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags with medium severity (score between 75-89)."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?min_score=75&max_score=89", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # sample_content_flags has 2 flags in [75, 89]: scores 80, 88
        # (there is no score=85 flag in the fixture).
        assert data["total"] == 2
        for item in data["items"]:
            assert 75 <= item["confidence_score"] <= 89

    async def test_filter_by_low_severity(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags with low severity (score <= 75)."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?min_score=0&max_score=75", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should include flags with scores 72, 71
        assert data["total"] == 2
        for item in data["items"]:
            assert item["confidence_score"] <= 75

    async def test_filter_by_flag_type_spam(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags by SPAM flag type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?flag_type=spam&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should include 3 SPAM flags
        assert data["total"] == 3
        for item in data["items"]:
            assert item["flag_type"] == "spam"

    async def test_filter_by_flag_type_hate_speech(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags by HATE_SPEECH flag type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?flag_type=hate_speech&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["flag_type"] == "hate_speech"

    async def test_invalid_flag_type_returns_400(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test that invalid flag type returns 400 error."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?flag_type=INVALID_TYPE&min_score=0", headers=headers
        )

        assert response.status_code == 400
        assert "Invalid flag_type" in _error_detail(response)

    async def test_default_min_score_filters_low_confidence(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test that default min_score=70 filters out very low confidence flags."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        # With default min_score of 70, all our sample flags should be included
        response = await async_client.get("/api/v1/admin/content-flags/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        # sample_content_flags has 7 flags, all scores >= 71
        assert data["total"] == 7
        for item in data["items"]:
            assert item["confidence_score"] >= 70


# =============================================================================
# Test Date Range Filtering
# =============================================================================


@pytest.mark.asyncio
class TestDateRangeFiltering:
    """Test filtering moderation queue by date range.

    Datetime params MUST be passed via `params=`, never interpolated into the
    query string: isoformat() emits a "+00:00" offset, and a raw "+" in a query
    string decodes to a space server-side, so the value arrives as an invalid
    datetime and FastAPI 422s before the endpoint is ever reached.

    Cutoffs are also kept strictly between two fixture ages. The fixture's
    `now` is captured before the test's, so a flag created at exactly N days
    falls a few microseconds *outside* an N-day cutoff.
    """

    async def test_filter_by_date_from(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags created after a specific date."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_from = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={"date_from": date_from, "min_score": 0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Keeps the 5-day, 3-day, 1-day and 6-hour flags; drops 10/15/30-day
        assert data["total"] == 4

    async def test_filter_by_date_to(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags created before a specific date."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_to = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={"date_to": date_to, "min_score": 0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should include flags older than 4 days (5-day, 10-day, 15-day, 30-day)
        assert data["total"] == 4

    async def test_filter_by_date_range(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags within a specific date range."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_from = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        date_to = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={"date_from": date_from, "date_to": date_to, "min_score": 0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Flags aged between 2 and 7 days: the 5-day and 3-day ones
        assert data["total"] == 2

    async def test_filter_recent_flags_last_24_hours(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering flags from the last day."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        # 25h, not 24h: the 1-day-old flag sits exactly on a 24h cutoff
        date_from = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={"date_from": date_from, "min_score": 0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should include only very recent flags (1 day old and 6 hours old)
        assert data["total"] == 2

    async def test_filter_old_flags(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering old flags (more than 14 days ago)."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_to = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={"date_to": date_to, "min_score": 0},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should include 15-day and 30-day old flags
        assert data["total"] == 2


# =============================================================================
# Test Assigned Moderator Filtering
# =============================================================================


@pytest.mark.asyncio
class TestAssignedModeratorFiltering:
    """Test filtering moderation queue by assigned moderator (resolved_by)."""

    async def test_filter_by_first_moderator(
        self,
        async_client: AsyncClient,
        staff_user_token: str,
        staff_user: User,
        sample_content_flags,
    ):
        """Test filtering flags resolved by the first moderator."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            f"/api/v1/admin/content-flags/?resolved_by={staff_user.email}&min_score=0",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # First moderator resolved exactly one flag in the fixture (the 5-day spam flag)
        assert data["total"] == 1

    async def test_filter_by_second_moderator(
        self,
        async_client: AsyncClient,
        staff_user_token: str,
        second_staff_user: User,
        sample_content_flags,
    ):
        """Test filtering flags resolved by the second moderator."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            f"/api/v1/admin/content-flags/?resolved_by={second_staff_user.email}&min_score=0",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Second moderator resolved 2 flags
        assert data["total"] == 2

    async def test_filter_by_nonexistent_moderator_returns_empty(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test filtering by non-existent moderator returns empty results."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?resolved_by=nonexistent@l30.org&min_score=0",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_filter_unassigned_flags(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test that pending flags without a moderator can be found with status filter."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?status=pending&min_score=0", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # 4 pending flags in sample data
        assert data["total"] == 4
        for item in data["items"]:
            assert item["status"] == "pending"


# =============================================================================
# Test Combined Filters
# =============================================================================


@pytest.mark.asyncio
class TestCombinedFilters:
    """Test combining multiple filters together."""

    async def test_combine_content_type_and_severity(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test combining content type and severity filters."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=event_review&min_score=80", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # Event reviews with score >= 80: 95, 80, 88
        assert data["total"] == 3
        for item in data["items"]:
            assert item["review_type"] == "event_review"
            assert item["confidence_score"] >= 80

    async def test_combine_content_type_and_status(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test combining content type and status filters."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=indie_review&status=pending&min_score=0",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Pending indie reviews: only the excessive caps one
        assert data["total"] == 1
        assert data["items"][0]["review_type"] == "indie_review"
        assert data["items"][0]["status"] == "pending"

    async def test_combine_date_range_and_moderator(
        self,
        async_client: AsyncClient,
        staff_user_token: str,
        staff_user: User,
        sample_content_flags,
    ):
        """Test combining date range and moderator filters."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_from = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={
                "date_from": date_from,
                "resolved_by": staff_user.email,
                "min_score": 0,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # The first moderator's only resolved flag (5 days old) is inside the 7-day window
        assert data["total"] == 1

    async def test_combine_all_filters(
        self,
        async_client: AsyncClient,
        staff_user_token: str,
        staff_user: User,
        sample_content_flags,
    ):
        """Test combining all filter types."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}
        date_from = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

        response = await async_client.get(
            "/api/v1/admin/content-flags/",
            params={
                "review_type": "event_review",
                "status": "resolved",
                "min_score": 90,
                "date_from": date_from,
                "resolved_by": staff_user.email,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Only flag 1 matches all criteria: event_review, resolved, score 95,
        # within last 10 days, resolved by first moderator
        assert data["total"] == 1

    async def test_combine_severity_range_with_flag_type(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test combining severity score range with flag type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?flag_type=spam&min_score=85&max_score=95", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        # SPAM flags with score 85-95: scores 95, 90, 88
        assert data["total"] == 3
        for item in data["items"]:
            assert item["flag_type"] == "spam"
            assert 85 <= item["confidence_score"] <= 95


# =============================================================================
# Test Authorization and Edge Cases
# =============================================================================


@pytest.mark.asyncio
class TestAuthorizationAndEdgeCases:
    """Test authorization requirements and edge cases."""

    async def test_filtering_requires_authentication(
        self, async_client: AsyncClient, sample_content_flags
    ):
        """Test that filtering requires authentication."""
        response = await async_client.get("/api/v1/admin/content-flags/?review_type=event_review")

        assert response.status_code == 401

    async def test_filtering_requires_staff_role(
        self, async_client: AsyncClient, patron_user_token: str, sample_content_flags
    ):
        """Test that filtering requires staff role."""
        headers = {"Authorization": f"Bearer {patron_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/?review_type=event_review", headers=headers
        )

        assert response.status_code == 403

    async def test_empty_results_with_restrictive_filters(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test that very restrictive filters return empty results gracefully."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await async_client.get(
            "/api/v1/admin/content-flags/"
            "?review_type=event_review"
            "&status=false_negative"
            "&min_score=99",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_pagination_with_filters(
        self, async_client: AsyncClient, staff_user_token: str, sample_content_flags
    ):
        """Test pagination works correctly with filters."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        # Get first page with 2 items per page
        response = await async_client.get(
            "/api/v1/admin/content-flags/?min_score=0&page=1&per_page=2", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) == 2
        assert data["total"] == 7
        assert data["total_pages"] == 4

        # Get second page
        response = await async_client.get(
            "/api/v1/admin/content-flags/?min_score=0&page=2&per_page=2", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
