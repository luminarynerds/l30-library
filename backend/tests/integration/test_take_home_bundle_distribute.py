# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contract coverage for take-home reading bundle distribution.

Distribute previously required a `user_id` query param and the model stored no
student identity, so the staff form (free-text student name + class) 422'd every
time and the distributions table always rendered blank. These tests pin the new
contract: a JSON body with student_name/class_name, user_id optional.
"""

import pytest
from sqlalchemy import select

from app.models.outreach import OutreachPartner
from app.models.reading import TakeHomeReadingBundle, BundleDistribution

BASE = "/api/v1/school-partnerships/take-home-bundles"


async def _seed_bundle(test_db, partner_name, bundle_name, copies_available=5):
    partner = OutreachPartner(name=partner_name)
    test_db.add(partner)
    await test_db.flush()
    bundle = TakeHomeReadingBundle(
        partner_id=partner.id,
        name=bundle_name,
        copies_available=copies_available,
        copies_distributed=0,
    )
    test_db.add(bundle)
    await test_db.commit()
    return partner, bundle


@pytest.mark.asyncio
async def test_distribute_stores_student_name_and_class(staff_client, test_db):
    partner, bundle = await _seed_bundle(test_db, "Maple Elementary", "Bedtime Stories")

    resp = await staff_client.post(
        f"{BASE}/{bundle.id}/distribute",
        json={"student_name": "Jimmy R.", "class_name": "3rd Grade - A"},
    )
    assert resp.status_code == 201, resp.text
    dist_id = resp.json()["distribution_id"]

    row = (
        await test_db.execute(select(BundleDistribution).where(BundleDistribution.id == dist_id))
    ).scalar_one()
    assert row.student_name == "Jimmy R."
    assert row.class_name == "3rd Grade - A"
    assert row.user_id is None

    list_resp = await staff_client.get(f"{BASE}/{partner.id}/distributions")
    assert list_resp.status_code == 200, list_resp.text
    dists = list_resp.json()["distributions"]
    assert any(
        d["studentName"] == "Jimmy R." and d["className"] == "3rd Grade - A" for d in dists
    ), dists


@pytest.mark.asyncio
async def test_distribute_requires_student_name(staff_client, test_db):
    _, bundle = await _seed_bundle(test_db, "Oak Elementary", "Adventure Tales")

    resp = await staff_client.post(
        f"{BASE}/{bundle.id}/distribute",
        json={"class_name": "4th Grade"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_distribute_blocks_when_no_copies(staff_client, test_db):
    _, bundle = await _seed_bundle(
        test_db, "Birch Elementary", "Sold Out Bundle", copies_available=0
    )

    resp = await staff_client.post(
        f"{BASE}/{bundle.id}/distribute",
        json={"student_name": "Ana P.", "class_name": "2nd Grade"},
    )
    assert resp.status_code == 400, resp.text
