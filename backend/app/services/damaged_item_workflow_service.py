# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.email import send_email, COLORS
from ..core.frontend_routes import routes
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus
from ..models.fine import Fine, FineStatus, FineType
from ..models.inventory import ItemCopy, ItemCondition, DamageType
from ..models.lost_damaged import (
    DamagedItemRecord, DamagedItemStatus, DamageSeverity,
    MendingQueue, LostDamagedSettings
)
from ..models.user import User
from . import operations_audit_service as ops_audit

logger = get_logger(__name__)

settings = get_settings()


@dataclass
class DamageAssessmentResult:
    is_repairable: bool
    severity: DamageSeverity
    estimated_repair_cost: Decimal
    recommended_action: str  # "repair", "withdraw", "no_action"
    patron_charge_amount: Decimal
    charge_percentage: Decimal


@dataclass
class DamagedItemWorkflowResult:
    success: bool
    damaged_item_record: Optional[DamagedItemRecord]
    fine: Optional[Fine]
    mending_entry: Optional[MendingQueue]
    notification_sent: bool
    message: str
    assessment: Optional[DamageAssessmentResult]


@dataclass
class RepairResult:
    success: bool
    damaged_item_record: Optional[DamagedItemRecord]
    item_restored: bool
    actual_cost: Decimal
    message: str


class DamagedItemWorkflowService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(
        self,
        branch_id: Optional[int] = None,
        branch_location: Optional[str] = None,
    ) -> LostDamagedSettings:
        from ..core.branch_resolver import label_to_branch_id
        if branch_id is None:
            branch_id = label_to_branch_id(branch_location)
        if branch_id is not None:
            result = await self.db.execute(
                select(LostDamagedSettings).where(
                    LostDamagedSettings.branch_id == branch_id,
                    LostDamagedSettings.is_active == True
                )
            )
            branch_settings = result.scalar_one_or_none()
            if branch_settings:
                return branch_settings

        result = await self.db.execute(
            select(LostDamagedSettings).where(
                LostDamagedSettings.branch_id == None,
                LostDamagedSettings.branch_location == None,
                LostDamagedSettings.is_active == True
            )
        )
        system_settings = result.scalar_one_or_none()

        if system_settings:
            return system_settings

        # Return defaults from config
        return LostDamagedSettings(
            minor_damage_charge_percentage=Decimal(str(settings.minor_damage_charge_pct)),
            moderate_damage_charge_percentage=Decimal(str(settings.moderate_damage_charge_pct)),
            severe_damage_charge_percentage=Decimal(str(settings.severe_damage_charge_pct)),
            total_loss_charge_percentage=Decimal(str(settings.total_loss_damage_charge_pct)),
            default_replacement_cost=Decimal(str(settings.lost_item_default_replacement_cost)),
        )

    def calculate_damage_charge(
        self,
        severity: DamageSeverity,
        replacement_cost: Decimal,
        workflow_settings: LostDamagedSettings,
    ) -> Tuple[Decimal, Decimal]:
        percentage_map = {
            DamageSeverity.MINOR: workflow_settings.minor_damage_charge_percentage,
            DamageSeverity.MODERATE: workflow_settings.moderate_damage_charge_percentage,
            DamageSeverity.SEVERE: workflow_settings.severe_damage_charge_percentage,
            DamageSeverity.TOTAL_LOSS: workflow_settings.total_loss_charge_percentage,
        }

        percentage = percentage_map.get(severity, Decimal("0.00"))
        charge = (replacement_cost * percentage) / Decimal("100")

        return charge, percentage

    def assess_damage(
        self,
        severity: DamageSeverity,
        damage_types: List[str],
        replacement_cost: Decimal,
        workflow_settings: LostDamagedSettings,
    ) -> DamageAssessmentResult:
        # Determine if repairable based on severity and damage types
        is_repairable = True
        recommended_action = "repair"

        if severity == DamageSeverity.TOTAL_LOSS:
            is_repairable = False
            recommended_action = "withdraw"
        elif severity == DamageSeverity.SEVERE:
            # Some severe damages are not repairable
            unrepairable_damages = [
                DamageType.MISSING_PAGES.value,
                DamageType.WATER_DAMAGE.value,  # Often causes permanent damage
            ]
            if any(dt in damage_types for dt in unrepairable_damages):
                is_repairable = False
                recommended_action = "withdraw"

        # Estimate repair cost (rough calculation)
        repair_cost_estimates = {
            DamageSeverity.MINOR: Decimal("5.00"),
            DamageSeverity.MODERATE: Decimal("15.00"),
            DamageSeverity.SEVERE: Decimal("30.00"),
            DamageSeverity.TOTAL_LOSS: Decimal("0.00"),  # Not repairable
        }
        estimated_repair_cost = repair_cost_estimates.get(severity, Decimal("10.00"))

        # If repair cost > 50% of replacement cost, may be better to withdraw
        if is_repairable and estimated_repair_cost > (replacement_cost * Decimal("0.5")):
            is_repairable = False
            recommended_action = "withdraw"

        # Calculate patron charge
        charge_amount, charge_percentage = self.calculate_damage_charge(
            severity, replacement_cost, workflow_settings
        )

        if severity == DamageSeverity.MINOR:
            recommended_action = "no_action" if charge_amount == 0 else "repair"

        return DamageAssessmentResult(
            is_repairable=is_repairable,
            severity=severity,
            estimated_repair_cost=estimated_repair_cost if is_repairable else Decimal("0.00"),
            recommended_action=recommended_action,
            patron_charge_amount=charge_amount,
            charge_percentage=charge_percentage
        )

    async def report_damage(
        self,
        item_copy_id: int,
        damage_types: List[DamageType],
        damage_description: str,
        severity: DamageSeverity,
        reported_by: User,
        checkout_id: Optional[int] = None,
        patron_id: Optional[int] = None,
        is_patron_responsible: bool = False,
        photo_urls: Optional[List[str]] = None,
        send_notification: bool = True,
    ) -> DamagedItemWorkflowResult:
        # Get item copy with related data
        result = await self.db.execute(
            select(ItemCopy)
            .options(selectinload(ItemCopy.catalog_item))
            .where(ItemCopy.id == item_copy_id)
            .with_for_update()
        )
        item_copy = result.scalar_one_or_none()

        if not item_copy:
            return DamagedItemWorkflowResult(
                success=False,
                damaged_item_record=None,
                fine=None,
                mending_entry=None,
                notification_sent=False,
                message="Item copy not found",
                assessment=None
            )

        # Get settings and replacement cost
        workflow_settings = await self.get_settings(branch_location=item_copy.location)
        replacement_cost = Decimal(str(item_copy.replacement_cost)) if item_copy.replacement_cost \
            else workflow_settings.default_replacement_cost

        # Assess damage
        damage_type_values = [dt.value for dt in damage_types]
        assessment = self.assess_damage(
            severity=severity,
            damage_types=damage_type_values,
            replacement_cost=replacement_cost,
            workflow_settings=workflow_settings
        )

        now = datetime.now(timezone.utc)

        # Get patron info if checkout provided
        checkout = None
        if checkout_id:
            checkout_result = await self.db.execute(
                select(Checkout)
                .options(selectinload(Checkout.user))
                .where(Checkout.id == checkout_id)
            )
            checkout = checkout_result.scalar_one_or_none()
            if checkout:
                patron_id = checkout.user_id

        # Create damage record
        damage_record = DamagedItemRecord(
            item_copy_id=item_copy_id,
            checkout_id=checkout_id,
            catalog_item_id=item_copy.catalog_item_id,
            patron_id=patron_id,
            status=DamagedItemStatus.REPORTED,
            severity=severity,
            damage_types=damage_type_values,
            damage_description=damage_description,
            photo_urls=photo_urls,
            is_patron_responsible=is_patron_responsible,
            estimated_repair_cost=assessment.estimated_repair_cost,
            replacement_cost=replacement_cost,
            reported_by_id=reported_by.id,
            reported_at=now,
        )
        self.db.add(damage_record)
        await self.db.flush()

        # Update item status based on severity
        if severity == DamageSeverity.TOTAL_LOSS:
            item_copy.condition = ItemCondition.WITHDRAWN
            if item_copy.catalog_item:
                item_copy.catalog_item.status = ItemStatus.damaged_withdrawn
            damage_record.status = DamagedItemStatus.WITHDRAWN
            damage_record.withdrawn_at = now
        elif severity in [DamageSeverity.MODERATE, DamageSeverity.SEVERE]:
            item_copy.condition = ItemCondition.DAMAGED
            if item_copy.catalog_item:
                item_copy.catalog_item.status = ItemStatus.damaged_repairable
            damage_record.status = DamagedItemStatus.ASSESSMENT_PENDING
        else:
            item_copy.condition = ItemCondition.POOR
            damage_record.status = DamagedItemStatus.ASSESSMENT_PENDING

        # Update checkout status if applicable
        if checkout and checkout.status in [CheckoutStatus.active, CheckoutStatus.overdue]:
            checkout.status = CheckoutStatus.returned_damaged
            checkout.returned_at = now

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to report damage")
            raise

        # Re-fetch damage record with relationships to avoid MissingGreenlet
        # on lazy-load when serializing the response
        refetch_result = await self.db.execute(
            select(DamagedItemRecord)
            .options(
                selectinload(DamagedItemRecord.patron),
                selectinload(DamagedItemRecord.catalog_item),
                selectinload(DamagedItemRecord.item_copy),
                selectinload(DamagedItemRecord.fine),
            )
            .where(DamagedItemRecord.id == damage_record.id)
        )
        damage_record = refetch_result.scalar_one_or_none() or damage_record

        return DamagedItemWorkflowResult(
            success=True,
            damaged_item_record=damage_record,
            fine=None,
            mending_entry=None,
            notification_sent=False,
            message="Damage reported successfully",
            assessment=assessment
        )

    async def complete_assessment(
        self,
        damage_record_id: int,
        assessed_by: User,
        is_repairable: bool,
        charge_patron: bool = False,
        charge_amount: Optional[Decimal] = None,
        assessment_notes: Optional[str] = None,
        patron_responsibility_reason: Optional[str] = None,
        send_notification: bool = True,
    ) -> DamagedItemWorkflowResult:
        result = await self.db.execute(
            select(DamagedItemRecord)
            .options(
                selectinload(DamagedItemRecord.item_copy),
                selectinload(DamagedItemRecord.catalog_item),
                selectinload(DamagedItemRecord.patron)
            )
            .where(DamagedItemRecord.id == damage_record_id)
            .with_for_update()
        )
        damage_record = result.scalar_one_or_none()

        if not damage_record:
            return DamagedItemWorkflowResult(
                success=False,
                damaged_item_record=None,
                fine=None,
                mending_entry=None,
                notification_sent=False,
                message="Damage record not found",
                assessment=None
            )

        now = datetime.now(timezone.utc)
        fine = None
        mending_entry = None
        notification_sent = False

        # Update assessment info
        damage_record.assessed_by_id = assessed_by.id
        damage_record.assessed_at = now
        damage_record.assessment_notes = assessment_notes

        if patron_responsibility_reason:
            damage_record.is_patron_responsible = True
            damage_record.patron_responsibility_reason = patron_responsibility_reason

        # Charge patron if requested
        if charge_patron and damage_record.patron_id:
            amount = charge_amount or damage_record.charge_amount or Decimal("0.00")
            if amount > 0:
                fine = Fine(
                    user_id=damage_record.patron_id,
                    checkout_id=damage_record.checkout_id,
                    fine_type=FineType.damaged_item,
                    status=FineStatus.unpaid,
                    amount=amount,
                    description=f"Damage charge: {damage_record.catalog_item.title if damage_record.catalog_item else 'Unknown item'}",
                    notes=f"Damage type: {damage_record.severity}. {assessment_notes or ''}",
                )
                self.db.add(fine)
                await self.db.flush()
                damage_record.fine_id = fine.id
                damage_record.charge_amount = amount

                # Audit log for damage fine creation
                patron = await self.db.get(User, damage_record.patron_id)
                if patron:
                    await ops_audit.log_fine_assessed(
                        db=self.db, patron=patron, fine=fine
                    )

        if is_repairable:
            damage_record.status = DamagedItemStatus.REPAIRABLE
            if damage_record.catalog_item:
                damage_record.catalog_item.status = ItemStatus.damaged_repairable
        else:
            damage_record.status = DamagedItemStatus.WITHDRAWN
            damage_record.withdrawn_at = now
            if damage_record.item_copy:
                damage_record.item_copy.condition = ItemCondition.WITHDRAWN
            if damage_record.catalog_item:
                damage_record.catalog_item.status = ItemStatus.damaged_withdrawn

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to complete damage assessment")
            raise

        # Send notification only after successful commit
        if fine and send_notification and damage_record.patron and damage_record.patron.email:
            workflow_settings = await self.get_settings()
            if workflow_settings.notify_patron_on_damaged_charge:
                notification_sent = await self._send_damage_charge_notification(
                    patron=damage_record.patron,
                    item=damage_record.catalog_item,
                    charge_amount=fine.amount,
                    damage_description=damage_record.damage_description,
                )

        return DamagedItemWorkflowResult(
            success=True,
            damaged_item_record=damage_record,
            fine=fine,
            mending_entry=mending_entry,
            notification_sent=notification_sent,
            message="Assessment completed successfully",
            assessment=None
        )

    async def send_to_mending(
        self,
        damage_record_id: int,
        added_by: User,
        priority: int = 3,
        repair_type: Optional[str] = None,
        repair_instructions: Optional[str] = None,
        materials_needed: Optional[str] = None,
        estimated_time_hours: Optional[Decimal] = None,
        estimated_cost: Optional[Decimal] = None,
        assigned_to_id: Optional[int] = None,
    ) -> DamagedItemWorkflowResult:
        result = await self.db.execute(
            select(DamagedItemRecord)
            .options(
                selectinload(DamagedItemRecord.item_copy),
                selectinload(DamagedItemRecord.catalog_item)
            )
            .where(DamagedItemRecord.id == damage_record_id)
            .with_for_update()
        )
        damage_record = result.scalar_one_or_none()

        if not damage_record:
            return DamagedItemWorkflowResult(
                success=False,
                damaged_item_record=None,
                fine=None,
                mending_entry=None,
                notification_sent=False,
                message="Damage record not found",
                assessment=None
            )

        if damage_record.status not in [DamagedItemStatus.REPAIRABLE, DamagedItemStatus.ASSESSMENT_PENDING]:
            return DamagedItemWorkflowResult(
                success=False,
                damaged_item_record=damage_record,
                fine=None,
                mending_entry=None,
                notification_sent=False,
                message="Item is not in a repairable status",
                assessment=None
            )

        now = datetime.now(timezone.utc)

        # Calculate queue position
        count_result = await self.db.execute(
            select(func.count()).select_from(MendingQueue).where(
                MendingQueue.is_completed == False
            )
        )
        current_count = count_result.scalar() or 0

        # Create mending queue entry
        mending_entry = MendingQueue(
            damaged_item_record_id=damage_record.id,
            item_copy_id=damage_record.item_copy_id,
            priority=priority,
            queue_position=current_count + 1,
            repair_type=repair_type,
            repair_instructions=repair_instructions,
            materials_needed=materials_needed,
            estimated_time_hours=estimated_time_hours,
            estimated_cost=estimated_cost or damage_record.estimated_repair_cost,
            added_by_id=added_by.id,
            assigned_to_id=assigned_to_id,
        )
        self.db.add(mending_entry)

        # Update damage record and item status
        damage_record.status = DamagedItemStatus.IN_MENDING
        damage_record.sent_to_mending_at = now
        damage_record.repair_priority = priority

        if damage_record.catalog_item:
            damage_record.catalog_item.status = ItemStatus.in_mending

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to send item to mending")
            raise

        return DamagedItemWorkflowResult(
            success=True,
            damaged_item_record=damage_record,
            fine=None,
            mending_entry=mending_entry,
            notification_sent=False,
            message="Item added to mending queue",
            assessment=None
        )

    async def complete_repair(
        self,
        mending_entry_id: int,
        completed_by: User,
        actual_cost: Optional[Decimal] = None,
        completion_notes: Optional[str] = None,
        new_condition: ItemCondition = ItemCondition.GOOD,
    ) -> RepairResult:
        result = await self.db.execute(
            select(MendingQueue)
            .options(
                selectinload(MendingQueue.damaged_item_record).selectinload(DamagedItemRecord.item_copy),
                selectinload(MendingQueue.damaged_item_record).selectinload(DamagedItemRecord.catalog_item)
            )
            .where(MendingQueue.id == mending_entry_id)
            .with_for_update()
        )
        mending_entry = result.scalar_one_or_none()

        if not mending_entry:
            return RepairResult(
                success=False,
                damaged_item_record=None,
                item_restored=False,
                actual_cost=Decimal("0.00"),
                message="Mending entry not found"
            )

        if mending_entry.is_completed:
            return RepairResult(
                success=False,
                damaged_item_record=mending_entry.damaged_item_record,
                item_restored=False,
                actual_cost=Decimal("0.00"),
                message="Repair already completed"
            )

        now = datetime.now(timezone.utc)
        damage_record = mending_entry.damaged_item_record

        # Update mending entry
        mending_entry.is_completed = True
        mending_entry.completed_at = now
        mending_entry.completed_by_id = completed_by.id
        mending_entry.completion_notes = completion_notes
        mending_entry.actual_cost = actual_cost or mending_entry.estimated_cost

        # Update damage record
        damage_record.status = DamagedItemStatus.REPAIRED
        damage_record.repair_completed_at = now
        damage_record.repaired_by_id = completed_by.id
        damage_record.actual_repair_cost = mending_entry.actual_cost
        damage_record.repair_notes = completion_notes
        damage_record.resolved_at = now

        # Restore item to circulation
        item_restored = False
        if damage_record.item_copy:
            damage_record.item_copy.condition = new_condition
            item_restored = True

        if damage_record.catalog_item:
            damage_record.catalog_item.status = ItemStatus.available

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to complete repair")
            raise

        return RepairResult(
            success=True,
            damaged_item_record=damage_record,
            item_restored=item_restored,
            actual_cost=mending_entry.actual_cost or Decimal("0.00"),
            message="Repair completed successfully"
        )

    async def withdraw_damaged_item(
        self,
        damage_record_id: int,
        withdrawn_by: User,
        withdrawal_reason: Optional[str] = None,
        charge_patron: bool = False,
        charge_amount: Optional[Decimal] = None,
        send_notification: bool = True,
    ) -> DamagedItemWorkflowResult:
        result = await self.db.execute(
            select(DamagedItemRecord)
            .options(
                selectinload(DamagedItemRecord.item_copy),
                selectinload(DamagedItemRecord.catalog_item),
                selectinload(DamagedItemRecord.patron)
            )
            .where(DamagedItemRecord.id == damage_record_id)
            .with_for_update()
        )
        damage_record = result.scalar_one_or_none()

        if not damage_record:
            return DamagedItemWorkflowResult(
                success=False,
                damaged_item_record=None,
                fine=None,
                mending_entry=None,
                notification_sent=False,
                message="Damage record not found",
                assessment=None
            )

        now = datetime.now(timezone.utc)
        fine = None
        notification_sent = False

        # Charge patron if requested
        if charge_patron and damage_record.patron_id:
            amount = charge_amount or damage_record.replacement_cost or Decimal("0.00")
            if amount > 0:
                fine = Fine(
                    user_id=damage_record.patron_id,
                    checkout_id=damage_record.checkout_id,
                    fine_type=FineType.damaged_item,
                    status=FineStatus.unpaid,
                    amount=amount,
                    description=f"Damaged item replacement: {damage_record.catalog_item.title if damage_record.catalog_item else 'Unknown'}",
                    notes=f"Item withdrawn due to damage beyond repair. {withdrawal_reason or ''}",
                )
                self.db.add(fine)
                await self.db.flush()
                damage_record.fine_id = fine.id
                damage_record.charge_amount = amount

                # Audit log for damage fine creation
                if damage_record.patron:
                    await ops_audit.log_fine_assessed(
                        db=self.db, patron=damage_record.patron, fine=fine
                    )

        # Update damage record
        damage_record.status = DamagedItemStatus.WITHDRAWN
        damage_record.withdrawn_at = now
        damage_record.withdrawal_reason = withdrawal_reason
        damage_record.resolved_at = now

        # Update item
        if damage_record.item_copy:
            damage_record.item_copy.condition = ItemCondition.WITHDRAWN

        if damage_record.catalog_item:
            damage_record.catalog_item.status = ItemStatus.damaged_withdrawn

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to withdraw damaged item")
            raise

        # Send notification only after successful commit
        if fine and send_notification and damage_record.patron and damage_record.patron.email:
            workflow_settings = await self.get_settings()
            if workflow_settings.notify_patron_on_damaged_charge:
                notification_sent = await self._send_damage_charge_notification(
                    patron=damage_record.patron,
                    item=damage_record.catalog_item,
                    charge_amount=fine.amount,
                    damage_description=damage_record.damage_description,
                )

        return DamagedItemWorkflowResult(
            success=True,
            damaged_item_record=damage_record,
            fine=fine,
            mending_entry=None,
            notification_sent=notification_sent,
            message="Item withdrawn successfully",
            assessment=None
        )

    async def get_mending_queue(
        self,
        include_completed: bool = False,
        assigned_to_id: Optional[int] = None,
        priority: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[MendingQueue], int]:
        query = select(MendingQueue).options(
            selectinload(MendingQueue.damaged_item_record).selectinload(DamagedItemRecord.catalog_item),
            selectinload(MendingQueue.item_copy),
            selectinload(MendingQueue.assigned_to)
        )

        conditions = []
        if not include_completed:
            conditions.append(MendingQueue.is_completed == False)
        if assigned_to_id:
            conditions.append(MendingQueue.assigned_to_id == assigned_to_id)
        if priority:
            conditions.append(MendingQueue.priority == priority)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(MendingQueue)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Order by priority and position
        query = query.order_by(MendingQueue.priority, MendingQueue.queue_position)
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_damaged_items(
        self,
        status: Optional[DamagedItemStatus] = None,
        severity: Optional[DamageSeverity] = None,
        patron_id: Optional[int] = None,
        is_patron_responsible: Optional[bool] = None,
        days_ago: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DamagedItemRecord], int]:
        query = select(DamagedItemRecord).options(
            selectinload(DamagedItemRecord.patron),
            selectinload(DamagedItemRecord.catalog_item),
            selectinload(DamagedItemRecord.item_copy),
            selectinload(DamagedItemRecord.fine)
        )

        conditions = []
        if status:
            conditions.append(DamagedItemRecord.status == status)
        if severity:
            conditions.append(DamagedItemRecord.severity == severity)
        if patron_id:
            conditions.append(DamagedItemRecord.patron_id == patron_id)
        if is_patron_responsible is not None:
            conditions.append(DamagedItemRecord.is_patron_responsible == is_patron_responsible)
        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(DamagedItemRecord.reported_at >= cutoff)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(DamagedItemRecord)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(DamagedItemRecord.reported_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def _send_damage_charge_notification(
        self,
        patron: User,
        item: Optional[CatalogItem],
        charge_amount: Decimal,
        damage_description: str,
    ) -> bool:
        account_url = routes.url(settings.frontend_url, routes.account_fines)
        item_title = item.title if item else "Unknown item"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS['heading']};">Damage Charge Notice</h2>
            <p>Hi {patron.first_name},</p>
            <p>A damage charge has been applied to your account for the following item:</p>

            <div style="background-color: #FEF3E2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #E89B44;">
                <h3 style="color: {COLORS['heading']}; margin-top: 0;">{item_title}</h3>
                <p style="margin: 10px 0;"><strong>Description of Damage:</strong></p>
                <p style="color: {COLORS['body']}; margin: 5px 0;">{damage_description}</p>

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: {COLORS['heading']};">Damage Charge:</td>
                        <td style="padding: 8px 0; color: #C0392B; font-weight: bold;">${charge_amount:.2f}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS['body']};">
                If you have questions about this charge or believe it was applied in error,
                please contact the library to discuss.
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{account_url}"
                   style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Account
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
            <p style="color: {COLORS['text_light']}; font-size: 12px;">
                {settings.app_name}<br>
                Thank you for helping us maintain our collection.
            </p>
        </div>
        """

        return await send_email(patron.email, f"Damage Charge Notice: {item_title}", html)
