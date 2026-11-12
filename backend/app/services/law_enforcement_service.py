# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.circulation import Checkout, Hold
from ..models.event_registration import EventRegistration
from ..models.favorite import Favorite
from ..models.fine import Fine
from ..models.law_enforcement_request import (
    DEFAULT_CHECKLIST_ITEMS,
    AuditActionType,
    ChecklistItemType,
    LawEnforcementAuditLog,
    LawEnforcementChecklist,
    LawEnforcementRequest,
    LawEnforcementResponseTemplate,
    LegalReviewStatus,
    RequestType,
    WorkflowStatus,
)
from ..models.privacy_ledger import DataSharingLog, DataSharingPurpose
from ..models.reading import ReadingLog
from ..models.user import User
from ..schemas.law_enforcement_request import (
    LawEnforcementRequestCreate,
    LawEnforcementRequestUpdate,
    LegalReviewUpdate,
    PatronDataExportRequest,
    PatronDataExportResponse,
    ResponseUpdate,
    TransparencyReport,
    TransparencyReportDetail,
    TransparencyReportSummary,
    WorkflowStatusUpdate,
)

logger = get_logger(__name__)


class LawEnforcementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Request Management
    # =========================================================================

    async def create_request(
        self,
        data: LawEnforcementRequestCreate,
        created_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LawEnforcementRequest:
        # Generate unique tracking number
        tracking_number = await self._generate_tracking_number()

        # Create the request
        request = LawEnforcementRequest(
            tracking_number=tracking_number,
            requesting_agency=data.requesting_agency,
            agency_contact_name=data.agency_contact_name,
            agency_contact_phone=data.agency_contact_phone,
            agency_contact_email=data.agency_contact_email,
            agency_case_number=data.agency_case_number,
            request_type=data.request_type,
            date_received=data.date_received,
            date_due=data.date_due,
            patron_id=data.patron_id,
            patron_name_on_request=data.patron_name_on_request,
            patron_identifiers=data.patron_identifiers,
            data_requested=data.data_requested,
            data_date_range_start=data.data_date_range_start,
            data_date_range_end=data.data_date_range_end,
            patron_notification_permitted=data.patron_notification_permitted,
            gag_order_until=data.gag_order_until,
            internal_notes=data.internal_notes,
            workflow_status=WorkflowStatus.RECEIVED,
            legal_review_status=LegalReviewStatus.PENDING_REVIEW,
            created_by_id=created_by.id,
        )

        self.db.add(request)
        await self.db.flush()  # Get the ID

        # Create default checklist items
        await self._create_checklist_items(request.id, data.request_type)

        # Mark first checklist item as complete
        await self._complete_checklist_item(
            request.id,
            ChecklistItemType.RECEIVE_REQUEST,
            created_by.id,
            notes="Request logged into system",
        )

        # Create audit log entry
        await self._create_audit_log(
            request_id=request.id,
            action=AuditActionType.REQUEST_CREATED,
            performed_by_id=created_by.id,
            details={
                "tracking_number": tracking_number,
                "request_type": str(data.request_type),
                "requesting_agency": data.requesting_agency,
                "patron_id": data.patron_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        logger.info(
            f"Law enforcement request created: {tracking_number}",
            extra={
                "tracking_number": tracking_number,
                "request_type": str(data.request_type),
                "created_by": created_by.id,
            },
        )

        return request

    async def get_request(
        self,
        request_id: int,
        viewer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest)
            .options(
                selectinload(LawEnforcementRequest.patron),
                selectinload(LawEnforcementRequest.checklist_items),
            )
            .where(LawEnforcementRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if request:
            # Log the view
            await self._create_audit_log(
                request_id=request.id,
                action=AuditActionType.VIEWED,
                performed_by_id=viewer.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()

        return request

    async def get_request_by_tracking(
        self, tracking_number: str
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest)
            .options(
                selectinload(LawEnforcementRequest.patron),
                selectinload(LawEnforcementRequest.checklist_items),
            )
            .where(LawEnforcementRequest.tracking_number == tracking_number)
        )
        return result.scalar_one_or_none()

    async def update_request(
        self,
        request_id: int,
        data: LawEnforcementRequestUpdate,
        updated_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()

        if not request:
            return None

        # Track changes for audit log
        changes = {}
        update_data = data.model_dump(exclude_unset=True)

        for field, new_value in update_data.items():
            old_value = getattr(request, field)
            if old_value != new_value:
                changes[field] = {"old": str(old_value), "new": str(new_value)}
                setattr(request, field, new_value)

        if changes:
            await self._create_audit_log(
                request_id=request.id,
                action=AuditActionType.REQUEST_UPDATED,
                performed_by_id=updated_by.id,
                details={"changes": changes},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def list_requests(
        self,
        skip: int = 0,
        limit: int = 50,
        request_type: Optional[RequestType] = None,
        workflow_status: Optional[WorkflowStatus] = None,
        legal_review_status: Optional[LegalReviewStatus] = None,
        year: Optional[int] = None,
        patron_id: Optional[int] = None,
    ) -> tuple[list[LawEnforcementRequest], int]:
        query = select(LawEnforcementRequest)
        count_query = select(func.count(LawEnforcementRequest.id))

        # Apply filters
        conditions = []
        if request_type:
            conditions.append(LawEnforcementRequest.request_type == request_type)
        if workflow_status:
            conditions.append(LawEnforcementRequest.workflow_status == workflow_status)
        if legal_review_status:
            conditions.append(
                LawEnforcementRequest.legal_review_status == legal_review_status
            )
        if year:
            conditions.append(
                extract("year", LawEnforcementRequest.date_received) == year
            )
        if patron_id:
            conditions.append(LawEnforcementRequest.patron_id == patron_id)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = (
            query.options(selectinload(LawEnforcementRequest.patron))
            .order_by(LawEnforcementRequest.date_received.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        requests = list(result.scalars().all())

        return requests, total

    # =========================================================================
    # Legal Review
    # =========================================================================

    async def update_legal_review(
        self,
        request_id: int,
        data: LegalReviewUpdate,
        reviewer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()

        if not request:
            return None

        old_status = request.legal_review_status
        request.legal_review_status = data.legal_review_status
        request.legal_reviewer_id = reviewer.id
        request.legal_review_date = datetime.now(timezone.utc)
        if data.legal_review_notes:
            request.legal_review_notes = data.legal_review_notes

        # Update workflow status based on legal review outcome
        if data.legal_review_status == LegalReviewStatus.APPROVED:
            request.workflow_status = WorkflowStatus.PATRON_NOTIFICATION
            # Complete legal review checklist item
            await self._complete_checklist_item(
                request_id,
                ChecklistItemType.LEGAL_REVIEW,
                reviewer.id,
                notes=f"Approved: {data.legal_review_notes or 'No notes'}",
            )
        elif data.legal_review_status == LegalReviewStatus.REJECTED:
            request.workflow_status = WorkflowStatus.REJECTED
            await self._complete_checklist_item(
                request_id,
                ChecklistItemType.LEGAL_REVIEW,
                reviewer.id,
                notes=f"Rejected: {data.legal_review_notes or 'No notes'}",
            )
        elif data.legal_review_status == LegalReviewStatus.UNDER_REVIEW:
            request.workflow_status = WorkflowStatus.LEGAL_REVIEW

        await self._create_audit_log(
            request_id=request.id,
            action=AuditActionType.LEGAL_REVIEW_UPDATED,
            performed_by_id=reviewer.id,
            details={
                "old_status": old_status.value,
                "new_status": str(data.legal_review_status),
                "notes": data.legal_review_notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Workflow Management
    # =========================================================================

    async def update_workflow_status(
        self,
        request_id: int,
        data: WorkflowStatusUpdate,
        updated_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()

        if not request:
            return None

        old_status = request.workflow_status
        request.workflow_status = data.workflow_status

        await self._create_audit_log(
            request_id=request.id,
            action=AuditActionType.STATUS_CHANGED,
            performed_by_id=updated_by.id,
            details={
                "old_status": old_status.value,
                "new_status": str(data.workflow_status),
                "notes": data.notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def get_checklist(
        self, request_id: int
    ) -> list[LawEnforcementChecklist]:
        result = await self.db.execute(
            select(LawEnforcementChecklist)
            .where(LawEnforcementChecklist.request_id == request_id)
            .order_by(LawEnforcementChecklist.sort_order)
        )
        return list(result.scalars().all())

    async def update_checklist_item(
        self,
        request_id: int,
        item_type: ChecklistItemType,
        is_completed: bool,
        updated_by: User,
        completion_notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementChecklist]:
        result = await self.db.execute(
            select(LawEnforcementChecklist).where(
                and_(
                    LawEnforcementChecklist.request_id == request_id,
                    LawEnforcementChecklist.item_type == item_type,
                )
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            return None

        old_completed = item.is_completed
        item.is_completed = is_completed

        if is_completed:
            item.completed_by_id = updated_by.id
            item.completed_at = datetime.now(timezone.utc)
            if completion_notes:
                item.completion_notes = completion_notes
        else:
            item.completed_by_id = None
            item.completed_at = None
            item.completion_notes = None

        await self._create_audit_log(
            request_id=request_id,
            action=AuditActionType.CHECKLIST_UPDATED,
            performed_by_id=updated_by.id,
            details={
                "item_type": item_type.value,
                "was_completed": old_completed,
                "is_completed": is_completed,
                "notes": completion_notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def get_checklist_progress(self, request_id: int) -> dict:
        result = await self.db.execute(
            select(LawEnforcementChecklist).where(
                and_(
                    LawEnforcementChecklist.request_id == request_id,
                    LawEnforcementChecklist.is_applicable == True,
                )
            )
        )
        items = result.scalars().all()

        total = len(items)
        completed = sum(1 for item in items if item.is_completed)
        percent = (completed / total * 100) if total > 0 else 0

        return {
            "completed": completed,
            "total": total,
            "percent": round(percent, 1),
        }

    # =========================================================================
    # Response and Compliance
    # =========================================================================

    async def record_response(
        self,
        request_id: int,
        data: ResponseUpdate,
        responded_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()

        if not request:
            return None

        request.response_date = datetime.now(timezone.utc)
        request.responding_staff_id = responded_by.id
        request.response_method = data.response_method
        request.response_summary = data.response_summary
        request.data_provided_summary = data.data_provided_summary
        request.workflow_status = WorkflowStatus.RESPONSE_SENT

        # Complete related checklist items
        await self._complete_checklist_item(
            request_id,
            ChecklistItemType.SEND_RESPONSE,
            responded_by.id,
            notes=f"Response sent via {data.response_method}",
        )

        await self._create_audit_log(
            request_id=request.id,
            action=AuditActionType.RESPONSE_SENT,
            performed_by_id=responded_by.id,
            details={
                "response_method": data.response_method,
                "response_summary": data.response_summary,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    async def record_patron_notification(
        self,
        request_id: int,
        notification_method: str,
        notified_by: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        request = result.scalar_one_or_none()

        if not request:
            return None

        if not request.patron_notification_permitted:
            raise ValueError("Patron notification is not permitted for this request")

        request.patron_notification_date = datetime.now(timezone.utc)
        request.patron_notification_method = notification_method

        await self._complete_checklist_item(
            request_id,
            ChecklistItemType.NOTIFY_PATRON,
            notified_by.id,
            notes=notes or f"Notified via {notification_method}",
        )

        await self._create_audit_log(
            request_id=request.id,
            action=AuditActionType.PATRON_NOTIFIED,
            performed_by_id=notified_by.id,
            details={
                "notification_method": notification_method,
                "notes": notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()
        await self.db.refresh(request)

        return request

    # =========================================================================
    # Data Export
    # =========================================================================

    async def export_patron_data(
        self,
        export_request: PatronDataExportRequest,
        exported_by: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PatronDataExportResponse:
        # Verify the law enforcement request exists
        le_request = await self.get_request_by_tracking_id(export_request.request_id)
        if not le_request:
            raise ValueError("Law enforcement request not found")

        if not le_request.patron_id:
            raise ValueError("No patron associated with this request")

        # Get patron
        patron_result = await self.db.execute(
            select(User).where(User.id == le_request.patron_id)
        )
        patron = patron_result.scalar_one_or_none()

        if not patron:
            raise ValueError("Patron not found")

        exported_data = PatronDataExportResponse(
            request_id=export_request.request_id,
            patron_id=patron.id,
            exported_at=datetime.now(timezone.utc),
            data_categories_included=[],
        )

        # Build date range filter
        date_start = export_request.date_range_start or le_request.data_date_range_start
        date_end = export_request.date_range_end or le_request.data_date_range_end

        # Export profile
        if export_request.include_profile:
            exported_data.data_categories_included.append("profile")
            exported_data.profile = {
                "id": patron.id,
                "first_name": patron.first_name,
                "last_name": patron.last_name,
                "email": patron.email,
                "phone": patron.phone,
                "address": patron.address,
                "library_card": patron.library_card,
                "date_of_birth": patron.date_of_birth.isoformat()
                if patron.date_of_birth
                else None,
                "created_at": patron.created_at.isoformat()
                if patron.created_at
                else None,
            }

        # Export checkouts
        if export_request.include_checkouts:
            exported_data.data_categories_included.append("checkouts")
            checkout_query = select(Checkout).where(Checkout.user_id == patron.id)
            if date_start:
                checkout_query = checkout_query.where(
                    Checkout.checked_out_at >= date_start
                )
            if date_end:
                checkout_query = checkout_query.where(
                    Checkout.checked_out_at <= date_end
                )

            checkout_result = await self.db.execute(checkout_query)
            exported_data.checkouts = [
                {
                    "id": c.id,
                    "item_id": c.item_id,
                    "status": str(c.status),
                    "checked_out_at": c.checked_out_at.isoformat()
                    if c.checked_out_at
                    else None,
                    "due_date": c.due_date.isoformat() if c.due_date else None,
                    "returned_at": c.returned_at.isoformat()
                    if c.returned_at
                    else None,
                }
                for c in checkout_result.scalars().all()
            ]

        # Export holds
        if export_request.include_holds:
            exported_data.data_categories_included.append("holds")
            hold_query = select(Hold).where(Hold.user_id == patron.id)
            if date_start:
                hold_query = hold_query.where(Hold.created_at >= date_start)
            if date_end:
                hold_query = hold_query.where(Hold.created_at <= date_end)

            hold_result = await self.db.execute(hold_query)
            exported_data.holds = [
                {
                    "id": h.id,
                    "item_id": h.item_id,
                    "status": str(h.status),
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in hold_result.scalars().all()
            ]

        # Export fines
        if export_request.include_fines:
            exported_data.data_categories_included.append("fines")
            fine_query = select(Fine).where(Fine.user_id == patron.id)
            if date_start:
                fine_query = fine_query.where(Fine.created_at >= date_start)
            if date_end:
                fine_query = fine_query.where(Fine.created_at <= date_end)

            fine_result = await self.db.execute(fine_query)
            exported_data.fines = [
                {
                    "id": f.id,
                    "amount": str(f.amount),
                    "amount_paid": str(f.amount_paid),
                    "status": str(f.status),
                    "fine_type": str(f.fine_type),
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in fine_result.scalars().all()
            ]

        # Export reading history (only if explicitly requested and patron tracks it)
        if export_request.include_reading_history and patron.track_reading_history:
            exported_data.data_categories_included.append("reading_history")
            reading_query = select(ReadingLog).where(ReadingLog.user_id == patron.id)
            if date_start:
                reading_query = reading_query.where(
                    ReadingLog.reading_date >= date_start.date()
                )
            if date_end:
                reading_query = reading_query.where(
                    ReadingLog.reading_date <= date_end.date()
                )

            reading_result = await self.db.execute(reading_query)
            exported_data.reading_history = [
                {
                    "id": r.id,
                    "book_title": r.book_title,
                    "book_author": r.book_author,
                    "reading_date": r.reading_date.isoformat()
                    if r.reading_date
                    else None,
                    "minutes": r.minutes,
                }
                for r in reading_result.scalars().all()
            ]

        # Log the export
        await self._create_audit_log(
            request_id=export_request.request_id,
            action=AuditActionType.DATA_EXPORTED,
            performed_by_id=exported_by.id,
            details={
                "patron_id": patron.id,
                "categories_exported": exported_data.data_categories_included,
                "date_range_start": date_start.isoformat() if date_start else None,
                "date_range_end": date_end.isoformat() if date_end else None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Auto-log to DataSharingLog for privacy compliance ("who have you shared my data with?")
        sharing_log = DataSharingLog(
            user_id=patron.id,
            recipient_name=le_request.requesting_agency,
            recipient_type="law_enforcement",
            purpose=DataSharingPurpose.LAW_ENFORCEMENT_REQUEST,
            data_categories=exported_data.data_categories_included,
            legal_basis=str(le_request.request_type),
            reference_id=str(le_request.id),
            reference_type="law_enforcement_request",
            patron_notified=le_request.patron_notification_date is not None,
            patron_notified_at=le_request.patron_notification_date,
            shared_by_staff_id=exported_by.id,
            notes=f"Data exported for law enforcement request {le_request.tracking_number}",
        )
        self.db.add(sharing_log)

        await self.db.commit()

        return exported_data

    async def get_request_by_tracking_id(
        self, request_id: int
    ) -> Optional[LawEnforcementRequest]:
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                LawEnforcementRequest.id == request_id
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Audit Log
    # =========================================================================

    async def get_audit_log(
        self, request_id: int, skip: int = 0, limit: int = 100
    ) -> list[LawEnforcementAuditLog]:
        result = await self.db.execute(
            select(LawEnforcementAuditLog)
            .options(selectinload(LawEnforcementAuditLog.performed_by))
            .where(LawEnforcementAuditLog.request_id == request_id)
            .order_by(LawEnforcementAuditLog.created_at.desc())
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
    ) -> LawEnforcementAuditLog:
        audit_log = await self._create_audit_log(
            request_id=request_id,
            action=AuditActionType.NOTE_ADDED,
            performed_by_id=added_by.id,
            details={"note": note},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()
        return audit_log

    # =========================================================================
    # Transparency Reporting
    # =========================================================================

    async def generate_transparency_report(
        self, year: int, include_details: bool = False
    ) -> TransparencyReport:
        # Get all requests for the year
        result = await self.db.execute(
            select(LawEnforcementRequest).where(
                extract("year", LawEnforcementRequest.date_received) == year
            )
        )
        requests = list(result.scalars().all())

        # Calculate statistics
        total_requests = len(requests)

        # Requests by type
        requests_by_type = {}
        for rt in RequestType:
            count = sum(1 for r in requests if r.request_type == rt)
            if count > 0:
                requests_by_type[rt.value] = count

        # Requests by workflow status
        requests_by_status = {}
        for ws in WorkflowStatus:
            count = sum(1 for r in requests if r.workflow_status == ws)
            if count > 0:
                requests_by_status[ws.value] = count

        # Requests by legal review outcome
        requests_by_legal_outcome = {}
        for ls in LegalReviewStatus:
            count = sum(1 for r in requests if r.legal_review_status == ls)
            if count > 0:
                requests_by_legal_outcome[ls.value] = count

        # Calculate average response time
        response_times = []
        for r in requests:
            if r.response_date and r.date_received:
                delta = r.response_date - r.date_received
                response_times.append(delta.days)
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )

        # Patron notification stats
        requests_with_notification = sum(
            1 for r in requests if r.patron_notification_date is not None
        )
        requests_with_gag_order = sum(
            1 for r in requests if r.gag_order_until is not None
        )

        # Compliance stats
        requests_fully_complied = sum(
            1
            for r in requests
            if r.workflow_status == WorkflowStatus.COMPLETED
            and r.legal_review_status == LegalReviewStatus.APPROVED
        )
        requests_partially_complied = sum(
            1
            for r in requests
            if r.workflow_status == WorkflowStatus.RESPONSE_SENT
            and r.legal_review_status == LegalReviewStatus.REQUIRES_MODIFICATION
        )
        requests_rejected = sum(
            1 for r in requests if r.workflow_status == WorkflowStatus.REJECTED
        )
        requests_withdrawn = sum(
            1 for r in requests if r.workflow_status == WorkflowStatus.WITHDRAWN
        )

        # Unique patrons affected
        unique_patrons = len(set(r.patron_id for r in requests if r.patron_id))

        summary = TransparencyReportSummary(
            year=year,
            total_requests=total_requests,
            requests_by_type=requests_by_type,
            requests_by_status=requests_by_status,
            requests_by_legal_outcome=requests_by_legal_outcome,
            average_response_time_days=avg_response_time,
            requests_with_patron_notification=requests_with_notification,
            requests_with_gag_order=requests_with_gag_order,
            requests_fully_complied=requests_fully_complied,
            requests_partially_complied=requests_partially_complied,
            requests_rejected=requests_rejected,
            requests_withdrawn=requests_withdrawn,
            unique_patrons_affected=unique_patrons,
        )

        details = None
        if include_details:
            details = [
                TransparencyReportDetail(
                    tracking_number=r.tracking_number,
                    request_type=r.request_type,
                    requesting_agency=r.requesting_agency,
                    date_received=r.date_received,
                    response_date=r.response_date,
                    legal_outcome=r.legal_review_status,
                    workflow_status=r.workflow_status,
                    patron_notified=r.patron_notification_date is not None,
                    data_types_provided=r.data_provided_summary,
                )
                for r in requests
            ]

        return TransparencyReport(
            report_generated_at=datetime.now(timezone.utc),
            summary=summary,
            details=details,
        )

    # =========================================================================
    # Response Templates
    # =========================================================================

    async def get_templates(
        self,
        template_type: Optional[str] = None,
        active_only: bool = True,
    ) -> list[LawEnforcementResponseTemplate]:
        query = select(LawEnforcementResponseTemplate)

        if template_type:
            query = query.where(
                LawEnforcementResponseTemplate.template_type == template_type
            )
        if active_only:
            query = query.where(LawEnforcementResponseTemplate.is_active == True)

        query = query.order_by(LawEnforcementResponseTemplate.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_template(
        self, template_id: int
    ) -> Optional[LawEnforcementResponseTemplate]:
        result = await self.db.execute(
            select(LawEnforcementResponseTemplate).where(
                LawEnforcementResponseTemplate.id == template_id
            )
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        name: str,
        description: Optional[str],
        template_type: str,
        body_template: str,
        subject_template: Optional[str] = None,
        applicable_request_types: Optional[list[str]] = None,
        created_by: Optional[User] = None,
    ) -> LawEnforcementResponseTemplate:
        template = LawEnforcementResponseTemplate(
            name=name,
            description=description,
            template_type=template_type,
            body_template=body_template,
            subject_template=subject_template,
            applicable_request_types=applicable_request_types,
            created_by_id=created_by.id if created_by else None,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def render_template(
        self, template_id: int, request_id: int
    ) -> dict[str, Optional[str]]:
        template = await self.get_template(template_id)
        if not template:
            raise ValueError("Template not found")

        request = await self.get_request_by_tracking_id(request_id)
        if not request:
            raise ValueError("Request not found")

        # Build placeholder values
        placeholders = {
            "tracking_number": request.tracking_number,
            "agency_name": request.requesting_agency,
            "agency_contact": request.agency_contact_name or "",
            "agency_case_number": request.agency_case_number or "",
            "date_received": request.date_received.strftime("%B %d, %Y"),
            "date_today": datetime.now().strftime("%B %d, %Y"),
            "patron_name": request.patron_name_on_request or "",
            "request_type": str(request.request_type).replace("_", " ").title(),
            "data_requested": request.data_requested,
            "library_name": os.environ.get("LIBRARY_NAME", "My Library"),
        }

        # Add patron details if available
        if request.patron:
            placeholders["patron_full_name"] = (
                f"{request.patron.first_name} {request.patron.last_name}"
            )
            placeholders["patron_library_card"] = request.patron.library_card or ""

        # Render template
        subject = template.subject_template
        body = template.body_template

        for key, value in placeholders.items():
            placeholder = "{{" + key + "}}"
            if subject:
                subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return {"subject": subject, "body": body}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _generate_tracking_number(self) -> str:
        year = datetime.now().year
        while True:
            # Format: LE-YYYY-XXXXXX (random alphanumeric)
            random_part = secrets.token_hex(3).upper()
            tracking = f"LE-{year}-{random_part}"

            # Check uniqueness
            result = await self.db.execute(
                select(LawEnforcementRequest).where(
                    LawEnforcementRequest.tracking_number == tracking
                )
            )
            if not result.scalar_one_or_none():
                return tracking

    async def _create_checklist_items(
        self, request_id: int, request_type: RequestType
    ) -> None:
        for item_data in DEFAULT_CHECKLIST_ITEMS:
            # Adjust applicability based on request type
            is_applicable = item_data["is_required"]

            # Patron notification may not be applicable for NSLs
            if item_data["item_type"] == ChecklistItemType.NOTIFY_PATRON:
                if request_type == RequestType.NATIONAL_SECURITY_LETTER:
                    is_applicable = False

            item = LawEnforcementChecklist(
                request_id=request_id,
                item_type=item_data["item_type"],
                item_description=item_data["item_description"],
                is_required=item_data["is_required"],
                is_applicable=is_applicable,
                sort_order=item_data["sort_order"],
            )
            self.db.add(item)

    async def _complete_checklist_item(
        self,
        request_id: int,
        item_type: ChecklistItemType,
        completed_by_id: int,
        notes: Optional[str] = None,
    ) -> None:
        result = await self.db.execute(
            select(LawEnforcementChecklist).where(
                and_(
                    LawEnforcementChecklist.request_id == request_id,
                    LawEnforcementChecklist.item_type == item_type,
                )
            )
        )
        item = result.scalar_one_or_none()

        if item:
            item.is_completed = True
            item.completed_by_id = completed_by_id
            item.completed_at = datetime.now(timezone.utc)
            if notes:
                item.completion_notes = notes

    async def _create_audit_log(
        self,
        request_id: int,
        action: AuditActionType,
        performed_by_id: int,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LawEnforcementAuditLog:
        audit_log = LawEnforcementAuditLog(
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
