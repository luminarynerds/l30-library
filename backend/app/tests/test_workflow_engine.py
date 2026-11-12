# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for the workflow automation system.

Tests cover:
- Workflow model creation and configuration
- Condition evaluation (comparisons, type coercion, edge cases)
- Action execution for each action type
- Workflow engine step-by-step execution
- Branching on condition success/failure
- Delay step handling
- Notification steps
- Error handling and retry logic
- Pre-built template instantiation and execution
- Workflow CRUD operations
"""

import pytest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.workflow_engine import (
    WorkflowEngine,
    cancel_execution,
    create_workflow,
    delete_workflow,
    evaluate_condition,
    execute_action,
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
    HOLD_FULFILLMENT,
    NEW_ITEM_PROCESSING,
    OVERDUE_NOTICE_ESCALATION,
    TEMPLATES,
    instantiate_template,
    list_available_templates,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# NOTE: no local `db` fixture here. This file used to spin up its own
# in-memory SQLite engine via Base.metadata.create_all, which pulls in
# every model registered on the shared Base.metadata (importing
# app.models.workflows imports the app.models package first, which
# registers every table) -- including several Postgres-only column
# types/defaults (TSVECTOR, ARRAY, `::jsonb`-cast server defaults) that
# SQLite's compiler can't render. Falls through to the shared
# Postgres-backed `db` fixture in app/tests/conftest.py instead.


@pytest.fixture
async def sample_workflow(db: AsyncSession) -> Workflow:
    """Create a simple workflow with a few steps."""
    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow for unit testing",
        trigger=TriggerType.manual,
        trigger_config={"description": "manual trigger"},
        active=True,
    )
    db.add(workflow)
    await db.flush()

    steps = [
        WorkflowStep(
            workflow_id=workflow.id,
            order=0,
            name="Send email",
            step_type=StepType.action,
            action_type=ActionType.send_email,
            config={"template_id": "test", "recipient": "patron@test.com"},
        ),
        WorkflowStep(
            workflow_id=workflow.id,
            order=1,
            name="Wait 3 days",
            step_type=StepType.delay,
            delay_duration=3,
            delay_unit="days",
        ),
        WorkflowStep(
            workflow_id=workflow.id,
            order=2,
            name="Send SMS",
            step_type=StepType.action,
            action_type=ActionType.send_sms,
            config={"phone": "555-0100"},
        ),
    ]
    for s in steps:
        db.add(s)

    await db.flush()
    await db.refresh(workflow)
    return workflow


@pytest.fixture
async def conditional_workflow(db: AsyncSession) -> Workflow:
    """Create a workflow with a condition step."""
    workflow = Workflow(
        name="Conditional Workflow",
        trigger=TriggerType.manual,
        active=True,
    )
    db.add(workflow)
    await db.flush()

    steps = [
        WorkflowStep(
            workflow_id=workflow.id,
            order=0,
            name="Check patron type",
            step_type=StepType.condition,
            condition='patron_type == "adult"',
        ),
        WorkflowStep(
            workflow_id=workflow.id,
            order=1,
            name="Send adult email",
            step_type=StepType.action,
            action_type=ActionType.send_email,
            config={"template_id": "adult_notice"},
        ),
    ]
    for s in steps:
        db.add(s)

    await db.flush()
    await db.refresh(workflow)
    return workflow


# ---------------------------------------------------------------------------
# Condition Evaluation Tests
# ---------------------------------------------------------------------------


class TestConditionEvaluation:
    """Tests for the condition expression evaluator."""

    def test_string_equality(self):
        assert evaluate_condition('patron_type == "adult"', {"patron_type": "adult"}) is True

    def test_string_inequality(self):
        assert evaluate_condition('patron_type == "adult"', {"patron_type": "child"}) is False

    def test_numeric_greater_than(self):
        assert evaluate_condition("days_overdue > 14", {"days_overdue": 15}) is True

    def test_numeric_greater_than_equal(self):
        assert evaluate_condition("days_overdue > 14", {"days_overdue": 14}) is False

    def test_numeric_less_than(self):
        assert evaluate_condition("fine_amount < 10.00", {"fine_amount": 5.50}) is True

    def test_numeric_less_than_false(self):
        assert evaluate_condition("fine_amount < 10.00", {"fine_amount": 15.00}) is False

    def test_greater_equal(self):
        assert evaluate_condition("fine_amount >= 10.00", {"fine_amount": 10.00}) is True

    def test_less_equal(self):
        assert evaluate_condition("days_overdue <= 7", {"days_overdue": 7}) is True

    def test_not_equal(self):
        assert evaluate_condition('status != "active"', {"status": "expired"}) is True

    def test_boolean_true(self):
        assert evaluate_condition("is_popular_author == true", {"is_popular_author": True}) is True

    def test_boolean_false(self):
        assert evaluate_condition("has_marc_record == false", {"has_marc_record": False}) is True

    def test_missing_field_returns_false(self):
        assert evaluate_condition("nonexistent > 5", {}) is False

    def test_unparseable_expression(self):
        assert evaluate_condition("this is not valid", {}) is False

    def test_integer_comparison(self):
        assert evaluate_condition("count == 42", {"count": 42}) is True

    def test_float_comparison_with_decimal(self):
        from decimal import Decimal
        assert evaluate_condition("amount > 10.00", {"amount": Decimal("15.50")}) is True

    def test_single_quote_string(self):
        assert evaluate_condition("name == 'John'", {"name": "John"}) is True

    def test_branch_comparison(self):
        assert evaluate_condition(
            "item_branch != pickup_branch",
            {"item_branch": "Main", "pickup_branch": "Main"},
        ) is False


# ---------------------------------------------------------------------------
# Action Execution Tests
# ---------------------------------------------------------------------------


class TestActionExecution:
    """Tests for individual action step execution."""

    @pytest.mark.asyncio
    async def test_send_email(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.send_email,
            config={"template_id": "test", "recipient": "user@test.com"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True
        assert "user@test.com" in result["message"]

    @pytest.mark.asyncio
    async def test_send_sms(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.send_sms,
            config={"phone": "555-0100"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True
        assert "555-0100" in result["message"]

    @pytest.mark.asyncio
    async def test_create_transit(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.create_transit,
            config={"from_branch": "Main", "to_branch": "North"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True
        assert "Main" in result["message"]
        assert "North" in result["message"]

    @pytest.mark.asyncio
    async def test_update_status(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.update_status,
            config={"target": "item", "new_status": "in_transit"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_report(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.generate_report,
            config={"report_type": "overdue_summary"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_assign_task(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.assign_task,
            config={"assignee": 42},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_place_hold(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.place_hold,
            config={"item_id": 1, "patron_id": 2},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_hold(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.cancel_hold,
            config={"hold_id": 99},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_flag_account(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.flag_account,
            config={"patron_id": 5, "reason": "overdue 30+ days"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_to_collections(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.send_to_collections,
            config={"patron_id": 5},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_auto_order_copies(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.auto_order_copies,
            config={"item_id": 10, "quantity": 3},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True
        assert "3" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_marc_record(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.generate_marc_record,
            config={"item_id": 10},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_check_duplicates(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.check_duplicates,
            config={"item_id": 10},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True
        assert result["duplicates_found"] == 0

    @pytest.mark.asyncio
    async def test_assign_shelf_location(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.assign_shelf_location,
            config={"item_id": 10, "location": "Fiction A-F"},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_move_to_hold_shelf(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.move_to_hold_shelf,
            config={"item_id": 10},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_notify_next_in_queue(self, db: AsyncSession):
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.notify_next_in_queue,
            config={"hold_id": 99},
        )
        result = await execute_action(step, {}, db)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_action_uses_context_fallback(self, db: AsyncSession):
        """Actions should use context values when config doesn't provide them."""
        step = WorkflowStep(
            step_type=StepType.action,
            action_type=ActionType.send_email,
            config={"template_id": "test"},
        )
        context = {"patron_email": "context@test.com"}
        result = await execute_action(step, context, db)
        assert result["success"] is True
        assert "context@test.com" in result["message"]


# ---------------------------------------------------------------------------
# Workflow Engine Execution Tests
# ---------------------------------------------------------------------------


class TestWorkflowEngine:
    """Tests for full workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(
        self, db: AsyncSession, sample_workflow: Workflow
    ):
        # Reload with steps
        workflow = await get_workflow(db, sample_workflow.id)
        engine = WorkflowEngine(db)
        execution = await engine.execute(workflow, {})

        assert execution.status == ExecutionStatus.completed
        assert execution.completed_at is not None
        assert len(execution.step_results) == 3
        assert all(
            r["status"] in (StepResultStatus.success, StepResultStatus.skipped)
            for r in execution.step_results
        )

    @pytest.mark.asyncio
    async def test_execute_with_condition_met(
        self, db: AsyncSession, conditional_workflow: Workflow
    ):
        workflow = await get_workflow(db, conditional_workflow.id)
        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow, {"patron_type": "adult"}
        )

        assert execution.status == ExecutionStatus.completed
        assert len(execution.step_results) == 2
        assert execution.step_results[0]["condition_met"] is True

    @pytest.mark.asyncio
    async def test_execute_with_condition_not_met(
        self, db: AsyncSession, conditional_workflow: Workflow
    ):
        workflow = await get_workflow(db, conditional_workflow.id)
        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow, {"patron_type": "child"}
        )

        assert execution.status == ExecutionStatus.completed
        # Condition skipped, but still proceeds to next step
        assert execution.step_results[0]["condition_met"] is False
        assert execution.step_results[0]["status"] == StepResultStatus.skipped

    @pytest.mark.asyncio
    async def test_execute_updates_run_count(
        self, db: AsyncSession, sample_workflow: Workflow
    ):
        workflow = await get_workflow(db, sample_workflow.id)
        original_count = workflow.run_count or 0

        engine = WorkflowEngine(db)
        await engine.execute(workflow, {})

        assert workflow.run_count == original_count + 1
        assert workflow.last_run is not None

    @pytest.mark.asyncio
    async def test_execute_notification_step(self, db: AsyncSession):
        workflow = Workflow(
            name="Notification Test",
            trigger=TriggerType.manual,
            active=True,
        )
        db.add(workflow)
        await db.flush()

        step = WorkflowStep(
            workflow_id=workflow.id,
            order=0,
            name="Send notification",
            step_type=StepType.notification,
            config={
                "channel": "email",
                "recipient": "staff@l30.org",
                "message": "Test notification",
            },
        )
        db.add(step)
        await db.flush()

        workflow = await get_workflow(db, workflow.id)
        engine = WorkflowEngine(db)
        execution = await engine.execute(workflow, {})

        assert execution.status == ExecutionStatus.completed
        assert "notification" in execution.step_results[0]["message"].lower()

    @pytest.mark.asyncio
    async def test_delay_step_records_duration(self, db: AsyncSession):
        workflow = Workflow(
            name="Delay Test",
            trigger=TriggerType.manual,
            active=True,
        )
        db.add(workflow)
        await db.flush()

        step = WorkflowStep(
            workflow_id=workflow.id,
            order=0,
            name="Wait 5 days",
            step_type=StepType.delay,
            delay_duration=5,
            delay_unit="days",
        )
        db.add(step)
        await db.flush()

        workflow = await get_workflow(db, workflow.id)
        engine = WorkflowEngine(db)
        execution = await engine.execute(workflow, {})

        assert execution.status == ExecutionStatus.completed
        assert execution.step_results[0]["delay_minutes"] == 5 * 24 * 60


# ---------------------------------------------------------------------------
# Service Layer Tests
# ---------------------------------------------------------------------------


class TestWorkflowCRUD:
    """Tests for workflow CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_workflow(self, db: AsyncSession):
        workflow = await create_workflow(
            db=db,
            name="New Workflow",
            description="Testing creation",
            trigger=TriggerType.manual,
            trigger_config=None,
            created_by_id=None,
            steps_data=[
                {
                    "name": "Step 1",
                    "step_type": StepType.action,
                    "action_type": ActionType.send_email,
                    "config": {"recipient": "test@test.com"},
                }
            ],
        )
        assert workflow.id is not None
        assert workflow.name == "New Workflow"

    @pytest.mark.asyncio
    async def test_get_workflows(self, db: AsyncSession, sample_workflow: Workflow):
        workflows = await get_workflows(db)
        assert len(workflows) >= 1
        assert any(w.id == sample_workflow.id for w in workflows)

    @pytest.mark.asyncio
    async def test_get_workflows_active_only(self, db: AsyncSession):
        active = Workflow(name="Active", trigger=TriggerType.manual, active=True)
        inactive = Workflow(name="Inactive", trigger=TriggerType.manual, active=False)
        db.add(active)
        db.add(inactive)
        await db.flush()

        workflows = await get_workflows(db, active_only=True)
        names = [w.name for w in workflows]
        assert "Active" in names
        assert "Inactive" not in names

    @pytest.mark.asyncio
    async def test_update_workflow(self, db: AsyncSession, sample_workflow: Workflow):
        updated = await update_workflow(
            db, sample_workflow.id, {"name": "Updated Name", "description": "New desc"}
        )
        assert updated.name == "Updated Name"
        assert updated.description == "New desc"

    @pytest.mark.asyncio
    async def test_delete_workflow(self, db: AsyncSession, sample_workflow: Workflow):
        deleted = await delete_workflow(db, sample_workflow.id)
        assert deleted is True

        fetched = await get_workflow(db, sample_workflow.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_toggle_workflow(self, db: AsyncSession, sample_workflow: Workflow):
        original = sample_workflow.active
        toggled = await toggle_workflow(db, sample_workflow.id)
        assert toggled.active is not original

    @pytest.mark.asyncio
    async def test_run_workflow(self, db: AsyncSession, sample_workflow: Workflow):
        execution = await run_workflow(db, sample_workflow.id, context={})
        assert execution.status == ExecutionStatus.completed

    @pytest.mark.asyncio
    async def test_run_inactive_workflow_raises(self, db: AsyncSession):
        workflow = Workflow(
            name="Inactive", trigger=TriggerType.manual, active=False
        )
        db.add(workflow)
        await db.flush()

        with pytest.raises(ValueError, match="not active"):
            await run_workflow(db, workflow.id)

    @pytest.mark.asyncio
    async def test_run_nonexistent_workflow_raises(self, db: AsyncSession):
        with pytest.raises(ValueError, match="not found"):
            await run_workflow(db, 99999)


# ---------------------------------------------------------------------------
# Execution Management Tests
# ---------------------------------------------------------------------------


class TestExecutionManagement:
    """Tests for execution listing and cancellation."""

    @pytest.mark.asyncio
    async def test_get_executions(self, db: AsyncSession, sample_workflow: Workflow):
        await run_workflow(db, sample_workflow.id, context={})
        await run_workflow(db, sample_workflow.id, context={})

        executions = await get_executions(db, workflow_id=sample_workflow.id)
        assert len(executions) >= 2

    @pytest.mark.asyncio
    async def test_cancel_running_execution(
        self, db: AsyncSession, sample_workflow: Workflow
    ):
        # workflow_id is a real FK to workflows.id; a hardcoded 1 only
        # happened to work against a fresh in-memory SQLite db (which
        # doesn't enforce FKs by default). The shared Postgres-backed `db`
        # fixture does enforce it, and IDs aren't reset to 1 between tests.
        execution = WorkflowExecution(
            workflow_id=sample_workflow.id,
            status=ExecutionStatus.running,
        )
        db.add(execution)
        await db.flush()

        cancelled = await cancel_execution(db, execution.id)
        assert cancelled.status == ExecutionStatus.cancelled
        assert cancelled.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_completed_execution_is_noop(
        self, db: AsyncSession, sample_workflow: Workflow
    ):
        execution = WorkflowExecution(
            workflow_id=sample_workflow.id,
            status=ExecutionStatus.completed,
        )
        db.add(execution)
        await db.flush()

        result = await cancel_execution(db, execution.id)
        assert result.status == ExecutionStatus.completed  # unchanged

    @pytest.mark.asyncio
    async def test_get_workflow_preview(
        self, db: AsyncSession, sample_workflow: Workflow
    ):
        preview = await get_workflow_preview(db, sample_workflow.id)
        assert "workflow_id" in preview
        assert "steps_count" in preview


# ---------------------------------------------------------------------------
# Template Tests
# ---------------------------------------------------------------------------


class TestWorkflowTemplates:
    """Tests for pre-built workflow templates."""

    @pytest.mark.asyncio
    async def test_list_available_templates(self):
        templates = await list_available_templates()
        assert len(templates) == 3
        keys = [t["key"] for t in templates]
        assert "overdue_notice_escalation" in keys
        assert "hold_fulfillment" in keys
        assert "new_item_processing" in keys

    @pytest.mark.asyncio
    async def test_instantiate_overdue_notice(self, db: AsyncSession):
        workflow = await instantiate_template(db, "overdue_notice_escalation")
        assert workflow.name == "Overdue Notice Escalation"
        assert workflow.trigger == TriggerType.event
        assert workflow.active is True

        workflow = await get_workflow(db, workflow.id)
        assert len(workflow.steps) == len(OVERDUE_NOTICE_ESCALATION["steps"])

    @pytest.mark.asyncio
    async def test_instantiate_hold_fulfillment(self, db: AsyncSession):
        workflow = await instantiate_template(db, "hold_fulfillment")
        assert workflow.name == "Hold Fulfillment"
        assert len(HOLD_FULFILLMENT["steps"]) == 9

        workflow = await get_workflow(db, workflow.id)
        assert len(workflow.steps) == len(HOLD_FULFILLMENT["steps"])

    @pytest.mark.asyncio
    async def test_instantiate_new_item_processing(self, db: AsyncSession):
        workflow = await instantiate_template(db, "new_item_processing")
        assert workflow.name == "New Item Processing"

        workflow = await get_workflow(db, workflow.id)
        assert len(workflow.steps) == len(NEW_ITEM_PROCESSING["steps"])

    @pytest.mark.asyncio
    async def test_instantiate_unknown_template_raises(self, db: AsyncSession):
        with pytest.raises(ValueError, match="Unknown template"):
            await instantiate_template(db, "nonexistent")

    @pytest.mark.asyncio
    async def test_execute_overdue_notice_template(self, db: AsyncSession):
        """Execute the overdue notice escalation template end-to-end."""
        workflow = await instantiate_template(db, "overdue_notice_escalation")
        workflow = await get_workflow(db, workflow.id)

        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow,
            {
                "patron_email": "patron@test.com",
                "patron_phone": "555-0100",
                "patron_id": 42,
                "item_id": 7,
            },
        )

        assert execution.status == ExecutionStatus.completed
        assert len(execution.step_results) == len(OVERDUE_NOTICE_ESCALATION["steps"])

    @pytest.mark.asyncio
    async def test_execute_hold_fulfillment_same_branch(self, db: AsyncSession):
        """Execute hold fulfillment when item is at the same branch (skip transit)."""
        workflow = await instantiate_template(db, "hold_fulfillment")
        workflow = await get_workflow(db, workflow.id)

        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow,
            {
                "item_branch": "Main",
                "pickup_branch": "Main",
                "patron_email": "patron@test.com",
                "hold_id": 99,
            },
        )

        assert execution.status == ExecutionStatus.completed
        # First step (condition) should be skipped since branches are the same
        assert execution.step_results[0]["condition_met"] is False

    @pytest.mark.asyncio
    async def test_execute_hold_fulfillment_different_branch(self, db: AsyncSession):
        """Execute hold fulfillment when item needs transit."""
        workflow = await instantiate_template(db, "hold_fulfillment")
        workflow = await get_workflow(db, workflow.id)

        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow,
            {
                "item_branch": "Main",
                "pickup_branch": "North",
                "patron_email": "patron@test.com",
                "hold_id": 99,
            },
        )

        assert execution.status == ExecutionStatus.completed
        assert execution.step_results[0]["condition_met"] is True

    @pytest.mark.asyncio
    async def test_execute_new_item_with_marc(self, db: AsyncSession):
        """Execute new item processing when MARC record exists (skip generation)."""
        workflow = await instantiate_template(db, "new_item_processing")
        workflow = await get_workflow(db, workflow.id)

        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow,
            {
                "item_id": 10,
                "has_marc_record": True,
                "is_popular_author": False,
            },
        )

        assert execution.status == ExecutionStatus.completed
        # First condition (has_marc_record == false) should be false
        assert execution.step_results[0]["condition_met"] is False

    @pytest.mark.asyncio
    async def test_execute_new_item_popular_author(self, db: AsyncSession):
        """Execute new item processing for a popular author (auto-order copies)."""
        workflow = await instantiate_template(db, "new_item_processing")
        workflow = await get_workflow(db, workflow.id)

        engine = WorkflowEngine(db)
        execution = await engine.execute(
            workflow,
            {
                "item_id": 10,
                "has_marc_record": False,
                "is_popular_author": True,
            },
        )

        assert execution.status == ExecutionStatus.completed
        # All steps should execute including the popular author auto-order
        results = execution.step_results
        assert any("auto_order_copies" in str(r.get("action", "")) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
