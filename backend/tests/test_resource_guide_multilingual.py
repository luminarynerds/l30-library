# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backend tests for the parent-resource multilingual surface.

Covers:
  * ``GET /api/v1/parent-onboarding/resource-guide/sections?lang=es``
    substitutes title/description with the Spanish translation when
    present and falls back to the source field when absent.
  * ``GET`` without ``lang`` always returns source-language copy AND
    surfaces the full ``translations`` map so the staff edit UI can
    populate every language without a second fetch.
  * ``PATCH /resource-guide/items/{id}`` with
    ``{"translations": {"es": {...}}}`` merges into existing translations
    without wiping other languages already on the row.
  * ``PATCH`` with ``{"translations": {"es": null}}`` removes the
    Spanish entry only.
  * The ``languages`` ARRAY column is round-tripped through both
    create and update endpoints (latent bug-fix: surfacing the
    pre-existing column the FE never read).
"""
from __future__ import annotations

import pytest

from app.models.parent_onboarding import (
    ParentResourceGuideItem,
    ParentResourceGuideSection,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mk_section(test_db, *, title_key: str = "test_health") -> int:
    s = ParentResourceGuideSection(
        title_key=title_key,
        icon="health",
        display_order=0,
        is_active=True,
    )
    test_db.add(s)
    await test_db.commit()
    await test_db.refresh(s)
    return s.id


async def _mk_item(
    test_db,
    *,
    section_id: int,
    title: str = "Community Clinic",
    description: str | None = "Walk-in family medicine",
    languages: list[str] | None = None,
    translations: dict | None = None,
) -> int:
    item = ParentResourceGuideItem(
        section_id=section_id,
        title=title,
        description=description,
        contact_info=None,
        url=None,
        languages=languages or [],
        translations=translations or {},
        display_order=0,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item.id


# ---------------------------------------------------------------------------
# GET with lang substitution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sections_substitutes_translation_when_lang_matches(
    staff_client, test_db
):
    """``?lang=es`` swaps title/description for items with a Spanish entry."""
    section_id = await _mk_section(test_db, title_key="hl_translate")
    await _mk_item(
        test_db,
        section_id=section_id,
        title="Postpartum support line",
        description="Trained peers, 8am-8pm",
        languages=["en", "es"],
        translations={
            "es": {
                "title": "Línea de apoyo posparto",
                "description": "Pares capacitados, 8am-8pm",
            }
        },
    )

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections?lang=es"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    section = next(s for s in payload if s["title_key"] == "hl_translate")
    item = section["items"][0]
    assert item["title"] == "Línea de apoyo posparto"
    assert item["description"] == "Pares capacitados, 8am-8pm"
    # Languages array is surfaced (the latent bug-fix).
    assert item["languages"] == ["en", "es"]
    # Full translations map round-trips even when lang= is set, so the
    # staff edit UI doesn't need a second fetch.
    assert item["translations"]["es"]["title"] == "Línea de apoyo posparto"


@pytest.mark.asyncio
async def test_get_sections_falls_back_when_translation_missing(
    staff_client, test_db
):
    """Items lacking the requested language keep the English source copy."""
    section_id = await _mk_section(test_db, title_key="hl_fallback")
    await _mk_item(
        test_db,
        section_id=section_id,
        title="English-only Clinic",
        description="No Spanish copy yet",
        languages=["en"],
        translations={},
    )

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections?lang=es"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    section = next(s for s in payload if s["title_key"] == "hl_fallback")
    item = section["items"][0]
    assert item["title"] == "English-only Clinic"
    assert item["description"] == "No Spanish copy yet"
    # Empty translations map still surfaces (not omitted).
    assert item["translations"] == {}


@pytest.mark.asyncio
async def test_get_sections_partial_translation_falls_back_per_field(
    staff_client, test_db
):
    """Only fields the translator filled in get substituted; rest stay English."""
    section_id = await _mk_section(test_db, title_key="hl_partial")
    await _mk_item(
        test_db,
        section_id=section_id,
        title="Food Pantry",
        description="Free groceries, Tuesdays",
        languages=["en", "es"],
        translations={
            "es": {
                "title": "Despensa de alimentos",
                # description intentionally absent
            }
        },
    )

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections?lang=es"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    section = next(s for s in payload if s["title_key"] == "hl_partial")
    item = section["items"][0]
    assert item["title"] == "Despensa de alimentos"
    # description falls back to English
    assert item["description"] == "Free groceries, Tuesdays"


@pytest.mark.asyncio
async def test_get_sections_without_lang_returns_source_copy(staff_client, test_db):
    """No ``lang`` param means no substitution -- even if translations exist."""
    section_id = await _mk_section(test_db, title_key="hl_nolang")
    await _mk_item(
        test_db,
        section_id=section_id,
        title="WIC",
        description="Nutrition support",
        languages=["en", "es"],
        translations={"es": {"title": "WIC en español"}},
    )

    resp = await staff_client.get(
        "/api/v1/parent-onboarding/resource-guide/sections"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    section = next(s for s in payload if s["title_key"] == "hl_nolang")
    item = section["items"][0]
    assert item["title"] == "WIC"
    # Map still present for staff UI.
    assert item["translations"]["es"]["title"] == "WIC en español"


# ---------------------------------------------------------------------------
# PATCH translation merge semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_translations_merges_into_existing_languages(
    staff_client, test_db
):
    """Patching ``{"es": {...}}`` leaves a pre-existing ``so`` entry alone."""
    section_id = await _mk_section(test_db, title_key="hl_merge")
    item_id = await _mk_item(
        test_db,
        section_id=section_id,
        title="Postpartum line",
        translations={
            "so": {"title": "Khadka taageerada", "description": "8am-8pm"},
        },
    )

    resp = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/items/{item_id}",
        json={
            "translations": {
                "es": {
                    "title": "Línea de apoyo posparto",
                    "description": "Pares capacitados, 8am-8pm",
                }
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["translations"]["so"]["title"] == "Khadka taageerada"
    assert body["translations"]["es"]["title"] == "Línea de apoyo posparto"


@pytest.mark.asyncio
async def test_patch_translations_null_value_removes_language(
    staff_client, test_db
):
    """``{"es": null}`` deletes the Spanish entry and leaves others alone."""
    section_id = await _mk_section(test_db, title_key="hl_delete")
    item_id = await _mk_item(
        test_db,
        section_id=section_id,
        title="Pediatric clinic",
        translations={
            "es": {"title": "Clínica pediátrica"},
            "so": {"title": "Rugta cudurada carruurta"},
        },
    )

    resp = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/items/{item_id}",
        json={"translations": {"es": None}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "es" not in body["translations"]
    assert body["translations"]["so"]["title"] == "Rugta cudurada carruurta"


@pytest.mark.asyncio
async def test_patch_other_fields_leaves_translations_alone(staff_client, test_db):
    """Non-translation PATCH (e.g. languages update) leaves translations untouched."""
    section_id = await _mk_section(test_db, title_key="hl_noop")
    item_id = await _mk_item(
        test_db,
        section_id=section_id,
        title="Care line",
        languages=["en"],
        translations={"es": {"title": "Línea de cuidado"}},
    )

    resp = await staff_client.patch(
        f"/api/v1/parent-onboarding/resource-guide/items/{item_id}",
        json={"languages": ["en", "es", "so"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["languages"] == ["en", "es", "so"]
    assert body["translations"]["es"]["title"] == "Línea de cuidado"


# ---------------------------------------------------------------------------
# Latent bug-fix: ``languages`` round-trips through create + update.
# Prior to this PR the field existed in the DB column + backend Response
# schema but the FE TS type ignored it, so neither side ever exercised
# the round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_item_round_trips_languages_array(staff_client, test_db):
    section_id = await _mk_section(test_db, title_key="hl_create_langs")

    resp = await staff_client.post(
        f"/api/v1/parent-onboarding/resource-guide/sections/{section_id}/items",
        json={
            "title": "Bilingual hotline",
            "description": "EN/ES",
            "languages": ["en", "es"],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["languages"] == ["en", "es"]
    # Default empty translations map is present on create.
    assert body["translations"] == {}
