# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
from app.core.logging import get_logger
import secrets
import socket
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, Integer, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.error_codes import ErrorCode
from ..core.exceptions import (
    APIError,
    BusinessLogicError,
    ConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus
from ..models.inventory import ItemCopy, InventoryAudit, AuditScan, ItemCondition
from ..models.rfid import (
    RFIDReader, RFIDReaderStatus, RFIDReaderType, RFIDProtocol,
    RFIDTag, RFIDSession, RFIDSessionType, RFIDScan,
    SecurityAlert, SecurityAlertType,
)
from ..models.user import User, UserRole
from .checkout_service import create_checkout, return_checkout, send_pending_hold_notification
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


# ============ SIP2 Protocol Implementation ============


class SIP2Client:

    # SIP2 Message codes
    PATRON_STATUS_REQUEST = "23"
    PATRON_STATUS_RESPONSE = "24"
    CHECKOUT = "11"
    CHECKOUT_RESPONSE = "12"
    CHECKIN = "09"
    CHECKIN_RESPONSE = "10"
    ITEM_INFO_REQUEST = "17"
    ITEM_INFO_RESPONSE = "18"
    SC_STATUS = "99"
    ACS_STATUS = "98"

    def __init__(self, host: str, port: int, institution_id: str = "LSC",
                 terminal_password: str = "", timeout: float = 5.0):
        self.host = host
        self.port = port
        self.institution_id = institution_id
        self.terminal_password = terminal_password
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._sequence = 0

    async def connect(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            await loop.run_in_executor(
                None, self._socket.connect, (self.host, self.port)
            )
            logger.info(f"SIP2 connected to {self.host}:{self.port}")
            return True
        except (socket.error, ConnectionError, OSError, TimeoutError) as e:
            logger.error(
                f"SIP2 connection failed: {e}",
                extra={"error_type": type(e).__name__, "host": self.host, "port": self.port},
            )
            return False

    async def disconnect(self):
        if self._socket:
            # Socket cleanup errors are non-critical.
            with contextlib.suppress(socket.error, OSError):
                self._socket.close()
            self._socket = None

    def _build_message(self, command: str, fields: dict) -> str:
        self._sequence = (self._sequence + 1) % 10

        message_parts = [command]
        for key, value in fields.items():
            if value is not None:
                message_parts.append(f"{key}{value}|")

        message = "".join(message_parts)
        # Add sequence and checksum
        message += f"AY{self._sequence}AZ"
        checksum = self._calculate_checksum(message)
        message += checksum
        return message + "\r"

    def _calculate_checksum(self, message: str) -> str:
        total = sum(ord(c) for c in message)
        checksum = (~total + 1) & 0xFFFF
        return f"{checksum:04X}"

    def _parse_response(self, response: str) -> dict:
        result = {"raw": response, "code": response[:2] if len(response) >= 2 else ""}

        # Parse fixed fields based on response type
        # Parse variable fields (|XX value|)
        parts = response.split("|")
        for part in parts[1:]:
            if len(part) >= 2:
                field_id = part[:2]
                field_value = part[2:]
                result[field_id] = field_value

        return result

    async def _send_receive(self, message: str) -> Optional[dict]:
        if not self._socket:
            return None

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._socket.sendall, message.encode("utf-8")
            )

            response = await loop.run_in_executor(
                None, self._socket.recv, 4096
            )
            return self._parse_response(response.decode("utf-8"))
        except Exception as e:  # noqa: BLE001 -- protocol boundary: socket/decode errors must not drop SIP2 connection state
            logger.error(f"SIP2 communication error: {e}")
            return None

    async def checkout_item(self, patron_id: str, item_barcode: str,
                           no_block: bool = False) -> dict:
        fields = {
            "AO": self.institution_id,
            "AA": patron_id,
            "AB": item_barcode,
            "AC": self.terminal_password,
        }

        # Build checkout message (11)
        now = utc_now()
        date_str = now.strftime("%Y%m%d    %H%M%S")
        nb_flag = "Y" if no_block else "N"

        message = f"{self.CHECKOUT}{nb_flag}N{date_str}"
        for key, value in fields.items():
            message += f"|{key}{value}"
        message += f"|AY{self._sequence}AZ"
        message += self._calculate_checksum(message) + "\r"

        response = await self._send_receive(message)
        if response and response.get("code") == self.CHECKOUT_RESPONSE:
            return {
                "success": response.get("raw", "")[2] == "1",
                "message": response.get("AF", ""),
                "due_date": response.get("AH", ""),
            }
        return {"success": False, "message": "SIP2 communication failed"}

    async def checkin_item(self, item_barcode: str,
                          return_location: str = "") -> dict:
        fields = {
            "AO": self.institution_id,
            "AB": item_barcode,
            "AC": self.terminal_password,
            "AP": return_location,
        }

        now = utc_now()
        date_str = now.strftime("%Y%m%d    %H%M%S")

        message = f"{self.CHECKIN}NN{date_str}{date_str}"
        for key, value in fields.items():
            if value:
                message += f"|{key}{value}"
        message += f"|AY{self._sequence}AZ"
        message += self._calculate_checksum(message) + "\r"

        response = await self._send_receive(message)
        if response and response.get("code") == self.CHECKIN_RESPONSE:
            return {
                "success": response.get("raw", "")[2] == "1",
                "message": response.get("AF", ""),
                "alert": response.get("raw", "")[3] == "Y",
            }
        return {"success": False, "message": "SIP2 communication failed"}

    async def get_item_info(self, item_barcode: str) -> dict:
        now = utc_now()
        date_str = now.strftime("%Y%m%d    %H%M%S")

        message = f"{self.ITEM_INFO_REQUEST}{date_str}"
        message += f"|AO{self.institution_id}"
        message += f"|AB{item_barcode}"
        message += f"|AC{self.terminal_password}"
        message += f"|AY{self._sequence}AZ"
        message += self._calculate_checksum(message) + "\r"

        response = await self._send_receive(message)
        if response and response.get("code") == self.ITEM_INFO_RESPONSE:
            return {
                "found": True,
                "title": response.get("AJ", ""),
                "circulation_status": response.get("raw", "")[2:4] if len(response.get("raw", "")) > 3 else "",
                "location": response.get("AQ", ""),
            }
        return {"found": False}


# ============ Reader Connection Manager ============


class RFIDReaderManager:

    _connections: dict[int, SIP2Client] = {}

    @classmethod
    async def get_client(cls, reader: RFIDReader) -> Optional[SIP2Client]:
        if reader.id in cls._connections:
            return cls._connections[reader.id]

        if reader.protocol == RFIDProtocol.SIP2:
            if not reader.ip_address or not reader.port:
                return None

            client = SIP2Client(
                host=reader.ip_address,
                port=reader.port,
                institution_id="LSC",
                terminal_password=reader.password or "",
            )

            if await client.connect():
                cls._connections[reader.id] = client
                return client

        # For other protocols, implement as needed
        return None

    @classmethod
    async def disconnect_reader(cls, reader_id: int):
        if reader_id in cls._connections:
            await cls._connections[reader_id].disconnect()
            del cls._connections[reader_id]

    @classmethod
    async def disconnect_all(cls):
        for client in cls._connections.values():
            await client.disconnect()
        cls._connections.clear()


# ============ Core RFID Service Functions ============


async def get_reader(db: AsyncSession, reader_id: int) -> RFIDReader:
    result = await db.execute(
        select(RFIDReader).where(RFIDReader.id == reader_id)
    )
    reader = result.scalar_one_or_none()
    if not reader:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="RFID reader not found")
    return reader


async def get_tag_by_id(db: AsyncSession, tag_id: str) -> Optional[RFIDTag]:
    result = await db.execute(
        select(RFIDTag)
        .where(RFIDTag.tag_id == tag_id.upper(), RFIDTag.is_active == True)
        .options(selectinload(RFIDTag.item_copy))
    )
    return result.scalar_one_or_none()


async def get_tag_by_barcode(db: AsyncSession, barcode: str) -> Optional[RFIDTag]:
    result = await db.execute(
        select(RFIDTag)
        .where(RFIDTag.item_barcode == barcode, RFIDTag.is_active == True)
    )
    return result.scalar_one_or_none()


async def resolve_tag_to_item(db: AsyncSession, tag_id: str) -> Optional[tuple[RFIDTag, ItemCopy, CatalogItem]]:
    result = await db.execute(
        select(RFIDTag)
        .where(RFIDTag.tag_id == tag_id.upper(), RFIDTag.is_active == True)
    )
    tag = result.scalar_one_or_none()
    if not tag:
        return None

    # Get item copy
    copy_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.barcode == tag.item_barcode)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = copy_result.scalar_one_or_none()
    if not copy:
        return None

    return (tag, copy, copy.catalog_item)


# ============ Tag Programming ============


async def program_tag(
    db: AsyncSession,
    item_barcode: str,
    reader_id: int,
    user: User,
    tag_type: str = "ISO 15693",
    include_item_data: bool = True,
) -> dict:
    # Verify reader exists and is online
    reader = await get_reader(db, reader_id)
    if reader.status != RFIDReaderStatus.ONLINE:
        raise BusinessLogicError(
            code=ErrorCode.INVALID_STATE,
            message=f"Reader is not online (status: {reader.status})"
        )

    # Verify item exists
    copy_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.barcode == item_barcode)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = copy_result.scalar_one_or_none()
    if not copy:
        raise ResourceNotFoundError(code=ErrorCode.CATALOG_ITEM_NOT_FOUND, message="Item not found with this barcode")

    # Check if tag already exists for this barcode
    existing_tag = await get_tag_by_barcode(db, item_barcode)
    if existing_tag:
        raise ConflictError(
            code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            message="An active RFID tag already exists for this item"
        )

    # Generate unique tag ID (in production, this comes from the physical tag)
    tag_id = secrets.token_hex(12).upper()

    # Prepare tag data
    tag_data = {}
    if include_item_data and copy.catalog_item:
        tag_data = {
            "title": copy.catalog_item.title[:100] if copy.catalog_item.title else "",
            "author": copy.catalog_item.author[:50] if copy.catalog_item.author else "",
            "isbn": copy.catalog_item.isbn or "",
            "item_type": str(copy.catalog_item.item_type) if copy.catalog_item.item_type else "",
        }

    # Create tag record
    tag = RFIDTag(
        tag_id=tag_id,
        item_barcode=item_barcode,
        security_bit=True,  # Active by default
        eas_enabled=True,
        tag_type=tag_type,
        programmed_by_id=user.id,
        programmed_by_reader_id=reader_id,
        tag_data=tag_data,
    )
    db.add(tag)
    await db.flush()

    logger.info(f"Programmed RFID tag {tag_id} for item {item_barcode}")

    return {
        "success": True,
        "tag_id": tag_id,
        "message": f"Tag programmed successfully for {copy.catalog_item.title if copy.catalog_item else item_barcode}",
        "tag": tag,
    }


async def deactivate_tag(
    db: AsyncSession,
    tag_id: str,
    user: User,
    reason: str,
) -> RFIDTag:
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="RFID tag not found")

    tag.is_active = False
    tag.deactivated_at = utc_now()
    tag.deactivation_reason = reason

    logger.info(f"Deactivated RFID tag {tag_id}: {reason}")
    return tag


async def update_tag_security(
    db: AsyncSession,
    tag_id: str,
    security_bit: bool,
) -> RFIDTag:
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="RFID tag not found")

    tag.security_bit = security_bit
    tag.updated_at = utc_now()

    logger.info(f"Updated security bit for tag {tag_id} to {security_bit}")
    return tag


# ============ Session Management ============


async def create_session(
    db: AsyncSession,
    session_type: RFIDSessionType,
    reader_id: int,
    operator: User,
    patron_id: Optional[int] = None,
    inventory_audit_id: Optional[int] = None,
    target_location: Optional[str] = None,
) -> RFIDSession:
    # Verify reader exists
    await get_reader(db, reader_id)

    session = RFIDSession(
        session_type=session_type,
        reader_id=reader_id,
        operator_id=operator.id,
        patron_id=patron_id,
        inventory_audit_id=inventory_audit_id,
        target_location=target_location,
    )
    db.add(session)
    await db.flush()

    logger.info(f"Created RFID session {session.id} of type {session_type.value}")
    return session


async def end_session(db: AsyncSession, session_id: int) -> RFIDSession:
    result = await db.execute(
        select(RFIDSession).where(RFIDSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Session not found")

    if not session.is_active:
        raise BusinessLogicError(code=ErrorCode.INVALID_STATE, message="Session is already ended")

    session.is_active = False
    session.ended_at = utc_now()

    logger.info(f"Ended RFID session {session_id}")
    return session


async def record_scan(
    db: AsyncSession,
    session_id: int,
    tag_id: str,
    signal_strength: Optional[float] = None,
    antenna_id: Optional[int] = None,
    found_at_location: Optional[str] = None,
) -> RFIDScan:
    # Get session
    session_result = await db.execute(
        select(RFIDSession)
        .where(RFIDSession.id == session_id)
        .with_for_update()
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Session not found")

    if not session.is_active:
        raise BusinessLogicError(code=ErrorCode.INVALID_STATE, message="Session is not active")

    # Try to resolve tag
    tag_data = await resolve_tag_to_item(db, tag_id)

    scan = RFIDScan(
        session_id=session_id,
        tag_id=tag_id.upper(),
        signal_strength=signal_strength,
        antenna_id=antenna_id,
        found_at_location=found_at_location,
    )

    if tag_data:
        tag, copy, catalog_item = tag_data
        scan.rfid_tag_id = tag.id
        scan.item_barcode = tag.item_barcode
        scan.item_title = catalog_item.title if catalog_item else None
        scan.expected_location = copy.location

        # Check if misplaced
        if found_at_location and copy.location:
            scan.is_misplaced = found_at_location.lower() != copy.location.lower()

        # Update tag read stats
        tag.last_read_at = utc_now()
        tag.read_count += 1

    db.add(scan)
    session.tags_scanned += 1

    return scan


# ============ Batch Checkout ============


async def batch_checkout(
    db: AsyncSession,
    reader_id: int,
    patron_id: int,
    tag_ids: list[str],
    operator: User,
    progress_callback: Optional[callable] = None,
) -> dict:
    # Get patron
    patron_result = await db.execute(
        select(User).where(User.id == patron_id)
    )
    patron = patron_result.scalar_one_or_none()
    if not patron:
        raise ResourceNotFoundError(code=ErrorCode.PATRON_NOT_FOUND, message="Patron not found")

    # Create session
    session = await create_session(
        db=db,
        session_type=RFIDSessionType.BATCH_CHECKOUT,
        reader_id=reader_id,
        operator=operator,
        patron_id=patron_id,
    )

    results = []
    successful = 0
    failed = 0
    total = len(tag_ids)

    for idx, tag_id in enumerate(tag_ids):
        result = await _process_single_checkout(db, session.id, tag_id, patron, operator)
        results.append(result)
        if result["success"]:
            successful += 1
        else:
            failed += 1

        # Broadcast progress if callback provided
        if progress_callback:
            await progress_callback(
                session.id, total, idx + 1, successful, failed,
                {"tag_id": tag_id, **result}
            )

    # Update session stats
    session.tags_processed = successful
    session.tags_failed = failed

    # End session
    session.is_active = False
    session.ended_at = utc_now()

    return {
        "session_id": session.id,
        "patron_id": patron_id,
        "total_items": len(tag_ids),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


async def _process_single_checkout(
    db: AsyncSession,
    session_id: int,
    tag_id: str,
    patron: User,
    operator: User,
) -> dict:
    # Record scan
    scan = await record_scan(db, session_id, tag_id)

    # Try to resolve tag
    tag_data = await resolve_tag_to_item(db, tag_id)

    if not tag_data:
        scan.processed = True
        scan.process_result = "tag_not_found"
        scan.error_message = "Tag not registered in system"
        return {
            "tag_id": tag_id,
            "item_barcode": None,
            "item_title": None,
            "success": False,
            "message": "Tag not registered in system",
            "checkout_id": None,
            "due_date": None,
        }

    tag, copy, catalog_item = tag_data

    # Check if item is available
    if catalog_item.status != ItemStatus.available:
        scan.processed = True
        scan.process_result = "not_available"
        scan.error_message = f"Item not available (status: {catalog_item.status})"
        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": False,
            "message": f"Item not available (status: {catalog_item.status})",
            "checkout_id": None,
            "due_date": None,
        }

    try:
        # Create checkout bound to the scanned copy so the per-copy
        # guard and distributed lock actually cover this copy.
        checkout_result = await create_checkout(
            user=patron,
            item_id=catalog_item.id,
            db=db,
            item_copy_id=copy.id,
        )
        checkout = checkout_result.checkout

        # Desensitize tag (turn off security)
        tag.security_bit = False
        tag.updated_at = utc_now()

        scan.processed = True
        scan.process_result = "checkout_success"
        scan.processed_at = utc_now()

        # Release checkout lock after DB work is prepared
        # (get_db auto-commit will finalize the transaction)
        await checkout_result.release_lock()

        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": True,
            "message": "Checkout successful",
            "checkout_id": checkout.id,
            "due_date": checkout.due_date,
        }
    except APIError as e:
        scan.processed = True
        scan.process_result = "checkout_failed"
        scan.error_message = e.message
        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": False,
            "message": e.message,
            "checkout_id": None,
            "due_date": None,
        }


# ============ Batch Checkin ============


async def batch_checkin(
    db: AsyncSession,
    reader_id: int,
    tag_ids: list[str],
    operator: User,
    progress_callback: Optional[callable] = None,
) -> dict:
    # Create session
    session = await create_session(
        db=db,
        session_type=RFIDSessionType.BATCH_CHECKIN,
        reader_id=reader_id,
        operator=operator,
    )

    results = []
    successful = 0
    failed = 0
    items_with_holds = 0
    items_with_fines = 0
    total = len(tag_ids)

    for idx, tag_id in enumerate(tag_ids):
        result = await _process_single_checkin(db, session.id, tag_id, operator)
        results.append(result)
        if result["success"]:
            successful += 1
            if result.get("next_hold_patron"):
                items_with_holds += 1
            if result.get("fine_amount"):
                items_with_fines += 1
        else:
            failed += 1

        # Broadcast progress if callback provided
        if progress_callback:
            await progress_callback(
                session.id, total, idx + 1, successful, failed,
                {"tag_id": tag_id, **result}
            )

    # Update session stats
    session.tags_processed = successful
    session.tags_failed = failed

    # End session
    session.is_active = False
    session.ended_at = utc_now()

    return {
        "session_id": session.id,
        "total_items": len(tag_ids),
        "successful": successful,
        "failed": failed,
        "items_with_holds": items_with_holds,
        "items_with_fines": items_with_fines,
        "results": results,
    }


async def _process_single_checkin(
    db: AsyncSession,
    session_id: int,
    tag_id: str,
    operator: User,
) -> dict:
    from .fine_service import check_and_create_overdue_fine

    # Record scan
    scan = await record_scan(db, session_id, tag_id)

    # Try to resolve tag
    tag_data = await resolve_tag_to_item(db, tag_id)

    if not tag_data:
        scan.processed = True
        scan.process_result = "tag_not_found"
        scan.error_message = "Tag not registered in system"
        return {
            "tag_id": tag_id,
            "item_barcode": None,
            "item_title": None,
            "success": False,
            "message": "Tag not registered in system",
            "was_overdue": False,
            "fine_amount": None,
            "next_hold_patron": None,
        }

    tag, copy, catalog_item = tag_data

    # Find active checkout for this item
    checkout_result = await db.execute(
        select(Checkout)
        .where(
            Checkout.item_id == catalog_item.id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
        .options(selectinload(Checkout.user))
        .with_for_update()
    )
    checkout = checkout_result.scalar_one_or_none()

    if not checkout:
        # Item wasn't checked out - just resensitize
        tag.security_bit = True
        tag.updated_at = utc_now()

        scan.processed = True
        scan.process_result = "not_checked_out"
        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": True,
            "message": "Item was not checked out - resensitized",
            "was_overdue": False,
            "fine_amount": None,
            "next_hold_patron": None,
        }

    # Check for overdue
    was_overdue = checkout.status == CheckoutStatus.overdue or checkout.due_date < utc_now()
    fine_amount = None

    try:
        # Process return
        ret_result = await return_checkout(checkout, db, operator)
        item = ret_result.item

        # Check for fines
        if was_overdue:
            # Fine may have been created by return_checkout
            from ..models.fine import Fine, FineStatus
            fine_result = await db.execute(
                select(Fine)
                .where(
                    Fine.checkout_id == checkout.id,
                    Fine.status == FineStatus.unpaid,
                )
            )
            fine = fine_result.scalar_one_or_none()
            if fine:
                fine_amount = float(fine.amount)

        # Resensitize tag
        tag.security_bit = True
        tag.updated_at = utc_now()

        # Check for next hold
        next_hold_patron = None
        if item and item.status == ItemStatus.on_hold:
            from ..models.circulation import Hold, HoldStatus
            hold_result = await db.execute(
                select(Hold)
                .where(Hold.item_id == catalog_item.id, Hold.status == HoldStatus.ready)
                .options(selectinload(Hold.user))
            )
            hold = hold_result.scalar_one_or_none()
            if hold and hold.user:
                next_hold_patron = f"{hold.user.first_name} {hold.user.last_name}"

        scan.processed = True
        scan.process_result = "checkin_success"
        scan.processed_at = utc_now()

        # Send hold-ready notification after all DB work is prepared
        # (caller is responsible for commit, but RFID operations commit
        # via get_db auto-commit so notification goes out post-flush)
        await send_pending_hold_notification(ret_result.pending_notification)

        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": True,
            "message": "Checkin successful",
            "was_overdue": was_overdue,
            "fine_amount": fine_amount,
            "next_hold_patron": next_hold_patron,
        }
    except APIError as e:
        scan.processed = True
        scan.process_result = "checkin_failed"
        scan.error_message = e.message
        return {
            "tag_id": tag_id,
            "item_barcode": copy.barcode,
            "item_title": catalog_item.title,
            "success": False,
            "message": e.message,
            "was_overdue": False,
            "fine_amount": None,
            "next_hold_patron": None,
        }


# ============ Security Gate Integration ============


async def handle_security_alert(
    db: AsyncSession,
    reader_id: int,
    tag_id: Optional[str],
    signal_strength: Optional[float] = None,
) -> SecurityAlert:
    reader = await get_reader(db, reader_id)

    # Try to resolve tag
    item_barcode = None
    item_title = None
    alert_type = SecurityAlertType.UNAUTHORIZED_EXIT

    if tag_id:
        tag_data = await resolve_tag_to_item(db, tag_id)
        if tag_data:
            tag, copy, catalog_item = tag_data
            item_barcode = copy.barcode
            item_title = catalog_item.title if catalog_item else None

            # Check if tag should have triggered alert
            if not tag.security_bit:
                # Tag is desensitized but triggered alert - might be false alarm
                alert_type = SecurityAlertType.INVALID_TAG
        else:
            alert_type = SecurityAlertType.INVALID_TAG
    else:
        alert_type = SecurityAlertType.MISSING_TAG

    alert = SecurityAlert(
        reader_id=reader_id,
        alert_type=alert_type,
        tag_id=tag_id,
        item_barcode=item_barcode,
        item_title=item_title,
        description=f"Security alert at {reader.location or reader.name}",
        signal_strength=signal_strength,
    )
    db.add(alert)
    await db.flush()

    logger.warning(
        f"Security alert {alert.id}: {alert_type.value} at {reader.name} - "
        f"Tag: {tag_id}, Item: {item_barcode}"
    )

    return alert


async def resolve_security_alert(
    db: AsyncSession,
    alert_id: int,
    user: User,
    resolution_notes: str,
) -> SecurityAlert:
    result = await db.execute(
        select(SecurityAlert).where(SecurityAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Security alert not found")

    if alert.is_resolved:
        raise BusinessLogicError(code=ErrorCode.INVALID_STATE, message="Alert is already resolved")

    alert.is_resolved = True
    alert.resolved_at = utc_now()
    alert.resolved_by_id = user.id
    alert.resolution_notes = resolution_notes

    logger.info(f"Resolved security alert {alert_id}: {resolution_notes}")
    return alert


async def get_unresolved_alerts(
    db: AsyncSession,
    reader_id: Optional[int] = None,
    limit: int = 50,
) -> list[SecurityAlert]:
    query = select(SecurityAlert).where(SecurityAlert.is_resolved == False)

    if reader_id:
        query = query.where(SecurityAlert.reader_id == reader_id)

    query = query.order_by(SecurityAlert.created_at.desc()).limit(limit)

    result = await db.execute(query.options(selectinload(SecurityAlert.reader)))
    return list(result.scalars().all())


# ============ Inventory Mode ============


async def start_inventory_session(
    db: AsyncSession,
    reader_id: int,
    operator: User,
    inventory_audit_id: Optional[int] = None,
    target_location: Optional[str] = None,
    create_audit: bool = False,
    audit_name: Optional[str] = None,
) -> RFIDSession:
    # Create audit if requested and no ID provided
    if create_audit and not inventory_audit_id:
        audit = InventoryAudit(
            name=audit_name or f"RFID Inventory Scan - {utc_now().strftime('%Y-%m-%d %H:%M')}",
            location_filter=target_location,
            created_by_id=operator.id,
        )

        # Count expected items
        count_query = select(func.count(ItemCopy.id)).where(
            ItemCopy.condition != ItemCondition.WITHDRAWN
        )
        if target_location:
            safe_loc = target_location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            count_query = count_query.where(
                ItemCopy.location.ilike(f"%{safe_loc}%")
            )
        count_result = await db.execute(count_query)
        audit.items_expected = count_result.scalar() or 0

        db.add(audit)
        await db.flush()
        inventory_audit_id = audit.id

    session = await create_session(
        db=db,
        session_type=RFIDSessionType.INVENTORY_SCAN,
        reader_id=reader_id,
        operator=operator,
        inventory_audit_id=inventory_audit_id,
        target_location=target_location,
    )

    return session


async def process_inventory_scan(
    db: AsyncSession,
    session_id: int,
    tag_id: str,
    found_at_location: Optional[str] = None,
    signal_strength: Optional[float] = None,
) -> dict:
    # Get session
    session_result = await db.execute(
        select(RFIDSession)
        .where(RFIDSession.id == session_id)
        .with_for_update()
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Session not found")

    if session.session_type != RFIDSessionType.INVENTORY_SCAN:
        raise ValidationError(code=ErrorCode.INVALID_PARAMETER, message="Session is not an inventory session")

    # Record scan
    scan = await record_scan(
        db=db,
        session_id=session_id,
        tag_id=tag_id,
        signal_strength=signal_strength,
        found_at_location=found_at_location or session.target_location,
    )

    # If linked to audit, record audit scan too
    if session.inventory_audit_id and scan.rfid_tag_id:
        tag_data = await resolve_tag_to_item(db, tag_id)
        if tag_data:
            tag, copy, _ = tag_data

            # Check if already scanned in this audit
            existing_result = await db.execute(
                select(AuditScan)
                .where(
                    AuditScan.audit_id == session.inventory_audit_id,
                    AuditScan.item_copy_id == copy.id,
                )
            )

            if not existing_result.scalar_one_or_none():
                # Create audit scan record
                is_misplaced = False
                if found_at_location and copy.location:
                    is_misplaced = found_at_location.lower() != copy.location.lower()

                audit_scan = AuditScan(
                    audit_id=session.inventory_audit_id,
                    item_copy_id=copy.id,
                    found_at_location=found_at_location,
                    is_misplaced=is_misplaced,
                    scanned_by_id=session.operator_id,
                )
                db.add(audit_scan)

                # Update audit stats
                audit_result = await db.execute(
                    select(InventoryAudit)
                    .where(InventoryAudit.id == session.inventory_audit_id)
                    .with_for_update()
                )
                audit = audit_result.scalar_one_or_none()
                if audit:
                    audit.items_found += 1
                    if is_misplaced:
                        audit.items_misplaced += 1

    scan.processed = True
    scan.process_result = "inventory_recorded"
    scan.processed_at = utc_now()
    session.tags_processed += 1

    return {
        "scan_id": scan.id,
        "tag_id": tag_id,
        "item_barcode": scan.item_barcode,
        "item_title": scan.item_title,
        "expected_location": scan.expected_location,
        "found_at_location": scan.found_at_location,
        "is_misplaced": scan.is_misplaced,
        "registered": scan.rfid_tag_id is not None,
    }


# ============ Shelf Reading ============


async def start_shelf_read_session(
    db: AsyncSession,
    reader_id: int,
    operator: User,
    target_location: str,
) -> RFIDSession:
    session = await create_session(
        db=db,
        session_type=RFIDSessionType.SHELF_READ,
        reader_id=reader_id,
        operator=operator,
        target_location=target_location,
    )
    return session


async def get_shelf_read_results(
    db: AsyncSession,
    session_id: int,
) -> dict:
    session_result = await db.execute(
        select(RFIDSession)
        .where(RFIDSession.id == session_id)
        .options(selectinload(RFIDSession.scans))
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Session not found")

    misplaced_items = []
    unknown_tags = []
    items_in_correct_location = 0

    for scan in session.scans:
        if scan.rfid_tag_id is None:
            unknown_tags.append(scan.tag_id)
        elif scan.is_misplaced:
            misplaced_items.append({
                "tag_id": scan.tag_id,
                "barcode": scan.item_barcode,
                "title": scan.item_title,
                "expected_location": scan.expected_location,
                "found_at_location": scan.found_at_location,
            })
        else:
            items_in_correct_location += 1

    return {
        "session_id": session_id,
        "location": session.target_location,
        "items_scanned": session.tags_scanned,
        "items_in_correct_location": items_in_correct_location,
        "items_misplaced": len(misplaced_items),
        "items_not_in_catalog": len(unknown_tags),
        "misplaced_items": misplaced_items,
        "unknown_tags": unknown_tags,
    }


# ============ Missing Item Detection ============


async def find_missing_items(
    db: AsyncSession,
    inventory_audit_id: Optional[int] = None,
    location_filter: Optional[str] = None,
    days_since_last_seen: Optional[int] = None,
) -> list[dict]:
    missing_items = []

    if inventory_audit_id:
        # Get items expected in audit but not scanned
        audit_result = await db.execute(
            select(InventoryAudit).where(InventoryAudit.id == inventory_audit_id)
        )
        audit = audit_result.scalar_one_or_none()
        if not audit:
            raise ResourceNotFoundError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Audit not found")

        # Get all scanned item copy IDs
        scanned_result = await db.execute(
            select(AuditScan.item_copy_id)
            .where(AuditScan.audit_id == inventory_audit_id)
        )
        scanned_ids = set(row[0] for row in scanned_result.all())

        # Get expected items (not withdrawn, matching location filter)
        query = (
            select(ItemCopy)
            .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
            .options(selectinload(ItemCopy.catalog_item))
        )
        if audit.location_filter:
            safe_loc = audit.location_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                ItemCopy.location.ilike(f"%{safe_loc}%")
            )

        result = await db.execute(query)
        all_copies = result.scalars().all()
        unscanned_copies = [c for c in all_copies if c.id not in scanned_ids]

        if unscanned_copies:
            # Batch fetch RFID tags for all unscanned barcodes
            unscanned_barcodes = [c.barcode for c in unscanned_copies if c.barcode]
            tags_by_barcode = {}
            if unscanned_barcodes:
                tags_result = await db.execute(
                    select(RFIDTag).where(
                        RFIDTag.item_barcode.in_(unscanned_barcodes),
                        RFIDTag.is_active == True,
                    )
                )
                tags_by_barcode = {t.item_barcode: t for t in tags_result.scalars().all()}

            # Batch fetch active/overdue checkouts for all unscanned copy IDs
            unscanned_copy_ids = [c.id for c in unscanned_copies]
            checkouts_by_copy_id = {}
            if unscanned_copy_ids:
                checkouts_result = await db.execute(
                    select(Checkout).where(
                        Checkout.item_copy_id.in_(unscanned_copy_ids),
                        Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
                    )
                )
                checkouts_by_copy_id = {
                    co.item_copy_id: co for co in checkouts_result.scalars().all()
                }

            for copy in unscanned_copies:
                tag = tags_by_barcode.get(copy.barcode)
                checkout = checkouts_by_copy_id.get(copy.id)
                missing_items.append({
                    "item_copy_id": copy.id,
                    "barcode": copy.barcode,
                    "title": copy.catalog_item.title if copy.catalog_item else "Unknown",
                    "author": copy.catalog_item.author if copy.catalog_item else None,
                    "expected_location": copy.location,
                    "last_seen_at": tag.last_read_at if tag else None,
                    "last_seen_location": None,  # Would need scan history
                    "days_missing": None,
                    "tag_id": tag.tag_id if tag else None,
                    "checkout_status": str(checkout.status) if checkout else "not_checked_out",
                })

    elif days_since_last_seen:
        # Find items with tags not scanned recently
        cutoff_date = utc_now() - timedelta(days=days_since_last_seen)

        # Use a JOIN query to fetch tags with their item copies in one roundtrip
        joined_query = (
            select(RFIDTag, ItemCopy, CatalogItem)
            .outerjoin(ItemCopy, ItemCopy.barcode == RFIDTag.item_barcode)
            .outerjoin(CatalogItem, CatalogItem.id == ItemCopy.catalog_item_id)
            .where(
                RFIDTag.is_active == True,
                or_(
                    RFIDTag.last_read_at < cutoff_date,
                    RFIDTag.last_read_at.is_(None),
                ),
            )
        )

        result = await db.execute(joined_query)
        now = utc_now()
        for tag, copy, catalog_item in result.all():
            if copy and copy.condition != ItemCondition.WITHDRAWN:
                days_missing = None
                if tag.last_read_at:
                    days_missing = (now - tag.last_read_at).days

                missing_items.append({
                    "item_copy_id": copy.id,
                    "barcode": copy.barcode,
                    "title": catalog_item.title if catalog_item else "Unknown",
                    "author": catalog_item.author if catalog_item else None,
                    "expected_location": copy.location,
                    "last_seen_at": tag.last_read_at,
                    "last_seen_location": None,
                    "days_missing": days_missing,
                    "tag_id": tag.tag_id,
                    "checkout_status": None,
                })

    else:
        # Just filter by location
        query = (
            select(ItemCopy)
            .where(ItemCopy.condition != ItemCondition.WITHDRAWN)
            .options(selectinload(ItemCopy.catalog_item))
        )
        if location_filter:
            safe_loc = location_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                ItemCopy.location.ilike(f"%{safe_loc}%")
            )

        # This returns all items - might need pagination for large collections
        query = query.limit(500)

        result = await db.execute(query)
        all_copies = result.scalars().all()

        # Batch fetch RFID tags for all barcodes
        barcodes = [c.barcode for c in all_copies if c.barcode]
        tags_by_barcode = {}
        if barcodes:
            tags_result = await db.execute(
                select(RFIDTag).where(
                    RFIDTag.item_barcode.in_(barcodes),
                    RFIDTag.is_active == True,
                )
            )
            tags_by_barcode = {t.item_barcode: t for t in tags_result.scalars().all()}

        for copy in all_copies:
            tag = tags_by_barcode.get(copy.barcode)
            if not tag:
                # Item without RFID tag
                missing_items.append({
                    "item_copy_id": copy.id,
                    "barcode": copy.barcode,
                    "title": copy.catalog_item.title if copy.catalog_item else "Unknown",
                    "author": copy.catalog_item.author if copy.catalog_item else None,
                    "expected_location": copy.location,
                    "last_seen_at": None,
                    "last_seen_location": None,
                    "days_missing": None,
                    "tag_id": None,
                    "checkout_status": None,
                })

    return missing_items


# ============ Reader Health & Statistics ============


async def update_reader_heartbeat(
    db: AsyncSession,
    reader_id: int,
    status: RFIDReaderStatus = RFIDReaderStatus.ONLINE,
    error: Optional[str] = None,
) -> RFIDReader:
    reader = await get_reader(db, reader_id)
    reader.last_heartbeat = utc_now()
    reader.status = status
    if error:
        reader.last_error = error
    elif status == RFIDReaderStatus.ONLINE:
        reader.last_error = None
    return reader


async def get_rfid_dashboard_stats(db: AsyncSession) -> dict:
    # Reader stats
    reader_result = await db.execute(
        select(
            func.count(RFIDReader.id).label("total"),
            func.sum(func.cast(RFIDReader.status == RFIDReaderStatus.ONLINE, Integer)).label("online"),
            func.sum(func.cast(RFIDReader.status == RFIDReaderStatus.OFFLINE, Integer)).label("offline"),
            func.sum(func.cast(RFIDReader.status == RFIDReaderStatus.ERROR, Integer)).label("error"),
        )
        .where(RFIDReader.is_active == True)
    )
    reader_stats = reader_result.one()

    # Tag stats
    tag_result = await db.execute(
        select(
            func.count(RFIDTag.id).label("total"),
            func.sum(func.cast(RFIDTag.is_active == True, Integer)).label("active"),
        )
    )
    tag_stats = tag_result.one()

    # Today's stats
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)

    session_result = await db.execute(
        select(func.count(RFIDSession.id))
        .where(RFIDSession.started_at >= today_start)
    )
    sessions_today = session_result.scalar() or 0

    scan_result = await db.execute(
        select(func.count(RFIDScan.id))
        .where(RFIDScan.scanned_at >= today_start, RFIDScan.processed == True)
    )
    items_processed_today = scan_result.scalar() or 0

    # Alert stats
    alert_today_result = await db.execute(
        select(func.count(SecurityAlert.id))
        .where(SecurityAlert.created_at >= today_start)
    )
    alerts_today = alert_today_result.scalar() or 0

    unresolved_result = await db.execute(
        select(func.count(SecurityAlert.id))
        .where(SecurityAlert.is_resolved == False)
    )
    unresolved_alerts = unresolved_result.scalar() or 0

    # Recent sessions
    recent_sessions_result = await db.execute(
        select(RFIDSession)
        .order_by(RFIDSession.started_at.desc())
        .limit(5)
        .options(
            selectinload(RFIDSession.reader),
            selectinload(RFIDSession.operator),
        )
    )
    recent_sessions = recent_sessions_result.scalars().all()

    # Recent alerts
    recent_alerts = await get_unresolved_alerts(db, limit=5)

    return {
        "total_readers": reader_stats.total or 0,
        "readers_online": reader_stats.online or 0,
        "readers_offline": reader_stats.offline or 0,
        "readers_error": reader_stats.error or 0,
        "total_tags": tag_stats.total or 0,
        "active_tags": tag_stats.active or 0,
        "total_sessions_today": sessions_today,
        "items_processed_today": items_processed_today,
        "security_alerts_today": alerts_today,
        "unresolved_alerts": unresolved_alerts,
        "recent_sessions": recent_sessions,
        "recent_alerts": recent_alerts,
    }
