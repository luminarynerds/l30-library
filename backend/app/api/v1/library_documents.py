# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Library Document Ingestion API

Endpoints for uploading newsletters, reports, and other library content
for semantic search indexing. Supports both PDF upload and direct text paste.

All endpoints require admin access.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.file_validation import validate_file_type, validate_file_size
from .dependencies import require_admin
from ...models.user import User
from ...services.document_processing_service import get_document_processing_service
from ...services.semantic_search_service import get_semantic_search_service

logger = get_logger(__name__)

router = APIRouter(prefix="/library-documents", tags=["library-documents"])


# ==================== Upload Endpoints ====================


@router.post("/upload/pdf")
async def upload_pdf_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("newsletter"),
    description: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    auto_embed: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Upload a PDF document for text extraction and semantic search indexing.

    The PDF text is extracted, chunked into ~500-word segments, and stored.
    If auto_embed is True, embedding generation starts automatically.

    **Supported document types:**
    newsletter, annual_report, board_report, flyer, program_guide,
    policy_document, press_release, other
    """
    # Validate file
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return {"error": "Only PDF files are supported for upload."}

    content = await file.read()

    # Validate magic bytes
    mime = validate_file_type(content[:16], file.filename)
    if mime != "application/pdf":
        return {"error": "File does not appear to be a valid PDF."}

    # Validate size (25MB document limit)
    if not validate_file_size(len(content), "document"):
        return {"error": "File exceeds the 25MB size limit."}

    # Parse publish date if provided
    parsed_date = None
    if publish_date:
        try:
            parsed_date = datetime.fromisoformat(publish_date).replace(tzinfo=timezone.utc)
        except ValueError:
            return {"error": "Invalid publish_date format. Use ISO 8601 (e.g., 2024-06-15)."}

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    service = get_document_processing_service(db)

    try:
        doc = await service.ingest_pdf(
            file_bytes=content,
            filename=file.filename,
            title=title,
            document_type=document_type,
            uploaded_by_id=current_user.id,
            description=description,
            publish_date=parsed_date,
            tags=tag_list,
        )
    except ImportError as e:
        return {"error": str(e)}
    except ValueError as e:
        return {"error": str(e)}

    result = doc.to_dict()

    # Auto-generate embeddings
    if auto_embed:
        semantic_service = get_semantic_search_service(db)
        background_tasks.add_task(
            semantic_service.generate_embeddings_batch,
            entity_type="library_document",
            batch_size=50,
            skip_existing=True,
        )
        result["embedding_status"] = "generation_started"

    return result


@router.post("/upload/text")
async def upload_text_document(
    title: str = Form(...),
    text_content: str = Form(...),
    document_type: str = Form("newsletter"),
    description: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    auto_embed: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Ingest text content directly (copy-paste from web newsletters, etc.).

    Text is chunked into ~500-word segments and stored for embedding.
    """
    parsed_date = None
    if publish_date:
        try:
            parsed_date = datetime.fromisoformat(publish_date).replace(tzinfo=timezone.utc)
        except ValueError:
            return {"error": "Invalid publish_date format. Use ISO 8601 (e.g., 2024-06-15)."}

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    service = get_document_processing_service(db)

    try:
        doc = await service.ingest_text(
            text=text_content,
            title=title,
            document_type=document_type,
            uploaded_by_id=current_user.id,
            description=description,
            publish_date=parsed_date,
            tags=tag_list,
        )
    except ValueError as e:
        return {"error": str(e)}

    result = doc.to_dict()

    if auto_embed:
        semantic_service = get_semantic_search_service(db)
        background_tasks.add_task(
            semantic_service.generate_embeddings_batch,
            entity_type="library_document",
            batch_size=50,
            skip_existing=True,
        )
        result["embedding_status"] = "generation_started"

    return result


# ==================== List / Get / Delete ====================


@router.get("")
async def list_documents(
    document_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all ingested library documents with pagination."""
    service = get_document_processing_service(db)
    return await service.list_documents(
        document_type=document_type, limit=limit, offset=offset
    )


@router.get("/stats")
async def document_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get statistics about ingested library documents."""
    service = get_document_processing_service(db)
    return await service.get_document_stats()


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get a single document with its chunks."""
    service = get_document_processing_service(db)
    doc = await service.get_document(document_id)
    if not doc:
        return {"error": "Document not found."}

    result = doc.to_dict()
    result["chunks"] = [c.to_dict() for c in doc.chunks]
    return result


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Delete a document, its chunks, and associated embeddings."""
    service = get_document_processing_service(db)
    deleted = await service.delete_document(document_id)
    if not deleted:
        return {"error": "Document not found."}
    return {"message": "Document and associated embeddings deleted.", "document_id": document_id}
