# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for simplified reading programs endpoints (Upgrade 4).
Tests for: join, my-programs, progress, and log-reading endpoints.
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import select

from app.models.reading import ReadingProgram, ReadingRegistration, ReadingLogEntry, ReadingProgramType
from app.models.user import User, UserRole


@pytest.fixture
async def reading_program(test_db):
    """Create a test reading program."""
    program = ReadingProgram(
        name="Summer Reading Challenge 2024",
        description="Join us for summer reading fun!",
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
async def reading_program_inactive(test_db):
    """Create an inactive reading program."""
    program = ReadingProgram(
        name="Inactive Reading Program",
        description="This program is inactive",
        program_type=ReadingProgramType.year_round,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() - timedelta(days=30),
        reading_goal_type="books",
        reading_goal_value=5,
        is_active=False,
    )
    test_db.add(program)
    await test_db.commit()
    await test_db.refresh(program)
    return program


@pytest.mark.asyncio
class TestJoinReadingProgram:
    """Test POST /reading-programs/join endpoint."""

    async def test_join_program_success(self, client, test_patron, reading_program):
        """Test successfully joining a reading program."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Join program
        response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": reading_program.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_patron.id
        assert data["program_id"] == reading_program.id
        assert data["total_minutes"] == 0
        assert data["total_books"] == 0
        assert data["progress_percentage"] == 0.0
        assert data["goal_target"] == 1000  # From program's reading_goal_value

    async def test_join_program_already_joined(self, client, test_patron, reading_program, test_db):
        """Test joining a program user is already registered in."""
        # First join
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Try to join again
        response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": reading_program.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "Already registered" in response.json()["error"]["message"]

    async def test_join_nonexistent_program(self, client, test_patron):
        """Test joining a program that doesn't exist."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": 99999},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()

    async def test_join_inactive_program(self, client, test_patron, reading_program_inactive):
        """Test attempting to join an inactive program."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": reading_program_inactive.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "not active" in response.json()["error"]["message"].lower()

    async def test_join_requires_authentication(self, client, reading_program):
        """Test that join endpoint requires authentication."""
        response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": reading_program.id},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetMyPrograms:
    """Test GET /reading-programs/my-programs endpoint."""

    async def test_get_my_programs_empty(self, client, test_patron):
        """Test getting programs when user has none."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/my-programs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_my_programs_with_registrations(self, client, test_patron, reading_program, test_db):
        """Test getting programs user is registered in."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/my-programs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["program_name"] == "Summer Reading Challenge 2024"
        assert data[0]["program_id"] == reading_program.id
        assert data[0]["registration_id"] == registration.id
        assert data[0]["total_minutes"] == 0
        assert data[0]["goal_target"] == 1000
        assert data[0]["progress_percentage"] == 0.0

    async def test_get_my_programs_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = await client.get("/api/v1/reading-programs/my-programs")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetProgress:
    """Test GET /reading-programs/progress endpoint."""

    async def test_get_progress_empty(self, client, test_patron):
        """Test getting progress when user has no programs."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/progress",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_progress_with_logs(self, client, test_patron, reading_program, test_db):
        """Test getting progress with reading logs."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        # Create log entries
        log_entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=1,
            minutes_read=150,
            pages_read=45,
            title="Test Book",
            notes="Great book",
        )
        test_db.add(log_entry)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/progress",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["total_minutes"] == 150
        assert data[0]["total_books"] == 1
        assert data[0]["total_pages"] == 45
        # Progress: 150 / 1000 * 100 = 15%
        assert data[0]["progress_percentage"] == 15.0

    async def test_get_progress_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = await client.get("/api/v1/reading-programs/progress")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogReading:
    """Test POST /reading-programs/log-reading endpoint."""

    async def test_log_reading_success(self, client, test_patron, reading_program, test_db):
        """Test successfully logging reading activity."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
            goal_target=1000,
        )
        test_db.add(registration)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Log reading
        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "The Great Gatsby",
                "pages_read": 80,
                "reading_minutes": 45,
                "notes": "Finished chapter 3",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["registration_id"] == registration.id
        assert data["title"] == "The Great Gatsby"
        assert data["pages_read"] == 80
        assert data["minutes_read"] == 45
        assert data["notes"] == "Finished chapter 3"
        assert data["books_read"] == 1  # Auto-counted since pages/minutes > 0

    async def test_log_reading_without_registration(self, client, test_patron, reading_program):
        """Test logging reading when user isn't registered."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "Test Book",
                "pages_read": 50,
                "reading_minutes": 30,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not registered" in response.json()["error"]["message"].lower()

    async def test_log_reading_invalid_pages(self, client, test_patron, reading_program, test_db):
        """Test logging with invalid pages count."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
        )
        test_db.add(registration)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "Test Book",
                "pages_read": 50000,  # Invalid: > 10000
                "reading_minutes": 30,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "pages_read" in response.json()["error"]["message"].lower()

    async def test_log_reading_invalid_minutes(self, client, test_patron, reading_program, test_db):
        """Test logging with invalid minutes count."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
        )
        test_db.add(registration)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "Test Book",
                "pages_read": 50,
                "reading_minutes": 200,  # Invalid: > 120
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "reading_minutes" in response.json()["error"]["message"].lower()

    async def test_log_reading_requires_authentication(self, client, reading_program):
        """Test that endpoint requires authentication."""
        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "Test Book",
                "pages_read": 50,
                "reading_minutes": 30,
            },
        )

        assert response.status_code == 401

    async def test_log_reading_zero_values(self, client, test_patron, reading_program, test_db):
        """Test logging with zero pages and minutes."""
        # Create registration
        registration = ReadingRegistration(
            user_id=test_patron.id,
            program_id=reading_program.id,
        )
        test_db.add(registration)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/reading-programs/log-reading",
            json={
                "program_id": reading_program.id,
                "book_title": "Test Book",
                "pages_read": 0,
                "reading_minutes": 0,
                "notes": "Just wanted to record this book",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["books_read"] == 0  # No pages or minutes, so no book count


@pytest.mark.asyncio
class TestEndpointIntegration:
    """Integration tests for the complete workflow."""

    async def test_complete_workflow(self, client, test_patron, reading_program, test_db):
        """Test complete workflow: join -> log -> check progress."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Join program
        join_response = await client.post(
            "/api/v1/reading-programs/join",
            json={"program_id": reading_program.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert join_response.status_code == 201
        _ = join_response.json()["id"]

        # Log multiple reading sessions
        for i in range(3):
            log_response = await client.post(
                "/api/v1/reading-programs/log-reading",
                json={
                    "program_id": reading_program.id,
                    "book_title": f"Book {i+1}",
                    "pages_read": 50 + (i * 10),
                    "reading_minutes": 30 + (i * 5),
                    "notes": f"Session {i+1}",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert log_response.status_code == 201

        # Check progress
        progress_response = await client.get(
            "/api/v1/reading-programs/progress",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert progress_response.status_code == 200
        data = progress_response.json()
        assert len(data) == 1

        # Verify aggregated stats
        # Total minutes: 30 + 35 + 40 = 105
        assert data[0]["total_minutes"] == 105
        # Total pages: 50 + 60 + 70 = 180
        assert data[0]["total_pages"] == 180
        # Total books: 3 (one per session since all have pages/minutes)
        assert data[0]["total_books"] == 3
        # Progress: 105 / 1000 * 100 = 10.5%
        assert data[0]["progress_percentage"] == 10.5


@pytest.mark.asyncio
class TestSimplifiedGetCompanionEndpoints:
    """Test GET companion endpoints for simplified reading program flows."""

    async def test_get_join_lists_active_programs(self, client, test_patron, reading_program):
        # test_patron fixture is required (not referenced directly) -- it's
        # what creates the "testuser@example.com" user the login below
        # authenticates as; without it the login legitimately 401s.
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/join",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_available"] >= 1
        assert any(p["program_id"] == reading_program.id for p in data["available_programs"])

    async def test_get_log_entries_returns_user_entries(self, client, test_patron, reading_program, test_db):
        registration = ReadingRegistration(user_id=test_patron.id, program_id=reading_program.id)
        test_db.add(registration)
        await test_db.commit()
        await test_db.refresh(registration)

        entry = ReadingLogEntry(
            registration_id=registration.id,
            books_read=1,
            minutes_read=25,
            pages_read=18,
            title="Charlotte's Web",
        )
        test_db.add(entry)
        await test_db.commit()

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/log-entries",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["registration_id"] == registration.id for e in data["entries"])

    async def test_get_log_reading_metadata(self, client, test_patron):
        # test_patron fixture required for the same reason as
        # test_get_join_lists_active_programs above.
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/reading-programs/log-reading",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["required_fields"] == ["program_id"]
        assert data["validation"]["pages_read"]["max"] == 10000
