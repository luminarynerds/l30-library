# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""QueryCounterMiddleware - wired in main.py via app.add_middleware(QueryCounterMiddleware, threshold=10)."""

import contextvars
from app.core.logging import get_logger
import time
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = get_logger(__name__)

# ContextVar holds the per-request counter.  It is automatically
# scoped to each asyncio task, which maps 1-to-1 to a Starlette
# request in production (using the standard ASGI lifecycle).
_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "sql_query_count", default=0
)

# Expose the ContextVar for use by the event listener
query_count_var = _query_count


def increment_query_count() -> None:
    _query_count.set(_query_count.get(0) + 1)


def get_query_count() -> int:
    return _query_count.get(0)


def install_query_counter_hook(engine) -> None:
    """For async engines, listen on the underlying sync engine -
    SQLAlchemy dispatches cursor-level events on the sync side."""
    from sqlalchemy import event

    target = engine.sync_engine if hasattr(engine, "sync_engine") else engine

    @event.listens_for(target, "before_cursor_execute")
    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        increment_query_count()


class QueryCounterMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, threshold: int = 10, debug: bool = False):
        super().__init__(app)
        self.threshold = threshold
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Reset counter for this request
        token = _query_count.set(0)
        try:
            response = await call_next(request)

            count = _query_count.get(0)

            if count > self.threshold:
                logger.warning(
                    "High SQL query count detected",
                    extra={
                        "query_count": count,
                        "threshold": self.threshold,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )

            if self.debug:
                response.headers["X-Query-Count"] = str(count)

            return response
        finally:
            _query_count.reset(token)
