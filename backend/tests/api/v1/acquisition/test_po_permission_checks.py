# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Purchase Order Permission Checks

Comprehensive test suite for PO permission-based access control:
- PATRON users cannot create POs (403)
- STAFF users cannot approve POs (403, director required)
- STAFF users cannot update SUBMITTED POs (400, draft only)
- ADMIN users cannot delete non-DRAFT POs (400, draft only)
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.acquisition import PurchaseOrder, Vendor, Fund, PurchaseOrderStatus, FundStatus
from app.core.security import create_access_token


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def patron_user(test_db: AsyncSession) -> User:
    """Create a PATRON user for permission tests"""
    from app.core.security import hash_password

    user = User(
        email="po_patron@library.local",
        password_hash=hash_password("PatronUser123!"),
        first_name="PO",
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
async def staff_user(test_db: AsyncSession) -> User:
    """Create a STAFF user for permission tests"""
    from app.core.security import hash_password

    user = User(
        email="po_staff@library.local",
        password_hash=hash_password("StaffUser123!"),
        first_name="PO",
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
async def admin_user(test_db: AsyncSession) -> User:
    """Create an ADMIN user for permission tests"""
    from app.core.security import hash_password

    user = User(
        email="po_admin@library.local",
        password_hash=hash_password("AdminUser123!"),
        first_name="PO",
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
async def vendor(test_db: AsyncSession) -> Vendor:
    """Create a test vendor"""
    vendor = Vendor(
        name="Test Vendor",
        email="vendor@example.com",
        phone="555-0000",
        # Vendor has a single free-text `address` field, not separate
        # city/state/postal_code columns.
        address="123 Test St, Test City, TS 00000",
    )
    test_db.add(vendor)
    await test_db.commit()
    await test_db.refresh(vendor)
    return vendor


@pytest.fixture
async def fund(test_db: AsyncSession) -> Fund:
    """Create a test fund"""
    current_year = datetime.now().year
    fund = Fund(
        code="TEST-001",
        name="Test Fund",
        fiscal_year=current_year,
        status=FundStatus.ACTIVE,
        # Fund has allocated/encumbered/spent columns, not
        # budgeted_amount/available_amount (the latter is derived, not stored).
        allocated_amount=Decimal("10000.00"),
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.fixture
async def draft_po(test_db: AsyncSession, staff_user: User, vendor: Vendor, fund: Fund) -> PurchaseOrder:
    """Create a DRAFT purchase order"""
    po = PurchaseOrder(
        po_number="PO-202602-0001",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        expected_delivery=date.today() + timedelta(days=30),
        created_by_id=staff_user.id,
        status=PurchaseOrderStatus.DRAFT,
        total_amount=Decimal("1000.00"),
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)
    return po


@pytest.fixture
async def submitted_po(test_db: AsyncSession, staff_user: User, vendor: Vendor, fund: Fund) -> PurchaseOrder:
    """Create a purchase order awaiting approval.

    The approve endpoint (POFacadeService.approve_purchase_order) gates on
    PurchaseOrderStatus.PENDING_APPROVAL specifically, not SUBMITTED (a
    distinct later-pipeline status: ordered/shipped/received). "submitted"
    here means "submitted for approval", i.e. pending_approval.
    """
    po = PurchaseOrder(
        po_number="PO-202602-0002",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        expected_delivery=date.today() + timedelta(days=30),
        created_by_id=staff_user.id,
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        total_amount=Decimal("1000.00"),
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)
    return po


@pytest.fixture
async def approved_po(test_db: AsyncSession, admin_user: User, vendor: Vendor, fund: Fund) -> PurchaseOrder:
    """Create an APPROVED purchase order"""
    po = PurchaseOrder(
        po_number="PO-202602-0003",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        expected_delivery=date.today() + timedelta(days=30),
        created_by_id=admin_user.id,
        status=PurchaseOrderStatus.APPROVED,
        total_amount=Decimal("1000.00"),
        approved_by_id=admin_user.id,
        approved_at=datetime.now(),
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)
    return po


def get_auth_headers(user: User) -> dict:
    """Get authentication headers for user"""
    # get_current_user reads the JWT "sub" claim as int(user_id), not email.
    token = create_access_token(subject=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Test Cases
# ============================================================================


@pytest.mark.asyncio
class TestPOCreatePermissions:
    """Test PO creation permissions"""

    async def test_patron_cannot_create_po(self, client: AsyncClient, patron_user: User, vendor: Vendor, fund: Fund):
        """PATRON user attempting to create PO should get 403"""
        headers = get_auth_headers(patron_user)

        po_data = {
            "vendor_id": vendor.id,
            "fund_id": fund.id,
            "order_date": date.today().isoformat(),
            "expected_delivery": (date.today() + timedelta(days=30)).isoformat(),
            "items": [
                {
                    # POItemCreate (StrictInputSchema) requires "title", not
                    # "description" -- extras are rejected outright.
                    "title": "Test Item",
                    "quantity": 1,
                    "unit_price": "100.00",
                }
            ],
        }

        response = await client.post(
            "/api/v1/acquisition/purchase-orders",
            json=po_data,
            headers=headers,
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "Staff" in data["detail"] or "staff" in data["detail"].lower()

    async def test_staff_can_create_po(self, client: AsyncClient, staff_user: User, vendor: Vendor, fund: Fund):
        """STAFF user attempting to create PO should succeed (200/201)"""
        headers = get_auth_headers(staff_user)

        po_data = {
            "vendor_id": vendor.id,
            "fund_id": fund.id,
            "order_date": date.today().isoformat(),
            "expected_delivery": (date.today() + timedelta(days=30)).isoformat(),
            "items": [
                {
                    # POItemCreate (StrictInputSchema) requires "title", not
                    # "description" -- extras are rejected outright.
                    "title": "Test Item",
                    "quantity": 1,
                    "unit_price": "100.00",
                }
            ],
        }

        response = await client.post(
            "/api/v1/acquisition/purchase-orders",
            json=po_data,
            headers=headers,
        )

        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
class TestPOApprovalPermissions:
    """Test PO approval permissions"""

    async def test_staff_cannot_approve_po(self, client: AsyncClient, staff_user: User, submitted_po: PurchaseOrder):
        """STAFF user attempting to approve PO should get 403"""
        headers = get_auth_headers(staff_user)

        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{submitted_po.id}/approve",
            headers=headers,
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "Director" in data["detail"] or "director" in data["detail"].lower()

    async def test_admin_can_approve_po(self, client: AsyncClient, admin_user: User, submitted_po: PurchaseOrder):
        """ADMIN user attempting to approve PO should succeed (200)"""
        headers = get_auth_headers(admin_user)

        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{submitted_po.id}/approve",
            headers=headers,
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
class TestPOUpdatePermissions:
    """Test PO update permissions"""

    async def test_staff_cannot_update_submitted_po(
        self, client: AsyncClient, staff_user: User, submitted_po: PurchaseOrder
    ):
        """STAFF user attempting to update SUBMITTED PO should get 400 (draft only)"""
        headers = get_auth_headers(staff_user)

        update_data = {
            "notes": "Updated notes",
        }

        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{submitted_po.id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "draft" in data["detail"].lower()

    async def test_staff_cannot_update_approved_po(self, client: AsyncClient, staff_user: User, approved_po: PurchaseOrder):
        """STAFF user attempting to update APPROVED PO should get 400 (draft only)"""
        headers = get_auth_headers(staff_user)

        update_data = {
            "notes": "Updated notes",
        }

        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{approved_po.id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "draft" in data["detail"].lower()

    async def test_staff_can_update_draft_po(self, client: AsyncClient, staff_user: User, draft_po: PurchaseOrder):
        """STAFF user updating DRAFT PO should succeed (200)"""
        headers = get_auth_headers(staff_user)

        update_data = {
            "notes": "Updated notes",
        }

        response = await client.patch(
            f"/api/v1/acquisition/purchase-orders/{draft_po.id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


@pytest.mark.asyncio
class TestPODeletePermissions:
    """Test PO delete permissions"""

    async def test_admin_cannot_delete_approved_po(self, client: AsyncClient, admin_user: User, approved_po: PurchaseOrder):
        """ADMIN user attempting to delete APPROVED PO should get 400 (draft only)"""
        headers = get_auth_headers(admin_user)

        response = await client.delete(
            f"/api/v1/acquisition/purchase-orders/{approved_po.id}",
            headers=headers,
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "draft" in data["detail"].lower()

    async def test_admin_cannot_delete_submitted_po(self, client: AsyncClient, admin_user: User, submitted_po: PurchaseOrder):
        """ADMIN user attempting to delete SUBMITTED PO should get 400 (draft only)"""
        headers = get_auth_headers(admin_user)

        response = await client.delete(
            f"/api/v1/acquisition/purchase-orders/{submitted_po.id}",
            headers=headers,
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "draft" in data["detail"].lower()

    async def test_admin_can_delete_draft_po(self, client: AsyncClient, admin_user: User, draft_po: PurchaseOrder):
        """ADMIN user deleting DRAFT PO should succeed (204)"""
        headers = get_auth_headers(admin_user)

        response = await client.delete(
            f"/api/v1/acquisition/purchase-orders/{draft_po.id}",
            headers=headers,
        )

        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"

    async def test_staff_cannot_delete_po_created_by_others(
        self, client: AsyncClient, staff_user: User, admin_user: User, vendor: Vendor, fund: Fund, test_db: AsyncSession
    ):
        """STAFF user cannot delete PO created by someone else (even if DRAFT)"""
        # Create a draft PO by admin_user
        po = PurchaseOrder(
            po_number="PO-202602-0004",
            vendor_id=vendor.id,
            fund_id=fund.id,
            order_date=date.today(),
            expected_delivery=date.today() + timedelta(days=30),
            created_by_id=admin_user.id,
            status=PurchaseOrderStatus.DRAFT,
            total_amount=Decimal("1000.00"),
        )
        test_db.add(po)
        await test_db.commit()
        await test_db.refresh(po)

        headers = get_auth_headers(staff_user)

        response = await client.delete(
            f"/api/v1/acquisition/purchase-orders/{po.id}",
            headers=headers,
        )

        # Should get 403 (not authorized) because staff_user didn't create it
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
