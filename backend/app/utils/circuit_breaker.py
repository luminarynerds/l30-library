# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
import time
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")

_cb_logger = get_logger(__name__)


class CircuitBreakerState(StrEnum):
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Service is down
    HALF_OPEN = "half_open"   # Testing recovery


class CircuitBreakerException(Exception):
    pass


class CircuitBreaker(Generic[T]):

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        max_timeout: int = 300,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.max_timeout = max_timeout

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

    def _should_attempt_reset(self) -> bool:
        if self.state != CircuitBreakerState.OPEN:
            return False

        if not self.last_failure_time:
            return True

        timeout = self.recovery_timeout
        if self.opened_at:
            elapsed = (datetime.now(timezone.utc) - self.opened_at).total_seconds()
            # Exponential backoff: increase timeout with each consecutive failure
            timeout = min(self.max_timeout, self.recovery_timeout * (2 ** (self.failure_count // self.failure_threshold)))

        return (datetime.now(timezone.utc) - self.last_failure_time).total_seconds() > timeout

    def _emit_state_change(self, from_state: str, to_state: str, reason: str = "") -> None:
        try:
            from ..core.metrics import increment
            increment("circuit_breaker_state_change_total", {
                "breaker": self.name, "from": from_state, "to": to_state,
            })
        except Exception:  # noqa: BLE001  # observability metric emit must not break the breaker
            _cb_logger.debug("Failed to emit circuit breaker state change metric for %s", self.name)
        _cb_logger.warning(
            f"Circuit breaker '{self.name}' state change: {from_state} -> {to_state}",
            extra={"breaker": self.name, "from_state": from_state, "to_state": to_state, "reason": reason},
        )

    def _on_success(self) -> None:
        self.failure_count = 0

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                prev = self.state.value
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0
                self._emit_state_change(prev, "closed", "service recovered")

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.state == CircuitBreakerState.HALF_OPEN:
            prev = self.state.value
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            self.opened_at = datetime.now(timezone.utc)
            self._emit_state_change(prev, "open", "failure during recovery attempt")

        elif self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
            prev = self.state.value
            self.state = CircuitBreakerState.OPEN
            self.opened_at = datetime.now(timezone.utc)
            self._emit_state_change(prev, "open", f"{self.failure_count} consecutive failures")

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        # Check if we should attempt recovery
        if self._should_attempt_reset():
            prev = self.state.value
            self.state = CircuitBreakerState.HALF_OPEN
            self.success_count = 0
            self._emit_state_change(prev, "half_open", "attempting recovery")

        # Open circuit - fail immediately
        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerException(
                f"Circuit breaker '{self.name}' is open. Service is unavailable."
            )

        # Execute the call
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }

    def reset(self) -> None:
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None


class CircuitBreakerManager:

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self.breakers[name]

    def get_all_states(self) -> dict:
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
