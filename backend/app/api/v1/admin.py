# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin endpoints for system monitoring and statistics.

Provides endpoints for viewing:
- Endpoint usage statistics
- Application uptime
- Never-accessed (orphaned) endpoints
- Health and diagnostic information

All endpoints require admin authentication.
"""

from app.core.logging import get_logger
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...middleware.endpoint_tracker import get_endpoint_tracker
from ...models.user import User
from ...core.config import get_settings
from ...schemas.common import EndpointStatsResponse, SingleEndpointStatsResponse
from .auth import get_current_user

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin"])


def _extract_routes_from_app(app_instance: Any) -> Dict[str, str]:
    routes = {}

    # Iterate through all routes registered in the app
    if hasattr(app_instance, "routes"):
        for route in app_instance.routes:
            # Skip middleware routes and other non-API routes
            if hasattr(route, "path") and hasattr(route, "methods"):
                path = route.path
                methods = route.methods or {"GET"}

                for method in methods:
                    # Skip OPTIONS (CORS preflight) and HEAD methods
                    if method not in ("OPTIONS", "HEAD"):
                        routes[path] = method

    return routes


async def _verify_admin_access(
    current_user: User = Depends(get_current_user),
) -> User:
    # Use the authorization module's role checking
    from ...models.user import UserRole

    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        logger.warning(
            "Unauthorized admin access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": current_user.role,
                "endpoint": "/api/v1/admin/endpoint-stats",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


@router.get(
    "/endpoint-stats",
    summary="Get endpoint usage statistics",
    description="Returns runtime statistics for all API endpoints including hit counts, "
    "last access times, and status code distribution. Requires admin authentication.",
)
async def get_endpoint_stats(
    include_orphaned: bool = True,
    current_user: User = Depends(_verify_admin_access),
) -> Dict[str, Any]:
    """Get comprehensive endpoint usage statistics.

    Returns detailed stats for all endpoints including:
    - Hit count per endpoint
    - Last accessed timestamp
    - Status code distribution
    - Orphaned endpoints (registered but never accessed)
    - Application uptime

    Query Parameters:
        include_orphaned: Whether to include never-accessed endpoints (default: true)

    Returns:
        Dict containing:
            - endpoints: Dict of {method path: stats}
            - orphaned_endpoints: Dict of endpoints never accessed
            - uptime: Application uptime information
            - summary: Overall statistics summary
            - enabled: Whether endpoint tracking is enabled

    Raises:
        HTTPException: 403 if user is not admin
    """
    tracker = get_endpoint_tracker()

    # Get all stats
    all_stats = await tracker.get_all_stats()

    # Get app instance from Starlette context if available
    # For this implementation, we'll return empty orphaned list
    # In production, you'd pass the app instance to this function
    orphaned_endpoints: Dict[str, str] = {}

    if include_orphaned:
        # To get orphaned endpoints, we need the app instance
        # This would be passed in from main.py for full functionality
        orphaned_endpoints = {}

    # Calculate summary statistics
    total_endpoints = len(all_stats)
    total_requests = sum(stats.get("hit_count", 0) for stats in all_stats.values())

    # Get status code distribution across all endpoints
    all_status_codes: Dict[int, int] = {}
    for stats in all_stats.values():
        for code, count in stats.get("status_codes", {}).items():
            all_status_codes[code] = all_status_codes.get(code, 0) + count

    uptime_info = tracker.get_uptime()

    response = {
        "enabled": settings.enable_endpoint_tracking,
        "endpoints": all_stats,
        "orphaned_endpoints": orphaned_endpoints,
        "uptime": uptime_info,
        "summary": {
            "total_endpoints": total_endpoints,
            "total_requests": total_requests,
            "status_code_distribution": dict(sorted(all_status_codes.items())),
            "unique_status_codes": len(all_status_codes),
        },
        "queried_by": {
            "user_id": current_user.id,
            "email": current_user.email,
        },
    }

    logger.info(
        "Admin accessed endpoint statistics",
        extra={
            "user_id": current_user.id,
            "total_endpoints": total_endpoints,
            "total_requests": total_requests,
        },
    )

    return response


@router.get(
    "/endpoint-stats/summary",
    response_model=EndpointStatsResponse,
    summary="Get endpoint statistics summary",
    description="Returns a brief summary of endpoint usage without detailed per-endpoint data. "
    "Useful for dashboards and monitoring.",
)
async def get_endpoint_stats_summary(
    current_user: User = Depends(_verify_admin_access),
):
    """Get a summary of endpoint usage statistics.

    Returns high-level statistics without detailed per-endpoint breakdown.

    Returns:
        Dict containing:
            - total_endpoints: Number of endpoints with requests
            - total_requests: Total requests across all endpoints
            - uptime: Application uptime
            - most_accessed: Top 10 most frequently accessed endpoints
            - status_code_distribution: Distribution of HTTP status codes
            - enabled: Whether endpoint tracking is enabled
    """
    tracker = get_endpoint_tracker()
    all_stats = await tracker.get_all_stats()

    # Calculate summary statistics
    total_endpoints = len(all_stats)
    total_requests = sum(stats.get("hit_count", 0) for stats in all_stats.values())

    # Get most accessed endpoints
    sorted_endpoints = sorted(
        all_stats.items(), key=lambda x: x[1].get("hit_count", 0), reverse=True
    )
    most_accessed = [
        {
            "endpoint": key,
            "hit_count": stats.get("hit_count", 0),
            "last_accessed": stats.get("last_accessed"),
        }
        for key, stats in sorted_endpoints[:10]
    ]

    # Get status code distribution
    all_status_codes: Dict[int, int] = {}
    for stats in all_stats.values():
        for code, count in stats.get("status_codes", {}).items():
            all_status_codes[code] = all_status_codes.get(code, 0) + count

    uptime_info = tracker.get_uptime()

    return {
        "enabled": settings.enable_endpoint_tracking,
        "total_endpoints": total_endpoints,
        "total_requests": total_requests,
        "uptime": uptime_info,
        "most_accessed": most_accessed,
        "status_code_distribution": dict(sorted(all_status_codes.items())),
    }


@router.get(
    "/endpoint-stats/endpoint/{method}/{path:path}",
    response_model=SingleEndpointStatsResponse,
    summary="Get statistics for a specific endpoint",
    description="Returns detailed statistics for a single endpoint including hit count, "
    "last access time, and status code distribution.",
)
async def get_single_endpoint_stats(
    method: str = Path(...),
    path: str = Path(...),
    current_user: User = Depends(_verify_admin_access),
):
    """Get statistics for a specific endpoint.

    Path Parameters:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: The URL path

    Returns:
        Dict with endpoint statistics or 404 if endpoint not found

    Raises:
        HTTPException: 404 if endpoint has not been accessed
    """
    tracker = get_endpoint_tracker()
    stats = await tracker.get_endpoint_stats(method.upper(), f"/{path}")

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No statistics found for {method.upper()} /{path}",
        )

    return {
        "enabled": settings.enable_endpoint_tracking,
        "endpoint_stats": stats,
    }


@router.post(
    "/endpoint-stats/clear",
    summary="Clear endpoint statistics",
    description="Clears all collected endpoint statistics and resets uptime. "
    "Useful for benchmarking or removing data from previous deployments.",
)
async def clear_endpoint_stats(
    current_user: User = Depends(_verify_admin_access),
) -> Dict[str, str]:
    """Clear all collected endpoint statistics.

    WARNING: This action cannot be undone. All statistics will be reset.

    Returns:
        Confirmation message

    Raises:
        HTTPException: 403 if user is not admin
    """
    tracker = get_endpoint_tracker()
    await tracker.clear_stats()

    logger.warning(
        "Endpoint statistics cleared",
        extra={
            "user_id": current_user.id,
            "email": current_user.email,
        },
    )

    return {
        "message": "Endpoint statistics cleared successfully",
        "cleared_by_user_id": str(current_user.id),
    }


@router.get("/dashboard", summary="Admin dashboard summary stats")
async def admin_dashboard(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Admin dashboard with summary statistics."""
    from sqlalchemy import func, select
    from ...models.catalog import CatalogItem
    from ...models.circulation import Checkout

    total_items = (await db.execute(select(func.count(CatalogItem.id)))).scalar() or 0
    active_checkouts = (await db.execute(
        select(func.count(Checkout.id)).where(Checkout.status == "active")
    )).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    return {
        "total_catalog_items": total_items,
        "active_checkouts": active_checkouts,
        "total_users": total_users,
    }


@router.get("/settings", summary="System settings overview")
async def admin_settings(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return current system settings (non-sensitive)."""
    return {
        "library_name": settings.library_name,
        "timezone": getattr(settings, "timezone", "UTC"),
        "features_enabled": True,
        "maintenance_mode": False,
    }


@router.get("/audit-logs", summary="System audit logs")
async def admin_audit_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return recent audit log entries."""
    from sqlalchemy import text

    try:
        result = await db.execute(
            text(
                "SELECT id, action, admin_id, target_user_id, details, ip_address, created_at "
                "FROM audit_logs ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
            ),
            {"limit": limit, "skip": skip},
        )
        rows = result.fetchall()
        total_result = await db.execute(text("SELECT COUNT(*) FROM audit_logs"))
        total = total_result.scalar() or 0
        return {
            "total": total,
            "items": [
                {
                    "id": r[0],
                    "action": r[1],
                    "admin_id": r[2],
                    "target_user_id": r[3],
                    "details": r[4],
                    "ip_address": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                }
                for r in rows
            ],
        }
    except Exception:  # noqa: BLE001  # audit table may not exist or have different schema
        # Table may not exist or have different schema
        return {"total": 0, "items": [], "note": "Audit log table not available"}


# ---------------------------------------------------------------------------
# Configuration section endpoints for system dashboard overview cards
# ---------------------------------------------------------------------------

_CONFIGURATION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "storage": {
        "storage_backend": "local",
        "storage_local_path": "/app/uploads",
        "s3_bucket": "",
        "s3_region": "us-east-1",
        "s3_endpoint_url": ""
    },
    "security": {
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 3,
        "max_login_attempts": 5,
        "lockout_duration_minutes": 15,
        "password_min_length": 10,
        "token_blacklist_fail_closed": False
    },
    "scheduler": {
        "scheduler_enabled": True,
        "scheduler_timezone": "UTC",
        "scheduler_job_store": "sqlalchemy",
        "scheduler_retry_enabled": True,
        "scheduler_retry_max_attempts": 3,
        "scheduler_retry_initial_delay": 2.0,
        "scheduler_retry_max_delay": 300.0,
        "overdue_notice_interval_days": 7,
        "hold_expiry_days": 7,
        "job_alert_enabled": True,
        "job_alert_email": "",
        "job_alert_warning_threshold": 5.0,
        "job_alert_critical_threshold": 15.0,
        "job_log_retention_days": 90
    },
    "virus_scan": {
        "virus_scan_enabled": True,
        "virus_scan_fail_on_error": True,
        "clamav_socket": "/var/run/clamav/clamd.sock",
        "clamav_host": "",
        "clamav_port": 3310
    }
}


async def _get_configuration_section(
    section: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    from ...services.organization_features_service import OrganizationFeaturesService

    features = await OrganizationFeaturesService.get_or_create_features(db)
    config = features.configuration or {}
    stored = config.get(section) or {}
    defaults = _CONFIGURATION_DEFAULTS.get(section, {})
    return {**defaults, **stored}


@router.get(
    "/configuration/{section}",
    summary="Get a configuration section for system dashboard",
)
async def get_configuration_section(
    section: str = Path(..., description="Configuration section name"),
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return configuration values for a named section.

    Used by the system monitoring dashboard to display current settings
    on overview cards. Reads from OrganizationFeatures.configuration JSONB.
    """
    if section not in _CONFIGURATION_DEFAULTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown configuration section: {section}",
        )
    values = await _get_configuration_section(section, db)
    return {"section": section, "values": values}
