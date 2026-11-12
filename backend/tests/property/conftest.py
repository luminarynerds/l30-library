# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hypothesis setup shared by the property suite.

Everything in tests/property/ exercises pure functions: no database, no
fixtures, no event loop beyond asyncio.run on async-but-pure functions.

The first SQLAlchemy model instantiation triggers configure_mappers() over
the full registry (~5s); warm it up here so Hypothesis doesn't flag the
first generated example as a flaky slow test. Deadlines are disabled for
the same reason: wall-clock noise is meaningless for pure functions.
"""
import app.models  # noqa: F401  -- register all mappers before configuring
from hypothesis import settings
from sqlalchemy.orm import configure_mappers

configure_mappers()

settings.register_profile("l30_property", deadline=None)
settings.load_profile("l30_property")
