# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conftest that ensures API routers are registered before endpoint tests."""

import logging

import pytest


@pytest.fixture(autouse=True)
def _ensure_routers_registered():
    """Ensure API routers are mounted before endpoint tests.

    Importing app.main triggers register_all_routers(app, ...) at module
    import time (see app/main.py), so this fixture just needs to perform
    the import once. The previous implementation referenced a
    nonexistent _routers_registered guard that broke fixture setup.
    """
    from app.main import app  # noqa: F401


@pytest.fixture(autouse=True)
def _restore_app_logger_propagation():
    """Re-enable propagation on the app logger during tests.

    app/core/logging.py sets propagate=False on the 'app' logger so that
    caplog cannot capture records in tests. This fixture temporarily
    restores propagation so caplog works correctly.
    """
    app_logger = logging.getLogger("app")
    original = app_logger.propagate
    app_logger.propagate = True
    yield
    app_logger.propagate = original
