# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from ..middleware.logging_middleware import get_405_tracker

logger = get_logger(__name__)


class HTTP405MonitoringService:

    # Alert severity thresholds
    CRITICAL_THRESHOLD = 100  # 100+ errors in 1 hour = critical
    HIGH_THRESHOLD = 50      # 50-99 errors in 1 hour = high
    MEDIUM_THRESHOLD = 20    # 20-49 errors in 1 hour = medium

    @staticmethod
    def get_errors_summary() -> Dict:
        tracker = get_405_tracker()

        errors_24h = tracker.get_errors_last_24h()
        errors_1h = tracker.get_errors_last_hour()

        return {
            "total_errors_24h": len(errors_24h),
            "total_errors_1h": len(errors_1h),
            "error_rate_per_hour": len(errors_24h) / 24,
            "peak_hour": _calculate_peak_hour(errors_24h),
            "unique_endpoints": len(tracker.endpoint_errors),
            "unique_clients": len(tracker.client_errors),
        }

    @staticmethod
    def get_top_endpoints(limit: int = 10) -> List[Dict]:
        tracker = get_405_tracker()
        endpoints = tracker.get_top_endpoints(limit=limit)

        # Enrich with additional metrics
        enriched = []
        for ep_data in endpoints:
            endpoint = ep_data["endpoint"]
            method, path = endpoint.split(" ", 1)

            # Find sample errors for debugging
            errors_24h = tracker.get_errors_last_24h()
            sample_errors = [
                e for e in errors_24h
                if e["method"] == method and e["path"] == path
            ]

            enriched.append({
                "endpoint": endpoint,
                "method": method,
                "path": path,
                "error_count": ep_data["count"],
                "last_error": (
                    sample_errors[0]["timestamp"].isoformat()
                    if sample_errors else None
                ),
                "client_ips": list(set(
                    e["client_ip"] for e in sample_errors if e["client_ip"]
                ))[:5],  # Top 5 client IPs
                "sample_user_agents": list(set(
                    e["user_agent"] for e in sample_errors
                ))[:3],  # Sample user agents for debugging
            })

        return enriched

    @staticmethod
    def get_problematic_clients(limit: int = 10) -> List[Dict]:
        tracker = get_405_tracker()
        clients = tracker.get_top_clients(limit=limit)

        enriched = []
        errors_24h = tracker.get_errors_last_24h()

        for client_data in clients:
            client_ip = client_data["client_ip"]
            client_errors = [
                e for e in errors_24h if e["client_ip"] == client_ip
            ]

            # Analyze patterns
            unique_endpoints = len(set(
                f"{e['method']} {e['path']}" for e in client_errors
            ))
            unique_user_agents = len(set(
                e["user_agent"] for e in client_errors
            ))

            enriched.append({
                "client_ip": client_ip,
                "error_count": client_data["count"],
                "unique_endpoints_tried": unique_endpoints,
                "unique_user_agents": unique_user_agents,
                "last_error": (
                    client_errors[0]["timestamp"].isoformat()
                    if client_errors else None
                ),
                "first_error": (
                    client_errors[-1]["timestamp"].isoformat()
                    if client_errors else None
                ),
                "suspected_pattern": _detect_client_pattern(client_errors),
            })

        return enriched

    @staticmethod
    def get_error_trend(hours: int = 24, bucket_minutes: int = 60) -> Dict:
        tracker = get_405_tracker()
        return tracker.get_error_trend(hours=hours, bucket_minutes=bucket_minutes)

    @staticmethod
    def get_alert_status() -> Dict:
        tracker = get_405_tracker()
        errors_1h = len(tracker.get_errors_last_hour())

        if errors_1h >= HTTP405MonitoringService.CRITICAL_THRESHOLD:
            severity = "critical"
            status = "firing"
        elif errors_1h >= HTTP405MonitoringService.HIGH_THRESHOLD:
            severity = "high"
            status = "firing"
        elif errors_1h >= HTTP405MonitoringService.MEDIUM_THRESHOLD:
            severity = "medium"
            status = "warning"
        else:
            severity = "low"
            status = "ok"

        should_alert, count, threshold = tracker.should_alert()

        return {
            "status": status,
            "severity": severity,
            "errors_last_hour": errors_1h,
            "threshold": threshold,
            "should_alert": should_alert,
            "alert_message": (
                f"High 405 error rate: {errors_1h} errors in last hour"
                if should_alert
                else "405 error rate normal"
            ),
        }

    @staticmethod
    def get_debugging_context(method: str, path: str) -> Dict:
        tracker = get_405_tracker()
        errors_24h = tracker.get_errors_last_24h()

        endpoint_errors = [
            e for e in errors_24h
            if e["method"] == method and e["path"] == path
        ]

        if not endpoint_errors:
            return {
                "endpoint": f"{method} {path}",
                "error_count": 0,
                "message": "No recent 405 errors for this endpoint",
            }

        return {
            "endpoint": f"{method} {path}",
            "error_count": len(endpoint_errors),
            "first_occurrence": endpoint_errors[-1]["timestamp"].isoformat(),
            "last_occurrence": endpoint_errors[0]["timestamp"].isoformat(),
            "client_ips": list(set(
                e["client_ip"] for e in endpoint_errors if e["client_ip"]
            )),
            "user_agents": list(set(
                e["user_agent"] for e in endpoint_errors
            )),
            "user_ids_affected": list(set(
                e["user_id"] for e in endpoint_errors if e["user_id"]
            )),
            "sample_errors": [
                {
                    "timestamp": e["timestamp"].isoformat(),
                    "client_ip": e["client_ip"],
                    "user_id": e["user_id"],
                    "user_agent": e["user_agent"],
                    "query_params": e["query_params"],
                }
                for e in endpoint_errors[:5]  # Last 5 errors
            ],
            "remediation_suggestions": _generate_remediation_suggestions(
                method, path
            ),
        }

    @staticmethod
    def get_health_check() -> Dict:
        tracker = get_405_tracker()
        errors_24h = tracker.get_errors_last_24h()

        return {
            "system_status": "operational",
            "events_tracked": len(tracker.events),
            "max_capacity": tracker.MAX_EVENTS,
            "capacity_utilization_percent": (
                len(tracker.events) / tracker.MAX_EVENTS * 100
            ),
            "total_unique_endpoints": len(tracker.endpoint_errors),
            "total_unique_clients": len(tracker.client_errors),
            "errors_24h": len(errors_24h),
            "error_rate_per_hour": len(errors_24h) / 24,
        }


def _calculate_peak_hour(errors: List[Dict]) -> Optional[str]:
    if not errors:
        return None

    hour_counts = {}
    for error in errors:
        hour_key = error["timestamp"].strftime("%Y-%m-%d %H:00")
        hour_counts[hour_key] = hour_counts.get(hour_key, 0) + 1

    if not hour_counts:
        return None

    peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
    return peak_hour


def _detect_client_pattern(errors: List[Dict]) -> str:
    if not errors:
        return "unknown"

    # Check for bot-like behavior: many requests, few unique user agents
    error_count = len(errors)
    unique_user_agents = len(set(e["user_agent"] for e in errors))

    if error_count > 20 and unique_user_agents == 1:
        return "likely_automated_client"

    # Check for bruteforce: many different endpoints
    unique_endpoints = len(set(f"{e['method']} {e['path']}" for e in errors))
    if error_count > 10 and unique_endpoints / error_count > 0.5:
        return "endpoint_enumeration"

    # Check for rapid fire: many errors in short time
    if error_count >= 3:
        time_span = (errors[0]["timestamp"] - errors[-1]["timestamp"]).total_seconds()
        if time_span < 60 and error_count > 3:
            return "rapid_fire_requests"

    return "normal_client_behavior"


def _generate_remediation_suggestions(method: str, path: str) -> List[str]:
    suggestions = []

    if method == "GET":
        suggestions.append(
            f"Ensure GET is supported on {path}. "
            "Check route registration in router."
        )
    elif method == "POST":
        suggestions.append(
            f"Ensure POST is supported on {path}. "
            "Check if endpoint only supports GET or other methods."
        )
    elif method == "DELETE":
        suggestions.append(
            f"Verify {path} supports DELETE method. "
            "May need to add DELETE handler or use POST with _method param."
        )

    suggestions.append(
        "Review route analysis tool output for route conflicts or missing handlers."
    )
    suggestions.append(
        f"Check if path parameters are correctly defined: {path}"
    )
    suggestions.append(
        f"Verify CORS configuration includes {method} method."
    )

    return suggestions
