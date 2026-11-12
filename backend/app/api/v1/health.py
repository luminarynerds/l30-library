# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Health check endpoints.

Provides Kubernetes-style liveness/readiness/startup probes that actually verify
PostgreSQL, Redis, APScheduler, and WebSocket managers. Also exposes a staff-only
dashboard endpoint with detailed metrics for the admin UI.
"""

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

from ...core.cache import get_redis
from ...core.config import get_settings
from ...core.database import get_db
from ...core.logging import get_logger
from .auth import get_current_user
from .dependencies import require_admin, require_staff

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()

# Track application boot time for uptime reporting
_app_start_time: float = time.monotonic()


# ---------------------------------------------------------------------------
# Internal helpers – shared by multiple endpoints
# ---------------------------------------------------------------------------

async def _check_postgres(db: AsyncSession) -> Dict[str, Any]:
    from ...core.database import engine as async_engine

    start = time.perf_counter()
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        pool_info: Dict[str, Any] = {}
        try:
            pool = async_engine.pool
            pool_info = {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
            }
        except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
            logger.debug("Could not retrieve connection pool info", exc_info=True)

        return {
            "status": "healthy" if latency_ms < 500 else "degraded",
            "response_time_ms": latency_ms,
            **pool_info,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("PostgreSQL health check failed: %s", e)
        return {
            "status": "unhealthy",
            "response_time_ms": latency_ms,
            "error": str(e),
        }


async def _check_redis() -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        redis_client = await get_redis()
        if redis_client is None:
            return {
                "status": "unhealthy",
                "response_time_ms": 0,
                "error": "Redis client unavailable",
            }
        await redis_client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        redis_info: Dict[str, Any] = {}
        try:
            info = await redis_client.info()
            redis_info = {
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
            logger.debug("Could not retrieve Redis info", exc_info=True)

        return {"status": "healthy", "response_time_ms": latency_ms, **redis_info}
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("Redis health check failed: %s", e)
        return {
            "status": "unhealthy",
            "response_time_ms": latency_ms,
            "error": str(e),
        }


def _probe_scheduler_lock() -> str:
    import fcntl

    try:
        lock_fd = open("/tmp/.lsc_scheduler.lock", "r")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # We got the lock — no other worker has it, scheduler isn't running
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        return "not_running"
    except (IOError, OSError):
        # Lock is held by another worker — scheduler is running there
        return "running_elsewhere"
    except FileNotFoundError:
        return "no_lock_file"


async def _check_scheduler() -> Dict[str, Any]:
    try:
        from ...services.schedulers.main import get_scheduler

        sched = get_scheduler()
        if sched is None:
            # This worker doesn't own the scheduler. Check if another worker
            # holds the lock (meaning the scheduler is running elsewhere).
            if not settings.scheduler_enabled:
                return {"status": "disabled", "message": "Scheduler disabled via config"}
            lock_status = await asyncio.to_thread(_probe_scheduler_lock)
            if lock_status == "running_elsewhere":
                return {"status": "healthy", "message": "Running on another worker"}
            elif lock_status == "no_lock_file":
                return {"status": "unhealthy", "message": "Scheduler lock file not found"}
            else:
                return {"status": "unhealthy", "message": "Scheduler enabled but not running"}

        running = sched.running
        jobs = sched.get_jobs()
        next_run = None
        if jobs:
            upcoming = min(
                (j.next_run_time for j in jobs if j.next_run_time is not None),
                default=None,
            )
            if upcoming is not None:
                next_run = upcoming.isoformat()

        return {
            "status": "healthy" if running else "unhealthy",
            "running": running,
            "job_count": len(jobs),
            "next_run_time": next_run,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("Scheduler health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


def _check_websockets() -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "healthy"}
    try:
        from ...core.websocket import patron_ws_manager

        patron_stats = patron_ws_manager.get_stats()
        result["patron"] = {
            "active_connections": patron_stats.get("active_connections", 0),
            "unique_users": patron_stats.get("unique_users", 0),
            "total_messages_sent": patron_stats.get("total_messages_sent", 0),
            "running": patron_ws_manager._running,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        result["patron"] = {"status": "error", "error": str(e)}

    try:
        from ...services.rfid_websocket import rfid_ws_manager

        result["rfid"] = {
            "active_connections": rfid_ws_manager.active_connections,
            "total_sessions": rfid_ws_manager.total_sessions,
            "disconnected_sessions": rfid_ws_manager.disconnected_sessions,
            "total_queued_messages": rfid_ws_manager.total_queued_messages,
            "running": rfid_ws_manager._running,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        result["rfid"] = {"status": "error", "error": str(e)}

    return result


def _check_disk() -> Dict[str, Any]:
    try:
        upload_path = settings.storage_local_path
        usage = shutil.disk_usage(upload_path)
        disk_percent = round((usage.used / usage.total) * 100, 1)

        if disk_percent >= 90:
            disk_status = "critical"
        elif disk_percent >= 80:
            disk_status = "warning"
        else:
            disk_status = "ok"

        return {
            "status": disk_status,
            "path": upload_path,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "used_percent": disk_percent,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("Disk health check failed: %s", e)
        return {"status": "unknown", "error": str(e)}


async def _check_metislib() -> Dict[str, Any]:
    if not settings.metislib_enabled:
        return {"status": "disabled", "message": "METISLIB_ENABLED=false"}
    if settings.metislib_mock:
        return {"status": "healthy", "message": "metislib mock mode"}
    try:
        from ...services.metislib_client import get_metislib_client

        client = get_metislib_client()
        if not hasattr(client, "ping"):
            return {"status": "healthy", "message": "no probe available"}
        result = await client.ping(timeout=2.0)
        breaker_state = result.get("breaker_state")
        if result.get("ok"):
            return {
                "status": "healthy",
                "response_time_ms": result.get("latency_ms"),
                "breaker_state": breaker_state,
            }
        return {
            "status": "degraded",
            "response_time_ms": result.get("latency_ms"),
            "breaker_state": breaker_state,
            "breaker_failures": result.get("breaker_failures"),
            "error": result.get("error") or f"HTTP {result.get('status_code')}",
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("MetisLib health check failed: %s", e)
        return {"status": "degraded", "error": str(e)}


def _check_encryption() -> Dict[str, Any]:
    from ...core.encryption import (
        decrypt_pii,
        encrypt_pii,
        get_decryption_health,
        is_encryption_enabled,
    )

    health_metrics = get_decryption_health()

    if not is_encryption_enabled():
        return {
            "status": "disabled",
            "message": "PII encryption is not enabled",
            **health_metrics,
        }

    canary = "LSC_CANARY_CHECK"
    try:
        encrypted = encrypt_pii(canary)
        decrypted = decrypt_pii(encrypted)
        if decrypted == canary:
            return {
                "status": "healthy",
                **health_metrics,
            }
        else:
            logger.error(
                "Encryption canary mismatch: decrypted value does not match original"
            )
            return {
                "status": "critical",
                "error": "Canary decrypt mismatch — encryption may be misconfigured",
                **health_metrics,
            }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("Encryption canary check failed: %s", e)
        return {
            "status": "critical",
            "error": f"Canary round-trip failed: {e}",
            **health_metrics,
        }


def _overall_status(checks: Dict[str, Any]) -> str:
    statuses = [c.get("status", "unknown") for c in checks.values()]
    if any(s == "unhealthy" for s in statuses):
        return "unhealthy"
    if any(s in ("degraded", "error", "critical", "warning") for s in statuses):
        return "degraded"
    return "healthy"


# ---------------------------------------------------------------------------
# Public probe endpoints
# ---------------------------------------------------------------------------

@router.get("/health", tags=["health"], summary="Basic liveness check")
async def health_check() -> Dict[str, Any]:
    """
    Basic liveness check – returns 200 if the service process is alive.

    Use for Docker/Kubernetes liveness probes and load-balancer health checks.
    Intentionally lightweight: no DB or Redis calls.
    """
    return {
        "status": "ok",
        "service": "l30-library",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.app_version,
    }


@router.get("/health/live", tags=["health"], summary="Liveness probe")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes-style liveness probe.

    Returns 200 if the application process is alive and not deadlocked.
    """
    return {
        "status": "alive",
        "service": "l30-library",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", tags=["health"], summary="Readiness check with dependencies")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe – verifies all critical dependencies before the service
    can accept traffic.

    Checks PostgreSQL, Redis, APScheduler, and WebSocket managers.

    Returns 503 if any critical dependency is unhealthy.
    """
    checks: Dict[str, Any] = {}
    # Run async checks concurrently, sync checks inline
    db_result, redis_result, sched_result, metislib_result = await asyncio.gather(
        _check_postgres(db),
        _check_redis(),
        _check_scheduler(),
        _check_metislib(),
    )
    checks["database"] = db_result
    checks["redis"] = redis_result
    checks["scheduler"] = sched_result
    checks["websockets"] = _check_websockets()
    checks["disk"] = _check_disk()
    checks["encryption"] = _check_encryption()
    checks["metislib"] = metislib_result

    overall = _overall_status(checks)

    response = {
        "status": "ready" if overall == "healthy" else overall,
        "service": "l30-library",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if overall == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response,
        )

    return response


@router.get("/health/startup", tags=["health"], summary="Startup probe")
async def startup_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Kubernetes-style startup probe.

    Verifies that the database is reachable and the scheduler has been
    initialised. More lenient than the readiness probe.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        scheduler_info = await _check_scheduler()

        return {
            "status": "started",
            "service": "l30-library",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "scheduler": scheduler_info.get("status", "unknown"),
        }
    except Exception as e:
        logger.error("Startup check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "starting",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from e


@router.get("/health/detailed", tags=["health"], summary="Detailed health information")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Dict[str, Any]:
    """
    Detailed health information for monitoring dashboards.

    Returns comprehensive data about every subsystem including pool sizes,
    memory usage, scheduler jobs, and WebSocket connections.
    """
    checks: Dict[str, Any] = {}

    # PostgreSQL – also grab version
    pg = await _check_postgres(db)
    try:
        ver_result = await db.execute(text("SELECT version()"))
        db_version = ver_result.scalar()
        pg["version"] = db_version.split(",")[0] if db_version else "unknown"
        pg["type"] = "postgresql"
    except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.debug("Could not retrieve PostgreSQL version", exc_info=True)
    checks["database"] = pg

    redis_result, sched_result, metislib_result = await asyncio.gather(
        _check_redis(),
        _check_scheduler(),
        _check_metislib(),
    )
    checks["redis"] = redis_result
    checks["scheduler"] = sched_result
    checks["websockets"] = _check_websockets()
    checks["disk"] = _check_disk()
    checks["encryption"] = _check_encryption()
    checks["metislib"] = metislib_result

    # Email safeguard stats
    try:
        from ...core.email_safeguards import get_email_stats

        checks["email"] = await get_email_stats()
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        checks["email"] = {"status": "unknown", "error": str(e)}

    overall = _overall_status(checks)
    uptime_seconds = round(time.monotonic() - _app_start_time, 1)

    return {
        "status": overall,
        "service": "l30-library",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "checks": checks,
    }


@router.get(
    "/health/metislib",
    tags=["health"],
    summary="MetisLib upstream health",
)
async def health_metislib() -> Dict[str, Any]:
    """
    Targeted MetisLib upstream check. Returns the same payload as the
    ``metislib`` slot in ``/health/detailed``, exposed as its own endpoint
    for operators and monitoring systems that want to probe the dependency
    directly. Anonymous (no auth) so monitoring can poll without
    credentials, matching the other ``/health/*`` probes.
    """
    return await _check_metislib()


# ---------------------------------------------------------------------------
# Staff-only dashboard endpoint (authenticated, requires admin/staff)
# ---------------------------------------------------------------------------

@router.get(
    "/health/dashboard",
    tags=["health", "admin"],
    summary="Staff-facing dependency health dashboard",
)
async def health_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Dict[str, Any]:
    """
    Comprehensive dependency health dashboard for the admin UI.

    Requires authentication (staff or admin).  Returns the same data as
    ``/health/detailed`` plus scheduler job listing, WebSocket channel stats,
    and cache warming status.
    """
    checks: Dict[str, Any] = {}

    # --- PostgreSQL ---
    pg = await _check_postgres(db)
    try:
        ver_result = await db.execute(text("SELECT version()"))
        db_version = ver_result.scalar()
        pg["version"] = db_version.split(",")[0] if db_version else "unknown"

        # Active connections count
        ac_result = await db.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
        )
        pg["active_connections"] = ac_result.scalar()
    except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.debug("Could not retrieve active connection stats", exc_info=True)
    checks["database"] = pg

    # --- Redis ---
    checks["redis"] = await _check_redis()

    # --- APScheduler ---
    sched_check = await _check_scheduler()
    try:
        from ...services.schedulers.main import get_scheduler

        sched = get_scheduler()
        if sched and sched.running:
            jobs = sched.get_jobs()
            sched_check["jobs"] = [
                {
                    "id": j.id,
                    "name": j.name,
                    "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                }
                for j in jobs
            ]
    except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.debug("Could not retrieve scheduler job info", exc_info=True)
    checks["scheduler"] = sched_check

    # --- WebSockets ---
    ws_check = _check_websockets()
    try:
        from ...core.websocket import patron_ws_manager

        patron_full = patron_ws_manager.get_stats()
        ws_check["patron"]["channel_subscriptions"] = patron_full.get(
            "channel_subscriptions", {}
        )
    except Exception:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.debug("Could not retrieve WebSocket stats", exc_info=True)
    checks["websockets"] = ws_check

    # --- Disk ---
    checks["disk"] = _check_disk()

    # --- Cache ---
    try:
        from app.core.cache import get_cache_stats

        cache_stats = await get_cache_stats()
        checks["cache"] = {
            "status": "healthy" if cache_stats.get("connected") else "degraded",
            **cache_stats,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        checks["cache"] = {"status": "error", "error": str(e)}

    # --- Encryption ---
    checks["encryption"] = _check_encryption()

    # --- MetisLib upstream ---
    checks["metislib"] = await _check_metislib()

    overall = _overall_status(checks)
    uptime_seconds = round(time.monotonic() - _app_start_time, 1)

    return {
        "status": overall,
        "service": "l30-library",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Cache helpers (kept for backward compatibility)
# ---------------------------------------------------------------------------

@router.get("/health/cache", tags=["health"], summary="Cache warming status")
async def cache_health_check(
    current_user: User = Depends(require_staff),
) -> Dict[str, Any]:
    """Cache warming status endpoint."""
    from app.core.cache import get_cache_stats

    try:
        cache_status = await get_cache_stats()
        return {
            "status": "ok" if cache_status.get("redis_connected") else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **cache_status,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("Cache health check failed: %s", e)
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@router.post("/health/cache/warm", tags=["health"], summary="Trigger cache warming")
async def trigger_cache_warming(
    current_user: User = Depends(require_staff),
) -> Dict[str, Any]:
    """Manually trigger cache warming."""
    from app.core.cache import warm_caches

    try:
        result = await warm_caches()
        return {
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }
    except Exception as e:  # noqa: BLE001  # health probe — must not crash on any infrastructure failure
        logger.error("Manual cache warming failed: %s", e)
        return {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@router.get("/health/cache/warm")
async def check_health_cache_warm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check status for /health/cache/warm."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Schema drift detection (cached startup report)
# ---------------------------------------------------------------------------

@router.get("/health/drift", tags=["health"], summary="Schema drift report")
async def drift_report(current_user: User = Depends(require_admin)) -> Dict[str, Any]:
    """
    Returns the drift detection report from the last startup check.
    This is a cached result — not a live check.
    """
    report_path = Path("/tmp/drift_report.json")
    if not report_path.exists():
        return {
            "status": "unknown",
            "message": "No drift report available — check may not have run at startup",
        }
    return json.loads(report_path.read_text())


# ---------------------------------------------------------------------------
# Circulation status drift detection
# ---------------------------------------------------------------------------

@router.get(
    "/health/circulation-drift",
    tags=["health", "admin"],
    summary="Circulation status drift report",
)
async def circulation_drift_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> Dict[str, Any]:
    """
    Detect mismatches between catalog_items.status and checkouts.status.

    Returns items where an active checkout exists but the catalog item is not
    marked 'checked_out', and items marked 'checked_out' with no active
    checkout. Staff-only.
    """
    active_not_checked_out = await db.execute(text(
        "SELECT ci.id, ci.title, ci.status::text AS item_status, "
        "c.id AS checkout_id, c.user_id, c.due_date "
        "FROM catalog_items ci "
        "JOIN checkouts c ON c.item_id = ci.id AND c.status = 'active' "
        "WHERE ci.status != 'checked_out' "
        "ORDER BY ci.id"
    ))
    forward_drift = [
        {
            "item_id": row.id,
            "title": row.title,
            "item_status": row.item_status,
            "checkout_id": row.checkout_id,
            "user_id": row.user_id,
            "due_date": row.due_date.isoformat() if row.due_date else None,
        }
        for row in active_not_checked_out.fetchall()
    ]

    orphaned_checked_out = await db.execute(text(
        "SELECT ci.id, ci.title "
        "FROM catalog_items ci "
        "WHERE ci.status = 'checked_out' "
        "AND NOT EXISTS ("
        "    SELECT 1 FROM checkouts c "
        "    WHERE c.item_id = ci.id AND c.status = 'active'"
        ") "
        "ORDER BY ci.id"
    ))
    reverse_drift = [
        {"item_id": row.id, "title": row.title}
        for row in orphaned_checked_out.fetchall()
    ]

    total = len(forward_drift) + len(reverse_drift)
    return {
        "status": "ok" if total == 0 else "drift_detected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_mismatches": total,
        "active_checkout_wrong_item_status": forward_drift,
        "checked_out_no_active_checkout": reverse_drift,
    }
