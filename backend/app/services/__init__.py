# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Services module."""

from importlib import import_module

__all__ = ["legal_service"]


def __getattr__(name: str):
    if name == "legal_service":
        return import_module("app.services.legal")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
