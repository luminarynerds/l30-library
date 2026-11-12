# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for the three new ProfessionalDevelopmentPage endpoints under
school-partnerships/training-modules.

These call the route handlers directly with mocked SQLAlchemy sessions, which
matches the test_agent_interaction_capture.py pattern in this directory and
avoids the heavy `client` fixture (which the L30 test DB infrastructure cannot
build in this container -- duplicate index name across models breaks Base.metadata.create_all).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request


def _make_request():
    """Build a minimal real starlette Request to satisfy slowapi's decorator check."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 0),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "raw_path": b"/",
        "app": MagicMock(state=MagicMock(limiter=MagicMock(enabled=False))),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def _make_user(user_id=42):
    user = MagicMock()
    user.id = user_id
    return user


def _exec_returning_scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _exec_returning_scalars(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _make_module(module_id=1, partner_id=10, title="Phonics 101"):
    m = MagicMock()
    m.id = module_id
    m.partner_id = partner_id
    m.title = title
    return m


def _make_completion(module_id=1, user_id=42, status="in_progress", module=None):
    c = MagicMock()
    c.id = 100
    c.module_id = module_id
    c.user_id = user_id
    c.status = status
    c.started_at = datetime.now(timezone.utc)
    c.completed_at = None
    c.quiz_score = None
    c.passed_assessment = False
    c.module = module
    return c


def _make_cert(user_id=42, partner_id=10):
    cert = MagicMock()
    cert.id = 7
    cert.user_id = user_id
    cert.partner_id = partner_id
    cert.certification_name = "Reading Champion"
    cert.certification_level = "bronze"
    cert.certification_number = "CERT-001"
    cert.certified_at = datetime.now(timezone.utc)
    cert.expires_at = None
    return cert


@pytest.mark.asyncio
async def test_list_training_completions_returns_user_completions_for_school():
    from app.api.v1.school_reading.family_engagement import list_training_completions

    user = _make_user()
    module = _make_module(module_id=1, partner_id=10, title="Module A")
    completion = _make_completion(module_id=1, user_id=user.id, module=module)

    db = AsyncMock()
    db.execute.return_value = _exec_returning_scalars([completion])

    body = await list_training_completions(
        request=_make_request(), school_id=10, current_user=user, db=db
    )

    assert "completions" in body
    assert len(body["completions"]) == 1
    row = body["completions"][0]
    assert row["module_id"] == 1
    assert row["module_title"] == "Module A"
    assert row["status"] == "in_progress"
    assert row["passed_assessment"] is False
    assert row["quiz_score"] is None


@pytest.mark.asyncio
async def test_list_training_certificates_returns_user_certs_for_school():
    from app.api.v1.school_reading.family_engagement import list_training_certificates

    user = _make_user()
    cert = _make_cert(user_id=user.id, partner_id=10)

    db = AsyncMock()
    db.execute.return_value = _exec_returning_scalars([cert])

    body = await list_training_certificates(
        request=_make_request(), school_id=10, current_user=user, db=db
    )

    assert "certificates" in body
    assert len(body["certificates"]) == 1
    item = body["certificates"][0]
    assert item["id"] == 7
    assert item["certification_name"] == "Reading Champion"
    assert item["certification_level"] == "bronze"
    assert item["certification_number"] == "CERT-001"
    assert item["issued_at"] is not None


@pytest.mark.asyncio
async def test_complete_training_module_marks_completed_and_records_score():
    from app.api.v1.school_reading.family_engagement import (
        complete_training_module,
        CompleteTrainingModuleRequest,
    )

    user = _make_user()
    module = _make_module(module_id=1, partner_id=10)
    completion = _make_completion(module_id=1, user_id=user.id, status="in_progress")

    db = AsyncMock()
    db.execute.side_effect = [
        _exec_returning_scalar(module),       # module lookup
        _exec_returning_scalar(completion),   # completion lookup
    ]

    body = CompleteTrainingModuleRequest(partnerId=10, assessmentScore=85, answers=["A", "B"])

    result = await complete_training_module(
        request=_make_request(), module_id=1, body=body, current_user=user, db=db
    )

    assert result is completion
    assert completion.status == "completed"
    assert completion.quiz_score == 85
    assert completion.passed_assessment is True
    assert completion.completed_at is not None
    db.commit.assert_awaited()
    db.refresh.assert_awaited_with(completion)


@pytest.mark.asyncio
async def test_complete_training_module_404_when_module_missing():
    from fastapi import HTTPException
    from app.api.v1.school_reading.family_engagement import (
        complete_training_module,
        CompleteTrainingModuleRequest,
    )

    user = _make_user()
    db = AsyncMock()
    db.execute.return_value = _exec_returning_scalar(None)  # module missing

    body = CompleteTrainingModuleRequest(partnerId=10, assessmentScore=85)

    with pytest.raises(HTTPException) as exc:
        await complete_training_module(
            request=_make_request(), module_id=1, body=body, current_user=user, db=db
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_training_module_404_when_no_prior_start():
    from fastapi import HTTPException
    from app.api.v1.school_reading.family_engagement import (
        complete_training_module,
        CompleteTrainingModuleRequest,
    )

    user = _make_user()
    module = _make_module(module_id=1, partner_id=10)

    db = AsyncMock()
    db.execute.side_effect = [
        _exec_returning_scalar(module),  # module lookup succeeds
        _exec_returning_scalar(None),    # no completion record
    ]

    body = CompleteTrainingModuleRequest(partnerId=10, assessmentScore=85)

    with pytest.raises(HTTPException) as exc:
        await complete_training_module(
            request=_make_request(), module_id=1, body=body, current_user=user, db=db
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_training_module_records_failing_score():
    from app.api.v1.school_reading.family_engagement import (
        complete_training_module,
        CompleteTrainingModuleRequest,
    )

    user = _make_user()
    module = _make_module(module_id=1, partner_id=10)
    completion = _make_completion(module_id=1, user_id=user.id, status="in_progress")

    db = AsyncMock()
    db.execute.side_effect = [
        _exec_returning_scalar(module),
        _exec_returning_scalar(completion),
    ]

    body = CompleteTrainingModuleRequest(partnerId=10, assessmentScore=50)

    await complete_training_module(
        request=_make_request(), module_id=1, body=body, current_user=user, db=db
    )

    assert completion.status == "completed"
    assert completion.quiz_score == 50
    assert completion.passed_assessment is False
