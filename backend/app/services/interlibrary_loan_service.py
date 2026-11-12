# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.catalog import CatalogItem
from app.models.interlibrary_loan import (
    ILLCostCategory,
    ILLCostRecord,
    ILLRequest,
    ILLRequestStatus,
    ILLRequestType,
    ILLTrackingUpdate,
    PartnerLibrary,
    PartnerLibraryStatus,
    ShippingMethod,
)
from app.models.multi_branch import Branch
from app.models.user import User

logger = get_logger(__name__)


# Human-readable status labels
STATUS_LABELS: dict[ILLRequestStatus, str] = {
    ILLRequestStatus.pending: "Request submitted",
    ILLRequestStatus.searching: "Searching partner libraries",
    ILLRequestStatus.located: "Item located at partner library",
    ILLRequestStatus.not_found: "Item not found at partner libraries",
    ILLRequestStatus.submitted: "Request sent to lending library",
    ILLRequestStatus.approved: "Request approved by lending library",
    ILLRequestStatus.denied: "Request denied by lending library",
    ILLRequestStatus.in_transit: "Item in transit to our library",
    ILLRequestStatus.received: "Item received — ready for pickup",
    ILLRequestStatus.checked_out: "Checked out to you",
    ILLRequestStatus.returned: "Returned — being shipped back",
    ILLRequestStatus.return_in_transit: "Return shipment in progress",
    ILLRequestStatus.completed: "Completed",
    ILLRequestStatus.cancelled: "Cancelled",
    ILLRequestStatus.lost: "Lost",
}


VALID_TRANSITIONS = {
    "pending": ["searching", "cancelled"],
    "searching": ["located", "not_found", "cancelled"],
    "located": ["submitted", "cancelled"],
    "submitted": ["approved", "denied", "cancelled"],
    "approved": ["in_transit"],
    "denied": ["searching"],
    "not_found": ["searching"],
    "in_transit": ["received"],
    "received": ["checked_out"],
    "checked_out": ["returned", "lost"],
    "returned": ["return_in_transit"],
    "return_in_transit": ["completed"],
    "completed": [],
    "cancelled": [],
    "lost": [],
}


class InterlibraryLoanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # PARTNER LIBRARY MANAGEMENT
    # =========================================================================

    async def create_partner_library(self, **kwargs) -> PartnerLibrary:
        partner = PartnerLibrary(**kwargs)
        try:
            self.db.add(partner)
            await self.db.flush()
            await self.db.refresh(partner)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409, detail="Partner library with this code already exists"
            ) from None
        return partner

    async def update_partner_library(
        self, partner_id: int, updates: dict[str, Any]
    ) -> PartnerLibrary | None:
        result = await self.db.execute(
            select(PartnerLibrary).where(PartnerLibrary.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        if not partner:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(partner, key, value)
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

    async def get_partner_library(self, partner_id: int) -> PartnerLibrary | None:
        result = await self.db.execute(
            select(PartnerLibrary).where(PartnerLibrary.id == partner_id)
        )
        return result.scalar_one_or_none()

    async def list_partner_libraries(
        self,
        status: PartnerLibraryStatus | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PartnerLibrary]:
        query = select(PartnerLibrary)
        if status:
            query = query.where(PartnerLibrary.status == status)
        if search:
            safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                or_(
                    PartnerLibrary.name.ilike(f"%{safe_search}%"),
                    PartnerLibrary.code.ilike(f"%{safe_search}%"),
                    PartnerLibrary.city.ilike(f"%{safe_search}%"),
                )
            )
        query = query.order_by(PartnerLibrary.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # ILL REQUEST LIFECYCLE
    # =========================================================================

    async def create_request(
        self,
        patron_id: int,
        request_type: ILLRequestType = ILLRequestType.borrow,
        staff_id: int | None = None,
        **kwargs,
    ) -> ILLRequest:
        ill_request = ILLRequest(
            patron_id=patron_id,
            staff_id=staff_id,
            request_type=request_type,
            status=ILLRequestStatus.pending,
            **kwargs,
        )
        self.db.add(ill_request)
        await self.db.flush()
        await self.db.refresh(ill_request)

        # Create initial tracking update
        await self._add_tracking_update(
            ill_request.id,
            ILLRequestStatus.pending,
            "Your interlibrary loan request has been submitted.",
            created_by_id=staff_id,
        )

        logger.info(
            "ILL request created: id=%d patron=%d type=%s title=%s",
            ill_request.id,
            patron_id,
            request_type.value,
            kwargs.get("title", ""),
        )
        return ill_request

    async def get_request(self, request_id: int) -> ILLRequest | None:
        result = await self.db.execute(
            select(ILLRequest)
            .options(
                joinedload(ILLRequest.partner_library),
                selectinload(ILLRequest.tracking_updates),
                selectinload(ILLRequest.cost_records),
            )
            .where(ILLRequest.id == request_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_requests(
        self,
        patron_id: int | None = None,
        partner_library_id: int | None = None,
        request_type: ILLRequestType | None = None,
        status: ILLRequestStatus | None = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ILLRequest]:
        query = select(ILLRequest).options(joinedload(ILLRequest.partner_library))

        if patron_id is not None:
            query = query.where(ILLRequest.patron_id == patron_id)
        if partner_library_id is not None:
            query = query.where(ILLRequest.partner_library_id == partner_library_id)
        if request_type is not None:
            query = query.where(ILLRequest.request_type == request_type)
        if status is not None:
            query = query.where(ILLRequest.status == status)
        if active_only:
            terminal = {
                ILLRequestStatus.completed,
                ILLRequestStatus.cancelled,
                ILLRequestStatus.not_found,
                ILLRequestStatus.denied,
                ILLRequestStatus.lost,
            }
            query = query.where(ILLRequest.status.notin_(terminal))

        query = query.order_by(ILLRequest.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.unique().scalars().all())

    async def update_request(
        self,
        request_id: int,
        staff_id: int,
        updates: dict[str, Any],
        tracking_message: str | None = None,
    ) -> ILLRequest | None:
        ill_request = await self.get_request(request_id)
        if not ill_request:
            return None

        old_status = ill_request.status
        new_status = updates.get("status")

        # Validate status transition
        if new_status and new_status != old_status:
            current_status = old_status.value if hasattr(old_status, "value") else str(old_status)
            new_status_str = new_status.value if hasattr(new_status, "value") else str(new_status)
            allowed = VALID_TRANSITIONS.get(current_status, [])
            if new_status_str not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot transition from '{current_status}' to '{new_status_str}'. Allowed transitions: {allowed}",
                )

        for key, value in updates.items():
            if value is not None:
                setattr(ill_request, key, value)

        # Auto-set date fields based on status changes
        now = datetime.now(timezone.utc)
        if new_status and new_status != old_status:
            self._apply_status_dates(ill_request, new_status, now)

        await self.db.flush()
        await self.db.refresh(ill_request)

        # Add tracking update
        if new_status and new_status != old_status:
            message = tracking_message or STATUS_LABELS.get(
                new_status, f"Status updated to {new_status.value}"
            )
            await self._add_tracking_update(request_id, new_status, message, created_by_id=staff_id)

        return ill_request

    async def cancel_request(
        self, request_id: int, cancelled_by_id: int, reason: str = "Cancelled by user"
    ) -> ILLRequest | None:
        cancellable = {
            ILLRequestStatus.pending,
            ILLRequestStatus.searching,
            ILLRequestStatus.located,
            ILLRequestStatus.submitted,
        }
        ill_request = await self.get_request(request_id)
        if not ill_request or ill_request.status not in cancellable:
            return None

        ill_request.status = ILLRequestStatus.cancelled
        await self.db.flush()
        await self._add_tracking_update(
            request_id, ILLRequestStatus.cancelled, reason, created_by_id=cancelled_by_id
        )
        return ill_request

    async def renew_request(self, request_id: int, staff_id: int) -> ILLRequest | None:
        ill_request = await self.get_request(request_id)
        if not ill_request:
            return None
        if ill_request.status != ILLRequestStatus.checked_out:
            return None
        if ill_request.renewal_count >= ill_request.max_renewals:
            return None

        # Extend by partner's loan period (default 21 days)
        partner = ill_request.partner_library
        extension_days = partner.max_loan_days if partner else 21
        old_due = ill_request.due_date or date.today()
        new_due = old_due + timedelta(days=extension_days)

        ill_request.due_date = new_due
        ill_request.renewal_count += 1
        await self.db.flush()

        await self._add_tracking_update(
            request_id,
            ILLRequestStatus.checked_out,
            f"Renewal approved. New due date: {new_due.isoformat()}",
            created_by_id=staff_id,
        )
        return ill_request

    # =========================================================================
    # AUTO-SEARCH PARTNER LIBRARIES
    # =========================================================================

    async def search_partner_catalogs(
        self, title: str, author: str | None = None, isbn: str | None = None
    ) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(PartnerLibrary).where(PartnerLibrary.status == PartnerLibraryStatus.active)
        )
        partners = list(result.scalars().all())

        # Try federated search for real catalog lookups
        federated_results = []
        try:
            from app.services.federated_search import FederatedSearchService

            fed_service = FederatedSearchService(
                db=self.db,
                include_local=False,
                source_timeout=10.0,
                overall_timeout=20.0,
            )
            fed_response = await fed_service.search(
                title=title,
                author=author,
                isbn=isbn,
                max_results_per_source=5,
            )
            federated_results = fed_response.results
            logger.info(
                "Federated search for ILL: title=%s found=%d results from %d sources",
                title,
                fed_response.total_results,
                fed_response.sources_succeeded,
            )
        except Exception as e:  # noqa: BLE001 -- federated search optional: fall back to local partners on any failure
            logger.warning("Federated search unavailable for ILL, using fallback: %s", e)

        # Build partner results — enrich with federated search data if available
        search_results = []
        for partner in partners:
            # An active ILL partner is a candidate by definition: we hold an
            # agreement with them and THEY confirm or decline holdings. Federated
            # search cannot tell us whether a given partner holds a title -- it
            # only ever said "some source somewhere returned something" -- so
            # gating availability on it meant a slow or empty federated response
            # marked every partner unavailable and dropped the request into
            # not_found. Federated results now only enrich the call number.
            partner_available = True
            call_number = None

            # Try to match federated results to partner by finding LC call numbers
            for fed_result in federated_results:
                if fed_result.get("lc_classification"):
                    call_number = fed_result["lc_classification"]
                    break

            search_results.append(
                {
                    "partner_library_id": partner.id,
                    "partner_library_name": partner.name,
                    "partner_library_code": partner.code,
                    "available": partner_available,
                    "call_number": call_number,
                    "estimated_delivery_days": 5 if partner.reciprocal_agreement else 10,
                    "lending_fee": float(partner.lending_fee),
                    "federated_match_count": len(federated_results),
                }
            )

        logger.info(
            "Partner catalog search: title=%s found=%d partners", title, len(search_results)
        )
        return search_results

    async def auto_search_and_submit(
        self,
        request_id: int,
        staff_id: int,
    ) -> ILLRequest | None:
        ill_request = await self.get_request(request_id)
        if not ill_request:
            return None

        # Update status to searching
        ill_request.status = ILLRequestStatus.searching
        await self.db.flush()
        await self._add_tracking_update(
            request_id,
            ILLRequestStatus.searching,
            "Searching partner library catalogs...",
            created_by_id=staff_id,
        )

        # Search partners
        results = await self.search_partner_catalogs(
            title=ill_request.title,
            author=ill_request.author,
            isbn=ill_request.isbn,
        )

        available = [r for r in results if r["available"]]
        if not available:
            ill_request.status = ILLRequestStatus.not_found
            await self.db.flush()
            await self._add_tracking_update(
                request_id,
                ILLRequestStatus.not_found,
                "Item could not be located at any partner library.",
                created_by_id=staff_id,
            )
            return ill_request

        # Pick best partner: prefer reciprocal (free), then cheapest, then fastest
        best = sorted(
            available,
            key=lambda r: (r["lending_fee"], r.get("estimated_delivery_days", 99)),
        )[0]

        ill_request.partner_library_id = best["partner_library_id"]
        ill_request.estimated_cost = Decimal(str(best["lending_fee"]))
        ill_request.status = ILLRequestStatus.located
        await self.db.flush()

        await self._add_tracking_update(
            request_id,
            ILLRequestStatus.located,
            f"Item located at {best['partner_library_name']}. Submitting request.",
            created_by_id=staff_id,
        )

        # Auto-submit
        ill_request.status = ILLRequestStatus.submitted
        await self.db.flush()
        await self._add_tracking_update(
            request_id,
            ILLRequestStatus.submitted,
            f"Request submitted to {best['partner_library_name']}.",
            created_by_id=staff_id,
        )

        return ill_request

    # =========================================================================
    # TRACKING UPDATES
    # =========================================================================

    async def get_patron_tracking(self, request_id: int) -> list[ILLTrackingUpdate]:
        result = await self.db.execute(
            select(ILLTrackingUpdate)
            .where(
                and_(
                    ILLTrackingUpdate.ill_request_id == request_id,
                    ILLTrackingUpdate.is_patron_visible == True,  # noqa: E712
                )
            )
            .order_by(ILLTrackingUpdate.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_tracking_update(
        self,
        request_id: int,
        status: ILLRequestStatus,
        message: str,
        created_by_id: int | None = None,
        is_patron_visible: bool = True,
    ) -> ILLTrackingUpdate:
        return await self._add_tracking_update(
            request_id, status, message, created_by_id, is_patron_visible
        )

    # =========================================================================
    # DUE DATE REMINDERS
    # =========================================================================

    async def get_upcoming_due_requests(self, days_ahead: int = 7) -> list[ILLRequest]:
        target_date = date.today() + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(ILLRequest)
            .options(joinedload(ILLRequest.partner_library))
            .where(
                and_(
                    ILLRequest.status == ILLRequestStatus.checked_out,
                    ILLRequest.due_date != None,  # noqa: E711
                    ILLRequest.due_date <= target_date,
                    ILLRequest.due_date >= date.today(),
                )
            )
            .order_by(ILLRequest.due_date)
        )
        return list(result.unique().scalars().all())

    async def get_overdue_requests(self) -> list[ILLRequest]:
        result = await self.db.execute(
            select(ILLRequest)
            .options(joinedload(ILLRequest.partner_library))
            .where(
                and_(
                    ILLRequest.status == ILLRequestStatus.checked_out,
                    ILLRequest.due_date != None,  # noqa: E711
                    ILLRequest.due_date < date.today(),
                )
            )
            .order_by(ILLRequest.due_date)
        )
        return list(result.unique().scalars().all())

    # =========================================================================
    # RETURN SHIPPING LABEL
    # =========================================================================

    async def generate_return_shipping_label(self, request_id: int) -> dict[str, Any] | None:
        ill_request = await self.get_request(request_id)
        if not ill_request or not ill_request.partner_library:
            return None

        partner = ill_request.partner_library
        return {
            "request_id": request_id,
            "from_library": os.environ.get("LIBRARY_NAME", "My Library"),
            "from_address": os.environ.get("LIBRARY_ADDRESS", ""),
            "to_library": partner.name,
            "to_address": partner.address or "",
            "to_city": partner.city or "",
            "to_state": partner.state or "",
            "to_zip": partner.zip_code or "",
            "to_country": partner.country or "US",
            "shipping_method": (
                str(ill_request.shipping_method) if ill_request.shipping_method else "usps"
            ),
            "weight_estimate_oz": 16,  # Default 1 lb
            "tracking_number": ill_request.return_tracking,
            "label_format": "pdf",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # COST TRACKING
    # =========================================================================

    async def add_cost_record(
        self,
        request_id: int,
        category: ILLCostCategory,
        amount: Decimal,
        description: str | None = None,
        created_by_id: int | None = None,
    ) -> ILLCostRecord:
        cost = ILLCostRecord(
            ill_request_id=request_id,
            category=category,
            amount=amount,
            description=description,
            created_by_id=created_by_id,
        )
        self.db.add(cost)
        await self.db.flush()

        # Update total actual cost on the request
        total_result = await self.db.execute(
            select(func.sum(ILLCostRecord.amount)).where(ILLCostRecord.ill_request_id == request_id)
        )
        total = total_result.scalar() or Decimal("0")
        await self.db.execute(
            update(ILLRequest).where(ILLRequest.id == request_id).values(actual_cost=total)
        )
        await self.db.flush()

        return cost

    async def get_cost_records(self, request_id: int) -> list[ILLCostRecord]:
        result = await self.db.execute(
            select(ILLCostRecord)
            .where(ILLCostRecord.ill_request_id == request_id)
            .order_by(ILLCostRecord.created_at)
        )
        return list(result.scalars().all())

    async def get_cost_summary(self, period_start: date, period_end: date) -> dict[str, Any]:
        # Borrowing costs
        borrow_result = await self.db.execute(
            select(func.coalesce(func.sum(ILLCostRecord.amount), 0)).where(
                and_(
                    ILLCostRecord.ill_request_id == ILLRequest.id,
                    ILLRequest.request_type == ILLRequestType.borrow,
                    ILLCostRecord.created_at >= datetime.combine(period_start, datetime.min.time()),
                    ILLCostRecord.created_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        borrowing_costs = borrow_result.scalar() or Decimal("0")

        # Lending revenue
        lend_result = await self.db.execute(
            select(func.coalesce(func.sum(ILLCostRecord.amount), 0)).where(
                and_(
                    ILLCostRecord.ill_request_id == ILLRequest.id,
                    ILLRequest.request_type == ILLRequestType.lend,
                    ILLCostRecord.created_at >= datetime.combine(period_start, datetime.min.time()),
                    ILLCostRecord.created_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        lending_revenue = lend_result.scalar() or Decimal("0")

        # By category
        cat_result = await self.db.execute(
            select(ILLCostRecord.category, func.sum(ILLCostRecord.amount))
            .where(
                and_(
                    ILLCostRecord.created_at >= datetime.combine(period_start, datetime.min.time()),
                    ILLCostRecord.created_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
            .group_by(ILLCostRecord.category)
        )
        cost_by_category = {row[0].value: row[1] for row in cat_result}

        # Count requests for average
        count_result = await self.db.execute(
            select(func.count(func.distinct(ILLCostRecord.ill_request_id))).where(
                and_(
                    ILLCostRecord.created_at >= datetime.combine(period_start, datetime.min.time()),
                    ILLCostRecord.created_at <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        request_count = count_result.scalar() or 0

        return {
            "total_borrowing_costs": borrowing_costs,
            "total_lending_revenue": lending_revenue,
            "net_cost": borrowing_costs - lending_revenue,
            "average_cost_per_request": (
                borrowing_costs / request_count if request_count > 0 else Decimal("0")
            ),
            "cost_by_category": cost_by_category,
            "period_start": period_start,
            "period_end": period_end,
        }

    # =========================================================================
    # FILL RATE REPORTING
    # =========================================================================

    async def get_fill_rate_report(self, period_start: date, period_end: date) -> dict[str, Any]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        base_filter = and_(
            ILLRequest.request_type == ILLRequestType.borrow,
            ILLRequest.created_at >= start_dt,
            ILLRequest.created_at <= end_dt,
        )

        # Total requests
        total_result = await self.db.execute(select(func.count(ILLRequest.id)).where(base_filter))
        total = total_result.scalar() or 0

        # Filled = reached checked_out or beyond
        filled_statuses = {
            ILLRequestStatus.checked_out,
            ILLRequestStatus.returned,
            ILLRequestStatus.return_in_transit,
            ILLRequestStatus.completed,
        }
        filled_result = await self.db.execute(
            select(func.count(ILLRequest.id)).where(
                and_(base_filter, ILLRequest.status.in_(filled_statuses))
            )
        )
        filled = filled_result.scalar() or 0

        # Cancelled
        cancelled_result = await self.db.execute(
            select(func.count(ILLRequest.id)).where(
                and_(base_filter, ILLRequest.status == ILLRequestStatus.cancelled)
            )
        )
        cancelled = cancelled_result.scalar() or 0

        unfilled = total - filled - cancelled

        # Average turnaround (submitted → received)
        turnaround_result = await self.db.execute(
            select(
                func.avg(
                    func.extract("epoch", ILLRequest.received_at)
                    - func.extract("epoch", ILLRequest.created_at)
                )
            ).where(
                and_(
                    base_filter,
                    ILLRequest.received_at != None,  # noqa: E711
                )
            )
        )
        avg_seconds = turnaround_result.scalar()
        avg_days = round(avg_seconds / 86400, 1) if avg_seconds else None

        return {
            "total_requests": total,
            "filled_requests": filled,
            "unfilled_requests": unfilled,
            "cancelled_requests": cancelled,
            "fill_rate_percent": round((filled / total * 100) if total > 0 else 0, 1),
            "average_turnaround_days": avg_days,
            "period_start": period_start,
            "period_end": period_end,
        }

    # =========================================================================
    # RECIPROCAL LENDING DASHBOARD
    # =========================================================================

    async def get_reciprocal_lending_dashboard(
        self, period_start: date, period_end: date
    ) -> dict[str, Any]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        partners = await self.list_partner_libraries()

        partner_stats = []
        total_borrowed = 0
        total_lent = 0
        total_borrow_cost = Decimal("0")
        total_lend_revenue = Decimal("0")

        for partner in partners:
            date_filter = and_(
                ILLRequest.created_at >= start_dt,
                ILLRequest.created_at <= end_dt,
                ILLRequest.partner_library_id == partner.id,
            )

            # Items borrowed from this partner
            borrow_result = await self.db.execute(
                select(func.count(ILLRequest.id)).where(
                    and_(date_filter, ILLRequest.request_type == ILLRequestType.borrow)
                )
            )
            borrowed = borrow_result.scalar() or 0

            # Items lent to this partner
            lend_result = await self.db.execute(
                select(func.count(ILLRequest.id)).where(
                    and_(date_filter, ILLRequest.request_type == ILLRequestType.lend)
                )
            )
            lent = lend_result.scalar() or 0

            # Costs for this partner
            borrow_cost_result = await self.db.execute(
                select(func.coalesce(func.sum(ILLRequest.actual_cost), 0)).where(
                    and_(date_filter, ILLRequest.request_type == ILLRequestType.borrow)
                )
            )
            borrow_cost = borrow_cost_result.scalar() or Decimal("0")

            lend_rev_result = await self.db.execute(
                select(func.coalesce(func.sum(ILLRequest.actual_cost), 0)).where(
                    and_(date_filter, ILLRequest.request_type == ILLRequestType.lend)
                )
            )
            lend_revenue = lend_rev_result.scalar() or Decimal("0")

            # Active borrows/lends
            active_statuses = {
                ILLRequestStatus.submitted,
                ILLRequestStatus.approved,
                ILLRequestStatus.in_transit,
                ILLRequestStatus.received,
                ILLRequestStatus.checked_out,
            }
            active_borrow_result = await self.db.execute(
                select(func.count(ILLRequest.id)).where(
                    and_(
                        ILLRequest.partner_library_id == partner.id,
                        ILLRequest.request_type == ILLRequestType.borrow,
                        ILLRequest.status.in_(active_statuses),
                    )
                )
            )
            active_borrows = active_borrow_result.scalar() or 0

            active_lend_result = await self.db.execute(
                select(func.count(ILLRequest.id)).where(
                    and_(
                        ILLRequest.partner_library_id == partner.id,
                        ILLRequest.request_type == ILLRequestType.lend,
                        ILLRequest.status.in_(active_statuses),
                    )
                )
            )
            active_lends = active_lend_result.scalar() or 0

            # Fill rate for this partner
            total_partner_requests = borrowed
            filled_result = await self.db.execute(
                select(func.count(ILLRequest.id)).where(
                    and_(
                        date_filter,
                        ILLRequest.request_type == ILLRequestType.borrow,
                        ILLRequest.status.in_(
                            {
                                ILLRequestStatus.checked_out,
                                ILLRequestStatus.returned,
                                ILLRequestStatus.return_in_transit,
                                ILLRequestStatus.completed,
                            }
                        ),
                    )
                )
            )
            partner_filled = filled_result.scalar() or 0
            fill_rate = round(
                (partner_filled / total_partner_requests * 100)
                if total_partner_requests > 0
                else 0,
                1,
            )

            partner_stats.append(
                {
                    "partner_library_id": partner.id,
                    "partner_library_name": partner.name,
                    "partner_library_code": partner.code,
                    "items_borrowed": borrowed,
                    "items_lent": lent,
                    "balance": borrowed - lent,
                    "total_borrowing_cost": borrow_cost,
                    "total_lending_revenue": lend_revenue,
                    "active_borrows": active_borrows,
                    "active_lends": active_lends,
                    "fill_rate_percent": fill_rate,
                }
            )

            total_borrowed += borrowed
            total_lent += lent
            total_borrow_cost += borrow_cost
            total_lend_revenue += lend_revenue

        active_count = sum(1 for p in partners if p.status == PartnerLibraryStatus.active)

        return {
            "total_partners": len(partners),
            "active_partners": active_count,
            "total_items_borrowed": total_borrowed,
            "total_items_lent": total_lent,
            "overall_balance": total_borrowed - total_lent,
            "net_cost": total_borrow_cost - total_lend_revenue,
            "partner_stats": partner_stats,
            "period_start": period_start,
            "period_end": period_end,
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _add_tracking_update(
        self,
        request_id: int,
        status: ILLRequestStatus,
        message: str,
        created_by_id: int | None = None,
        is_patron_visible: bool = True,
    ) -> ILLTrackingUpdate:
        tracking = ILLTrackingUpdate(
            ill_request_id=request_id,
            status=status,
            message=message,
            is_patron_visible=is_patron_visible,
            created_by_id=created_by_id,
        )
        self.db.add(tracking)
        await self.db.flush()
        return tracking

    @staticmethod
    def _apply_status_dates(
        ill_request: ILLRequest,
        new_status: ILLRequestStatus,
        now: datetime,
    ) -> None:
        if new_status == ILLRequestStatus.in_transit:
            ill_request.shipped_at = now
        elif new_status == ILLRequestStatus.received:
            ill_request.received_at = now
        elif new_status == ILLRequestStatus.checked_out:
            ill_request.checked_out_at = now
            if not ill_request.due_date:
                partner = ill_request.partner_library
                loan_days = partner.max_loan_days if partner else 21
                ill_request.due_date = (now + timedelta(days=loan_days)).date()
        elif new_status == ILLRequestStatus.returned:
            ill_request.returned_at = now
        elif new_status == ILLRequestStatus.completed:
            ill_request.completed_at = now
