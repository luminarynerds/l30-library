# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local conftest for legal API tests.

Ensures legal routers are registered before tests run,
since the FastAPI startup event may not fire in test mode.
"""

import pytest
from httpx import AsyncClient, ASGITransport

# register_all_routers(app) has no idempotency guard -- every call does ~390
# app.include_router(...) calls against the module-level `app` singleton.
# This fixture used to call it on every single test, so by test N the ASGI
# app carried N x 390 duplicate routes. Starlette matches an incoming
# request by scanning app.router.routes in order, so per-request routing
# cost grew with accumulated route count across the file -- a real O(n^2)
# blowup over a test session that eventually exceeds any external timeout
# (looks exactly like a "hang" from outside, no DB/redis involved at all).
# Register once per process and reuse.
_legal_routers_registered = False


@pytest.fixture
async def client(test_db):
    """Create test client with legal routers explicitly registered.

    Overrides the global client fixture to ensure register_all_routers
    is called, since FastAPI's on_event("startup") may not fire
    during ASGI transport-based testing.
    """
    global _legal_routers_registered
    from app.core.database import get_db
    from app.main import app
    from app.api.v1.registry import register_all_routers

    # Ensure all routers (including legal) are registered -- exactly once.
    if not _legal_routers_registered:
        register_all_routers(app)
        _legal_routers_registered = True

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Bypass FirstBootMiddleware: tests use an empty DB with no admin users,
    # which would otherwise trip the setup-required check on every request
    # (503 SETUP_REQUIRED) via a DB session that isn't even the overridden
    # test_db -- it's a fresh connection off app.core.database's production
    # pooled engine (FirstBootMiddleware runs outside FastAPI's DI, so the
    # get_db override above doesn't reach it). Matches the global `client`
    # fixture in tests/conftest.py, which this local fixture otherwise
    # duplicates.
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client
    finally:
        try:
            app.dependency_overrides.clear()
        except Exception:
            pass
