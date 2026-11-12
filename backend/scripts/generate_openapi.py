#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Generate OpenAPI specification from FastAPI application.

Creates openapi.json file that documents all API endpoints,
including which ones should have seeded test data.

Output is deterministic: identical invocations against an unchanged
schema produce byte-identical files. This is enforced by

  1. Sorting `unique_models` by fully-qualified name before FastAPI
     builds its `model_name_map` (otherwise set-iteration order
     decides which class wins a colliding short name, e.g.
     `CatalogItemResponse` vs `app__schemas__catalog__CatalogItemResponse`,
     and that varies per process).
  2. Passing `sort_keys=True` to `json.dump`.

Usage:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output ./docs/api.json
"""

import sys
import os
import json
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# --- determinism patch: must run before `from app.main import app` so that
# the first call to `app.openapi()` sees the sorted iteration order. -------
import fastapi._compat.v2 as _fastapi_v2  # noqa: E402

_ORIGINAL_GET_MODEL_NAME_MAP = _fastapi_v2.get_model_name_map


def _deterministic_get_model_name_map(unique_models):
    """Drop-in replacement that sorts models before naming.

    FastAPI's stock implementation iterates a `set`, so when two Pydantic
    classes share a `__name__` (common in this codebase: e.g. multiple
    `CatalogItemResponse` classes across routers), which one wins the
    short name and which gets the fully-qualified fallback depends on
    set hash-iteration order — non-deterministic across Python processes.
    Sorting by `module.qualname` gives the same winner every run.
    """
    sorted_models = sorted(
        unique_models,
        key=lambda m: f"{getattr(m, '__module__', '')}.{getattr(m, '__qualname__', m.__name__)}",
    )
    name_model_map = {}
    for model in sorted_models:
        model_name = _fastapi_v2.normalize_name(model.__name__)
        name_model_map[model_name] = model
    return {v: k for k, v in name_model_map.items()}


_fastapi_v2.get_model_name_map = _deterministic_get_model_name_map

# --- operationId determinism patch: sort methods before picking the first ---
# FastAPI's generate_unique_id does `list(route.methods)[0]` where methods is
# a set — non-deterministic when a route accepts multiple HTTP methods (e.g.
# GET+POST on the same handler).  Sort first so GET always beats POST.
#
# The tricky part: APIRoute.__init__ captures generate_unique_id in a
# DefaultPlaceholder at module-import time.  Patching fastapi.utils /
# fastapi.routing after the fact has no effect because the Default object
# already holds the old reference.  We must also patch the Default object
# stored as the default parameter value in APIRoute.__init__'s signature.
import fastapi.utils as _fastapi_utils
import fastapi.routing as _fastapi_routing
import inspect as _inspect
import re as _re


def _deterministic_generate_unique_id(route):
    operation_id = f"{route.name}{route.path_format}"
    operation_id = _re.sub(r"\W", "_", operation_id)
    assert route.methods
    operation_id = f"{operation_id}_{sorted(route.methods)[0].lower()}"
    return operation_id


# Patch module-level names
_fastapi_utils.generate_unique_id = _deterministic_generate_unique_id
_fastapi_routing.generate_unique_id = _deterministic_generate_unique_id

# Patch the DefaultPlaceholder stored as the default argument in
# APIRoute.__init__ so new routes pick up our function.
_sig = _inspect.signature(_fastapi_routing.APIRoute.__init__)
_default_placeholder = _sig.parameters["generate_unique_id_function"].default
_default_placeholder.value = _deterministic_generate_unique_id
# --- end operationId determinism patch ------------------------------------
# --- end determinism patch ------------------------------------------------

from app.main import app
from app.api.v1.registry import register_all_routers

# Ensure all routers are registered (they are normally registered lazily on startup)
register_all_routers(app)


# Endpoints that should have seeded test data
SEEDED_ENDPOINTS = {
    "/api/v1/catalog": {
        "get": "List seeded catalog items",
        "min_items": 20,
    },
    "/api/v1/events": {
        "get": "List seeded events",
        "min_items": 5,
    },
    "/api/v1/reading-programs": {
        "get": "List seeded reading programs",
        "min_items": 3,
    },
    "/api/v1/rooms": {
        "get": "List seeded study rooms",
        "min_items": 4,
    },
    "/api/v1/staff": {
        "get": "List seeded staff members",
        "min_items": 1,
    },
    "/api/v1/databases": {
        "get": "List seeded database subscriptions",
        "min_items": 5,
    },
    "/api/v1/collections": {
        "get": "List seeded collections",
        "min_items": 3,
    },
    "/api/v1/announcements": {
        "get": "List seeded announcements",
        "min_items": 1,
    },
    "/api/v1/board": {
        "get": "List seeded board members",
        "min_items": 3,
    },
}


def generate_openapi_spec(output_path: Path = None):
    """Generate OpenAPI specification from FastAPI app."""
    if output_path is None:
        output_path = backend_path / "openapi.json"

    # Get OpenAPI schema from FastAPI
    openapi_schema = app.openapi()

    # Add custom x-seeded-data extension to relevant endpoints
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            if path in SEEDED_ENDPOINTS:
                for method, method_config in SEEDED_ENDPOINTS[path].items():
                    if method in path_item:
                        # Add extension to document seeded data requirements
                        if "x-seeded-data" not in path_item[method]:
                            path_item[method]["x-seeded-data"] = {
                                "description": method_config,
                                "min_items": SEEDED_ENDPOINTS[path].get("min_items", 0),
                            }

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        # sort_keys=True is part of the determinism contract — see module docstring.
        json.dump(openapi_schema, f, indent=2, sort_keys=True)

    print(f"✅ OpenAPI spec generated: {output_path}")
    print(f"   Total endpoints: {len(openapi_schema.get('paths', {}))}")
    print(f"   Seeded endpoints: {len(SEEDED_ENDPOINTS)}")

    return output_path


def generate_markdown_docs(output_path: Path = None):
    """Generate markdown API documentation."""
    if output_path is None:
        output_path = backend_path / "docs" / "API.md"

    openapi_schema = app.openapi()

    docs = ["# API Documentation\n"]
    docs.append(f"Generated from OpenAPI {openapi_schema.get('openapi', 'unknown')}\n")
    docs.append(f"Title: {openapi_schema.get('info', {}).get('title')}\n")
    docs.append(f"Version: {openapi_schema.get('info', {}).get('version')}\n\n")

    # Categorize endpoints by tag
    endpoints_by_tag = {}

    if "paths" in openapi_schema:
        for path, path_item in sorted(openapi_schema["paths"].items()):
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    tags = operation.get("tags", ["Uncategorized"])
                    tag = tags[0] if tags else "Uncategorized"

                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []

                    endpoint_info = {
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "has_seeded_data": path in SEEDED_ENDPOINTS,
                    }

                    if path in SEEDED_ENDPOINTS:
                        endpoint_info["min_items"] = SEEDED_ENDPOINTS[path].get("min_items")

                    endpoints_by_tag[tag].append(endpoint_info)

    # Write documentation
    for tag, endpoints in sorted(endpoints_by_tag.items()):
        docs.append(f"## {tag}\n")

        for ep in sorted(endpoints, key=lambda x: (x["path"], x["method"])):
            method_badge = f"`{ep['method']}`"
            seeded_badge = " 🌱 _Has seeded data_" if ep["has_seeded_data"] else ""

            docs.append(f"### {method_badge} {ep['path']}{seeded_badge}\n")

            if ep["summary"]:
                docs.append(f"{ep['summary']}\n")

            if ep.get("min_items"):
                docs.append(f"> Seeded with minimum {ep['min_items']} items\n")

            docs.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("\n".join(docs))

    print(f"✅ API markdown docs generated: {output_path}")


def main():
    """Generate OpenAPI documentation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate OpenAPI documentation")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path for OpenAPI JSON",
        default=backend_path / "openapi.json"
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        help="Output file path for markdown docs",
        default=backend_path / "docs" / "API.md"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format"
    )

    args = parser.parse_args()

    if args.format in ["json", "both"]:
        generate_openapi_spec(args.output)

    if args.format in ["markdown", "both"]:
        generate_markdown_docs(args.markdown)

    print("\n✅ Documentation generation complete!")


if __name__ == "__main__":
    main()
