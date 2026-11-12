# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strategic Planning API module.

This package organizes strategic planning endpoints into domain-specific
modules for better maintainability and team scalability.

Module structure:
- collaboration.py - Comments and notifications (merged from comments + notifications)
- attachments.py - File attachment upload, listing, deletion
- initiatives.py - Initiative CRUD, milestones, board decisions
- kpis.py        - KPI CRUD, values, alerts
- common.py      - Shared auth helpers (require_staff, require_admin)

plans.py, goals.py, milestones.py, templates.py, and analytics.py were
removed 2026-07-10: they duplicated the legacy strategic_{plans,goals,
milestones,admin,board}.py flat modules at identical (method, path)
pairs, and those flat modules register first in registry.py, so the
package versions never served live traffic.

Each remaining submodule is registered directly in registry.py
(app.api.v1.strategic.<name>) rather than through this package's
__init__ -- no aggregate router is built here.
"""
