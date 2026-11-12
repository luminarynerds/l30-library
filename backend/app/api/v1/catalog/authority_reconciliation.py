# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import AsyncSessionLocal, get_db
from ....models.user import User
from ....services.authority_reconciliation_service import (
    get_reconciliation_stats,
    reconcile_unlinked_contributors,
    reconcile_unlinked_subjects,
)
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/authority", tags=["catalog-authority"])

# In-memory job tracker (single-worker safe)
_job_status: dict = {"running": False, "last_result": None}


async def _run_reconciliation():
    global _job_status
    try:
        async with AsyncSessionLocal() as db:
            contributors = await reconcile_unlinked_contributors(db)
            subjects = await reconcile_unlinked_subjects(db)
        _job_status["last_result"] = {
            "contributors": contributors,
            "subjects": subjects,
            "status": "completed",
        }
    except Exception as exc:
        logger.exception("Authority reconciliation failed")
        _job_status["last_result"] = {"status": "failed", "error": str(exc)}
    finally:
        _job_status["running"] = False


@router.post("/reconcile", status_code=status.HTTP_202_ACCEPTED)
async def trigger_reconciliation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_staff),
):
    """Trigger a batch authority reconciliation run (staff only)."""
    if _job_status["running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A reconciliation job is already running.",
        )
    _job_status["running"] = True
    _job_status["last_result"] = None
    background_tasks.add_task(_run_reconciliation)
    return {"message": "Reconciliation started", "status": "running"}


@router.get("/reconcile/stats")
async def reconciliation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return linked/unlinked counts for contributors and subjects (staff only)."""
    stats = await get_reconciliation_stats(db)
    stats["job"] = {
        "running": _job_status["running"],
        "last_result": _job_status["last_result"],
    }
    return stats
