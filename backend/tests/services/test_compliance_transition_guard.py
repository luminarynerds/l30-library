# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests: compliance incident status transition guard (H3, sweep 2026-07-01).

update_incident_status must reject invalid transitions (e.g. reported ->
closed skipping all triage/investigation steps) and must acquire a row
lock before reading current status.

Previously: no transition validation; any status could be applied to any
incident regardless of current state.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.unified_compliance_audit import ComplianceIncident, IncidentStatus
from app.services.unified_compliance_service import UnifiedComplianceService


def _db_with_incident(incident):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = incident
    db.execute.return_value = mock_result
    return db


def _incident(status: IncidentStatus) -> MagicMock:
    inc = MagicMock(spec=ComplianceIncident)
    inc.id = 1
    inc.status = status
    inc.notes = None
    return inc


# ---------------------------------------------------------------------------
# Transition guard — invalid paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reported_cannot_jump_to_closed():
    """reported -> closed bypasses all mandatory investigation steps."""
    incident = _incident(IncidentStatus.reported)
    db = _db_with_incident(incident)

    with pytest.raises(ValueError, match="Invalid transition"):
        await UnifiedComplianceService.update_incident_status(
            db, incident_id=1,
            new_status=IncidentStatus.closed,
            updated_by_id=1,
        )


@pytest.mark.asyncio
async def test_resolved_cannot_go_back_to_investigating():
    """Status regression is forbidden."""
    incident = _incident(IncidentStatus.resolved)
    db = _db_with_incident(incident)

    with pytest.raises(ValueError, match="Invalid transition"):
        await UnifiedComplianceService.update_incident_status(
            db, incident_id=1,
            new_status=IncidentStatus.investigating,
            updated_by_id=1,
        )


@pytest.mark.asyncio
async def test_closed_is_terminal():
    """Once closed, no further transitions are allowed."""
    incident = _incident(IncidentStatus.closed)
    db = _db_with_incident(incident)

    with pytest.raises(ValueError, match="Invalid transition"):
        await UnifiedComplianceService.update_incident_status(
            db, incident_id=1,
            new_status=IncidentStatus.resolved,
            updated_by_id=1,
        )


# ---------------------------------------------------------------------------
# Transition guard — valid paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reported_to_triaging_is_valid():
    incident = _incident(IncidentStatus.reported)
    incident.triaged_at = None
    db = _db_with_incident(incident)

    result = await UnifiedComplianceService.update_incident_status(
        db, incident_id=1,
        new_status=IncidentStatus.triaging,
        updated_by_id=1,
    )

    assert result.status == IncidentStatus.triaging


@pytest.mark.asyncio
async def test_remediating_to_resolved_is_valid():
    incident = _incident(IncidentStatus.remediating)
    incident.resolved_at = None
    db = _db_with_incident(incident)

    result = await UnifiedComplianceService.update_incident_status(
        db, incident_id=1,
        new_status=IncidentStatus.resolved,
        updated_by_id=1,
    )

    assert result.status == IncidentStatus.resolved


@pytest.mark.asyncio
async def test_resolved_to_closed_is_valid():
    incident = _incident(IncidentStatus.resolved)
    incident.closed_at = None
    db = _db_with_incident(incident)

    result = await UnifiedComplianceService.update_incident_status(
        db, incident_id=1,
        new_status=IncidentStatus.closed,
        updated_by_id=1,
    )

    assert result.status == IncidentStatus.closed


# ---------------------------------------------------------------------------
# Row lock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_incident_status_uses_row_lock():
    """select must include .with_for_update() to prevent lost-update races."""
    incident = _incident(IncidentStatus.reported)
    incident.triaged_at = None
    db = _db_with_incident(incident)

    await UnifiedComplianceService.update_incident_status(
        db, incident_id=1,
        new_status=IncidentStatus.triaging,
        updated_by_id=1,
    )

    call_args = db.execute.call_args
    compiled = str(call_args[0][0].compile())
    assert "FOR UPDATE" in compiled.upper(), (
        "select must include FOR UPDATE to prevent lost-update races on concurrent status transitions"
    )
