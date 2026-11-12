# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, List, Optional

logger = get_logger(__name__)


def safe_extract_title(data: Any, default: str = "Unknown Title") -> str:
    if isinstance(data, str):
        return data if data.strip() else default

    if data is None or (isinstance(data, (dict, list)) and not data):
        return default

    # Handle dictionary structures
    if isinstance(data, dict):
        # Try various title property names in order of preference
        title = (
            data.get("bf:title") or
            data.get("title") or
            data.get("mainTitle") or
            data.get("bf:mainTitle")
        )

        # Recursively handle nested structures
        if title:
            return safe_extract_title(title, default)

    # Handle array structures
    if isinstance(data, list) and data:
        # Process first element recursively
        return safe_extract_title(data[0], default)

    return default


def extract_title_variants(data: Any) -> List[str]:
    variants = []
    visited = set()  # Prevent duplicates

    def _extract_recursive(item: Any) -> None:
        if isinstance(item, str):
            if item.strip() and item not in visited:
                variants.append(item)
                visited.add(item)
            return

        if isinstance(item, dict):
            # Check all title-like keys
            for key in ["bf:title", "title", "mainTitle", "bf:mainTitle",
                       "subtitle", "bf:subtitle", "variantTitle", "bf:variantTitle"]:
                if key in item and item[key]:
                    _extract_recursive(item[key])

            # Also check title_variant (JSON field from database)
            if "title_variant" in item and item["title_variant"]:
                try:
                    import json
                    if isinstance(item["title_variant"], str):
                        variants_list = json.loads(item["title_variant"])
                        if isinstance(variants_list, list):
                            for v in variants_list:
                                _extract_recursive(v)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Failed to parse title_variant JSON: %s", e)

            return

        if isinstance(item, list):
            for element in item:
                _extract_recursive(element)
            return

    _extract_recursive(data)
    return variants


def extract_subtitle(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data if data.strip() else None

    if isinstance(data, dict):
        # Try various subtitle property names
        subtitle = (
            data.get("bf:subtitle") or
            data.get("subtitle")
        )

        # If subtitle is nested in title object, extract recursively
        if not subtitle and ("bf:title" in data or "title" in data):
            title_obj = data.get("bf:title") or data.get("title")
            if isinstance(title_obj, dict):
                subtitle = (
                    title_obj.get("bf:subtitle") or
                    title_obj.get("subtitle")
                )

        # Recursively handle if still a structure
        if subtitle and isinstance(subtitle, (dict, list)):
            return extract_subtitle(subtitle)

        return subtitle if subtitle else None

    if isinstance(data, list) and data:
        return extract_subtitle(data[0])

    return None


def normalize_title_for_sorting(title: str) -> str:
    title_lower = title.lower().strip()

    # Articles in multiple languages
    articles = [
        "the ", "a ", "an ",  # English
        "le ", "la ", "les ",  # French
        "el ", "los ", "las ",  # Spanish
        "der ", "die ", "das ",  # German
    ]

    for article in articles:
        if title_lower.startswith(article):
            return title[len(article):]

    return title
