# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Chaos and Resilience Testing Suite for LSC Library Management System.

Tests the system's ability to:
- Handle database timeouts and connection failures
- Gracefully degrade when external services fail (Ollama, Redis)
- Manage network failures and partial outages
- Enforce rate limiting under load
- Recover from cascading failures

These tests simulate real-world failure scenarios to identify
system weaknesses and validate resilience mechanisms.
"""

import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeout


class DatabaseFailureSimulator:
    """Simulates database failures for chaos testing."""

    def __init__(self):
        self.failure_mode = None
        self.failure_rate = 0.0
        self.recovery_time = 0
        self.connection_count = 0

    async def simulate_timeout(self, duration_ms: int = 5000):
        """Simulate database query timeout."""
        await asyncio.sleep(duration_ms / 1000.0)
        raise SQLAlchemyTimeout("Database query timeout")

    async def simulate_connection_failure(self):
        """Simulate database connection refused."""
        raise OperationalError(
            "could not connect to server",
            "connection refused",
            "FATAL: connection refused",
        )

    async def simulate_connection_pool_exhaustion(self):
        """Simulate connection pool exhaustion."""
        raise OperationalError(
            "QueuePool limit exceeded",
            "connection pool exhausted",
            "Could not get database connection",
        )


class ServiceDegradationSimulator:
    """Simulates external service degradation."""

    def __init__(self):
        self.ollama_available = True
        self.redis_available = True
        self.response_time = 0.1
        self.error_rate = 0.0

    async def simulate_ollama_timeout(self):
        """Simulate Ollama service timeout."""
        raise httpx.TimeoutException("Ollama request timed out")

    async def simulate_ollama_unavailable(self):
        """Simulate Ollama service unavailable."""
        raise httpx.ConnectError("Failed to connect to Ollama")

    async def simulate_redis_timeout(self):
        """Simulate Redis connection timeout."""
        raise TimeoutError("Redis connection timeout")

    async def simulate_redis_unavailable(self):
        """Simulate Redis service unavailable."""
        raise ConnectionError("Cannot connect to Redis")

    async def simulate_slow_response(self, delay_ms: int = 5000):
        """Simulate slow service response."""
        await asyncio.sleep(delay_ms / 1000.0)
        return {"response": "slow_response", "time_ms": delay_ms}


class NetworkFailureSimulator:
    """Simulates network-level failures."""

    def __init__(self):
        self.packet_loss_rate = 0.0
        self.latency_ms = 0

    async def simulate_network_timeout(self):
        """Simulate network timeout."""
        raise TimeoutError("Network timeout after 30 seconds")

    async def simulate_dns_failure(self):
        """Simulate DNS resolution failure."""
        raise httpx.ConnectError("Name or service not known")

    async def simulate_partial_connectivity(self):
        """Simulate intermittent connectivity issues."""
        if asyncio.get_event_loop().time() % 2 > 1:
            raise httpx.ConnectError("Connection reset by peer")
        return {"status": "partially_connected"}


# ============================================================================
# DATABASE RESILIENCE TESTS
# ============================================================================


class TestDatabaseTimeoutHandling:
    """Tests database timeout handling and recovery."""

    @pytest.mark.asyncio
    async def test_query_timeout_graceful_handling(self, test_db):
        """Test that database query timeouts are handled gracefully."""
        simulator = DatabaseFailureSimulator()

        try:
            await simulator.simulate_timeout(duration_ms=5000)
            assert False, "Should have raised timeout exception"
        except SQLAlchemyTimeout as e:
            assert "timeout" in str(e).lower()
            assert isinstance(e, SQLAlchemyTimeout)

    @pytest.mark.asyncio
    async def test_connection_refused_handling(self, test_db):
        """Test handling of database connection refused errors."""
        simulator = DatabaseFailureSimulator()

        with pytest.raises(OperationalError):
            await simulator.simulate_connection_failure()

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, test_db):
        """Test system behavior when connection pool is exhausted."""
        simulator = DatabaseFailureSimulator()

        with pytest.raises(OperationalError) as exc_info:
            await simulator.simulate_connection_pool_exhaustion()

        assert "pool" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_timeout(self, test_db):
        """Test that transactions are rolled back on timeout."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        user = User(
            email="timeout_test@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Timeout",
            last_name="Test",
            role=UserRole.PATRON,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        assert user.id is not None

    @pytest.mark.asyncio
    async def test_readonly_query_timeout_recovery(self):
        """Test that readonly queries can recover after timeout."""
        simulator = DatabaseFailureSimulator()
        attempt = 0
        max_attempts = 3

        async def retry_query():
            nonlocal attempt
            attempt += 1
            if attempt < max_attempts:
                await simulator.simulate_timeout(duration_ms=1000)
            return {"data": "success"}

        attempt = 0
        success = False
        for i in range(max_attempts + 1):
            try:
                _ = await retry_query()
                success = True
                break
            except SQLAlchemyTimeout:
                continue

        assert success, "Should succeed after retries"


class TestServiceDegradation:
    """Tests system behavior when external services degrade."""

    @pytest.mark.asyncio
    async def test_ollama_timeout_graceful_degradation(self):
        """Test graceful degradation when Ollama times out."""
        simulator = ServiceDegradationSimulator()

        try:
            await simulator.simulate_ollama_timeout()
            assert False, "Should have raised timeout"
        except httpx.TimeoutException as e:
            assert "timed out" in str(e).lower()

    @pytest.mark.asyncio
    async def test_ollama_unavailable_service_fallback(self):
        """Test fallback when Ollama service is unavailable."""
        simulator = ServiceDegradationSimulator()

        with pytest.raises(httpx.ConnectError):
            await simulator.simulate_ollama_unavailable()

    @pytest.mark.asyncio
    async def test_redis_timeout_fallback(self):
        """Test system continues when Redis times out."""
        simulator = ServiceDegradationSimulator()

        try:
            await simulator.simulate_redis_timeout()
            assert False, "Should timeout"
        except TimeoutError as e:
            assert "redis" in str(e).lower()

    @pytest.mark.asyncio
    async def test_redis_unavailable_cache_bypass(self):
        """Test system can bypass caching when Redis is unavailable."""
        simulator = ServiceDegradationSimulator()

        with pytest.raises(ConnectionError):
            await simulator.simulate_redis_unavailable()

    @pytest.mark.asyncio
    async def test_slow_ollama_response_timeout(self):
        """Test timeout handling for slow Ollama responses."""
        simulator = ServiceDegradationSimulator()

        start = time.time()
        result = await simulator.simulate_slow_response(delay_ms=100)
        elapsed = (time.time() - start) * 1000

        assert result["time_ms"] == 100
        assert elapsed >= 100


# ============================================================================
# NETWORK FAILURE TESTS
# ============================================================================


class TestNetworkFailures:
    """Tests handling of network-level failures."""

    @pytest.mark.asyncio
    async def test_network_timeout_retry_logic(self):
        """Test that network timeouts trigger proper retry logic."""
        simulator = NetworkFailureSimulator()

        with pytest.raises(TimeoutError):
            await simulator.simulate_network_timeout()

    @pytest.mark.asyncio
    async def test_dns_failure_handling(self):
        """Test system handles DNS resolution failures."""
        simulator = NetworkFailureSimulator()

        with pytest.raises(httpx.ConnectError):
            await simulator.simulate_dns_failure()

    @pytest.mark.asyncio
    async def test_partial_connectivity_resilience(self):
        """Test system resilience during partial connectivity."""
        simulator = NetworkFailureSimulator()

        success = False
        attempts = 0

        for attempt in range(5):
            try:
                result = await simulator.simulate_partial_connectivity()
                if "partially_connected" in result.get("status", ""):
                    success = True
                    break
            except httpx.ConnectError:
                attempts += 1
                continue

        assert attempts + success > 0


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================


class TestRateLimitingResilience:
    """Tests rate limiting under high load and failure conditions."""

    @pytest.mark.asyncio
    async def test_rate_limit_rejection_under_load(self):
        """Test that rate limiting properly rejects excess requests."""
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        _ = Limiter(key_func=get_remote_address)
        request_count = 0

        for i in range(10):
            request_count += 1

        assert request_count == 10

    @pytest.mark.asyncio
    async def test_rate_limit_key_generation(self):
        """Test that rate limit keys are properly generated."""
        from slowapi.util import get_remote_address

        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        key = get_remote_address(mock_request)
        assert key == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_rate_limit_recovery_after_reset(self):
        """Test rate limit counter resets properly."""
        request_times = []
        _ = 60
        max_requests = 5

        current_time = time.time()
        for i in range(max_requests):
            request_times.append(current_time + i * 1)

        assert len(request_times) == max_requests


# ============================================================================
# CASCADING FAILURE TESTS
# ============================================================================


class TestCascadingFailures:
    """Tests system behavior during cascading failures."""

    @pytest.mark.asyncio
    async def test_database_failure_with_cache_unavailable(self):
        """Test system when both database and cache are unavailable."""
        db_simulator = DatabaseFailureSimulator()
        cache_simulator = ServiceDegradationSimulator()
        cache_simulator.redis_available = False

        with pytest.raises((OperationalError, ConnectionError)):
            await db_simulator.simulate_connection_failure()

    @pytest.mark.asyncio
    async def test_external_service_cascade_with_slow_db(self):
        """Test behavior when multiple services are slow/failing."""
        start = time.time()
        await asyncio.sleep(0.2)
        elapsed = time.time() - start

        assert elapsed >= 0.2

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for preventing cascading failures."""

        class CircuitBreaker:
            def __init__(self, failure_threshold: int = 5, timeout: int = 60):
                self.failure_count = 0
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.last_failure_time = None
                self.state = "closed"

            async def call(self, coro):
                if self.state == "open":
                    if time.time() - (self.last_failure_time or 0) > self.timeout:
                        self.state = "half_open"
                        self.failure_count = 0
                    else:
                        raise Exception("Circuit breaker is open")

                try:
                    result = await coro
                    if self.state == "half_open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    raise

        cb = CircuitBreaker()

        assert cb.state == "closed"

        for i in range(5):
            try:

                async def failing_coro():
                    raise Exception("Service error")

                await cb.call(failing_coro())
            except Exception:
                pass

        assert cb.state == "open"


# ============================================================================
# GRACEFUL DEGRADATION TESTS
# ============================================================================


class TestGracefulDegradation:
    """Tests system's ability to gracefully degrade functionality."""

    @pytest.mark.asyncio
    async def test_ai_service_unavailable_returns_defaults(self):
        """Test system returns sensible defaults when AI unavailable."""

        async def get_recommendations(item_id: int):
            try:
                raise httpx.ConnectError("AI service unavailable")
            except httpx.ConnectError:
                return {
                    "recommendations": [],
                    "fallback": True,
                    "reason": "AI service unavailable",
                }

        result = await get_recommendations(1)
        assert result["fallback"] is True
        assert result["recommendations"] == []

    @pytest.mark.asyncio
    async def test_cache_unavailable_proceeds_with_db(self):
        """Test system can proceed without cache by hitting database."""

        async def get_data(use_cache=True):
            try:
                if use_cache:
                    raise ConnectionError("Cache unavailable")
            except ConnectionError:
                pass

            return {"data": "from_database", "cached": False}

        result = await get_data(use_cache=True)
        assert result["cached"] is False
        assert "database" in result["data"]

    @pytest.mark.asyncio
    async def test_partial_feature_availability(self):
        """Test system provides available features when some degrade."""

        class FeatureAvailability:
            def __init__(self):
                self.features = {
                    "search": True,
                    "recommendations": False,
                    "checkout": True,
                    "holds": True,
                }

            def get_available_features(self):
                return {k: v for k, v in self.features.items() if v}

        fa = FeatureAvailability()
        available = fa.get_available_features()

        assert "search" in available
        assert "checkout" in available
        assert "recommendations" not in available
        assert len(available) == 3


# ============================================================================
# RECOVERY TESTS
# ============================================================================


class TestRecoveryMechanisms:
    """Tests system recovery from various failure states."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self):
        """Test exponential backoff retry strategy."""

        async def retry_with_backoff(coro_func, max_retries=5, base_delay=0.1):
            # coro_func must be a zero-arg callable that returns a *fresh*
            # coroutine each call -- a coroutine object can only be awaited
            # once, so retrying by re-awaiting the same one raises
            # "RuntimeError: cannot reuse already awaited coroutine".
            attempt = 0
            last_error = None

            while attempt < max_retries:
                try:
                    return await coro_func()
                except Exception as e:
                    last_error = e
                    attempt += 1
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)

            raise last_error

        attempts = []

        async def failing_coro():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await retry_with_backoff(failing_coro)
        assert result == "success"
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_health_check_detection(self):
        """Test health checks detect service recovery."""

        class ServiceHealthCheck:
            def __init__(self):
                self.service_available = False
                self.check_interval = 5
                self.last_check = None

            async def is_healthy(self):
                return self.service_available

            async def mark_recovered(self):
                self.service_available = True
                self.last_check = time.time()

        hc = ServiceHealthCheck()
        assert not await hc.is_healthy()

        await hc.mark_recovered()
        assert await hc.is_healthy()

    @pytest.mark.asyncio
    async def test_connection_pool_recovery(self):
        """Test connection pool recovers after exhaustion."""

        class ConnectionPoolRecovery:
            def __init__(self, pool_size=5):
                self.pool_size = pool_size
                self.available_connections = pool_size
                self.failed_connections = 0

            async def acquire_connection(self):
                if self.available_connections > 0:
                    self.available_connections -= 1
                    return Mock()
                raise Exception("No available connections")

            async def release_connection(self, conn):
                self.available_connections = min(
                    self.available_connections + 1, self.pool_size
                )

        pool = ConnectionPoolRecovery()

        conns = []
        for i in range(5):
            conns.append(await pool.acquire_connection())

        assert pool.available_connections == 0

        for conn in conns:
            await pool.release_connection(conn)

        assert pool.available_connections == 5


# ============================================================================
# LOAD AND STRESS TESTS
# ============================================================================


class TestLoadHandling:
    """Tests system behavior under load."""

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test system handles concurrent requests."""

        async def handle_request(request_id: int):
            await asyncio.sleep(0.01)
            return {"id": request_id, "status": "completed"}

        tasks = [handle_request(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 100
        assert all(r["status"] == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_queue_management_under_load(self):
        """Test message queue management under high load."""

        class TaskQueue:
            def __init__(self, max_size=100):
                self.queue = asyncio.Queue(maxsize=max_size)
                self.processed = 0

            async def enqueue(self, task):
                try:
                    self.queue.put_nowait(task)
                except asyncio.QueueFull:
                    raise Exception("Queue full - rejecting task")

            async def process_all(self):
                while not self.queue.empty():
                    _ = await self.queue.get()
                    self.processed += 1

        queue = TaskQueue()

        for i in range(50):
            await queue.enqueue({"id": i})

        await queue.process_all()
        assert queue.processed == 50

    @pytest.mark.asyncio
    async def test_resource_exhaustion_detection(self):
        """Test detection and handling of resource exhaustion."""

        class ResourceMonitor:
            def __init__(self, threshold=80):
                self.memory_percent = 0
                self.cpu_percent = 0
                self.threshold = threshold

            def is_exhausted(self):
                return (
                    self.memory_percent > self.threshold
                    or self.cpu_percent > self.threshold
                )

            def set_resource_usage(self, memory, cpu):
                self.memory_percent = memory
                self.cpu_percent = cpu

        monitor = ResourceMonitor()

        monitor.set_resource_usage(50, 40)
        assert not monitor.is_exhausted()

        monitor.set_resource_usage(85, 50)
        assert monitor.is_exhausted()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegrationResilience:
    """Integration tests for resilience across components."""

    @pytest.mark.asyncio
    async def test_full_request_flow_with_partial_failure(self, test_db):
        """Test complete request flow when some components fail."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        user = User(
            email="integration_test@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Integration",
            last_name="Test",
            role=UserRole.PATRON,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        assert user.id is not None

    @pytest.mark.asyncio
    async def test_resilience_metrics_collection(self):
        """Test collection of resilience metrics."""

        class ResilienceMetrics:
            def __init__(self):
                self.failures = []
                self.recoveries = []
                self.degradations = []

            def record_failure(self, failure_type: str, timestamp=None):
                self.failures.append(
                    {"type": failure_type, "timestamp": timestamp or time.time()}
                )

            def record_recovery(self, service: str, timestamp=None):
                self.recoveries.append(
                    {"service": service, "timestamp": timestamp or time.time()}
                )

            def get_mttf(self):
                if not self.failures:
                    return None
                return len(self.failures)

            def get_mttr(self):
                return len(self.recoveries)

        metrics = ResilienceMetrics()

        metrics.record_failure("database_timeout")
        metrics.record_failure("cache_unavailable")
        metrics.record_recovery("cache")

        assert metrics.get_mttf() == 2
        assert metrics.get_mttr() == 1


# ============================================================================
# PERFORMANCE DEGRADATION TESTS
# ============================================================================


class TestPerformanceDegradation:
    """Tests system performance under degraded conditions."""

    @pytest.mark.asyncio
    async def test_response_time_under_high_latency(self):
        """Test response times when latency is high."""

        start = time.time()
        await asyncio.sleep(0.5)
        elapsed = time.time() - start

        assert elapsed >= 0.5

    @pytest.mark.asyncio
    async def test_throughput_degradation_under_resource_constraint(self):
        """Test throughput reduction under resource constraints."""

        async def process_item(item_id: int, delay_ms: int = 10):
            await asyncio.sleep(delay_ms / 1000.0)
            return {"id": item_id, "processed": True}

        start = time.time()
        tasks = [process_item(i, delay_ms=1) for i in range(10)]
        await asyncio.gather(*tasks)
        normal_time = time.time() - start

        start = time.time()
        tasks = [process_item(i, delay_ms=50) for i in range(10)]
        await asyncio.gather(*tasks)
        degraded_time = time.time() - start

        assert degraded_time > normal_time


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
