# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.print import (
    PrintJob, Printer, PrintPricing, PrintQuota, PrintRefund,
    PrintJobStatus, ColorMode, ScanToEmail, ScanToEmailStatus, PrinterAlert,
    PrintReleaseStation
)
from ..models.user import User


class PrintService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_print_job(
        self,
        user_id: Optional[int],
        job_name: str,
        pages: int,
        copies: int = 1,
        color_mode: ColorMode = ColorMode.blackwhite,
        double_sided: bool = True,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        file_path: Optional[str] = None,
        file_mime_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PrintJob:

        # Generate unique job ID
        job_uid = str(uuid.uuid4())

        # Calculate cost
        cost, cost_breakdown = await self._calculate_cost(
            pages=pages,
            copies=copies,
            color_mode=color_mode,
            double_sided=double_sided,
            device_type=device_type
        )

        # Check quota if user is authenticated
        if user_id:
            quota = await self._get_or_create_quota(user_id)
            # Check if user would exceed quota
            total_pages = pages * copies
            if (quota.pages_used_this_month + total_pages > quota.monthly_pages_limit and
                    not quota.quota_override_enabled and quota.enforce_quota):
                raise ValueError(
                    f"Print quota exceeded. You have {quota.pages_remaining} pages remaining this month."
                )

        # Create job
        job = PrintJob(
            user_id=user_id,
            job_name=job_name,
            job_uid=job_uid,
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            pages=pages,
            copies=copies,
            color_mode=color_mode,
            double_sided=double_sided,
            cost=cost,
            cost_breakdown=cost_breakdown,
            file_path=file_path,
            file_mime_type=file_mime_type,
            ip_address=ip_address,
            user_agent=user_agent,
            status=PrintJobStatus.submitted,
        )

        self.db.add(job)
        await self.db.flush()  # Get the job ID

        # Update quota
        if user_id:
            quota = await self._get_or_create_quota(user_id)
            quota.pages_used_this_month += pages * copies
            quota.cost_incurred_this_month += cost

        await self.db.commit()
        return job

    async def get_print_job(self, job_id: int) -> Optional[PrintJob]:
        result = await self.db.execute(select(PrintJob).filter(PrintJob.id == job_id))
        return result.scalar_one_or_none()

    async def get_user_print_jobs(
        self,
        user_id: int,
        status: Optional[PrintJobStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[PrintJob], int]:
        query = select(PrintJob).filter(PrintJob.user_id == user_id)

        if status:
            query = query.filter(PrintJob.status == status)

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(PrintJob).filter(PrintJob.user_id == user_id)
        )
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(PrintJob.submitted_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        jobs = result.scalars().all()

        return jobs, total

    async def get_print_queue(self, printer_id: Optional[int] = None) -> List[PrintJob]:
        query = select(PrintJob).filter(
            PrintJob.status.in_([PrintJobStatus.submitted, PrintJobStatus.queued])
        )

        if printer_id:
            query = query.filter(PrintJob.printer_id == printer_id)

        query = query.order_by(PrintJob.submitted_at.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def assign_printer(self, job_id: int, printer_id: int) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.printer_id = printer_id
        job.status = PrintJobStatus.queued

        # Get printer info
        result = await self.db.execute(select(Printer).filter(Printer.id == printer_id))
        printer = result.scalar_one_or_none()
        if printer:
            job.printer_name = printer.name

        await self.db.commit()
        return job

    async def send_to_printer(self, job_id: int) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.status = PrintJobStatus.printing
        job.sent_to_printer_at = datetime.now(timezone.utc)
        job.printing_started_at = datetime.now(timezone.utc)

        await self.db.commit()
        return job

    async def mark_job_completed(self, job_id: int, release_station_id: Optional[int] = None) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.status = PrintJobStatus.completed
        job.completed_at = datetime.now(timezone.utc)

        if release_station_id:
            job.release_station_id = release_station_id
            job.status = PrintJobStatus.held  # Hold at release station

        # Update printer stats
        if job.printer_id:
            printer = await self.db.execute(
                select(Printer).filter(Printer.id == job.printer_id)
            )
            printer_obj = printer.scalar_one_or_none()
            if printer_obj:
                printer_obj.total_jobs += 1
                printer_obj.total_pages_printed += job.total_pages
                if job.color_mode == ColorMode.color:
                    printer_obj.total_color_pages += job.total_pages
                printer_obj.total_revenue += job.cost

        await self.db.commit()
        return job

    async def mark_job_failed(self, job_id: int, failure_reason: str, last_error: Optional[str] = None) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.status = PrintJobStatus.failed
        job.failed_at = datetime.now(timezone.utc)
        job.failure_reason = failure_reason
        job.last_error = last_error

        await self.db.commit()
        return job

    async def cancel_job(self, job_id: int) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        if job.status in [PrintJobStatus.printing, PrintJobStatus.completed]:
            raise ValueError(f"Cannot cancel job with status {job.status}")

        job.status = PrintJobStatus.cancelled
        job.cancelled_at = datetime.now(timezone.utc)

        # Refund user's quota
        if job.user_id:
            quota = await self._get_or_create_quota(job.user_id)
            quota.pages_used_this_month = max(0, quota.pages_used_this_month - (job.pages * job.copies))
            quota.cost_incurred_this_month = max(Decimal("0.00"), quota.cost_incurred_this_month - job.cost)

        await self.db.commit()
        return job

    async def process_payment(
        self,
        job_id: int,
        payment_method: str,
        payment_reference: Optional[str] = None,
        account_balance_used: Decimal = Decimal("0.00"),
    ) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.payment_method = payment_method
        job.payment_processed = True
        job.payment_reference = payment_reference
        job.payment_amount_charged = job.cost - account_balance_used
        job.account_balance_used = account_balance_used

        await self.db.commit()
        return job

    async def release_print_job(
        self,
        job_id: int,
        release_station_id: int,
        card_number_last_4: Optional[str] = None,
    ) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        if job.status != PrintJobStatus.held:
            raise ValueError(f"Job is not in held status (current: {job.status})")

        if not job.payment_processed:
            raise ValueError("Payment must be processed before release")

        job.release_timestamp = datetime.now(timezone.utc)
        job.released_at = datetime.now(timezone.utc)
        job.status = PrintJobStatus.completed
        job.card_number_scanned = card_number_last_4

        # Update release station stats
        result = await self.db.execute(
            select(PrintReleaseStation).filter(PrintReleaseStation.id == release_station_id)
        )
        station = result.scalar_one_or_none()
        if station:
            station.total_jobs_released += 1
            station.total_payments_collected += job.payment_amount_charged or job.cost

        await self.db.commit()
        return job

    async def generate_release_code(self, job_id: int) -> str:
        import random
        import string

        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        # Generate 4-6 digit PIN
        code = str(random.randint(1000, 999999))

        job.release_code = code
        await self.db.commit()

        return code

    async def create_refund_request(
        self,
        job_id: int,
        reason: str,
        refund_method: str = "account_credit",
        description: Optional[str] = None,
        photo_evidence_path: Optional[str] = None,
    ) -> PrintRefund:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        if not job.user_id:
            raise ValueError("Cannot refund anonymous print job")

        refund = PrintRefund(
            print_job_id=job_id,
            user_id=job.user_id,
            reason=reason,
            refund_amount=job.cost,
            refund_method=refund_method,
            description=description,
            photo_evidence_path=photo_evidence_path,
        )

        self.db.add(refund)
        await self.db.commit()

        return refund

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _calculate_cost(
        self,
        pages: int,
        copies: int,
        color_mode: ColorMode,
        double_sided: bool,
        device_type: Optional[str] = None,
    ) -> tuple[Decimal, Dict]:

        # Get active pricing
        result = await self.db.execute(
            select(PrintPricing).filter(
                and_(
                    PrintPricing.is_active == True,
                    PrintPricing.effective_from <= func.now(),
                    or_(
                        PrintPricing.effective_to == None,
                        PrintPricing.effective_to > func.now()
                    )
                )
            ).order_by(PrintPricing.effective_from.desc())
        )
        pricing = result.scalar_one_or_none()

        if not pricing:
            # Default pricing
            pricing = PrintPricing()

        total_pages = pages * copies
        cost_breakdown = {}

        # Base cost per page
        if color_mode == ColorMode.color:
            base_cost = Decimal(str(pricing.color_price_per_page)) * Decimal(str(total_pages))
            cost_breakdown["color_pages"] = float(base_cost)
        else:
            base_cost = Decimal(str(pricing.blackwhite_price_per_page)) * Decimal(str(total_pages))
            cost_breakdown["blackwhite_pages"] = float(base_cost)

        # Double-sided discount
        if double_sided and pricing.double_sided_discount_percentage > 0:
            discount = base_cost * Decimal(str(pricing.double_sided_discount_percentage)) / Decimal("100")
            base_cost -= discount
            cost_breakdown["double_sided_discount"] = -float(discount)

        # Bulk discount
        if total_pages > pricing.bulk_threshold_pages and pricing.discount_percentage_for_bulk > 0:
            discount = base_cost * Decimal(str(pricing.discount_percentage_for_bulk)) / Decimal("100")
            base_cost -= discount
            cost_breakdown["bulk_discount"] = -float(discount)

        # Copy machine surcharge
        if device_type == "copy_machine" and pricing.copy_machine_surcharge_percentage > 0:
            surcharge = base_cost * Decimal(str(pricing.copy_machine_surcharge_percentage)) / Decimal("100")
            base_cost += surcharge
            cost_breakdown["copy_machine_surcharge"] = float(surcharge)

        # Apply minimum charge
        if base_cost < pricing.minimum_charge:
            adjustment = pricing.minimum_charge - base_cost
            cost_breakdown["minimum_charge_adjustment"] = float(adjustment)
            base_cost = pricing.minimum_charge

        cost_breakdown["total"] = float(base_cost)

        return base_cost, cost_breakdown

    async def _get_or_create_quota(self, user_id: int) -> PrintQuota:
        result = await self.db.execute(
            select(PrintQuota).filter(PrintQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()

        if not quota:
            quota = PrintQuota(user_id=user_id)
            self.db.add(quota)
            await self.db.flush()

        # Reset monthly quota if needed
        now = datetime.now(timezone.utc)
        if quota.month_starts_on and (now - quota.month_starts_on).days >= 30:
            quota.pages_used_this_month = 0
            quota.cost_incurred_this_month = Decimal("0.00")
            quota.month_starts_on = now

        return quota

    async def reset_monthly_quotas(self) -> int:
        result = await self.db.execute(
            select(PrintQuota).filter(
                PrintQuota.month_starts_on <= func.now() - timedelta(days=30)
            )
        )
        quotas = result.scalars().all()

        now = datetime.now(timezone.utc)
        for quota in quotas:
            quota.pages_used_this_month = 0
            quota.cost_incurred_this_month = Decimal("0.00")
            quota.month_starts_on = now

        await self.db.commit()
        return len(quotas)

    async def get_user_quota(self, user_id: int) -> PrintQuota:
        quota = await self._get_or_create_quota(user_id)
        return quota

    # ========================================================================
    # Scan to Email
    # ========================================================================

    async def create_scan_to_email(
        self,
        user_id: int,
        recipient_email: str,
        job_name: str,
        scanner_device_id: Optional[str] = None,
        scanner_name: Optional[str] = None,
        page_count: int = 1,
    ) -> ScanToEmail:

        scan = ScanToEmail(
            user_id=user_id,
            recipient_email=recipient_email,
            job_name=job_name,
            scanner_device_id=scanner_device_id,
            scanner_name=scanner_name,
            page_count=page_count,
            status=ScanToEmailStatus.pending,
        )

        self.db.add(scan)
        await self.db.flush()

        return scan

    async def get_scan_to_email(self, scan_id: int) -> Optional[ScanToEmail]:
        result = await self.db.execute(
            select(ScanToEmail).filter(ScanToEmail.id == scan_id)
        )
        return result.scalar_one_or_none()

    async def mark_scan_sent(
        self,
        scan_id: int,
        file_path: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
    ) -> ScanToEmail:
        scan = await self.get_scan_to_email(scan_id)
        if not scan:
            raise ValueError(f"Scan job {scan_id} not found")

        scan.status = ScanToEmailStatus.sent
        scan.email_sent_at = datetime.now(timezone.utc)
        if file_path:
            scan.file_path = file_path
        if file_size_bytes:
            scan.file_size_bytes = file_size_bytes

        await self.db.commit()
        return scan

    async def mark_scan_failed(
        self,
        scan_id: int,
        error_message: str,
    ) -> ScanToEmail:
        scan = await self.get_scan_to_email(scan_id)
        if not scan:
            raise ValueError(f"Scan job {scan_id} not found")

        scan.status = ScanToEmailStatus.failed
        scan.error_message = error_message

        await self.db.commit()
        return scan

    # ========================================================================
    # Print Preview
    # ========================================================================

    async def generate_print_preview(
        self,
        job_id: int,
        preview_image_path: str,
    ) -> PrintJob:
        job = await self.get_print_job(job_id)
        if not job:
            raise ValueError(f"Print job {job_id} not found")

        job.preview_image_path = preview_image_path

        await self.db.commit()
        return job

    async def get_print_job_preview(self, job_id: int) -> Optional[str]:
        job = await self.get_print_job(job_id)
        if not job:
            return None

        return job.preview_image_path
