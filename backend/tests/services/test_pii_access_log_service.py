# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the granular pii_access_log_service.log_access."""

import uuid

import pytest
from sqlalchemy import select

from app.core.pii_audit import PIIAccessLog
from app.models.user import User, UserRole
from app.services import pii_access_log_service


async def _make_user(db, *, role: UserRole, suffix: str) -> User:
    user = User(
        email=f"pii-svc-{suffix}-{uuid.uuid4().hex[:6]}@test.local",
        password_hash="x",
        first_name="Svc",
        last_name=suffix.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_log_access_persists_row_with_granular_fields(db_session):
    staff = await _make_user(db_session, role=UserRole.STAFF, suffix="staff")
    patron = await _make_user(db_session, role=UserRole.PATRON, suffix="patron")

    record = await pii_access_log_service.log_access(
        db_session,
        user_id=staff.id,
        patron_id=patron.id,
        subject_type="patron_profile",
        subject_id=patron.id,
        action="read",
        reason="reviewing application",
        user_role=staff.role,
        ip_address="10.0.0.1",
    )
    await db_session.commit()

    assert record.id is not None
    fetched = (
        await db_session.execute(select(PIIAccessLog).where(PIIAccessLog.id == record.id))
    ).scalar_one()

    assert fetched.user_id == staff.id
    assert fetched.patron_id == patron.id
    assert fetched.subject_type == "patron_profile"
    assert fetched.subject_id == patron.id
    assert fetched.action == "read"
    assert fetched.reason == "reviewing application"
    assert fetched.user_role == "staff"
    assert fetched.ip_address == "10.0.0.1"
    # The granular write also leaves the legacy patron_ids_accessed populated
    # so the existing viewer's patron filter keeps returning these rows.
    assert fetched.patron_ids_accessed == [patron.id]
    # Endpoint is a stable marker, not a URL.
    assert fetched.endpoint == "granular:pii_access_log"


@pytest.mark.asyncio
async def test_log_access_double_write_creates_two_rows(db_session):
    """Idempotency is NOT required; two identical calls produce two rows."""
    staff = await _make_user(db_session, role=UserRole.STAFF, suffix="dup-staff")
    patron = await _make_user(db_session, role=UserRole.PATRON, suffix="dup-patron")

    for _ in range(2):
        await pii_access_log_service.log_access(
            db_session,
            user_id=staff.id,
            patron_id=patron.id,
            subject_type="home_address",
            action="reveal",
            user_role=staff.role,
        )
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(PIIAccessLog).where(
                PIIAccessLog.user_id == staff.id,
                PIIAccessLog.patron_id == patron.id,
                PIIAccessLog.action == "reveal",
            )
        )
    ).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_log_access_rejects_unknown_action(db_session):
    staff = await _make_user(db_session, role=UserRole.STAFF, suffix="bad-action")
    patron = await _make_user(db_session, role=UserRole.PATRON, suffix="bad-action-patron")

    with pytest.raises(ValueError):
        await pii_access_log_service.log_access(
            db_session,
            user_id=staff.id,
            patron_id=patron.id,
            subject_type="patron_profile",
            action="delete",  # not in ALLOWED_ACTIONS
            user_role=staff.role,
        )


@pytest.mark.asyncio
async def test_log_access_role_coercion(db_session):
    """UserRole enum, str, and None all become a stored string."""
    staff = await _make_user(db_session, role=UserRole.STAFF, suffix="coerce")
    patron = await _make_user(db_session, role=UserRole.PATRON, suffix="coerce-patron")

    # UserRole enum
    r1 = await pii_access_log_service.log_access(
        db_session,
        user_id=staff.id,
        patron_id=patron.id,
        subject_type="patron_profile",
        action="read",
        user_role=UserRole.ADMIN,
    )
    # bare str
    r2 = await pii_access_log_service.log_access(
        db_session,
        user_id=staff.id,
        patron_id=patron.id,
        subject_type="patron_profile",
        action="read",
        user_role="director",
    )
    # None
    r3 = await pii_access_log_service.log_access(
        db_session,
        user_id=staff.id,
        patron_id=patron.id,
        subject_type="patron_profile",
        action="read",
        user_role=None,
    )
    await db_session.commit()

    assert r1.user_role == "admin"
    assert r2.user_role == "director"
    assert r3.user_role == "unknown"


@pytest.mark.asyncio
async def test_log_access_minimal_required_fields(db_session):
    """subject_id and reason are optional."""
    staff = await _make_user(db_session, role=UserRole.STAFF, suffix="minimal")
    patron = await _make_user(db_session, role=UserRole.PATRON, suffix="minimal-patron")

    record = await pii_access_log_service.log_access(
        db_session,
        user_id=staff.id,
        patron_id=patron.id,
        subject_type="minor_data",
        action="export",
        user_role=staff.role,
    )
    await db_session.commit()

    assert record.subject_id is None
    assert record.reason is None
    assert record.subject_type == "minor_data"
    assert record.action == "export"
