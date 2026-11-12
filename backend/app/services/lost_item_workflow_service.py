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
from ..models.inventory import ItemCopy, ItemCondition
from ..models.lost_damaged import LostItemRecord, LostItemStatus, LostItemType, LostDamagedSettings
from ..models.user import User
from . import operations_audit_service as ops_audit

logger = get_logger(__name__)

settings = get_settings()


@dataclass
class ReplacementCostBreakdown:
    item_price: Decimal
    processing_fee: Decimal
    total: Decimal
    source: str  # Where the price came from (item, catalog, default)


@dataclass
class LostItemWorkflowResult:
    success: bool
    lost_item_record: Optional[LostItemRecord]
    fine: Optional[Fine]
    notification_sent: bool
    message: str
    replacement_cost: Optional[ReplacementCostBreakdown]


@dataclass
class FoundItemResult:
    success: bool
    lost_item_record: Optional[LostItemRecord]
    credit_amount: Decimal
    credit_fine: Optional[Fine]
    item_restored: bool
    notification_sent: bool
    message: str


class LostItemWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._settings_cache = None

    async def get_settings(
        self,
        branch_id: Optional[int] = None,
        branch_location: Optional[str] = None,
    ) -> LostDamagedSettings:
        from ..core.branch_resolver import label_to_branch_id

        if branch_id is None:
            branch_id = label_to_branch_id(branch_location)

        # Try branch-specific settings first
        if branch_id is not None:
            result = await self.db.execute(
                select(LostDamagedSettings).where(
                    LostDamagedSettings.branch_id == branch_id,
                    LostDamagedSettings.is_active == True,
                )
            )
            branch_settings = result.scalar_one_or_none()
            if branch_settings:
                return branch_settings

        # Fall back to system-wide settings
        result = await self.db.execute(
            select(LostDamagedSettings).where(
                LostDamagedSettings.branch_id == None,
                LostDamagedSettings.branch_location == None,
                LostDamagedSettings.is_active == True,
            )
        )
        system_settings = result.scalar_one_or_none()

        if system_settings:
            return system_settings

        # Return default settings from config.
        default_settings = LostDamagedSettings(
            lost_item_processing_fee=Decimal(str(settings.lost_item_processing_fee)),
            default_replacement_cost=Decimal(str(settings.lost_item_default_replacement_cost)),
            overdue_to_lost_days=settings.lost_item_threshold_days,
            auto_convert_overdue_enabled=settings.auto_convert_overdue_to_lost,
            found_item_credit_percentage=Decimal(str(settings.found_item_credit_percentage)),
            found_item_grace_period_days=settings.found_item_grace_period_days,
        )
        # This row is never INSERTed, so SQLAlchemy has not applied any column
        # defaults to it -- every field not set above would read back as None,
        # including the notify_* flags (real default True), silently disabling
        # patron notifications. Apply the model's own defaults, as an INSERT would.
        for column in LostDamagedSettings.__table__.columns:
            if getattr(default_settings, column.name, None) is not None:
                continue
            default = column.default
            if default is not None and default.is_scalar:
                setattr(default_settings, column.name, default.arg)
        return default_settings

    def calculate_replacement_cost(
        self,
        item_copy: Optional[ItemCopy],
        catalog_item: Optional[CatalogItem],
        processing_fee: Decimal,
        default_cost: Decimal,
    ) -> ReplacementCostBreakdown:
        item_price = Decimal("0.00")
        source = "default"

        # Try ItemCopy replacement cost first
        if item_copy and item_copy.replacement_cost:
            item_price = Decimal(str(item_copy.replacement_cost))
            source = "item_copy"
        # Try CatalogItem price (from purchase order acquisition cost)
        elif (
            item_copy and item_copy.purchase_order_item and item_copy.purchase_order_item.unit_price
        ):
            item_price = Decimal(str(item_copy.purchase_order_item.unit_price))
            source = "catalog_item"
        # Fall back to default
        else:
            item_price = default_cost
            source = "default"

        total = item_price + processing_fee

        return ReplacementCostBreakdown(
            item_price=item_price, processing_fee=processing_fee, total=total, source=source
        )

    async def mark_item_lost(
        self,
        checkout_id: int,
        lost_type: LostItemType,
        reported_by: Optional[User],
        report_notes: Optional[str] = None,
        custom_replacement_cost: Optional[Decimal] = None,
        send_notification: bool = True,
        commit: bool = True,
    ) -> LostItemWorkflowResult:
        # Get checkout with related data
        result = await self.db.execute(
            select(Checkout)
            .options(
                selectinload(Checkout.user),
                selectinload(Checkout.item),
                selectinload(Checkout.item_copy).selectinload(ItemCopy.purchase_order_item),
            )
            .where(Checkout.id == checkout_id)
            .with_for_update()
        )
        checkout = result.scalar_one_or_none()

        if not checkout:
            return LostItemWorkflowResult(
                success=False,
                lost_item_record=None,
                fine=None,
                notification_sent=False,
                message="Checkout not found",
                replacement_cost=None,
            )

        # Check if already marked lost
        if checkout.status in [
            CheckoutStatus.lost,
            CheckoutStatus.lost_by_patron,
            CheckoutStatus.lost_in_transit,
            CheckoutStatus.claims_returned,
        ]:
            return LostItemWorkflowResult(
                success=False,
                lost_item_record=None,
                fine=None,
                notification_sent=False,
                message="Item is already marked as lost",
                replacement_cost=None,
            )

        # Get settings
        workflow_settings = await self.get_settings(
            branch_location=checkout.item_copy.location if checkout.item_copy else None
        )

        # Calculate replacement cost
        if custom_replacement_cost:
            cost_breakdown = ReplacementCostBreakdown(
                item_price=custom_replacement_cost,
                processing_fee=Decimal("0.00"),
                total=custom_replacement_cost,
                source="custom",
            )
        else:
            cost_breakdown = self.calculate_replacement_cost(
                item_copy=checkout.item_copy,
                catalog_item=checkout.item,
                processing_fee=workflow_settings.lost_item_processing_fee,
                default_cost=workflow_settings.default_replacement_cost,
            )

        # Calculate days overdue
        now = datetime.now(timezone.utc)
        days_overdue = 0
        if checkout.due_date:
            if checkout.due_date.tzinfo:
                now = datetime.now(checkout.due_date.tzinfo)
            days_overdue = max(0, (now - checkout.due_date).days)

        # Determine checkout status based on lost type
        checkout_status_map = {
            LostItemType.LOST_BY_PATRON: CheckoutStatus.lost_by_patron,
            LostItemType.LOST_IN_TRANSIT: CheckoutStatus.lost_in_transit,
            LostItemType.CLAIMS_RETURNED: CheckoutStatus.claims_returned,
            LostItemType.OVERDUE_CONVERSION: CheckoutStatus.lost,
            LostItemType.MISSING_INVENTORY: CheckoutStatus.lost,
        }

        # Determine item status based on lost type
        item_status_map = {
            LostItemType.LOST_BY_PATRON: ItemStatus.lost_by_patron,
            LostItemType.LOST_IN_TRANSIT: ItemStatus.lost_in_transit,
            LostItemType.CLAIMS_RETURNED: ItemStatus.claims_returned,
            LostItemType.OVERDUE_CONVERSION: ItemStatus.lost,
            LostItemType.MISSING_INVENTORY: ItemStatus.lost,
        }

        # Create lost item record
        lost_record = LostItemRecord(
            item_copy_id=checkout.item_copy_id,
            checkout_id=checkout.id,
            catalog_item_id=checkout.item_id,
            patron_id=checkout.user_id,
            status=LostItemStatus.REPORTED,
            lost_type=lost_type,
            item_price=cost_breakdown.item_price,
            processing_fee=cost_breakdown.processing_fee,
            replacement_cost=cost_breakdown.total,
            days_overdue_at_loss=days_overdue,
            report_notes=report_notes,
            # None for automated conversions -- no human reported it. The column
            # is nullable; the old code passed an in-memory User(id=0) that was
            # never inserted, tripping the users FK on every scheduled run.
            reported_by_id=reported_by.id if reported_by else None,
            reported_at=now,
            last_known_location=checkout.item_copy.location if checkout.item_copy else None,
        )
        self.db.add(lost_record)
        await self.db.flush()

        # Create fine for patron (unless claims returned, which is disputed first)
        fine = None
        if lost_type != LostItemType.CLAIMS_RETURNED:
            fine = Fine(
                user_id=checkout.user_id,
                checkout_id=checkout.id,
                fine_type=FineType.lost_item,
                status=FineStatus.unpaid,
                amount=cost_breakdown.total,
                description=f"Lost item replacement: {checkout.item.title if checkout.item else 'Unknown item'}",
                notes=f"Item: {cost_breakdown.item_price}, Processing fee: {cost_breakdown.processing_fee}",
            )
            self.db.add(fine)
            await self.db.flush()

            # Update lost record with fine
            lost_record.fine_id = fine.id
            lost_record.status = LostItemStatus.CHARGED
            lost_record.charged_at = now
        else:
            # Claims returned goes to dispute pending
            lost_record.status = LostItemStatus.DISPUTE_PENDING

        # Update checkout status
        checkout.status = checkout_status_map.get(lost_type, CheckoutStatus.lost)

        # Update item status
        if checkout.item:
            checkout.item.status = item_status_map.get(lost_type, ItemStatus.lost)

        # Update item copy condition
        if checkout.item_copy:
            checkout.item_copy.condition = ItemCondition.WITHDRAWN

        await self.db.flush()

        # Audit log for fine creation
        if fine:
            await ops_audit.log_fine_assessed(
                db=self.db, patron=checkout.user, fine=fine, checkout=checkout
            )

        if commit:
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                logger.exception("Failed to mark item as lost")
                raise
        else:
            await self.db.flush()

        # Send notification only after successful commit
        notification_sent = False
        if commit and send_notification and checkout.user and checkout.user.email:
            if workflow_settings.notify_patron_on_lost:
                notification_sent = await self._send_lost_item_notification(
                    patron=checkout.user,
                    item=checkout.item,
                    cost_breakdown=cost_breakdown,
                    days_overdue=days_overdue,
                    lost_type=lost_type,
                )

        # Re-fetch lost record with relationships to avoid MissingGreenlet
        # on lazy-load when serializing the response
        if commit:
            refetch_result = await self.db.execute(
                select(LostItemRecord)
                .options(
                    selectinload(LostItemRecord.patron),
                    selectinload(LostItemRecord.catalog_item),
                    selectinload(LostItemRecord.item_copy),
                    selectinload(LostItemRecord.fine),
                )
                .where(LostItemRecord.id == lost_record.id)
            )
            lost_record = refetch_result.scalar_one_or_none() or lost_record

        return LostItemWorkflowResult(
            success=True,
            lost_item_record=lost_record,
            fine=fine,
            notification_sent=notification_sent,
            message="Item marked as lost successfully",
            replacement_cost=cost_breakdown,
        )

    async def process_found_item(
        self,
        lost_record_id: int,
        found_by: User,
        found_condition: ItemCondition = ItemCondition.GOOD,
        resolution_notes: Optional[str] = None,
        send_notification: bool = True,
    ) -> FoundItemResult:
        # Get lost item record with related data
        result = await self.db.execute(
            select(LostItemRecord)
            .options(
                selectinload(LostItemRecord.item_copy),
                selectinload(LostItemRecord.catalog_item),
                selectinload(LostItemRecord.patron),
                selectinload(LostItemRecord.checkout),
                selectinload(LostItemRecord.fine),
            )
            .where(LostItemRecord.id == lost_record_id)
            .with_for_update()
        )
        lost_record = result.scalar_one_or_none()

        if not lost_record:
            return FoundItemResult(
                success=False,
                lost_item_record=None,
                credit_amount=Decimal("0.00"),
                credit_fine=None,
                item_restored=False,
                notification_sent=False,
                message="Lost item record not found",
            )

        # Check if already resolved
        if lost_record.status in [LostItemStatus.FOUND, LostItemStatus.WRITTEN_OFF]:
            return FoundItemResult(
                success=False,
                lost_item_record=lost_record,
                credit_amount=Decimal("0.00"),
                credit_fine=None,
                item_restored=False,
                notification_sent=False,
                message="This lost item has already been resolved",
            )

        # Get settings
        workflow_settings = await self.get_settings(
            branch_location=lost_record.item_copy.location if lost_record.item_copy else None
        )

        now = datetime.now(timezone.utc)

        # Check if within grace period for credit
        credit_amount = Decimal("0.00")
        credit_fine = None
        days_since_lost = (now - lost_record.charged_at).days if lost_record.charged_at else 0

        if days_since_lost <= workflow_settings.found_item_grace_period_days:
            # Calculate credit amount
            if lost_record.replacement_cost:
                if workflow_settings.found_item_full_credit:
                    credit_amount = lost_record.replacement_cost
                else:
                    credit_percentage = workflow_settings.found_item_credit_percentage / Decimal(
                        "100"
                    )
                    credit_amount = lost_record.replacement_cost * credit_percentage

                # Handle the original fine
                if lost_record.fine:
                    if lost_record.fine.status == FineStatus.unpaid:
                        # Waive the fine
                        lost_record.fine.status = FineStatus.waived
                        lost_record.fine.waived_at = now
                        lost_record.fine.waived_by_id = found_by.id
                        lost_record.fine.notes = (
                            lost_record.fine.notes or ""
                        ) + f"\nWaived: Item found and returned on {now.strftime('%Y-%m-%d')}"
                    elif lost_record.fine.status in [FineStatus.paid, FineStatus.partial]:
                        # Create a credit fine (negative amount adjustment)
                        amount_to_credit = min(credit_amount, lost_record.fine.amount_paid)
                        if amount_to_credit > 0:
                            credit_fine = Fine(
                                user_id=lost_record.patron_id,
                                checkout_id=lost_record.checkout_id,
                                fine_type=FineType.other,
                                status=FineStatus.paid,  # Credit is "paid" immediately
                                amount=-amount_to_credit,  # Negative amount = credit
                                amount_paid=Decimal("0.00"),
                                description=f"Credit for found item: {lost_record.catalog_item.title if lost_record.catalog_item else 'Unknown'}",
                                notes="Item found after being marked lost. Credit issued for returned item.",
                            )
                            self.db.add(credit_fine)
                            await self.db.flush()
                            lost_record.credit_fine_id = credit_fine.id
                            credit_amount = amount_to_credit

        # Update lost record status
        lost_record.status = LostItemStatus.FOUND
        lost_record.found_at = now
        lost_record.resolved_by_id = found_by.id
        lost_record.resolution_notes = resolution_notes
        lost_record.credit_amount = credit_amount

        # Restore item to circulation
        item_restored = False
        if lost_record.item_copy and found_condition != ItemCondition.WITHDRAWN:
            lost_record.item_copy.condition = found_condition
            item_restored = True

        if lost_record.catalog_item:
            if found_condition == ItemCondition.WITHDRAWN:
                lost_record.catalog_item.status = ItemStatus.damaged_withdrawn
            elif found_condition in [ItemCondition.DAMAGED, ItemCondition.POOR]:
                lost_record.catalog_item.status = ItemStatus.damaged_repairable
            else:
                lost_record.catalog_item.status = ItemStatus.available

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to process found item")
            raise

        # Send notification only after successful commit
        notification_sent = False
        if send_notification and lost_record.patron and lost_record.patron.email:
            if workflow_settings.notify_patron_on_found:
                notification_sent = await self._send_found_item_notification(
                    patron=lost_record.patron,
                    item=lost_record.catalog_item,
                    credit_amount=credit_amount,
                )

        return FoundItemResult(
            success=True,
            lost_item_record=lost_record,
            credit_amount=credit_amount,
            credit_fine=credit_fine,
            item_restored=item_restored,
            notification_sent=notification_sent,
            message="Found item processed successfully",
        )

    async def write_off_lost_item(
        self,
        lost_record_id: int,
        written_off_by: User,
        notes: Optional[str] = None,
    ) -> LostItemWorkflowResult:
        result = await self.db.execute(
            select(LostItemRecord)
            .options(selectinload(LostItemRecord.item_copy))
            .where(LostItemRecord.id == lost_record_id)
            .with_for_update()
        )
        lost_record = result.scalar_one_or_none()

        if not lost_record:
            return LostItemWorkflowResult(
                success=False,
                lost_item_record=None,
                fine=None,
                notification_sent=False,
                message="Lost item record not found",
                replacement_cost=None,
            )

        now = datetime.now(timezone.utc)
        lost_record.status = LostItemStatus.WRITTEN_OFF
        lost_record.written_off_at = now
        lost_record.resolved_by_id = written_off_by.id
        lost_record.resolution_notes = notes

        # Mark item copy as withdrawn
        if lost_record.item_copy:
            lost_record.item_copy.condition = ItemCondition.WITHDRAWN

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to write off lost item")
            raise

        return LostItemWorkflowResult(
            success=True,
            lost_item_record=lost_record,
            fine=None,
            notification_sent=False,
            message="Lost item written off successfully",
            replacement_cost=None,
        )

    async def get_lost_items(
        self,
        status: Optional[LostItemStatus] = None,
        lost_type: Optional[LostItemType] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LostItemRecord], int]:
        query = select(LostItemRecord).options(
            selectinload(LostItemRecord.patron),
            selectinload(LostItemRecord.catalog_item),
            selectinload(LostItemRecord.item_copy),
            selectinload(LostItemRecord.fine),
        )

        conditions = []
        if status:
            conditions.append(LostItemRecord.status == status)
        if lost_type:
            conditions.append(LostItemRecord.lost_type == lost_type)
        if patron_id:
            conditions.append(LostItemRecord.patron_id == patron_id)
        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(LostItemRecord.reported_at >= cutoff)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(LostItemRecord)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get items
        query = query.order_by(LostItemRecord.reported_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def auto_convert_overdue_items(
        self,
        threshold_days: Optional[int] = None,
        dry_run: bool = False,
    ) -> List[LostItemWorkflowResult]:
        workflow_settings = await self.get_settings()

        if threshold_days is None:
            threshold_days = workflow_settings.overdue_to_lost_days

        if not workflow_settings.auto_convert_overdue_enabled and not dry_run:
            return []

        threshold_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)

        # Find eligible checkouts
        result = await self.db.execute(
            select(Checkout)
            .options(
                selectinload(Checkout.user),
                selectinload(Checkout.item),
                selectinload(Checkout.item_copy).selectinload(ItemCopy.purchase_order_item),
            )
            .where(
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
                Checkout.due_date < threshold_date,
            )
            .with_for_update(skip_locked=True)
        )
        overdue_checkouts = result.scalars().all()

        results = []

        for checkout in overdue_checkouts:
            if dry_run:
                # Return preview result
                workflow_settings = await self.get_settings(
                    branch_location=checkout.item_copy.location if checkout.item_copy else None
                )
                cost = self.calculate_replacement_cost(
                    checkout.item_copy,
                    checkout.item,
                    workflow_settings.lost_item_processing_fee,
                    workflow_settings.default_replacement_cost,
                )
                results.append(
                    LostItemWorkflowResult(
                        success=True,
                        lost_item_record=None,
                        fine=None,
                        notification_sent=False,
                        message=f"Would mark checkout {checkout.id} as lost",
                        replacement_cost=cost,
                    )
                )
            else:
                result = await self.mark_item_lost(
                    checkout_id=checkout.id,
                    lost_type=LostItemType.OVERDUE_CONVERSION,
                    reported_by=None,
                    report_notes=f"Auto-converted from overdue after {threshold_days} days",
                    send_notification=False,
                    commit=False,
                )
                results.append(result)

        # Single commit after processing all items to avoid releasing locks mid-iteration
        if not dry_run and results:
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                logger.exception("Failed to auto-convert overdue items to lost")
                raise

            # Send notifications after successful commit
            for checkout, wf_result in zip(overdue_checkouts, results):
                if wf_result.success and checkout.user and checkout.user.email:
                    wf_settings = await self.get_settings(
                        branch_location=checkout.item_copy.location if checkout.item_copy else None
                    )
                    if wf_settings.notify_patron_on_lost:
                        cost = wf_result.replacement_cost
                        if cost:
                            days_overdue = (
                                max(0, (datetime.now(timezone.utc) - checkout.due_date).days)
                                if checkout.due_date
                                else 0
                            )
                            await self._send_lost_item_notification(
                                patron=checkout.user,
                                item=checkout.item,
                                cost_breakdown=cost,
                                days_overdue=days_overdue,
                                lost_type=LostItemType.OVERDUE_CONVERSION,
                            )

        return results

    async def _send_lost_item_notification(
        self,
        patron: User,
        item: Optional[CatalogItem],
        cost_breakdown: ReplacementCostBreakdown,
        days_overdue: int,
        lost_type: LostItemType,
    ) -> bool:
        account_url = routes.url(settings.frontend_url, routes.account_fines)
        item_title = item.title if item else "Unknown item"
        item_author = item.author if item else None
        author_line = (
            f'<p style="color: {COLORS["text_light"]}; margin: 5px 0;">by {item_author}</p>'
            if item_author
            else ""
        )

        type_descriptions = {
            LostItemType.LOST_BY_PATRON: "marked as lost",
            LostItemType.LOST_IN_TRANSIT: "reported lost during transit",
            LostItemType.OVERDUE_CONVERSION: f"automatically marked as lost after {days_overdue} days overdue",
            LostItemType.CLAIMS_RETURNED: "recorded as claims returned",
            LostItemType.MISSING_INVENTORY: "found missing during inventory",
        }
        type_desc = type_descriptions.get(lost_type, "marked as lost")

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS["heading"]};">Item Marked as Lost</h2>
            <p>Hi {patron.first_name},</p>
            <p>The following item has been {type_desc}. A replacement fee has been added to your account.</p>

            <div style="background-color: #FEF3E2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #E89B44;">
                <h3 style="color: {COLORS["heading"]}; margin-top: 0;">{item_title}</h3>
                {author_line}

                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: {COLORS["heading"]};">Item Value:</td>
                        <td style="padding: 8px 0;">${cost_breakdown.item_price:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: {COLORS["heading"]};">Processing Fee:</td>
                        <td style="padding: 8px 0;">${cost_breakdown.processing_fee:.2f}</td>
                    </tr>
                    <tr style="border-top: 1px solid {COLORS["divider"]};">
                        <td style="padding: 8px 0; font-weight: bold; color: {COLORS["heading"]};">Total Due:</td>
                        <td style="padding: 8px 0; color: #C0392B; font-weight: bold;">${cost_breakdown.total:.2f}</td>
                    </tr>
                </table>
            </div>

            <p style="color: {COLORS["body"]};">
                <strong>Found the item?</strong> If you locate this item and return it in good condition,
                we may be able to waive or reduce the replacement fee. Please bring it to the library
                as soon as possible.
            </p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{account_url}"
                   style="background-color: {COLORS["button"]}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Account
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS["divider"]}; margin: 30px 0;">
            <p style="color: {COLORS["text_light"]}; font-size: 12px;">
                {settings.app_name}<br>
                If you believe this is an error or have questions, please contact the library.
            </p>
        </div>
        """

        return await send_email(patron.email, f"Item Marked as Lost: {item_title}", html)

    async def _send_found_item_notification(
        self,
        patron: User,
        item: Optional[CatalogItem],
        credit_amount: Decimal,
    ) -> bool:
        account_url = routes.url(settings.frontend_url, routes.account_fines)
        item_title = item.title if item else "Unknown item"

        credit_section = ""
        if credit_amount > 0:
            credit_section = f"""
            <div style="background-color: #D4EDDA; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28A745;">
                <h3 style="color: #155724; margin-top: 0;">Credit Applied</h3>
                <p style="font-size: 24px; font-weight: bold; color: #155724; margin: 10px 0;">
                    ${credit_amount:.2f}
                </p>
                <p style="color: #155724;">
                    This credit has been applied to your account.
                </p>
            </div>
            """

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS["heading"]};">Good News - Item Found!</h2>
            <p>Hi {patron.first_name},</p>
            <p>Great news! The following item that was previously marked as lost has been found:</p>

            <div style="background-color: #E8F4FD; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3498DB;">
                <h3 style="color: {COLORS["heading"]}; margin-top: 0;">{item_title}</h3>
            </div>

            {credit_section}

            <p style="text-align: center; margin: 30px 0;">
                <a href="{account_url}"
                   style="background-color: {COLORS["button"]}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View My Account
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS["divider"]}; margin: 30px 0;">
            <p style="color: {COLORS["text_light"]}; font-size: 12px;">
                {settings.app_name}<br>
                Thank you for your patience while we located this item.
            </p>
        </div>
        """

        return await send_email(patron.email, f"Good News: Lost Item Found - {item_title}", html)
