# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.public_records_request import (
    calculate_response_deadline,
    ExemptionType,
    JURISDICTION_DEADLINES,
    JurisdictionType,
    PublicRecordsAuditAction,
    PublicRecordsAuditLog,
    PublicRecordsRedaction,
    PublicRecordsRequest,
    PublicRecordsRequestStatus,
    PublicRecordsRequestType,
)
from ..models.user import User

logger = get_logger(__name__)

# Fee configuration (per page/hour)
DEFAULT_COPY_FEE_PER_PAGE = Decimal("0.10")
DEFAULT_SEARCH_FEE_PER_HOUR = Decimal("25.00")
DEFAULT_REVIEW_FEE_PER_HOUR = Decimal("35.00")


class PublicRecordsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Request Management
    # =========================================================================

    async def create_request(
        self,
        request_type: PublicRecordsRequestType,
        jurisdiction: JurisdictionType,
        requester_name: str,
        description: str,
        date_received: datetime,
        created_by: Optional[User] = None,
        requester_email: Optional[str] = None,
        requester_phone: Optional[str] = None,
        requester_organization: Optional[str] = None,
        requester_address: Optional[str] = None,
        is_media: bool = False,
        is_commercial: bool = False,
        records_date_range_start: Optional[date] = None,
        records_date_range_end: Optional[date] = None,
        preferred_format: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        meeting_id: Optional[int] = None,
        committee_id: Optional[int] = None,
        submitted_via: Optional[str] = None,
    ) -> PublicRecordsRequest:
        # Generate tracking number
        tracking_number = await self._generate_tracking_number()

        # Calculate deadline
        response_deadline = calculate_response_deadline(date_received, jurisdiction)

        # Create the request
        request = PublicRecordsRequest(
            tracking_number=tracking_number,
            request_type=request_type,
            jurisdiction=jurisdiction,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_phone=requester_phone,
            requester_organization=requester_organization,
            requester_address=requester_address,
            is_media=is_media,
            is_commercial=is_commercial,
            date_received=date_received,
            description=description,
            records_date_range_start=records_date_range_start,
            records_date_range_end=records_date_range_end,
            preferred_format=preferred_format,
            response_deadline=response_deadline,
            status=PublicRecordsRequestStatus.RECEIVED,
            created_by_id=created_by.id if created_by else None,
            meeting_id=meeting_id,
            committee_id=committee_id,
            submitted_via=submitted_via,
        )

        self.db.add(request)
        await self.db.flush()

        # Create audit log
        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.REQUEST_RECEIVED,
            performed_by_id=created_by.id if created_by else None,
            details={
                "tracking_number": tracking_number,
                "request_type": request_type.value,
                "jurisdiction": jurisdiction.value,
                "requester_name": requester_name,
                "response_deadline": response_deadline.isoformat(),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        logger.info(
            f"Public records request created: {tracking_number}",
            extra={
                "tracking_number": tracking_number,
                "request_type": request_type.value,
                "jurisdiction": jurisdiction.value,
            },
        )

        return request

    async def get_request(
        self,
        request_id: int,
        viewer: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        result = await self.db.execute(
            select(PublicRecordsRequest)
            .options(
                selectinload(PublicRecordsRequest.assigned_to),
                selectinload(PublicRecordsRequest.redactions),
            )
            .where(PublicRecordsRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if request and viewer:
            await self._create_audit_log(
                request_id=request.id,
                action=PublicRecordsAuditAction.VIEWED,
                performed_by_id=viewer.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()

        return request

    async def get_request_by_tracking(
        self, tracking_number: str
    ) -> Optional[PublicRecordsRequest]:
        result = await self.db.execute(
            select(PublicRecordsRequest)
            .options(
                selectinload(PublicRecordsRequest.assigned_to),
                selectinload(PublicRecordsRequest.redactions),
            )
            .where(PublicRecordsRequest.tracking_number == tracking_number)
        )
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        skip: int = 0,
        limit: int = 50,
        request_type: Optional[PublicRecordsRequestType] = None,
        status: Optional[PublicRecordsRequestStatus] = None,
        jurisdiction: Optional[JurisdictionType] = None,
        assigned_to_id: Optional[int] = None,
        is_overdue: Optional[bool] = None,
        year: Optional[int] = None,
    ) -> tuple[list[PublicRecordsRequest], int]:
        query = select(PublicRecordsRequest)
        count_query = select(func.count(PublicRecordsRequest.id))

        conditions = []
        if request_type:
            conditions.append(PublicRecordsRequest.request_type == request_type)
        if status:
            conditions.append(PublicRecordsRequest.status == status)
        if jurisdiction:
            conditions.append(PublicRecordsRequest.jurisdiction == jurisdiction)
        if assigned_to_id:
            conditions.append(PublicRecordsRequest.assigned_to_id == assigned_to_id)
        if year:
            conditions.append(
                extract("year", PublicRecordsRequest.date_received) == year
            )
        if is_overdue is not None:
            today = date.today()
            active_statuses = [
                PublicRecordsRequestStatus.RECEIVED,
                PublicRecordsRequestStatus.ACKNOWLEDGED,
                PublicRecordsRequestStatus.IN_PROGRESS,
                PublicRecordsRequestStatus.PENDING_CLARIFICATION,
                PublicRecordsRequestStatus.PENDING_FEE_PAYMENT,
                PublicRecordsRequestStatus.RECORDS_LOCATED,
                PublicRecordsRequestStatus.UNDER_REVIEW,
                PublicRecordsRequestStatus.REDACTION_IN_PROGRESS,
                PublicRecordsRequestStatus.READY_FOR_RELEASE,
            ]
            if is_overdue:
                conditions.append(
                    and_(
                        PublicRecordsRequest.status.in_(active_statuses),
                        or_(
                            and_(
                                PublicRecordsRequest.extended_deadline.isnot(None),
                                PublicRecordsRequest.extended_deadline < today,
                            ),
                            and_(
                                PublicRecordsRequest.extended_deadline.is_(None),
                                PublicRecordsRequest.response_deadline < today,
                            ),
                        ),
                    )
                )
            else:
                conditions.append(
                    or_(
                        ~PublicRecordsRequest.status.in_(active_statuses),
                        and_(
                            PublicRecordsRequest.extended_deadline.isnot(None),
                            PublicRecordsRequest.extended_deadline >= today,
                        ),
                        and_(
                            PublicRecordsRequest.extended_deadline.is_(None),
                            PublicRecordsRequest.response_deadline >= today,
                        ),
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get results
        query = (
            query.options(selectinload(PublicRecordsRequest.assigned_to))
            .order_by(PublicRecordsRequest.response_deadline.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    async def acknowledge_request(
        self,
        request_id: int,
        acknowledged_by: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        now = datetime.now(timezone.utc)
        request.date_acknowledged = now
        request.status = PublicRecordsRequestStatus.ACKNOWLEDGED

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.REQUEST_ACKNOWLEDGED,
            performed_by_id=acknowledged_by.id,
            details={"notes": notes},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def update_status(
        self,
        request_id: int,
        new_status: PublicRecordsRequestStatus,
        updated_by: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        old_status = request.status
        request.status = new_status

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.STATUS_CHANGED,
            performed_by_id=updated_by.id,
            details={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "notes": notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def assign_request(
        self,
        request_id: int,
        assign_to_id: int,
        assigned_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        old_assignee = request.assigned_to_id
        request.assigned_to_id = assign_to_id

        if request.status == PublicRecordsRequestStatus.RECEIVED:
            request.status = PublicRecordsRequestStatus.IN_PROGRESS

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.STATUS_CHANGED,
            performed_by_id=assigned_by.id,
            details={
                "old_assignee_id": old_assignee,
                "new_assignee_id": assign_to_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Extension Management
    # =========================================================================

    async def grant_extension(
        self,
        request_id: int,
        additional_days: int,
        reason: str,
        granted_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        # Calculate new deadline from current effective deadline
        current_deadline = request.extended_deadline or request.response_deadline
        new_deadline = current_deadline + timedelta(days=additional_days)

        request.extension_granted = True
        request.extension_reason = reason
        request.extended_deadline = new_deadline

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.EXTENSION_GRANTED,
            performed_by_id=granted_by.id,
            details={
                "original_deadline": request.response_deadline.isoformat(),
                "previous_extended_deadline": current_deadline.isoformat(),
                "new_deadline": new_deadline.isoformat(),
                "additional_days": additional_days,
                "reason": reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Fee Management
    # =========================================================================

    async def estimate_fees(
        self,
        request_id: int,
        pages: int,
        search_hours: float,
        review_hours: float,
        estimated_by: User,
        copy_fee_per_page: Optional[Decimal] = None,
        search_fee_per_hour: Optional[Decimal] = None,
        review_fee_per_hour: Optional[Decimal] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        copy_fee = copy_fee_per_page or DEFAULT_COPY_FEE_PER_PAGE
        search_fee = search_fee_per_hour or DEFAULT_SEARCH_FEE_PER_HOUR
        review_fee = review_fee_per_hour or DEFAULT_REVIEW_FEE_PER_HOUR

        total = (
            Decimal(pages) * copy_fee
            + Decimal(str(search_hours)) * search_fee
            + Decimal(str(review_hours)) * review_fee
        )

        request.fee_estimate = total
        request.fee_estimate_date = datetime.now(timezone.utc)
        request.status = PublicRecordsRequestStatus.PENDING_FEE_PAYMENT

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.FEE_ESTIMATED,
            performed_by_id=estimated_by.id,
            details={
                "pages": pages,
                "copy_fee_per_page": str(copy_fee),
                "search_hours": search_hours,
                "search_fee_per_hour": str(search_fee),
                "review_hours": review_hours,
                "review_fee_per_hour": str(review_fee),
                "total_estimate": str(total),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def waive_fees(
        self,
        request_id: int,
        reason: str,
        waived_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        request.fee_waived = True
        request.fee_waiver_reason = reason

        if request.status == PublicRecordsRequestStatus.PENDING_FEE_PAYMENT:
            request.status = PublicRecordsRequestStatus.IN_PROGRESS

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.FEE_WAIVED,
            performed_by_id=waived_by.id,
            details={
                "waived_amount": str(request.fee_estimate) if request.fee_estimate else None,
                "reason": reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def record_fee_payment(
        self,
        request_id: int,
        amount: Decimal,
        recorded_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        request.fee_paid = amount
        request.fee_paid_date = datetime.now(timezone.utc)

        if request.status == PublicRecordsRequestStatus.PENDING_FEE_PAYMENT:
            request.status = PublicRecordsRequestStatus.IN_PROGRESS

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.FEE_PAID,
            performed_by_id=recorded_by.id,
            details={
                "amount_paid": str(amount),
                "estimate_was": str(request.fee_estimate) if request.fee_estimate else None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Redaction Management
    # =========================================================================

    async def add_redaction(
        self,
        request_id: int,
        document_name: str,
        exemption_type: ExemptionType,
        redacted_by: User,
        page_number: Optional[int] = None,
        section_reference: Optional[str] = None,
        exemption_description: Optional[str] = None,
        redaction_description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicRecordsRedaction:
        redaction = PublicRecordsRedaction(
            request_id=request_id,
            document_name=document_name,
            page_number=page_number,
            section_reference=section_reference,
            exemption_type=exemption_type,
            exemption_description=exemption_description,
            redaction_description=redaction_description,
            redacted_by_id=redacted_by.id,
        )
        self.db.add(redaction)
        await self.db.flush()

        # Update request status if needed
        request = await self._get_request_for_update(request_id)
        if request and request.status not in [
            PublicRecordsRequestStatus.REDACTION_IN_PROGRESS,
            PublicRecordsRequestStatus.READY_FOR_RELEASE,
        ]:
            request.status = PublicRecordsRequestStatus.REDACTION_IN_PROGRESS

        await self._create_audit_log(
            request_id=request_id,
            action=PublicRecordsAuditAction.REDACTION_STARTED,
            performed_by_id=redacted_by.id,
            details={
                "document_name": document_name,
                "exemption_type": exemption_type.value,
                "page_number": page_number,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(redaction)

        return redaction

    async def get_redactions(self, request_id: int) -> list[PublicRecordsRedaction]:
        result = await self.db.execute(
            select(PublicRecordsRedaction)
            .options(
                selectinload(PublicRecordsRedaction.redacted_by),
                selectinload(PublicRecordsRedaction.reviewed_by),
            )
            .where(PublicRecordsRedaction.request_id == request_id)
            .order_by(PublicRecordsRedaction.document_name, PublicRecordsRedaction.page_number)
        )
        return list(result.scalars().all())

    # =========================================================================
    # Response Management
    # =========================================================================

    async def record_response(
        self,
        request_id: int,
        response_method: str,
        responded_by: User,
        records_provided_count: int = 0,
        records_withheld_count: int = 0,
        response_summary: Optional[str] = None,
        denial_reason: Optional[str] = None,
        exemptions_cited: Optional[list[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        now = datetime.now(timezone.utc)
        request.response_date = now
        request.response_method = response_method
        request.records_provided_count = records_provided_count
        request.records_withheld_count = records_withheld_count
        request.response_summary = response_summary

        # Determine final status
        if records_provided_count == 0 and records_withheld_count > 0:
            request.status = PublicRecordsRequestStatus.DENIED
            request.denial_reason = denial_reason
            request.exemptions_cited = exemptions_cited
        elif records_withheld_count > 0:
            request.status = PublicRecordsRequestStatus.PARTIALLY_DENIED
            request.denial_reason = denial_reason
            request.exemptions_cited = exemptions_cited
        else:
            request.status = PublicRecordsRequestStatus.COMPLETED

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.RECORDS_RELEASED,
            performed_by_id=responded_by.id,
            details={
                "response_method": response_method,
                "records_provided": records_provided_count,
                "records_withheld": records_withheld_count,
                "status": str(request.status),
                "exemptions_cited": exemptions_cited,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def deny_request(
        self,
        request_id: int,
        denial_reason: str,
        exemptions_cited: list[str],
        denied_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        request.status = PublicRecordsRequestStatus.DENIED
        request.denial_reason = denial_reason
        request.exemptions_cited = exemptions_cited
        request.response_date = datetime.now(timezone.utc)
        request.records_provided_count = 0

        # Calculate appeal deadline (typically 30 days)
        request.appeal_deadline = date.today() + timedelta(days=30)

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.REQUEST_DENIED,
            performed_by_id=denied_by.id,
            details={
                "denial_reason": denial_reason,
                "exemptions_cited": exemptions_cited,
                "appeal_deadline": request.appeal_deadline.isoformat(),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Appeal Handling
    # =========================================================================

    async def record_appeal(
        self,
        request_id: int,
        recorded_by: User,
        appeal_notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        request.appeal_filed = True
        request.appeal_date = datetime.now(timezone.utc)
        request.status = PublicRecordsRequestStatus.APPEALED

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.APPEAL_FILED,
            performed_by_id=recorded_by.id,
            details={"notes": appeal_notes},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def record_appeal_decision(
        self,
        request_id: int,
        decision: str,  # upheld, overturned, partial
        recorded_by: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicRecordsRequest]:
        request = await self._get_request_for_update(request_id)
        if not request:
            return None

        request.appeal_decision = decision
        request.appeal_decision_date = datetime.now(timezone.utc)

        if decision == "upheld":
            request.status = PublicRecordsRequestStatus.DENIED
        elif decision == "overturned":
            request.status = PublicRecordsRequestStatus.IN_PROGRESS
        elif decision == "partial":
            request.status = PublicRecordsRequestStatus.IN_PROGRESS

        await self._create_audit_log(
            request_id=request.id,
            action=PublicRecordsAuditAction.APPEAL_DECIDED,
            performed_by_id=recorded_by.id,
            details={
                "decision": decision,
                "notes": notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Reporting
    # =========================================================================

    async def get_disclosure_log(
        self,
        year: int,
        include_pending: bool = False,
    ) -> list[dict]:
        conditions = [
            extract("year", PublicRecordsRequest.date_received) == year,
        ]

        if not include_pending:
            completed_statuses = [
                PublicRecordsRequestStatus.COMPLETED,
                PublicRecordsRequestStatus.DENIED,
                PublicRecordsRequestStatus.PARTIALLY_DENIED,
                PublicRecordsRequestStatus.WITHDRAWN,
            ]
            conditions.append(PublicRecordsRequest.status.in_(completed_statuses))

        result = await self.db.execute(
            select(PublicRecordsRequest)
            .where(and_(*conditions))
            .order_by(PublicRecordsRequest.date_received)
        )
        requests = result.scalars().all()

        disclosure_log = []
        for req in requests:
            entry = {
                "tracking_number": req.tracking_number,
                "date_received": req.date_received.date().isoformat(),
                "request_type": str(req.request_type),
                "description_summary": req.description[:200] + "..." if len(req.description) > 200 else req.description,
                "requester_type": "Media" if req.is_media else ("Commercial" if req.is_commercial else "Public"),
                "status": str(req.status),
                "response_date": req.response_date.date().isoformat() if req.response_date else None,
                "records_provided": req.records_provided_count or 0,
                "records_withheld": req.records_withheld_count or 0,
                "exemptions_cited": req.exemptions_cited or [],
                "fees_charged": float(req.fee_paid) if req.fee_paid else 0,
                "fee_waived": req.fee_waived,
            }
            disclosure_log.append(entry)

        return disclosure_log

    async def get_statistics(self, year: int) -> dict:
        result = await self.db.execute(
            select(PublicRecordsRequest).where(
                extract("year", PublicRecordsRequest.date_received) == year
            )
        )
        requests = list(result.scalars().all())

        total = len(requests)
        completed = sum(1 for r in requests if r.status == PublicRecordsRequestStatus.COMPLETED)
        denied = sum(1 for r in requests if r.status == PublicRecordsRequestStatus.DENIED)
        partial = sum(1 for r in requests if r.status == PublicRecordsRequestStatus.PARTIALLY_DENIED)
        withdrawn = sum(1 for r in requests if r.status == PublicRecordsRequestStatus.WITHDRAWN)
        pending = total - completed - denied - partial - withdrawn
        appealed = sum(1 for r in requests if r.appeal_filed)

        # Calculate average response time
        response_times = []
        for r in requests:
            if r.response_date and r.date_received:
                delta = r.response_date.date() - r.date_received.date()
                response_times.append(delta.days)
        avg_response = sum(response_times) / len(response_times) if response_times else None

        # Requests by type
        by_type = {}
        for rt in PublicRecordsRequestType:
            count = sum(1 for r in requests if r.request_type == rt)
            if count > 0:
                by_type[rt.value] = count

        # Total fees
        total_fees = sum(float(r.fee_paid or 0) for r in requests)
        fees_waived = sum(1 for r in requests if r.fee_waived)

        return {
            "year": year,
            "total_requests": total,
            "completed": completed,
            "denied": denied,
            "partially_denied": partial,
            "withdrawn": withdrawn,
            "pending": pending,
            "appealed": appealed,
            "average_response_days": avg_response,
            "requests_by_type": by_type,
            "total_fees_collected": total_fees,
            "fee_waivers_granted": fees_waived,
        }

    async def get_overdue_requests(self) -> list[PublicRecordsRequest]:
        today = date.today()
        active_statuses = [
            PublicRecordsRequestStatus.RECEIVED,
            PublicRecordsRequestStatus.ACKNOWLEDGED,
            PublicRecordsRequestStatus.IN_PROGRESS,
            PublicRecordsRequestStatus.PENDING_CLARIFICATION,
            PublicRecordsRequestStatus.PENDING_FEE_PAYMENT,
            PublicRecordsRequestStatus.RECORDS_LOCATED,
            PublicRecordsRequestStatus.UNDER_REVIEW,
            PublicRecordsRequestStatus.REDACTION_IN_PROGRESS,
        ]

        result = await self.db.execute(
            select(PublicRecordsRequest)
            .options(selectinload(PublicRecordsRequest.assigned_to))
            .where(
                and_(
                    PublicRecordsRequest.status.in_(active_statuses),
                    or_(
                        and_(
                            PublicRecordsRequest.extended_deadline.isnot(None),
                            PublicRecordsRequest.extended_deadline < today,
                        ),
                        and_(
                            PublicRecordsRequest.extended_deadline.is_(None),
                            PublicRecordsRequest.response_deadline < today,
                        ),
                    ),
                )
            )
            .order_by(PublicRecordsRequest.response_deadline)
        )
        return list(result.scalars().all())

    # =========================================================================
    # Audit Log
    # =========================================================================

    async def get_audit_log(
        self, request_id: int, skip: int = 0, limit: int = 100
    ) -> list[PublicRecordsAuditLog]:
        result = await self.db.execute(
            select(PublicRecordsAuditLog)
            .options(selectinload(PublicRecordsAuditLog.performed_by))
            .where(PublicRecordsAuditLog.request_id == request_id)
            .order_by(PublicRecordsAuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_note(
        self,
        request_id: int,
        note: str,
        added_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicRecordsAuditLog:
        audit_log = await self._create_audit_log(
            request_id=request_id,
            action=PublicRecordsAuditAction.NOTE_ADDED,
            performed_by_id=added_by.id,
            details={"note": note},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()
        return audit_log

    # =========================================================================
    # Public Patron-Facing Methods
    # =========================================================================

    async def create_request_from_public_form(
        self,
        *,
        requester_name: str,
        requester_email: str,
        description: str,
        jurisdiction: JurisdictionType,
        preferred_format: str,
        meeting_id: Optional[int] = None,
        committee_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicRecordsRequest:
        return await self.create_request(
            request_type=PublicRecordsRequestType.STATE_OPEN_RECORDS,
            jurisdiction=jurisdiction,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_phone=None,
            requester_organization=None,
            requester_address=None,
            is_media=False,
            is_commercial=False,
            date_received=datetime.now(timezone.utc),
            description=description,
            records_date_range_start=None,
            records_date_range_end=None,
            preferred_format=preferred_format,
            created_by=None,
            ip_address=ip_address,
            user_agent=user_agent,
            meeting_id=meeting_id,
            committee_id=committee_id,
            submitted_via="public_form",
        )

    async def get_disclosure_log_public(
        self, year: int
    ) -> list[PublicRecordsRequest]:
        stmt = (
            select(PublicRecordsRequest)
            .where(
                PublicRecordsRequest.date_received >= datetime(year, 1, 1, tzinfo=timezone.utc),
                PublicRecordsRequest.date_received < datetime(year + 1, 1, 1, tzinfo=timezone.utc),
                or_(
                    PublicRecordsRequest.status
                    == PublicRecordsRequestStatus.COMPLETED,
                    PublicRecordsRequest.status
                    == PublicRecordsRequestStatus.DENIED,
                    PublicRecordsRequest.status
                    == PublicRecordsRequestStatus.PARTIALLY_DENIED,
                ),
            )
            .order_by(PublicRecordsRequest.date_received.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars())

    # =========================================================================
    # Helper Methods
    # =========================================================================


    async def _generate_tracking_number(self) -> str:
        year = datetime.now().year
        while True:
            random_part = secrets.token_hex(3).upper()
            tracking = f"PRR-{year}-{random_part}"

            result = await self.db.execute(
                select(PublicRecordsRequest).where(
                    PublicRecordsRequest.tracking_number == tracking
                )
            )
            if not result.scalar_one_or_none():
                return tracking

    async def _get_request_for_update(
        self, request_id: int
    ) -> Optional[PublicRecordsRequest]:
        result = await self.db.execute(
            select(PublicRecordsRequest).where(
                PublicRecordsRequest.id == request_id
            )
        )
        return result.scalar_one_or_none()

    async def _create_audit_log(
        self,
        request_id: int,
        action: PublicRecordsAuditAction,
        performed_by_id: int,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PublicRecordsAuditLog:
        audit_log = PublicRecordsAuditLog(
            request_id=request_id,
            action=action,
            performed_by_id=performed_by_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log
