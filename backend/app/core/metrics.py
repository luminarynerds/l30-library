# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

# In-memory counters -- reset on restart; durable metrics live in DB tables.
_counters: dict[str, int] = {}
_gauges: dict[str, float] = {}


def increment(metric: str, labels: Optional[dict[str, str]] = None, count: int = 1) -> None:
    key = _build_key(metric, labels)
    _counters[key] = _counters.get(key, 0) + count


def set_gauge(metric: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
    key = _build_key(metric, labels)
    _gauges[key] = value


def get_counter(metric: str, labels: Optional[dict[str, str]] = None) -> int:
    return _counters.get(_build_key(metric, labels), 0)


def get_gauge(metric: str, labels: Optional[dict[str, str]] = None) -> float:
    return _gauges.get(_build_key(metric, labels), 0.0)


def get_all_metrics() -> dict:
    return {
        "counters": dict(_counters),
        "gauges": dict(_gauges),
    }


def _build_key(metric: str, labels: Optional[dict[str, str]] = None) -> str:
    if not labels:
        return metric
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{metric}{{{label_str}}}"
