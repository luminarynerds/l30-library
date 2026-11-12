# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Knowledge Pipeline API - Admin/staff endpoints for the unified knowledge ingestion system.

Endpoints:
  POST /knowledge-pipeline/ingest/manual        - staff creates a knowledge entry manually
  POST /knowledge-pipeline/ingest/document      - staff triggers Q&A extraction from a document (background)
  POST /knowledge-pipeline/generate-synthetic   - admin triggers synthetic Q&A generation (background)
  GET  /knowledge-pipeline/conflicts            - staff scans for conflicting entries
  PUT  /knowledge-pipeline/entries/{entry_id}   - staff updates an entry with version tracking
  GET  /knowledge-pipeline/entries/{entry_id}/history - staff views version history
  GET  /knowledge-pipeline/stats                - staff views pipeline statistics
"""

from app.core.logging import get_logger
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.knowledge_base import KnowledgeEntry
from ...models.knowledge_version import KnowledgeVersion
from ...models.user import User
from ...services.conflict_detection_service import ConflictDetectionService
from ...services.knowledge_pipeline_service import KnowledgePipelineService
from ...services.synthetic_generation_service import SyntheticGenerationService
from ...services.knowledge_retention_service import KnowledgeRetentionService
from ...services.training_pipeline_service import TrainingPipelineService
from ...models.patron_training_opt_out import PatronTrainingOptOut
from ...models.training_example import TrainingExample
from .dependencies import require_admin, require_patron, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge-pipeline", tags=["knowledge-pipeline"])


# ============================================================================
# Request / Response Schemas
# ============================================================================


class ManualIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=50)
    tags: Optional[str] = Field(None, max_length=500)
    persona_domain: Optional[str] = Field(None, max_length=50)
    location_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    entry_metadata: Optional[dict[str, Any]] = None


class DocumentIngestRequest(BaseModel):
    document_id: int
    category: str = Field(default="faq", max_length=50)
    persona_domain: Optional[str] = Field(None, max_length=50)
    location_id: Optional[int] = None


class SyntheticGenerateRequest(BaseModel):
    persona_domain: Optional[str] = Field(None, max_length=50)
    limit: int = Field(default=50, ge=1, le=200)


class EntryUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    tags: Optional[str] = Field(None, max_length=500)
    review_status: Optional[str] = Field(None, pattern=r"^(pending|approved|rejected)$")
    persona_domain: Optional[str] = Field(None, max_length=50)
    change_reason: Optional[str] = Field(None, max_length=500)


class KnowledgeEntryResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    tags: Optional[str]
    persona_domain: Optional[str]
    location_id: Optional[int]
    source_type: Optional[str]
    review_status: str
    version: int
    added_by_id: Optional[int]
    added_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeVersionResponse(BaseModel):
    id: int
    knowledge_entry_id: int
    version_number: int
    title: str
    content: str
    category: Optional[str]
    persona_domain: Optional[str]
    changed_by_id: Optional[int]
    changed_by_name: Optional[str]
    change_reason: Optional[str]
    previous_content: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictPairResponse(BaseModel):
    entry_a_id: int
    entry_a_title: str
    entry_b_id: int
    entry_b_title: str
    similarity: float
    domain: Optional[str]


class PipelineStatsResponse(BaseModel):
    total_entries: int
    by_source: dict[str, int]
    by_status: dict[str, int]
    by_domain: dict[str, int]


# ============================================================================
# Background task helpers
# ============================================================================


async def _bg_ingest_document(document_id: int, category: str, persona_domain: Optional[str], location_id: Optional[int]) -> None:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    async with AsyncSessionLocal() as db:
        try:
            svc = KnowledgePipelineService()
            entries = await svc.ingest_document(
                db,
                document_id,
                category=category,
                persona_domain=persona_domain,
                location_id=location_id,
            )
            await db.commit()
            logger.info("Document %s ingested: %d entries created", document_id, len(entries))
        except Exception:
            await db.rollback()
            logger.exception("Background document ingestion failed for document %s", document_id)


async def _bg_generate_synthetic(persona_domain: Optional[str], limit: int) -> None:
    from app.core.database import AsyncSessionLocal  # noqa: PLC0415
    async with AsyncSessionLocal() as db:
        try:
            svc = SyntheticGenerationService()
            entries = await svc.generate_batch(db, persona_domain=persona_domain, limit=limit)
            logger.info("Synthetic generation complete: %d entries created", len(entries))
        except Exception:
            await db.rollback()
            logger.exception("Background synthetic generation failed")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/ingest/manual", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_manual(
    payload: ManualIngestRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntry:
    """Create a manually-authored knowledge entry (auto-approved with embedding)."""
    svc = KnowledgePipelineService()
    entry = await svc.ingest_manual(
        db,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        added_by_id=current_user.id,
        added_by_name=getattr(current_user, "full_name", None) or current_user.username,
        tags=payload.tags,
        persona_domain=payload.persona_domain,
        location_id=payload.location_id,
        expires_at=payload.expires_at,
        entry_metadata=payload.entry_metadata,
    )
    await db.commit()
    await db.refresh(entry)
    return entry


@router.post("/ingest/document", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document(
    payload: DocumentIngestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_staff),
) -> dict[str, Any]:
    """Trigger Q&A extraction from an uploaded document (runs in background)."""
    background_tasks.add_task(
        _bg_ingest_document,
        payload.document_id,
        payload.category,
        payload.persona_domain,
        payload.location_id,
    )
    return {"status": "accepted", "message": f"Document {payload.document_id} queued for ingestion"}


@router.post("/generate-synthetic", status_code=status.HTTP_202_ACCEPTED)
async def generate_synthetic(
    payload: SyntheticGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger synthetic Q&A generation from approved entries (admin only, runs in background)."""
    background_tasks.add_task(
        _bg_generate_synthetic,
        payload.persona_domain,
        payload.limit,
    )
    return {"status": "accepted", "message": "Synthetic generation queued"}


@router.get("/conflicts", response_model=list[ConflictPairResponse])
async def scan_conflicts(
    persona_domain: Optional[str] = Query(None, description="Filter by persona domain"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Scan approved entries for semantic conflicts (similarity >= 0.92)."""
    svc = ConflictDetectionService()
    conflicts = await svc.scan_all(db, persona_domain=persona_domain)
    return conflicts


@router.put("/entries/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_entry(
    entry_id: int,
    payload: EntryUpdateRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntry:
    """Update a knowledge entry with full version tracking and optional re-embedding."""
    svc = KnowledgePipelineService()
    entry = await svc.update_entry(
        db,
        entry_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        tags=payload.tags,
        review_status=payload.review_status,
        persona_domain=payload.persona_domain,
        changed_by_id=current_user.id,
        changed_by_name=getattr(current_user, "full_name", None) or current_user.username,
        change_reason=payload.change_reason,
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entry {entry_id} not found")
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/entries/{entry_id}/history", response_model=list[KnowledgeVersionResponse])
async def get_entry_history(
    entry_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeVersion]:
    """Return all versions of a knowledge entry, ordered by version number descending."""
    result = await db.execute(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.knowledge_entry_id == entry_id)
        .order_by(KnowledgeVersion.version_number.desc())
    )
    versions = result.scalars().all()
    if not versions:
        # Confirm the entry exists before returning empty list
        entry_exists = await db.scalar(
            select(func.count(KnowledgeEntry.id)).where(KnowledgeEntry.id == entry_id)
        )
        if not entry_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Entry {entry_id} not found")
    return list(versions)


@router.get("/stats", response_model=PipelineStatsResponse)
async def get_stats(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return pipeline statistics: counts by source type, review status, and persona domain."""
    total = await db.scalar(select(func.count(KnowledgeEntry.id))) or 0

    source_rows = await db.execute(
        select(KnowledgeEntry.source_type, func.count(KnowledgeEntry.id))
        .group_by(KnowledgeEntry.source_type)
    )
    by_source = {(row[0] or "unknown"): row[1] for row in source_rows}

    status_rows = await db.execute(
        select(KnowledgeEntry.review_status, func.count(KnowledgeEntry.id))
        .group_by(KnowledgeEntry.review_status)
    )
    by_status = {(row[0] or "unknown"): row[1] for row in status_rows}

    domain_rows = await db.execute(
        select(KnowledgeEntry.persona_domain, func.count(KnowledgeEntry.id))
        .group_by(KnowledgeEntry.persona_domain)
    )
    by_domain = {(row[0] or "unset"): row[1] for row in domain_rows}

    return {
        "total_entries": total,
        "by_source": by_source,
        "by_status": by_status,
        "by_domain": by_domain,
    }


# ============================================================================
# Patron Opt-Out
# ============================================================================


class PatronOptOutRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


@router.post("/patron-opt-out")
async def patron_opt_out(
    payload: PatronOptOutRequest,
    current_user: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Opt the current user out of training data capture."""
    from datetime import timezone as tz
    existing = await db.execute(
        select(PatronTrainingOptOut).where(PatronTrainingOptOut.patron_id == current_user.id)
    )
    opt_out = existing.scalar_one_or_none()
    if opt_out:
        opt_out.opted_out_at = datetime.now(tz.utc)
        opt_out.opted_in_at = None
        opt_out.reason = payload.reason
    else:
        opt_out = PatronTrainingOptOut(
            patron_id=current_user.id, reason=payload.reason, requested_via="web",
        )
        db.add(opt_out)
    await db.commit()
    return {"status": "opted_out", "patron_id": current_user.id}


@router.post("/patron-opt-in")
async def patron_opt_in(
    current_user: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Opt back in to training data capture."""
    from datetime import timezone as tz
    existing = await db.execute(
        select(PatronTrainingOptOut).where(PatronTrainingOptOut.patron_id == current_user.id)
    )
    opt_out = existing.scalar_one_or_none()
    if opt_out:
        opt_out.opted_in_at = datetime.now(tz.utc)
        await db.commit()
    return {"status": "opted_in", "patron_id": current_user.id}


@router.get("/patron-opt-out/status")
async def patron_opt_out_status(
    current_user: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check opt-out status."""
    existing = await db.execute(
        select(PatronTrainingOptOut).where(PatronTrainingOptOut.patron_id == current_user.id)
    )
    opt_out = existing.scalar_one_or_none()
    if opt_out and opt_out.is_opted_out:
        return {"opted_out": True, "since": opt_out.opted_out_at.isoformat()}
    return {"opted_out": False}


# ============================================================================
# Admin Retention / Purge
# ============================================================================


class PurgeRequest(BaseModel):
    purge_type: str = Field(..., pattern=r"^(date_range|source_type|patron)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source_type: Optional[str] = None
    patron_id: Optional[int] = None


@router.post("/admin/purge")
async def admin_purge(
    payload: PurgeRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin bulk purge of knowledge entries."""
    svc = KnowledgeRetentionService()
    count = 0
    if payload.purge_type == "date_range":
        if not payload.start_date or not payload.end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date required")
        count = await svc.purge_by_date_range(db, payload.start_date, payload.end_date)
    elif payload.purge_type == "source_type":
        if not payload.source_type:
            raise HTTPException(status_code=400, detail="source_type required")
        count = await svc.purge_by_source_type(db, payload.source_type)
    elif payload.purge_type == "patron":
        if not payload.patron_id:
            raise HTTPException(status_code=400, detail="patron_id required")
        count = await svc.purge_by_patron(db, payload.patron_id)
    await db.commit()
    return {"purged_count": count, "purge_type": payload.purge_type}


@router.get("/admin/retention-stats")
async def retention_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retention statistics."""
    svc = KnowledgeRetentionService()
    return await svc.get_retention_stats(db)


@router.post("/admin/run-retention", status_code=status.HTTP_202_ACCEPTED)
async def run_retention(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger scheduled retention cleanup."""
    async def _bg_run():
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                svc = KnowledgeRetentionService()
                count = await svc.purge_expired_conversations(db)
                await db.commit()
                logger.info("Retention cleanup: %d entries purged", count)
            except Exception:
                await db.rollback()
                logger.exception("Retention cleanup failed")
    background_tasks.add_task(_bg_run)
    return {"status": "accepted", "message": "Retention cleanup queued"}


# ============================================================================
# Training Data
# ============================================================================


class TrainingExampleResponse(BaseModel):
    id: int
    knowledge_entry_id: int
    persona_domain: Optional[str]
    instruction: str
    response: str
    source_type: str
    quality_score: int
    quality_breakdown: Optional[dict]
    bucket: str
    is_multi_turn: bool
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by_name: Optional[str]
    staff_override: bool
    override_reason: Optional[str]
    model_config = {"from_attributes": True}


class OverrideRequest(BaseModel):
    bucket: str = Field(..., pattern=r"^(approved|review|rejected)$")
    reason: str = Field(..., min_length=1, max_length=500)


@router.get("/training/review-queue", response_model=list[TrainingExampleResponse])
async def training_review_queue(
    persona_domain: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[TrainingExample]:
    """Paginated review queue of training examples."""
    query = select(TrainingExample).where(TrainingExample.bucket == "review")
    if persona_domain:
        query = query.where(TrainingExample.persona_domain == persona_domain)
    query = query.order_by(TrainingExample.quality_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/training/{example_id}/approve")
async def approve_training_example(
    example_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Staff approves a training example."""
    from datetime import timezone as tz
    result = await db.execute(select(TrainingExample).where(TrainingExample.id == example_id))
    te = result.scalar_one_or_none()
    if not te:
        raise HTTPException(status_code=404, detail="Training example not found")
    te.bucket = "approved"
    te.reviewed_at = datetime.now(tz.utc)
    te.reviewed_by_id = current_user.id
    te.reviewed_by_name = getattr(current_user, "full_name", None) or current_user.username
    await db.commit()
    return {"id": te.id, "bucket": "approved"}


@router.post("/training/{example_id}/reject")
async def reject_training_example(
    example_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Staff rejects a training example."""
    from datetime import timezone as tz
    result = await db.execute(select(TrainingExample).where(TrainingExample.id == example_id))
    te = result.scalar_one_or_none()
    if not te:
        raise HTTPException(status_code=404, detail="Training example not found")
    te.bucket = "rejected"
    te.reviewed_at = datetime.now(tz.utc)
    te.reviewed_by_id = current_user.id
    te.reviewed_by_name = getattr(current_user, "full_name", None) or current_user.username
    await db.commit()
    return {"id": te.id, "bucket": "rejected"}


@router.post("/training/{example_id}/override")
async def override_training_example(
    example_id: int,
    payload: OverrideRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Staff overrides bucket assignment."""
    from datetime import timezone as tz
    result = await db.execute(select(TrainingExample).where(TrainingExample.id == example_id))
    te = result.scalar_one_or_none()
    if not te:
        raise HTTPException(status_code=404, detail="Training example not found")
    te.bucket = payload.bucket
    te.staff_override = True
    te.override_reason = payload.reason
    te.reviewed_at = datetime.now(tz.utc)
    te.reviewed_by_id = current_user.id
    te.reviewed_by_name = getattr(current_user, "full_name", None) or current_user.username
    await db.commit()
    return {"id": te.id, "bucket": payload.bucket, "overridden": True}


@router.get("/training/stats")
async def training_stats(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Training data factory dashboard statistics."""
    svc = TrainingPipelineService()
    return await svc.get_stats(db)


@router.get("/training/readiness/{persona_domain}")
async def training_readiness(
    persona_domain: str,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check fine-tuning readiness for a persona."""
    svc = TrainingPipelineService()
    return await svc.get_readiness(db, persona_domain)


@router.get("/training/export")
async def export_training_data(
    persona_domain: str = Query(...),
    min_score: int = Query(80, ge=0, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Export approved training examples as JSONL."""
    from ...services.training_data_formatter_service import TrainingDataFormatterService
    result = await db.execute(
        select(TrainingExample).where(
            TrainingExample.bucket == "approved",
            TrainingExample.persona_domain == persona_domain,
            TrainingExample.quality_score >= min_score,
        ).order_by(TrainingExample.quality_score.desc())
    )
    examples = result.scalars().all()
    formatter = TrainingDataFormatterService()
    data = [{"instruction": te.instruction, "response": te.response} for te in examples]
    jsonl = formatter.export_jsonl(data)
    return {"persona_domain": persona_domain, "example_count": len(examples), "jsonl": jsonl}


@router.post("/training/process-batch", status_code=status.HTTP_202_ACCEPTED)
async def process_training_batch(
    persona_domain: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Trigger batch processing of knowledge entries into training examples."""
    async def _bg_process():
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                svc = TrainingPipelineService()
                examples = await svc.process_batch(db, persona_domain=persona_domain, limit=limit)
                await db.commit()
                logger.info("Batch processing: %d examples created", len(examples))
            except Exception:
                await db.rollback()
                logger.exception("Batch processing failed")
    background_tasks.add_task(_bg_process)
    return {"status": "accepted", "message": "Batch processing queued"}
