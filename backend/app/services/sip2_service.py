# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.book_drop import (
    SIP2Device, SIP2DeviceStatus, SortDestination,
    CheckInResultStatus
)

logger = get_logger(__name__)


class SIP2MessageType(StrEnum):
    # Patron status
    PATRON_STATUS_REQUEST = "23"
    PATRON_STATUS_RESPONSE = "24"

    # Checkout
    CHECKOUT_REQUEST = "11"
    CHECKOUT_RESPONSE = "12"

    # Checkin
    CHECKIN_REQUEST = "09"
    CHECKIN_RESPONSE = "10"

    # Block patron
    BLOCK_PATRON = "01"
    BLOCK_PATRON_RESPONSE = "02"

    # SC/ACS Status
    SC_STATUS = "99"
    ACS_STATUS = "98"

    # Item information
    ITEM_INFO_REQUEST = "17"
    ITEM_INFO_RESPONSE = "18"

    # Patron information
    PATRON_INFO_REQUEST = "63"
    PATRON_INFO_RESPONSE = "64"

    # End session
    END_SESSION = "35"
    END_SESSION_RESPONSE = "36"

    # Fee paid
    FEE_PAID = "37"
    FEE_PAID_RESPONSE = "38"

    # Item status update
    ITEM_STATUS_UPDATE = "19"
    ITEM_STATUS_UPDATE_RESPONSE = "20"

    # Renew
    RENEW = "29"
    RENEW_RESPONSE = "30"


@dataclass
class SIP2CheckinRequest:
    item_barcode: str
    institution_id: str
    terminal_password: Optional[str] = None
    current_location: Optional[str] = None
    return_date: Optional[datetime] = None
    no_block: bool = False

    def to_message(self) -> str:
        # Message type 09 = Checkin
        msg = "09"

        # No block flag (Y/N)
        msg += "Y" if self.no_block else "N"

        # Transaction date (18 chars: YYYYMMDD    HHMMSS)
        now = datetime.now(timezone.utc)
        msg += now.strftime("%Y%m%d    %H%M%S")

        # Return date (optional)
        if self.return_date:
            msg += self.return_date.strftime("%Y%m%d    %H%M%S")
        else:
            msg += now.strftime("%Y%m%d    %H%M%S")

        # Current location (optional, AQ field)
        if self.current_location:
            msg += f"AP{self.current_location}|"

        # Institution ID (AO field - required)
        msg += f"AO{self.institution_id}|"

        # Item identifier (AB field - required)
        msg += f"AB{self.item_barcode}|"

        # Terminal password (AC field - optional)
        if self.terminal_password:
            msg += f"AC{self.terminal_password}|"

        return msg


@dataclass
class SIP2CheckinResponse:
    ok: bool
    resensitize: bool
    magnetic_media: Optional[bool]
    alert: bool
    transaction_date: datetime
    institution_id: str
    item_identifier: str
    permanent_location: Optional[str] = None
    title_identifier: Optional[str] = None
    sort_bin: Optional[str] = None
    patron_identifier: Optional[str] = None  # For hold traps
    destination_location: Optional[str] = None  # For transits
    hold_patron_name: Optional[str] = None
    screen_message: Optional[str] = None

    @classmethod
    def from_message(cls, msg: str) -> "SIP2CheckinResponse":
        # Message type 10 = Checkin Response
        if not msg.startswith("10"):
            raise ValueError(f"Invalid checkin response: {msg[:2]}")

        # Fixed fields
        ok = msg[2] == "1"
        resensitize = msg[3] == "Y"
        magnetic_media = msg[4] == "Y" if msg[4] in "YNU" else None
        alert = msg[5] == "Y"

        # Transaction date (positions 6-23)
        date_str = msg[6:24].strip()
        transaction_date = datetime.strptime(date_str, "%Y%m%d%H%M%S")
        transaction_date = transaction_date.replace(tzinfo=timezone.utc)

        # Variable fields (after position 24)
        fields = {}
        parts = msg[24:].split("|")
        for part in parts:
            if len(part) >= 2:
                field_id = part[:2]
                field_value = part[2:]
                fields[field_id] = field_value

        return cls(
            ok=ok,
            resensitize=resensitize,
            magnetic_media=magnetic_media,
            alert=alert,
            transaction_date=transaction_date,
            institution_id=fields.get("AO", ""),
            item_identifier=fields.get("AB", ""),
            permanent_location=fields.get("AQ"),
            title_identifier=fields.get("AJ"),
            sort_bin=fields.get("CL"),
            patron_identifier=fields.get("AA"),
            destination_location=fields.get("CT"),
            hold_patron_name=fields.get("CY"),
            screen_message=fields.get("AF"),
        )


@dataclass
class SIP2SortInstruction:
    item_barcode: str
    destination: SortDestination
    bin_id: str
    message: Optional[str] = None


class SIP2Service:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._connections: dict[int, tuple] = {}  # device_id -> (reader, writer)

    async def get_device(self, device_id: int) -> Optional[SIP2Device]:
        result = await self.db.execute(
            select(SIP2Device).where(SIP2Device.id == device_id)
        )
        return result.scalar_one_or_none()

    async def get_device_by_code(self, device_code: str) -> Optional[SIP2Device]:
        result = await self.db.execute(
            select(SIP2Device).where(SIP2Device.device_id == device_code)
        )
        return result.scalar_one_or_none()

    async def connect(self, device: SIP2Device) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(device.host, device.port),
                timeout=device.timeout_seconds
            )
            self._connections[device.id] = (reader, writer)

            # Update device status
            await self.db.execute(
                update(SIP2Device)
                .where(SIP2Device.id == device.id)
                .values(
                    status=SIP2DeviceStatus.ONLINE,
                    last_communication=datetime.now(timezone.utc),
                    error_message=None
                )
            )

            logger.info(f"Connected to SIP2 device {device.device_id} at {device.host}:{device.port}")
            return True

        except asyncio.TimeoutError:
            await self._handle_connection_error(device, "Connection timeout")
            return False
        except ConnectionRefusedError:
            await self._handle_connection_error(device, "Connection refused")
            return False
        except Exception as e:  # noqa: BLE001 - protocol boundary — must not drop SIP2 connection on unexpected error
            await self._handle_connection_error(device, str(e))
            return False

    async def disconnect(self, device: SIP2Device) -> None:
        if device.id in self._connections:
            reader, writer = self._connections[device.id]
            writer.close()
            await writer.wait_closed()
            del self._connections[device.id]
            logger.info(f"Disconnected from SIP2 device {device.device_id}")

    async def _handle_connection_error(self, device: SIP2Device, error: str) -> None:
        await self.db.execute(
            update(SIP2Device)
            .where(SIP2Device.id == device.id)
            .values(
                status=SIP2DeviceStatus.ERROR,
                error_message=error
            )
        )
        logger.error(f"SIP2 device {device.device_id} error: {error}")

    async def send_message(
        self,
        device: SIP2Device,
        message: str
    ) -> Optional[str]:
        if device.id not in self._connections:
            if not await self.connect(device):
                return None

        reader, writer = self._connections[device.id]

        try:
            # Add message terminator (CR)
            full_message = message + "\r"
            writer.write(full_message.encode("ascii"))
            await writer.drain()

            # Read response until CR
            response = await asyncio.wait_for(
                reader.readuntil(b"\r"),
                timeout=device.timeout_seconds
            )

            # Update last communication time
            await self.db.execute(
                update(SIP2Device)
                .where(SIP2Device.id == device.id)
                .values(last_communication=datetime.now(timezone.utc))
            )

            return response.decode("ascii").rstrip("\r")

        except asyncio.TimeoutError:
            await self._handle_connection_error(device, "Response timeout")
            return None
        except Exception as e:  # noqa: BLE001 - protocol boundary — must not drop SIP2 connection on send failure
            await self._handle_connection_error(device, str(e))
            return None

    async def checkin_item(
        self,
        device: SIP2Device,
        barcode: str,
        current_location: Optional[str] = None,
        return_date: Optional[datetime] = None
    ) -> Optional[SIP2CheckinResponse]:
        request = SIP2CheckinRequest(
            item_barcode=barcode,
            institution_id=device.institution_id,
            terminal_password=device.terminal_password,
            current_location=current_location,
            return_date=return_date
        )

        response_msg = await self.send_message(device, request.to_message())
        if not response_msg:
            return None

        try:
            return SIP2CheckinResponse.from_message(response_msg)
        except Exception as e:  # noqa: BLE001 - protocol boundary — malformed SIP2 response must not crash handler
            logger.error(f"Failed to parse SIP2 checkin response: {e}")
            return None

    def determine_sort_destination(
        self,
        device: SIP2Device,
        checkin_status: CheckInResultStatus,
        has_hold: bool = False,
        needs_transit: bool = False,
        has_exception: bool = False,
        needs_condition_check: bool = False
    ) -> SIP2SortInstruction:
        mapping = device.sort_bin_mapping or {}

        # Priority order: exception > hold > transit > condition check > reshelve
        if has_exception:
            destination = SortDestination.EXCEPTION
            bin_id = mapping.get("exception", "exception_bin")
            message = "Route to exception handling"
        elif has_hold:
            destination = SortDestination.HOLD_SHELF
            bin_id = mapping.get("hold", "hold_bin")
            message = "Route to hold shelf"
        elif needs_transit:
            destination = SortDestination.TRANSIT
            bin_id = mapping.get("transit", "transit_bin")
            message = "Route for transit"
        elif needs_condition_check:
            destination = SortDestination.CONDITION_CHECK
            bin_id = mapping.get("condition", "condition_bin")
            message = "Route for condition check"
        else:
            destination = SortDestination.RESHELVE
            bin_id = mapping.get("reshelve", "reshelve_bin")
            message = "Route for reshelving"

        return SIP2SortInstruction(
            item_barcode="",  # Will be set by caller
            destination=destination,
            bin_id=bin_id,
            message=message
        )

    async def send_sort_instruction(
        self,
        device: SIP2Device,
        barcode: str,
        sort_bin: str
    ) -> bool:
        if not device.supports_sorting:
            logger.warning(f"Device {device.device_id} does not support sorting")
            return False

        # Build Item Status Update message
        # Message type 19 with sort bin field
        now = datetime.now(timezone.utc)
        msg = "19"
        msg += now.strftime("%Y%m%d    %H%M%S")
        msg += f"AO{device.institution_id}|"
        msg += f"AB{barcode}|"
        msg += f"CL{sort_bin}|"  # Sort bin field

        if device.terminal_password:
            msg += f"AC{device.terminal_password}|"

        response = await self.send_message(device, msg)
        if response and response.startswith("20"):
            # Check if operation was successful (position 2 should be "1")
            return len(response) > 2 and response[2] == "1"

        return False

    async def check_device_status(self, device: SIP2Device) -> bool:
        # SC Status message
        msg = "9900CNUnknown|CO|"

        response = await self.send_message(device, msg)
        if response and response.startswith("98"):
            # Device responded with ACS Status
            await self.db.execute(
                update(SIP2Device)
                .where(SIP2Device.id == device.id)
                .values(
                    status=SIP2DeviceStatus.ONLINE,
                    last_communication=datetime.now(timezone.utc),
                    error_message=None
                )
            )
            return True

        return False

    async def get_all_devices(self) -> list[SIP2Device]:
        result = await self.db.execute(select(SIP2Device))
        return list(result.scalars().all())

    async def get_online_devices(self) -> list[SIP2Device]:
        result = await self.db.execute(
            select(SIP2Device).where(SIP2Device.status == SIP2DeviceStatus.ONLINE)
        )
        return list(result.scalars().all())
