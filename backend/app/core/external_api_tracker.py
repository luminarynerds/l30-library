# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
from contextlib import asynccontextmanager
from typing import Optional

from .logging import get_logger
from .metrics import increment, set_gauge

logger = get_logger(__name__)


@asynccontextmanager
async def track_external_call(service: str, endpoint: str = ""):
    start = time.monotonic()
    status = "success"
    try:
        yield
    except Exception as exc:
        exc_type = type(exc).__name__
        if "Timeout" in exc_type:
            status = "timeout"
        elif "ConnectionError" in exc_type or "OSError" in exc_type:
            status = "connection_error"
        else:
            status = "error"
        raise
    finally:
        elapsed = time.monotonic() - start
        increment("external_api_call_total", {"service": service, "status": status})
        set_gauge("external_api_latency_seconds", elapsed, {"service": service})

        if status != "success":
            logger.warning(
                f"External API call to {service} failed",
                extra={
                    "service": service,
                    "endpoint": endpoint,
                    "status": status,
                    "latency_seconds": round(elapsed, 3),
                },
            )
