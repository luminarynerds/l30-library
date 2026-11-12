# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflows import (
    ActionType,
    StepType,
    TriggerType,
    Workflow,
    WorkflowStep,
)


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

OVERDUE_NOTICE_ESCALATION: Dict[str, Any] = {
    "name": "Overdue Notice Escalation",
    "description": (
        "Automatically escalates overdue notices over 30 days: "
        "email reminder at 3 days, SMS + email at 10 days, "
        "final notice + account flag at 24 days, and collections referral at 30 days."
    ),
    "trigger": TriggerType.event,
    "trigger_config": {
        "event_type": "item_overdue",
        "description": "Fires when an item becomes overdue",
    },
    "steps": [
        {
            "order": 0,
            "name": "Wait 3 days",
            "step_type": StepType.delay,
            "delay_duration": 3,
            "delay_unit": "days",
            "config": {"description": "Allow a grace period before first notice"},
        },
        {
            "order": 1,
            "name": "Send email reminder",
            "step_type": StepType.action,
            "action_type": ActionType.send_email,
            "config": {
                "template_id": "overdue_reminder_1",
                "subject": "Friendly reminder: you have an overdue item",
                "recipient": "{{patron_email}}",
            },
        },
        {
            "order": 2,
            "name": "Wait 7 days",
            "step_type": StepType.delay,
            "delay_duration": 7,
            "delay_unit": "days",
            "config": {"description": "Wait before second notice"},
        },
        {
            "order": 3,
            "name": "Send SMS + email",
            "step_type": StepType.notification,
            "config": {
                "channel": "sms+email",
                "message": "Your item is now 10 days overdue. Please return it to avoid additional fees.",
                "template_id": "overdue_reminder_2",
                "recipient": "{{patron_email}}",
                "phone": "{{patron_phone}}",
            },
        },
        {
            "order": 4,
            "name": "Wait 14 days",
            "step_type": StepType.delay,
            "delay_duration": 14,
            "delay_unit": "days",
            "config": {"description": "Wait before final notice"},
        },
        {
            "order": 5,
            "name": "Send final notice + flag account",
            "step_type": StepType.action,
            "action_type": ActionType.send_email,
            "config": {
                "template_id": "overdue_final_notice",
                "subject": "FINAL NOTICE: Overdue library item",
                "recipient": "{{patron_email}}",
            },
        },
        {
            "order": 6,
            "name": "Flag patron account",
            "step_type": StepType.action,
            "action_type": ActionType.flag_account,
            "config": {
                "reason": "Item overdue 24+ days - final notice sent",
            },
        },
        {
            "order": 7,
            "name": "Wait 6 more days",
            "step_type": StepType.delay,
            "delay_duration": 6,
            "delay_unit": "days",
            "config": {"description": "Wait remaining days before collections"},
        },
        {
            "order": 8,
            "name": "Send to collections",
            "step_type": StepType.action,
            "action_type": ActionType.send_to_collections,
            "config": {
                "reason": "Item overdue 30+ days, all notices exhausted",
            },
        },
    ],
}


HOLD_FULFILLMENT: Dict[str, Any] = {
    "name": "Hold Fulfillment",
    "description": (
        "Automates hold fulfillment when a returned item matches a hold: "
        "creates transit if needed, moves to hold shelf, sends pickup "
        "notification, reminds before expiry, and cancels if uncollected."
    ),
    "trigger": TriggerType.event,
    "trigger_config": {
        "event_type": "hold_matched",
        "description": "Fires when a returned item matches an active hold",
    },
    "steps": [
        {
            "order": 0,
            "name": "Check if transit needed",
            "step_type": StepType.condition,
            "condition": "item_branch != pickup_branch",
            "config": {"description": "Is the item at a different branch than the pickup location?"},
            "on_failure": "2",  # Skip transit, go to hold shelf step
        },
        {
            "order": 1,
            "name": "Create transit to pickup branch",
            "step_type": StepType.action,
            "action_type": ActionType.create_transit,
            "config": {
                "from_branch": "{{item_branch}}",
                "to_branch": "{{pickup_branch}}",
            },
        },
        {
            "order": 2,
            "name": "Move to hold shelf",
            "step_type": StepType.action,
            "action_type": ActionType.move_to_hold_shelf,
            "config": {
                "description": "Place item on the hold shelf at pickup branch",
            },
        },
        {
            "order": 3,
            "name": "Send hold-ready notification",
            "step_type": StepType.notification,
            "config": {
                "channel": "email",
                "template_id": "hold_ready",
                "message": "Your hold is ready for pickup!",
                "recipient": "{{patron_email}}",
            },
        },
        {
            "order": 4,
            "name": "Wait 7 days",
            "step_type": StepType.delay,
            "delay_duration": 7,
            "delay_unit": "days",
            "config": {"description": "Wait for patron to pick up"},
        },
        {
            "order": 5,
            "name": "Send expiring-soon reminder",
            "step_type": StepType.notification,
            "config": {
                "channel": "email",
                "template_id": "hold_expiring",
                "message": "Your hold expires in 3 days. Please pick it up soon!",
                "recipient": "{{patron_email}}",
            },
        },
        {
            "order": 6,
            "name": "Wait 3 more days",
            "step_type": StepType.delay,
            "delay_duration": 3,
            "delay_unit": "days",
            "config": {"description": "Final waiting period before cancellation"},
        },
        {
            "order": 7,
            "name": "Cancel hold",
            "step_type": StepType.action,
            "action_type": ActionType.cancel_hold,
            "config": {
                "reason": "Hold expired - not picked up within 10 days",
            },
        },
        {
            "order": 8,
            "name": "Notify next patron in queue",
            "step_type": StepType.action,
            "action_type": ActionType.notify_next_in_queue,
            "config": {
                "description": "Move to next patron in the hold queue",
            },
        },
    ],
}


NEW_ITEM_PROCESSING: Dict[str, Any] = {
    "name": "New Item Processing",
    "description": (
        "Automates new-item intake: generates a MARC record if missing, "
        "checks for catalog duplicates, assigns a shelf location, and "
        "auto-orders additional copies for popular authors."
    ),
    "trigger": TriggerType.event,
    "trigger_config": {
        "event_type": "item_added",
        "description": "Fires when a new item is added to the catalog",
    },
    "steps": [
        {
            "order": 0,
            "name": "Check for MARC record",
            "step_type": StepType.condition,
            "condition": "has_marc_record == false",
            "config": {"description": "Does this item need a MARC record?"},
            "on_failure": "2",  # Skip MARC generation
        },
        {
            "order": 1,
            "name": "Generate MARC record",
            "step_type": StepType.action,
            "action_type": ActionType.generate_marc_record,
            "config": {
                "description": "Auto-generate MARC record from item metadata",
            },
        },
        {
            "order": 2,
            "name": "Check for duplicate catalog entries",
            "step_type": StepType.action,
            "action_type": ActionType.check_duplicates,
            "config": {
                "description": "Search catalog for potential duplicate entries",
            },
        },
        {
            "order": 3,
            "name": "Assign shelf location",
            "step_type": StepType.action,
            "action_type": ActionType.assign_shelf_location,
            "config": {
                "description": "Auto-assign based on item type, genre, and call number",
            },
        },
        {
            "order": 4,
            "name": "Check if popular author",
            "step_type": StepType.condition,
            "condition": "is_popular_author == true",
            "config": {"description": "Is this a popular/high-demand author?"},
        },
        {
            "order": 5,
            "name": "Auto-order 2 additional copies",
            "step_type": StepType.action,
            "action_type": ActionType.auto_order_copies,
            "config": {
                "quantity": 2,
                "reason": "Popular author - auto-ordering additional copies",
            },
        },
    ],
}


# Lookup by template slug
TEMPLATES = {
    "overdue_notice_escalation": OVERDUE_NOTICE_ESCALATION,
    "hold_fulfillment": HOLD_FULFILLMENT,
    "new_item_processing": NEW_ITEM_PROCESSING,
}


# ---------------------------------------------------------------------------
# Template instantiation
# ---------------------------------------------------------------------------

async def instantiate_template(
    db: AsyncSession,
    template_key: str,
    created_by_id: int | None = None,
    active: bool = True,
) -> Workflow:
    template = TEMPLATES.get(template_key)
    if not template:
        raise ValueError(
            f"Unknown template '{template_key}'. "
            f"Available: {', '.join(TEMPLATES.keys())}"
        )

    workflow = Workflow(
        name=template["name"],
        description=template["description"],
        trigger=template["trigger"],
        trigger_config=template["trigger_config"],
        created_by_id=created_by_id,
        active=active,
        is_template=False,
        template_name=template_key,
    )
    db.add(workflow)
    await db.flush()

    for step_data in template["steps"]:
        step = WorkflowStep(
            workflow_id=workflow.id,
            order=step_data["order"],
            name=step_data.get("name"),
            step_type=step_data["step_type"],
            action_type=step_data.get("action_type"),
            condition=step_data.get("condition"),
            delay_duration=step_data.get("delay_duration"),
            delay_unit=step_data.get("delay_unit"),
            config=step_data.get("config"),
            on_success=step_data.get("on_success"),
            on_failure=step_data.get("on_failure"),
        )
        db.add(step)

    await db.flush()
    return workflow


async def list_available_templates() -> List[Dict[str, Any]]:
    summaries = []
    for key, tmpl in TEMPLATES.items():
        summaries.append({
            "key": key,
            "name": tmpl["name"],
            "description": tmpl["description"],
            "trigger": tmpl["trigger"],
            "trigger_config": tmpl["trigger_config"],
            "steps_count": len(tmpl["steps"]),
        })
    return summaries
