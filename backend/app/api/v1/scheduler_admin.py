# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Scheduler administration endpoints.
Monitor and manage background jobs.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from .auth import get_current_user
from .dependencies import require_admin
from ...models.user import User
from ...core.scheduler import get_scheduler, get_job

router = APIRouter(prefix="/admin/scheduler", tags=["Admin Scheduler"])


class JobInfo(Dict[str, Any]):
    pass


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_scheduler_jobs(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
):
    """
    List all scheduled background jobs.
    Admin only.
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    result = []
    for job in jobs:
        next_run = getattr(job, 'next_run_time', None)
        result.append({
            "id": job.id,
            "name": job.name,
            "func": job.func_ref if hasattr(job, 'func_ref') else str(job.func),
            "trigger": str(job.trigger),
            "next_run_time": next_run.isoformat() if next_run else None,
            "args": getattr(job, 'args', []),
            "kwargs": getattr(job, 'kwargs', {}),
        })
    return result


@router.post("/jobs/{job_id}/run", response_model=Dict[str, Any])
async def run_job_now(
    job_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
):
    """
    Trigger a scheduled job immediately.
    Admin only. Useful for testing or forcing early execution.
    """
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        # Execute the job function
        if job.func_ref:
            # For async functions
            import asyncio
            result = await job.func(*job.args, **job.kwargs)
        else:
            result = job.func(*job.args, **job.kwargs)

        return {
            "status": "executed",
            "job_id": job_id,
            "result": result,
        }
    except Exception as e:  # noqa: BLE001  # manual job execution — surface any error to operator
        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e),
        }


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_info(
    job_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin),
):
    """
    Get detailed information about a scheduled job.
    Admin only.
    """
    job = await get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "id": job.id,
        "name": job.name,
        "func": job.func_ref if hasattr(job, 'func_ref') else str(job.func),
        "trigger": str(job.trigger),
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "args": job.args,
        "kwargs": job.kwargs,
    }
