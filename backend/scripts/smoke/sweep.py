# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sweep all API endpoints and categorize responses."""
import asyncio
import re
import sys
import time
from dataclasses import dataclass, field

import httpx

sys.path.insert(0, "/opt/l30/backend")
from scripts.smoke.auth import get_auth_headers
from scripts.smoke.discover import discover_routes


BASE_URL = "http://localhost:8000"
TIMEOUT = 15.0
CONCURRENCY = 10

# Default values for common path parameter patterns
PATH_PARAM_DEFAULTS = {
    "user_id": "1", "item_id": "1", "id": "1", "patron_id": "1",
    "checkout_id": "1", "hold_id": "1", "fine_id": "1", "event_id": "1",
    "meeting_id": "1", "drawer_id": "1", "session_id": "1",
    "transaction_id": "1", "course_id": "1", "lesson_id": "1",
    "branch_id": "1", "role_id": "1", "report_id": "1", "room_id": "1",
    "booking_id": "1", "equipment_id": "1", "vendor_id": "1",
    "po_id": "1", "order_id": "1", "program_id": "1", "club_id": "1",
    "motion_id": "1", "committee_id": "1", "document_id": "1",
    "notification_id": "1", "strain_id": "1", "agent_id": "1",
    "plan_id": "1", "goal_id": "1", "milestone_id": "1",
    "workflow_id": "1", "slug": "test", "seriesSlug": "test",
    "meetingId": "1", "motionId": "1", "committeeId": "1",
    "courseId": "1", "lessonId": "1", "eventId": "1",
}


def substitute_path_params(path: str) -> str:
    """Replace {param_name} placeholders with reasonable defaults."""
    def replacer(match):
        param = match.group(1)
        return PATH_PARAM_DEFAULTS.get(param, "1")
    return re.sub(r"\{(\w+)\}", replacer, path)


@dataclass
class EndpointResult:
    method: str
    path: str
    status: int = 0
    response_time: float = 0.0
    error: str = ""
    content_type: str = ""
    body_size: int = 0

    @property
    def category(self) -> str:
        if self.error:
            return "RED"
        if self.status >= 500:
            return "RED"
        if self.status in (200, 201, 204):
            return "GREEN"
        if self.status in (401, 403):
            return "YELLOW"
        if self.status == 404:
            return "YELLOW"
        if self.status == 405:
            return "YELLOW"
        return "YELLOW"


async def hit_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    headers: dict,
    sem: asyncio.Semaphore,
) -> EndpointResult:
    """Hit a single endpoint and return the result."""
    result = EndpointResult(method=method, path=path)
    async with sem:
        try:
            start = time.monotonic()
            if method != "GET":
                result.status = -1
                result.error = "skipped (non-GET)"
                return result

            url = f"{BASE_URL}{substitute_path_params(path)}"
            resp = await client.get(
                url, headers=headers, timeout=TIMEOUT, follow_redirects=True,
            )
            result.response_time = time.monotonic() - start
            result.status = resp.status_code
            result.content_type = resp.headers.get("content-type", "")
            result.body_size = len(resp.content)
        except httpx.TimeoutException:
            result.error = "TIMEOUT"
        except httpx.ConnectError:
            result.error = "CONNECTION_REFUSED"
        except Exception as e:
            result.error = str(e)[:200]
    return result


async def run_sweep(include_mutations: bool = False) -> list[EndpointResult]:
    """Sweep all discovered endpoints."""
    routes = discover_routes()
    headers = get_auth_headers()
    sem = asyncio.Semaphore(CONCURRENCY)

    if not include_mutations:
        routes = [r for r in routes if r["method"] == "GET"]

    print(f"Sweeping {len(routes)} endpoints...")

    async with httpx.AsyncClient() as client:
        tasks = [
            hit_endpoint(client, r["method"], r["path"], headers, sem)
            for r in routes
        ]
        results = await asyncio.gather(*tasks)

    return list(results)


def validate_pdf_endpoints(results: list[EndpointResult]) -> list[str]:
    """Check that PDF/report endpoints return proper content types."""
    issues = []
    pdf_keywords = ["pdf", "report", "export", "download", "receipt", "slip"]
    for r in results:
        path_lower = r.path.lower()
        is_pdf_endpoint = any(kw in path_lower for kw in pdf_keywords)
        if not is_pdf_endpoint or r.category != "GREEN":
            continue
        ct = r.content_type.lower()
        if "application/pdf" not in ct and "text/csv" not in ct and "application/octet-stream" not in ct and "application/vnd" not in ct:
            if "application/json" in ct:
                continue
            issues.append(f"  {r.method} {r.path} -> unexpected content-type: {r.content_type}")
        if r.body_size == 0:
            issues.append(f"  {r.method} {r.path} -> empty response body (0 bytes)")
    return issues


def print_report(results: list[EndpointResult]) -> None:
    """Print a categorized report."""
    red = [r for r in results if r.category == "RED"]
    yellow = [r for r in results if r.category == "YELLOW"]
    green = [r for r in results if r.category == "GREEN"]
    skipped = [r for r in results if r.status == -1]

    print(f"\n{'='*70}")
    print(f"SMOKE TEST REPORT")
    print(f"{'='*70}")
    print(f"  Total: {len(results)}  |  "
          f"\033[32mGREEN: {len(green)}\033[0m  |  "
          f"\033[33mYELLOW: {len(yellow)}\033[0m  |  "
          f"\033[31mRED: {len(red)}\033[0m  |  "
          f"Skipped: {len(skipped)}")
    print(f"{'='*70}")

    if red:
        print(f"\n\033[31m--- RED (Broken) ---\033[0m")
        for r in sorted(red, key=lambda x: x.path):
            err = f" error={r.error}" if r.error else ""
            print(f"  {r.method:6s} {r.path}  [{r.status}]{err}")

    if yellow:
        print(f"\n\033[33m--- YELLOW (Needs Review) ---\033[0m")
        for r in sorted(yellow, key=lambda x: x.path):
            err = f" error={r.error}" if r.error else ""
            print(f"  {r.method:6s} {r.path}  [{r.status}]{err}")

    slow = [r for r in results if r.response_time > 2.0 and r.category == "GREEN"]
    if slow:
        print(f"\n\033[33m--- SLOW (>2s) ---\033[0m")
        for r in sorted(slow, key=lambda x: -x.response_time):
            print(f"  {r.method:6s} {r.path}  [{r.response_time:.1f}s]")

    pdf_issues = validate_pdf_endpoints(results)
    if pdf_issues:
        print(f"\n\033[33m--- PDF/REPORT ISSUES ---\033[0m")
        for issue in pdf_issues:
            print(issue)

    print()


if __name__ == "__main__":
    results = asyncio.run(run_sweep())
    print_report(results)
