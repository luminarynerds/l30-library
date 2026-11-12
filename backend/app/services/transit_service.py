# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.multi_branch import (
    Branch,
    BranchItemCopy,
    FloatingCollectionType,
    LibrarySystem,
    TransitPriority,
    TransitReason,
    TransitRequest,
    TransitShipment,
    TransitShipmentItem,
    TransitStatus,
    ConsortiumTransaction,
)
from app.models.circulation import Hold, HoldStatus
from app.models.inventory import ItemCopy


class TransitService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # TRANSIT REQUEST MANAGEMENT
    # =========================================================================

    async def create_transit_request(
        self,
        item_copy_id: int,
        from_branch_id: int,
        to_branch_id: int,
        reason: TransitReason,
        requested_by_id: int,
        priority: TransitPriority = TransitPriority.NORMAL,
        hold_id: int | None = None,
        notes: str | None = None,
        auto_approve: bool = True
    ) -> TransitRequest:
        # Calculate expected arrival based on system settings
        expected_days = 2  # Default, should come from system settings
        expected_arrival = date.today() + timedelta(days=expected_days)

        request = TransitRequest(
            item_copy_id=item_copy_id,
            from_branch_id=from_branch_id,
            to_branch_id=to_branch_id,
            reason=reason,
            priority=priority,
            status=TransitStatus.REQUESTED,
            hold_id=hold_id,
            requested_by_id=requested_by_id,
            expected_arrival_date=expected_arrival,
            notes=notes,
        )

        self.db.add(request)

        # Auto-approve if enabled
        if auto_approve:
            request.status = TransitStatus.APPROVED
            request.approved_at = datetime.now(timezone.utc)
            request.approved_by_id = requested_by_id

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def get_transit_request(self, request_id: int) -> TransitRequest | None:
        result = await self.db.execute(
            select(TransitRequest)
            .options(
                joinedload(TransitRequest.item_copy),
                joinedload(TransitRequest.hold),
            )
            .where(TransitRequest.id == request_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_transit_request_for_item(
        self,
        item_copy_id: int,
        active_only: bool = True
    ) -> TransitRequest | None:
        query = select(TransitRequest).where(
            TransitRequest.item_copy_id == item_copy_id
        )

        if active_only:
            query = query.where(
                TransitRequest.status.in_([
                    TransitStatus.REQUESTED,
                    TransitStatus.APPROVED,
                    TransitStatus.PICKED_UP,
                    TransitStatus.IN_TRANSIT,
                ])
            )

        query = query.order_by(TransitRequest.requested_at.desc())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_transit_requests(
        self,
        from_branch_id: int | None = None,
        to_branch_id: int | None = None,
        status: TransitStatus | None = None,
        priority: TransitPriority | None = None,
        reason: TransitReason | None = None,
        library_system_id: int | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[TransitRequest]:
        query = (
            select(TransitRequest)
            .options(
                joinedload(TransitRequest.item_copy),
            )
        )

        if from_branch_id:
            query = query.where(TransitRequest.from_branch_id == from_branch_id)
        if to_branch_id:
            query = query.where(TransitRequest.to_branch_id == to_branch_id)
        if status:
            query = query.where(TransitRequest.status == status)
        if priority:
            query = query.where(TransitRequest.priority == priority)
        if reason:
            query = query.where(TransitRequest.reason == reason)
        if library_system_id:
            query = query.join(Branch, TransitRequest.from_branch_id == Branch.id).where(
                Branch.library_system_id == library_system_id
            )

        query = query.order_by(
            TransitRequest.priority.desc(),
            TransitRequest.requested_at
        ).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.unique().scalars().all())

    async def approve_transit_request(
        self,
        request_id: int,
        approved_by_id: int
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status != TransitStatus.REQUESTED:
            raise ValueError(f"Cannot approve request in {request.status} status")

        request.status = TransitStatus.APPROVED
        request.approved_at = datetime.now(timezone.utc)
        request.approved_by_id = approved_by_id

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def cancel_transit_request(
        self,
        request_id: int,
        cancelled_by_id: int,
        reason: str | None = None
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status in [TransitStatus.RECEIVED, TransitStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel request in {request.status} status")

        request.status = TransitStatus.CANCELLED
        request.cancelled_at = datetime.now(timezone.utc)
        request.cancelled_by_id = cancelled_by_id
        request.cancellation_reason = reason

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def mark_item_picked_up(
        self,
        request_id: int,
        picked_up_by_id: int
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status not in [TransitStatus.APPROVED, TransitStatus.REQUESTED]:
            raise ValueError(f"Cannot pick up request in {request.status} status")

        request.status = TransitStatus.PICKED_UP
        request.picked_up_at = datetime.now(timezone.utc)
        request.picked_up_by_id = picked_up_by_id

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def mark_item_in_transit(
        self,
        request_id: int
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status != TransitStatus.PICKED_UP:
            raise ValueError(f"Cannot mark in transit from {request.status} status")

        request.status = TransitStatus.IN_TRANSIT
        request.shipped_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def receive_transit_item(
        self,
        request_id: int,
        received_by_id: int
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status not in [TransitStatus.IN_TRANSIT, TransitStatus.PICKED_UP]:
            raise ValueError(f"Cannot receive request in {request.status} status")

        request.status = TransitStatus.RECEIVED
        request.received_at = datetime.now(timezone.utc)
        request.received_by_id = received_by_id

        # Update item location
        await self._update_item_location(
            request.item_copy_id,
            request.to_branch_id
        )

        # If this was for a hold, update the hold status
        if request.hold_id:
            await self._update_hold_ready(request.hold_id)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def mark_lost_in_transit(
        self,
        request_id: int,
        notes: str | None = None
    ) -> TransitRequest | None:
        request = await self.get_transit_request(request_id)
        if not request:
            return None

        if request.status != TransitStatus.IN_TRANSIT:
            raise ValueError(f"Cannot mark lost from {request.status} status")

        request.status = TransitStatus.LOST_IN_TRANSIT
        if notes:
            request.notes = (request.notes or "") + f"\n\nLost in transit: {notes}"

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def _update_item_location(
        self,
        item_copy_id: int,
        branch_id: int
    ) -> None:
        result = await self.db.execute(
            select(BranchItemCopy).where(BranchItemCopy.item_copy_id == item_copy_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment:
            assignment.current_branch_id = branch_id
            assignment.last_seen_at = datetime.now(timezone.utc)
        else:
            # Create new assignment
            assignment = BranchItemCopy(
                item_copy_id=item_copy_id,
                current_branch_id=branch_id,
                home_branch_id=branch_id,
                last_seen_at=datetime.now(timezone.utc),
            )
            self.db.add(assignment)

    async def _update_hold_ready(self, hold_id: int) -> None:
        result = await self.db.execute(
            select(Hold).where(Hold.id == hold_id)
        )
        hold = result.scalar_one_or_none()

        if hold and hold.status == HoldStatus.PENDING:
            hold.status = HoldStatus.READY

    # =========================================================================
    # SHIPMENT MANAGEMENT
    # =========================================================================

    async def create_shipment(
        self,
        from_branch_id: int,
        to_branch_id: int,
        created_by_id: int,
        container_count: int = 1,
        carrier: str | None = None,
        tracking_number: str | None = None,
        notes: str | None = None
    ) -> TransitShipment:
        # Generate shipment number
        shipment_number = f"SHP-{uuid.uuid4().hex[:8].upper()}"

        shipment = TransitShipment(
            shipment_number=shipment_number,
            from_branch_id=from_branch_id,
            to_branch_id=to_branch_id,
            container_count=container_count,
            created_by_id=created_by_id,
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
        )

        self.db.add(shipment)
        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def get_shipment(self, shipment_id: int) -> TransitShipment | None:
        result = await self.db.execute(
            select(TransitShipment)
            .options(
                selectinload(TransitShipment.items).joinedload(TransitShipmentItem.transit_request),
            )
            .where(TransitShipment.id == shipment_id)
        )
        shipment = result.unique().scalar_one_or_none()
        if not shipment:
            return None

        # Load branches manually (relationships are disabled on the model)
        from_result = await self.db.execute(
            select(Branch).where(Branch.id == shipment.from_branch_id)
        )
        shipment.from_branch = from_result.scalar_one_or_none()

        to_result = await self.db.execute(
            select(Branch).where(Branch.id == shipment.to_branch_id)
        )
        shipment.to_branch = to_result.scalar_one_or_none()

        return shipment

    async def get_shipment_by_number(self, shipment_number: str) -> TransitShipment | None:
        result = await self.db.execute(
            select(TransitShipment)
            .options(
                selectinload(TransitShipment.items),
            )
            .where(TransitShipment.shipment_number == shipment_number)
        )
        shipment = result.unique().scalar_one_or_none()
        if not shipment:
            return None

        # Load branches manually (relationships are disabled on the model)
        from_result = await self.db.execute(
            select(Branch).where(Branch.id == shipment.from_branch_id)
        )
        shipment.from_branch = from_result.scalar_one_or_none()

        to_result = await self.db.execute(
            select(Branch).where(Branch.id == shipment.to_branch_id)
        )
        shipment.to_branch = to_result.scalar_one_or_none()

        return shipment

    async def list_shipments(
        self,
        from_branch_id: int | None = None,
        to_branch_id: int | None = None,
        shipped: bool | None = None,
        received: bool | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[TransitShipment]:
        query = select(TransitShipment)

        if from_branch_id:
            query = query.where(TransitShipment.from_branch_id == from_branch_id)
        if to_branch_id:
            query = query.where(TransitShipment.to_branch_id == to_branch_id)
        if shipped is not None:
            if shipped:
                query = query.where(TransitShipment.shipped_at.isnot(None))
            else:
                query = query.where(TransitShipment.shipped_at.is_(None))
        if received is not None:
            if received:
                query = query.where(TransitShipment.received_at.isnot(None))
            else:
                query = query.where(TransitShipment.received_at.is_(None))
        if from_date:
            query = query.where(TransitShipment.shipped_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            query = query.where(TransitShipment.shipped_at <= datetime.combine(to_date, datetime.max.time()))

        query = query.order_by(TransitShipment.id.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_item_to_shipment(
        self,
        shipment_id: int,
        transit_request_id: int,
        scanned_by_id: int
    ) -> TransitShipmentItem:
        # Update the transit request status
        request = await self.get_transit_request(transit_request_id)
        if not request:
            raise ValueError(f"Transit request {transit_request_id} not found")

        if request.status not in [TransitStatus.APPROVED, TransitStatus.PICKED_UP]:
            raise ValueError(f"Cannot add request in {request.status} status to shipment")

        # Mark as picked up if not already
        if request.status == TransitStatus.APPROVED:
            request.status = TransitStatus.PICKED_UP
            request.picked_up_at = datetime.now(timezone.utc)
            request.picked_up_by_id = scanned_by_id

        # Create shipment item
        item = TransitShipmentItem(
            shipment_id=shipment_id,
            transit_request_id=transit_request_id,
            scanned_in_by_id=scanned_by_id,
        )
        self.db.add(item)

        # Update shipment item count
        result = await self.db.execute(
            select(TransitShipment).where(TransitShipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()
        if shipment:
            shipment.item_count = (shipment.item_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def ship_shipment(
        self,
        shipment_id: int,
        shipped_by_id: int,
        tracking_number: str | None = None
    ) -> TransitShipment | None:
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            return None

        if shipment.shipped_at:
            raise ValueError("Shipment has already been shipped")

        shipment.shipped_at = datetime.now(timezone.utc)
        shipment.shipped_by_id = shipped_by_id
        if tracking_number:
            shipment.tracking_number = tracking_number

        # Update all transit requests to in_transit
        for item in shipment.items:
            if item.transit_request:
                item.transit_request.status = TransitStatus.IN_TRANSIT
                item.transit_request.shipped_at = shipment.shipped_at

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def receive_shipment(
        self,
        shipment_id: int,
        received_by_id: int
    ) -> TransitShipment | None:
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            return None

        if not shipment.shipped_at:
            raise ValueError("Shipment has not been shipped yet")

        if shipment.received_at:
            raise ValueError("Shipment has already been received")

        now = datetime.now(timezone.utc)
        shipment.received_at = now
        shipment.received_by_id = received_by_id

        # Update all shipment items and transit requests
        for item in shipment.items:
            item.received_at = now
            item.received_by_id = received_by_id

            if item.transit_request:
                await self.receive_transit_item(
                    item.transit_request.id,
                    received_by_id
                )

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def receive_shipment_item(
        self,
        shipment_item_id: int,
        received_by_id: int,
        notes: str | None = None
    ) -> TransitShipmentItem | None:
        result = await self.db.execute(
            select(TransitShipmentItem)
            .options(joinedload(TransitShipmentItem.transit_request))
            .where(TransitShipmentItem.id == shipment_item_id)
        )
        item = result.unique().scalar_one_or_none()

        if not item:
            return None

        item.received_at = datetime.now(timezone.utc)
        item.received_by_id = received_by_id
        if notes:
            item.notes = notes

        # Update the transit request
        if item.transit_request_id:
            await self.receive_transit_item(item.transit_request_id, received_by_id)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    # =========================================================================
    # FLOATING COLLECTION HANDLING
    # =========================================================================

    async def determine_return_destination(
        self,
        item_copy_id: int,
        return_branch_id: int
    ) -> int:
        result = await self.db.execute(
            select(BranchItemCopy).where(BranchItemCopy.item_copy_id == item_copy_id)
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return return_branch_id

        # Floating items stay where they are
        if assignment.is_floating:
            return return_branch_id

        # Check float scope
        if assignment.float_scope != FloatingCollectionType.NO_FLOAT:
            # Check if return branch is within float scope
            if await self._is_within_float_scope(
                assignment.home_branch_id,
                return_branch_id,
                assignment.float_scope
            ):
                return return_branch_id

        # Non-floating: return to home branch
        return assignment.home_branch_id or return_branch_id

    async def _is_within_float_scope(
        self,
        home_branch_id: int | None,
        target_branch_id: int,
        float_scope: FloatingCollectionType
    ) -> bool:
        if not home_branch_id:
            return True

        if float_scope == FloatingCollectionType.NO_FLOAT:
            return home_branch_id == target_branch_id

        # Get both branches
        result = await self.db.execute(
            select(Branch).where(Branch.id.in_([home_branch_id, target_branch_id]))
        )
        branches = {b.id: b for b in result.scalars().all()}

        home = branches.get(home_branch_id)
        target = branches.get(target_branch_id)

        if not home or not target:
            return False

        if float_scope == FloatingCollectionType.REGION_FLOAT:
            return home.region_id == target.region_id

        if float_scope == FloatingCollectionType.SYSTEM_FLOAT:
            return home.library_system_id == target.library_system_id

        if float_scope == FloatingCollectionType.CONSORTIUM_FLOAT:
            # Check if both systems are in the same consortium
            # This would require checking consortium membership
            return True  # Simplified for now

        return False

    async def create_return_transit_if_needed(
        self,
        item_copy_id: int,
        return_branch_id: int,
        returned_by_id: int
    ) -> TransitRequest | None:
        destination = await self.determine_return_destination(item_copy_id, return_branch_id)

        if destination == return_branch_id:
            # Item can stay here
            await self._update_item_location(item_copy_id, return_branch_id)
            return None

        # Need to transit to home branch
        return await self.create_transit_request(
            item_copy_id=item_copy_id,
            from_branch_id=return_branch_id,
            to_branch_id=destination,
            reason=TransitReason.RETURN_TO_HOME,
            requested_by_id=returned_by_id,
            priority=TransitPriority.LOW,
            auto_approve=True,
        )

    # =========================================================================
    # HOLD FULFILLMENT
    # =========================================================================

    async def create_hold_fulfillment_transit(
        self,
        hold_id: int,
        item_copy_id: int,
        from_branch_id: int,
        to_branch_id: int,
        requested_by_id: int
    ) -> TransitRequest:
        return await self.create_transit_request(
            item_copy_id=item_copy_id,
            from_branch_id=from_branch_id,
            to_branch_id=to_branch_id,
            reason=TransitReason.HOLD_FULFILLMENT,
            requested_by_id=requested_by_id,
            priority=TransitPriority.HIGH,
            hold_id=hold_id,
            auto_approve=True,
        )

    async def get_pending_hold_transits(
        self,
        branch_id: int
    ) -> list[TransitRequest]:
        return await self.list_transit_requests(
            to_branch_id=branch_id,
            status=TransitStatus.IN_TRANSIT,
            reason=TransitReason.HOLD_FULFILLMENT,
        )

    # =========================================================================
    # COLLECTION REBALANCING
    # =========================================================================

    async def create_rebalancing_transit(
        self,
        item_copy_id: int,
        from_branch_id: int,
        to_branch_id: int,
        requested_by_id: int,
        notes: str | None = None
    ) -> TransitRequest:
        return await self.create_transit_request(
            item_copy_id=item_copy_id,
            from_branch_id=from_branch_id,
            to_branch_id=to_branch_id,
            reason=TransitReason.REBALANCING,
            requested_by_id=requested_by_id,
            priority=TransitPriority.LOW,
            notes=notes,
            auto_approve=True,
        )

    # =========================================================================
    # TRANSIT STATISTICS
    # =========================================================================

    async def get_transit_statistics(
        self,
        library_system_id: int | None = None,
        branch_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None
    ) -> dict[str, Any]:
        # Base query
        base_conditions = []
        if from_date:
            base_conditions.append(TransitRequest.requested_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            base_conditions.append(TransitRequest.requested_at <= datetime.combine(to_date, datetime.max.time()))
        if branch_id:
            base_conditions.append(
                or_(
                    TransitRequest.from_branch_id == branch_id,
                    TransitRequest.to_branch_id == branch_id
                )
            )

        # Total requests
        total_query = select(func.count(TransitRequest.id)).where(and_(*base_conditions) if base_conditions else True)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # By status
        status_query = (
            select(TransitRequest.status, func.count(TransitRequest.id))
            .where(and_(*base_conditions) if base_conditions else True)
            .group_by(TransitRequest.status)
        )
        status_result = await self.db.execute(status_query)
        by_status = {(row[0].value if hasattr(row[0], "value") else row[0]): row[1] for row in status_result.all()}

        # By reason
        reason_query = (
            select(TransitRequest.reason, func.count(TransitRequest.id))
            .where(and_(*base_conditions) if base_conditions else True)
            .group_by(TransitRequest.reason)
        )
        reason_result = await self.db.execute(reason_query)
        by_reason = {(row[0].value if hasattr(row[0], "value") else row[0]): row[1] for row in reason_result.all()}

        # Average transit time (for completed)
        completed_conditions = base_conditions + [
            TransitRequest.status == TransitStatus.RECEIVED,
            TransitRequest.shipped_at.isnot(None),
            TransitRequest.received_at.isnot(None),
        ]
        avg_time_query = select(
            func.avg(
                func.extract('epoch', TransitRequest.received_at) -
                func.extract('epoch', TransitRequest.shipped_at)
            ) / 3600  # Convert to hours
        ).where(and_(*completed_conditions))
        avg_time_result = await self.db.execute(avg_time_query)
        avg_transit_hours = avg_time_result.scalar()

        return {
            "total_requests": total,
            "by_status": by_status,
            "by_reason": by_reason,
            "average_transit_hours": round(avg_transit_hours, 1) if avg_transit_hours else None,
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            }
        }

    async def get_items_in_transit_to_branch(
        self,
        branch_id: int
    ) -> list[TransitRequest]:
        return await self.list_transit_requests(
            to_branch_id=branch_id,
            status=TransitStatus.IN_TRANSIT,
        )

    async def get_items_awaiting_shipment(
        self,
        branch_id: int
    ) -> list[TransitRequest]:
        return await self.list_transit_requests(
            from_branch_id=branch_id,
            status=TransitStatus.APPROVED,
        )
