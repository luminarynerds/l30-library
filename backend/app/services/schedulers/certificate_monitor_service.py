# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import asyncio
import os
import ssl
import socket
from datetime import datetime, timezone
from typing import TypedDict

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger(__name__)

# Thresholds (days)
WARNING_DAYS = 14
CRITICAL_DAYS = 7


class CertSummary(TypedDict):
    total_checked: int
    valid: int
    warning: int
    critical: int
    expired: int
    errors: int


def _check_host_cert(hostname: str, port: int = 443, timeout: int = 10) -> dict:
    result: dict = {
        "hostname": hostname,
        "port": port,
        "days_remaining": None,
        "expires_at": None,
        "status": "error",
        "error": None,
    }
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if cert is None:
                    result["error"] = "No certificate returned"
                    return result

                not_after = cert.get("notAfter")
                if not_after is None:
                    result["error"] = "Certificate missing notAfter field"
                    return result

                # ssl date format: 'Mon DD HH:MM:SS YYYY GMT'
                expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                expires_at = expires_at.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_remaining = (expires_at - now).days

                result["expires_at"] = expires_at.isoformat()
                result["days_remaining"] = days_remaining

                if days_remaining < 0:
                    result["status"] = "expired"
                elif days_remaining <= CRITICAL_DAYS:
                    result["status"] = "critical"
                elif days_remaining <= WARNING_DAYS:
                    result["status"] = "warning"
                else:
                    result["status"] = "valid"
    except Exception as exc:  # noqa: BLE001  # cert probe - record any failure mode in result.error
        result["error"] = str(exc)

    return result


def _check_sip2_cert(cert_path: str) -> dict:
    result: dict = {
        "hostname": f"sip2:{cert_path}",
        "port": 0,
        "days_remaining": None,
        "expires_at": None,
        "status": "error",
        "error": None,
    }
    try:
        if not os.path.isfile(cert_path):
            result["error"] = f"Certificate file not found: {cert_path}"
            return result

        # _test_decode_cert is a CPython internal that reads a PEM file
        # and returns the same dict structure as SSLSocket.getpeercert().
        cert_dict = ssl._ssl._test_decode_cert(cert_path)  # type: ignore[attr-defined]

        not_after = cert_dict.get("notAfter")
        if not_after is None:
            result["error"] = "Certificate missing notAfter field"
            return result

        expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_remaining = (expires_at - now).days

        result["expires_at"] = expires_at.isoformat()
        result["days_remaining"] = days_remaining

        if days_remaining < 0:
            result["status"] = "expired"
        elif days_remaining <= CRITICAL_DAYS:
            result["status"] = "critical"
        elif days_remaining <= WARNING_DAYS:
            result["status"] = "warning"
        else:
            result["status"] = "valid"
    except Exception as exc:  # noqa: BLE001  # cert probe - record any failure mode in result.error
        result["error"] = str(exc)

    return result


def _gather_checks() -> list[dict]:
    settings = get_settings()
    results: list[dict] = []

    # 1. Domain certificates from trusted_hosts
    # Filter out localhost / bare IPs — only real domains
    domains = [
        h.strip()
        for h in settings.trusted_hosts.split(",")
        if h.strip() and h.strip() not in ("localhost", "127.0.0.1", "0.0.0.0")
    ]
    for domain in domains:
        result = _check_host_cert(domain, port=443)
        results.append(result)

    # 2. SIP2 TLS certificate (local file)
    if settings.sip2_enabled and settings.sip2_use_tls and settings.sip2_tls_cert:
        result = _check_sip2_cert(settings.sip2_tls_cert)
        results.append(result)

    return results


async def run_certificate_check() -> CertSummary:
    results = await asyncio.to_thread(_gather_checks)

    summary: CertSummary = {
        "total_checked": len(results),
        "valid": 0,
        "warning": 0,
        "critical": 0,
        "expired": 0,
        "errors": 0,
    }

    for r in results:
        status = r["status"]
        host = r["hostname"]
        days = r["days_remaining"]

        if r.get("error"):
            summary["errors"] += 1
            logger.error(
                "Certificate check failed for %s: %s",
                host,
                r["error"],
            )
            continue

        summary[status] += 1  # type: ignore[literal-required]

        if status == "expired":
            logger.critical(
                "Certificate EXPIRED for %s (expired %d days ago)",
                host,
                abs(days),
            )
        elif status == "critical":
            logger.critical(
                "Certificate expiring SOON for %s (%d days remaining)",
                host,
                days,
            )
        elif status == "warning":
            logger.warning(
                "Certificate expiring for %s (%d days remaining)",
                host,
                days,
            )
        else:
            logger.info(
                "Certificate OK for %s (%d days remaining)",
                host,
                days,
            )

    return summary
