# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serve the four CSV import templates so a library admin can download them.

The templates live on disk at
``backend/app/templates/import_templates/*.csv`` and are operator-set, not
user-uploaded. This endpoint exposes them so a librarian doing the
new-library cutover (see docs/runbooks/new-library-go-live.md) can grab
them directly from the deployed instance instead of needing filesystem
access.
"""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.v1.dependencies import require_staff

router = APIRouter(prefix="/import-templates", tags=["import"])

_TEMPLATE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "templates"
    / "import_templates"
)

_TEMPLATE_MAP: dict[str, str] = {
    "patron": "patron_import_template.csv",
    "catalog": "catalog_import_template.csv",
    "holdings": "holdings_import_template.csv",
    "circulation": "circulation_history_template.csv",
}


@router.get("/{template_type}")
async def get_import_template(
    template_type: Literal["patron", "catalog", "holdings", "circulation"],
    _: object = Depends(require_staff),
) -> Response:
    """Return one of the four CSV templates as a downloadable file."""
    filename = _TEMPLATE_MAP.get(template_type)
    if filename is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown template type: {template_type}"
        )

    path = _TEMPLATE_DIR / filename
    if not path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Template file missing on server: {filename}",
        )

    return Response(
        content=path.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
