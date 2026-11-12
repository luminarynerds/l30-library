# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Equipment API Endpoints

Tests equipment CRUD operations:
- POST /equipment to create equipment
- GET /equipment to list equipment with filtering by type
- PATCH /equipment/{id} to update equipment condition
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import (
    Equipment,
    EquipmentType,
    EquipmentStatus,
    EquipmentCondition,
)
from app.models.user import User, UserRole


@pytest.fixture
async def test_staff(db: AsyncSession) -> User:
    """Create a test staff member."""
    staff = User(
        email="staff@example.com",
        password_hash="hashed",
        first_name="Jane",
        last_name="Staff",
        role=UserRole.STAFF,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


class TestEquipmentCreate:
    """Test creating equipment via POST /equipment."""

    async def test_create_equipment_success(
        self, staff_client: AsyncClient, db: AsyncSession, test_staff: User
    ):
        """Test successfully creating equipment."""
        payload = {
            "equipment_type": "laptop",
            "name": "Dell Latitude 5520",
            "serial_number": "DL5520-001",
            "barcode": "EQP-DL5520-001",
        }

        # Create equipment
        response = await staff_client.post("/api/v1/equipment", json=payload)

        # Equipment creation should work (201 Created or 200 OK)
        assert response.status_code in [201, 200]
        data = response.json()
        assert data["name"] == "Dell Latitude 5520"
        assert data["equipment_type"] == "laptop"
        assert data["serial_number"] == "DL5520-001"
        assert data["status"] == "available"
        assert data["condition"] == "good"

    async def test_create_equipment_with_all_fields(
        self, staff_client: AsyncClient, db: AsyncSession
    ):
        """Test creating equipment with all optional fields."""
        payload = {
            "name": "MacBook Pro 14",
            "equipment_type": "laptop",
            "description": "Apple MacBook Pro 14-inch",
            "serial_number": "MBP-14-2024-001",
            "barcode": "EQP-MBP-14-001",
            "manufacturer": "Apple",
            "model": "MacBook Pro 14",
            "model_year": 2024,
            "requires_agreement": True,
            "max_checkout_days": 14,
            "fine_per_day": "10.00",
            "max_renewals": 2,
            "deposit_required": True,
            "deposit_amount": "500.00",
            "replacement_cost": "2000.00",
            "purchase_price": "1500.00",
            "location": "Main Branch",
        }

        response = await staff_client.post("/api/v1/equipment", json=payload)
        assert response.status_code in [201, 200]
        data = response.json()
        assert data["name"] == "MacBook Pro 14"
        assert data["manufacturer"] == "Apple"
        assert data["model"] == "MacBook Pro 14"
        assert data["deposit_required"] is True


class TestEquipmentList:
    """Test listing equipment via GET /equipment."""

    async def test_list_equipment_empty(self, client: AsyncClient):
        """Test listing equipment when none exist."""
        response = await client.get("/api/v1/equipment")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_equipment_with_type_filter(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Test listing equipment filtered by type=LAPTOP."""
        # Create some equipment
        laptop = Equipment(
            name="Dell Latitude 5520",
            equipment_type=EquipmentType.LAPTOP,
            serial_number="DL5520-001",
            barcode="EQP-DL5520-001",
            status=EquipmentStatus.AVAILABLE,
            condition=EquipmentCondition.GOOD,
        )
        hotspot = Equipment(
            name="Netgear Hotspot",
            equipment_type=EquipmentType.HOTSPOT,
            serial_number="HS-001",
            barcode="EQP-HS-001",
            status=EquipmentStatus.AVAILABLE,
            condition=EquipmentCondition.GOOD,
        )
        db.add(laptop)
        db.add(hotspot)
        await db.commit()

        # List equipment with type filter for LAPTOP
        response = await client.get("/api/v1/equipment?equipment_type=laptop")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Filter should return only laptops
        assert all(item["equipment_type"] == "laptop" for item in data["items"])

    async def test_list_equipment_pagination(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Test pagination when listing equipment."""
        # Create multiple equipment items
        for i in range(5):
            equipment = Equipment(
                name=f"Laptop {i}",
                equipment_type=EquipmentType.LAPTOP,
                serial_number=f"LAP-{i:03d}",
                barcode=f"EQP-LAP-{i:03d}",
                status=EquipmentStatus.AVAILABLE,
                condition=EquipmentCondition.GOOD,
            )
            db.add(equipment)
        await db.commit()

        # List with pagination
        response = await client.get("/api/v1/equipment?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "per_page" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["per_page"] == 2


class TestEquipmentUpdate:
    """Test updating equipment via PATCH /equipment/{id}."""

    async def test_update_equipment_condition(
        self, staff_client: AsyncClient, db: AsyncSession
    ):
        """Test updating equipment condition to GOOD."""
        # Create equipment
        equipment = Equipment(
            name="Dell Latitude 5520",
            equipment_type=EquipmentType.LAPTOP,
            serial_number="DL5520-001",
            barcode="EQP-DL5520-001",
            status=EquipmentStatus.AVAILABLE,
            condition=EquipmentCondition.FAIR,
        )
        db.add(equipment)
        await db.commit()
        await db.refresh(equipment)

        # Update condition to GOOD
        payload = {
            "condition": "good",
        }
        response = await staff_client.patch(
            f"/api/v1/equipment/{equipment.id}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["condition"] == "good"
        assert data["id"] == equipment.id

    async def test_update_equipment_status(
        self, staff_client: AsyncClient, db: AsyncSession
    ):
        """Test updating equipment status."""
        # Create equipment
        equipment = Equipment(
            name="Dell Latitude 5520",
            equipment_type=EquipmentType.LAPTOP,
            serial_number="DL5520-001",
            barcode="EQP-DL5520-001",
            status=EquipmentStatus.AVAILABLE,
            condition=EquipmentCondition.GOOD,
        )
        db.add(equipment)
        await db.commit()
        await db.refresh(equipment)

        # Update status
        payload = {
            "status": "in_maintenance",
        }
        response = await staff_client.patch(
            f"/api/v1/equipment/{equipment.id}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_maintenance"

    async def test_update_equipment_multiple_fields(
        self, staff_client: AsyncClient, db: AsyncSession
    ):
        """Test updating multiple equipment fields."""
        # Create equipment
        equipment = Equipment(
            name="Dell Latitude 5520",
            equipment_type=EquipmentType.LAPTOP,
            serial_number="DL5520-001",
            barcode="EQP-DL5520-001",
            status=EquipmentStatus.AVAILABLE,
            condition=EquipmentCondition.GOOD,
            location="Main Branch",
        )
        db.add(equipment)
        await db.commit()
        await db.refresh(equipment)

        # Update multiple fields
        payload = {
            "condition": "excellent",
            "location": "North Branch",
            "notes": "Recently serviced",
        }
        response = await staff_client.patch(
            f"/api/v1/equipment/{equipment.id}", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["condition"] == "excellent"
        assert data["location"] == "North Branch"
        assert data["notes"] == "Recently serviced"

    async def test_update_nonexistent_equipment(self, staff_client: AsyncClient):
        """Test updating equipment that does not exist."""
        payload = {
            "condition": "good",
        }
        response = await staff_client.patch("/api/v1/equipment/9999", json=payload)
        assert response.status_code == 404


class TestEquipmentIntegration:
    """Integration tests for equipment endpoints."""

    async def test_create_list_update_workflow(
        self, staff_client: AsyncClient, db: AsyncSession
    ):
        """Test complete workflow: create, list, update equipment."""
        # Step 1: Create equipment
        create_payload = {
            "name": "Dell Latitude 5520",
            "equipment_type": "laptop",
            "serial_number": "DL5520-001",
            "barcode": "EQP-DL5520-001",
        }
        create_response = await staff_client.post("/api/v1/equipment", json=create_payload)
        assert create_response.status_code in [201, 200]
        created = create_response.json()
        equipment_id = created["id"]

        # Step 2: List equipment and verify it appears
        list_response = await staff_client.get(
            "/api/v1/equipment?equipment_type=laptop"
        )
        assert list_response.status_code == 200
        list_data = list_response.json()
        equipment_ids = [item["id"] for item in list_data["items"]]
        assert equipment_id in equipment_ids

        # Step 3: Update equipment condition
        update_payload = {
            "condition": "good",
        }
        update_response = await staff_client.patch(
            f"/api/v1/equipment/{equipment_id}", json=update_payload
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["condition"] == "good"
        assert updated["id"] == equipment_id
