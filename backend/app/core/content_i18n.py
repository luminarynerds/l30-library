# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared resolver for per-record JSONB content translations.

Mirrors the substitution semantics in
app/api/v1/parent_onboarding/resource_guide.py: translations[lang][field]
wins when it's a non-empty string, else the record's own English column.
"""
from typing import Optional


def translated(record, field: str, lang: Optional[str]) -> Optional[str]:
    source = getattr(record, field)
    if not lang:
        return source
    entry = (record.translations or {}).get(lang) or {}
    if isinstance(entry, dict):
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return source
