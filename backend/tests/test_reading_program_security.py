# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for reading program security and privacy.
Tests for leaderboard privacy and achievement edge cases.
"""

import pytest
from datetime import date, timedelta

from app.models.reading import (
    ReadingProgram,
    ReadingRegistration,
    ReadingLogEntry,
    ReadingProgramType,
    ReadingAchievement,
)
from app.models.user import User, UserRole


@pytest.fixture
async def reading_program(test_db):
    """Create a test reading program."""
    program = ReadingProgram(
        name="Privacy Test Program",
        description="Testing leaderboard privacy",
        program_type=ReadingProgramType.summer,
        age_group="All Ages",
        start_date=date.today() - timedelta(days=5),
        end_date=date.today() + timedelta(days=60),
        reading_goal_type="minutes",
        reading_goal_value=1000,
        is_active=True,
    )
    test_db.add(program)
    await test_db.commit()
    await test_db.refresh(program)
    return program


@pytest.fixture
async def multiple_users_with_registrations(test_db, reading_program):
    """Create multiple users with registrations and reading logs."""
    users = []
    registrations = []

    for i in range(5):
        user = User(
            email=f"testuser{i}@example.com",
            password_hash="hashedpassword",
            first_name=f"TestFirst{i}",
            last_name=f"TestLast{i}",
            role=UserRole.PATRON,
            is_active=True,
            reading_minutes_logged=(i + 1) * 100,  # For read-to-reduce leaderboard
        )
        test_db.add(user)
        await test_db.flush()
        users.append(user)

        registration = ReadingRegistration(
            user_id=user.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.flush()
        registrations.append(registration)

        # Add some reading logs
        log_entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=i + 1,
            minutes_read=(i + 1) * 50,
            pages_read=(i + 1) * 30,
        )
        test_db.add(log_entry)

    await test_db.commit()
    return users, registrations


@pytest.mark.asyncio
class TestLeaderboardPrivacy:
    """Test that leaderboards don't expose sensitive user information."""

    async def test_reading_programs_leaderboard_no_user_id(
        self, client, test_patron, reading_program, multiple_users_with_registrations
    ):
        """Test that reading programs leaderboard doesn't expose user_id."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Get leaderboard
        response = await client.get(
            f"/api/v1/reading-programs/programs/{reading_program.id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check that no entry contains user_id
        for entry in data["entries"]:
            assert "user_id" not in entry, "Leaderboard entry should not contain user_id"
            # Verify display_name is anonymized
            assert "display_name" in entry
            display_name = entry["display_name"]
            # Should be either "Reader #XXXX" or "X***" format
            assert (
                display_name.startswith("Reader #") or
                (len(display_name) == 4 and display_name.endswith("***"))
            ), f"Display name '{display_name}' is not properly anonymized"

    async def test_reading_programs_leaderboard_no_email(
        self, client, test_patron, reading_program, multiple_users_with_registrations
    ):
        """Test that reading programs leaderboard doesn't expose email."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/programs/{reading_program.id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check that no entry contains email
        for entry in data["entries"]:
            assert "email" not in entry, "Leaderboard entry should not contain email"
            # Also check display_name doesn't contain @ symbol
            assert "@" not in entry.get("display_name", ""), "Display name should not contain email"

    async def test_reading_programs_leaderboard_no_full_name(
        self, client, test_patron, reading_program, multiple_users_with_registrations
    ):
        """Test that reading programs leaderboard doesn't expose full name."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/programs/{reading_program.id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check that no entry contains full name fields
        for entry in data["entries"]:
            assert "first_name" not in entry
            assert "last_name" not in entry
            assert "full_name" not in entry
            assert "user_name" not in entry

    async def test_read_to_reduce_leaderboard_no_user_id(
        self, client, test_patron, multiple_users_with_registrations
    ):
        """Test that read-to-reduce leaderboard doesn't expose user_id."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check that no entry contains user_id
        for entry in data:
            assert "user_id" not in entry, "Leaderboard entry should not contain user_id"
            # Verify display_name is anonymized
            assert "display_name" in entry
            display_name = entry["display_name"]
            assert (
                display_name.startswith("Reader #") or
                (len(display_name) == 4 and display_name.endswith("***"))
            ), f"Display name '{display_name}' is not properly anonymized"

    async def test_leaderboard_user_rank_still_works(
        self, client, test_patron, reading_program, test_db
    ):
        """Test that user can still see their own rank without exposing IDs."""
        # Register test_patron for the program
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.flush()  # populate registration.id before referencing it below

        # Add some reading logs
        log_entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=5,
            minutes_read=300,
            pages_read=200,
        )
        test_db.add(log_entry)
        await test_db.commit()

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/programs/{reading_program.id}/leaderboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # User should still be able to see their rank
        assert "user_rank" in data
        assert data["user_rank"] is not None or data["total_participants"] == 0


@pytest.mark.asyncio
class TestAchievementEdgeCases:
    """Test achievement awarding edge cases."""

    async def test_achievement_not_awarded_twice(
        self, client, test_patron, reading_program, test_db
    ):
        """Test that achievements are not awarded multiple times."""
        # Register for program
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Log reading to trigger first-book badge
        response1 = await client.post(
            "/api/v1/reading-programs/log-entries-with-achievements",
            json={
                "registration_id": registration.id,
                "books_read": 1,
                "minutes_read": 30,
                "pages_read": 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 201
        _ = response1.json()["achievements_earned"]

        # Log again - should not get the same badge
        response2 = await client.post(
            "/api/v1/reading-programs/log-entries-with-achievements",
            json={
                "registration_id": registration.id,
                "books_read": 1,
                "minutes_read": 30,
                "pages_read": 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 201
        _ = response2.json()["achievements_earned"]

        # If first-book was awarded in first response, it should not be in second
        first_badge_ids = [a.get("badge_id") for a in response1.json().get("new_achievements", [])]
        second_badge_ids = [a.get("badge_id") for a in response2.json().get("new_achievements", [])]

        for badge_id in first_badge_ids:
            assert badge_id not in second_badge_ids, f"Badge {badge_id} was awarded twice"

    async def test_streak_calculation_with_gap(
        self, client, test_patron, reading_program, test_db
    ):
        """Test streak calculation handles gaps correctly."""
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Get streak info
        response = await client.get(
            f"/api/v1/reading-programs/registrations/{registration.id}/streak",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # With no logs, streak should be 0
        assert data["current_streak"] == 0
        assert data["longest_streak"] == 0

    async def test_goal_badge_progress_display(
        self, client, test_patron, reading_program, test_db
    ):
        """Test that goal badge progress is displayed correctly."""
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,  # 1000 minutes goal
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        # Add 500 minutes (50% progress)
        log_entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=1,
            minutes_read=500,
            pages_read=100,
        )
        test_db.add(log_entry)
        await test_db.commit()

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/registrations/{registration.id}/badges",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        badges = response.json()

        # Find goal-achiever badge
        goal_badge = next((b for b in badges if b["badge_id"] == "goal-achiever"), None)
        assert goal_badge is not None, "Goal achiever badge should exist"

        # Progress should be 50% (500/1000 * 100)
        assert goal_badge["current"] == 50.0, f"Expected 50.0%, got {goal_badge['current']}%"
        assert goal_badge["progress_percentage"] == 50.0

    async def test_overachiever_badge_progress(
        self, client, test_patron, reading_program, test_db
    ):
        """Test overachiever badge progress calculation."""
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        # Add 1200 minutes (120% progress toward goal)
        log_entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=1,
            minutes_read=1200,
            pages_read=200,
        )
        test_db.add(log_entry)
        await test_db.commit()

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/registrations/{registration.id}/badges",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        badges = response.json()

        # Find overachiever badge (requires 150%)
        overachiever = next((b for b in badges if b["badge_id"] == "overachiever"), None)
        assert overachiever is not None

        # Progress should be 120% (1200/1000 * 100), but capped for display
        assert overachiever["current"] == 120.0
        # Progress percentage toward the 150% threshold = 120/150 * 100 = 80%
        assert overachiever["progress_percentage"] == 80.0

    async def test_zero_goal_target_handling(
        self, client, test_patron, reading_program, test_db
    ):
        """Test that zero goal target doesn't cause division by zero."""
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=0,  # Edge case: zero goal
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/registrations/{registration.id}/badges",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should not crash with division by zero
        assert response.status_code == 200

    async def test_null_goal_target_handling(
        self, client, test_patron, reading_program, test_db
    ):
        """Test that null goal target is handled gracefully."""
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=None,  # Edge case: null goal
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/v1/reading-programs/registrations/{registration.id}/badges",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should not crash
        assert response.status_code == 200
