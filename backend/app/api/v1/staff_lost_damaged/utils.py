# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared utilities for the staff lost/damaged API package.

Contains:
- Common error handling decorator
- Record conversion helper functions used across multiple sub-routers
"""

import functools
from app.core.logging import get_logger
from typing import Callable

from fastapi import HTTPException, status

from ....schemas.lost_damaged import (
    LostItemRecordResponse,
    DamagedItemRecordResponse,
    MendingQueueEntryResponse,
    ClaimsReturnedDisputeResponse,
)

logger = get_logger(__name__)


def handle_enum_validation(enum_class, value: str, field_name: str):
    try:
        return enum_class(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: {value}",
        ) from None


def handle_service_error(result):
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )


def convert_lost_record(record) -> LostItemRecordResponse:
    patron_name = None
    if record.patron:
        patron_name = f"{record.patron.first_name} {record.patron.last_name}"

    item_title = None
    if record.catalog_item:
        item_title = record.catalog_item.title

    fine_amount = None
    fine_status = None
    if record.fine:
        fine_amount = record.fine.amount
        fine_status = str(record.fine.status)

    return LostItemRecordResponse(
        id=record.id,
        item_copy_id=record.item_copy_id,
        checkout_id=record.checkout_id,
        catalog_item_id=record.catalog_item_id,
        patron_id=record.patron_id,
        status=record.status,
        lost_type=record.lost_type,
        item_price=record.item_price,
        processing_fee=record.processing_fee,
        replacement_cost=record.replacement_cost,
        credit_amount=record.credit_amount,
        days_overdue_at_loss=record.days_overdue_at_loss,
        report_notes=record.report_notes,
        resolution_notes=record.resolution_notes,
        reported_at=record.reported_at,
        confirmed_at=record.confirmed_at,
        charged_at=record.charged_at,
        found_at=record.found_at,
        written_off_at=record.written_off_at,
        last_known_location=record.last_known_location,
        patron_name=patron_name,
        item_title=item_title,
        fine_amount=fine_amount,
        fine_status=fine_status,
    )


def convert_damaged_record(record) -> DamagedItemRecordResponse:
    patron_name = None
    if record.patron:
        patron_name = f"{record.patron.first_name} {record.patron.last_name}"

    item_title = None
    if record.catalog_item:
        item_title = record.catalog_item.title

    fine_status = None
    if record.fine:
        fine_status = str(record.fine.status)

    return DamagedItemRecordResponse(
        id=record.id,
        item_copy_id=record.item_copy_id,
        checkout_id=record.checkout_id,
        catalog_item_id=record.catalog_item_id,
        patron_id=record.patron_id,
        status=record.status,
        severity=record.severity,
        damage_types=record.damage_types,
        damage_description=record.damage_description,
        photo_urls=record.photo_urls,
        assessment_notes=record.assessment_notes,
        is_patron_responsible=record.is_patron_responsible,
        estimated_repair_cost=record.estimated_repair_cost,
        actual_repair_cost=record.actual_repair_cost,
        replacement_cost=record.replacement_cost,
        charge_amount=record.charge_amount,
        repair_priority=record.repair_priority,
        repair_notes=record.repair_notes,
        reported_at=record.reported_at,
        assessed_at=record.assessed_at,
        resolved_at=record.resolved_at,
        patron_name=patron_name,
        item_title=item_title,
        fine_status=fine_status,
    )


def convert_mending_entry(entry) -> MendingQueueEntryResponse:
    item_title = None
    if entry.damaged_item_record and entry.damaged_item_record.catalog_item:
        item_title = entry.damaged_item_record.catalog_item.title

    assigned_to_name = None
    if entry.assigned_to:
        assigned_to_name = f"{entry.assigned_to.first_name} {entry.assigned_to.last_name}"

    return MendingQueueEntryResponse(
        id=entry.id,
        damaged_item_record_id=entry.damaged_item_record_id,
        item_copy_id=entry.item_copy_id,
        priority=entry.priority,
        queue_position=entry.queue_position,
        repair_type=entry.repair_type,
        repair_instructions=entry.repair_instructions,
        materials_needed=entry.materials_needed,
        estimated_time_hours=entry.estimated_time_hours,
        estimated_cost=entry.estimated_cost,
        actual_cost=entry.actual_cost,
        is_in_progress=entry.is_in_progress,
        is_completed=entry.is_completed,
        added_at=entry.added_at,
        started_at=entry.started_at,
        completed_at=entry.completed_at,
        notes=entry.notes,
        completion_notes=entry.completion_notes,
        item_title=item_title,
        assigned_to_name=assigned_to_name,
    )


def convert_dispute(dispute) -> ClaimsReturnedDisputeResponse:
    patron_name = None
    if dispute.patron:
        patron_name = f"{dispute.patron.first_name} {dispute.patron.last_name}"

    item_title = None
    if dispute.item_copy and dispute.item_copy.catalog_item:
        item_title = dispute.item_copy.catalog_item.title
    elif dispute.checkout and dispute.checkout.item:
        item_title = dispute.checkout.item.title

    reviewer_name = None
    if dispute.reviewed_by:
        reviewer_name = f"{dispute.reviewed_by.first_name} {dispute.reviewed_by.last_name}"

    return ClaimsReturnedDisputeResponse(
        id=dispute.id,
        lost_item_record_id=dispute.lost_item_record_id,
        item_copy_id=dispute.item_copy_id,
        checkout_id=dispute.checkout_id,
        patron_id=dispute.patron_id,
        status=dispute.status,
        patron_statement=dispute.patron_statement,
        claimed_return_date=dispute.claimed_return_date,
        claimed_return_location=dispute.claimed_return_location,
        investigation_notes=dispute.investigation_notes,
        search_locations=dispute.search_locations,
        resolution=dispute.resolution,
        resolution_reason=dispute.resolution_reason,
        credit_amount=dispute.credit_amount,
        patron_previous_claims_count=dispute.patron_previous_claims_count,
        filed_at=dispute.filed_at,
        reviewed_at=dispute.reviewed_at,
        resolved_at=dispute.resolved_at,
        patron_name=patron_name,
        item_title=item_title,
        reviewer_name=reviewer_name,
    )
