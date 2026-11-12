# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the parent resource guide verification trail.

Covers:
  - Verify endpoint sets last_verified_at + verified_by_id and is idempotent.
  - Verify auto-resolves all open flags on the item with verified_current.
  - Flag-create with valid reason_code returns 201; invalid reason returns 422.
  - Flag list returns oldest-first; status filter works.
  - Patch flag transitions status; double-resolve is idempotent.
  - last_verified_at < now() - STALE_AFTER_MONTHS computes stale=True.
  - Notification path: self-flag suppressed; no recipient when never verified.

Auth pattern: staff_client fixture overrides get_current_user with a
STAFF user. Real-login JWT path requires Redis for token revocation
(feedback_l30_test_auth_token_revocation) and is not exercised here.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.parent_onboarding import (
    ParentResourceGuideFlag,
    ParentResourceGuideItem,
    ParentResourceGuideSection,
    ResourceGuideFlagReason,
    ResourceGuideFlagStatus,
)

pytestmark = pytest.mark.asyncio


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


async def _seed_item(test_db, *, title: str = "WIC Office", last_verified_at=None, verified_by_id=None):
    section = ParentResourceGuideSection(
        title_key="health",
        icon="health",
        display_order=0,
        is_active=True,
    )
    test_db.add(section)
    await test_db.flush()
    item = ParentResourceGuideItem(
        section_id=section.id,
        title=title,
        description="Federal nutrition program",
        contact_info="(555) 555-5555",
        url="https://wic.example.gov",
        languages=["en", "es"],
        display_order=0,
        last_verified_at=last_verified_at,
        verified_by_id=verified_by_id,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return section, item


# ----------------------------------------------------------------------------
# Verify endpoint
# ----------------------------------------------------------------------------


async def test_verify_item_sets_last_verified_at_and_verifier(
    staff_client, test_db, test_staff
):
    _section, item = await _seed_item(test_db)
    assert item.last_verified_at is None

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/verify"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["last_verified_at"] is not None
    assert body["verified_by_id"] == test_staff.id
    # verified_by_name uses first+last when present
    expected_name = f"{test_staff.first_name} {test_staff.last_name}".strip()
    assert body["verified_by_name"] in (expected_name, test_staff.email.split("@")[0])
    assert body["stale"] is False
    assert body["open_flag_count"] == 0


async def test_verify_item_is_idempotent(staff_client, test_db, test_staff):
    _section, item = await _seed_item(test_db)

    first = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/verify"
    )
    second = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/verify"
    )
    assert first.status_code == 200
    assert second.status_code == 200
    # Both have a timestamp; second is >= first.
    assert second.json()["last_verified_at"] >= first.json()["last_verified_at"]


async def test_verify_item_auto_resolves_open_flags(
    staff_client, test_db, test_staff
):
    _section, item = await _seed_item(test_db)
    flag = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.disconnected_phone.value,
        comment="dead line",
        status=ResourceGuideFlagStatus.open.value,
    )
    test_db.add(flag)
    await test_db.commit()

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/verify"
    )
    assert resp.status_code == 200

    refreshed = (
        await test_db.execute(
            select(ParentResourceGuideFlag).where(
                ParentResourceGuideFlag.id == flag.id
            )
        )
    ).scalar_one()
    assert refreshed.status == ResourceGuideFlagStatus.resolved.value
    assert refreshed.resolution == "verified_current"
    assert refreshed.resolved_by_id == test_staff.id
    assert refreshed.resolved_at is not None


async def test_verify_404_for_missing_item(staff_client):
    resp = await staff_client.post(
        "/api/v1/parent-onboarding/resource-guide/items/9999999/verify"
    )
    assert resp.status_code == 404


# ----------------------------------------------------------------------------
# Flag endpoint
# ----------------------------------------------------------------------------


async def test_flag_creates_row_with_valid_reason(
    staff_client, test_db, test_staff
):
    _section, item = await _seed_item(test_db)

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/flags",
        json={
            "reason_code": "disconnected_phone",
            "comment": "Called three times, line is dead.",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["reason_code"] == "disconnected_phone"
    assert body["status"] == "open"
    assert body["item"]["id"] == item.id
    assert body["item"]["title"] == "WIC Office"


async def test_flag_invalid_reason_returns_422(staff_client, test_db):
    _section, item = await _seed_item(test_db)

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/flags",
        json={"reason_code": "made_up_reason"},
    )
    assert resp.status_code == 422


async def test_flag_404_for_missing_item(staff_client):
    resp = await staff_client.post(
        "/api/v1/parent-onboarding/resource-guide/items/9999999/flags",
        json={"reason_code": "wrong_address"},
    )
    assert resp.status_code == 404


# ----------------------------------------------------------------------------
# List flags
# ----------------------------------------------------------------------------


async def test_list_open_flags_oldest_first(staff_client, test_db, test_staff):
    _section, item = await _seed_item(test_db)

    # Create two flags with a measurable gap so order_by created_at ASC
    # is verifiable across both SQLite + PG without flake.
    flag_a = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.wrong_address.value,
        status=ResourceGuideFlagStatus.open.value,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    flag_b = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.eligibility_changed.value,
        status=ResourceGuideFlagStatus.open.value,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    test_db.add(flag_a)
    test_db.add(flag_b)
    await test_db.commit()

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/flags?status=open"
    )
    assert resp.status_code == 200
    body = resp.json()
    # Two flags, oldest first.
    assert [f["reason_code"] for f in body] == [
        ResourceGuideFlagReason.wrong_address.value,
        ResourceGuideFlagReason.eligibility_changed.value,
    ]


async def test_list_flags_filters_by_status(staff_client, test_db, test_staff):
    _section, item = await _seed_item(test_db)
    open_flag = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.other.value,
        status=ResourceGuideFlagStatus.open.value,
    )
    resolved_flag = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.other.value,
        status=ResourceGuideFlagStatus.resolved.value,
        resolution="verified_current",
        resolved_by_id=test_staff.id,
        resolved_at=datetime.now(timezone.utc),
    )
    test_db.add(open_flag)
    test_db.add(resolved_flag)
    await test_db.commit()

    resp_open = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/flags?status=open"
    )
    resp_resolved = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/flags?status=resolved"
    )
    assert resp_open.status_code == 200
    assert resp_resolved.status_code == 200
    assert len(resp_open.json()) == 1
    assert resp_open.json()[0]["status"] == "open"
    assert len(resp_resolved.json()) == 1
    assert resp_resolved.json()[0]["status"] == "resolved"


# ----------------------------------------------------------------------------
# Patch flag
# ----------------------------------------------------------------------------


async def test_patch_flag_transitions_status(staff_client, test_db, test_staff):
    _section, item = await _seed_item(test_db)
    flag = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.wrong_address.value,
        status=ResourceGuideFlagStatus.open.value,
    )
    test_db.add(flag)
    await test_db.commit()
    await test_db.refresh(flag)

    resp = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/flags/{flag.id}",
        json={"status": "dismissed", "resolution": "invalid",
              "resolution_notes": "dialed wrong area code"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "dismissed"
    assert body["resolution"] == "invalid"
    assert body["resolved_by_id"] == test_staff.id


async def test_patch_flag_double_resolve_is_idempotent(
    staff_client, test_db, test_staff
):
    _section, item = await _seed_item(test_db)
    flag = ParentResourceGuideFlag(
        item_id=item.id,
        flagged_by_id=test_staff.id,
        reason_code=ResourceGuideFlagReason.other.value,
        status=ResourceGuideFlagStatus.open.value,
    )
    test_db.add(flag)
    await test_db.commit()

    first = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/flags/{flag.id}",
        json={"status": "resolved", "resolution": "edited"},
    )
    second = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/flags/{flag.id}",
        json={"status": "resolved", "resolution": "edited"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    # Resolution stable across the no-op.
    assert second.json()["resolution"] == "edited"


# ----------------------------------------------------------------------------
# Stale computation
# ----------------------------------------------------------------------------


async def test_old_last_verified_marks_item_stale(staff_client, test_db, test_staff):
    # 9 months in the past, well past the 6-month default.
    nine_months_ago = datetime.now(timezone.utc) - timedelta(days=30 * 9)
    _section, item = await _seed_item(
        test_db, last_verified_at=nine_months_ago, verified_by_id=test_staff.id
    )

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections"
    )
    assert resp.status_code == 200
    sections = resp.json()
    assert sections, "expected at least one section"
    items = sections[0]["items"]
    assert items, "expected at least one item"
    assert items[0]["stale"] is True


async def test_never_verified_is_stale_by_default(staff_client, test_db):
    # last_verified_at NULL -> stale (the right starting condition per spec).
    _section, _item = await _seed_item(test_db, last_verified_at=None)

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections"
    )
    assert resp.status_code == 200
    items = resp.json()[0]["items"]
    assert items[0]["stale"] is True
    assert items[0]["verified_by_name"] is None


# ----------------------------------------------------------------------------
# Notification path
# ----------------------------------------------------------------------------


async def test_self_flag_skips_notification(
    monkeypatch, staff_client, test_db, test_staff
):
    """If the flagger is the same user as the last verifier, no email."""
    _section, item = await _seed_item(
        test_db,
        last_verified_at=datetime.now(timezone.utc),
        verified_by_id=test_staff.id,
    )

    calls: list[tuple] = []

    async def _fake_send(*args, **kwargs):  # noqa: ANN001
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(
        "app.services.parent_resource_flag_notify.send_email", _fake_send
    )

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/flags",
        json={"reason_code": "wrong_address"},
    )
    assert resp.status_code == 201
    assert calls == [], "expected self-flag to suppress email"


async def test_no_recipient_when_never_verified(
    monkeypatch, staff_client, test_db
):
    """v1: never-verified items have no notification recipient."""
    _section, item = await _seed_item(test_db, last_verified_at=None)

    calls: list[tuple] = []

    async def _fake_send(*args, **kwargs):  # noqa: ANN001
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(
        "app.services.parent_resource_flag_notify.send_email", _fake_send
    )

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/items/{item.id}/flags",
        json={"reason_code": "closed_permanently"},
    )
    assert resp.status_code == 201
    assert calls == [], "expected no email when item has never been verified"
