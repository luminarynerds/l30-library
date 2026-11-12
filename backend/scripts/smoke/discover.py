# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Discover all registered API routes from the FastAPI app."""
import sys
sys.path.insert(0, "/opt/l30/backend")

from app.main import app
from app.api.v1.registry import register_all_routers


def discover_routes() -> list[dict]:
    """Return every registered route as {method, path, tags, name}."""
    # Routers are registered lazily in startup event, so force registration
    register_all_routers(app)

    routes = []
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        path = route.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            routes.append({
                "method": method,
                "path": path,
                "tags": getattr(route, "tags", []),
                "name": getattr(route, "name", ""),
            })
    return sorted(routes, key=lambda r: (r["path"], r["method"]))


if __name__ == "__main__":
    routes = discover_routes()
    print(f"Discovered {len(routes)} endpoints")
    for r in routes[:20]:
        print(f"  {r['method']:6s} {r['path']}")
    if len(routes) > 20:
        print(f"  ... and {len(routes) - 20} more")
