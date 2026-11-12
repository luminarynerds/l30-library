# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backend tests for DB content translations.

Covers:
  * ``app.core.content_i18n.translated`` fallback semantics.
  * ``GET /api/v1/discover/shelves?lang=es`` substitutes title/description
    when a translation exists, and returns source copy without ``lang``.
  * Staff content-translations editor: GET listing across all content
    types, PUT merge, PUT empty-string/null delete, 404 unknown
    type/id, 422 unknown field.
"""
from __future__ import annotations

import pytest

from app.core.content_i18n import translated
from app.models.staff_shelves import StaffShelf


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Resolver unit tests
# ---------------------------------------------------------------------------


class _Fake:
    def __init__(self, name, translations):
        self.name = name
        self.translations = translations


def test_translated_returns_source_when_lang_omitted():
    record = _Fake("Community Room", {"es": {"name": "Sala comunitaria"}})
    assert translated(record, "name", None) == "Community Room"


def test_translated_returns_translation_when_present():
    record = _Fake("Community Room", {"es": {"name": "Sala comunitaria"}})
    assert translated(record, "name", "es") == "Sala comunitaria"


def test_translated_falls_back_when_language_missing():
    record = _Fake("Community Room", {"fr": {"name": "Salle communautaire"}})
    assert translated(record, "name", "es") == "Community Room"


def test_translated_falls_back_when_field_blank():
    record = _Fake("Community Room", {"es": {"name": "   "}})
    assert translated(record, "name", "es") == "Community Room"


def test_translated_falls_back_when_translations_none():
    record = _Fake("Community Room", None)
    assert translated(record, "name", "es") == "Community Room"


# ---------------------------------------------------------------------------
# Public endpoint substitution (discover shelves)
# ---------------------------------------------------------------------------


async def _mk_shelf(session, **kw):
    shelf = StaffShelf(
        slug=kw["slug"],
        title=kw["title"],
        description=kw.get("description"),
        item_ids=kw.get("item_ids", []),
        translations=kw.get("translations", {}),
    )
    session.add(shelf)
    await session.flush()
    return shelf


async def test_discover_shelves_substitutes_translation_with_lang(client, test_db):
    await _mk_shelf(
        test_db,
        slug="cozy-mysteries",
        title="Cozy mysteries",
        description="small-town sleuths",
        translations={
            "es": {"title": "Misterios acogedores", "description": "detectives de pueblo"}
        },
    )
    await test_db.commit()

    r = await client.get("/api/v1/discover/shelves?lang=es")
    assert r.status_code == 200, r.text
    shelf = next(s for s in r.json() if s["slug"] == "cozy-mysteries")
    assert shelf["title"] == "Misterios acogedores"
    assert shelf["description"] == "detectives de pueblo"


async def test_discover_shelves_source_copy_without_lang(client, test_db):
    await _mk_shelf(
        test_db,
        slug="cozy-mysteries-2",
        title="Cozy mysteries",
        description="small-town sleuths",
        translations={"es": {"title": "Misterios acogedores"}},
    )
    await test_db.commit()

    r = await client.get("/api/v1/discover/shelves")
    assert r.status_code == 200, r.text
    shelf = next(s for s in r.json() if s["slug"] == "cozy-mysteries-2")
    assert shelf["title"] == "Cozy mysteries"
    assert shelf["description"] == "small-town sleuths"


# ---------------------------------------------------------------------------
# Staff content-translations editor
# ---------------------------------------------------------------------------


async def test_get_content_translations_lists_all_types(staff_client, test_db):
    await _mk_shelf(test_db, slug="staff-shelf-a", title="Staff Picks", description="Curated")
    await test_db.commit()

    resp = await staff_client.get("/api/v1/staff/content-translations?lang=es")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] == "es"
    content_types = {g["content_type"] for g in body["groups"]}
    assert content_types == {"room", "tech_help_option", "legal_topic", "discover_shelf"}

    shelf_group = next(g for g in body["groups"] if g["content_type"] == "discover_shelf")
    record = next(r for r in shelf_group["records"] if r["display_name"] == "Staff Picks")
    field_map = {f["field"]: f for f in record["fields"]}
    assert field_map["title"]["source"] == "Staff Picks"
    assert field_map["title"]["value"] is None  # untranslated


async def test_put_content_translation_merges_and_returns_record(staff_client, test_db):
    shelf = await _mk_shelf(
        test_db,
        slug="staff-shelf-b",
        title="Staff Picks",
        description="Curated",
        translations={"fr": {"title": "Choix du personnel"}},
    )
    await test_db.commit()

    resp = await staff_client.put(
        f"/api/v1/staff/content-translations/discover_shelf/{shelf.id}",
        json={"language": "es", "values": {"title": "Selecciones del personal"}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    field_map = {f["field"]: f for f in body["fields"]}
    assert field_map["title"]["value"] == "Selecciones del personal"

    await test_db.refresh(shelf)
    assert shelf.translations["fr"]["title"] == "Choix du personnel"
    assert shelf.translations["es"]["title"] == "Selecciones del personal"


async def test_put_content_translation_empty_string_deletes_field(staff_client, test_db):
    shelf = await _mk_shelf(
        test_db,
        slug="staff-shelf-c",
        title="Staff Picks",
        description="Curated",
        translations={"es": {"title": "Selecciones", "description": "Colección curada"}},
    )
    await test_db.commit()

    resp = await staff_client.put(
        f"/api/v1/staff/content-translations/discover_shelf/{shelf.id}",
        json={"language": "es", "values": {"description": ""}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    field_map = {f["field"]: f for f in body["fields"]}
    assert field_map["description"]["value"] is None
    assert field_map["title"]["value"] == "Selecciones"

    await test_db.refresh(shelf)
    assert "description" not in shelf.translations["es"]
    assert shelf.translations["es"]["title"] == "Selecciones"


async def test_put_content_translation_unknown_type_404(staff_client, test_db):
    resp = await staff_client.put(
        "/api/v1/staff/content-translations/not_a_type/1",
        json={"language": "es", "values": {"title": "x"}},
    )
    assert resp.status_code == 404


async def test_put_content_translation_unknown_id_404(staff_client, test_db):
    resp = await staff_client.put(
        "/api/v1/staff/content-translations/discover_shelf/999999",
        json={"language": "es", "values": {"title": "x"}},
    )
    assert resp.status_code == 404


async def test_put_content_translation_unknown_field_422(staff_client, test_db):
    shelf = await _mk_shelf(test_db, slug="staff-shelf-d", title="Staff Picks")
    await test_db.commit()

    resp = await staff_client.put(
        f"/api/v1/staff/content-translations/discover_shelf/{shelf.id}",
        json={"language": "es", "values": {"not_a_field": "x"}},
    )
    assert resp.status_code == 422
