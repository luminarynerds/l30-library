# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test fixtures package for LSC backend.

This package contains pytest fixtures used across all tests to:
- Set up test databases
- Create mock users and data
- Mock external service integrations
"""

from .external_services import (
    mock_z3950_service,
    mock_email_service,
    mock_sms_service,
    mock_all_external_services,
)

__all__ = [
    "mock_z3950_service",
    "mock_email_service",
    "mock_sms_service",
    "mock_all_external_services",
]
