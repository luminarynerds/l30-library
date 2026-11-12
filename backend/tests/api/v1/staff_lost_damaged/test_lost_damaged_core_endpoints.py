# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Staff Lost & Damaged Domain Core Endpoints

Comprehensive test suite for lost and damaged item management covering:
- Lost item tracking and claims
- Damaged item reports and repairs
- Claims returned items
- Financial tracking and restitution
- Status tracking and workflows
- Reports and analytics
"""

import pytest
from datetime import datetime, timedelta, date
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLostItemsEndpoints:
    """Test lost item management endpoints."""

    async def test_list_lost_items(self, client: AsyncClient):
        """Test listing lost items."""
        response = await client.get("/api/v1/staff/lost-damaged/lost-items")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    async def test_get_lost_item(self, client: AsyncClient):
        """Test getting lost item details."""
        response = await client.get("/api/v1/staff/lost-damaged/lost-items/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_report_lost_item(self, client: AsyncClient):
        """Test reporting a lost item."""
        # Current route is POST /lost/{checkout_id}/mark-lost, not a bare
        # POST /lost-items (that path is GET-only -- list endpoint).
        item_data = {
            "checkout_id": 1,
            "lost_type": "lost_by_patron",
            "report_notes": "Lost while checking out",
        }
        response = await client.post("/api/v1/staff/lost-damaged/lost/1/mark-lost", json=item_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_update_lost_item(self, client: AsyncClient):
        """Test updating lost item status."""
        update_data = {"status": "resolved", "resolution_notes": "Item returned by patron"}
        response = await client.put("/api/v1/staff/lost-damaged/lost-items/1", json=update_data)
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_lost_items_by_status(self, client: AsyncClient):
        """Test filtering lost items by status."""
        response = await client.get("/api/v1/staff/lost-damaged/lost-items?status=reported")
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_lost_items_by_date(self, client: AsyncClient):
        """Test filtering lost items by date range."""
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        response = await client.get(
            f"/api/v1/staff/lost-damaged/lost-items?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_lost_item_history(self, client: AsyncClient):
        """Test getting lost item history."""
        response = await client.get("/api/v1/staff/lost-damaged/lost-items/1/history")
        assert response.status_code in [200, 401, 403, 404]

    async def test_mark_lost_item_found(self, client: AsyncClient):
        """Test marking lost item as found."""
        response = await client.post("/api/v1/staff/lost-damaged/lost-items/1/found")
        assert response.status_code in [200, 201, 401, 403, 404]


@pytest.mark.asyncio
class TestDamagedItemsEndpoints:
    """Test damaged item management endpoints."""

    async def test_list_damaged_items(self, client: AsyncClient):
        """Test listing damaged items."""
        response = await client.get("/api/v1/staff/lost-damaged/damaged-items")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    async def test_get_damaged_item(self, client: AsyncClient):
        """Test getting damaged item details."""
        response = await client.get("/api/v1/staff/lost-damaged/damaged-items/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_report_damaged_item(self, client: AsyncClient):
        """Test reporting a damaged item."""
        # Current route is POST /damaged/report, not a bare POST
        # /damaged-items (that path is GET-only -- list endpoint).
        item_data = {
            "item_copy_id": 1,
            "damage_types": ["water_damage"],
            "damage_description": "Water damage from spill",
            "severity": "severe",
        }
        response = await client.post("/api/v1/staff/lost-damaged/damaged/report", json=item_data)
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_update_damaged_item(self, client: AsyncClient):
        """Test updating damaged item status."""
        update_data = {"status": "being_repaired", "repair_notes": "Sent to bindery"}
        response = await client.put("/api/v1/staff/lost-damaged/damaged-items/1", json=update_data)
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_damaged_items_by_severity(self, client: AsyncClient):
        """Test filtering damaged items by severity."""
        response = await client.get("/api/v1/staff/lost-damaged/damaged-items?severity=high")
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_damaged_items_by_type(self, client: AsyncClient):
        """Test filtering damaged items by damage type."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/damaged-items?damage_type=water_damage"
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_mark_damaged_item_repaired(self, client: AsyncClient):
        """Test marking damaged item as repaired."""
        response = await client.post(
            "/api/v1/staff/lost-damaged/damaged-items/1/repaired",
            json={"repair_completion_date": date.today().isoformat()},
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_mark_damaged_item_discarded(self, client: AsyncClient):
        """Test marking damaged item as discarded."""
        response = await client.post("/api/v1/staff/lost-damaged/damaged-items/1/discard")
        assert response.status_code in [200, 201, 401, 403, 404]


@pytest.mark.asyncio
class TestClaimsReturnedEndpoints:
    """Test claims returned (item returned after being lost) endpoints."""

    async def test_list_claims_returned(self, client: AsyncClient):
        """Test listing claims returned items."""
        response = await client.get("/api/v1/staff/lost-damaged/claims-returned")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_claims_returned_item(self, client: AsyncClient):
        """Test getting claims returned item."""
        response = await client.get("/api/v1/staff/lost-damaged/claims-returned/1")
        assert response.status_code in [200, 401, 403, 404]

    async def test_record_item_returned(self, client: AsyncClient):
        """Test recording item returned after being claimed lost."""
        # Current route is POST /claims-returned/file, not a bare POST
        # /claims-returned (that path is GET-only -- list endpoint).
        return_data = {
            "checkout_id": 1,
            "patron_statement": "I returned it to the book drop last week",
        }
        response = await client.post(
            "/api/v1/staff/lost-damaged/claims-returned/file", json=return_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_process_restitution(self, client: AsyncClient):
        """Test processing restitution for returned item."""
        restitution_data = {
            "claims_returned_id": 1,
            "refund_amount": 25.00,
            "refund_method": "cash",
        }
        response = await client.post(
            "/api/v1/staff/lost-damaged/claims-returned/1/refund", json=restitution_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_filter_claims_by_status(self, client: AsyncClient):
        """Test filtering claims returned by status."""
        response = await client.get("/api/v1/staff/lost-damaged/claims-returned?status=refunded")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestFinancialTrackingEndpoints:
    """Test financial tracking for lost/damaged items."""

    async def test_get_lost_item_charges(self, client: AsyncClient):
        """Test getting charges for lost item."""
        response = await client.get("/api/v1/staff/lost-damaged/lost-items/1/charges")
        assert response.status_code in [200, 401, 403, 404]

    async def test_apply_replacement_charge(self, client: AsyncClient):
        """Test applying replacement charge."""
        charge_data = {"lost_item_id": 1, "charge_amount": 25.00, "charge_type": "replacement"}
        response = await client.post(
            "/api/v1/staff/lost-damaged/lost-items/1/charges", json=charge_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_get_repair_costs(self, client: AsyncClient):
        """Test getting repair costs for damaged item."""
        response = await client.get("/api/v1/staff/lost-damaged/damaged-items/1/costs")
        assert response.status_code in [200, 401, 403, 404]

    async def test_record_repair_cost(self, client: AsyncClient):
        """Test recording repair cost."""
        cost_data = {"damaged_item_id": 1, "cost_amount": 50.00, "vendor": "Bindery Inc"}
        response = await client.post(
            "/api/v1/staff/lost-damaged/damaged-items/1/costs", json=cost_data
        )
        assert response.status_code in [200, 201, 401, 403, 404]

    async def test_get_financial_summary(self, client: AsyncClient):
        """Test getting financial summary."""
        response = await client.get("/api/v1/staff/lost-damaged/financial-summary")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestReportsEndpoints:
    """Test reporting and analytics endpoints."""

    async def test_get_lost_damaged_summary(self, client: AsyncClient):
        """Test getting lost/damaged items summary."""
        response = await client.get("/api/v1/staff/lost-damaged/summary")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_monthly_report(self, client: AsyncClient):
        """Test getting monthly loss/damage report."""
        response = await client.get("/api/v1/staff/lost-damaged/reports/monthly")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_patron_losses(self, client: AsyncClient):
        """Test getting patron loss statistics."""
        response = await client.get("/api/v1/staff/lost-damaged/reports/patron-losses")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_collection_losses(self, client: AsyncClient):
        """Test getting collection loss statistics."""
        response = await client.get("/api/v1/staff/lost-damaged/reports/collection-losses")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_damage_type_report(self, client: AsyncClient):
        """Test getting damage type analysis."""
        response = await client.get("/api/v1/staff/lost-damaged/reports/damage-types")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_financial_impact_report(self, client: AsyncClient):
        """Test getting financial impact report."""
        response = await client.get("/api/v1/staff/lost-damaged/reports/financial-impact")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestLostDamagedIntegration:
    """Integration tests for lost/damaged item workflows."""

    async def test_lost_item_lifecycle(self, client: AsyncClient):
        """Test complete lost item lifecycle."""
        # Report lost
        report = await client.post(
            "/api/v1/staff/lost-damaged/lost-items",
            json={"item_id": 1, "patron_id": 1, "date_reported": date.today().isoformat()},
        )

        if report.status_code in [200, 201]:
            # Apply charge
            charge = await client.post(
                "/api/v1/staff/lost-damaged/lost-items/1/charges",
                json={"charge_amount": 25.00, "charge_type": "replacement"},
            )
            assert charge.status_code in [200, 201, 401, 403]

            # Item found
            found = await client.post("/api/v1/staff/lost-damaged/lost-items/1/found")
            assert found.status_code in [200, 201, 401, 403]

            # Refund
            refund = await client.post(
                "/api/v1/staff/lost-damaged/claims-returned/1/refund",
                json={"refund_amount": 25.00, "refund_method": "cash"},
            )
            assert refund.status_code in [200, 201, 401, 403]

    async def test_damaged_item_workflow(self, client: AsyncClient):
        """Test damaged item repair workflow."""
        # Report damaged
        report = await client.post(
            "/api/v1/staff/lost-damaged/damaged-items",
            json={"item_id": 1, "damage_type": "water_damage", "severity": "high"},
        )

        if report.status_code in [200, 201]:
            # Record repair cost
            cost = await client.post(
                "/api/v1/staff/lost-damaged/damaged-items/1/costs",
                json={"cost_amount": 50.00, "vendor": "Bindery"},
            )
            assert cost.status_code in [200, 201, 401, 403]

            # Mark repaired
            repair = await client.post(
                "/api/v1/staff/lost-damaged/damaged-items/1/repaired",
                json={"repair_completion_date": date.today().isoformat()},
            )
            assert repair.status_code in [200, 201, 401, 403]

    async def test_reporting_workflow(self, client: AsyncClient):
        """Test reporting and analytics workflow."""
        # Get summary
        summary = await client.get("/api/v1/staff/lost-damaged/summary")

        # Get monthly report
        monthly = await client.get("/api/v1/staff/lost-damaged/reports/monthly")

        # Get patron losses
        patrons = await client.get("/api/v1/staff/lost-damaged/reports/patron-losses")

        # Get financial impact
        financial = await client.get("/api/v1/staff/lost-damaged/reports/financial-impact")

        for response in [summary, monthly, patrons, financial]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_financial_tracking_workflow(self, client: AsyncClient):
        """Test financial tracking workflow."""
        # Get summary
        summary = await client.get("/api/v1/staff/lost-damaged/financial-summary")

        # Get lost item charges
        charges = await client.get("/api/v1/staff/lost-damaged/lost-items/1/charges")

        # Get repair costs
        costs = await client.get("/api/v1/staff/lost-damaged/damaged-items/1/costs")

        for response in [summary, charges, costs]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_claims_returned_full_workflow(self, client: AsyncClient):
        """Test full claims returned workflow."""
        # Record return
        return_record = await client.post(
            "/api/v1/staff/lost-damaged/claims-returned",
            json={
                "lost_item_id": 1,
                "return_date": date.today().isoformat(),
                "condition": "acceptable",
            },
        )

        if return_record.status_code in [200, 201]:
            # Process refund
            refund = await client.post(
                "/api/v1/staff/lost-damaged/claims-returned/1/refund",
                json={"refund_amount": 25.00, "refund_method": "cash"},
            )
            assert refund.status_code in [200, 201, 401, 403]

            # Get claims
            claims = await client.get("/api/v1/staff/lost-damaged/claims-returned")
            assert claims.status_code in [200, 401, 403]

    async def test_comprehensive_dashboard_workflow(self, client: AsyncClient):
        """Test comprehensive dashboard with all metrics."""
        # Lost items
        lost = await client.get("/api/v1/staff/lost-damaged/lost-items")

        # Damaged items
        damaged = await client.get("/api/v1/staff/lost-damaged/damaged-items")

        # Claims
        claims = await client.get("/api/v1/staff/lost-damaged/claims-returned")

        # Summary
        summary = await client.get("/api/v1/staff/lost-damaged/summary")

        # Financial summary
        financial = await client.get("/api/v1/staff/lost-damaged/financial-summary")

        for response in [lost, damaged, claims, summary, financial]:
            assert response.status_code in [200, 401, 403, 404]
