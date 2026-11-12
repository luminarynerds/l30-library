# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test for the whole-DB export tenancy guard.

security-findings.md #5: the /admin/data-export/bundle pull is unscoped
(whole-DB), correct only on a single-system deployment. It must refuse rather
than hand one system's director every other system's patron PII.
"""

import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def test_export_bundle_guards_single_system():
    s = (BACKEND / "app/api/v1/admin_data_export.py").read_text()
    assert "Full-bundle export is only supported on single-system" in s
    assert "LibrarySystem.id).where(LibrarySystem.is_active" in s
    assert "HTTP_409_CONFLICT" in s
