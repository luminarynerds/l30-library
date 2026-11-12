# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive mocking fixtures for external library services.

This module provides pytest fixtures that mock HTTP interactions with:
- Z3950/MARC copy cataloging services
- Email services and other external APIs

Each fixture intercepts httpx calls and returns realistic mock responses.
"""

import json
import base64
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


# =============================================================================
# Z3950 Service Mocks
# =============================================================================

class MockZ3950Responses:
    """Mock responses for Z3950 copy cataloging."""

    @staticmethod
    def marc_record_by_isbn(isbn: str) -> Dict[str, Any]:
        """Mock MARC record response from Z3950 search."""
        return {
            "title": f"Book with ISBN {isbn}",
            "author": "Test Author",
            "isbn": isbn.replace("-", ""),
            "publisher": "Test Publisher",
            "publication_year": 2024,
            "call_number": "813.54 TEST",
            "dewey_decimal": "813.54",
            "subjects": ["Fiction", "Test Subject"],
        }


@pytest.fixture
def mock_z3950_service():
    """
    Mock Z3950 service for copy cataloging.

    Returns a fixture that patches the Z3950Service to return mock MARC records
    without attempting real network connections.
    """
    with patch("app.services.z3950_service.Z3950Service") as mock_service_class:
        mock_instance = AsyncMock()
        mock_service_class.return_value = mock_instance

        # Mock search methods
        async def mock_search_by_isbn(isbn: str, source: str = "loc", **kwargs):
            """Mock ISBN search."""
            return [MockZ3950Responses.marc_record_by_isbn(isbn)]

        async def mock_search_by_title(title: str, source: str = "loc", **kwargs):
            """Mock title search."""
            return [
                {
                    "title": title,
                    "author": "Test Author",
                    "isbn": "9780123456789",
                    "publisher": "Test Publisher",
                    "publication_year": 2024,
                }
            ]

        async def mock_search_by_author(author: str, source: str = "loc", **kwargs):
            """Mock author search."""
            return [
                {
                    "title": "Book by Author",
                    "author": author,
                    "isbn": "9780987654321",
                    "publisher": "Test Publisher",
                    "publication_year": 2024,
                }
            ]

        mock_instance.search_by_isbn = mock_search_by_isbn
        mock_instance.search_by_title = mock_search_by_title
        mock_instance.search_by_author = mock_search_by_author
        mock_instance.available = True
        mock_instance.is_configured = True
        mock_instance.get_available_sources = MagicMock(return_value=["loc", "oclc"])
        mock_instance.get_source_config = MagicMock(
            return_value={
                "name": "Library of Congress",
                "host": "lx2.loc.gov",
                "port": 210,
                "database": "LCDB",
            }
        )

        yield mock_instance


# =============================================================================
# Email Service Mocks
# =============================================================================

@pytest.fixture
def mock_email_service():
    """
    Mock email service to prevent real emails from being sent during tests.

    Captures email data that would be sent and stores it for verification.
    """
    sent_emails = []

    async def mock_send_email(
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Mock email sending."""
        sent_emails.append({
            "to": to,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "timestamp": datetime.now(timezone.utc),
        })
        return True

    with patch("app.core.email.send_email", side_effect=mock_send_email):
        # Expose sent_emails through the fixture for assertions
        mock_send_email.sent_emails = sent_emails
        yield mock_send_email


# =============================================================================
# SMS Service Mocks
# =============================================================================

@pytest.fixture
def mock_sms_service():
    """
    Mock SMS service to prevent real SMS messages during tests.
    """
    sent_messages = []

    async def mock_send_sms(phone: str, message: str, **kwargs) -> bool:
        """Mock SMS sending."""
        sent_messages.append({
            "phone": phone,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
        })
        return True

    with patch("app.core.sms.send_sms", side_effect=mock_send_sms):
        mock_send_sms.sent_messages = sent_messages
        yield mock_send_sms


# =============================================================================
# Composite Fixture: All External Services
# =============================================================================

@pytest.fixture
def mock_all_external_services(
    mock_z3950_service,
    mock_email_service,
    mock_sms_service,
):
    """
    Composite fixture that mocks all external services at once.

    Use this when a test needs to interact with multiple external services
    without making real network calls.
    """
    return {
        "z3950": mock_z3950_service,
        "email": mock_email_service,
        "sms": mock_sms_service,
    }
