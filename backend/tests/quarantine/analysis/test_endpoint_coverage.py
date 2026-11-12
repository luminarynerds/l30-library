# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
import json
from pathlib import Path

@pytest.mark.analysis
def test_audit_report_exists():
    """Verify audit report was generated."""
    audit_file = Path("/opt/l30/PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json")
    assert audit_file.exists(), "Audit report not found"

@pytest.mark.analysis
def test_endpoint_coverage_metrics():
    """Verify endpoint coverage metrics are correct."""
    audit_file = Path("/opt/l30/PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json")
    with open(audit_file) as f:
        data = json.load(f)

    # Verify structure
    assert "total_endpoints" in data
    assert "used_endpoints" in data
    assert "orphaned_endpoints" in data
    assert "coverage_percentage" in data
    assert "categorized" in data

    # Verify math
    assert (data["used_endpoints"] + data["orphaned_endpoints"] ==
            data["total_endpoints"]), "Numbers don't add up"

    # Verify coverage percentage
    expected_coverage = round(
        (data["used_endpoints"] / data["total_endpoints"] * 100), 1
    )
    assert data["coverage_percentage"] == expected_coverage

    # Verify we have significant orphaned endpoints (sanity check)
    assert data["orphaned_endpoints"] > 100, "Should have many orphaned endpoints"

@pytest.mark.analysis
def test_orphaned_endpoints_categorized():
    """Verify all orphaned endpoints are categorized."""
    audit_file = Path("/opt/l30/PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json")
    with open(audit_file) as f:
        data = json.load(f)

    # Count endpoints across categories
    total_categorized = sum(
        cat["count"] for cat in data["categorized"].values()
    )

    assert total_categorized == data["orphaned_endpoints"], \
        "All orphaned endpoints should be categorized"

@pytest.mark.analysis
def test_required_categories_exist():
    """Verify required categories are present."""
    audit_file = Path("/opt/l30/PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json")
    with open(audit_file) as f:
        data = json.load(f)

    required = ["unclear", "dead_code", "incomplete_feature"]
    for category in required:
        assert category in data["categorized"], \
            f"Missing required category: {category}"
