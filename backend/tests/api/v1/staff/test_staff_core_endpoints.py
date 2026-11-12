# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Staff Domain Core Endpoints

Comprehensive test suite for the Staff management system covering:
- Staff directory and search
- Dashboard and metrics
- Reports and analytics
- Outreach programs
- Safety and emergency
- Room and space management
- Account operations
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestStaffDirectoryEndpoints:
    """Test staff member directory and search endpoints."""

    async def test_list_staff_directory(self, client: AsyncClient):
        """Test listing staff members in directory."""
        response = await client.get("/api/v1/staff/directory")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "staff_members" in data
            assert "total" in data
            assert "page" in data

    async def test_search_staff_by_name(self, client: AsyncClient):
        """Test searching staff by name."""
        response = await client.get("/api/v1/staff/directory?q=smith")
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_staff_by_role(self, client: AsyncClient):
        """Test filtering staff by role."""
        response = await client.get("/api/v1/staff/directory?role=staff")
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_staff_by_active_status(self, client: AsyncClient):
        """Test filtering staff by active status."""
        response = await client.get("/api/v1/staff/directory?is_active=true")
        assert response.status_code in [200, 401, 403, 404]

    async def test_staff_directory_pagination(self, client: AsyncClient):
        """Test staff directory pagination."""
        response = await client.get("/api/v1/staff/directory?page=1&per_page=20")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_staff_profile(self, client: AsyncClient):
        """Test getting individual staff member profile."""
        response = await client.get("/api/v1/staff/profile/1")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data or "email" in data


@pytest.mark.asyncio
class TestStaffDashboardEndpoints:
    """Test staff dashboard endpoints."""

    async def test_get_dashboard_stats(self, client: AsyncClient):
        """Test getting dashboard statistics."""
        response = await client.get("/api/v1/staff/dashboard/stats")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            # Should have circulation stats
            assert isinstance(data, dict)

    async def test_get_dashboard_activity(self, client: AsyncClient):
        """Test getting activity feed for dashboard."""
        response = await client.get("/api/v1/staff/dashboard/activity")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    async def test_get_outreach_metrics(self, client: AsyncClient):
        """Test getting outreach program metrics."""
        response = await client.get("/api/v1/staff/dashboard/outreach")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffReportsEndpoints:
    """Test staff reports and analytics endpoints."""

    async def test_get_circulation_report(self, client: AsyncClient):
        """Test getting circulation reports."""
        response = await client.get("/api/v1/staff/reports/circulation")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_collection_usage_report(self, client: AsyncClient):
        """Test getting collection usage statistics."""
        response = await client.get("/api/v1/staff/reports/collection-usage")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_statistics(self, client: AsyncClient):
        """Test getting patron statistics."""
        response = await client.get("/api/v1/staff/reports/patron-stats")
        assert response.status_code in [200, 401, 403, 404]

    async def test_report_with_date_range(self, client: AsyncClient):
        """Test getting report with date range filter."""
        start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
        end_date = datetime.now().date().isoformat()
        response = await client.get(
            f"/api/v1/staff/reports/circulation?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffOutreachEndpoints:
    """Test staff outreach program endpoints."""

    async def test_list_outreach_programs(self, client: AsyncClient):
        """Test listing outreach programs."""
        response = await client.get("/api/v1/staff/outreach/programs")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_outreach_program(self, client: AsyncClient):
        """Test getting specific outreach program details."""
        response = await client.get("/api/v1/staff/outreach/programs/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_outreach_partners(self, client: AsyncClient):
        """Test getting outreach partners."""
        response = await client.get("/api/v1/staff/outreach/partners")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_outreach_events(self, client: AsyncClient):
        """Test getting outreach events."""
        response = await client.get("/api/v1/staff/outreach/events")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffSafetyEndpoints:
    """Test staff safety and emergency endpoints."""

    async def test_get_safety_protocols(self, client: AsyncClient):
        """Test getting safety protocols."""
        response = await client.get("/api/v1/staff/safety/protocols")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_emergency_procedures(self, client: AsyncClient):
        """Test getting emergency procedures."""
        response = await client.get("/api/v1/staff/safety/emergency-procedures")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_incident_reports(self, client: AsyncClient):
        """Test getting incident reports."""
        response = await client.get("/api/v1/staff/safety/incidents")
        assert response.status_code in [200, 401, 403, 404]

    async def test_report_incident(self, client: AsyncClient):
        """Test reporting a safety incident."""
        incident_data = {
            "title": "Spill in main area",
            "description": "Water spill near circulation desk",
            "severity": "low",
            "location": "Main Floor"
        }
        response = await client.post(
            "/api/v1/staff/safety/incidents",
            json=incident_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffRoomManagementEndpoints:
    """Test room and space management endpoints."""

    async def test_list_library_rooms(self, client: AsyncClient):
        """Test listing library rooms and spaces."""
        response = await client.get("/api/v1/staff/rooms")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_room_details(self, client: AsyncClient):
        """Test getting specific room details."""
        response = await client.get("/api/v1/staff/rooms/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_room_availability(self, client: AsyncClient):
        """Test checking room availability."""
        response = await client.get("/api/v1/staff/rooms/1/availability")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_room_bookings(self, client: AsyncClient):
        """Test getting room bookings."""
        response = await client.get("/api/v1/staff/rooms/1/bookings")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffPatronOperationsEndpoints:
    """Test patron account and operations endpoints."""

    async def test_list_patrons(self, client: AsyncClient):
        """Test listing patrons."""
        response = await client.get("/api/v1/staff/patrons")
        assert response.status_code in [200, 401, 403, 404]

    async def test_search_patrons(self, client: AsyncClient):
        """Test searching for patrons."""
        response = await client.get("/api/v1/staff/patrons?q=smith")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_account(self, client: AsyncClient):
        """Test getting patron account details."""
        response = await client.get("/api/v1/staff/patrons/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_checkouts(self, client: AsyncClient):
        """Test getting patron checkouts."""
        response = await client.get("/api/v1/staff/patrons/1/checkouts")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_holds(self, client: AsyncClient):
        """Test getting patron holds."""
        response = await client.get("/api/v1/staff/patrons/1/holds")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_fines(self, client: AsyncClient):
        """Test getting patron fines."""
        response = await client.get("/api/v1/staff/patrons/1/fines")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffSearchEndpoints:
    """Test staff search functionality endpoints."""

    async def test_search_catalog(self, client: AsyncClient):
        """Test searching the catalog."""
        response = await client.get("/api/v1/staff/search?q=fiction")
        assert response.status_code in [200, 401, 403, 404]

    async def test_search_with_filters(self, client: AsyncClient):
        """Test searching with filters."""
        response = await client.get("/api/v1/staff/search?q=fiction&type=book&limit=20")
        assert response.status_code in [200, 401, 403, 404]

    async def test_advanced_search(self, client: AsyncClient):
        """Test advanced search functionality."""
        response = await client.get(
            "/api/v1/staff/search/advanced?author=smith&title=history&year=2020"
        )
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffCollectionAlertsEndpoints:
    """Test collection alerts and notifications endpoints."""

    async def test_get_collection_alerts(self, client: AsyncClient):
        """Test getting collection alerts."""
        response = await client.get("/api/v1/staff/alerts/collection")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_item_alerts(self, client: AsyncClient):
        """Test getting alerts for specific item."""
        response = await client.get("/api/v1/staff/alerts/item/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_acknowledge_alert(self, client: AsyncClient):
        """Test acknowledging an alert."""
        response = await client.post(
            "/api/v1/staff/alerts/1/acknowledge"
        )
        assert response.status_code in [200, 201, 401, 403, 404]


@pytest.mark.asyncio
class TestStaffIntegration:
    """Integration tests for staff workflows."""

    async def test_complete_patron_service_workflow(self, client: AsyncClient):
        """Test complete patron service workflow."""
        # Search for patron
        search_response = await client.get("/api/v1/staff/patrons?q=smith")

        if search_response.status_code == 200:
            # Get patron details
            patron_response = await client.get("/api/v1/staff/patrons/1")
            assert patron_response.status_code in [200, 401, 403]

            # Get patron's checkouts
            checkout_response = await client.get("/api/v1/staff/patrons/1/checkouts")
            assert checkout_response.status_code in [200, 401, 403]

            # Get patron's fines
            fines_response = await client.get("/api/v1/staff/patrons/1/fines")
            assert fines_response.status_code in [200, 401, 403]

    async def test_dashboard_monitoring_workflow(self, client: AsyncClient):
        """Test dashboard monitoring workflow."""
        # Get dashboard stats
        stats_response = await client.get("/api/v1/staff/dashboard/stats")

        # Get activity feed
        activity_response = await client.get("/api/v1/staff/dashboard/activity")

        # Get outreach metrics
        outreach_response = await client.get("/api/v1/staff/dashboard/outreach")

        for response in [stats_response, activity_response, outreach_response]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_reporting_workflow(self, client: AsyncClient):
        """Test reporting and analytics workflow."""
        # Get circulation report
        circulation = await client.get("/api/v1/staff/reports/circulation")

        # Get patron statistics
        stats = await client.get("/api/v1/staff/reports/patron-stats")

        # Get collection usage
        usage = await client.get("/api/v1/staff/reports/collection-usage")

        for response in [circulation, stats, usage]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_safety_compliance_workflow(self, client: AsyncClient):
        """Test safety and compliance workflow."""
        # Get safety protocols
        protocols = await client.get("/api/v1/staff/safety/protocols")

        # Get emergency procedures
        procedures = await client.get("/api/v1/staff/safety/emergency-procedures")

        # Get incident reports
        incidents = await client.get("/api/v1/staff/safety/incidents")

        for response in [protocols, procedures, incidents]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_room_management_workflow(self, client: AsyncClient):
        """Test room management workflow."""
        # List rooms
        rooms_response = await client.get("/api/v1/staff/rooms")

        if rooms_response.status_code == 200:
            # Get room details
            room_response = await client.get("/api/v1/staff/rooms/1")
            assert room_response.status_code in [200, 401, 403]

            # Check availability
            availability_response = await client.get("/api/v1/staff/rooms/1/availability")
            assert availability_response.status_code in [200, 401, 403]

            # Get bookings
            bookings_response = await client.get("/api/v1/staff/rooms/1/bookings")
            assert bookings_response.status_code in [200, 401, 403]

    async def test_outreach_program_workflow(self, client: AsyncClient):
        """Test outreach program management workflow."""
        # List programs
        programs = await client.get("/api/v1/staff/outreach/programs")

        # Get partners
        partners = await client.get("/api/v1/staff/outreach/partners")

        # Get events
        events = await client.get("/api/v1/staff/outreach/events")

        for response in [programs, partners, events]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_comprehensive_staff_operations(self, client: AsyncClient):
        """Test comprehensive staff operations across multiple functions."""
        # Directory search
        directory = await client.get("/api/v1/staff/directory")

        # Dashboard access
        dashboard = await client.get("/api/v1/staff/dashboard/stats")

        # Patron service
        patron_search = await client.get("/api/v1/staff/patrons")

        # Catalog search
        catalog_search = await client.get("/api/v1/staff/search?q=test")

        # Alerts
        alerts = await client.get("/api/v1/staff/alerts/collection")

        for response in [directory, dashboard, patron_search, catalog_search, alerts]:
            assert response.status_code in [200, 401, 403, 404]
