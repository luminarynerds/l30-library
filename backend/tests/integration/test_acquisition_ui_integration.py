# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Acquisition UI endpoints.

Tests verify that the Acquisition management pages (AcquisitionManagementPage
and StaffAcquisitionPage) can successfully communicate with backend endpoints.
"""

import pytest
from decimal import Decimal


@pytest.fixture
async def staff_token(client, test_staff, test_staff_data):
    """Get staff access token for testing."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client, test_admin, test_admin_data):
    """Get admin access token for testing."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def patron_token(client, test_patron, test_user_data):
    """Get patron access token for testing."""
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def test_vendor(test_db, test_staff):
    """Create a test vendor."""
    from app.models.acquisition import Vendor

    vendor = Vendor(
        name="Test Vendor Inc",
        contact_name="John Smith",
        email="vendor@example.com",
        phone="555-1234",
        is_active=True
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)
    return vendor


@pytest.fixture
async def test_fund(test_db):
    """Create a test fund."""
    from app.models.acquisition import Fund, FundStatus

    fund = Fund(
        code="TEST-2026",
        name="Test Fund",
        fiscal_year=2026,
        allocated_amount=Decimal("10000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        status=FundStatus.ACTIVE
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.mark.integration
@pytest.mark.asyncio
class TestAcquisitionUIIntegration:
    """Test acquisition API endpoints called by frontend pages."""

    # ============ Fund Endpoints ============

    async def test_funds_list(self, client, staff_token):
        """Frontend can list acquisition funds."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get("/api/v1/acquisition/funds", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_fund_create(self, client, admin_token):
        """Frontend can create a fund (admin only)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "code": "NEW-2026",
            "name": "New Test Fund",
            "fiscal_year": 2026,
            "allocated_amount": 5000.00
        }
        response = await client.post("/api/v1/acquisition/funds", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEW-2026"
        assert data["name"] == "New Test Fund"

    async def test_fund_update(self, client, admin_token, test_fund):
        """Frontend can update a fund (admin only)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "name": "Updated Fund Name"
        }
        response = await client.patch(
            f"/api/v1/acquisition/funds/{test_fund.id}",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Fund Name"

    # ============ Vendor Endpoints ============

    async def test_vendors_list(self, client, staff_token):
        """Frontend can list vendors."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get("/api/v1/acquisition/vendors", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_vendor_create(self, client, staff_token):
        """Frontend can create a vendor."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "name": "New Vendor LLC",
            "contact_name": "Jane Doe",
            "email": "new@vendor.com",
            "phone": "555-5678"
        }
        response = await client.post("/api/v1/acquisition/vendors", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Vendor LLC"
        assert data["email"] == "new@vendor.com"

    async def test_vendor_update(self, client, staff_token, test_vendor):
        """Frontend can update a vendor."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "phone": "555-9999"
        }
        response = await client.patch(
            f"/api/v1/acquisition/vendors/{test_vendor.id}",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "555-9999"

    async def test_vendors_search(self, client, staff_token, test_vendor):
        """Frontend can search vendors."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get(
            "/api/v1/acquisition/vendors?q=Test",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Should find our test vendor
        assert len(data["items"]) > 0

    # ============ Purchase Order Endpoints ============

    async def test_purchase_orders_list(self, client, staff_token):
        """Frontend can list purchase orders."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get("/api/v1/acquisition/purchase-orders", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_purchase_order_create(self, client, staff_token, test_vendor, test_fund):
        """Frontend can create a purchase order."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "vendor_id": test_vendor.id,
            "fund_id": test_fund.id,
            "notes": "Test PO"
        }
        response = await client.post(
            "/api/v1/acquisition/purchase-orders",
            json=payload,
            headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["vendor_id"] == test_vendor.id
        assert data["fund_id"] == test_fund.id
        assert "po_number" in data

    async def test_purchase_order_get_detail(self, client, staff_token, test_db, test_vendor, test_fund, test_staff):
        """Frontend can get purchase order details."""
        from app.models.acquisition import PurchaseOrder

        # Create a PO
        po = PurchaseOrder(
            po_number="PO-TEST-001",
            vendor_id=test_vendor.id,
            fund_id=test_fund.id,
            created_by_id=test_staff.id,
            total_amount=Decimal("100.00")
        )
        test_db.add(po)
        await test_db.commit()
        await test_db.refresh(po)

        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get(
            f"/api/v1/acquisition/purchase-orders/{po.id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["po_number"] == "PO-TEST-001"
        assert data["vendor_id"] == test_vendor.id

    async def test_purchase_order_update(self, client, staff_token, test_db, test_vendor, test_fund, test_staff):
        """Frontend can update a purchase order."""
        from app.models.acquisition import PurchaseOrder, PurchaseOrderStatus

        # Create a draft PO
        po = PurchaseOrder(
            po_number="PO-TEST-002",
            vendor_id=test_vendor.id,
            fund_id=test_fund.id,
            created_by_id=test_staff.id,
            status=PurchaseOrderStatus.DRAFT,
            total_amount=Decimal("100.00")
        )
        test_db.add(po)
        await test_db.commit()
        await test_db.refresh(po)

        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "notes": "Updated notes"
        }
        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{po.id}",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200

    # ============ Selection List Endpoints ============

    async def test_selection_list_list(self, client, staff_token):
        """Frontend can list selection list items."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get("/api/v1/acquisition/selection-list", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_selection_list_create(self, client, staff_token):
        """Frontend can add items to selection list."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "978-1234567890",
            "estimated_price": 29.99,
            "priority": "medium",
            "source": "manual"
        }
        response = await client.post(
            "/api/v1/acquisition/selection-list",
            json=payload,
            headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"

    async def test_selection_list_delete(self, client, staff_token, test_db, test_staff):
        """Frontend can remove items from selection list."""
        from app.models.acquisition import SelectionListItem, SelectionPriority, SelectionSource

        # Create a selection item
        item = SelectionListItem(
            title="Book to Delete",
            author="Author Name",
            priority=SelectionPriority.MEDIUM,
            source=SelectionSource.MANUAL,
            requested_by_id=test_staff.id
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.delete(
            f"/api/v1/acquisition/selection-list/{item.id}",
            headers=headers
        )
        assert response.status_code == 204

    # ============ Authorization Tests ============

    async def test_patron_cannot_access_acquisition(self, client, patron_token):
        """Patrons cannot access acquisition endpoints."""
        headers = {"Authorization": f"Bearer {patron_token}"}

        # Try to list funds
        response = await client.get("/api/v1/acquisition/funds", headers=headers)
        assert response.status_code == 403

        # Try to list vendors
        response = await client.get("/api/v1/acquisition/vendors", headers=headers)
        assert response.status_code == 403

        # Try to list purchase orders
        response = await client.get("/api/v1/acquisition/purchase-orders", headers=headers)
        assert response.status_code == 403

    async def test_unauthenticated_cannot_access_acquisition(self, client):
        """Unauthenticated users cannot access acquisition endpoints."""
        # Try to list funds
        response = await client.get("/api/v1/acquisition/funds")
        assert response.status_code == 401

        # Try to list vendors
        response = await client.get("/api/v1/acquisition/vendors")
        assert response.status_code == 401

        # Try to list purchase orders
        response = await client.get("/api/v1/acquisition/purchase-orders")
        assert response.status_code == 401

    async def test_staff_cannot_create_fund(self, client, staff_token):
        """Staff cannot create funds (admin only)."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "code": "STAFF-2026",
            "name": "Staff Fund",
            "fiscal_year": 2026,
            "allocated_amount": 1000.00
        }
        response = await client.post("/api/v1/acquisition/funds", json=payload, headers=headers)
        assert response.status_code == 403
