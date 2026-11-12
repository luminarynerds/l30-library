# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest


@pytest.mark.asyncio
async def test_import_endpoint_requires_staff(client):
    resp = await client.post("/api/v1/admin/indie/import")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_import_endpoint_runs_importer(staff_client, monkeypatch):
    from app.core.config import get_settings

    async def fake_import_all(self):
        return {"created": 83, "updated": 0, "files": 83, "errors": 0}

    monkeypatch.setattr(
        "app.services.metislib_opds_import_service.MetisLibOpdsImporter.import_all",
        fake_import_all,
    )
    # Import is frozen by default (INDIE_OPDS_IMPORT_ENABLED=false) so MetisLib
    # demo/seed titles can't accidentally flow into the owned catalog; enable
    # it for this test to exercise the real importer path.
    monkeypatch.setattr(get_settings(), "indie_opds_import_enabled", True)
    resp = await staff_client.post("/api/v1/admin/indie/import")
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 83
    assert body["files"] == 83
