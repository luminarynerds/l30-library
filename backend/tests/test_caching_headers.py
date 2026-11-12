# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Catalog endpoints must not be served `immutable` (inventory changes must
surface promptly). Reference/health endpoints stay immutable."""
from app.middleware.caching_headers import _get_cache_header


def test_catalog_browse_is_short_revalidatable_not_immutable():
    assert _get_cache_header("/api/v1/catalog/items", "GET") == "public, max-age=60, must-revalidate"


def test_catalog_search_is_short_revalidatable_not_immutable():
    assert _get_cache_header("/api/v1/catalog/search", "GET") == "public, max-age=60, must-revalidate"


def test_catalog_item_detail_not_immutable():
    assert "immutable" not in _get_cache_header("/api/v1/catalog/123", "GET")


def test_catalog_special_still_dynamic_300():
    assert _get_cache_header("/api/v1/catalog/special/new-arrivals", "GET") == "private, max-age=300"


def test_health_still_immutable():
    assert _get_cache_header("/api/v1/health", "GET") == "public, max-age=86400, immutable"
