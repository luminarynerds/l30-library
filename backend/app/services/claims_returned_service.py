# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.core.logging import get_logger
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.email import send_email, COLORS
from ..core.frontend_routes import routes
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus
from ..models.fine import Fine, FineStatus, FineType
from ..models.inventory import ItemCopy, ItemCondition
from ..models.lost_damaged import (
    ClaimsReturnedDispute, ClaimDisputeStatus,
    LostItemRecord, LostItemStatus, LostItemType,
    LostDamagedSettings
)
from ..models.notification import Notification, NotificationStatus, NotificationType as InternalNotificationType
from ..models.user import User, UserRole
from ..services.unified_notification_service import UnifiedNotificationService, NotificationType

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class ClaimsReturnedResult:
    success: bool
    dispute: Optional[ClaimsReturnedDispute]
    message: str
    notification_sent: bool


@dataclass
class ClaimResolutionResult:
    success: bool
    dispute: Optional[ClaimsReturnedDispute]
    credit_amount: Decimal
    credit_fine: Optional[Fine]
    item_found: bool
    notification_sent: bool
    message: str


@dataclass
class PatronClaimsHistory:
    patron_id: int
    total_claims: int
    claims_this_year: int
    approved_claims: int
    denied_claims: int
    pending_claims: int
    items_later_found: int
    is_at_risk: bool  # True if approaching max claims limit
    max_claims_allowed: int


class ClaimsReturnedService:

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

        return LostDamagedSettings(
            claims_returned_review_days=settings.claims_returned_review_days,
            max_claims_per_patron_year=settings.max_claims_per_patron_year,
        )

    async def get_patron_claims_history(self, patron_id: int) -> PatronClaimsHistory:
        current_year = datetime.now(timezone.utc).year

        # Get all claims for this patron
        all_claims_result = await self.db.execute(
            select(ClaimsReturnedDispute).where(
                ClaimsReturnedDispute.patron_id == patron_id
            )
        )
        all_claims = all_claims_result.scalars().all()

        # Count claims this year
        claims_this_year = sum(
            1 for c in all_claims
            if c.filed_at and c.filed_at.year == current_year
        )

        # Count by status
        approved = sum(1 for c in all_claims if c.status == ClaimDisputeStatus.APPROVED)
        denied = sum(1 for c in all_claims if c.status == ClaimDisputeStatus.DENIED)
        pending = sum(1 for c in all_claims if c.status in [
            ClaimDisputeStatus.PENDING,
            ClaimDisputeStatus.UNDER_REVIEW,
            ClaimDisputeStatus.SEARCH_IN_PROGRESS
        ])
        items_found = sum(1 for c in all_claims if c.status == ClaimDisputeStatus.ITEM_FOUND)

        workflow_settings = await self.get_settings()
        max_claims = workflow_settings.max_claims_per_patron_year

        return PatronClaimsHistory(
            patron_id=patron_id,
            total_claims=len(all_claims),
            claims_this_year=claims_this_year,
            approved_claims=approved,
            denied_claims=denied,
            pending_claims=pending,
            items_later_found=items_found,
            is_at_risk=claims_this_year >= max_claims - 1,
            max_claims_allowed=max_claims
        )

    async def file_claim(
        self,
        checkout_id: int,
        patron_statement: str,
        claimed_return_date: Optional[date] = None,
        claimed_return_location: Optional[str] = None,
        filed_by: Optional[User] = None,
        send_notification: bool = True,
    ) -> ClaimsReturnedResult:
        # Get checkout with related data
        result = await self.db.execute(
            select(Checkout)
            .options(
                selectinload(Checkout.user),
                selectinload(Checkout.item),
                selectinload(Checkout.item_copy)
            )
            .where(Checkout.id == checkout_id)
            .with_for_update()
        )
        checkout = result.scalar_one_or_none()

        if not checkout:
            return ClaimsReturnedResult(
                success=False,
                dispute=None,
                message="Checkout not found",
                notification_sent=False
            )

        # Check if checkout is eligible for claims returned
        if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue,
                                   CheckoutStatus.lost, CheckoutStatus.lost_by_patron]:
            return ClaimsReturnedResult(
                success=False,
                dispute=None,
                message="Checkout is not eligible for claims returned dispute",
                notification_sent=False
            )

        patron = checkout.user
        workflow_settings = await self.get_settings(
            branch_location=checkout.item_copy.location if checkout.item_copy else None
        )

        # Check patron's claims history
        claims_history = await self.get_patron_claims_history(patron.id)

        # Auto-deny if patron has exceeded yearly limit
        if claims_history.claims_this_year >= workflow_settings.max_claims_per_patron_year:
            return ClaimsReturnedResult(
                success=False,
                dispute=None,
                message=f"Patron has reached maximum claims limit ({workflow_settings.max_claims_per_patron_year} per year)",
                notification_sent=False
            )

        now = datetime.now(timezone.utc)

        # Check if there's already a lost item record
        existing_lost_result = await self.db.execute(
            select(LostItemRecord).where(
                LostItemRecord.checkout_id == checkout_id,
                LostItemRecord.status != LostItemStatus.FOUND
            )
        )
        lost_record = existing_lost_result.scalar_one_or_none()

        # If no lost record exists, create one
        if not lost_record:
            lost_record = LostItemRecord(
                item_copy_id=checkout.item_copy_id,
                checkout_id=checkout.id,
                catalog_item_id=checkout.item_id,
                patron_id=patron.id,
                status=LostItemStatus.DISPUTE_PENDING,
                lost_type=LostItemType.CLAIMS_RETURNED,
                reported_by_id=filed_by.id if filed_by else patron.id,
                reported_at=now,
                report_notes=f"Claims returned filed: {patron_statement}",
                last_known_location=checkout.item_copy.location if checkout.item_copy else None,
            )
            self.db.add(lost_record)
            await self.db.flush()
        else:
            # Update existing record to claims returned status
            lost_record.status = LostItemStatus.DISPUTE_PENDING
            lost_record.lost_type = LostItemType.CLAIMS_RETURNED

        # Create claims returned dispute
        dispute = ClaimsReturnedDispute(
            lost_item_record_id=lost_record.id,
            item_copy_id=checkout.item_copy_id,
            checkout_id=checkout.id,
            patron_id=patron.id,
            status=ClaimDisputeStatus.PENDING,
            patron_statement=patron_statement,
            claimed_return_date=claimed_return_date,
            claimed_return_location=claimed_return_location,
            patron_previous_claims_count=claims_history.total_claims,
            filed_by_id=filed_by.id if filed_by else patron.id,
            filed_at=now,
        )
        self.db.add(dispute)

        # Update checkout status
        checkout.status = CheckoutStatus.claims_returned

        # Update item status
        if checkout.item:
            checkout.item.status = ItemStatus.claims_returned

        await self.db.flush()

        # Send notification to staff if configured
        notification_sent = False
        if send_notification and workflow_settings.notify_staff_on_claims:
            try:
                # Get staff users with appropriate permissions to handle disputes
                staff_result = await self.db.execute(
                    select(User).where(
                        User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]),
                        User.is_active == True
                    )
                )
                staff_users = staff_result.scalars().all()

                # Prepare notification context data
                item_title = checkout.item.title if checkout.item else "Unknown Item"
                patron_name = patron.full_name
                dispute_url = routes.url(settings.frontend_url, routes.staff_disputes_claims_returned, id=dispute.id)

                context_data = {
                    "dispute_id": dispute.id,
                    "patron_id": patron.id,
                    "patron_name": patron_name,
                    "item_title": item_title,
                    "checkout_id": checkout.id,
                    "dispute_url": dispute_url,
                    "patron_statement": patron_statement,
                }

                # Initialize notification service
                notification_service = UnifiedNotificationService()

                # Send email and in-app notifications to each staff member
                sent_count = 0
                for staff_user in staff_users:
                    delivered = False
                    if staff_user.email:
                        try:
                            await notification_service.send_templated(
                                notification_type=NotificationType.CLAIMS_RETURNED,
                                recipient_email=staff_user.email,
                                context_data=context_data,
                                user_id=staff_user.id,
                                db=self.db,
                            )
                            delivered = True
                        except (ValueError, TypeError, KeyError, AttributeError) as e:
                            logger.error(
                                f"Failed to send claims-returned notification to {staff_user.email}: {e}",
                                extra={
                                    "dispute_id": dispute.id,
                                    "patron_id": patron.id,
                                    "staff_user_id": staff_user.id,
                                },
                                exc_info=True
                            )
                            # Continue sending to other staff members

                    try:
                        self.db.add(
                            Notification(
                                user_id=staff_user.id,
                                notification_type=InternalNotificationType.EVENT_UPDATED,
                                status=NotificationStatus.SENT,
                                subject="Claims-returned dispute requires review",
                                message=(
                                    f"A claims-returned dispute was filed by {patron_name} "
                                    f"for '{item_title}'."
                                ),
                                context_data=context_data,
                                sent_at=datetime.now(timezone.utc),
                            )
                        )
                        delivered = True
                    except (ValueError, TypeError, KeyError, AttributeError) as e:
                        logger.error(
                            f"Failed to create in-app claims-returned notification for user {staff_user.id}: {e}",
                            extra={"dispute_id": dispute.id, "staff_user_id": staff_user.id},
                            exc_info=True,
                        )

                    if delivered:
                        sent_count += 1

                # Mark as sent if at least one notification was successful
                if sent_count > 0:
                    notification_sent = True
                    logger.info(
                        f"Claims-returned notifications sent to {sent_count} staff members",
                        extra={"dispute_id": dispute.id, "patron_id": patron.id}
                    )
                else:
                    logger.warning(
                        "No claims-returned notifications were sent successfully",
                        extra={"dispute_id": dispute.id, "patron_id": patron.id}
                    )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(
                    f"Failed to send claims-returned staff notifications: {e}",
                    extra={"dispute_id": dispute.id, "patron_id": patron.id},
                    exc_info=True
                )
                # Don't fail the dispute filing if notification fails
                notification_sent = False

        await self.db.commit()

        # Re-fetch dispute with relationships to avoid MissingGreenlet
        # on lazy-load when serializing the response
        refetch_result = await self.db.execute(
            select(ClaimsReturnedDispute)
            .options(
                selectinload(ClaimsReturnedDispute.patron),
                selectinload(ClaimsReturnedDispute.item_copy).selectinload(ItemCopy.catalog_item),
                selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item),
                selectinload(ClaimsReturnedDispute.reviewed_by),
            )
            .where(ClaimsReturnedDispute.id == dispute.id)
        )
        dispute = refetch_result.scalar_one_or_none() or dispute

        return ClaimsReturnedResult(
            success=True,
            dispute=dispute,
            message="Claims returned dispute filed successfully",
            notification_sent=notification_sent
        )

    async def start_review(
        self,
        dispute_id: int,
        reviewed_by: User,
        initial_notes: Optional[str] = None,
    ) -> ClaimsReturnedResult:
        result = await self.db.execute(
            select(ClaimsReturnedDispute)
            .options(selectinload(ClaimsReturnedDispute.patron))
            .where(ClaimsReturnedDispute.id == dispute_id)
            .with_for_update()
        )
        dispute = result.scalar_one_or_none()

        if not dispute:
            return ClaimsReturnedResult(
                success=False,
                dispute=None,
                message="Dispute not found",
                notification_sent=False
            )

        if dispute.status != ClaimDisputeStatus.PENDING:
            return ClaimsReturnedResult(
                success=False,
                dispute=dispute,
                message="Dispute is not in pending status",
                notification_sent=False
            )

        now = datetime.now(timezone.utc)
        dispute.status = ClaimDisputeStatus.UNDER_REVIEW
        dispute.reviewed_by_id = reviewed_by.id
        dispute.reviewed_at = now
        dispute.investigation_notes = initial_notes or ""
        dispute.patron_checkout_history_reviewed = True

        await self.db.commit()

        return ClaimsReturnedResult(
            success=True,
            dispute=dispute,
            message="Review started",
            notification_sent=False
        )

    async def start_search(
        self,
        dispute_id: int,
        search_locations: List[str],
        search_notes: Optional[str] = None,
    ) -> ClaimsReturnedResult:
        result = await self.db.execute(
            select(ClaimsReturnedDispute)
            .options(selectinload(ClaimsReturnedDispute.lost_item_record))
            .where(ClaimsReturnedDispute.id == dispute_id)
            .with_for_update()
        )
        dispute = result.scalar_one_or_none()

        if not dispute:
            return ClaimsReturnedResult(
                success=False,
                dispute=None,
                message="Dispute not found",
                notification_sent=False
            )

        dispute.status = ClaimDisputeStatus.SEARCH_IN_PROGRESS
        dispute.search_locations = search_locations
        if search_notes:
            dispute.investigation_notes = (dispute.investigation_notes or "") + f"\n\nSearch started: {search_notes}"

        # Update lost record with search notes
        if dispute.lost_item_record:
            dispute.lost_item_record.search_notes = (dispute.lost_item_record.search_notes or "") + \
                f"\nLocations to search: {', '.join(search_locations)}"

        await self.db.commit()

        return ClaimsReturnedResult(
            success=True,
            dispute=dispute,
            message="Search initiated",
            notification_sent=False
        )

    async def resolve_claim(
        self,
        dispute_id: int,
        resolved_by: User,
        approved: bool,
        resolution_reason: str,
        item_found: bool = False,
        credit_amount: Optional[Decimal] = None,
        send_notification: bool = True,
    ) -> ClaimResolutionResult:
        result = await self.db.execute(
            select(ClaimsReturnedDispute)
            .options(
                selectinload(ClaimsReturnedDispute.lost_item_record).selectinload(LostItemRecord.fine),
                selectinload(ClaimsReturnedDispute.patron),
                selectinload(ClaimsReturnedDispute.item_copy),
                selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item)
            )
            .where(ClaimsReturnedDispute.id == dispute_id)
            .with_for_update()
        )
        dispute = result.scalar_one_or_none()

        if not dispute:
            return ClaimResolutionResult(
                success=False,
                dispute=None,
                credit_amount=Decimal("0.00"),
                credit_fine=None,
                item_found=False,
                notification_sent=False,
                message="Dispute not found"
            )

        if dispute.status in [ClaimDisputeStatus.APPROVED, ClaimDisputeStatus.DENIED,
                              ClaimDisputeStatus.ITEM_FOUND]:
            return ClaimResolutionResult(
                success=False,
                dispute=dispute,
                credit_amount=Decimal("0.00"),
                credit_fine=None,
                item_found=False,
                notification_sent=False,
                message="Dispute has already been resolved"
            )

        now = datetime.now(timezone.utc)
        credit_fine = None
        actual_credit = Decimal("0.00")
        notification_sent = False

        # Determine status
        if item_found:
            dispute.status = ClaimDisputeStatus.ITEM_FOUND
        elif approved:
            dispute.status = ClaimDisputeStatus.APPROVED
        else:
            dispute.status = ClaimDisputeStatus.DENIED

        dispute.resolved_at = now
        dispute.resolved_by_id = resolved_by.id
        dispute.resolution = "approved" if (approved or item_found) else "denied"
        dispute.resolution_reason = resolution_reason

        # Handle credits for approved claims or found items
        if approved or item_found:
            lost_record = dispute.lost_item_record
            if lost_record and lost_record.fine:
                fine = lost_record.fine
                if fine.status == FineStatus.unpaid:
                    # Waive the fine
                    fine.status = FineStatus.waived
                    fine.waived_at = now
                    fine.waived_by_id = resolved_by.id
                    fine.notes = (fine.notes or "") + f"\nWaived due to claims returned - {resolution_reason}"
                    actual_credit = fine.amount
                elif fine.status in [FineStatus.paid, FineStatus.partial]:
                    # Create credit for amount paid
                    amount_to_credit = credit_amount or fine.amount_paid
                    if amount_to_credit > 0:
                        credit_fine = Fine(
                            user_id=dispute.patron_id,
                            checkout_id=dispute.checkout_id,
                            fine_type=FineType.other,
                            status=FineStatus.paid,
                            amount=-amount_to_credit,
                            amount_paid=Decimal("0.00"),
                            description=f"Credit: Claims returned approved for {dispute.checkout.item.title if dispute.checkout and dispute.checkout.item else 'Unknown'}",
                            notes=resolution_reason,
                        )
                        self.db.add(credit_fine)
                        await self.db.flush()
                        dispute.credit_fine_id = credit_fine.id
                        actual_credit = amount_to_credit

            dispute.credit_amount = actual_credit

            # Update lost record status
            if lost_record:
                if item_found:
                    lost_record.status = LostItemStatus.FOUND
                    lost_record.found_at = now
                else:
                    lost_record.status = LostItemStatus.WRITTEN_OFF  # Patron claim accepted
                lost_record.resolved_by_id = resolved_by.id
                lost_record.resolution_notes = resolution_reason

            # Update item status if found
            if item_found:
                if dispute.item_copy:
                    dispute.item_copy.condition = ItemCondition.GOOD
                if dispute.checkout and dispute.checkout.item:
                    dispute.checkout.item.status = ItemStatus.available

        # Send notification to patron
        if send_notification and dispute.patron and dispute.patron.email:
            notification_sent = await self._send_resolution_notification(
                dispute=dispute,
                approved=approved or item_found,
                item_found=item_found,
                credit_amount=actual_credit,
            )

        await self.db.commit()

        # Check for claims-returned abuse escalation if claim was denied
        if not approved and not item_found:
            try:
                from .fraud_detection_service import check_claims_returned_escalation
                await check_claims_returned_escalation(
                    patron_id=dispute.patron_id,
                    db=self.db,
                    staff_id=resolved_by.id,
                )
                await self.db.commit()
            except Exception as esc_err:  # noqa: BLE001 -- escalation check is non-critical: dispute resolution proceeds regardless
                logger.debug(f"Claims escalation check failed (non-critical): {esc_err}")

        return ClaimResolutionResult(
            success=True,
            dispute=dispute,
            credit_amount=actual_credit,
            credit_fine=credit_fine,
            item_found=item_found,
            notification_sent=notification_sent,
            message="Dispute resolved successfully"
        )

    async def get_disputes(
        self,
        status: Optional[ClaimDisputeStatus] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
        unresolved_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ClaimsReturnedDispute], int]:
        query = select(ClaimsReturnedDispute).options(
            selectinload(ClaimsReturnedDispute.patron),
            selectinload(ClaimsReturnedDispute.item_copy).selectinload(ItemCopy.catalog_item),
            selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item),
            selectinload(ClaimsReturnedDispute.reviewed_by)
        )

        conditions = []
        if status:
            conditions.append(ClaimsReturnedDispute.status == status)
        if patron_id:
            conditions.append(ClaimsReturnedDispute.patron_id == patron_id)
        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(ClaimsReturnedDispute.filed_at >= cutoff)
        if unresolved_only:
            conditions.append(ClaimsReturnedDispute.status.in_([
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS
            ]))

        if conditions:
            query = query.where(and_(*conditions))

        # Get count
        count_query = select(func.count()).select_from(ClaimsReturnedDispute)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(ClaimsReturnedDispute.filed_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        disputes = result.scalars().all()

        return list(disputes), total

    async def get_overdue_disputes(self) -> List[ClaimsReturnedDispute]:
        workflow_settings = await self.get_settings()
        review_days = workflow_settings.claims_returned_review_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=review_days)

        result = await self.db.execute(
            select(ClaimsReturnedDispute)
            .options(
                selectinload(ClaimsReturnedDispute.patron),
                selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item)
            )
            .where(
                ClaimsReturnedDispute.status.in_([
                    ClaimDisputeStatus.PENDING,
                    ClaimDisputeStatus.UNDER_REVIEW,
                    ClaimDisputeStatus.SEARCH_IN_PROGRESS
                ]),
                ClaimsReturnedDispute.filed_at < cutoff
            )
            .order_by(ClaimsReturnedDispute.filed_at)
        )
        return list(result.scalars().all())

    async def _send_resolution_notification(
        self,
        dispute: ClaimsReturnedDispute,
        approved: bool,
        item_found: bool,
        credit_amount: Decimal,
    ) -> bool:
        account_url = routes.url(settings.frontend_url, routes.account_fines)
        patron = dispute.patron
        item_title = "Unknown item"
        if dispute.checkout and dispute.checkout.item:
            item_title = dispute.checkout.item.title

        if item_found:
            subject = f"Good News: Your Item Was Found - {item_title}"
            status_text = "We found the item you claimed to have returned!"
            status_color = "#28A745"
        elif approved:
            subject = f"Claims Returned Approved - {item_title}"
            status_text = "Your claims returned dispute has been approved."
            status_color = "#28A745"
        else:
            subject = f"Claims Returned Decision - {item_title}"
            status_text = "After careful review, we were unable to approve your claims returned dispute."
            status_color = "#DC3545"

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
            <h2 style="color: {COLORS['heading']};">Claims Returned Update</h2>
            <p>Hi {patron.first_name},</p>

            <div style="background-color: {'#D4EDDA' if approved or item_found else '#F8D7DA'}; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {status_color};">
                <h3 style="color: {'#155724' if approved or item_found else '#721C24'}; margin-top: 0;">{status_text}</h3>
                <p style="margin: 10px 0;"><strong>Item:</strong> {item_title}</p>
            </div>

            {credit_section}

            <p style="margin: 20px 0;"><strong>Resolution Details:</strong></p>
            <p style="color: {COLORS['body']};">{dispute.resolution_reason or 'Please contact the library if you have questions.'}</p>

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
                If you have questions, please contact the library.
            </p>
        </div>
        """

        return await send_email(patron.email, subject, html)
