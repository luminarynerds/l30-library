# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff-only trigger for the Phase 1 indie OPDS import.

POST /api/v1/admin/indie/import walks MetisLib's `/opds/indie` feed and upserts
owned `indie_ebooks` rows + local EPUB files. Returns the importer stats.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...models.user import User
from ...services.metislib_opds_import_service import MetisLibOpdsImporter
from .dependencies import require_staff

router = APIRouter(prefix="/admin/indie", tags=["admin", "indie"])


@router.post("/import")
async def trigger_indie_import(
    db: AsyncSession = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> dict:
    if not get_settings().indie_opds_import_enabled:
        return {
            "status": "frozen",
            "detail": (
                "Indie OPDS import is frozen to keep MetisLib demo/seed titles "
                "out of the owned catalog. Set INDIE_OPDS_IMPORT_ENABLED=true to run."
            ),
            "created": 0,
            "updated": 0,
            "files": 0,
            "errors": 0,
        }
    return await MetisLibOpdsImporter(db).import_all()
