# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import asyncio
from app.core.logging import get_logger
import time
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable
from urllib.parse import urlparse

import httpx

from ..core.config import get_settings

logger = get_logger(__name__)

PROBE_TIMEOUT_S = 5
DETAIL_MAX_CHARS = 200
RATE_LIMIT_WINDOW_S = 60
RATE_LIMIT_MAX_CALLS = 6


@dataclass
class ProbeResult:
    integration_id: str
    name: str
    category: str   # "Email", "SMS", "Payments", "Storage", "Observability", "Auth", "AI", "Other"
    configured: bool
    status: str     # "ok" | "error" | "never" | "unconfigured"
    last_probe_at: Optional[datetime]
    last_probe_detail: Optional[str]


# --- in-process state -------------------------------------------------------

_LAST_RESULTS: dict[str, ProbeResult] = {}
# (admin_id, integration_id) -> list[float] of recent call timestamps
_RATE_LIMIT_CALLS: dict[tuple[Optional[int], str], list[float]] = {}


def _truncate(detail: Optional[str]) -> Optional[str]:
    if detail is None:
        return None
    s = str(detail)
    return s if len(s) <= DETAIL_MAX_CHARS else s[: DETAIL_MAX_CHARS - 3] + "..."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rate_limit_check(admin_id: Optional[int], integration_id: str) -> bool:
    key = (admin_id, integration_id)
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_S
    calls = [t for t in _RATE_LIMIT_CALLS.get(key, []) if t > cutoff]
    if len(calls) >= RATE_LIMIT_MAX_CALLS:
        _RATE_LIMIT_CALLS[key] = calls
        return False
    calls.append(now)
    _RATE_LIMIT_CALLS[key] = calls
    return True


# --- per-integration probes -------------------------------------------------

async def _probe_resend(settings) -> ProbeResult:
    name, category = "Email (Resend)", "Email"
    api_key = getattr(settings, "resend_api_key", "") or ""
    if not api_key:
        return ProbeResult("resend", name, category, False, "unconfigured", None, "not configured")
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
            r = await client.get(
                "https://api.resend.com/domains",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if r.status_code == 200:
            return ProbeResult("resend", name, category, True, "ok", _now(), None)
        if r.status_code == 401:
            return ProbeResult("resend", name, category, True, "error", _now(), "401 -- invalid API key")
        return ProbeResult("resend", name, category, True, "error", _now(), f"HTTP {r.status_code}")
    except httpx.TimeoutException:
        return ProbeResult("resend", name, category, True, "error", _now(), "timeout")
    except Exception as e:  # noqa: BLE001
        return ProbeResult("resend", name, category, True, "error", _now(), _truncate(f"{type(e).__name__}: {e}"))



async def _probe_stripe(settings) -> ProbeResult:
    name, category = "Payments (Stripe)", "Payments"
    api_key = getattr(settings, "stripe_secret_key", "") or ""
    if not api_key:
        return ProbeResult("stripe", name, category, False, "unconfigured", None, "not configured")
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
            r = await client.get(
                "https://api.stripe.com/v1/balance",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if r.status_code == 200:
            return ProbeResult("stripe", name, category, True, "ok", _now(), None)
        if r.status_code == 401:
            return ProbeResult("stripe", name, category, True, "error", _now(), "401 -- invalid API key")
        return ProbeResult("stripe", name, category, True, "error", _now(), f"HTTP {r.status_code}")
    except httpx.TimeoutException:
        return ProbeResult("stripe", name, category, True, "error", _now(), "timeout")
    except Exception as e:  # noqa: BLE001
        return ProbeResult("stripe", name, category, True, "error", _now(), _truncate(f"{type(e).__name__}: {e}"))


async def _probe_s3(settings) -> ProbeResult:
    name, category = "Object storage (S3 backups)", "Storage"
    bucket = (
        getattr(settings, "backup_s3_bucket", "")
        or getattr(settings, "s3_backup_bucket", "")
        or getattr(settings, "aws_s3_bucket", "")
        or ""
    )
    if not bucket:
        return ProbeResult("s3", name, category, False, "unconfigured", None, "not configured")

    def _head() -> tuple[bool, Optional[str]]:
        # boto3 is sync; isolate it from the event loop.
        try:
            import boto3  # type: ignore
            from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
            from botocore.config import Config  # type: ignore
        except Exception as e:  # noqa: BLE001
            return False, f"boto3 import error: {type(e).__name__}"
        try:
            client = boto3.client(
                "s3",
                config=Config(connect_timeout=PROBE_TIMEOUT_S, read_timeout=PROBE_TIMEOUT_S, retries={"max_attempts": 1}),
            )
            client.head_bucket(Bucket=bucket)
            return True, None
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "ClientError") if hasattr(e, "response") else "ClientError"
            return False, f"S3 {code}"
        except BotoCoreError as e:
            return False, f"{type(e).__name__}"
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}"

    try:
        ok, detail = await asyncio.wait_for(asyncio.to_thread(_head), timeout=PROBE_TIMEOUT_S + 1)
    except asyncio.TimeoutError:
        return ProbeResult("s3", name, category, True, "error", _now(), "timeout")
    except Exception as e:  # noqa: BLE001
        return ProbeResult("s3", name, category, True, "error", _now(), _truncate(f"{type(e).__name__}: {e}"))

    if ok:
        return ProbeResult("s3", name, category, True, "ok", _now(), None)
    return ProbeResult("s3", name, category, True, "error", _now(), _truncate(detail))


_SENTRY_DSN_RE = re.compile(r"^https://[^:@/]+(?::[^@/]+)?@[^/]+/\d+$")


async def _probe_sentry(settings) -> ProbeResult:
    name, category = "Error tracking (Sentry)", "Observability"
    dsn = (getattr(settings, "sentry_dsn", "") or "").strip()
    if not dsn:
        return ProbeResult("sentry", name, category, False, "unconfigured", None, "not configured")
    try:
        parsed = urlparse(dsn)
        valid = (
            parsed.scheme in ("http", "https")
            and parsed.username
            and parsed.hostname
            and parsed.path
            and parsed.path.strip("/").isdigit()
        )
    except Exception:  # noqa: BLE001
        valid = False
    if valid:
        return ProbeResult("sentry", name, category, True, "ok", _now(), "DSN format valid")
    return ProbeResult("sentry", name, category, True, "error", _now(), "DSN format invalid")




async def _probe_microsoft_oauth(settings) -> ProbeResult:
    name, category = "OAuth (Microsoft)", "Auth"
    cid = (
        getattr(settings, "microsoft_oauth_client_id", "")
        or getattr(settings, "microsoft_client_id", "")
        or ""
    )
    csec = (
        getattr(settings, "microsoft_oauth_client_secret", "")
        or getattr(settings, "microsoft_client_secret", "")
        or ""
    )
    if not cid or not csec:
        return ProbeResult("microsoft_oauth", name, category, False, "unconfigured", None, "not configured")
    return ProbeResult("microsoft_oauth", name, category, True, "ok", _now(), "client_id + secret present")


async def _probe_ollama(settings) -> ProbeResult:
    name, category = "AI provider (Ollama)", "AI"
    base = (getattr(settings, "ollama_base_url", "") or getattr(settings, "ollama_host", "") or "").strip()
    if not base:
        return ProbeResult("ollama", name, category, False, "unconfigured", None, "not configured")
    url = base.rstrip("/") + "/api/version"
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
            r = await client.get(url)
        if r.status_code == 200:
            return ProbeResult("ollama", name, category, True, "ok", _now(), None)
        return ProbeResult("ollama", name, category, True, "error", _now(), f"HTTP {r.status_code}")
    except httpx.TimeoutException:
        return ProbeResult("ollama", name, category, True, "error", _now(), "timeout")
    except Exception as e:  # noqa: BLE001
        return ProbeResult("ollama", name, category, True, "error", _now(), _truncate(f"{type(e).__name__}: {e}"))


async def _probe_webhook_signing(settings) -> ProbeResult:
    name, category = "Webhook signing secret", "Other"
    secret = (
        getattr(settings, "webhook_signing_secret", "")
        or getattr(settings, "stripe_overflow_webhook_secret", "")
        or getattr(settings, "stripe_pod_webhook_secret", "")
        or getattr(settings, "lulu_webhook_secret", "")
        or ""
    )
    if not secret:
        return ProbeResult("webhook_signing", name, category, False, "unconfigured", None, "not configured")
    if len(secret) < 16:
        return ProbeResult("webhook_signing", name, category, True, "error", _now(), "secret shorter than 16 chars")
    return ProbeResult("webhook_signing", name, category, True, "ok", _now(), "secret length valid")


# --- registry ---------------------------------------------------------------

_PROBES: dict[str, Callable[[object], Awaitable[ProbeResult]]] = {
    "resend": _probe_resend,
    "stripe": _probe_stripe,
    "s3": _probe_s3,
    "sentry": _probe_sentry,
    "microsoft_oauth": _probe_microsoft_oauth,
    "ollama": _probe_ollama,
    "webhook_signing": _probe_webhook_signing,
}


def _unconfigured_placeholder(integration_id: str, settings) -> ProbeResult:
    # Cheap labelling -- re-derive from the probe function by calling with a
    # minimal stub is not safe (could trigger network). Hard-code labels here.
    labels = {
        "resend": ("Email (Resend)", "Email", "resend_api_key"),
        "stripe": ("Payments (Stripe)", "Payments", "stripe_secret_key"),
        "s3": ("Object storage (S3 backups)", "Storage", "backup_s3_bucket"),
        "sentry": ("Error tracking (Sentry)", "Observability", "sentry_dsn"),
        "microsoft_oauth": ("OAuth (Microsoft)", "Auth", "microsoft_oauth_client_id"),
        "ollama": ("AI provider (Ollama)", "AI", "ollama_base_url"),
        "webhook_signing": ("Webhook signing secret", "Other", "webhook_signing_secret"),
    }
    name, category, primary_field = labels[integration_id]
    val = getattr(settings, primary_field, "") or ""
    # Ollama has a default non-empty value so treat presence loosely
    configured = bool(val)
    if not configured:
        return ProbeResult(integration_id, name, category, False, "unconfigured", None, "not configured")
    return ProbeResult(integration_id, name, category, True, "never", None, None)


# --- public API -------------------------------------------------------------

async def snapshot_all() -> list[ProbeResult]:
    settings = get_settings()
    rows: list[ProbeResult] = []
    for integration_id in _PROBES.keys():
        cached = _LAST_RESULTS.get(integration_id)
        if cached is not None:
            rows.append(cached)
        else:
            rows.append(_unconfigured_placeholder(integration_id, settings))
    return rows


async def run(integration_id: str, admin_user_id: Optional[int] = None) -> ProbeResult:
    if integration_id not in _PROBES:
        return ProbeResult(
            integration_id=integration_id,
            name=integration_id,
            category="Other",
            configured=False,
            status="error",
            last_probe_at=_now(),
            last_probe_detail="unknown integration_id",
        )

    if not _rate_limit_check(admin_user_id, integration_id):
        # 429-style synthetic response. Don't audit-log noise from rate limit.
        cached = _LAST_RESULTS.get(integration_id)
        name = cached.name if cached else integration_id
        category = cached.category if cached else "Other"
        configured = cached.configured if cached else False
        return ProbeResult(
            integration_id=integration_id,
            name=name,
            category=category,
            configured=configured,
            status="error",
            last_probe_at=_now(),
            last_probe_detail=f"rate limited: max {RATE_LIMIT_MAX_CALLS} probes/min",
        )

    settings = get_settings()
    probe_fn = _PROBES[integration_id]
    try:
        result = await asyncio.wait_for(probe_fn(settings), timeout=PROBE_TIMEOUT_S + 2)
    except asyncio.TimeoutError:
        result = ProbeResult(
            integration_id=integration_id,
            name=integration_id,
            category="Other",
            configured=True,
            status="error",
            last_probe_at=_now(),
            last_probe_detail="probe wrapper timeout",
        )
    except Exception as e:  # noqa: BLE001 -- probes must never raise out
        result = ProbeResult(
            integration_id=integration_id,
            name=integration_id,
            category="Other",
            configured=True,
            status="error",
            last_probe_at=_now(),
            last_probe_detail=_truncate(f"{type(e).__name__}: {e}"),
        )

    _LAST_RESULTS[integration_id] = result
    await _write_audit_log(admin_user_id, result)
    return result


async def _write_audit_log(admin_user_id: Optional[int], result: ProbeResult) -> None:
    try:
        from ..core.database import get_async_session
        from ..models.audit_log import AuditLog, AuditAction

        async with get_async_session() as session:
            session.add(AuditLog(
                admin_id=admin_user_id,
                action=AuditAction.INTEGRATION_PROBE,
                details={
                    "integration_id": result.integration_id,
                    "status": result.status,
                    "detail_truncated_to_200": _truncate(result.last_probe_detail),
                },
            ))
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to write integration_probe audit log: %s", type(e).__name__)


async def send_test_email(admin_user, admin_email: str) -> tuple[bool, str]:
    if not admin_email:
        return False, "no admin email on file"
    try:
        from ..core.email import send_email
        ok = await send_email(
            to_email=admin_email,
            subject="L30 test email",
            html_content=(
                "<p>This is a test email from the L30 System Integrations Status page.</p>"
                "<p>If you're reading this, transactional email is wired up correctly.</p>"
            ),
            categories=["integration_probe_test_email"],
        )
        if ok:
            return True, f"sent to {admin_email}"
        return False, "send_email returned False (check daily cap / dedup / provider)"
    except Exception as e:  # noqa: BLE001
        return False, _truncate(f"{type(e).__name__}: {e}") or "error"
