# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Locust Load Testing Script for L30

Simulates realistic library user behavior with 50+ concurrent users
performing catalog searches, circulation operations, and other common tasks.

Usage:
    locust -f locustfile.py -u 50 -r 5 --run-time 5m http://localhost:8000
    locust -f locustfile.py --web http://localhost:8000 (for web UI)
"""

from locust import HttpUser, task, between, events
import random
import json
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

# Track metrics across all users
GLOBAL_METRICS = {
    'cache_hits': 0,
    'cache_misses': 0,
    'slow_requests': [],  # Requests > 1000ms
    'errors': [],
    'requests_per_endpoint': {}
}


class L30LibraryUser(HttpUser):
    """Simulates a typical L30 library patron or staff member."""

    # Users stay active for 1-5 minutes per session
    wait_time = between(1, 3)

    # Test data for realistic searches
    SEARCH_QUERIES = [
        'fiction', 'mystery', 'science', 'history', 'biography',
        'children', 'young adult', 'cookbook', 'travel', 'business',
        'python', 'javascript', 'machine learning', 'devops', 'kubernetes'
    ]

    ITEM_TYPES = ['Book', 'Ebook', 'AudioBook', 'DVD', 'Magazine']

    def on_start(self):
        """Called when a User instance is created."""
        self.auth_token = None
        self.user_id = None
        self.login()

    def login(self):
        """Authenticate and get JWT token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": f"patron{random.randint(1, 100)}@test.com", "password": "password123"},
            catch_response=True
        )

        if response.status_code == 200:
            self.auth_token = response.json().get("access_token")
            self.user_id = response.json().get("user_id")
        else:
            response.failure(f"Login failed: {response.status_code}")

    def get_headers(self):
        """Get headers with auth token."""
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        return headers

    @task(20)  # Catalog search is the most common operation
    def search_catalog(self):
        """Search catalog with various queries."""
        query = random.choice(self.SEARCH_QUERIES)
        limit = random.choice([10, 20, 50])
        offset = random.randint(0, 200)

        with self.client.get(
            "/api/v1/catalog",
            params={"q": query, "limit": limit, "offset": offset},
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                self._track_request("catalog_search", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(15)  # Advanced search
    def advanced_search(self):
        """Perform advanced catalog search."""
        search_filters = {
            "title": random.choice(self.SEARCH_QUERIES),
            "item_type": random.choice(self.ITEM_TYPES),
            "limit": 20,
        }

        with self.client.get(
            "/api/v1/catalog/advanced",
            params=search_filters,
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
                self._track_request("advanced_search", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"Advanced search failed: {response.status_code}")

    @task(10)  # Unified search across multiple sources
    def unified_search(self):
        """Search across local catalog, OverDrive, Hoopla, etc."""
        query = random.choice(self.SEARCH_QUERIES)

        with self.client.get(
            "/api/v1/search/unified",
            params={"q": query, "limit": 20},
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
                self._track_request("unified_search", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"Unified search failed: {response.status_code}")

    @task(8)
    def view_checkouts(self):
        """View patron's current checkouts."""
        with self.client.get(
            "/api/v1/circulation/checkouts",
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
                self._track_request("view_checkouts", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"View checkouts failed: {response.status_code}")

    @task(5)
    def view_holds(self):
        """View patron's holds."""
        with self.client.get(
            "/api/v1/circulation/holds",
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
                self._track_request("view_holds", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"View holds failed: {response.status_code}")

    @task(4)
    def view_favorites(self):
        """View patron's favorite items."""
        with self.client.get(
            "/api/v1/favorites",
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
                self._track_request("view_favorites", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"View favorites failed: {response.status_code}")

    @task(3)
    def add_to_favorites(self):
        """Add item to favorites."""
        item_id = f"item_{random.randint(1, 10000)}"

        with self.client.post(
            "/api/v1/favorites",
            json={"item_id": item_id},
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400, 401]:
                response.success()
                self._track_request("add_favorite", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"Add favorite failed: {response.status_code}")

    @task(2)
    def view_new_releases(self):
        """View new releases."""
        with self.client.get(
            "/api/v1/releases",
            params={"limit": 20},
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
                self._track_request("new_releases", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"New releases failed: {response.status_code}")

    @task(1)
    def view_staff_picks(self):
        """View staff recommendations."""
        with self.client.get(
            "/api/v1/staff-picks",
            params={"limit": 20},
            headers=self.get_headers(),
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
                self._track_request("staff_picks", response.elapsed.total_seconds() * 1000)
            else:
                response.failure(f"Staff picks failed: {response.status_code}")

    def _track_request(self, endpoint: str, duration_ms: float):
        """Track request metrics."""
        if endpoint not in GLOBAL_METRICS['requests_per_endpoint']:
            GLOBAL_METRICS['requests_per_endpoint'][endpoint] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
            }

        stats = GLOBAL_METRICS['requests_per_endpoint'][endpoint]
        stats['count'] += 1
        stats['total_time'] += duration_ms
        stats['min_time'] = min(stats['min_time'], duration_ms)
        stats['max_time'] = max(stats['max_time'], duration_ms)

        # Track slow requests
        if duration_ms > 1000:
            GLOBAL_METRICS['slow_requests'].append({
                'endpoint': endpoint,
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat()
            })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test is started."""
    logger.info("=== L30 Performance Load Test Started ===")
    logger.info(f"Users: {environment.runner.target_user_count}")
    logger.info(f"Spawn rate: {environment.runner.spawn_rate} users/sec")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test is stopped."""
    logger.info("\n=== L30 Performance Load Test Completed ===")
    print_summary_report()


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track all requests."""
    if exception:
        GLOBAL_METRICS['errors'].append({
            'endpoint': name,
            'error': str(exception),
            'timestamp': datetime.now().isoformat()
        })


def print_summary_report():
    """Print performance summary report."""
    print("\n" + "="*80)
    print("PERFORMANCE TEST SUMMARY REPORT")
    print("="*80)

    print("\nEndpoint Performance:")
    print("-" * 80)
    print(f"{'Endpoint':<30} {'Requests':<12} {'Avg(ms)':<12} {'Min(ms)':<12} {'Max(ms)':<12}")
    print("-" * 80)

    for endpoint, stats in sorted(GLOBAL_METRICS['requests_per_endpoint'].items()):
        avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
        print(f"{endpoint:<30} {stats['count']:<12} {avg_time:<12.2f} {stats['min_time']:<12.2f} {stats['max_time']:<12.2f}")

    print("\nSlow Requests (> 1000ms):")
    print("-" * 80)
    if GLOBAL_METRICS['slow_requests']:
        for req in sorted(GLOBAL_METRICS['slow_requests'], key=lambda x: x['duration_ms'], reverse=True)[:10]:
            print(f"{req['endpoint']:<30} {req['duration_ms']:.2f}ms")
    else:
        print("No slow requests detected!")

    print("\nErrors:")
    print("-" * 80)
    if GLOBAL_METRICS['errors']:
        error_counts = {}
        for error in GLOBAL_METRICS['errors']:
            key = f"{error['endpoint']}: {error['error']}"
            error_counts[key] = error_counts.get(key, 0) + 1
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{error:<60} {count}")
    else:
        print("No errors detected!")

    print("\n" + "="*80)
