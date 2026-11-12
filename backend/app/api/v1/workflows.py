# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Workflow Automation API Endpoints

Staff-facing API for creating, managing, and executing automated workflows.
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_staff
from ...models.user import User
from ...models.workflows import TriggerType
from app.services.workflow_engine import (
    cancel_execution,
    create_workflow,
    delete_workflow,
    get_execution,
    get_executions,
    get_workflow,
    get_workflow_preview,
    get_workflows,
    run_workflow,
    toggle_workflow,
    update_workflow,
)
from app.services.workflow_templates import (
    instantiate_template,
    list_available_templates,
)

router = APIRouter(prefix="/staff/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# Workflow CRUD
# ---------------------------------------------------------------------------

@router.get("")
async def list_workflows(
    active_only: bool = Query(False, description="Only show active workflows"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List all workflows visible to staff."""
    workflows = await get_workflows(db, active_only=active_only)
    return {
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "trigger": w.trigger,
                "trigger_config": w.trigger_config,
                "active": w.active,
                "is_template": w.is_template,
                "template_name": w.template_name,
                "last_run": w.last_run.isoformat() if w.last_run else None,
                "run_count": w.run_count,
                "steps_count": len(w.steps),
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in workflows
        ]
    }


@router.get("/{workflow_id}")
async def get_workflow_detail(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get a workflow with all its steps."""
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow": _serialize_workflow(workflow),
    }


@router.post("")
async def create_new_workflow(
    name: str,
    trigger: TriggerType,
    description: Optional[str] = None,
    trigger_config: Optional[Dict] = None,
    steps: Optional[List[Dict]] = None,
    active: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a custom workflow."""
    workflow = await create_workflow(
        db=db,
        name=name,
        description=description,
        trigger=trigger,
        trigger_config=trigger_config,
        created_by_id=current_user.id,
        steps_data=steps,
        active=active,
    )
    await db.commit()
    await db.refresh(workflow)
    return {
        "message": f"Workflow '{workflow.name}' created",
        "workflow": _serialize_workflow(workflow),
    }


@router.put("/{workflow_id}")
async def update_existing_workflow(
    workflow_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    trigger: Optional[TriggerType] = None,
    trigger_config: Optional[Dict] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a workflow's configuration."""
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if trigger is not None:
        updates["trigger"] = trigger
    if trigger_config is not None:
        updates["trigger_config"] = trigger_config
    if active is not None:
        updates["active"] = active

    workflow = await update_workflow(db, workflow_id, updates)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    await db.commit()
    await db.refresh(workflow)
    return {
        "message": f"Workflow '{workflow.name}' updated",
        "workflow": _serialize_workflow(workflow),
    }


@router.delete("/{workflow_id}")
async def delete_existing_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a workflow and all associated data."""
    deleted = await delete_workflow(db, workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.commit()
    return {"message": "Workflow deleted"}


@router.post("/{workflow_id}/toggle")
async def toggle_workflow_active(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Toggle a workflow's active/inactive state."""
    workflow = await toggle_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.commit()
    return {
        "message": f"Workflow {'activated' if workflow.active else 'deactivated'}",
        "active": workflow.active,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/run")
async def execute_workflow(
    workflow_id: int,
    context: Optional[Dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually run a workflow with optional context."""
    try:
        execution = await run_workflow(
            db=db,
            workflow_id=workflow_id,
            context=context,
            triggered_by_id=current_user.id,
        )
        await db.commit()
        return {
            "message": f"Workflow execution {execution.status}",
            "execution": _serialize_execution(execution),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List execution history for a workflow."""
    executions = await get_executions(db, workflow_id=workflow_id, limit=limit)
    return {
        "executions": [_serialize_execution(e) for e in executions],
    }


@router.get("/{workflow_id}/preview")
async def preview_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Preview what a workflow would affect if run today."""
    preview = await get_workflow_preview(db, workflow_id)
    return preview


@router.get("/executions/all")
async def list_all_executions(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List recent executions across all workflows."""
    executions = await get_executions(db, limit=limit)
    return {
        "executions": [_serialize_execution(e) for e in executions],
    }


@router.get("/executions/{execution_id}")
async def get_execution_detail(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed execution results including step-by-step log."""
    execution = await get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        "execution": _serialize_execution(execution),
    }


@router.post("/executions/{execution_id}/cancel")
async def cancel_workflow_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Cancel a running workflow execution."""
    execution = await cancel_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    await db.commit()
    return {
        "message": "Execution cancelled",
        "execution": _serialize_execution(execution),
    }


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

async def get_available_templates(
    current_user: User = Depends(require_staff),
):
    templates = await list_available_templates()
    return {"templates": templates}


async def instantiate_workflow_template(
    template_key: str,
    active: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    try:
        workflow = await instantiate_template(
            db=db,
            template_key=template_key,
            created_by_id=current_user.id,
            active=active,
        )
        await db.commit()
        await db.refresh(workflow)
        return {
            "message": f"Template '{template_key}' instantiated as workflow '{workflow.name}'",
            "workflow": _serialize_workflow(workflow),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_workflow(w) -> Dict:
    return {
        "id": w.id,
        "name": w.name,
        "description": w.description,
        "trigger": w.trigger,
        "trigger_config": w.trigger_config,
        "active": w.active,
        "is_template": w.is_template,
        "template_name": w.template_name,
        "last_run": w.last_run.isoformat() if w.last_run else None,
        "run_count": w.run_count,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "steps": [
            {
                "id": s.id,
                "order": s.order,
                "name": s.name,
                "step_type": s.step_type,
                "action_type": s.action_type,
                "condition": s.condition,
                "delay_duration": s.delay_duration,
                "delay_unit": s.delay_unit,
                "config": s.config,
                "on_success": s.on_success,
                "on_failure": s.on_failure,
            }
            for s in sorted(w.steps, key=lambda s: s.order)
        ],
    }


def _serialize_execution(e) -> Dict:
    return {
        "id": e.id,
        "workflow_id": e.workflow_id,
        "triggered_by_id": e.triggered_by_id,
        "triggered_at": e.triggered_at.isoformat() if e.triggered_at else None,
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "status": e.status,
        "current_step": e.current_step,
        "context": e.context,
        "step_results": e.step_results,
        "error_message": e.error_message,
    }
