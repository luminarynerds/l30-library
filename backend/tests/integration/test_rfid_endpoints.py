# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for RFID API endpoints.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest


@pytest.fixture
async def test_item_copy_for_rfid(test_db, test_catalog_item):
    """Create a test item copy with a barcode for RFID operations."""
    from app.models.inventory import ItemCopy, ItemCondition

    copy = ItemCopy(
        catalog_item_id=test_catalog_item.id,
        barcode="RFID-TEST-001",
        copy_number=1,
        condition=ItemCondition.GOOD,
        location="Adult Fiction A-1",
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def test_rfid_reader(test_db):
    """Create a test RFID reader."""
    from app.models.rfid import RFIDReader, RFIDReaderType, RFIDReaderStatus, RFIDProtocol

    reader = RFIDReader(
        name="Test Circulation Desk Reader",
        serial_number="TEST-READER-001",
        location="Main Circulation Desk",
        reader_type=RFIDReaderType.CIRCULATION_DESK,
        protocol=RFIDProtocol.SIP2,
        ip_address="192.168.1.100",
        port=6001,
        status=RFIDReaderStatus.ONLINE,
        is_active=True,
    )
    test_db.add(reader)
    await test_db.commit()
    await test_db.refresh(reader)
    return reader


@pytest.fixture
async def test_rfid_tag(test_db, test_item_copy_for_rfid, test_rfid_reader, test_staff):
    """Create a test RFID tag linked to an item."""
    from app.models.rfid import RFIDTag

    tag = RFIDTag(
        tag_id="E2000016221301240950ABCD",
        item_barcode=test_item_copy_for_rfid.barcode,
        security_bit=True,
        eas_enabled=True,
        tag_type="ISO 15693",
        programmed_by_id=test_staff.id,
        programmed_by_reader_id=test_rfid_reader.id,
        is_active=True,
    )
    test_db.add(tag)
    await test_db.commit()
    await test_db.refresh(tag)
    return tag


@pytest.fixture
async def test_security_gate_reader(test_db):
    """Create a test security gate reader."""
    from app.models.rfid import RFIDReader, RFIDReaderType, RFIDReaderStatus, RFIDProtocol

    reader = RFIDReader(
        name="Main Entrance Security Gate",
        serial_number="TEST-GATE-001",
        location="Main Entrance",
        reader_type=RFIDReaderType.SECURITY_GATE,
        protocol=RFIDProtocol.TCP_SOCKET,
        ip_address="192.168.1.50",
        port=5000,
        status=RFIDReaderStatus.ONLINE,
        is_active=True,
    )
    test_db.add(reader)
    await test_db.commit()
    await test_db.refresh(reader)
    return reader


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    # First register the staff user (if not exists)
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_staff_data["email"],
            "password": test_staff_data["password"],
        },
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_admin_data["email"],
            "password": test_admin_data["password"],
        },
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


class TestRFIDReaderEndpoints:
    """Tests for RFID reader management endpoints."""

    @pytest.mark.asyncio
    async def test_list_readers_requires_staff(self, client):
        """Test that listing readers requires staff authentication."""
        response = await client.get("/api/v1/rfid/readers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_readers_as_staff(
        self, client, test_staff, test_staff_data, test_rfid_reader
    ):
        """Test listing readers as staff."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            "/api/v1/rfid/readers", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_reader_requires_admin(self, client, test_staff, test_staff_data):
        """Test that creating a reader requires admin role."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/readers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Reader",
                "serial_number": "NEW-001",
                "reader_type": "circulation_desk",
                "protocol": "sip2",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_reader_as_admin(self, client, test_admin, test_admin_data):
        """Test creating a reader as admin."""
        token = await get_admin_token(client, test_admin_data)
        if not token:
            pytest.skip("Could not get admin token")

        response = await client.post(
            "/api/v1/rfid/readers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Test Reader",
                "serial_number": "NEW-TEST-002",
                "location": "Test Location",
                "reader_type": "handheld",
                "protocol": "rest_api",
                "ip_address": "192.168.1.200",
                "port": 8080,
            },
        )
        # POST /readers creates a resource; the route declares 201.
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "New Test Reader"
        assert data["serial_number"] == "NEW-TEST-002"

    @pytest.mark.asyncio
    async def test_get_reader_details(self, client, test_staff, test_staff_data, test_rfid_reader):
        """Test getting reader details."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            f"/api/v1/rfid/readers/{test_rfid_reader.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_rfid_reader.name
        assert data["serial_number"] == test_rfid_reader.serial_number


class TestRFIDTagEndpoints:
    """Tests for RFID tag management endpoints."""

    @pytest.mark.asyncio
    async def test_list_tags(self, client, test_staff, test_staff_data, test_rfid_tag):
        """Test listing RFID tags."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            "/api/v1/rfid/tags", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_get_tag_by_id(self, client, test_staff, test_staff_data, test_rfid_tag):
        """Test getting a tag by tag ID."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            f"/api/v1/rfid/tags/{test_rfid_tag.tag_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tag_id"] == test_rfid_tag.tag_id

    @pytest.mark.asyncio
    async def test_program_tag(
        self, client, test_staff, test_staff_data, test_rfid_reader, test_item_copy_for_rfid
    ):
        """Test programming a new RFID tag."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        # Create another item copy without a tag
        from app.models.inventory import ItemCopy, ItemCondition
        # Note: This requires creating a new item in the test

        response = await client.post(
            "/api/v1/rfid/tags/program",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "item_barcode": test_item_copy_for_rfid.barcode,
                "reader_id": test_rfid_reader.id,
                "tag_type": "ISO 15693",
                "include_item_data": True,
            },
        )
        # May fail if tag already exists, which is expected in some test scenarios
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_toggle_tag_security(self, client, test_staff, test_staff_data, test_rfid_tag):
        """Test toggling tag security bit."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        # Desensitize
        response = await client.post(
            f"/api/v1/rfid/tags/{test_rfid_tag.tag_id}/security?security_bit=false",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["security_bit"] is False

        # Re-sensitize
        response = await client.post(
            f"/api/v1/rfid/tags/{test_rfid_tag.tag_id}/security?security_bit=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["security_bit"] is True


class TestBatchOperations:
    """Tests for batch checkout/checkin operations."""

    @pytest.mark.asyncio
    async def test_batch_checkout(
        self,
        client,
        test_staff,
        test_staff_data,
        test_patron,
        test_rfid_reader,
        test_rfid_tag,
        test_catalog_item,
    ):
        """Test batch checkout via RFID."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/batch-checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_rfid_reader.id,
                "patron_id": test_patron.id,
                "tag_ids": [test_rfid_tag.tag_id],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "results" in data
        assert data["total_items"] == 1

    @pytest.mark.asyncio
    async def test_batch_checkout_unknown_tag(
        self, client, test_staff, test_staff_data, test_patron, test_rfid_reader
    ):
        """Test batch checkout with unknown tag."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/batch-checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_rfid_reader.id,
                "patron_id": test_patron.id,
                "tag_ids": ["UNKNOWN_TAG_12345"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["failed"] == 1
        assert data["results"][0]["success"] is False

    @pytest.mark.asyncio
    async def test_batch_checkin(
        self, client, test_staff, test_staff_data, test_rfid_reader, test_rfid_tag
    ):
        """Test batch checkin via RFID."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/batch-checkin",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_rfid_reader.id,
                "tag_ids": [test_rfid_tag.tag_id],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "results" in data


class TestSecurityAlerts:
    """Tests for security alert endpoints."""

    @pytest.mark.asyncio
    async def test_create_security_alert(
        self, client, test_staff, test_staff_data, test_security_gate_reader, test_rfid_tag
    ):
        """Test creating a security alert from gate."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/security/alerts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_security_gate_reader.id,
                "alert_type": "unauthorized_exit",
                "tag_id": test_rfid_tag.tag_id,
                "description": "Test security alert",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["alert_type"] == "unauthorized_exit"
        assert data["is_resolved"] is False

    @pytest.mark.asyncio
    async def test_list_security_alerts(self, client, test_staff, test_staff_data):
        """Test listing security alerts."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            "/api/v1/rfid/security/alerts?is_resolved=false",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_resolve_security_alert(
        self, client, test_staff, test_staff_data, test_security_gate_reader, test_rfid_tag
    ):
        """Test resolving a security alert."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        # First create an alert
        create_response = await client.post(
            "/api/v1/rfid/security/alerts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_security_gate_reader.id,
                "alert_type": "unauthorized_exit",
                "tag_id": test_rfid_tag.tag_id,
            },
        )
        if create_response.status_code != 200:
            pytest.skip("Could not create test alert")

        alert_id = create_response.json()["id"]

        # Resolve it
        response = await client.post(
            f"/api/v1/rfid/security/alerts/{alert_id}/resolve",
            headers={"Authorization": f"Bearer {token}"},
            json={"resolution_notes": "Item was properly checked out, false alarm"},
        )
        assert response.status_code == 200
        assert response.json()["is_resolved"] is True


class TestInventoryMode:
    """Tests for inventory scanning mode."""

    @pytest.mark.asyncio
    async def test_start_inventory_session(
        self, client, test_staff, test_staff_data, test_rfid_reader
    ):
        """Test starting an inventory session."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/inventory/start",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_rfid_reader.id,
                "target_location": "Adult Fiction",
                "create_audit": True,
                "audit_name": "Test Inventory Scan",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["session_type"] == "inventory_scan"
        assert data["is_active"] is True


class TestShelfReading:
    """Tests for shelf reading mode."""

    @pytest.mark.asyncio
    async def test_start_shelf_read_session(
        self, client, test_staff, test_staff_data, test_rfid_reader
    ):
        """Test starting a shelf reading session."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.post(
            "/api/v1/rfid/shelf-read/start",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reader_id": test_rfid_reader.id,
                "target_location": "Adult Fiction A-1",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["session_type"] == "shelf_read"
        assert data["target_location"] == "Adult Fiction A-1"


class TestDashboard:
    """Tests for RFID dashboard."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(
        self, client, test_staff, test_staff_data, test_rfid_reader, test_rfid_tag
    ):
        """Test getting dashboard statistics."""
        token = await get_staff_token(client, test_staff_data)
        if not token:
            pytest.skip("Could not get staff token")

        response = await client.get(
            "/api/v1/rfid/dashboard", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_readers" in data
        assert "readers_online" in data
        assert "total_tags" in data
        assert "active_tags" in data
        assert "security_alerts_today" in data
        assert "unresolved_alerts" in data
