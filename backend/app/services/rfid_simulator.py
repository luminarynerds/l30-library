# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
from app.core.logging import get_logger
import random
import secrets
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.rfid import (
    RFIDReader, RFIDReaderStatus, RFIDReaderType, RFIDProtocol,
    RFIDTag, RFIDSession, RFIDSessionType,
)
from ..models.inventory import ItemCopy
from .rfid_websocket import (
    rfid_ws_manager,
    create_scan_event,
    create_security_alert_event,
    create_reader_status_event,
)
from . import rfid_service
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


def generate_tag_id() -> str:
    return secrets.token_hex(12).upper()


def generate_signal_strength() -> float:
    return round(random.uniform(-70, -20), 1)


class RFIDSimulator:

    def __init__(self):
        self._auto_scan_tasks: dict[int, asyncio.Task] = {}
        self._running = False

    async def create_simulated_reader(
        self,
        db: AsyncSession,
        name: str = "Test Reader",
        reader_type: RFIDReaderType = RFIDReaderType.CIRCULATION_DESK,
        location: str = "Test Location",
    ) -> RFIDReader:
        serial_number = f"SIM-{secrets.token_hex(6).upper()}"

        reader = RFIDReader(
            name=name,
            serial_number=serial_number,
            location=location,
            reader_type=reader_type,
            protocol=RFIDProtocol.REST_API,
            status=RFIDReaderStatus.ONLINE,
            config_metadata={
                "simulated": True,
                "created_at": utc_now().isoformat(),
            },
        )
        db.add(reader)
        await db.flush()

        logger.info(f"Created simulated reader: {reader.name} (ID: {reader.id})")
        return reader

    async def simulate_tag_read(
        self,
        db: AsyncSession,
        session_id: int,
        tag_id: Optional[str] = None,
        signal_strength: Optional[float] = None,
        found_at_location: Optional[str] = None,
    ) -> dict:
        if not tag_id:
            tag_id = generate_tag_id()
        if signal_strength is None:
            signal_strength = generate_signal_strength()

        # Get session to find target location
        session_result = await db.execute(
            select(RFIDSession).where(RFIDSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not found_at_location and session.target_location:
            found_at_location = session.target_location

        # Record the scan
        scan = await rfid_service.record_scan(
            db=db,
            session_id=session_id,
            tag_id=tag_id,
            signal_strength=signal_strength,
            antenna_id=1,
            found_at_location=found_at_location,
        )

        # Broadcast via WebSocket
        event = create_scan_event(
            session_id=session_id,
            tag_id=tag_id,
            item_barcode=scan.item_barcode,
            item_title=scan.item_title,
            is_registered=scan.rfid_tag_id is not None,
            is_misplaced=scan.is_misplaced or False,
            expected_location=scan.expected_location,
            found_at_location=found_at_location,
            signal_strength=signal_strength,
        )
        await rfid_ws_manager.broadcast_scan(event)

        return {
            "scan_id": scan.id,
            "tag_id": tag_id,
            "item_barcode": scan.item_barcode,
            "item_title": scan.item_title,
            "is_registered": scan.rfid_tag_id is not None,
            "signal_strength": signal_strength,
        }

    async def simulate_batch_read(
        self,
        db: AsyncSession,
        session_id: int,
        count: int = 5,
        include_registered: bool = True,
        include_unregistered: bool = True,
        delay_ms: int = 200,
    ) -> list[dict]:
        results = []
        tags_to_read = []

        if include_registered:
            # Get some registered tags
            tag_result = await db.execute(
                select(RFIDTag)
                .where(RFIDTag.is_active == True)
                .limit(count)
            )
            registered_tags = tag_result.scalars().all()
            tags_to_read.extend([tag.tag_id for tag in registered_tags])

        if include_unregistered and len(tags_to_read) < count:
            # Generate random tags to fill the rest
            remaining = count - len(tags_to_read)
            for _ in range(remaining):
                tags_to_read.append(generate_tag_id())

        # Shuffle and limit
        random.shuffle(tags_to_read)
        tags_to_read = tags_to_read[:count]

        for tag_id in tags_to_read:
            result = await self.simulate_tag_read(db, session_id, tag_id=tag_id)
            results.append(result)

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

        return results

    async def simulate_security_alert(
        self,
        db: AsyncSession,
        reader_id: int,
        tag_id: Optional[str] = None,
        use_registered_tag: bool = True,
    ) -> dict:
        if not tag_id and use_registered_tag:
            # Get a random registered tag with security bit enabled
            tag_result = await db.execute(
                select(RFIDTag)
                .where(RFIDTag.is_active == True, RFIDTag.security_bit == True)
                .limit(10)
            )
            tags = tag_result.scalars().all()
            if tags:
                tag_id = random.choice(tags).tag_id

        if not tag_id:
            tag_id = generate_tag_id()

        # Create security alert
        alert = await rfid_service.handle_security_alert(
            db=db,
            reader_id=reader_id,
            tag_id=tag_id,
            signal_strength=generate_signal_strength(),
        )

        # Get reader for broadcast
        reader = await rfid_service.get_reader(db, reader_id)

        # Broadcast via WebSocket
        event = create_security_alert_event(
            alert_id=alert.id,
            reader_id=reader_id,
            alert_type=str(alert.alert_type),
            reader_name=reader.name,
            reader_location=reader.location,
            tag_id=tag_id,
            item_barcode=alert.item_barcode,
            item_title=alert.item_title,
        )
        await rfid_ws_manager.broadcast_security_alert(event)

        logger.info(f"Simulated security alert: {alert.alert_type} at {reader.name}")

        return {
            "alert_id": alert.id,
            "alert_type": str(alert.alert_type),
            "tag_id": tag_id,
            "item_barcode": alert.item_barcode,
            "item_title": alert.item_title,
        }

    async def simulate_reader_status_change(
        self,
        db: AsyncSession,
        reader_id: int,
        status: RFIDReaderStatus,
        error_message: Optional[str] = None,
    ) -> dict:
        reader = await rfid_service.update_reader_heartbeat(
            db=db,
            reader_id=reader_id,
            status=status,
            error=error_message,
        )

        # Broadcast via WebSocket
        event = create_reader_status_event(
            reader_id=reader_id,
            reader_name=reader.name,
            status=status.value,
            last_error=error_message,
        )
        await rfid_ws_manager.broadcast_reader_status(event)

        logger.info(f"Reader {reader.name} status changed to {status.value}")

        return {
            "reader_id": reader_id,
            "reader_name": reader.name,
            "status": status.value,
            "last_error": error_message,
        }

    async def start_auto_scan(
        self,
        db: AsyncSession,
        session_id: int,
        interval_ms: int = 1000,
        include_registered: bool = True,
        include_unregistered: bool = False,
    ):
        if session_id in self._auto_scan_tasks:
            raise ValueError(f"Auto-scan already running for session {session_id}")

        async def _auto_scan_loop():
            try:
                while True:
                    tag_id = None
                    if include_registered:
                        # Try to get a registered tag
                        tag_result = await db.execute(
                            select(RFIDTag)
                            .where(RFIDTag.is_active == True)
                            .limit(50)
                        )
                        tags = tag_result.scalars().all()
                        if tags:
                            tag_id = random.choice(tags).tag_id

                    if not tag_id and include_unregistered:
                        tag_id = generate_tag_id()

                    if tag_id:
                        await self.simulate_tag_read(db, session_id, tag_id=tag_id)

                    await asyncio.sleep(interval_ms / 1000)
            except asyncio.CancelledError:
                logger.info(f"Auto-scan stopped for session {session_id}")
            except Exception as e:  # noqa: BLE001 -- scheduler job boundary: auto-scan loop must not crash background task
                logger.error(f"Auto-scan error for session {session_id}: {e}")

        task = asyncio.create_task(_auto_scan_loop())
        self._auto_scan_tasks[session_id] = task
        logger.info(f"Started auto-scan for session {session_id}")

    async def stop_auto_scan(self, session_id: int):
        if session_id in self._auto_scan_tasks:
            self._auto_scan_tasks[session_id].cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._auto_scan_tasks[session_id]
            del self._auto_scan_tasks[session_id]
            logger.info(f"Stopped auto-scan for session {session_id}")

    async def stop_all_auto_scans(self):
        for session_id in list(self._auto_scan_tasks.keys()):
            await self.stop_auto_scan(session_id)

    async def create_test_tags(
        self,
        db: AsyncSession,
        reader_id: int,
        user_id: int,
        count: int = 10,
    ) -> list[RFIDTag]:
        from ..models.user import User

        # Get user
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get items without RFID tags
        subquery = select(RFIDTag.item_barcode).where(RFIDTag.is_active == True)
        items_result = await db.execute(
            select(ItemCopy)
            .where(~ItemCopy.barcode.in_(subquery))
            .limit(count)
        )
        items = items_result.scalars().all()

        created_tags = []
        for item in items:
            result = await rfid_service.program_tag(
                db=db,
                item_barcode=item.barcode,
                reader_id=reader_id,
                user=user,
                tag_type="ISO 15693 (Simulated)",
            )
            created_tags.append(result["tag"])

        logger.info(f"Created {len(created_tags)} test RFID tags")
        return created_tags

    def get_auto_scan_status(self) -> dict:
        return {
            "active_sessions": list(self._auto_scan_tasks.keys()),
            "count": len(self._auto_scan_tasks),
        }


# Global simulator instance
rfid_simulator = RFIDSimulator()
