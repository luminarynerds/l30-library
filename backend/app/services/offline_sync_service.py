# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.offline_sync import OfflineSyncSession, ProcessedOfflineOp
from ..models.user import User, UserRole, PatronStatus
from ..models.catalog import CatalogItem, ItemStatus
from ..models.inventory import ItemCopy
from ..models.circulation import Checkout, CheckoutStatus
from ..schemas.offline_sync import (
    CachedPatron, CachedItem, PrepareRouteResponse,
    SyncOperation, SyncOperationResult,
)
from app.core.datetime_utils import utc_now
from app.core.errors import APIError as HTTPAPIError
from app.core.exceptions import APIError, ConflictError

logger = get_logger(__name__)


def _parse_op_timestamp(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        # Accept "Z" suffix as UTC
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


async def _lookup_patron(db: AsyncSession, barcode: Optional[str]) -> Optional[User]:
    if not barcode:
        return None
    result = await db.execute(
        select(User).where(User.library_card == barcode).limit(1)
    )
    return result.scalar_one_or_none()


async def _lookup_item_copy(
    db: AsyncSession, barcode: str,
) -> tuple[Optional[ItemCopy], Optional[CatalogItem]]:
    copy_result = await db.execute(
        select(ItemCopy).where(ItemCopy.barcode == barcode).limit(1)
    )
    copy = copy_result.scalar_one_or_none()
    if copy:
        item_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == copy.catalog_item_id).limit(1)
        )
        return copy, item_result.scalar_one_or_none()

    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.barcode == barcode).limit(1)
    )
    return None, item_result.scalar_one_or_none()


class OfflineSyncService:

    @staticmethod
    async def prepare_route(db: AsyncSession, branch_id: int) -> PrepareRouteResponse:

        # CatalogItem has no branch FK -- fetch available/checked_out items globally.
        # For a real bookmobile deployment, filter by location or a future branch_id column.
        items_result = await db.execute(
            select(CatalogItem).where(
                CatalogItem.status.in_([ItemStatus.available, ItemStatus.checked_out])
            )
        )
        items_rows = items_result.scalars().all()

        cached_items = [
            CachedItem(
                barcode=item.barcode or f"ITEM-{item.id}",
                id=item.id,
                title=item.title or "Unknown",
                author=item.author or "",
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
                branch_id=branch_id,  # no FK on CatalogItem; echo back requested branch
                call_number=item.call_number,
                media_type=item.item_type.value if item.item_type and hasattr(item.item_type, "value") else str(item.item_type or "book"),
            )
            for item in items_rows
        ]

        # All active patrons (small library: <5000)
        patrons_result = await db.execute(
            select(User).where(
                and_(
                    User.role == UserRole.PATRON,
                    User.patron_status == PatronStatus.ACTIVE,
                    )
            ).limit(5000)
        )
        patron_rows = patrons_result.scalars().all()

        cached_patrons = [
            CachedPatron(
                barcode=patron.library_card or f"P-{patron.id}",
                id=patron.id,
                name=f"{patron.first_name or ''} {patron.last_name or ''}".strip() or "Unknown",
                photo_url=None,
                status=patron.patron_status.value if hasattr(patron.patron_status, "value") else str(patron.patron_status),
                checkout_count=0,  # no cached count column; server-side count not pre-computed
                checkout_limit=50,
                card_expiry=patron.card_expires_at.isoformat() if patron.card_expires_at else None,
            )
            for patron in patron_rows
        ]

        return PrepareRouteResponse(
            patrons=cached_patrons,
            items=cached_items,
            patron_count=len(cached_patrons),
            item_count=len(cached_items),
            generated_at=utc_now(),
        )

    @staticmethod
    async def depart(
        db: AsyncSession,
        branch_id: int,
        staff_id: int,
        items_cached: int,
        patrons_cached: int,
    ) -> OfflineSyncSession:

        offline_token = secrets.token_urlsafe(48)

        session = OfflineSyncSession(
            branch_id=branch_id,
            staff_id=staff_id,
            status="departed",
            departed_at=utc_now(),
            items_cached=items_cached,
            patrons_cached=patrons_cached,
            offline_session_token=offline_token,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def mark_returned(db: AsyncSession, session_id: int) -> OfflineSyncSession:
        result = await db.execute(
            select(OfflineSyncSession).where(OfflineSyncSession.id == session_id)
        )
        session = result.scalar_one()
        session.status = "returned"
        session.returned_at = utc_now()
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def sync_operations(
        db: AsyncSession,
        session_id: int,
        operations: List[SyncOperation],
    ) -> List[SyncOperationResult]:

        results: List[SyncOperationResult] = []
        # Distributed checkout locks must be released AFTER commit so a
        # concurrent online checkout cannot slip in before our offline
        # sync data is durable.
        deferred_releases: list = []

        for op in operations:
            # Idempotency check
            existing_result = await db.execute(
                select(ProcessedOfflineOp).where(
                    ProcessedOfflineOp.client_op_id == op.client_op_id
                    )
            )
            existing_row = existing_result.scalar_one_or_none()
            if existing_row:
                results.append(SyncOperationResult(
                    client_op_id=op.client_op_id,
                    status=existing_row.result_status,
                    detail=existing_row.result_detail,
                    ))
                continue

            op_status = "synced"
            op_detail = None
            op_when = _parse_op_timestamp(op.timestamp) or utc_now()
            deferred_release = None

            try:
                # SAVEPOINT: one failed op cannot poison the session for remaining ops
                async with db.begin_nested():
                    op_status, op_detail, deferred_release = (
                        await OfflineSyncService._apply_operation(db, op, op_when)
                    )
            except ConflictError as e:
                # True conflicts: item already checked out, copy lock held
                op_status = "conflict"
                op_detail = str(e)[:500]
            except (HTTPAPIError, APIError) as e:
                # Business-logic errors: checkout limit, item unavailable, renewal limit
                # Surface as soft failure so staff can resolve.
                op_status = "failed"
                op_detail = str(e)[:500]
            except Exception as e:
                # Unexpected. Log with stack so operators can investigate;
                # the bookmobile patron isn't blocked for unrelated reasons.
                logger.exception(
                    "Offline op failed unexpectedly",
                    extra={
                        "client_op_id": op.client_op_id,
                        "session_id": session_id,
                        "type": op.type,
                    },
                    )
                op_status = "failed"
                op_detail = f"{type(e).__name__}: {e}"[:500]

            processed = ProcessedOfflineOp(
                client_op_id=op.client_op_id,
                session_id=session_id,
                result_status=op_status,
                result_detail=op_detail,
            )
            db.add(processed)
            results.append(SyncOperationResult(
                client_op_id=op.client_op_id,
                status=op_status,
                detail=op_detail,
            ))
            if deferred_release is not None:
                deferred_releases.append(deferred_release)

        # Update session stats
        session_result = await db.execute(
            select(OfflineSyncSession).where(OfflineSyncSession.id == session_id)
        )
        session = session_result.scalar_one()
        session.operations_queued = len(operations)
        session.operations_synced = sum(1 for r in results if r.status == "synced")
        session.operations_conflicted = sum(1 for r in results if r.status == "conflict")
        session.status = "synced"
        session.synced_at = utc_now()

        await db.commit()

        # Release locks now that the data is durable. Lock release failures
        # are logged inside CheckoutResult.release_lock and don't bubble.
        for release in deferred_releases:
            try:
                # SAVEPOINT: one failed op cannot poison the session for remaining ops
                async with db.begin_nested():
                    await release()
            except Exception:
                logger.exception("Failed to release deferred checkout lock")

        return results

    @staticmethod
    async def _apply_operation(
        db: AsyncSession, op: SyncOperation, op_when: datetime,
    ) -> tuple[str, Optional[str], Optional[object]]:
        # Imported lazily to avoid a circular import: checkout_service
        # imports operations_audit_service which imports a number of models
        # that pull from this module's neighbors.
        from .checkout_service import (
            create_checkout, return_checkout, renew_checkout,
        )

        copy, item = await _lookup_item_copy(db, op.item_barcode)
        if item is None:
            return "failed", f"Item barcode not found: {op.item_barcode}", None

        if op.type == "checkout":
            patron = await _lookup_patron(db, op.patron_barcode)
            if patron is None:
                return "failed", f"Patron barcode not found: {op.patron_barcode}", None
            # Replays a loan that already physically happened on the
            # bookmobile, so staff-operation rules apply (no card/fine
            # block; deceased/blocked still surfaces as a sync failure).
            result = await create_checkout(
                user=patron,
                item_id=item.id,
                db=db,
                item_copy_id=copy.id if copy else None,
                is_staff_operation=True,
            )
            # Backdate the transaction to when it actually happened on the
            # bookmobile so circulation reports reflect reality. Due date is
            # recomputed from the offline timestamp + the loan period that
            # create_checkout already applied.
            if result.checkout.due_date and result.checkout.checked_out_at:
                delta = result.checkout.due_date - result.checkout.checked_out_at
                result.checkout.checked_out_at = op_when
                result.checkout.due_date = op_when + delta
            else:
                result.checkout.checked_out_at = op_when
            await db.flush()
            return "synced", None, result.release_lock

        if op.type == "checkin":
            checkout_q = await db.execute(
                select(Checkout)
                .where(
                    Checkout.item_id == item.id,
                    Checkout.status.in_(
                        [CheckoutStatus.active, CheckoutStatus.overdue]
                        ),
                    )
                .order_by(Checkout.checked_out_at.desc())
                .limit(1)
            )
            checkout = checkout_q.scalar_one_or_none()
            if checkout is None:
                return "conflict", f"No active checkout for item {op.item_barcode}", None
            patron_q = await db.execute(
                select(User).where(User.id == checkout.user_id).limit(1)
            )
            patron = patron_q.scalar_one_or_none()
            if patron is None:
                return "failed", "Checkout references a missing patron", None
            await return_checkout(checkout=checkout, db=db, user=patron)
            checkout.returned_at = op_when
            await db.flush()
            return "synced", None, None

        if op.type == "renew":
            patron_for_renew = await _lookup_patron(db, op.patron_barcode)
            checkout_q = await db.execute(
                select(Checkout)
                .where(
                    Checkout.item_id == item.id,
                    Checkout.status.in_(
                        [CheckoutStatus.active, CheckoutStatus.overdue]
                        ),
                    )
                .order_by(Checkout.checked_out_at.desc())
                .limit(1)
            )
            checkout = checkout_q.scalar_one_or_none()
            if checkout is None:
                return "conflict", f"No active checkout for item {op.item_barcode}", None
            if patron_for_renew is None:
                patron_q = await db.execute(
                    select(User).where(User.id == checkout.user_id).limit(1)
                    )
                patron_for_renew = patron_q.scalar_one_or_none()
                if patron_for_renew is None:
                    return "failed", "Checkout references a missing patron", None
            await renew_checkout(
                checkout=checkout, user=patron_for_renew, db=db,
                is_staff_operation=True,
            )
            return "synced", None, None

        return "failed", f"Unknown operation type: {op.type}", None

    @staticmethod
    async def validate_offline_token(
        db: AsyncSession, offline_token: str
    ) -> Optional[OfflineSyncSession]:
        result = await db.execute(
            select(OfflineSyncSession).where(
                and_(
                    OfflineSyncSession.offline_session_token == offline_token,
                    OfflineSyncSession.status.in_(["departed", "returned"]),
                    )
            )
        )
        return result.scalar_one_or_none()
