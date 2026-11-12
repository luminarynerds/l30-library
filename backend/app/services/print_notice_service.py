# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.circulation import Checkout, Hold
from ..models.fine import Fine
from ..models.print_notice import (
    PrintNotice, PrintNoticeBatch, PrintNoticeBatchStatus,
    PrintNoticeCostConfig, PrintNoticeHistory, PrintNoticeStatus, PrintNoticeType
)
from ..models.user import AddressStatus, NoticePreference, User
from .address_service import AddressService, validate_address
from .print_notice_pdf import (
    generate_account_expiring_notice_pdf, generate_batch_manifest_pdf,
    generate_fine_notice_pdf, generate_hold_ready_notice_pdf,
    generate_merged_notices_pdf, generate_overdue_notice_pdf
)


# Directory for storing generated PDFs
PDF_STORAGE_DIR = Path("/tmp/print_notices")


class PrintNoticeService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cost_config(self) -> PrintNoticeCostConfig:
        result = await self.db.execute(
            select(PrintNoticeCostConfig)
            .where(PrintNoticeCostConfig.is_active == True)
            .order_by(PrintNoticeCostConfig.effective_from.desc())
            .limit(1)
        )
        config = result.scalar_one_or_none()

        if not config:
            # Return default config if none exists
            config = PrintNoticeCostConfig(
                cost_per_page=Decimal("0.05"),
                first_class_letter=Decimal("0.68"),
                first_class_large_envelope=Decimal("1.50"),
                presort_standard=Decimal("0.45"),
                large_envelope_page_threshold=6,
            )

        return config

    def calculate_notice_cost(
        self,
        pages: int,
        config: PrintNoticeCostConfig,
        use_presort: bool = False,
    ) -> tuple[Decimal, Decimal]:
        print_cost = config.cost_per_page * pages

        if use_presort:
            postage_cost = config.presort_standard
        elif pages >= config.large_envelope_page_threshold:
            postage_cost = config.first_class_large_envelope
        else:
            postage_cost = config.first_class_letter

        return (print_cost, postage_cost)

    async def create_notice(
        self,
        patron_id: int,
        notice_type: PrintNoticeType,
        subject: str,
        body_html: str,
        context_data: Optional[dict] = None,
        checkout_id: Optional[int] = None,
        hold_id: Optional[int] = None,
        fine_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> PrintNotice:
        # Get patron with address info
        result = await self.db.execute(
            select(User).where(User.id == patron_id)
        )
        patron = result.scalar_one_or_none()

        if not patron:
            raise ValueError(f"Patron not found: {patron_id}")

        # Validate patron has print preference or no email/SMS
        if patron.notice_preference not in (NoticePreference.PRINT, NoticePreference.NONE):
            if patron.email and patron.notice_preference == NoticePreference.EMAIL:
                raise ValueError("Patron prefers email notifications")

        # Validate address
        if not patron.address_line1 or not patron.city or not patron.state or not patron.zip_code:
            raise ValueError("Patron does not have a valid mailing address")

        # Verify address format
        validation = validate_address(
            patron.address_line1,
            patron.address_line2,
            patron.city,
            patron.state,
            patron.zip_code,
            patron.country or "USA"
        )

        if not validation.is_valid:
            raise ValueError(f"Invalid address: {', '.join(validation.errors)}")

        normalized = validation.normalized_address

        # Create merge key (patron_id + date for daily batching)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        merge_key = f"{patron_id}_{today}"

        # Get cost config and estimate pages (1 page per notice by default)
        config = await self.get_cost_config()
        estimated_pages = 1
        print_cost, postage_cost = self.calculate_notice_cost(estimated_pages, config)

        notice = PrintNotice(
            patron_id=patron_id,
            notice_type=notice_type,
            status=PrintNoticeStatus.PENDING,
            merge_key=merge_key,
            recipient_name=patron.full_name,
            address_line1=normalized.line1,
            address_line2=normalized.line2,
            city=normalized.city,
            state=normalized.state,
            zip_code=normalized.zip_code if not normalized.zip_plus4 else f"{normalized.zip_code}-{normalized.zip_plus4}",
            country=normalized.country,
            subject=subject,
            body_html=body_html,
            context_data=context_data,
            checkout_id=checkout_id,
            hold_id=hold_id,
            fine_id=fine_id,
            print_cost=print_cost,
            postage_cost=postage_cost,
            pages=estimated_pages,
            scheduled_for=scheduled_for or datetime.now(timezone.utc),
            created_by_id=created_by_id,
        )

        self.db.add(notice)
        await self.db.commit()
        await self.db.refresh(notice)

        return notice

    async def queue_overdue_notice(
        self,
        patron_id: int,
        checkout_ids: list[int],
        created_by_id: Optional[int] = None,
    ) -> PrintNotice:
        # Get checkout details
        result = await self.db.execute(
            select(Checkout)
            .options(selectinload(Checkout.item_copy))
            .where(Checkout.id.in_(checkout_ids))
        )
        checkouts = result.scalars().all()

        if not checkouts:
            raise ValueError("No checkouts found")

        # Build context data
        items = []
        total_fine = Decimal("0.00")
        for checkout in checkouts:
            days_overdue = (datetime.now(timezone.utc).date() - checkout.due_date).days
            fine_amount = Decimal("0.00")  # Would be calculated from fine policy

            items.append({
                "title": checkout.item_copy.catalog_item.title if checkout.item_copy and checkout.item_copy.catalog_item else "Unknown",
                "author": checkout.item_copy.catalog_item.author if checkout.item_copy and checkout.item_copy.catalog_item else "Unknown",
                "due_date": checkout.due_date.strftime("%B %d, %Y"),
                "days_overdue": days_overdue,
                "fine_amount": f"{fine_amount:.2f}",
            })
            total_fine += fine_amount

        context_data = {
            "items": items,
            "total_fine": f"{total_fine:.2f}",
            "checkout_ids": checkout_ids,
        }

        return await self.create_notice(
            patron_id=patron_id,
            notice_type=PrintNoticeType.OVERDUE,
            subject="Overdue Notice - Items Past Due",
            body_html="",  # Will be rendered from template
            context_data=context_data,
            checkout_id=checkout_ids[0] if len(checkout_ids) == 1 else None,
            created_by_id=created_by_id,
        )

    async def queue_fine_notice(
        self,
        patron_id: int,
        fine_ids: list[int],
        created_by_id: Optional[int] = None,
    ) -> PrintNotice:
        result = await self.db.execute(
            select(Fine).where(Fine.id.in_(fine_ids))
        )
        fines = result.scalars().all()

        if not fines:
            raise ValueError("No fines found")

        fine_items = []
        total_balance = Decimal("0.00")
        for fine in fines:
            fine_items.append({
                "description": fine.description or str(fine.fine_type).replace("_", " ").title(),
                "date": fine.created_at.strftime("%B %d, %Y") if fine.created_at else "N/A",
                "item_title": "N/A",  # Would need to join with checkout/item
                "amount": f"{fine.amount:.2f}",
            })
            total_balance += fine.amount - (fine.amount_paid or Decimal("0.00"))

        context_data = {
            "fines": fine_items,
            "total_balance": f"{total_balance:.2f}",
            "fine_ids": fine_ids,
        }

        return await self.create_notice(
            patron_id=patron_id,
            notice_type=PrintNoticeType.FINE,
            subject="Fine Notice - Outstanding Balance",
            body_html="",
            context_data=context_data,
            fine_id=fine_ids[0] if len(fine_ids) == 1 else None,
            created_by_id=created_by_id,
        )

    async def queue_hold_ready_notice(
        self,
        patron_id: int,
        hold_id: int,
        created_by_id: Optional[int] = None,
    ) -> PrintNotice:
        result = await self.db.execute(
            select(Hold)
            .options(selectinload(Hold.catalog_item))
            .where(Hold.id == hold_id)
        )
        hold = result.scalar_one_or_none()

        if not hold:
            raise ValueError(f"Hold not found: {hold_id}")

        pickup_by = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%B %d, %Y")

        context_data = {
            "items": [{
                "title": hold.catalog_item.title if hold.catalog_item else "Unknown",
                "author": hold.catalog_item.author if hold.catalog_item else "Unknown",
                "format": str(hold.catalog_item.item_type) if hold.catalog_item else "Unknown",
                "pickup_by": pickup_by,
            }],
            "pickup_location": "Main Library",
            "pickup_address": "123 Library Lane, Library 2030, NS 12345",
            "pickup_hours": "Mon-Thu 9AM-8PM, Fri-Sat 9AM-5PM, Sun 1PM-5PM",
            "final_pickup_date": pickup_by,
            "hold_id": hold_id,
        }

        return await self.create_notice(
            patron_id=patron_id,
            notice_type=PrintNoticeType.HOLD_READY,
            subject="Your Hold is Ready for Pickup",
            body_html="",
            context_data=context_data,
            hold_id=hold_id,
            created_by_id=created_by_id,
        )

    async def queue_account_expiring_notice(
        self,
        patron_id: int,
        expiration_date: datetime,
        created_by_id: Optional[int] = None,
    ) -> PrintNotice:
        result = await self.db.execute(
            select(User).where(User.id == patron_id)
        )
        patron = result.scalar_one_or_none()

        if not patron:
            raise ValueError(f"Patron not found: {patron_id}")

        days_until = (expiration_date.date() - datetime.now(timezone.utc).date()).days

        context_data = {
            "expiration_date": expiration_date.strftime("%B %d, %Y"),
            "days_until_expiry": days_until,
            "member_since": patron.created_at.strftime("%Y") if patron.created_at else "N/A",
            "card_type": patron.patron_type or "Standard",
            "library_card": patron.library_card,
        }

        return await self.create_notice(
            patron_id=patron_id,
            notice_type=PrintNoticeType.ACCOUNT_EXPIRING,
            subject="Library Card Renewal Notice",
            body_html="",
            context_data=context_data,
            created_by_id=created_by_id,
        )

    async def get_pending_notices(
        self,
        notice_types: Optional[list[PrintNoticeType]] = None,
        limit: int = 100,
    ) -> list[PrintNotice]:
        query = (
            select(PrintNotice)
            .where(
                and_(
                    PrintNotice.status == PrintNoticeStatus.PENDING,
                    or_(
                        PrintNotice.scheduled_for <= datetime.now(timezone.utc),
                        PrintNotice.scheduled_for.is_(None),
                    ),
                )
            )
            .order_by(PrintNotice.scheduled_for.asc())
            .limit(limit)
        )

        if notice_types:
            query = query.where(PrintNotice.notice_type.in_(notice_types))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_batch(
        self,
        name: Optional[str] = None,
        notice_types: Optional[list[PrintNoticeType]] = None,
        created_by_id: Optional[int] = None,
        auto_close_hours: Optional[int] = None,
    ) -> PrintNoticeBatch:
        batch_number = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        auto_close_at = None
        if auto_close_hours:
            auto_close_at = datetime.now(timezone.utc) + timedelta(hours=auto_close_hours)

        batch = PrintNoticeBatch(
            batch_number=batch_number,
            name=name,
            status=PrintNoticeBatchStatus.OPEN,
            notice_types=[nt.value for nt in notice_types] if notice_types else None,
            auto_close_at=auto_close_at,
            created_by_id=created_by_id,
        )

        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    async def add_notices_to_batch(
        self,
        batch_id: int,
        notice_ids: list[int],
    ) -> PrintNoticeBatch:
        result = await self.db.execute(
            select(PrintNoticeBatch).where(PrintNoticeBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        if batch.status != PrintNoticeBatchStatus.OPEN:
            raise ValueError(f"Batch is not open for additions: {batch.status}")

        # Update notices
        result = await self.db.execute(
            select(PrintNotice).where(
                and_(
                    PrintNotice.id.in_(notice_ids),
                    PrintNotice.status == PrintNoticeStatus.PENDING,
                )
            )
        )
        notices = list(result.scalars().all())

        for notice in notices:
            notice.batch_id = batch_id
            notice.status = PrintNoticeStatus.BATCHED

        # Update batch counts
        batch.notice_count = batch.notice_count + len(notices)
        batch.page_count = batch.page_count + sum(n.pages for n in notices)
        batch.total_print_cost = batch.total_print_cost + sum(n.print_cost for n in notices)
        batch.total_postage_cost = batch.total_postage_cost + sum(n.postage_cost for n in notices)

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    async def merge_notices_for_batch(self, batch_id: int) -> dict:
        result = await self.db.execute(
            select(PrintNotice)
            .where(PrintNotice.batch_id == batch_id)
            .order_by(PrintNotice.merge_key, PrintNotice.notice_type)
        )
        notices = list(result.scalars().all())

        # Group by merge key (patron + date)
        merge_groups = {}
        for notice in notices:
            if notice.merge_key not in merge_groups:
                merge_groups[notice.merge_key] = []
            merge_groups[notice.merge_key].append(notice)

        merged_count = 0
        total_savings = Decimal("0.00")

        for merge_key, group in merge_groups.items():
            if len(group) <= 1:
                continue

            # Calculate savings (one postage instead of multiple)
            config = await self.get_cost_config()
            original_postage = sum(n.postage_cost for n in group)
            combined_pages = sum(n.pages for n in group)
            _, new_postage = self.calculate_notice_cost(combined_pages, config)
            savings = original_postage - new_postage

            # Mark all but first as merged (cancelled)
            primary = group[0]
            primary.pages = combined_pages
            primary.postage_cost = new_postage
            primary.print_cost = config.cost_per_page * combined_pages

            # Combine context data
            combined_context = {
                "merged_notices": [],
                "notice_types": [],
            }
            for notice in group:
                combined_context["merged_notices"].append({
                    "type": str(notice.notice_type),
                    "subject": notice.subject,
                    "context": notice.context_data,
                })
                if str(notice.notice_type) not in combined_context["notice_types"]:
                    combined_context["notice_types"].append(str(notice.notice_type))

            primary.context_data = combined_context

            # Cancel duplicates
            for notice in group[1:]:
                notice.status = PrintNoticeStatus.CANCELLED
                notice.cancelled_at = datetime.now(timezone.utc)

            merged_count += len(group) - 1
            total_savings += savings

        await self.db.commit()

        return {
            "merged_count": merged_count,
            "total_savings": float(total_savings),
        }

    async def close_batch(
        self,
        batch_id: int,
        closed_by_id: Optional[int] = None,
    ) -> PrintNoticeBatch:
        result = await self.db.execute(
            select(PrintNoticeBatch).where(PrintNoticeBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        batch.status = PrintNoticeBatchStatus.CLOSED
        batch.closed_at = datetime.now(timezone.utc)
        batch.closed_by_id = closed_by_id

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    async def generate_batch_pdfs(
        self,
        batch_id: int,
    ) -> dict:
        result = await self.db.execute(
            select(PrintNoticeBatch).where(PrintNoticeBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        result = await self.db.execute(
            select(PrintNotice)
            .where(
                and_(
                    PrintNotice.batch_id == batch_id,
                    PrintNotice.status == PrintNoticeStatus.BATCHED,
                )
            )
            .order_by(PrintNotice.recipient_name)
        )
        notices = list(result.scalars().all())

        # Ensure storage directory exists
        PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        batch_dir = PDF_STORAGE_DIR / batch.batch_number
        batch_dir.mkdir(exist_ok=True)

        generated_count = 0
        total_pages = 0

        for notice in notices:
            try:
                pdf_bytes = await self._generate_notice_pdf(notice)

                # Save PDF
                pdf_filename = f"{notice.id}_{notice.notice_type}_{notice.recipient_name.replace(' ', '_')}.pdf"
                pdf_path = batch_dir / pdf_filename
                pdf_path.write_bytes(pdf_bytes)

                notice.pdf_file_path = str(pdf_path)
                notice.pdf_generated_at = datetime.now(timezone.utc)

                generated_count += 1
                total_pages += notice.pages

            except Exception as e:  # noqa: BLE001 -- per-iteration boundary: one PDF generation failure must not crash batch print job
                # Log error but continue with other notices
                print(f"Error generating PDF for notice {notice.id}: {e}")

        # Generate batch manifest
        manifest_bytes = generate_batch_manifest_pdf(batch, notices)
        manifest_path = batch_dir / f"MANIFEST_{batch.batch_number}.pdf"
        manifest_path.write_bytes(manifest_bytes)
        batch.manifest_pdf_path = str(manifest_path)

        batch.status = PrintNoticeBatchStatus.PRINTING
        batch.page_count = total_pages

        await self.db.commit()

        return {
            "generated_count": generated_count,
            "total_pages": total_pages,
            "manifest_path": str(manifest_path),
        }

    async def _generate_notice_pdf(self, notice: PrintNotice) -> bytes:
        context = notice.context_data or {}

        if notice.notice_type == PrintNoticeType.OVERDUE:
            return generate_overdue_notice_pdf(
                notice,
                items=context.get("items", []),
                total_fine=Decimal(context.get("total_fine", "0.00")),
            )

        elif notice.notice_type == PrintNoticeType.FINE:
            return generate_fine_notice_pdf(
                notice,
                fines=context.get("fines", []),
                total_balance=Decimal(context.get("total_balance", "0.00")),
                account_blocked=context.get("account_blocked", False),
            )

        elif notice.notice_type == PrintNoticeType.HOLD_READY:
            return generate_hold_ready_notice_pdf(
                notice,
                items=context.get("items", []),
                pickup_location=context.get("pickup_location", "Main Library"),
                pickup_address=context.get("pickup_address", ""),
                pickup_hours=context.get("pickup_hours", ""),
                final_pickup_date=context.get("final_pickup_date", ""),
            )

        elif notice.notice_type == PrintNoticeType.ACCOUNT_EXPIRING:
            return generate_account_expiring_notice_pdf(
                notice,
                expiration_date=context.get("expiration_date", ""),
                days_until_expiry=context.get("days_until_expiry", 0),
                member_since=context.get("member_since", ""),
                card_type=context.get("card_type", "Standard"),
                items_checked_out=context.get("items_checked_out", 0),
                holds_count=context.get("holds_count", 0),
            )

        else:
            # Generic notice - just use overdue template as base
            return generate_overdue_notice_pdf(notice, items=[], total_fine=Decimal("0.00"))

    async def mark_batch_printed(
        self,
        batch_id: int,
        printed_by_id: Optional[int] = None,
    ) -> PrintNoticeBatch:
        result = await self.db.execute(
            select(PrintNoticeBatch).where(PrintNoticeBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        batch.status = PrintNoticeBatchStatus.PRINTED
        batch.printed_at = datetime.now(timezone.utc)
        batch.printed_by_id = printed_by_id

        # Update all notices in batch
        result = await self.db.execute(
            select(PrintNotice).where(
                and_(
                    PrintNotice.batch_id == batch_id,
                    PrintNotice.status == PrintNoticeStatus.BATCHED,
                )
            )
        )
        notices = result.scalars().all()

        for notice in notices:
            notice.status = PrintNoticeStatus.PRINTED
            notice.printed_at = datetime.now(timezone.utc)
            notice.printed_by_id = printed_by_id

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    async def mark_batch_mailed(
        self,
        batch_id: int,
        mailed_by_id: Optional[int] = None,
    ) -> PrintNoticeBatch:
        result = await self.db.execute(
            select(PrintNoticeBatch).where(PrintNoticeBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        batch.status = PrintNoticeBatchStatus.MAILED
        batch.mailed_at = datetime.now(timezone.utc)
        batch.mailed_by_id = mailed_by_id

        # Update all notices and create history records
        result = await self.db.execute(
            select(PrintNotice)
            .options(selectinload(PrintNotice.patron))
            .where(
                and_(
                    PrintNotice.batch_id == batch_id,
                    PrintNotice.status == PrintNoticeStatus.PRINTED,
                )
            )
        )
        notices = result.scalars().all()

        for notice in notices:
            notice.status = PrintNoticeStatus.MAILED
            notice.mailed_at = datetime.now(timezone.utc)
            notice.mailed_by_id = mailed_by_id

            # Create history record
            history = PrintNoticeHistory(
                notice_id=notice.id,
                batch_id=batch_id,
                patron_id=notice.patron_id,
                patron_name=notice.recipient_name,
                patron_library_card=notice.patron.library_card if notice.patron else None,
                notice_type=notice.notice_type,
                subject=notice.subject,
                mailing_address=notice.full_address,
                final_status="mailed",
                mailed_at=notice.mailed_at,
                total_cost=notice.total_cost,
                context_summary=str(notice.context_data)[:500] if notice.context_data else None,
            )
            self.db.add(history)

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    async def mark_notice_returned(
        self,
        notice_id: int,
        return_reason: str,
        update_patron_address: bool = True,
    ) -> PrintNotice:
        result = await self.db.execute(
            select(PrintNotice)
            .options(selectinload(PrintNotice.patron))
            .where(PrintNotice.id == notice_id)
        )
        notice = result.scalar_one_or_none()

        if not notice:
            raise ValueError(f"Notice not found: {notice_id}")

        notice.status = PrintNoticeStatus.RETURNED
        notice.returned_at = datetime.now(timezone.utc)
        notice.return_reason = return_reason

        # Update history record if exists
        result = await self.db.execute(
            select(PrintNoticeHistory).where(PrintNoticeHistory.notice_id == notice_id)
        )
        history = result.scalar_one_or_none()

        if history:
            history.returned = True
            history.return_reason = return_reason
            history.final_status = "returned"

        # Update patron's address status
        if update_patron_address and notice.patron:
            notice.patron.address_status = AddressStatus.RETURNED_MAIL
            notice.patron.address_returned_mail_count += 1
            notice.patron.address_last_returned_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(notice)

        return notice

    async def get_patrons_needing_print_notices(self) -> list[User]:
        result = await self.db.execute(
            select(User).where(
                or_(
                    User.notice_preference == NoticePreference.PRINT,
                    and_(
                        User.notice_preference == NoticePreference.NONE,
                        User.email.is_(None),
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def get_batch(self, batch_id: int) -> Optional[PrintNoticeBatch]:
        result = await self.db.execute(
            select(PrintNoticeBatch)
            .options(selectinload(PrintNoticeBatch.notices))
            .where(PrintNoticeBatch.id == batch_id)
        )
        return result.scalar_one_or_none()

    async def get_notice(self, notice_id: int) -> Optional[PrintNotice]:
        result = await self.db.execute(
            select(PrintNotice)
            .options(selectinload(PrintNotice.patron))
            .where(PrintNotice.id == notice_id)
        )
        return result.scalar_one_or_none()

    async def list_batches(
        self,
        status: Optional[PrintNoticeBatchStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PrintNoticeBatch]:
        query = select(PrintNoticeBatch).order_by(PrintNoticeBatch.opened_at.desc())

        if status:
            query = query.where(PrintNoticeBatch.status == status)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_notices(
        self,
        patron_id: Optional[int] = None,
        status: Optional[PrintNoticeStatus] = None,
        notice_type: Optional[PrintNoticeType] = None,
        batch_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PrintNotice]:
        query = select(PrintNotice).order_by(PrintNotice.id.desc())

        if patron_id:
            query = query.where(PrintNotice.patron_id == patron_id)
        if status:
            query = query.where(PrintNotice.status == status)
        if notice_type:
            query = query.where(PrintNotice.notice_type == notice_type)
        if batch_id:
            query = query.where(PrintNotice.batch_id == batch_id)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_notice_history(
        self,
        patron_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PrintNoticeHistory]:
        query = select(PrintNoticeHistory).order_by(PrintNoticeHistory.mailed_at.desc())

        if patron_id:
            query = query.where(PrintNoticeHistory.patron_id == patron_id)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        query = select(
            func.count(PrintNoticeHistory.id).label("total_notices"),
            func.sum(PrintNoticeHistory.total_cost).label("total_cost"),
            func.count(PrintNoticeHistory.id).filter(PrintNoticeHistory.returned == True).label("returned_count"),
        ).select_from(PrintNoticeHistory)

        if start_date:
            query = query.where(PrintNoticeHistory.mailed_at >= start_date)
        if end_date:
            query = query.where(PrintNoticeHistory.mailed_at <= end_date)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_notices": row.total_notices or 0,
            "total_cost": float(row.total_cost or 0),
            "returned_count": row.returned_count or 0,
            "return_rate": (row.returned_count / row.total_notices * 100) if row.total_notices else 0,
        }
