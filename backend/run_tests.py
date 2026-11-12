#!/usr/bin/env python
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simple test runner to verify fixes"""
import subprocess
import sys

# Run the tests
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/test_auth.py", "-v", "--tb=short"],
    cwd="/opt/l30/backend"
)

sys.exit(result.returncode)
