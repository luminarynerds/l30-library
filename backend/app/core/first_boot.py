# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.services.setup_service import is_setup_required

ALLOWED_PREFIXES = (
    "/api/v1/setup",
    "/api/v1/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class FirstBootMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Demo public mode: always allow traffic through
        settings = get_settings()
        if settings.demo_public:
            return await call_next(request)

        # Fast path: once setup is complete, skip all DB checks
        if getattr(request.app.state, "setup_complete", False):
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            return await call_next(request)

        async with async_session_maker() as db:
            setup_needed = await is_setup_required(db)

        if setup_needed:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Setup required. Please complete first-boot setup.",
                    "code": "SETUP_REQUIRED",
                },
            )

        # Setup is done -- cache it so we never query again
        request.app.state.setup_complete = True
        return await call_next(request)
