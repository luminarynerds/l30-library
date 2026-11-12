# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guardrails for end-to-end coverage in high-value operational modules."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.analysis
def test_high_value_workflow_specs_exist():
    """Ensure critical operational modules keep dedicated integration workflow suites."""
    required_specs = {
        "makerspace": [
            REPO_ROOT / "backend/tests/integration/test_makerspace_endpoints.py",
            REPO_ROOT / "backend/tests/integration/test_makerspace_equipment_checkout.py",
        ],
        "fines_lost_damaged": [
            REPO_ROOT / "backend/tests/integration/test_all_fine_operations.py",
            REPO_ROOT / "backend/tests/integration/test_lost_damaged_workflow.py",
            REPO_ROOT / "backend/tests/integration/test_lost_damaged_workflows.py",
        ],
        # NOTE: dedicated streaming/digital-resources integration coverage
        # (test_digital_resources_comprehensive.py) was deleted in #1267
        # ("clean up pytest collection errors") without a replacement; the
        # app/api/v1/streaming.py route is still live but only indirectly
        # touched by tests/unit/test_rate_limit_config.py. Tracked as a
        # coverage gap in the 2026-07-08 re-baseline triage doc, not
        # recreated here (out of scope for a rot fix-or-quarantine pass).
        "linked_data_streaming": [
            REPO_ROOT / "backend/tests/integration/test_linked_data_endpoints.py",
        ],
    }

    for module_name, module_files in required_specs.items():
        missing = [str(path.relative_to(REPO_ROOT)) for path in module_files if not path.exists()]
        assert not missing, f"Missing workflow coverage files for {module_name}: {missing}"


@pytest.mark.analysis
@pytest.mark.parametrize(
    ("file_path", "required_tokens"),
    [
        (
            "backend/tests/integration/test_makerspace_endpoints.py",
            ["/api/v1/makerspace/resources", "test_list_resources"],
        ),
        (
            "backend/tests/integration/test_all_fine_operations.py",
            ["check_and_create_overdue_fine", "partial payment"],
        ),
        (
            "backend/tests/integration/test_lost_damaged_workflow.py",
            ["lost", "damaged"],
        ),
        (
            "backend/tests/integration/test_linked_data_endpoints.py",
            ["/api/v1/linked-data/works", "application/ld+json"],
        ),
    ],
)
def test_high_value_workflow_files_include_core_flow_tokens(file_path, required_tokens):
    """Verify each high-value suite still includes end-to-end workflow signals."""
    content = (REPO_ROOT / file_path).read_text(encoding="utf-8")

    for token in required_tokens:
        assert token in content, f"Expected token '{token}' not found in {file_path}"
