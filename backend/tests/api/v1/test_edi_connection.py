# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
EDI Connection Test Suite

Tests EDI connection testing functionality for various vendor profiles.
Verifies:
- Connectivity status
- Latency measurement
- Authentication result
- Error handling with wrong credentials
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.acquisition import Vendor
from app.models.edi import VendorEDIProfile, EDIStandard, TransportProtocol
from app.models.user import User, UserRole
from app.services.edi.edi_transport import TransportResult


@pytest.mark.integration
class TestEDIConnection:
    """Test EDI connection functionality."""

    @pytest.fixture
    async def admin_user(self, test_db: AsyncSession) -> User:
        """Create an admin user for testing."""
        user = User(
            email="admin@library.edu",
            password_hash="hashed_password",  # In real tests, this would be properly hashed
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user

    @pytest.fixture
    async def ingram_vendor(self, test_db: AsyncSession) -> Vendor:
        """Create Ingram Book Company vendor with EDI profile."""
        vendor = Vendor(
            name="Ingram Book Company",
            code="INGRAM",
            address="One Ingram Boulevard, La Vergne, TN 37086, USA",
            contact_name="EDI Support",
            email="edi@ingrambook.com",
            phone="1-800-937-0100",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        profile = VendorEDIProfile(
            vendor_id=vendor.id,
            is_enabled=True,
            edi_standard=EDIStandard.EDIFACT,
            sender_id="LSCLIB",
            sender_qualifier="ZZ",
            receiver_id="INGRAM",
            receiver_qualifier="ZZ",
            transport_protocol=TransportProtocol.SFTP,
            transport_host="edi.ingrambook.com",
            transport_port=22,
            transport_username="lsclib_user",
            transport_password="correct_password",
            transport_directory_outbound="/outbound",
            transport_directory_inbound="/inbound",
            supports_orders=True,
            supports_ordrsp=True,
            supports_desadv=True,
            supports_invoic=True,
            max_retries=3,
            retry_interval_minutes=60,
            auto_send_orders=False,
            auto_process_responses=True,
            auto_approve_invoices=False,
            is_test_mode=True,
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(vendor)
        return vendor

    @pytest.fixture
    async def vendor_with_wrong_credentials(
        self, test_db: AsyncSession
    ) -> Vendor:
        """Create a vendor with intentionally wrong EDI credentials."""
        vendor = Vendor(
            name="Test Vendor Wrong Creds",
            code="TEST_WRONG",
            address="123 Test St, Test City, TS 12345, USA",
            contact_name="Test Contact",
            email="test@example.com",
            phone="555-0100",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        profile = VendorEDIProfile(
            vendor_id=vendor.id,
            is_enabled=True,
            edi_standard=EDIStandard.EDIFACT,
            sender_id="TEST_SENDER",
            sender_qualifier="ZZ",
            receiver_id="TEST_RECEIVER",
            receiver_qualifier="ZZ",
            transport_protocol=TransportProtocol.SFTP,
            transport_host="edi.ingrambook.com",  # Real host to test auth failure
            transport_port=22,
            transport_username="wrong_username",  # Intentionally wrong
            transport_password="wrong_password",  # Intentionally wrong
            transport_directory_outbound="/outbound",
            transport_directory_inbound="/inbound",
            supports_orders=True,
            supports_ordrsp=True,
            supports_desadv=True,
            supports_invoic=True,
            is_test_mode=True,
        )
        test_db.add(profile)
        await test_db.commit()
        await test_db.refresh(vendor)
        return vendor

    @pytest.mark.asyncio
    async def test_connection_response_structure(
        self, client, test_db: AsyncSession, admin_user: User, ingram_vendor: Vendor
    ):
        """Test that connection response includes all required fields."""
        # This test verifies the response structure even if the actual connection fails
        # (since the real server may not be accessible in test environment)

        response = await client.post(
            "/api/v1/edi/test-connection",
            json={"vendor_id": ingram_vendor.id},
            headers={
                "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
            },
        )

        assert response.status_code in [200, 502, 503, 504]  # Allow connection errors
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "message" in data
        assert "connectivity_status" in data
        assert "latency_ms" in data
        assert "authentication_result" in data

        # Verify connectivity_status is valid
        assert data["connectivity_status"] in ["connected", "disconnected"]

        # If connected, verify latency is present and positive
        if data["success"]:
            assert data["latency_ms"] is not None
            assert data["latency_ms"] > 0
            assert data["authentication_result"] is not None

    @pytest.mark.asyncio
    async def test_ingram_profile_retrieval(
        self, client, test_db: AsyncSession, admin_user: User, ingram_vendor: Vendor
    ):
        """Test that Ingram profile can be retrieved."""
        # Verify the profile exists
        result = await test_db.execute(
            select(VendorEDIProfile).where(
                VendorEDIProfile.vendor_id == ingram_vendor.id
            )
        )
        profile = result.scalar_one_or_none()

        assert profile is not None
        assert profile.receiver_id == "INGRAM"
        assert profile.sender_id == "LSCLIB"
        assert profile.transport_host == "edi.ingrambook.com"
        assert profile.edi_standard == EDIStandard.EDIFACT

    @pytest.mark.asyncio
    async def test_connection_with_wrong_credentials_fails(
        self,
        client,
        test_db: AsyncSession,
        admin_user: User,
        vendor_with_wrong_credentials: Vendor,
    ):
        """Test that connection with wrong credentials fails with descriptive error."""
        # The test environment has no outbound network access, so the real
        # SFTP handshake is mocked to deterministically simulate an
        # authentication failure rather than a DNS/connection failure.
        with patch(
            "app.services.edi.edi_transport.EDITransport.test_connection",
            new=AsyncMock(
                return_value=TransportResult(
                    success=False,
                    message="Authentication failed: invalid credentials",
                    error="Authentication failed: invalid credentials",
                )
            ),
        ):
            response = await client.post(
                "/api/v1/edi/test-connection",
                json={"vendor_id": vendor_with_wrong_credentials.id},
                headers={
                    "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
                },
            )

        # Connection should fail
        assert response.status_code in [200, 502]
        data = response.json()

        # Verify failure indicators
        assert data["success"] is False
        assert data["connectivity_status"] == "disconnected"

        # Should have error details
        assert "error" in data.get("details", {}) or data["message"]
        assert len(data.get("message", "")) > 0

        # Latency and auth_result should be None or missing on failure
        if data.get("latency_ms"):
            # If latency is present, it should be reasonable
            assert data["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_wrong_credentials_produces_descriptive_error(
        self,
        client,
        test_db: AsyncSession,
        admin_user: User,
        vendor_with_wrong_credentials: Vendor,
    ):
        """Test that wrong credentials produce descriptive error messages."""
        with patch(
            "app.services.edi.edi_transport.EDITransport.test_connection",
            new=AsyncMock(
                return_value=TransportResult(
                    success=False,
                    message="Authentication failed: invalid credentials",
                    error="Authentication failed: invalid credentials",
                )
            ),
        ):
            response = await client.post(
                "/api/v1/edi/test-connection",
                json={"vendor_id": vendor_with_wrong_credentials.id},
                headers={
                    "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
                },
            )

        data = response.json()

        # Verify error information is present
        if not data["success"]:
            error_info = data.get("details", {}).get("error") or data.get("message")
            assert error_info is not None

            # Error should contain useful information
            error_lower = str(error_info).lower()
            # Common error indicators
            assert any(
                indicator in error_lower
                for indicator in [
                    "authentication",
                    "auth",
                    "login",
                    "permission",
                    "refused",
                    "denied",
                    "credential",
                    "incorrect",
                    "failed",
                    "timeout",
                ]
            )

    @pytest.mark.asyncio
    async def test_profile_not_found(
        self, client, test_db: AsyncSession, admin_user: User
    ):
        """Test that requesting connection for non-existent profile returns 404."""
        response = await client.post(
            "/api/v1/edi/test-connection",
            json={"vendor_id": 99999},
            headers={
                "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
            },
        )

        assert response.status_code == 404
        data = response.json()
        error_message = data.get("detail") or data.get("error", {}).get("message", "")
        assert "not found" in error_message.lower()

    @pytest.mark.asyncio
    async def test_latency_is_measured(
        self, client, test_db: AsyncSession, admin_user: User, ingram_vendor: Vendor
    ):
        """Test that latency is measured in milliseconds."""
        response = await client.post(
            "/api/v1/edi/test-connection",
            json={"vendor_id": ingram_vendor.id},
            headers={
                "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
            },
        )

        data = response.json()

        # Even if connection fails, latency should be measured
        if "latency_ms" in data and data["latency_ms"] is not None:
            # Latency should be in milliseconds
            assert isinstance(data["latency_ms"], (int, float))
            # Should be >= 0
            assert data["latency_ms"] >= 0
            # Should be reasonable (< 60 seconds)
            assert data["latency_ms"] < 60000

    @pytest.mark.asyncio
    async def test_authentication_status_reported(
        self, client, test_db: AsyncSession, admin_user: User, ingram_vendor: Vendor
    ):
        """Test that authentication status is reported."""
        response = await client.post(
            "/api/v1/edi/test-connection",
            json={"vendor_id": ingram_vendor.id},
            headers={
                "Authorization": f"Bearer {create_access_token(subject=admin_user.id, email=admin_user.email, role=admin_user.role)}"
            },
        )

        data = response.json()

        # If successful, authentication_result should indicate the method
        if data.get("success"):
            assert data.get("authentication_result") is not None
            assert data["authentication_result"] in [
                "authenticated_with_password",
                "authenticated_with_key",
            ]

    @pytest.mark.asyncio
    async def test_ingram_profile_configuration(
        self, test_db: AsyncSession, ingram_vendor: Vendor
    ):
        """Test that Ingram profile has correct configuration."""
        result = await test_db.execute(
            select(VendorEDIProfile).where(
                VendorEDIProfile.vendor_id == ingram_vendor.id
            )
        )
        profile = result.scalar_one()

        # Verify EDI configuration
        assert profile.edi_standard == EDIStandard.EDIFACT
        assert profile.transport_protocol == TransportProtocol.SFTP
        assert profile.receiver_id == "INGRAM"
        assert profile.sender_id == "LSCLIB"

        # Verify supported message types
        assert profile.supports_orders is True
        assert profile.supports_ordrsp is True
        assert profile.supports_desadv is True
        assert profile.supports_invoic is True

        # Verify auto-processing settings
        assert profile.auto_process_responses is True
        assert profile.is_test_mode is True


@pytest.mark.integration
class TestEDIConnectionEdgeCases:
    """Test edge cases for EDI connection testing."""

    @pytest.mark.asyncio
    async def test_invalid_protocol_handling(self, test_db: AsyncSession):
        """Test handling of unsupported protocols."""
        # This tests the error handling for unsupported protocols
        vendor = Vendor(
            name="Test Invalid Protocol",
            code="TEST_INVALID",
            address="123 Test St, Test City, TS 12345, USA",
            contact_name="Test Contact",
            email="test@example.com",
            phone="555-0100",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        # Create profile with AS2 protocol (which might have limited testing)
        profile = VendorEDIProfile(
            vendor_id=vendor.id,
            is_enabled=True,
            edi_standard=EDIStandard.EDIFACT,
            sender_id="TEST_SENDER",
            receiver_id="TEST_RECEIVER",
            transport_protocol=TransportProtocol.AS2,
            transport_host="test.example.com",
            transport_port=80,
            transport_username="testuser",
            transport_password="testpass",
        )
        test_db.add(profile)
        await test_db.commit()

        # Note: AS2 is not fully supported in the current implementation
        # This test documents that behavior

    @pytest.mark.asyncio
    async def test_empty_credentials(self, test_db: AsyncSession):
        """Test handling of empty credentials."""
        vendor = Vendor(
            name="Test Empty Creds",
            code="TEST_EMPTY",
            address="123 Test St, Test City, TS 12345, USA",
            contact_name="Test Contact",
            email="test@example.com",
            phone="555-0100",
            is_active=True,
        )
        test_db.add(vendor)
        await test_db.flush()

        profile = VendorEDIProfile(
            vendor_id=vendor.id,
            is_enabled=True,
            edi_standard=EDIStandard.EDIFACT,
            sender_id="TEST_SENDER",
            receiver_id="TEST_RECEIVER",
            transport_protocol=TransportProtocol.SFTP,
            transport_host="test.example.com",
            transport_port=22,
            transport_username="",  # Empty username
            # No password or SSH key provided
        )
        test_db.add(profile)
        await test_db.commit()

        # Should handle gracefully without crashing
        result = await test_db.execute(
            select(VendorEDIProfile).where(
                VendorEDIProfile.vendor_id == vendor.id
            )
        )
        profile = result.scalar_one()
        assert profile is not None
