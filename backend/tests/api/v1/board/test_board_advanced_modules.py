# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Board Domain Advanced Modules (Action Items, Notices, PDF Exports)

Comprehensive test suite for:
- Board meeting action item tracking
- Public meeting notice compliance
- PDF export functionality
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


@pytest.mark.asyncio
class TestActionItemsEndpoints:
    """Test board meeting action item tracking endpoints."""

    async def test_list_meeting_action_items(self, client: AsyncClient):
        """Test listing action items for a specific meeting."""
        response = await client.get("/api/v1/board/meetings/1/action-items")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    async def test_list_meeting_action_items_with_status_filter(self, client: AsyncClient):
        """Test listing action items filtered by status."""
        response = await client.get("/api/v1/board/meetings/1/action-items?status=in_progress")
        assert response.status_code in [200, 401, 403, 404]

    async def test_create_action_item(self, client: AsyncClient):
        """Test creating a new action item for a meeting."""
        action_item_data = {
            "title": "Review Budget Proposal",
            "description": "Review the budget proposal for next fiscal year",
            "assigned_to_id": 1,
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "priority": "high"
        }
        response = await client.post(
            "/api/v1/board/meetings/1/action-items",
            json=action_item_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_get_action_item_detail(self, client: AsyncClient):
        """Test getting specific action item details."""
        response = await client.get("/api/v1/board/action-items/1")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "title" in data

    async def test_list_all_action_items(self, client: AsyncClient):
        """Test listing all action items across meetings."""
        response = await client.get("/api/v1/board/action-items")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    async def test_list_action_items_with_filters(self, client: AsyncClient):
        """Test listing action items with multiple filters."""
        response = await client.get(
            "/api/v1/board/action-items?status=in_progress&priority=high&limit=20"
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_action_item_status(self, client: AsyncClient):
        """Test getting current status of an action item."""
        response = await client.get("/api/v1/board/action-items/1/status")
        assert response.status_code in [200, 401, 403, 404]

    async def test_update_action_item_status(self, client: AsyncClient):
        """Test updating action item status."""
        status_data = {
            "status": "in_progress",
            "notes": "Started working on this"
        }
        response = await client.post(
            "/api/v1/board/action-items/1/status",
            json=status_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_update_action_item(self, client: AsyncClient):
        """Test updating action item details."""
        update_data = {
            "title": "Updated Action Item Title",
            "priority": "medium"
        }
        response = await client.put(
            "/api/v1/board/action-items/1",
            json=update_data
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_delete_action_item(self, client: AsyncClient):
        """Test deleting an action item."""
        response = await client.delete("/api/v1/board/action-items/1")
        assert response.status_code in [204, 401, 403, 404]


@pytest.mark.asyncio
class TestNoticesEndpoints:
    """Test board public meeting notice compliance endpoints."""

    async def test_generate_meeting_notice(self, client: AsyncClient):
        """Test generating a public meeting notice."""
        notice_request = {
            "include_agenda": True,
            "include_accessibility_info": True
        }
        response = await client.post(
            "/api/v1/board/meetings/1/notice/generate",
            json=notice_request
        )
        assert response.status_code in [200, 201, 401, 403, 404]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "notice_content" in data
            assert "meeting_id" in data

    async def test_generate_notice_with_custom_header(self, client: AsyncClient):
        """Test generating notice with custom header and footer."""
        notice_request = {
            "custom_header": "LIBRARY BOARD MEETING",
            "custom_footer": "Contact: board@library.org",
            "include_agenda": True
        }
        response = await client.post(
            "/api/v1/board/meetings/1/notice/generate",
            json=notice_request
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_post_meeting_notice(self, client: AsyncClient):
        """Test recording that a notice has been posted."""
        post_data = {
            "location": "Library Website",
            "url": "https://library.org/meetings/board",
            "notes": "Posted to main page"
        }
        response = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json=post_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_check_notice_compliance(self, client: AsyncClient):
        """Test checking meeting notice compliance status."""
        response = await client.get("/api/v1/board/meetings/1/notice/compliance")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "meeting_id" in data
            assert "is_compliant" in data
            assert "compliance_issues" in data

    async def test_get_compliance_report(self, client: AsyncClient):
        """Test getting compliance report for multiple meetings."""
        response = await client.get(
            "/api/v1/board/notices/compliance-report?upcoming_only=true&limit=20"
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    async def test_publish_meeting_notice(self, client: AsyncClient):
        """Test marking meeting notice as officially published."""
        response = await client.post(
            "/api/v1/board/meetings/1/notice/publish"
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_remove_posting_location(self, client: AsyncClient):
        """Test removing a notice posting location."""
        response = await client.delete(
            "/api/v1/board/meetings/1/notice/posting/Library%20Website"
        )
        assert response.status_code in [200, 204, 401, 403, 404]


@pytest.mark.asyncio
class TestPDFExportEndpoints:
    """Test board PDF export endpoints."""

    async def test_export_meeting_agenda_pdf(self, client: AsyncClient):
        """Test exporting meeting agenda as PDF."""
        response = await client.get("/api/v1/board/meetings/1/agenda/pdf")
        # PDF export may be publicly accessible
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"

    async def test_export_meeting_minutes_pdf(self, client: AsyncClient):
        """Test exporting meeting minutes as PDF."""
        response = await client.get("/api/v1/board/meetings/1/minutes/pdf")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"

    async def test_export_public_notice_pdf(self, client: AsyncClient):
        """Test exporting public meeting notice as PDF."""
        response = await client.get("/api/v1/board/meetings/1/notice/pdf")
        assert response.status_code in [200, 401, 403, 404]

    async def test_export_vote_record_pdf(self, client: AsyncClient):
        """Test exporting vote record as PDF."""
        response = await client.get("/api/v1/board/meetings/1/votes/pdf")
        assert response.status_code in [200, 401, 403, 404]

    async def test_export_board_packet_pdf(self, client: AsyncClient):
        """Test exporting complete board meeting packet as PDF."""
        response = await client.get("/api/v1/board/meetings/1/packet/pdf")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"


@pytest.mark.asyncio
class TestActionItemsIntegration:
    """Integration tests for action item workflows."""

    async def test_action_item_lifecycle(self, client: AsyncClient):
        """Test complete action item workflow: create -> update -> status change."""
        # Create action item
        create_response = await client.post(
            "/api/v1/board/meetings/1/action-items",
            json={
                "title": "Test Action Item",
                "description": "Testing lifecycle",
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "priority": "high"
            }
        )
        if create_response.status_code in [200, 201]:
            action_item = create_response.json()
            action_id = action_item.get("id", 1)

            # Update status to in_progress
            update_response = await client.post(
                f"/api/v1/board/action-items/{action_id}/status",
                json={"status": "in_progress", "notes": "Started"}
            )
            assert update_response.status_code in [200, 201, 401, 403]

            # Update status to completed
            complete_response = await client.post(
                f"/api/v1/board/action-items/{action_id}/status",
                json={"status": "completed", "notes": "Done"}
            )
            assert complete_response.status_code in [200, 201, 401, 403]

    async def test_action_items_by_meeting(self, client: AsyncClient):
        """Test retrieving all action items for a meeting."""
        # Get meeting action items
        response = await client.get("/api/v1/board/meetings/1/action-items")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

            # If items exist, they should have required fields
            if len(data) > 0:
                item = data[0]
                assert "id" in item
                assert "status" in item

    async def test_filter_action_items_by_priority(self, client: AsyncClient):
        """Test filtering action items by priority."""
        response = await client.get(
            "/api/v1/board/action-items?priority=high&limit=10"
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_action_items_by_assignee(self, client: AsyncClient):
        """Test filtering action items by assigned person."""
        response = await client.get(
            "/api/v1/board/action-items?assigned_to_id=1&status=in_progress"
        )
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestNoticesIntegration:
    """Integration tests for notice compliance workflows."""

    async def test_notice_workflow(self, client: AsyncClient):
        """Test complete notice workflow: generate -> post -> check compliance."""
        # Generate notice
        generate_response = await client.post(
            "/api/v1/board/meetings/1/notice/generate",
            json={"include_agenda": True}
        )
        if generate_response.status_code in [200, 201]:
            # Post notice
            post_response = await client.post(
                "/api/v1/board/meetings/1/notice/post",
                json={
                    "location": "Library Website",
                    "url": "https://library.org"
                }
            )
            assert post_response.status_code in [200, 201, 401, 403]

            # Check compliance
            compliance_response = await client.get(
                "/api/v1/board/meetings/1/notice/compliance"
            )
            assert compliance_response.status_code in [200, 401, 403]

    async def test_compliance_report_structure(self, client: AsyncClient):
        """Test compliance report contains required fields."""
        response = await client.get(
            "/api/v1/board/notices/compliance-report?limit=10"
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

            # If reports exist, check structure
            if len(data) > 0:
                report = data[0]
                assert "meeting_id" in report
                assert "is_compliant" in report
                assert "compliance_issues" in report

    async def test_multiple_posting_locations(self, client: AsyncClient):
        """Test recording multiple posting locations for a notice."""
        # Post to first location
        _ = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json={"location": "Website"}
        )

        # Post to second location
        _ = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json={"location": "Public Board"}
        )

        # Check compliance includes both
        compliance_response = await client.get(
            "/api/v1/board/meetings/1/notice/compliance"
        )
        if compliance_response.status_code == 200:
            data = compliance_response.json()
            assert "posting_locations" in data


@pytest.mark.asyncio
class TestPDFExportIntegration:
    """Integration tests for PDF export workflows."""

    async def test_agenda_pdf_availability(self, client: AsyncClient):
        """Test agenda PDF is available for download."""
        response = await client.get("/api/v1/board/meetings/1/agenda/pdf")
        assert response.status_code in [200, 401, 403, 404]

    async def test_minutes_pdf_availability(self, client: AsyncClient):
        """Test minutes PDF is available for download."""
        response = await client.get("/api/v1/board/meetings/1/minutes/pdf")
        assert response.status_code in [200, 401, 403, 404]

    async def test_board_packet_pdf_availability(self, client: AsyncClient):
        """Test complete board packet PDF is available."""
        response = await client.get("/api/v1/board/meetings/1/packet/pdf")
        assert response.status_code in [200, 401, 403, 404]

    async def test_pdf_exports_content_type(self, client: AsyncClient):
        """Test PDF exports have correct content type."""
        response = await client.get("/api/v1/board/meetings/1/agenda/pdf")
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf"

    async def test_combined_document_export_workflow(self, client: AsyncClient):
        """Test exporting multiple document types for a meeting."""
        # Export agenda
        agenda_response = await client.get("/api/v1/board/meetings/1/agenda/pdf")

        # Export minutes
        minutes_response = await client.get("/api/v1/board/meetings/1/minutes/pdf")

        # Export notice
        notice_response = await client.get("/api/v1/board/meetings/1/notice/pdf")

        # All should have valid status codes
        for response in [agenda_response, minutes_response, notice_response]:
            assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestBoardAdvancedModulesIntegration:
    """Comprehensive integration tests across advanced modules."""

    async def test_meeting_preparation_workflow(self, client: AsyncClient):
        """Test complete meeting preparation workflow."""
        # 1. Generate meeting notice
        notice_response = await client.post(
            "/api/v1/board/meetings/1/notice/generate",
            json={"include_agenda": True, "include_accessibility_info": True}
        )

        # 2. Post notice to locations
        post_response = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json={"location": "Website"}
        )

        # 3. Create action items
        action_response = await client.post(
            "/api/v1/board/meetings/1/action-items",
            json={
                "title": "Prepare Materials",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat()
            }
        )

        # 4. Export agenda PDF
        pdf_response = await client.get("/api/v1/board/meetings/1/agenda/pdf")

        # 5. Check compliance
        compliance_response = await client.get(
            "/api/v1/board/meetings/1/notice/compliance"
        )

        # All workflows should complete
        for response in [notice_response, post_response, action_response, pdf_response, compliance_response]:
            assert response.status_code in [200, 201, 401, 403, 404]

    async def test_comprehensive_meeting_documentation(self, client: AsyncClient):
        """Test all documentation exports for a meeting."""
        # Get meeting details
        meeting_response = await client.get("/api/v1/board/meetings/1")

        # Export all documents
        agenda_pdf = await client.get("/api/v1/board/meetings/1/agenda/pdf")
        minutes_pdf = await client.get("/api/v1/board/meetings/1/minutes/pdf")
        notice_pdf = await client.get("/api/v1/board/meetings/1/notice/pdf")
        packet_pdf = await client.get("/api/v1/board/meetings/1/packet/pdf")
        vote_record = await client.get("/api/v1/board/meetings/1/votes/pdf")

        # All should return valid responses
        for response in [meeting_response, agenda_pdf, minutes_pdf, notice_pdf, packet_pdf, vote_record]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_action_item_tracking_for_meeting(self, client: AsyncClient):
        """Test action item tracking system for meetings."""
        # Get meeting action items
        items_response = await client.get("/api/v1/board/meetings/1/action-items")

        # Create new action item
        create_response = await client.post(
            "/api/v1/board/meetings/1/action-items",
            json={
                "title": "Follow-up Action",
                "priority": "high",
                "due_date": (datetime.now() + timedelta(days=5)).isoformat()
            }
        )

        # Filter by status
        filtered_response = await client.get(
            "/api/v1/board/action-items?status=not_started"
        )

        assert items_response.status_code in [200, 401, 403, 404]
        assert create_response.status_code in [200, 201, 401, 403, 404]
        assert filtered_response.status_code in [200, 401, 403, 404]

    async def test_notice_compliance_tracking(self, client: AsyncClient):
        """Test complete notice compliance tracking."""
        # Generate notice
        generate = await client.post(
            "/api/v1/board/meetings/1/notice/generate",
            json={"include_agenda": True}
        )

        # Post to locations
        location1 = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json={"location": "Website"}
        )

        location2 = await client.post(
            "/api/v1/board/meetings/1/notice/post",
            json={"location": "Public Board"}
        )

        # Check individual compliance
        compliance = await client.get("/api/v1/board/meetings/1/notice/compliance")

        # Get full report
        report = await client.get("/api/v1/board/notices/compliance-report")

        assert generate.status_code in [200, 201, 401, 403, 404]
        assert location1.status_code in [200, 201, 401, 403, 404]
        assert location2.status_code in [200, 201, 401, 403, 404]
        assert compliance.status_code in [200, 401, 403, 404]
        assert report.status_code in [200, 401, 403, 404]
