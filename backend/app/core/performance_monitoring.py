# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from threading import Lock
from app.core.datetime_utils import utc_now
from app.core.branding import branding

logger = logging.getLogger("app")


def _bytes_to_mb(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value / (1024 * 1024), 3)


@dataclass
class QueryMetrics:

    query: str
    duration_ms: float
    timestamp: datetime
    rows_affected: Optional[int] = None
    is_slow: bool = False
    indices_used: List[str] = field(default_factory=list)
    table_names: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class EndpointMetrics:

    endpoint: str
    method: str
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count: int = 0
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.count if self.count > 0 else 0.0

    @property
    def p95_duration_ms(self) -> Optional[float]:
        if not hasattr(self, '_durations'):
            return None
        if len(self._durations) < 2:
            return max(self._durations) if self._durations else None
        sorted_durations = sorted(self._durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[idx]

    @property
    def p99_duration_ms(self) -> Optional[float]:
        if not hasattr(self, '_durations'):
            return None
        if len(self._durations) < 2:
            return max(self._durations) if self._durations else None
        sorted_durations = sorted(self._durations)
        idx = int(len(sorted_durations) * 0.99)
        return sorted_durations[idx]

    @property
    def error_rate(self) -> float:
        return (self.error_count / self.count * 100) if self.count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'endpoint': self.endpoint,
            'method': self.method,
            'count': self.count,
            'avg_duration_ms': round(self.avg_duration_ms, 2),
            'min_duration_ms': round(self.min_duration_ms, 2),
            'max_duration_ms': round(self.max_duration_ms, 2),
            'p95_duration_ms': round(self.p95_duration_ms, 2) if self.p95_duration_ms else None,
            'p99_duration_ms': round(self.p99_duration_ms, 2) if self.p99_duration_ms else None,
            'error_count': self.error_count,
            'error_rate': round(self.error_rate, 2),
            'status_codes': dict(self.status_codes),
        }


@dataclass
class EndpointMemoryMetrics:

    endpoint: str
    method: str
    count: int = 0
    total_delta_bytes: int = 0
    min_delta_bytes: float = float('inf')
    max_delta_bytes: int = 0
    max_peak_bytes: int = 0
    error_count: int = 0

    @property
    def avg_delta_bytes(self) -> float:
        return self.total_delta_bytes / self.count if self.count > 0 else 0.0

    @property
    def p95_delta_bytes(self) -> Optional[float]:
        if not hasattr(self, '_deltas'):
            return None
        if len(self._deltas) < 2:
            return max(self._deltas) if self._deltas else None
        sorted_deltas = sorted(self._deltas)
        idx = int(len(sorted_deltas) * 0.95)
        return sorted_deltas[idx]

    @property
    def p99_delta_bytes(self) -> Optional[float]:
        if not hasattr(self, '_deltas'):
            return None
        if len(self._deltas) < 2:
            return max(self._deltas) if self._deltas else None
        sorted_deltas = sorted(self._deltas)
        idx = int(len(sorted_deltas) * 0.99)
        return sorted_deltas[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'endpoint': self.endpoint,
            'method': self.method,
            'count': self.count,
            'avg_delta_bytes': round(self.avg_delta_bytes, 2),
            'avg_delta_mb': _bytes_to_mb(self.avg_delta_bytes),
            'min_delta_bytes': round(self.min_delta_bytes, 2) if self.count > 0 else 0.0,
            'min_delta_mb': _bytes_to_mb(self.min_delta_bytes) if self.count > 0 else 0.0,
            'max_delta_bytes': self.max_delta_bytes,
            'max_delta_mb': _bytes_to_mb(self.max_delta_bytes),
            'max_peak_bytes': self.max_peak_bytes,
            'max_peak_mb': _bytes_to_mb(self.max_peak_bytes),
            'p95_delta_bytes': round(self.p95_delta_bytes, 2) if self.p95_delta_bytes else None,
            'p95_delta_mb': _bytes_to_mb(self.p95_delta_bytes),
            'p99_delta_bytes': round(self.p99_delta_bytes, 2) if self.p99_delta_bytes else None,
            'p99_delta_mb': _bytes_to_mb(self.p99_delta_bytes),
            'error_count': self.error_count,
        }


class PerformanceMonitor:

    MAX_QUERY_HISTORY = 5000  # Aggressive cap - was waiting for 10K
    CLEANUP_RETENTION_PERCENTAGE = 0.6  # Keep only 60% when cleanup triggers

    def __init__(
        self,
        slow_query_threshold_ms: float = 500,
        history_retention_hours: int = 24,
        max_samples_per_endpoint: int = 1000,
    ):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.history_retention_hours = history_retention_hours
        self.max_samples_per_endpoint = max_samples_per_endpoint

        # Thread-safe metrics storage
        self._lock = Lock()

        # Query metrics
        self._queries: List[QueryMetrics] = []
        self._slow_queries: List[QueryMetrics] = []
        self._query_frequency: Dict[str, int] = defaultdict(int)

        # Endpoint metrics - use key of "METHOD /path"
        self._endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self._endpoint_durations: Dict[str, List[float]] = defaultdict(list)

        # Endpoint memory metrics
        self._endpoint_memory_metrics: Dict[str, EndpointMemoryMetrics] = {}
        self._endpoint_memory_deltas: Dict[str, List[int]] = defaultdict(list)

        # Startup time for uptime calculation
        self._start_time = utc_now()

    def record_query(
        self,
        query: str,
        duration_ms: float,
        rows_affected: Optional[int] = None,
        indices_used: Optional[List[str]] = None,
        table_names: Optional[List[str]] = None,
    ) -> None:
        is_slow = duration_ms > self.slow_query_threshold_ms

        metrics = QueryMetrics(
            query=query,
            duration_ms=duration_ms,
            timestamp=utc_now(),
            rows_affected=rows_affected,
            is_slow=is_slow,
            indices_used=indices_used or [],
            table_names=table_names or [],
        )

        with self._lock:
            # Store query metrics
            self._queries.append(metrics)

            # Track slow queries separately
            if is_slow:
                self._slow_queries.append(metrics)
                logger.warning(
                    "Slow query detected",
                    extra={
                        'duration_ms': duration_ms,
                        'threshold_ms': self.slow_query_threshold_ms,
                        'query': query[:100],  # First 100 chars
                        'is_slow': True,
                    }
                )

            # Track query frequency (by normalized query pattern)
            query_pattern = self._normalize_query(query)
            self._query_frequency[query_pattern] += 1

            # Cleanup old data
            self._cleanup_old_queries()

    def record_endpoint_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        error: bool = False,
    ) -> None:
        key = f"{method} {endpoint}"

        with self._lock:
            # Create or update endpoint metrics
            if key not in self._endpoint_metrics:
                self._endpoint_metrics[key] = EndpointMetrics(
                    endpoint=endpoint,
                    method=method,
                )

            metrics = self._endpoint_metrics[key]
            metrics.count += 1
            metrics.total_duration_ms += duration_ms
            metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
            metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
            metrics.status_codes[status_code] += 1

            if error:
                metrics.error_count += 1

            # Store duration samples for percentile calculation
            self._endpoint_durations[key].append(duration_ms)

            # Keep only recent samples to manage memory
            if len(self._endpoint_durations[key]) > self.max_samples_per_endpoint:
                self._endpoint_durations[key] = self._endpoint_durations[key][-self.max_samples_per_endpoint:]

            # Store duration samples on metrics object for percentile calculation
            metrics._durations = self._endpoint_durations[key].copy()

    def record_endpoint_memory(
        self,
        endpoint: str,
        method: str,
        delta_bytes: int,
        peak_bytes: int,
        error: bool = False,
    ) -> None:
        key = f"{method} {endpoint}"

        with self._lock:
            if key not in self._endpoint_memory_metrics:
                self._endpoint_memory_metrics[key] = EndpointMemoryMetrics(
                    endpoint=endpoint,
                    method=method,
                )

            metrics = self._endpoint_memory_metrics[key]
            metrics.count += 1
            metrics.total_delta_bytes += delta_bytes
            metrics.min_delta_bytes = min(metrics.min_delta_bytes, delta_bytes)
            metrics.max_delta_bytes = max(metrics.max_delta_bytes, delta_bytes)
            metrics.max_peak_bytes = max(metrics.max_peak_bytes, peak_bytes)

            if error:
                metrics.error_count += 1

            self._endpoint_memory_deltas[key].append(delta_bytes)
            if len(self._endpoint_memory_deltas[key]) > self.max_samples_per_endpoint:
                self._endpoint_memory_deltas[key] = self._endpoint_memory_deltas[key][-self.max_samples_per_endpoint:]

            metrics._deltas = self._endpoint_memory_deltas[key].copy()

    def get_top_memory_endpoints(
        self,
        limit: int = 20,
        min_samples: int = 1,
        path_prefixes: Optional[List[str]] = None,
        sort_by: str = "avg_delta_bytes",
    ) -> List[Dict[str, Any]]:
        with self._lock:
            metrics_list = list(self._endpoint_memory_metrics.values())

        if path_prefixes:
            metrics_list = [
                metric for metric in metrics_list
                if any(metric.endpoint.startswith(prefix) for prefix in path_prefixes)
            ]

        metrics_list = [metric for metric in metrics_list if metric.count >= min_samples]

        sort_key_map = {
            "avg_delta_bytes": lambda metric: metric.avg_delta_bytes,
            "max_delta_bytes": lambda metric: metric.max_delta_bytes,
            "max_peak_bytes": lambda metric: metric.max_peak_bytes,
        }
        sort_key = sort_key_map.get(sort_by, sort_key_map["avg_delta_bytes"])

        sorted_metrics = sorted(metrics_list, key=sort_key, reverse=True)
        return [metric.to_dict() for metric in sorted_metrics[:limit]]

    def get_memory_endpoint_count(self, path_prefixes: Optional[List[str]] = None) -> int:
        with self._lock:
            metrics_list = list(self._endpoint_memory_metrics.values())

        if path_prefixes:
            metrics_list = [
                metric for metric in metrics_list
                if any(metric.endpoint.startswith(prefix) for prefix in path_prefixes)
            ]
        return len(metrics_list)

    def get_slow_queries(
        self,
        limit: Optional[int] = None,
        hours: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            queries = self._slow_queries.copy()

        if hours:
            cutoff = utc_now() - timedelta(hours=hours)
            queries = [q for q in queries if q.timestamp >= cutoff]

        # Sort by duration descending
        queries.sort(key=lambda q: q.duration_ms, reverse=True)

        if limit:
            queries = queries[:limit]

        return [q.to_dict() for q in queries]

    def get_query_frequency(self, top_n: int = 10) -> Dict[str, int]:
        with self._lock:
            frequency = self._query_frequency.copy()

        # Sort by frequency descending
        sorted_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_freq[:top_n])

    def get_endpoint_metrics(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            metrics = {}
            for key, endpoint_metrics in self._endpoint_metrics.items():
                # Ensure _durations is set for percentile calculation
                endpoint_metrics._durations = self._endpoint_durations[key].copy()
                metrics[key] = endpoint_metrics.to_dict()

        return metrics

    def get_endpoint_summary(self, threshold_error_rate: float = 5.0) -> Dict[str, Any]:
        endpoints = self.get_endpoint_metrics()

        problematic = []
        for key, metrics in endpoints.items():
            if metrics['error_rate'] > threshold_error_rate:
                problematic.append({
                    'endpoint': metrics['endpoint'],
                    'method': metrics['method'],
                    'error_rate': metrics['error_rate'],
                    'error_count': metrics['error_count'],
                    'total_requests': metrics['count'],
                })

        return {
            'total_endpoints': len(endpoints),
            'total_requests': sum(m['count'] for m in endpoints.values()),
            'avg_error_rate': sum(m['error_rate'] for m in endpoints.values()) / len(endpoints) if endpoints else 0.0,
            'problematic_endpoints': sorted(problematic, key=lambda x: x['error_rate'], reverse=True),
            'uptime_hours': (utc_now() - self._start_time).total_seconds() / 3600,
        }

    def get_performance_report(self) -> Dict[str, Any]:
        with self._lock:
            slow_query_count = len(self._slow_queries)
            total_query_count = len(self._queries)

        slow_queries = self.get_slow_queries(limit=5)
        query_freq = self.get_query_frequency(top_n=5)
        endpoints = self.get_endpoint_metrics()
        summary = self.get_endpoint_summary()

        # Calculate slowest endpoints
        slowest_endpoints = sorted(
            endpoints.items(),
            key=lambda x: x[1]['avg_duration_ms'],
            reverse=True
        )[:5]

        return {
            'timestamp': utc_now().isoformat(),
            'queries': {
                'total': total_query_count,
                'slow': slow_query_count,
                'slow_rate': (slow_query_count / total_query_count * 100) if total_query_count > 0 else 0.0,
                'threshold_ms': self.slow_query_threshold_ms,
                'top_slow_queries': slow_queries,
                'top_frequent_queries': query_freq,
            },
            'endpoints': {
                'total': summary['total_endpoints'],
                'total_requests': summary['total_requests'],
                'avg_error_rate': round(summary['avg_error_rate'], 2),
                'uptime_hours': round(summary['uptime_hours'], 2),
                'slowest': {key: val for key, val in slowest_endpoints},
                'problematic': summary['problematic_endpoints'],
            },
        }

    def export_prometheus_metrics(self) -> str:
        lines = []

        with self._lock:
            # Query metrics
            lines.append(f"# HELP {branding.METRICS_PREFIX}_slow_queries_total Total number of slow queries")
            lines.append(f"# TYPE {branding.METRICS_PREFIX}_slow_queries_total counter")
            lines.append(f"{branding.METRICS_PREFIX}_slow_queries_total {len(self._slow_queries)}")

            lines.append(f"# HELP {branding.METRICS_PREFIX}_total_queries_total Total number of database queries")
            lines.append(f"# TYPE {branding.METRICS_PREFIX}_total_queries_total counter")
            lines.append(f"{branding.METRICS_PREFIX}_total_queries_total {len(self._queries)}")

            # Endpoint metrics
            for key, metrics in self._endpoint_metrics.items():
                labels = f'method="{metrics.method}",endpoint="{metrics.endpoint}"'

                lines.append(f"# Endpoint: {key}")
                lines.append(f"{branding.METRICS_PREFIX}_endpoint_requests_total{{{labels}}} {metrics.count}")
                lines.append(f"{branding.METRICS_PREFIX}_endpoint_duration_avg_ms{{{labels}}} {metrics.avg_duration_ms:.2f}")
                lines.append(f"{branding.METRICS_PREFIX}_endpoint_duration_max_ms{{{labels}}} {metrics.max_duration_ms:.2f}")
                lines.append(f"{branding.METRICS_PREFIX}_endpoint_errors_total{{{labels}}} {metrics.error_count}")

        return "\n".join(lines)

    def clear_metrics(self) -> None:
        with self._lock:
            self._queries.clear()
            self._slow_queries.clear()
            self._query_frequency.clear()
            self._endpoint_metrics.clear()
            self._endpoint_durations.clear()

    def _normalize_query(self, query: str) -> str:
        # Remove newlines and extra whitespace
        normalized = " ".join(query.split())

        # This is a simple approach - in production, use sqlparse
        # to properly parse and normalize SQL
        return normalized[:200]  # Keep first 200 chars

    def _cleanup_old_queries(self) -> None:
        if len(self._queries) < self.MAX_QUERY_HISTORY:
            return

        cutoff = utc_now() - timedelta(hours=self.history_retention_hours)

        # First: Remove queries older than retention period
        self._queries = [q for q in self._queries if q.timestamp >= cutoff]
        self._slow_queries = [q for q in self._slow_queries if q.timestamp >= cutoff]

        # Second: If still over limit, keep only most recent queries
        if len(self._queries) > self.MAX_QUERY_HISTORY:
            keep_count = int(self.MAX_QUERY_HISTORY * self.CLEANUP_RETENTION_PERCENTAGE)
            self._queries = self._queries[-keep_count:]

            # Rebuild slow_queries from retained queries
            self._slow_queries = [q for q in self._queries if q.is_slow]


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = Lock()


def get_monitor() -> PerformanceMonitor:
    global _monitor

    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = PerformanceMonitor()

    return _monitor


def reset_monitor(
    slow_query_threshold_ms: float = 500,
    history_retention_hours: int = 24,
) -> PerformanceMonitor:
    global _monitor

    with _monitor_lock:
        _monitor = PerformanceMonitor(
            slow_query_threshold_ms=slow_query_threshold_ms,
            history_retention_hours=history_retention_hours,
        )

    return _monitor
