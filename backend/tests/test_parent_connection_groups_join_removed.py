# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression guard: the deprecated `/connection-groups/{id}/join` route
must NOT be registered on the FastAPI app.

That route let any authenticated patron self-join a connection group,
bypassing the approval queue that backs confidential-group privacy.
Replaced by:
  - POST /connection-groups/{id}/enroll          (staff-mediated)
  - POST /connection-groups/{id}/request         (patron-initiated, approval-gated)

If this test fails, confidentiality is broken and the route must be removed
before the change ships.

We assert against `app.routes` rather than firing an HTTP request: the L30
app boots with FirstBootMiddleware that touches the `users` table on every
request, so an AsyncClient + sqlite test would fail on a setup issue instead
of on the assertion this test is meant to make.
"""
from app.main import app


_DEPRECATED_PATH = "/api/v1/parent-onboarding/connection-groups/{group_id}/join"


def test_deprecated_join_route_not_registered():
    """The deprecated /join route must not be on the FastAPI app."""
    paths = {getattr(r, "path", None) for r in app.routes}
    assert _DEPRECATED_PATH not in paths, (
        f"Confidentiality-bypass route still registered: {_DEPRECATED_PATH}. "
        "Use /enroll (staff-mediated) or /request (patron-initiated, approval-gated)."
    )


def test_replacement_routes_present():
    """Sibling guard: the replacement endpoints must still exist, so the
    above check doesn't silently pass after a sweeping refactor that yanks
    everything in the file.
    """
    paths = {getattr(r, "path", None) for r in app.routes}
    assert (
        "/api/v1/parent-onboarding/connection-groups/{group_id}/enroll" in paths
    ), "Replacement /enroll route missing"
    assert (
        "/api/v1/parent-onboarding/connection-groups/{group_id}/request" in paths
    ), "Replacement /request route missing"
