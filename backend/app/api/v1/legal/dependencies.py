# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared dependencies for legal API routers.

This module exports authentication and authorization dependencies
used across all legal resource endpoints.
"""

# Re-export from parent API dependencies
from ..dependencies import get_current_user, get_current_user_optional

__all__ = [
    "get_current_user",
    "get_current_user_optional",
]
