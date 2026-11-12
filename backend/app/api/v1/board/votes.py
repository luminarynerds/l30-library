# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board voting API endpoints - vote management, casting, and tally.

This module re-exports the voting router from voting.py which contains
the canonical vote management endpoints. The votes.py name is provided
as an alias for clearer domain grouping.
"""

# Re-export from the canonical voting module
from .voting import router

__all__ = ["router"]
