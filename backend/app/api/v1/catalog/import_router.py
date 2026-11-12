# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ..dependencies import require_staff
from .import_schemas import (
    CsvHeadersResponse,
    ImportPreviewResponse,
    ImportRequest,
    ImportResult,
)
from ....services.catalog_import import (
    detect_format,
    parse_csv_preview,
    parse_marc21_preview,
    parse_marcxml_preview,
    run_import,
    save_upload,
    _find_upload_file,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/catalog/import", tags=["catalog-import"])

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

CSV_TEMPLATE_ROWS = [
    "title,author,isbn,item_type,year,publisher,description,subjects",
    "The Great Gatsby,F. Scott Fitzgerald,9780743273565,book,1925,Scribner,A novel of the Jazz Age,Fiction",
    "Planet Earth,David Attenborough,,dvd,2006,BBC,,Nature documentaries",
]


@router.post("/upload", response_model=ImportPreviewResponse)
async def upload_catalog_file(
    file: UploadFile = File(...),
    current_user=Depends(require_staff),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="This file is too large (max 500 MB). Try a smaller file or split it into parts.",
        )

    filename = file.filename or "upload.mrc"
    try:
        fmt = detect_format(filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        if fmt == "marc21":
            total, preview = parse_marc21_preview(content)
        elif fmt == "marcxml":
            total, preview = parse_marcxml_preview(content)
        else:
            total, preview, _headers = parse_csv_preview(content)
    except Exception as exc:
        logger.exception("Failed to parse upload %s", filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {exc}",
        ) from exc

    upload_id = save_upload(content, filename)

    return ImportPreviewResponse(
        upload_id=upload_id,
        total_records=total,
        preview=preview,
        format=fmt,
    )


@router.get("/headers/{upload_id}", response_model=CsvHeadersResponse)
async def get_csv_headers(
    upload_id: str,
    current_user=Depends(require_staff),
):
    import csv
    import io

    path = _find_upload_file(upload_id)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That upload couldn't be found. It may have expired -- please try uploading again.")

    if path.suffix.lower() != ".csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Column headers can only be viewed for CSV files.",
        )

    content = path.read_bytes()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])

    return CsvHeadersResponse(upload_id=upload_id, headers=headers)


@router.post("/run", response_model=ImportResult)
async def run_catalog_import(
    req: ImportRequest,
    current_user=Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    path = _find_upload_file(req.upload_id)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That upload couldn't be found. It may have expired -- please try uploading again.")

    try:
        fmt = detect_format(path.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        result = await run_import(
            upload_id=req.upload_id,
            fmt=fmt,
            field_mapping=req.field_mapping,
            skip_invalid=req.skip_invalid,
            db=db,
        )
    except Exception as exc:
        logger.exception("Import failed for upload %s", req.upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {exc}",
        ) from exc

    return result


@router.get("/template")
async def download_csv_template(
    current_user=Depends(require_staff),
):
    content = "\n".join(CSV_TEMPLATE_ROWS) + "\n"

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="catalog_import_template.csv"'},
    )
