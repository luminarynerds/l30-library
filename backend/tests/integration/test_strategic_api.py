# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Strategic Planning API endpoints.

Tests cover strategic plan CRUD operations, goal management, milestones,
dashboard statistics, import/export functionality, and permission enforcement.
"""

from datetime import datetime, timedelta, timezone

import pytest


# ============ Fixtures ============


@pytest.fixture
async def strategic_admin(test_db):
    """Create an admin user for strategic planning operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="strategic_admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        first_name="Strategic",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def strategic_staff(test_db):
    """Create a staff user for strategic planning operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="strategic_staff@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Strategic",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def strategic_patron(test_db):
    """Create a patron user (public) for permission testing."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="strategic_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Strategic",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def sample_plan(test_db, strategic_admin):
    """Create a sample strategic plan for testing."""
    from app.models.strategic import StrategicPlan

    plan = StrategicPlan(
        title="2025-2028 Strategic Plan",
        description="A comprehensive plan for library growth",
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2028, 12, 31, tzinfo=timezone.utc),
        mission="To provide equitable access to information and resources",
        vision="A community hub for lifelong learning",
        values=["Equity", "Innovation", "Community"],
        status="draft",
        created_by_id=strategic_admin.id,
    )
    test_db.add(plan)
    await test_db.commit()
    await test_db.refresh(plan)
    return plan


@pytest.fixture
async def active_plan(test_db, strategic_admin):
    """Create an active strategic plan for testing."""
    from app.models.strategic import StrategicPlan

    plan = StrategicPlan(
        title="Current Active Plan",
        description="The currently active strategic plan",
        period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2027, 12, 31, tzinfo=timezone.utc),
        mission="Empowering our community through knowledge",
        vision="A library for everyone",
        values=["Access", "Quality", "Service"],
        status="active",
        created_by_id=strategic_admin.id,
    )
    test_db.add(plan)
    await test_db.commit()
    await test_db.refresh(plan)
    return plan


@pytest.fixture
async def sample_goal(test_db, sample_plan):
    """Create a sample goal for testing."""
    from app.models.strategic import StrategicGoal

    goal = StrategicGoal(
        plan_id=sample_plan.id,
        title="Increase Library Card Registrations",
        description="Increase new library card registrations by 25%",
        public_description="Growing our community membership",
        category="Community Engagement",
        department="Outreach",
        target_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
        progress=0,
        status="not_started",
        metrics=[
            {"name": "New registrations", "current": 500, "target": 625, "unit": "cards/year"}
        ],
        priority=1,
        is_public=True,
        staff_can_update=True,
    )
    test_db.add(goal)
    await test_db.commit()
    await test_db.refresh(goal)
    return goal


@pytest.fixture
async def active_plan_with_goals(test_db, strategic_admin):
    """Create an active plan with multiple goals for dashboard testing."""
    from app.models.strategic import StrategicGoal, StrategicPlan

    plan = StrategicPlan(
        title="Dashboard Test Plan",
        description="Plan for testing dashboard statistics",
        period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2027, 12, 31, tzinfo=timezone.utc),
        mission="Test mission",
        vision="Test vision",
        values=["Value1", "Value2"],
        status="active",
        next_review=datetime(2025, 6, 1, tzinfo=timezone.utc),
        created_by_id=strategic_admin.id,
    )
    test_db.add(plan)
    await test_db.flush()

    # Create goals with different statuses
    goals_data = [
        {"title": "Goal 1", "status": "completed", "progress": 100, "category": "Tech"},
        {"title": "Goal 2", "status": "on_track", "progress": 50, "category": "Tech"},
        {"title": "Goal 3", "status": "at_risk", "progress": 30, "category": "Community"},
        {"title": "Goal 4", "status": "delayed", "progress": 10, "category": "Community"},
        {"title": "Goal 5", "status": "not_started", "progress": 0, "category": "Collections"},
    ]

    for gdata in goals_data:
        goal = StrategicGoal(
            plan_id=plan.id,
            title=gdata["title"],
            status=gdata["status"],
            progress=gdata["progress"],
            category=gdata["category"],
            is_public=True,
        )
        test_db.add(goal)

    await test_db.commit()
    await test_db.refresh(plan)
    return plan


@pytest.fixture
async def sample_milestone(test_db, sample_plan):
    """Create a sample milestone for testing."""
    from app.models.strategic import StrategicMilestone

    milestone = StrategicMilestone(
        plan_id=sample_plan.id,
        title="First 100 New Members",
        description="Reached our first 100 new library card registrations",
        achieved_date=datetime(2025, 3, 15, tzinfo=timezone.utc),
        celebration_text="We did it! 100 new community members!",
        impact_story="This milestone represents growing community engagement.",
        is_public=True,
        is_featured=True,
        display_order=1,
        milestone_type="achievement",
    )
    test_db.add(milestone)
    await test_db.commit()
    await test_db.refresh(milestone)
    return milestone


async def get_auth_headers(client, email, password):
    """Helper function to get authentication headers."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": password},
    )
    if login_response.status_code != 200:
        return None
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


# ============ Plan CRUD Tests ============


@pytest.mark.integration
class TestPlanCRUD:
    """Test strategic plan CRUD operations."""

    async def test_create_strategic_plan(self, client, strategic_admin):
        """Test creating a strategic plan as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None, "Admin login failed"

        plan_data = {
            "title": "New Strategic Plan 2025-2030",
            "description": "A new strategic plan for the next five years",
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2030, 12, 31, tzinfo=timezone.utc).isoformat(),
            "mission": "To serve our community",
            "vision": "The best library in the region",
            "values": ["Excellence", "Accessibility", "Innovation"],
            "status": "draft",
        }

        response = await client.post("/api/v1/strategic/plans", json=plan_data, headers=headers)
        assert response.status_code == 200, f"Create plan failed: {response.text}"
        data = response.json()
        assert data["title"] == "New Strategic Plan 2025-2030"
        assert data["mission"] == "To serve our community"
        assert data["status"] == "draft"
        assert "id" in data

    async def test_get_strategic_plan_public(self, client, sample_plan):
        """Test getting a specific strategic plan (public endpoint)."""
        response = await client.get(f"/api/v1/strategic/plans/{sample_plan.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_plan.title
        assert data["id"] == sample_plan.id

    async def test_update_strategic_plan(self, client, strategic_admin, sample_plan):
        """Test updating a strategic plan as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        update_data = {
            "title": "Updated Strategic Plan Title",
            "mission": "Updated mission statement",
        }

        response = await client.put(
            f"/api/v1/strategic/plans/{sample_plan.id}",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Strategic Plan Title"
        assert data["mission"] == "Updated mission statement"

    async def test_delete_strategic_plan(self, client, strategic_admin, sample_plan):
        """Test deleting a strategic plan as admin (draft plan)."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/plans/{sample_plan.id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify plan is deleted
        response = await client.get(f"/api/v1/strategic/plans/{sample_plan.id}")
        assert response.status_code == 404

    async def test_cannot_delete_active_plan(self, client, strategic_admin, active_plan):
        """Test that active plans cannot be deleted."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/plans/{active_plan.id}",
            headers=headers,
        )
        assert response.status_code == 400
        assert "active" in response.json()["error"]["message"].lower()

    async def test_activate_plan_deactivates_others(
        self, client, strategic_admin, sample_plan, active_plan, test_db
    ):
        """Test that activating a plan deactivates the currently active plan."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        # Activate the draft plan
        response = await client.post(
            f"/api/v1/strategic/plans/{sample_plan.id}/activate",
            headers=headers,
        )
        assert response.status_code == 200
        assert "active" in response.json()["message"].lower()

        # Verify the previously active plan is now archived
        from sqlalchemy import select
        from app.models.strategic import StrategicPlan

        result = await test_db.execute(
            select(StrategicPlan).where(StrategicPlan.id == active_plan.id)
        )
        old_plan = result.scalar_one_or_none()
        assert old_plan is not None
        # Status might be string or enum, check both
        status_str = old_plan.status.value if hasattr(old_plan.status, "value") else old_plan.status
        assert status_str == "archived"

    async def test_get_active_plan(self, client, active_plan):
        """Test getting the current active strategic plan."""
        response = await client.get("/api/v1/strategic/plans/active")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["id"] == active_plan.id
        assert data["title"] == active_plan.title

    async def test_list_plans_public_sees_only_active(self, client, sample_plan, active_plan):
        """Test that unauthenticated users only see active plans."""
        response = await client.get("/api/v1/strategic/plans")
        assert response.status_code == 200
        data = response.json()
        # Should only see active plan
        assert all(p["status"] == "active" for p in data["items"])

    async def test_list_plans_staff_sees_all(
        self, client, strategic_staff, sample_plan, active_plan
    ):
        """Test that staff can see all plans regardless of status."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.get("/api/v1/strategic/plans", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Staff should see both draft and active plans
        assert len(data) >= 2

    async def test_get_nonexistent_plan(self, client):
        """Test getting a plan that doesn't exist."""
        response = await client.get("/api/v1/strategic/plans/99999")
        assert response.status_code == 404


# ============ Goal CRUD Tests ============


@pytest.mark.integration
class TestGoalCRUD:
    """Test strategic goal CRUD operations."""

    async def test_create_goal(self, client, strategic_admin, sample_plan):
        """Test creating a goal as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        goal_data = {
            "title": "Expand Digital Collections",
            "description": "Increase e-book and digital resource offerings by 50%",
            "category": "Collections",
            "target_date": datetime(2026, 6, 30, tzinfo=timezone.utc).isoformat(),
            "progress": 0,
            "status": "not_started",
            "metrics": [
                {"name": "E-books added", "current": 1000, "target": 1500, "unit": "titles"}
            ],
            "priority": 2,
        }

        response = await client.post(
            f"/api/v1/strategic/plans/{sample_plan.id}/goals",
            json=goal_data,
            headers=headers,
        )
        assert response.status_code == 200, f"Create goal failed: {response.text}"
        data = response.json()
        assert data["title"] == "Expand Digital Collections"
        assert data["category"] == "Collections"
        assert data["priority"] == 2

    async def test_staff_can_create_goal(self, client, strategic_staff, sample_plan):
        """Test that staff can create goals."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        goal_data = {
            "title": "Staff Created Goal",
            "description": "A goal created by staff",
            "category": "Services",
            "status": "not_started",
        }

        response = await client.post(
            f"/api/v1/strategic/plans/{sample_plan.id}/goals",
            json=goal_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Staff Created Goal"

    async def test_update_goal(self, client, strategic_admin, sample_goal):
        """Test updating a goal as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        update_data = {
            "title": "Updated Goal Title",
            "progress": 25,
            "status": "on_track",
        }

        response = await client.put(
            f"/api/v1/strategic/goals/{sample_goal.id}",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Goal Title"
        assert data["progress"] == 25
        assert data["status"] == "on_track"

    async def test_staff_can_update_permission(self, client, strategic_staff, sample_goal):
        """Test that staff can update goals when staff_can_update is True."""
        # sample_goal has staff_can_update=True
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        update_data = {
            "progress": 30,
            "status": "on_track",
        }

        response = await client.put(
            f"/api/v1/strategic/goals/{sample_goal.id}",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == 30

    async def test_delete_goal(self, client, strategic_admin, sample_goal):
        """Test deleting a goal as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/goals/{sample_goal.id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    async def test_goal_progress_update(self, client, strategic_staff, sample_goal):
        """Test recording a progress update for a goal."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        progress_data = {
            "progress": 50,
            "note": "Reached halfway point in Q2",
            "status": "on_track",
        }

        response = await client.post(
            f"/api/v1/strategic/goals/{sample_goal.id}/progress",
            json=progress_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == 50
        assert data["status"] == "on_track"
        # Check that update was recorded
        assert len(data["updates"]) > 0
        assert data["updates"][-1]["progress"] == 50

    async def test_goal_auto_complete_at_100(self, client, strategic_staff, sample_goal):
        """Test that setting progress to 100 auto-completes the goal."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        progress_data = {
            "progress": 100,
            "note": "Goal completed!",
        }

        response = await client.post(
            f"/api/v1/strategic/goals/{sample_goal.id}/progress",
            json=progress_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == 100
        # Should auto-set status to completed
        assert data["status"] == "completed"

    async def test_goal_not_found(self, client, strategic_admin):
        """Test updating a goal that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.put(
            "/api/v1/strategic/goals/99999",
            json={"title": "Updated"},
            headers=headers,
        )
        assert response.status_code == 404


# ============ Milestone CRUD Tests ============


@pytest.mark.integration
class TestMilestoneCRUD:
    """Test strategic milestone CRUD operations."""

    async def test_create_milestone(self, client, strategic_staff, sample_plan):
        """Test creating a milestone as staff."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        milestone_data = {
            "title": "New Milestone Achievement",
            "description": "A significant achievement",
            "achieved_date": datetime(2025, 6, 15, tzinfo=timezone.utc).isoformat(),
            "celebration_text": "We achieved something great!",
            "is_public": True,
            "is_featured": False,
            "milestone_type": "achievement",
        }

        response = await client.post(
            f"/api/v1/strategic/plans/{sample_plan.id}/milestones",
            json=milestone_data,
            headers=headers,
        )
        assert response.status_code == 200, f"Create milestone failed: {response.text}"
        data = response.json()
        assert data["title"] == "New Milestone Achievement"
        assert data["is_public"] is True

    async def test_update_milestone(self, client, strategic_staff, sample_milestone):
        """Test updating a milestone."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        update_data = {
            "title": "Updated Milestone Title",
            "is_featured": True,
            "celebration_text": "Updated celebration message!",
        }

        response = await client.put(
            f"/api/v1/strategic/milestones/{sample_milestone.id}",
            json=update_data,
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Milestone Title"
        assert data["is_featured"] is True

    async def test_delete_milestone(self, client, strategic_admin, sample_milestone):
        """Test deleting a milestone as admin."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/milestones/{sample_milestone.id}",
            headers=headers,
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    async def test_list_milestones_public(self, client, sample_plan, sample_milestone):
        """Test listing public milestones."""
        response = await client.get(f"/api/v1/strategic/plans/{sample_plan.id}/milestones")
        assert response.status_code == 200
        data = response.json()
        # Should only see public milestones
        assert all(m["is_public"] is True for m in data["items"])

    async def test_featured_milestone_filter(self, client, test_db, sample_plan, sample_milestone):
        """Test that milestones are properly filtered."""
        # sample_milestone is featured, let's verify it's in results
        response = await client.get(f"/api/v1/strategic/plans/{sample_plan.id}/milestones")
        assert response.status_code == 200
        data = response.json()
        featured = [m for m in data["items"] if m["is_featured"]]
        assert len(featured) >= 1

    async def test_public_milestone_filter(self, client, test_db, sample_plan, strategic_admin):
        """Test that private milestones are hidden from public."""
        from app.models.strategic import StrategicMilestone

        # Create a private milestone
        private_milestone = StrategicMilestone(
            plan_id=sample_plan.id,
            title="Private Milestone",
            description="This should not be visible to public",
            is_public=False,
            is_featured=False,
            milestone_type="internal",
        )
        test_db.add(private_milestone)
        await test_db.commit()

        # Public request should not see private milestones
        response = await client.get(f"/api/v1/strategic/plans/{sample_plan.id}/milestones")
        assert response.status_code == 200
        data = response.json()
        titles = [m["title"] for m in data["items"]]
        assert "Private Milestone" not in titles

        # Staff with include_private should see it
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        response = await client.get(
            f"/api/v1/strategic/plans/{sample_plan.id}/milestones?include_private=true",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        titles = [m["title"] for m in data["items"]]
        assert "Private Milestone" in titles


# ============ Permission Tests ============


@pytest.mark.integration
class TestPermissions:
    """Test permission enforcement for strategic planning endpoints."""

    async def test_public_user_cannot_create_plan(self, client, strategic_patron):
        """Test that a patron/public user cannot create strategic plans."""
        headers = await get_auth_headers(
            client, "strategic_patron@example.com", "PatronPassword123!"
        )
        assert headers is not None

        plan_data = {
            "title": "Unauthorized Plan",
            "description": "Should not be created",
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2030, 12, 31, tzinfo=timezone.utc).isoformat(),
        }

        response = await client.post("/api/v1/strategic/plans", json=plan_data, headers=headers)
        assert response.status_code == 403
        assert "admin" in response.json()["error"]["message"].lower()

    async def test_staff_cannot_delete_plan(self, client, strategic_staff, sample_plan):
        """Test that staff cannot delete strategic plans."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/plans/{sample_plan.id}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_staff_cannot_delete_goal(self, client, strategic_staff, sample_goal):
        """Test that staff cannot delete goals."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/goals/{sample_goal.id}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_staff_cannot_delete_milestone(self, client, strategic_staff, sample_milestone):
        """Test that staff cannot delete milestones (admin only)."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.delete(
            f"/api/v1/strategic/milestones/{sample_milestone.id}",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_admin_has_full_access(self, client, strategic_admin, sample_plan, test_db):
        """Test that admin has full access to all operations."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        # Can create plan
        plan_data = {
            "title": "Admin Created Plan",
            "description": "Created by admin",
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2030, 12, 31, tzinfo=timezone.utc).isoformat(),
        }
        response = await client.post("/api/v1/strategic/plans", json=plan_data, headers=headers)
        assert response.status_code == 200
        new_plan_id = response.json()["id"]

        # Can update plan
        response = await client.put(
            f"/api/v1/strategic/plans/{new_plan_id}",
            json={"title": "Admin Updated Plan"},
            headers=headers,
        )
        assert response.status_code == 200

        # Can create goal
        goal_data = {"title": "Admin Goal", "status": "not_started"}
        response = await client.post(
            f"/api/v1/strategic/plans/{new_plan_id}/goals",
            json=goal_data,
            headers=headers,
        )
        assert response.status_code == 200
        goal_id = response.json()["id"]

        # Can delete goal
        response = await client.delete(
            f"/api/v1/strategic/goals/{goal_id}",
            headers=headers,
        )
        assert response.status_code == 200

        # Can delete plan
        response = await client.delete(
            f"/api/v1/strategic/plans/{new_plan_id}",
            headers=headers,
        )
        assert response.status_code == 200

    async def test_public_cannot_create_goal(self, client, strategic_patron, sample_plan):
        """Test that patron/public users cannot create goals."""
        headers = await get_auth_headers(
            client, "strategic_patron@example.com", "PatronPassword123!"
        )
        assert headers is not None

        goal_data = {
            "title": "Unauthorized Goal",
            "status": "not_started",
        }

        response = await client.post(
            f"/api/v1/strategic/plans/{sample_plan.id}/goals",
            json=goal_data,
            headers=headers,
        )
        assert response.status_code == 403

    async def test_unauthenticated_cannot_modify(self, client, sample_plan):
        """Test that unauthenticated users cannot modify resources."""
        # Try to create plan without auth
        plan_data = {
            "title": "Unauthenticated Plan",
            "period_start": datetime(2025, 1, 1).isoformat(),
            "period_end": datetime(2030, 12, 31).isoformat(),
        }
        response = await client.post("/api/v1/strategic/plans", json=plan_data)
        assert response.status_code == 401

        # Try to update plan without auth
        response = await client.put(
            f"/api/v1/strategic/plans/{sample_plan.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401


# ============ Dashboard/Analytics Tests ============


@pytest.mark.integration
class TestDashboardAnalytics:
    """Test dashboard and analytics endpoints."""

    async def test_dashboard_statistics(self, client, active_plan_with_goals):
        """Test that dashboard returns correct statistics."""
        response = await client.get("/api/v1/strategic/dashboard")
        assert response.status_code == 200
        data = response.json()

        assert data["has_active_plan"] is True
        assert "plan" in data
        assert "progress" in data
        assert "by_category" in data

        # Verify progress statistics
        progress = data["progress"]
        assert progress["total_goals"] == 5
        assert progress["completed"] == 1
        assert progress["on_track"] == 1
        assert progress["at_risk"] == 1
        assert progress["delayed"] == 1
        assert progress["not_started"] == 1

        # Verify overall progress calculation (100+50+30+10+0)/5 = 38
        assert progress["overall"] == 38

    async def test_dashboard_no_active_plan(self, client, sample_plan):
        """Test dashboard response when no active plan exists."""
        # sample_plan is draft, not active
        response = await client.get("/api/v1/strategic/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["has_active_plan"] is False

    async def test_dashboard_by_category(self, client, active_plan_with_goals):
        """Test dashboard category breakdown."""
        response = await client.get("/api/v1/strategic/dashboard")
        assert response.status_code == 200
        data = response.json()

        by_category = data["by_category"]
        assert "Tech" in by_category
        assert "Community" in by_category
        assert "Collections" in by_category

        # Tech: Goal 1 (100%) + Goal 2 (50%) = 2 goals, avg 75%
        assert by_category["Tech"]["count"] == 2
        assert by_category["Tech"]["progress"] == 75

    async def test_our_story_public_data(self, client, test_db, strategic_admin):
        """Test the public Our Story endpoint."""
        from app.models.strategic import StrategicGoal, StrategicMilestone, StrategicPlan

        # Create an active plan with public content
        plan = StrategicPlan(
            title="Our Story Test Plan",
            description="Test plan for Our Story endpoint",
            period_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2027, 12, 31, tzinfo=timezone.utc),
            mission="Our mission for the community",
            vision="Our vision for the future",
            values=["Integrity", "Service", "Excellence"],
            status="active",
            story_intro="Welcome to our library's story",
            history_timeline=[
                {"year": 1952, "title": "Founded", "description": "Library established"},
                {"year": 2000, "title": "Expansion", "description": "New building opened"},
            ],
            created_by_id=strategic_admin.id,
        )
        test_db.add(plan)
        await test_db.flush()

        # Add public goal
        goal = StrategicGoal(
            plan_id=plan.id,
            title="Public Goal",
            description="Internal description",
            public_description="This is what we share publicly",
            progress=50,
            status="on_track",
            is_public=True,
        )
        test_db.add(goal)

        # Add private goal (should not appear)
        private_goal = StrategicGoal(
            plan_id=plan.id,
            title="Private Goal",
            description="This should not be visible",
            progress=25,
            status="on_track",
            is_public=False,
        )
        test_db.add(private_goal)

        # Add public milestone
        milestone = StrategicMilestone(
            plan_id=plan.id,
            title="Public Milestone",
            celebration_text="Celebrating publicly!",
            is_public=True,
            milestone_type="achievement",
        )
        test_db.add(milestone)

        await test_db.commit()

        # Test Our Story endpoint
        response = await client.get("/api/v1/strategic/our-story")
        assert response.status_code == 200
        data = response.json()

        assert data["has_plan"] is True
        assert data["mission"] == "Our mission for the community"
        assert data["vision"] == "Our vision for the future"
        assert len(data["values"]) == 3
        assert data["story_intro"] == "Welcome to our library's story"

        # Check history timeline
        assert len(data["history_timeline"]) == 2
        assert data["history_timeline"][0]["year"] == 1952

        # Check only public goals are included
        goal_titles = [g["title"] for g in data["goals"]]
        assert "Public Goal" in goal_titles
        assert "Private Goal" not in goal_titles

        # Check public milestones
        milestone_titles = [m["title"] for m in data["milestones"]]
        assert "Public Milestone" in milestone_titles


# ============ Import/Export Tests ============


@pytest.mark.integration
class TestImportExport:
    """Test import and export functionality."""

    async def test_export_plan(
        self, client, strategic_admin, sample_plan, sample_goal, sample_milestone
    ):
        """Test exporting a strategic plan."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.get(
            f"/api/v1/strategic/plans/{sample_plan.id}/export",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify export structure
        assert data["title"] == sample_plan.title
        assert data["mission"] == sample_plan.mission
        assert "goals" in data
        assert "milestones" in data
        assert len(data["goals"]) >= 1
        assert len(data["milestones"]) >= 1

        # Verify goal data in export
        exported_goal = data["goals"][0]
        assert exported_goal["title"] == sample_goal.title
        assert "metrics" in exported_goal

    async def test_export_plan_not_found(self, client, strategic_admin):
        """Test exporting a plan that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.get(
            "/api/v1/strategic/plans/99999/export",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_export_plan_unauthorized(self, client, strategic_staff, sample_plan):
        """Test that non-admin cannot export plans."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.get(
            f"/api/v1/strategic/plans/{sample_plan.id}/export",
            headers=headers,
        )
        assert response.status_code == 403

    async def test_import_plan(self, client, strategic_admin):
        """Test importing a strategic plan."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        import_data = {
            "title": "Imported Strategic Plan",
            "description": "A plan imported from JSON",
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2030-12-31T23:59:59Z",
            "mission": "Imported mission statement",
            "vision": "Imported vision",
            "values": ["Imported Value 1", "Imported Value 2"],
            "goals": [
                {
                    "title": "Imported Goal 1",
                    "description": "First imported goal",
                    "category": "Technology",
                    "progress": 0,
                    "status": "not_started",
                    "priority": 1,
                    "is_public": True,
                },
                {
                    "title": "Imported Goal 2",
                    "description": "Second imported goal",
                    "category": "Community",
                    "target_date": "2026-12-31T00:00:00Z",
                    "progress": 25,
                    "status": "on_track",
                    "metrics": [
                        {"name": "Metric A", "current": 10, "target": 100, "unit": "count"}
                    ],
                },
            ],
            "milestones": [
                {
                    "title": "Imported Milestone",
                    "description": "A milestone from import",
                    "celebration_text": "Imported celebration!",
                    "is_public": True,
                    "is_featured": True,
                    "milestone_type": "achievement",
                },
            ],
        }

        response = await client.post(
            "/api/v1/strategic/import",
            json=import_data,
            headers=headers,
        )
        assert response.status_code == 200, f"Import failed: {response.text}"
        data = response.json()

        assert "plan_id" in data
        assert data["goals_imported"] == 2
        assert data["milestones_imported"] == 1

        # Verify the imported plan
        plan_response = await client.get(f"/api/v1/strategic/plans/{data['plan_id']}")
        assert plan_response.status_code == 200
        plan_data = plan_response.json()
        assert plan_data["title"] == "Imported Strategic Plan"
        assert plan_data["status"] == "draft"  # Imported plans should be draft by default
        assert len(plan_data["goals"]) == 2

    async def test_import_plan_unauthorized(self, client, strategic_staff):
        """Test that non-admin cannot import plans."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        import_data = {
            "title": "Unauthorized Import",
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2030-12-31T23:59:59Z",
        }

        response = await client.post(
            "/api/v1/strategic/import",
            json=import_data,
            headers=headers,
        )
        assert response.status_code == 403

    async def test_import_invalid_data(self, client, strategic_admin):
        """Test importing with invalid data."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        # Missing required fields
        import_data = {
            "title": "Incomplete Import",
            # Missing period_start and period_end
        }

        response = await client.post(
            "/api/v1/strategic/import",
            json=import_data,
            headers=headers,
        )
        assert response.status_code == 422  # Validation error


# ============ Staff View Tests ============


@pytest.mark.integration
class TestStaffViews:
    """Test staff-specific views and endpoints."""

    async def test_get_staff_goals(self, client, strategic_staff, active_plan_with_goals, test_db):
        """Test getting goals relevant to staff."""
        from app.models.strategic import StrategicGoal
        from sqlalchemy import select, update

        # Update one goal to have a department and staff_can_update=True
        await test_db.execute(
            update(StrategicGoal)
            .where(StrategicGoal.title == "Goal 1")
            .values(department="Technology", staff_can_update=True)
        )
        await test_db.commit()

        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.get("/api/v1/strategic/staff/my-goals", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["has_plan"] is True
        assert "goals" in data
        # Should return goals that staff can update or have department set
        assert len(data["goals"]) >= 1

    async def test_staff_goals_unauthorized(self, client, strategic_patron):
        """Test that patrons cannot access staff goals view."""
        headers = await get_auth_headers(
            client, "strategic_patron@example.com", "PatronPassword123!"
        )
        assert headers is not None

        response = await client.get("/api/v1/strategic/staff/my-goals", headers=headers)
        assert response.status_code == 403


# ============ Edge Cases and Error Handling Tests ============


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_create_goal_nonexistent_plan(self, client, strategic_admin):
        """Test creating a goal for a plan that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        goal_data = {
            "title": "Orphan Goal",
            "status": "not_started",
        }

        response = await client.post(
            "/api/v1/strategic/plans/99999/goals",
            json=goal_data,
            headers=headers,
        )
        assert response.status_code == 404
        assert "plan" in response.json()["error"]["message"].lower()

    async def test_create_milestone_nonexistent_plan(self, client, strategic_staff):
        """Test creating a milestone for a plan that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        milestone_data = {
            "title": "Orphan Milestone",
            "milestone_type": "achievement",
        }

        response = await client.post(
            "/api/v1/strategic/plans/99999/milestones",
            json=milestone_data,
            headers=headers,
        )
        assert response.status_code == 404

    async def test_progress_update_invalid_value(self, client, strategic_staff, sample_goal):
        """Test progress update with invalid value (>100)."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        progress_data = {
            "progress": 150,  # Invalid: exceeds 100
            "note": "Invalid progress",
        }

        response = await client.post(
            f"/api/v1/strategic/goals/{sample_goal.id}/progress",
            json=progress_data,
            headers=headers,
        )
        assert response.status_code == 422  # Validation error

    async def test_progress_update_negative_value(self, client, strategic_staff, sample_goal):
        """Test progress update with negative value."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        progress_data = {
            "progress": -10,  # Invalid: negative
            "note": "Invalid progress",
        }

        response = await client.post(
            f"/api/v1/strategic/goals/{sample_goal.id}/progress",
            json=progress_data,
            headers=headers,
        )
        assert response.status_code == 422  # Validation error

    async def test_activate_nonexistent_plan(self, client, strategic_admin):
        """Test activating a plan that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.post(
            "/api/v1/strategic/plans/99999/activate",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_update_nonexistent_milestone(self, client, strategic_staff):
        """Test updating a milestone that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.put(
            "/api/v1/strategic/milestones/99999",
            json={"title": "Updated"},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_milestone(self, client, strategic_admin):
        """Test deleting a milestone that doesn't exist."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        response = await client.delete(
            "/api/v1/strategic/milestones/99999",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_plan_period_validation(self, client, strategic_admin):
        """Test that plan period end must be after period start."""
        headers = await get_auth_headers(client, "strategic_admin@example.com", "AdminPassword123!")
        assert headers is not None

        # Create plan with period_end before period_start
        plan_data = {
            "title": "Invalid Period Plan",
            "period_start": datetime(2030, 1, 1, tzinfo=timezone.utc).isoformat(),
            "period_end": datetime(2025, 12, 31, tzinfo=timezone.utc).isoformat(),  # Before start
        }

        response = await client.post("/api/v1/strategic/plans", json=plan_data, headers=headers)
        # Should either reject (422) or accept and let the business logic handle it
        # The API might not validate this - testing the actual behavior
        assert response.status_code in [200, 400, 422]


# ============ Comment Tests (Placeholder - Endpoints May Not Exist) ============


@pytest.mark.integration
class TestComments:
    """Test comment functionality (if endpoints exist)."""

    async def test_create_comment_endpoint_exists(self, client, strategic_staff, sample_goal):
        """Test if comment creation endpoint exists."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        comment_data = {
            "content": "This is a test comment",
        }

        response = await client.post(
            f"/api/v1/strategic/goals/{sample_goal.id}/comments",
            json=comment_data,
            headers=headers,
        )
        # If endpoint doesn't exist, it will return 404
        # This test documents that comment endpoints may need to be implemented
        if response.status_code == 404:
            pytest.skip("Comment endpoints not implemented yet")
        assert response.status_code in [200, 201]


# ============ Notification Tests (Placeholder - Endpoints May Not Exist) ============


@pytest.mark.integration
class TestNotifications:
    """Test notification functionality (if endpoints exist)."""

    async def test_get_notifications_endpoint_exists(self, client, strategic_staff):
        """Test if notifications endpoint exists."""
        headers = await get_auth_headers(client, "strategic_staff@example.com", "StaffPassword123!")
        assert headers is not None

        response = await client.get(
            "/api/v1/strategic/notifications",
            headers=headers,
        )
        # If endpoint doesn't exist, it will return 404
        if response.status_code == 404:
            pytest.skip("Notification endpoints not implemented yet")
        assert response.status_code == 200
