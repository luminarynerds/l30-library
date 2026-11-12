# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import uuid
from datetime import datetime, time, timedelta, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.error_codes import ErrorCode
from ..core.branch_resolver import label_to_branch_id
from ..core.exceptions import ConflictError, ResourceNotFoundError

from ..models.book_drop import (
    BookDrop, BookDropStatus, BackdateMode,
    CheckInSession, CheckInSessionStatus,
    CheckInResult, CheckInResultStatus,
    CheckInStatistic, CheckInException,
    ExceptionType, SortDestination
)
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.inventory import ItemCopy, ItemCondition
from ..models.user import User
from ..models.fine import Fine, FineType, FineStatus
from ..models.lifecycle import ItemLifecycleEvent, LifecycleEventType
from ..models.patron_communication import PatronNote, NoteCategory, NotePriority
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class BookDropService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Book Drop Management
    # =========================================================================

    async def create_book_drop(
        self,
        name: str,
        code: str,
        branch_location: str,
        created_by: User,
        branch_id: Optional[int] = None,
        **kwargs
    ) -> BookDrop:
        if branch_id is None and branch_location:
            branch_id = label_to_branch_id(branch_location)
        # Check for duplicate code
        existing = await self.db.execute(
            select(BookDrop).where(BookDrop.code == code)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(
                code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                message=f"Book drop with code '{code}' already exists"
            )

        book_drop = BookDrop(
            name=name,
            code=code,
            branch_id=branch_id,
            branch_location=branch_location,
            created_by_id=created_by.id,
            **kwargs
        )
        self.db.add(book_drop)
        await self.db.flush()

        logger.info(f"Created book drop: {code} at {branch_location}")
        return book_drop

    async def get_book_drop(self, book_drop_id: int) -> Optional[BookDrop]:
        result = await self.db.execute(
            select(BookDrop).where(BookDrop.id == book_drop_id)
        )
        return result.scalar_one_or_none()

    async def get_book_drop_by_code(self, code: str) -> Optional[BookDrop]:
        result = await self.db.execute(
            select(BookDrop).where(BookDrop.code == code)
        )
        return result.scalar_one_or_none()

    async def list_book_drops(
        self,
        branch_location: Optional[str] = None,
        status_filter: Optional[BookDropStatus] = None,
        limit: int = 100,
        offset: int = 0,
        branch_id: Optional[int] = None,
    ) -> tuple[list[BookDrop], int]:
        if branch_id is None and branch_location:
            branch_id = label_to_branch_id(branch_location)
        query = select(BookDrop)
        if branch_id is not None:
            query = query.where(BookDrop.branch_id == branch_id)

        if status_filter:
            query = query.where(BookDrop.status == status_filter)

        # Get total count
        count_query = select(func.count(BookDrop.id))
        if branch_id is not None:
            count_query = count_query.where(BookDrop.branch_id == branch_id)
        if status_filter:
            count_query = count_query.where(BookDrop.status == status_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get items
        query = query.order_by(BookDrop.name).limit(limit).offset(offset)
        result = await self.db.execute(query)
        book_drops = list(result.scalars().all())

        return book_drops, total

    async def update_book_drop(
        self,
        book_drop_id: int,
        **updates
    ) -> BookDrop:
        book_drop = await self.get_book_drop(book_drop_id)
        if not book_drop:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Book drop not found"
            )

        for key, value in updates.items():
            if value is not None and hasattr(book_drop, key):
                setattr(book_drop, key, value)

        await self.db.flush()
        return book_drop

    # =========================================================================
    # Backdating Calculations
    # =========================================================================

    def calculate_backdate(
        self,
        book_drop: BookDrop,
        current_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        if current_time is None:
            current_time = utc_now()

        if book_drop.backdate_mode == BackdateMode.NONE:
            return None

        # Check if current day is in backdate_days
        current_day = current_time.weekday()
        if book_drop.backdate_days and current_day not in book_drop.backdate_days:
            return None

        if book_drop.backdate_mode == BackdateMode.FIXED_TIME:
            return self._calculate_fixed_time_backdate(book_drop, current_time)

        elif book_drop.backdate_mode == BackdateMode.PROCESSING_SCHEDULE:
            return self._calculate_processing_schedule_backdate(book_drop, current_time)

        elif book_drop.backdate_mode == BackdateMode.CUSTOM_HOURS:
            if book_drop.backdate_hours:
                backdate = current_time - timedelta(hours=book_drop.backdate_hours)
                # Don't exceed max backdate hours
                max_backdate = current_time - timedelta(hours=book_drop.max_backdate_hours)
                return max(backdate, max_backdate)

        return None

    def _calculate_fixed_time_backdate(
        self,
        book_drop: BookDrop,
        current_time: datetime
    ) -> Optional[datetime]:
        if not book_drop.backdate_fixed_time:
            return None

        # If we have a processing start time and current time is before it
        if book_drop.processing_start_time:
            current_time_only = current_time.time()

            if current_time_only < book_drop.processing_start_time:
                # Backdate to previous day's fixed time
                previous_day = current_time.date() - timedelta(days=1)
                backdate = datetime.combine(
                    previous_day,
                    book_drop.backdate_fixed_time,
                    tzinfo=current_time.tzinfo
                )

                # Ensure we don't exceed max backdate hours
                max_backdate = current_time - timedelta(hours=book_drop.max_backdate_hours)
                return max(backdate, max_backdate)

        return None

    def _calculate_processing_schedule_backdate(
        self,
        book_drop: BookDrop,
        current_time: datetime
    ) -> Optional[datetime]:
        if not book_drop.processing_end_time:
            return None

        current_time_only = current_time.time()

        # If before today's processing start, use yesterday's end time
        if (book_drop.processing_start_time and
                current_time_only < book_drop.processing_start_time):
            previous_day = current_time.date() - timedelta(days=1)
            backdate = datetime.combine(
                previous_day,
                book_drop.processing_end_time,
                tzinfo=current_time.tzinfo
            )
        else:
            # Use today's processing end time if we're past it
            if current_time_only > book_drop.processing_end_time:
                backdate = datetime.combine(
                    current_time.date(),
                    book_drop.processing_end_time,
                    tzinfo=current_time.tzinfo
                )
            else:
                # We're within processing window, no backdating needed
                return None

        # Ensure we don't exceed max backdate hours
        max_backdate = current_time - timedelta(hours=book_drop.max_backdate_hours)
        return max(backdate, max_backdate)

    # =========================================================================
    # Check-in Processing
    # =========================================================================

    async def process_checkin(
        self,
        session: CheckInSession,
        barcode: str,
        staff: User,
        condition_status: Optional[str] = None,
        condition_notes: Optional[str] = None,
        override_backdate: Optional[datetime] = None
    ) -> CheckInResult:
        result = CheckInResult(
            session_id=session.id,
            barcode=barcode,
            checked_in_at=utc_now()
        )

        # Calculate effective check-in time
        if override_backdate:
            result.effective_checkin_time = override_backdate
        elif session.use_backdating and session.backdate_to:
            result.effective_checkin_time = session.backdate_to
        else:
            result.effective_checkin_time = result.checked_in_at

        try:
            # Step 1: Find item by barcode
            item_copy = await self._find_item_by_barcode(barcode)
            if not item_copy:
                result.status = CheckInResultStatus.ITEM_NOT_FOUND
                result.exception_type = ExceptionType.OTHER
                result.exception_message = f"No item found with barcode: {barcode}"
                self.db.add(result)
                await self._update_session_stats(session, result)
                return result

            result.item_copy_id = item_copy.id

            # Step 2: Find active checkout
            checkout = await self._find_active_checkout(item_copy.id)
            if not checkout:
                result.status = CheckInResultStatus.NOT_CHECKED_OUT
                # Item exists but wasn't checked out - still allow for sorting
                await self._handle_not_checked_out(result, item_copy)
                self.db.add(result)
                await self._update_session_stats(session, result)
                return result

            result.checkout_id = checkout.id

            # Step 3: Check for exceptions (patron blocked, notes, etc.)
            exceptions = await self._check_for_exceptions(checkout, item_copy)

            # Step 4: Calculate overdue and fines
            await self._process_overdue_and_fines(
                result, checkout, item_copy,
                session.book_drop.exempt_overnight_fines if session.book_drop else False
            )

            # Step 5: Process the return - mark checkout as returned
            checkout.status = CheckoutStatus.returned
            checkout.returned_at = utc_now()

            # Step 6: Check for holds (hold trap)
            hold = await self._check_and_trap_hold(result, item_copy)

            # Step 7: Check for transit (item belongs to another branch)
            needs_transit = await self._check_for_transit(
                result, item_copy, session.branch_location
            )

            # Step 8: Determine final status and sort destination
            await self._determine_final_status(
                result, hold, needs_transit, exceptions
            )

            # Step 9: Handle condition check
            if condition_status:
                await self._record_condition_check(
                    result, item_copy, condition_status, condition_notes, staff
                )

            # Step 10: Create exceptions records
            for exc in exceptions:
                await self._create_exception_record(result, exc)

            # Step 11: Create lifecycle event
            await self._create_lifecycle_event(
                item_copy, checkout, staff, result, session
            )

            # Step 12: Log activity for the patron's reading shelf feed
            if item_copy.catalog_item:
                from .reading_activity_service import ReadingActivityService
                await ReadingActivityService.log_book_returned(
                    self.db,
                    user_id=checkout.user_id,
                    catalog_item_id=item_copy.catalog_item.id,
                    title=item_copy.catalog_item.title,
                )

            self.db.add(result)
            await self._update_session_stats(session, result)

            logger.info(
                f"Check-in completed: barcode={barcode}, "
                f"status={result.status}, session={session.session_code}"
            )

            return result

        except Exception as e:
            logger.error(f"Check-in error for {barcode}: {e}", exc_info=True)
            result.status = CheckInResultStatus.EXCEPTION
            result.exception_type = ExceptionType.OTHER
            result.exception_message = str(e)
            self.db.add(result)
            await self._update_session_stats(session, result)
            return result

    async def _find_item_by_barcode(self, barcode: str) -> Optional[ItemCopy]:
        result = await self.db.execute(
            select(ItemCopy)
            .options(selectinload(ItemCopy.catalog_item))
            .where(ItemCopy.barcode == barcode)
        )
        return result.scalar_one_or_none()

    async def _find_active_checkout(self, item_copy_id: int) -> Optional[Checkout]:
        result = await self.db.execute(
            select(Checkout)
            .options(selectinload(Checkout.user))
            .where(
                Checkout.item_copy_id == item_copy_id,
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue])
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def _handle_not_checked_out(
        self,
        result: CheckInResult,
        item_copy: ItemCopy
    ) -> None:
        # Still determine sort destination based on holds/location
        hold = await self._check_and_trap_hold(result, item_copy)
        if hold:
            result.sort_destination = SortDestination.HOLD_SHELF
        else:
            result.sort_destination = SortDestination.RESHELVE

    async def _check_for_exceptions(
        self,
        checkout: Checkout,
        item_copy: ItemCopy
    ) -> list[dict]:
        exceptions = []

        # Check patron status
        if checkout.user:
            patron = checkout.user
            if not patron.is_active:
                exceptions.append({
                    "type": ExceptionType.PATRON_BLOCKED,
                    "message": f"Patron account is blocked: {patron.first_name} {patron.last_name}",
                    "data": {"patron_id": patron.id},
                    "severity": "high"
                })

            # Check for patron notes. PatronNote has no `is_alert` column
            # (it never existed on the model) -- this raised AttributeError
            # on every book-drop return that reached a patron with any
            # notes at all. HIGH/URGENT priority is the model's actual
            # equivalent of an "alert-worthy" note.
            patron_notes = await self.db.execute(
                select(PatronNote)
                .where(
                    PatronNote.patron_id == patron.id,
                    PatronNote.priority.in_([NotePriority.HIGH, NotePriority.URGENT])
                )
            )
            notes = patron_notes.scalars().all()
            for note in notes:
                exceptions.append({
                    "type": ExceptionType.PATRON_NOTE,
                    "message": f"Patron note: {note.content[:100]}",
                    "data": {"note_id": note.id, "category": str(note.category)},
                    "severity": "normal"
                })

        # Check item notes
        if item_copy.notes:
            exceptions.append({
                "type": ExceptionType.ITEM_NOTE,
                "message": f"Item note: {item_copy.notes[:100]}",
                "data": {"item_copy_id": item_copy.id},
                "severity": "normal"
            })

        # Check for damage
        if item_copy.condition == ItemCondition.DAMAGED:
            exceptions.append({
                "type": ExceptionType.DAMAGED_ITEM,
                "message": "Item is marked as damaged",
                "data": {"condition": str(item_copy.condition)},
                "severity": "high"
            })

        # Check for lost item being returned
        if checkout.status == CheckoutStatus.lost:
            exceptions.append({
                "type": ExceptionType.LOST_ITEM_RETURNED,
                "message": "Previously lost item has been returned",
                "data": {"checkout_id": checkout.id},
                "severity": "high"
            })

        return exceptions

    async def _process_overdue_and_fines(
        self,
        result: CheckInResult,
        checkout: Checkout,
        item_copy: ItemCopy,
        exempt_overnight_fines: bool
    ) -> None:
        effective_time = result.effective_checkin_time or result.checked_in_at

        # Check if overdue based on effective check-in time
        if checkout.due_date < effective_time:
            result.was_overdue = True
            result.overdue_days = (effective_time.date() - checkout.due_date.date()).days

            # Calculate fine (simplified - could use FinePolicy)
            daily_rate = Decimal("0.25")
            result.fine_amount = daily_rate * result.overdue_days

            # Check if fine should be waived due to backdating
            if (exempt_overnight_fines and
                    result.effective_checkin_time != result.checked_in_at):
                # Check if item would have been overdue at actual check-in time
                actual_overdue_days = (
                    result.checked_in_at.date() - checkout.due_date.date()
                ).days

                if actual_overdue_days > result.overdue_days:
                    # Backdating reduced overdue days
                    result.fine_waived_by_backdate = True

                    # Create fine only for non-waived portion
                    if result.overdue_days > 0:
                        await self._create_fine(
                            checkout, result.fine_amount,
                            f"Overdue fine ({result.overdue_days} days)"
                        )
                else:
                    # Create full fine
                    if result.fine_amount > 0:
                        await self._create_fine(
                            checkout, result.fine_amount,
                            f"Overdue fine ({result.overdue_days} days)"
                        )
            else:
                # No backdate exemption, create full fine
                if result.fine_amount > 0:
                    await self._create_fine(
                        checkout, result.fine_amount,
                        f"Overdue fine ({result.overdue_days} days)"
                    )

    async def _create_fine(
        self,
        checkout: Checkout,
        amount: Decimal,
        description: str
    ) -> Fine:
        fine = Fine(
            user_id=checkout.user_id,
            checkout_id=checkout.id,
            item_id=checkout.item_id,
            fine_type=FineType.overdue,
            amount=amount,
            description=description,
            status=FineStatus.unpaid
        )
        self.db.add(fine)
        return fine

    async def _check_and_trap_hold(
        self,
        result: CheckInResult,
        item_copy: ItemCopy
    ) -> Optional[Hold]:
        # Get the catalog item ID
        if not item_copy.catalog_item_id:
            return None

        # Find next pending hold
        hold_result = await self.db.execute(
            select(Hold)
            .options(selectinload(Hold.user))
            .where(
                Hold.item_id == item_copy.catalog_item_id,
                Hold.status == HoldStatus.pending
            )
            .order_by(Hold.position)
            .with_for_update()
        )
        hold = hold_result.scalar_one_or_none()

        if hold:
            # Trap the hold
            hold.status = HoldStatus.ready
            hold.notified_at = utc_now()
            # Default 7-day hold expiry
            hold.expires_at = utc_now() + timedelta(days=7)

            result.hold_id = hold.id
            result.hold_patron_id = hold.user_id
            result.sort_destination = SortDestination.HOLD_SHELF

            # Rederive title status (other copies may still be free)
            if item_copy.catalog_item:
                from .hold_service import recompute_title_availability

                await recompute_title_availability(item_copy.catalog_item, self.db)

            logger.info(
                f"Hold trapped: item_copy={item_copy.id}, "
                f"hold={hold.id}, patron={hold.user_id}"
            )

            return hold

        return None

    async def _check_for_transit(
        self,
        result: CheckInResult,
        item_copy: ItemCopy,
        current_branch: str
    ) -> bool:
        # Compare item's home location with current branch
        home_location = item_copy.location or ""

        # Simple check - if location doesn't start with current branch
        # In a real system, this would use a proper branch/location mapping
        if home_location and not home_location.startswith(current_branch):
            result.destination_branch = home_location.split()[0] if home_location else "Unknown"
            result.sort_destination = SortDestination.TRANSIT

            # Update item status
            if item_copy.catalog_item:
                item_copy.catalog_item.status = ItemStatus.in_transit

            return True

        return False

    def should_prompt_damage_check(self, result: CheckInResult, exceptions: list[dict]) -> bool:
        # If item already marked as damaged in exceptions
        damage_exceptions = [e for e in exceptions if e.get("type") == ExceptionType.DAMAGED_ITEM]
        if damage_exceptions:
            return True

        # If returned after loss, might need inspection
        if any(e.get("type") == ExceptionType.LOST_ITEM_RETURNED for e in exceptions):
            return True

        return False

    async def get_destination_summary(self, session_id: int) -> dict:
        results = await self.get_session_results(session_id, limit=10000)

        summary = {
            "shelve": 0,
            "holds": 0,
            "transit": 0,
            "exceptions": 0,
            "total": len(results)
        }

        for result in results:
            if result.sort_destination == SortDestination.RESHELVE:
                summary["shelve"] += 1
            elif result.sort_destination == SortDestination.HOLD_SHELF:
                summary["holds"] += 1
            elif result.sort_destination == SortDestination.TRANSIT:
                summary["transit"] += 1
            elif result.sort_destination in [SortDestination.EXCEPTION, SortDestination.CONDITION_CHECK]:
                summary["exceptions"] += 1

        return summary

    async def mark_claims_returned_resolved(
        self,
        result: CheckInResult,
        resolution_notes: str,
        resolved_by: User
    ) -> CheckInResult:
        result.exception_resolved = True
        result.resolved_by_id = resolved_by.id
        result.resolved_at = utc_now()
        result.resolution_notes = resolution_notes

        # Find and update the related exception
        exception_result = await self.db.execute(
            select(CheckInException)
            .where(CheckInException.check_in_result_id == result.id)
        )
        exception = exception_result.scalar_one_or_none()

        if exception:
            exception.resolved = True
            exception.resolved_by_id = resolved_by.id
            exception.resolved_at = utc_now()
            exception.action_taken = resolution_notes

        logger.info(
            f"Resolved claims returned for check-in result {result.id}: {resolution_notes}"
        )

        return result

    async def _determine_final_status(
        self,
        result: CheckInResult,
        hold: Optional[Hold],
        needs_transit: bool,
        exceptions: list[dict]
    ) -> None:
        if exceptions:
            # Has exceptions - prioritize based on severity
            high_severity = [e for e in exceptions if e.get("severity") == "high"]
            if high_severity:
                result.status = CheckInResultStatus.EXCEPTION
                result.exception_type = high_severity[0]["type"]
                result.exception_message = high_severity[0]["message"]
                result.sort_destination = SortDestination.EXCEPTION
            else:
                # Low/normal severity exceptions - still process normally
                result.status = CheckInResultStatus.SUCCESS
                if hold:
                    result.status = CheckInResultStatus.HOLD_TRAPPED
                elif needs_transit:
                    result.status = CheckInResultStatus.TRANSIT_REQUIRED

        elif hold:
            result.status = CheckInResultStatus.HOLD_TRAPPED
            result.sort_destination = SortDestination.HOLD_SHELF

        elif needs_transit:
            result.status = CheckInResultStatus.TRANSIT_REQUIRED
            result.sort_destination = SortDestination.TRANSIT

        else:
            result.status = CheckInResultStatus.SUCCESS
            result.sort_destination = SortDestination.RESHELVE

            # Rederive title status now that this copy is back in circulation
            item_copy_result = await self.db.execute(
                select(ItemCopy)
                .options(selectinload(ItemCopy.catalog_item))
                .where(ItemCopy.id == result.item_copy_id)
            )
            item_copy = item_copy_result.scalar_one_or_none()
            if item_copy and item_copy.catalog_item:
                from .hold_service import recompute_title_availability

                await recompute_title_availability(item_copy.catalog_item, self.db)

    async def _record_condition_check(
        self,
        result: CheckInResult,
        item_copy: ItemCopy,
        condition_status: str,
        condition_notes: Optional[str],
        staff: User
    ) -> None:
        result.condition_checked = True
        result.condition_status = condition_status
        result.condition_notes = condition_notes

        # Check if condition changed
        old_condition = item_copy.condition

        # Map string to enum
        condition_map = {
            "new": ItemCondition.NEW,
            "good": ItemCondition.GOOD,
            "fair": ItemCondition.FAIR,
            "poor": ItemCondition.POOR,
            "damaged": ItemCondition.DAMAGED
        }

        new_condition = condition_map.get(condition_status.lower())
        if new_condition and new_condition != old_condition:
            item_copy.condition = new_condition

            # If now damaged, flag for exception
            if new_condition == ItemCondition.DAMAGED:
                result.status = CheckInResultStatus.CONDITION_ISSUE
                result.sort_destination = SortDestination.CONDITION_CHECK
                result.exception_type = ExceptionType.DAMAGED_ITEM
                result.exception_message = condition_notes or "Item condition changed to damaged"

    async def _create_exception_record(
        self,
        result: CheckInResult,
        exception_data: dict
    ) -> CheckInException:
        exception = CheckInException(
            check_in_result_id=result.id,
            exception_type=exception_data["type"],
            severity=exception_data.get("severity", "normal"),
            item_copy_id=result.item_copy_id,
            title=exception_data["message"][:255],
            description=exception_data["message"],
            exception_data=exception_data.get("data", {}),
            requires_action=exception_data.get("severity") == "high"
        )
        self.db.add(exception)
        return exception

    async def _create_lifecycle_event(
        self,
        item_copy: ItemCopy,
        checkout: Checkout,
        staff: User,
        result: CheckInResult,
        session: CheckInSession
    ) -> None:
        event = ItemLifecycleEvent(
            item_copy_id=item_copy.id,
            event_type=LifecycleEventType.RETURNED,
            description=f"Checked in via session {session.session_code}",
            event_metadata={
                "session_id": session.id,
                "book_drop_id": session.book_drop_id,
                "backdated": result.effective_checkin_time != result.checked_in_at,
                "effective_time": result.effective_checkin_time.isoformat() if result.effective_checkin_time else None,
                "was_overdue": result.was_overdue,
                "fine_amount": str(result.fine_amount) if result.fine_amount else "0",
                "hold_trapped": result.hold_id is not None,
                "transit_required": result.destination_branch is not None
            },
            performed_by_id=staff.id,
            related_checkout_id=checkout.id
        )
        self.db.add(event)

    async def _update_session_stats(
        self,
        session: CheckInSession,
        result: CheckInResult
    ) -> None:
        session.total_items += 1

        if result.status == CheckInResultStatus.SUCCESS:
            session.successful_checkins += 1
        elif result.status == CheckInResultStatus.HOLD_TRAPPED:
            session.successful_checkins += 1
            session.holds_trapped += 1
        elif result.status == CheckInResultStatus.TRANSIT_REQUIRED:
            session.successful_checkins += 1
            session.transits_created += 1
        elif result.status in [
            CheckInResultStatus.EXCEPTION,
            CheckInResultStatus.CONDITION_ISSUE
        ]:
            session.exceptions_count += 1

    # =========================================================================
    # Session Management
    # =========================================================================

    async def start_session(
        self,
        staff: User,
        branch_location: str,
        book_drop_id: Optional[int] = None,
        workstation_id: Optional[str] = None
    ) -> CheckInSession:
        session_code = f"CKI-{uuid.uuid4().hex[:8].upper()}"

        session = CheckInSession(
            session_code=session_code,
            book_drop_id=book_drop_id,
            branch_location=branch_location,
            workstation_id=workstation_id,
            staff_id=staff.id,
            status=CheckInSessionStatus.ACTIVE
        )

        # Calculate backdating if book drop specified
        if book_drop_id:
            book_drop = await self.get_book_drop(book_drop_id)
            if book_drop:
                backdate = self.calculate_backdate(book_drop)
                if backdate:
                    session.use_backdating = True
                    session.backdate_to = backdate

        self.db.add(session)
        await self.db.flush()

        logger.info(
            f"Started check-in session: {session_code}, "
            f"branch={branch_location}, book_drop={book_drop_id}"
        )

        return session

    async def end_session(self, session_id: int) -> CheckInSession:
        result = await self.db.execute(
            select(CheckInSession)
            .where(CheckInSession.id == session_id)
            .with_for_update()
        )
        session = result.scalar_one_or_none()

        if not session:
            raise ResourceNotFoundError(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Session not found"
            )

        session.status = CheckInSessionStatus.COMPLETED
        session.ended_at = utc_now()

        # Update statistics
        await self._update_hourly_statistics(session)

        logger.info(
            f"Ended check-in session: {session.session_code}, "
            f"items={session.total_items}"
        )

        return session

    async def get_session(self, session_id: int) -> Optional[CheckInSession]:
        result = await self.db.execute(
            select(CheckInSession)
            .options(selectinload(CheckInSession.book_drop))
            .where(CheckInSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_session_results(
        self,
        session_id: int,
        status_filter: Optional[CheckInResultStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[CheckInResult]:
        query = (
            select(CheckInResult)
            .where(CheckInResult.session_id == session_id)
        )

        if status_filter:
            query = query.where(CheckInResult.status == status_filter)

        query = query.order_by(CheckInResult.checked_in_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Statistics
    # =========================================================================

    async def _update_hourly_statistics(self, session: CheckInSession) -> None:
        # Get results grouped by hour
        results = await self.get_session_results(session.id, limit=10000)

        for result in results:
            check_time = result.checked_in_at
            stat_date = check_time.date()
            stat_hour = check_time.hour
            day_of_week = check_time.weekday()

            # Find or create statistic record
            if session.branch_id is not None:
                stat_filter_branch = CheckInStatistic.branch_id == session.branch_id
            else:
                stat_filter_branch = CheckInStatistic.branch_location == session.branch_location
            stat_result = await self.db.execute(
                select(CheckInStatistic).where(
                    CheckInStatistic.date == stat_date,
                    CheckInStatistic.hour == stat_hour,
                    stat_filter_branch,
                    CheckInStatistic.book_drop_id == session.book_drop_id
                )
            )
            stat = stat_result.scalar_one_or_none()

            if not stat:
                stat = CheckInStatistic(
                    date=stat_date,
                    hour=stat_hour,
                    day_of_week=day_of_week,
                    branch_id=session.branch_id,
                    branch_location=session.branch_location,
                    book_drop_id=session.book_drop_id
                )
                self.db.add(stat)

            # Update counts
            stat.total_checkins += 1
            if session.book_drop_id:
                stat.book_drop_checkins += 1
            else:
                stat.staff_checkins += 1

            if result.status == CheckInResultStatus.SUCCESS:
                stat.successful_count += 1
            elif result.status == CheckInResultStatus.HOLD_TRAPPED:
                stat.holds_trapped_count += 1
            elif result.status == CheckInResultStatus.TRANSIT_REQUIRED:
                stat.transits_count += 1
            elif result.status == CheckInResultStatus.EXCEPTION:
                stat.exceptions_count += 1

            if result.was_overdue:
                stat.overdue_items_count += 1
                stat.total_fines_amount += result.fine_amount or Decimal(0)

            if result.fine_waived_by_backdate:
                # Calculate waived amount (simplified)
                stat.fines_waived_amount += result.fine_amount or Decimal(0)

    async def get_statistics(
        self,
        start_date: date,
        end_date: date,
        branch_location: Optional[str] = None,
        book_drop_id: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> list[CheckInStatistic]:
        if branch_id is None and branch_location:
            from ..core.branch_resolver import label_to_branch_id
            branch_id = label_to_branch_id(branch_location)

        query = select(CheckInStatistic).where(
            CheckInStatistic.date >= start_date,
            CheckInStatistic.date <= end_date
        )

        if branch_id is not None:
            query = query.where(CheckInStatistic.branch_id == branch_id)
        elif branch_location:
            query = query.where(CheckInStatistic.branch_location == branch_location)
        if book_drop_id:
            query = query.where(CheckInStatistic.book_drop_id == book_drop_id)

        query = query.order_by(CheckInStatistic.date, CheckInStatistic.hour)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_statistics_summary(
        self,
        start_date: date,
        end_date: date,
        branch_location: Optional[str] = None
    ) -> dict:
        stats = await self.get_statistics(start_date, end_date, branch_location)

        if not stats:
            return {
                "period_start": start_date,
                "period_end": end_date,
                "total_checkins": 0
            }

        total_checkins = sum(s.total_checkins for s in stats)
        days = (end_date - start_date).days + 1

        # Find peak hour
        hourly_totals = {}
        daily_totals = {}
        for s in stats:
            hourly_totals[s.hour] = hourly_totals.get(s.hour, 0) + s.total_checkins
            daily_totals[s.day_of_week] = daily_totals.get(s.day_of_week, 0) + s.total_checkins

        peak_hour = max(hourly_totals, key=hourly_totals.get) if hourly_totals else 0
        peak_day = max(daily_totals, key=daily_totals.get) if daily_totals else 0

        return {
            "period_start": start_date,
            "period_end": end_date,
            "branch_location": branch_location,
            "total_checkins": total_checkins,
            "avg_daily_checkins": total_checkins / days if days > 0 else 0,
            "peak_hour": peak_hour,
            "peak_day_of_week": peak_day,
            "holds_trapped_total": sum(s.holds_trapped_count for s in stats),
            "transits_total": sum(s.transits_count for s in stats),
            "exceptions_total": sum(s.exceptions_count for s in stats),
            "total_fines": sum(s.total_fines_amount for s in stats),
            "total_fines_waived": sum(s.fines_waived_amount for s in stats),
            "staff_checkins_pct": (
                sum(s.staff_checkins for s in stats) / total_checkins * 100
                if total_checkins > 0 else 0
            ),
            "book_drop_checkins_pct": (
                sum(s.book_drop_checkins for s in stats) / total_checkins * 100
                if total_checkins > 0 else 0
            ),
            "self_service_checkins_pct": (
                sum(s.self_service_checkins for s in stats) / total_checkins * 100
                if total_checkins > 0 else 0
            )
        }
