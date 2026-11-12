# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Acquisition API sub-routers
from . import external, intelligence, main, po, selection, templates, vendors

# Expose main router for backward compatibility
# Usage: acquisition.router (as before) OR acquisition.main.router (new structure)
router = main.router

__all__ = [
    "router",  # Main router for FastAPI include_router
    "external",
    "intelligence",
    "main",
    "po",
    "selection",
    "templates",
    "vendors",
]
