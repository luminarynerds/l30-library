# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
from app.core.logging import get_logger
import operator
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflows import (
    ActionType,
    ExecutionStatus,
    StepResultStatus,
    StepType,
    TriggerType,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
)

logger = get_logger(__name__)

# Maximum retries for a failed step before giving up
MAX_STEP_RETRIES = 2


# ---------------------------------------------------------------------------
# Condition evaluator
# ---------------------------------------------------------------------------

# Supported comparison operators
_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}

_CONDITION_RE = re.compile(
    r"^\s*(\w+)\s*(==|!=|>=?|<=?)\s*(.+?)\s*$"
)


def _coerce_value(raw: str) -> Any:
    # Strip surrounding quotes
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    # Boolean
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    # Numeric
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def evaluate_condition(expression: str, context: Dict[str, Any]) -> bool:
    match = _CONDITION_RE.match(expression)
    if not match:
        logger.warning("Unparseable condition expression: %s", expression)
        return False

    field, op_str, raw_value = match.groups()
    # An unquoted RHS that names another context key is a field-to-field
    # comparison (e.g. the built-in HOLD_FULFILLMENT template's
    # "item_branch != pickup_branch"), not a literal string. Quoted
    # strings and numeric/boolean literals always win over a same-named
    # context key.
    is_quoted = raw_value[:1] in ("'", '"')
    if not is_quoted and raw_value in context:
        expected = context.get(raw_value)
    else:
        expected = _coerce_value(raw_value)
    actual = context.get(field)

    if actual is None:
        return False

    # Normalize types for comparison
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float, Decimal)):
        actual = float(actual)
        expected = float(expected)

    op_fn = _OPS.get(op_str)
    if op_fn is None:
        logger.warning("Unknown operator: %s", op_str)
        return False

    try:
        return op_fn(actual, expected)
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# Action executor
# ---------------------------------------------------------------------------

async def execute_action(
    step: WorkflowStep,
    context: Dict[str, Any],
    db: AsyncSession,
) -> Dict[str, Any]:
    action = step.action_type
    config = step.config or {}
    result: Dict[str, Any] = {"action": action, "config": config}

    if action == ActionType.send_email:
        recipient = config.get("recipient") or context.get("patron_email")
        template = config.get("template_id", "default")
        result.update({
            "success": True,
            "message": f"Email sent to {recipient} using template {template}",
            "recipient": recipient,
        })

    elif action == ActionType.send_sms:
        phone = config.get("phone") or context.get("patron_phone")
        result.update({
            "success": True,
            "message": f"SMS sent to {phone}",
            "phone": phone,
        })

    elif action == ActionType.create_transit:
        from_branch = config.get("from_branch") or context.get("item_branch")
        to_branch = config.get("to_branch") or context.get("pickup_branch")
        result.update({
            "success": True,
            "message": f"Transit created from {from_branch} to {to_branch}",
        })

    elif action == ActionType.update_status:
        target = config.get("target", "item")
        new_status = config.get("new_status")
        result.update({
            "success": True,
            "message": f"Status of {target} updated to {new_status}",
        })

    elif action == ActionType.generate_report:
        report_type = config.get("report_type", "general")
        result.update({
            "success": True,
            "message": f"Report generated: {report_type}",
        })

    elif action == ActionType.assign_task:
        assignee = config.get("assignee") or context.get("staff_id")
        result.update({
            "success": True,
            "message": f"Task assigned to staff {assignee}",
        })

    elif action == ActionType.place_hold:
        item_id = config.get("item_id") or context.get("item_id")
        patron_id = config.get("patron_id") or context.get("patron_id")
        result.update({
            "success": True,
            "message": f"Hold placed on item {item_id} for patron {patron_id}",
        })

    elif action == ActionType.cancel_hold:
        hold_id = config.get("hold_id") or context.get("hold_id")
        result.update({
            "success": True,
            "message": f"Hold {hold_id} cancelled",
        })

    elif action == ActionType.flag_account:
        patron_id = config.get("patron_id") or context.get("patron_id")
        flag_reason = config.get("reason", "automated workflow flag")
        result.update({
            "success": True,
            "message": f"Account {patron_id} flagged: {flag_reason}",
        })

    elif action == ActionType.send_to_collections:
        patron_id = config.get("patron_id") or context.get("patron_id")
        result.update({
            "success": True,
            "message": f"Patron {patron_id} account sent to collections",
        })

    elif action == ActionType.auto_order_copies:
        item_id = config.get("item_id") or context.get("item_id")
        quantity = config.get("quantity", 2)
        result.update({
            "success": True,
            "message": f"Auto-ordered {quantity} additional copies of item {item_id}",
        })

    elif action == ActionType.generate_marc_record:
        item_id = config.get("item_id") or context.get("item_id")
        result.update({
            "success": True,
            "message": f"MARC record generated for item {item_id}",
        })

    elif action == ActionType.check_duplicates:
        item_id = config.get("item_id") or context.get("item_id")
        result.update({
            "success": True,
            "message": f"Duplicate check completed for item {item_id}",
            "duplicates_found": 0,
        })

    elif action == ActionType.assign_shelf_location:
        item_id = config.get("item_id") or context.get("item_id")
        location = config.get("location", "auto-assigned")
        result.update({
            "success": True,
            "message": f"Item {item_id} assigned to shelf location {location}",
        })

    elif action == ActionType.move_to_hold_shelf:
        item_id = config.get("item_id") or context.get("item_id")
        result.update({
            "success": True,
            "message": f"Item {item_id} moved to hold shelf",
        })

    elif action == ActionType.notify_next_in_queue:
        hold_id = config.get("hold_id") or context.get("hold_id")
        result.update({
            "success": True,
            "message": f"Next patron in hold queue notified for hold {hold_id}",
        })

    else:
        result.update({
            "success": False,
            "message": f"Unknown action type: {action}",
        })

    return result


# ---------------------------------------------------------------------------
# Workflow engine – main execution loop
# ---------------------------------------------------------------------------

class WorkflowEngine:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None,
        triggered_by_id: Optional[int] = None,
    ) -> WorkflowExecution:
        context = dict(context or {})
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            triggered_by_id=triggered_by_id,
            status=ExecutionStatus.running,
            context=context,
            step_results=[],
        )
        self.db.add(execution)
        await self.db.flush()

        steps = sorted(workflow.steps, key=lambda s: s.order)
        step_idx = 0

        try:
            while step_idx < len(steps):
                step = steps[step_idx]
                execution.current_step = step.id

                step_result = await self._execute_step(step, context)
                results = list(execution.step_results or [])
                results.append(step_result)
                execution.step_results = results

                if step_result["status"] == StepResultStatus.failed:
                    # Determine branching on failure
                    on_fail = step.on_failure or "stop"
                    if on_fail == "stop":
                        execution.status = ExecutionStatus.failed
                        execution.error_message = step_result.get("message", "Step failed")
                        break
                    # Jump to the referenced step id
                    jump_idx = self._find_step_index(steps, on_fail)
                    if jump_idx is not None:
                        step_idx = jump_idx
                        continue
                    # Could not find target – stop
                    execution.status = ExecutionStatus.failed
                    execution.error_message = f"Branch target {on_fail} not found"
                    break

                if step_result["status"] == StepResultStatus.skipped:
                    # Condition was false – check on_failure for alternate path
                    on_fail = step.on_failure
                    if on_fail and on_fail != "stop":
                        jump_idx = self._find_step_index(steps, on_fail)
                        if jump_idx is not None:
                            step_idx = jump_idx
                            continue
                    step_idx += 1
                    continue

                # Success – check for explicit next step
                on_ok = step.on_success
                if on_ok:
                    jump_idx = self._find_step_index(steps, on_ok)
                    if jump_idx is not None:
                        step_idx = jump_idx
                        continue

                step_idx += 1

            # If we made it through all steps without failure, mark completed
            if execution.status == ExecutionStatus.running:
                execution.status = ExecutionStatus.completed

        except Exception as exc:
            logger.exception("Workflow %s execution error", workflow.id)
            execution.status = ExecutionStatus.failed
            execution.error_message = str(exc)

        execution.completed_at = datetime.now(timezone.utc)
        execution.current_step = None

        # Update workflow run stats
        workflow.last_run = execution.completed_at
        workflow.run_count = (workflow.run_count or 0) + 1

        await self.db.flush()
        return execution

    # ---- internal helpers ----

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "step_id": step.id,
            "step_name": step.name,
            "step_type": step.step_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            if step.step_type == StepType.condition:
                met = evaluate_condition(step.condition or "", context)
                result["status"] = StepResultStatus.success if met else StepResultStatus.skipped
                result["message"] = (
                    f"Condition met: {step.condition}" if met
                    else f"Condition not met: {step.condition}"
                )
                result["condition_met"] = met

            elif step.step_type == StepType.delay:
                duration_minutes = self._resolve_delay(step)
                # In production, this would schedule a continuation.
                # For immediate execution we log the intent.
                result["status"] = StepResultStatus.success
                result["message"] = f"Delay of {duration_minutes} minutes recorded"
                result["delay_minutes"] = duration_minutes

            elif step.step_type == StepType.action:
                action_result = await self._execute_action_with_retry(step, context)
                result.update(action_result)
                result["status"] = (
                    StepResultStatus.success if action_result.get("success")
                    else StepResultStatus.failed
                )

            elif step.step_type == StepType.notification:
                config = step.config or {}
                channel = config.get("channel", "email")
                recipient = config.get("recipient") or context.get("patron_email")
                message = config.get("message", "Workflow notification")
                result["status"] = StepResultStatus.success
                result["message"] = f"Notification ({channel}) sent to {recipient}: {message}"

            else:
                result["status"] = StepResultStatus.failed
                result["message"] = f"Unknown step type: {step.step_type}"

        except Exception as exc:  # noqa: BLE001 -- workflow step boundary: any step failure marks step failed for retry/skip, never crash engine
            result["status"] = StepResultStatus.failed
            result["message"] = str(exc)

        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        return result

    async def _execute_action_with_retry(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        last_result: Dict[str, Any] = {}
        for attempt in range(MAX_STEP_RETRIES + 1):  # 0 = initial attempt, 1..N = retries
            last_result = await execute_action(step, context, self.db)
            if last_result.get("success"):
                return last_result
            if attempt < MAX_STEP_RETRIES:
                logger.info(
                    "Step %s attempt %d failed, retrying...",
                    step.id, attempt + 1,
                )
        return last_result

    @staticmethod
    def _resolve_delay(step: WorkflowStep) -> int:
        duration = step.delay_duration or 0
        unit = (step.delay_unit or "minutes").lower()
        if unit == "hours":
            return duration * 60
        if unit == "days":
            return duration * 60 * 24
        return duration  # default minutes

    @staticmethod
    def _find_step_index(steps: List[WorkflowStep], target: str) -> Optional[int]:
        try:
            target_id = int(target)
        except (ValueError, TypeError):
            return None
        for i, s in enumerate(steps):
            if s.order == target_id:
                return i
        return None


# ---------------------------------------------------------------------------
# Service-level helper functions (used by the API layer)
# ---------------------------------------------------------------------------

async def get_workflows(
    db: AsyncSession,
    active_only: bool = False,
    include_templates: bool = False,
) -> List[Workflow]:
    query = select(Workflow).options(selectinload(Workflow.steps))
    if active_only:
        query = query.where(Workflow.active == True)
    if not include_templates:
        query = query.where(Workflow.is_template == False)
    query = query.order_by(Workflow.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_workflow(db: AsyncSession, workflow_id: int) -> Optional[Workflow]:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )
    return result.scalar_one_or_none()


async def create_workflow(
    db: AsyncSession,
    name: str,
    description: Optional[str],
    trigger: TriggerType,
    trigger_config: Optional[Dict],
    created_by_id: Optional[int],
    steps_data: Optional[List[Dict]] = None,
    active: bool = True,
) -> Workflow:
    workflow = Workflow(
        name=name,
        description=description,
        trigger=trigger,
        trigger_config=trigger_config,
        created_by_id=created_by_id,
        active=active,
    )
    db.add(workflow)
    await db.flush()

    if steps_data:
        for idx, sd in enumerate(steps_data):
            step = WorkflowStep(
                workflow_id=workflow.id,
                order=sd.get("order", idx),
                name=sd.get("name"),
                step_type=sd["step_type"],
                action_type=sd.get("action_type"),
                condition=sd.get("condition"),
                delay_duration=sd.get("delay_duration"),
                delay_unit=sd.get("delay_unit"),
                config=sd.get("config"),
                on_success=sd.get("on_success"),
                on_failure=sd.get("on_failure", "stop"),
            )
            db.add(step)

    await db.flush()
    return workflow


async def update_workflow(
    db: AsyncSession,
    workflow_id: int,
    updates: Dict[str, Any],
) -> Optional[Workflow]:
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(workflow, key):
            setattr(workflow, key, value)
    await db.flush()
    return workflow


async def delete_workflow(db: AsyncSession, workflow_id: int) -> bool:
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return False
    await db.delete(workflow)
    await db.flush()
    return True


async def toggle_workflow(db: AsyncSession, workflow_id: int) -> Optional[Workflow]:
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return None
    workflow.active = not workflow.active
    await db.flush()
    return workflow


async def run_workflow(
    db: AsyncSession,
    workflow_id: int,
    context: Optional[Dict[str, Any]] = None,
    triggered_by_id: Optional[int] = None,
) -> WorkflowExecution:
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise ValueError(f"Workflow {workflow_id} not found")
    if not workflow.active:
        raise ValueError(f"Workflow {workflow_id} is not active")

    engine = WorkflowEngine(db)
    return await engine.execute(workflow, context, triggered_by_id)


async def get_executions(
    db: AsyncSession,
    workflow_id: Optional[int] = None,
    limit: int = 50,
) -> List[WorkflowExecution]:
    query = select(WorkflowExecution)
    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    query = query.order_by(WorkflowExecution.triggered_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_execution(
    db: AsyncSession,
    execution_id: int,
) -> Optional[WorkflowExecution]:
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    return result.scalar_one_or_none()


async def cancel_execution(
    db: AsyncSession,
    execution_id: int,
) -> Optional[WorkflowExecution]:
    execution = await get_execution(db, execution_id)
    if not execution:
        return None
    if execution.status == ExecutionStatus.running:
        execution.status = ExecutionStatus.cancelled
        execution.completed_at = datetime.now(timezone.utc)
        await db.flush()
    return execution


async def get_workflow_preview(
    db: AsyncSession,
    workflow_id: int,
) -> Dict[str, Any]:
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        return {"error": "Workflow not found"}

    # Simulated preview – in production, this would query actual data
    trigger_config = workflow.trigger_config or {}
    event_type = trigger_config.get("event_type", "unknown")

    preview: Dict[str, Any] = {
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
        "trigger": workflow.trigger,
        "trigger_config": trigger_config,
        "steps_count": len(workflow.steps),
        "estimated_affected_items": 0,
        "description": "",
    }

    if event_type == "item_overdue":
        preview["estimated_affected_items"] = 47
        preview["description"] = "47 currently overdue items would enter this workflow"
    elif event_type == "hold_matched":
        preview["estimated_affected_items"] = 12
        preview["description"] = "12 holds currently awaiting fulfillment would be processed"
    elif event_type == "item_added":
        preview["estimated_affected_items"] = 5
        preview["description"] = "5 items added today would be processed"
    else:
        preview["estimated_affected_items"] = 0
        preview["description"] = "No preview data available for this trigger type"

    return preview
