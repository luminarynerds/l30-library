# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.config import get_settings
from .core.branding import branding
from .core.exceptions import APIError
from .core.rate_limit import limiter
from .core.cache import get_redis
from .middleware.rate_limit_middleware import CategoryRateLimitMiddleware
from .core.logging import setup_logging, get_logger
from .core.monitoring import setup_sentry
from .services.schedulers.main import init_scheduler
from starlette.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from .middleware.logging_middleware import RequestLoggingMiddleware
from .middleware.performance_middleware import PerformanceMiddleware
from .middleware.query_counter import QueryCounterMiddleware, install_query_counter_hook
from .middleware.caching_headers import CachingHeadersMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .api.v1.registry import register_all_routers
from fastapi.staticfiles import StaticFiles
import mimetypes

# Register modern image mime types missing from Python defaults (text/plain otherwise)
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")

# Initialize logging and monitoring
setup_logging()
setup_sentry()
logger = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title=branding.API_TITLE,
    description=branding.API_DESCRIPTION,
    version="0.1.0",
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def api_error_handler(request: Request, exc: APIError):
    content = {"detail": exc.message, "code": exc.code.value if exc.code else None}
    if exc.details:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code or 500, content=content)


app.add_exception_handler(APIError, api_error_handler)

# Register HTTP and validation exception handlers for consistent JSON responses
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.core.exception_handlers import http_exception_handler, validation_exception_handler
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Request/response logging middleware (add before CORS for proper execution order)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMiddleware)
app.add_middleware(QueryCounterMiddleware, threshold=8, debug=settings.debug)
app.add_middleware(CachingHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-Request-ID"],
)

# Trusted host validation (prevents host header attacks).
#
# Exempts /health and /api/v1/health from the Host check because:
#   1. Docker/orchestrator health probes legitimately arrive with
#      Host: backend:8000 (the compose service name) or other internal
#      aliases that we don't enumerate in TRUSTED_HOSTS.
#   2. Sibling Docker stacks co-attached on shared networks
#      (e.g. metislib_default) resolve `backend` DNS to *this* container
#      and probe its /health, producing a flood of 400s in logs.
#   3. The health endpoints return no Host-derived content, so the Host
#      check there is pure deployment friction.
class _HealthExemptTrustedHost(TrustedHostMiddleware):

    _EXEMPT_PATHS = frozenset({"/health", "/api/v1/health"})

    async def __call__(self, scope, receive, send):  # type: ignore[override]
        if scope.get("type") == "http" and scope.get("path") in self._EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


_trusted = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
if _trusted and _trusted != ["*"]:
    app.add_middleware(_HealthExemptTrustedHost, allowed_hosts=_trusted)

# Proxy headers: trust X-Forwarded-Proto so redirects use https
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

from .core.first_boot import FirstBootMiddleware
app.add_middleware(FirstBootMiddleware)

# Category-based rate limiting. Stage 0: RATE_LIMIT_OBSERVE_ONLY defaults
# True -> classify + log would_block, enforce NOTHING. Set it false ONLY
# to actually throttle (staged rollout per rate-limiting-tiered-policy spec).
app.add_middleware(
    CategoryRateLimitMiddleware,
    redis_getter=get_redis,
    enabled=settings.rate_limit_enabled,
)

# Security headers (CSP, HSTS, Permissions-Policy, sensitive-endpoint cache control).
# Registered LAST so it is outermost in the Starlette stack and stamps headers on
# every response, including errors raised by inner middleware.
# Note: nginx currently also sets CSP/Permissions-Policy with `always`, which wins
# for traffic egressing through the edge. This middleware is the source of truth
# for direct-to-backend traffic and a defense-in-depth layer; nginx header scrub
# is a separate followup so there is a single source of truth.
app.add_middleware(SecurityHeadersMiddleware)

# =====================================================================
# Router registration — delegated to registry.py (single source of truth)
# =====================================================================
register_all_routers(app, debug=settings.debug)

# Serve uploaded media (blog images)
import os
_uploads_dir = os.getenv("STORAGE_LOCAL_PATH", "/app/uploads")
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")


@app.on_event("startup")
async def startup_event():
    logger.info(f"{branding.library_name} API starting up", extra={
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
    })

    from .core.database import engine
    install_query_counter_hook(engine)

    from .core.lazy_load_guard import install_lazy_load_guard
    install_lazy_load_guard()

    # Validate and log PII encryption configuration
    _validate_pii_encryption_startup()

    # Warn loudly if bot/CAPTCHA protection is off in production
    _validate_turnstile_startup()

    try:
        init_scheduler()
    except Exception as e:  # noqa: BLE001  # startup must not crash on scheduler failure
        logger.error(f"Failed to start scheduler: {e}")

    try:
        from .services import floor_view_bus
        floor_view_bus.start_subscriber()
    except Exception as e:  # noqa: BLE001  # startup must not crash on subscriber failure
        logger.error(f"Failed to start floor-view bus subscriber: {e}")


def _validate_pii_encryption_startup() -> None:
    from .core.encryption import get_decryption_health

    try:
        health = get_decryption_health()
        encryption_status = "ENABLED" if health.get("encryption_enabled") else "DISABLED"

        logger.info(
            f"PII encryption: {encryption_status}",
            extra={
                "encryption_enabled": health.get("encryption_enabled", False),
                "previous_key_configured": health.get("previous_key_configured", False),
                "fallback_decryptions": health.get("fallback_decryptions", 0),
                "failed_decryptions": health.get("failed_decryptions", 0),
            }
        )

        # Log warning if key rotation is in progress
        if health.get("previous_key_configured"):
            logger.warning(
                "PII encryption key rotation detected. "
                "Please run the re-encryption migration to update all records: "
                "python scripts/reencrypt_pii.py",
                extra={
                    "fallback_count": health.get("fallback_decryptions", 0),
                }
            )
    except Exception as e:
        logger.error(f"Failed to validate PII encryption configuration: {e}", exc_info=True)


def _validate_turnstile_startup() -> None:
    current_settings = get_settings()

    if current_settings.environment == "production" and getattr(
        current_settings, "turnstile_disabled", False
    ):
        logger.warning(
            "TURNSTILE_DISABLED=true in PRODUCTION -- bot/CAPTCHA protection is OFF "
            "on ALL public forms that call verify_turnstile, not just login: "
            "registration, event registration, book challenge submissions, "
            "public-records requests, card applications, account-security, and "
            "password flows. This is expected on a fresh self-host that hasn't "
            "logged in yet, but before exposing this site to the public internet, "
            "set a real CF_TURNSTILE_SECRET and TURNSTILE_DISABLED=false."
        )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{branding.library_name} API shutting down")
    try:
        from .services import floor_view_bus
        await floor_view_bus.stop_subscriber()
    except Exception as e:  # noqa: BLE001  # shutdown must not crash on subscriber failure
        logger.error(f"Failed to stop floor-view bus subscriber: {e}")


@app.get("/health")
async def health_check():
    """Basic health check endpoint (no logging)."""
    return {"status": "healthy", "service": "l30-library"}


@app.get("/api/v1/health")
async def api_health():
    """Detailed API health check endpoint."""
    return {"status": "ok", "version": settings.app_version, "environment": settings.environment}


# Serve uploaded catalog images
import os as _os
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse


@app.get("/uploads/{file_path:path}")
async def serve_upload(file_path: str):
    base = _Path(_os.getenv("STORAGE_LOCAL_PATH", "/app/uploads"))
    full = (base / file_path).resolve()
    if not str(full).startswith(str(base.resolve())) or not full.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    return _FileResponse(full)

