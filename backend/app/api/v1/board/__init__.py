# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Board API sub-routers
from . import (
    action_items,
    attendance,
    committees,
    documents,
    main,
    meetings,
    members,
    minutes,
    motions,
    notices,
    pdf_exports,
    public_comments,
    reports,
    votes,
    voting,
)

# Expose main router for backward compatibility
router = main.router

__all__ = [
    "router",
    "action_items",
    "attendance",
    "committees",
    "documents",
    "main",
    "meetings",
    "members",
    "minutes",
    "motions",
    "notices",
    "pdf_exports",
    "public_comments",
    "reports",
    "votes",
    "voting",
]
