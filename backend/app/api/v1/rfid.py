# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
RFID API routes.
Handles RFID reader management, tag operations, batch circulation, and security.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.rfid import (
    RFIDReader, RFIDReaderStatus, RFIDReaderType,
    RFIDTag, RFIDSession, RFIDSessionType, RFIDScan,
    SecurityAlert, SecurityAlertType,
)
from ...models.user import User
from ...schemas.rfid import (
    RFIDReaderCreate, RFIDReaderUpdate, RFIDReaderResponse, RFIDReaderStatusUpdate,
    RFIDReaderListResponse,
    RFIDTagCreate, RFIDTagUpdate, RFIDTagResponse, RFIDTagProgramRequest, RFIDTagProgramResponse,
    RFIDTagListResponse,
    RFIDSessionCreate, RFIDSessionResponse, RFIDSessionSummary,
    RFIDScanCreate, RFIDScanResponse, RFIDScanBatchRequest, RFIDScanBatchResponse,
    BatchCheckoutRequest, BatchCheckoutResponse,
    BatchCheckinRequest, BatchCheckinResponse,
    SecurityAlertCreate, SecurityAlertResponse, SecurityAlertResolve,
    SecurityAlertListResponse,
    InventoryScanRequest, ShelfReadRequest, ShelfReadResult,
    MissingItemsRequest, MissingItemResponse,
    ReaderCommandRequest, ReaderCommandResponse,
    RFIDDashboardStats,
)
from ...services import rfid_service
from ...services.rfid_websocket import (
    rfid_ws_manager,
    create_scan_event,
    create_security_alert_event,
    create_session_status_event,
    create_batch_progress_event,
)
from .auth import get_current_user
from .dependencies import check_admin_access, require_staff as require_staff_role

router = APIRouter(prefix="/rfid", tags=["rfid"])




# ============ RFID Readers ============


@router.get("/readers", response_model=RFIDReaderListResponse)
async def list_readers(
    reader_type: Optional[RFIDReaderType] = Query(None),
    status: Optional[RFIDReaderStatus] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """List RFID readers with optional filters."""


    query = select(RFIDReader)
    count_query = select(func.count(RFIDReader.id))

    if reader_type:
        query = query.where(RFIDReader.reader_type == reader_type)
        count_query = count_query.where(RFIDReader.reader_type == reader_type)

    if status:
        query = query.where(RFIDReader.status == status)
        count_query = count_query.where(RFIDReader.status == status)

    if is_active is not None:
        query = query.where(RFIDReader.is_active == is_active)
        count_query = count_query.where(RFIDReader.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(RFIDReader.name)

    result = await db.execute(query)
    readers = result.scalars().all()

    return {
        "items": [RFIDReaderResponse.model_validate(r) for r in readers],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/readers", response_model=RFIDReaderResponse, status_code=status.HTTP_201_CREATED)
async def create_reader(
    reader_in: RFIDReaderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Register a new RFID reader."""
    check_admin_access(current_user)

    # Check for duplicate serial number
    existing = await db.execute(
        select(RFIDReader).where(RFIDReader.serial_number == reader_in.serial_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serial number already registered")

    reader = RFIDReader(**reader_in.model_dump())
    db.add(reader)
    await db.commit()
    await db.refresh(reader)
    return reader


@router.get("/readers/{reader_id}", response_model=RFIDReaderResponse)
async def get_reader(
    reader_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get RFID reader details."""


    reader = await get_or_404(db, RFIDReader, reader_id, "Reader not found")
    return reader


@router.patch("/readers/{reader_id}", response_model=RFIDReaderResponse)
async def update_reader(
    reader_id: int,
    reader_in: RFIDReaderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update RFID reader configuration."""
    check_admin_access(current_user)

    reader = await get_or_404(db, RFIDReader, reader_id, "Reader not found")

    update_data = reader_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(reader, field, value)

    await db.commit()
    await db.refresh(reader)
    return reader


@router.post("/readers/{reader_id}/heartbeat", response_model=RFIDReaderResponse)
async def reader_heartbeat(
    reader_id: int,
    status_update: RFIDReaderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update reader heartbeat and status (called by reader or polling service)."""


    reader = await rfid_service.update_reader_heartbeat(
        db=db,
        reader_id=reader_id,
        status=status_update.status,
        error=status_update.last_error,
    )
    await db.commit()
    await db.refresh(reader)
    return reader


@router.delete("/readers/{reader_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reader(
    reader_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Deactivate an RFID reader."""
    check_admin_access(current_user)

    reader = await get_or_404(db, RFIDReader, reader_id, "Reader not found")

    reader.is_active = False
    await db.commit()
    return None


# ============ RFID Tags ============


@router.get("/tags", response_model=RFIDTagListResponse)
async def list_tags(
    item_barcode: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    security_bit: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """List RFID tags with optional filters."""


    query = select(RFIDTag)
    count_query = select(func.count(RFIDTag.id))

    if item_barcode:
        query = query.where(RFIDTag.item_barcode == item_barcode)
        count_query = count_query.where(RFIDTag.item_barcode == item_barcode)

    if is_active is not None:
        query = query.where(RFIDTag.is_active == is_active)
        count_query = count_query.where(RFIDTag.is_active == is_active)

    if security_bit is not None:
        query = query.where(RFIDTag.security_bit == security_bit)
        count_query = count_query.where(RFIDTag.security_bit == security_bit)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(RFIDTag.created_at.desc())

    result = await db.execute(query)
    tags = result.scalars().all()

    return {
        "items": [RFIDTagResponse.model_validate(t) for t in tags],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/tags/{tag_id}", response_model=RFIDTagResponse)
async def get_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get RFID tag details by tag ID (hex)."""


    tag = await rfid_service.get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    # Enrich with item info
    tag_data = await rfid_service.resolve_tag_to_item(db, tag_id)
    response = RFIDTagResponse.model_validate(tag)
    if tag_data:
        _, copy, catalog_item = tag_data
        response.item_title = catalog_item.title if catalog_item else None
        response.item_author = catalog_item.author if catalog_item else None

    return response


@router.post("/tags/program", response_model=RFIDTagProgramResponse, status_code=status.HTTP_201_CREATED)
async def program_tag(
    request: RFIDTagProgramRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Program a new RFID tag for a library item."""


    result = await rfid_service.program_tag(
        db=db,
        item_barcode=request.item_barcode,
        reader_id=request.reader_id,
        user=current_user,
        tag_type=request.tag_type or "ISO 15693",
        include_item_data=request.include_item_data,
    )

    await db.commit()

    return RFIDTagProgramResponse(
        success=result["success"],
        tag_id=result["tag_id"],
        message=result["message"],
        tag=RFIDTagResponse.model_validate(result["tag"]) if result.get("tag") else None,
    )


@router.patch("/tags/{tag_id}", response_model=RFIDTagResponse)
async def update_tag(
    tag_id: str,
    tag_in: RFIDTagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Update RFID tag settings."""


    tag = await rfid_service.get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    update_data = tag_in.model_dump(exclude_unset=True)

    # Handle deactivation
    if update_data.get("is_active") is False and tag.is_active:
        if not update_data.get("deactivation_reason"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Deactivation reason required"
            )
        tag.deactivated_at = rfid_service.utc_now()

    for field, value in update_data.items():
        setattr(tag, field, value)

    await db.commit()
    await db.refresh(tag)
    return tag


@router.post("/tags/{tag_id}/security", response_model=RFIDTagResponse)
async def set_tag_security(
    tag_id: str,
    security_bit: bool = Query(..., description="True=secured, False=desensitized"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Set the security bit on an RFID tag."""


    tag = await rfid_service.update_tag_security(db, tag_id, security_bit)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.get("/tags/lookup/{barcode}", response_model=RFIDTagResponse)
async def lookup_tag_by_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Look up RFID tag by item barcode."""


    tag = await rfid_service.get_tag_by_barcode(db, barcode)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No RFID tag found for this barcode")
    return tag


# ============ Sessions ============


@router.post("/sessions", response_model=RFIDSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: RFIDSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a new RFID session."""


    session = await rfid_service.create_session(
        db=db,
        session_type=session_in.session_type,
        reader_id=session_in.reader_id,
        operator=current_user,
        patron_id=session_in.patron_id,
        inventory_audit_id=session_in.inventory_audit_id,
        target_location=session_in.target_location,
    )
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=RFIDSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get session details."""


    result = await db.execute(
        select(RFIDSession)
        .where(RFIDSession.id == session_id)
        .options(
            selectinload(RFIDSession.reader),
            selectinload(RFIDSession.operator),
            selectinload(RFIDSession.patron),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    response = RFIDSessionResponse.model_validate(session)
    response.reader_name = session.reader.name if session.reader else None
    response.operator_name = f"{session.operator.first_name} {session.operator.last_name}" if session.operator else None
    response.patron_name = f"{session.patron.first_name} {session.patron.last_name}" if session.patron else None

    return response


@router.post("/sessions/{session_id}/end", response_model=RFIDSessionResponse)
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """End an active session."""


    session = await rfid_service.end_session(db, session_id)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/scans", response_model=list[RFIDScanResponse])
async def get_session_scans(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get all scans for a session."""


    result = await db.execute(
        select(RFIDScan)
        .where(RFIDScan.session_id == session_id)
        .order_by(RFIDScan.scanned_at.desc())
    )
    scans = result.scalars().all()
    return [RFIDScanResponse.model_validate(s) for s in scans]


@router.post("/sessions/{session_id}/scan", response_model=RFIDScanResponse, status_code=status.HTTP_201_CREATED)
async def record_scan(
    session_id: int,
    scan_in: RFIDScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Record a tag scan in a session."""


    scan = await rfid_service.record_scan(
        db=db,
        session_id=session_id,
        tag_id=scan_in.tag_id,
        signal_strength=scan_in.signal_strength,
        antenna_id=scan_in.antenna_id,
        found_at_location=scan_in.found_at_location,
    )
    await db.commit()
    await db.refresh(scan)

    # Broadcast scan event via WebSocket
    scan_event = create_scan_event(
        session_id=session_id,
        tag_id=scan_in.tag_id,
        item_barcode=scan.item_barcode,
        item_title=scan.item_title,
        is_registered=scan.rfid_tag_id is not None,
        is_misplaced=scan.is_misplaced or False,
        expected_location=scan.expected_location,
        found_at_location=scan.found_at_location,
        signal_strength=scan.signal_strength,
    )
    await rfid_ws_manager.broadcast_scan(scan_event)

    return scan


# ============ Batch Checkout ============


@router.get("/batch-checkout", response_model=dict)
async def get_batch_checkout_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get information about batch checkout operation."""


    return {
        "max_items_per_batch": 50,
        "requires_patron_id": True,
        "requires_reader_id": True,
        "supports_progress_tracking": True,
        "returns_detailed_results": True,
    }


@router.post("/batch-checkout", response_model=BatchCheckoutResponse)
async def batch_checkout(
    request: BatchCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Process batch checkout for multiple items via RFID."""


    result = await rfid_service.batch_checkout(
        db=db,
        reader_id=request.reader_id,
        patron_id=request.patron_id,
        tag_ids=request.tag_ids,
        operator=current_user,
        progress_callback=_create_batch_progress_callback("checkout"),
    )
    await db.commit()
    return BatchCheckoutResponse(**result)


def _create_batch_progress_callback(operation: str):
    async def callback(session_id: int, total: int, processed: int,
                       successful: int, failed: int, current_item: dict | None):
        event = create_batch_progress_event(
            session_id=session_id,
            operation=operation,
            total_items=total,
            processed=processed,
            successful=successful,
            failed=failed,
            current_item=current_item,
        )
        await rfid_ws_manager.broadcast_batch_progress(event)
    return callback


# ============ Batch Checkin ============


@router.get("/batch-checkin", response_model=dict)
async def get_batch_checkin_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get information about batch checkin operation."""


    return {
        "max_items_per_batch": 50,
        "requires_reader_id": True,
        "supports_progress_tracking": True,
        "returns_detailed_results": True,
    }


@router.post("/batch-checkin", response_model=BatchCheckinResponse)
async def batch_checkin(
    request: BatchCheckinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Process batch checkin for multiple items via RFID."""


    result = await rfid_service.batch_checkin(
        db=db,
        reader_id=request.reader_id,
        tag_ids=request.tag_ids,
        operator=current_user,
        progress_callback=_create_batch_progress_callback("checkin"),
    )
    await db.commit()
    return BatchCheckinResponse(**result)


# ============ Security Alerts ============


@router.get("/security/alerts", response_model=SecurityAlertListResponse)
async def list_security_alerts(
    reader_id: Optional[int] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    alert_type: Optional[SecurityAlertType] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """List security alerts."""


    query = select(SecurityAlert)
    count_query = select(func.count(SecurityAlert.id))

    if reader_id:
        query = query.where(SecurityAlert.reader_id == reader_id)
        count_query = count_query.where(SecurityAlert.reader_id == reader_id)

    if is_resolved is not None:
        query = query.where(SecurityAlert.is_resolved == is_resolved)
        count_query = count_query.where(SecurityAlert.is_resolved == is_resolved)

    if alert_type:
        query = query.where(SecurityAlert.alert_type == alert_type)
        count_query = count_query.where(SecurityAlert.alert_type == alert_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query
        .offset(offset)
        .limit(per_page)
        .order_by(SecurityAlert.created_at.desc())
        .options(
            selectinload(SecurityAlert.reader),
            selectinload(SecurityAlert.resolved_by),
        )
    )

    result = await db.execute(query)
    alerts = result.scalars().all()

    items = []
    for alert in alerts:
        response = SecurityAlertResponse.model_validate(alert)
        response.reader_name = alert.reader.name if alert.reader else None
        response.reader_location = alert.reader.location if alert.reader else None
        response.resolved_by_name = (
            f"{alert.resolved_by.first_name} {alert.resolved_by.last_name}"
            if alert.resolved_by else None
        )
        items.append(response)

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.post("/security/alerts", response_model=SecurityAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_security_alert(
    alert_in: SecurityAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a security alert (typically from gate sensor)."""


    alert = await rfid_service.handle_security_alert(
        db=db,
        reader_id=alert_in.reader_id,
        tag_id=alert_in.tag_id,
        signal_strength=alert_in.signal_strength,
    )
    await db.commit()

    # Load reader for response
    result = await db.execute(
        select(SecurityAlert)
        .where(SecurityAlert.id == alert.id)
        .options(selectinload(SecurityAlert.reader))
    )
    alert = result.scalar_one()

    # Broadcast security alert via WebSocket
    ws_event = create_security_alert_event(
        alert_id=alert.id,
        reader_id=alert.reader_id,
        alert_type=str(alert.alert_type),
        reader_name=alert.reader.name if alert.reader else None,
        reader_location=alert.reader.location if alert.reader else None,
        tag_id=alert.tag_id,
        item_barcode=alert.item_barcode,
        item_title=alert.item_title,
    )
    await rfid_ws_manager.broadcast_security_alert(ws_event)

    return alert


@router.post("/security/alerts/{alert_id}/resolve", response_model=SecurityAlertResponse)
async def resolve_security_alert(
    alert_id: int,
    resolve_in: SecurityAlertResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Resolve a security alert."""


    alert = await rfid_service.resolve_security_alert(
        db=db,
        alert_id=alert_id,
        user=current_user,
        resolution_notes=resolve_in.resolution_notes,
    )
    await db.commit()
    await db.refresh(alert)
    return alert


# ============ Inventory Mode ============


@router.post("/inventory/start", response_model=RFIDSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_inventory_session(
    request: InventoryScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Start an inventory scanning session."""


    session = await rfid_service.start_inventory_session(
        db=db,
        reader_id=request.reader_id,
        operator=current_user,
        inventory_audit_id=request.inventory_audit_id,
        target_location=request.target_location,
        create_audit=request.create_audit,
        audit_name=request.audit_name,
    )
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/inventory/scan/{session_id}")
async def process_inventory_scan(
    session_id: int,
    scan_in: RFIDScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Process a scan during inventory mode."""


    result = await rfid_service.process_inventory_scan(
        db=db,
        session_id=session_id,
        tag_id=scan_in.tag_id,
        found_at_location=scan_in.found_at_location,
        signal_strength=scan_in.signal_strength,
    )
    await db.commit()

    # Broadcast scan event via WebSocket
    scan_event = create_scan_event(
        session_id=session_id,
        tag_id=scan_in.tag_id,
        item_barcode=result.get("item_barcode"),
        item_title=result.get("item_title"),
        is_registered=result.get("registered", False),
        is_misplaced=result.get("is_misplaced", False),
        expected_location=result.get("expected_location"),
        found_at_location=result.get("found_at_location"),
        signal_strength=scan_in.signal_strength,
    )
    await rfid_ws_manager.broadcast_scan(scan_event)

    return result


# ============ Shelf Reading ============


@router.post("/shelf-read/start", response_model=RFIDSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_shelf_read(
    request: ShelfReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Start a shelf reading session."""


    session = await rfid_service.start_shelf_read_session(
        db=db,
        reader_id=request.reader_id,
        operator=current_user,
        target_location=request.target_location,
    )
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/shelf-read/{session_id}/results", response_model=ShelfReadResult)
async def get_shelf_read_results(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get results of a shelf reading session."""


    results = await rfid_service.get_shelf_read_results(db, session_id)
    return ShelfReadResult(**results)


# ============ Missing Items ============


@router.post("/missing-items", response_model=list[MissingItemResponse])
async def find_missing_items(
    request: MissingItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Find missing items based on inventory data."""


    items = await rfid_service.find_missing_items(
        db=db,
        inventory_audit_id=request.inventory_audit_id,
        location_filter=request.location_filter,
        days_since_last_seen=request.days_since_last_seen,
    )
    return [MissingItemResponse(**item) for item in items]


# ============ Dashboard ============


@router.get("/dashboard", response_model=RFIDDashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get RFID system dashboard statistics."""


    stats = await rfid_service.get_rfid_dashboard_stats(db)

    # Convert models to response objects
    recent_sessions = []
    for session in stats["recent_sessions"]:
        response = RFIDSessionResponse.model_validate(session)
        response.reader_name = session.reader.name if session.reader else None
        response.operator_name = (
            f"{session.operator.first_name} {session.operator.last_name}"
            if session.operator else None
        )
        recent_sessions.append(response)

    recent_alerts = []
    for alert in stats["recent_alerts"]:
        response = SecurityAlertResponse.model_validate(alert)
        response.reader_name = alert.reader.name if alert.reader else None
        response.reader_location = alert.reader.location if alert.reader else None
        recent_alerts.append(response)

    return RFIDDashboardStats(
        total_readers=stats["total_readers"],
        readers_online=stats["readers_online"],
        readers_offline=stats["readers_offline"],
        readers_error=stats["readers_error"],
        total_tags=stats["total_tags"],
        active_tags=stats["active_tags"],
        total_sessions_today=stats["total_sessions_today"],
        items_processed_today=stats["items_processed_today"],
        security_alerts_today=stats["security_alerts_today"],
        unresolved_alerts=stats["unresolved_alerts"],
        recent_sessions=recent_sessions,
        recent_alerts=recent_alerts,
    )


# ============ WebSocket for Real-time Updates ============


@router.websocket("/ws")
async def rfid_websocket(
    websocket: WebSocket,
    subscriptions: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None, alias="sessionId"),
):
    # Parse subscriptions
    sub_list = None
    if subscriptions:
        sub_list = [s.strip() for s in subscriptions.split(",") if s.strip()]

    # Connect with optional session_id for reconnection
    assigned_session_id = await rfid_ws_manager.connect(
        websocket,
        sub_list,
        session_id=session_id
    )

    try:
        while True:
            # Handle incoming messages (for subscription management)
            data = await websocket.receive_json()

            if data.get("action") == "subscribe":
                channel = data.get("channel")
                if channel:
                    await rfid_ws_manager.subscribe(websocket, channel)
                    await websocket.send_json({
                        "event_type": "subscribed",
                        "channel": channel,
                    })

            elif data.get("action") == "unsubscribe":
                channel = data.get("channel")
                if channel:
                    await rfid_ws_manager.unsubscribe(websocket, channel)
                    await websocket.send_json({
                        "event_type": "unsubscribed",
                        "channel": channel,
                    })

            elif data.get("action") == "ping":
                await websocket.send_json({"event_type": "pong"})

            elif data.get("action") == "get_session_info":
                # Allow client to query their session info
                session_info = rfid_ws_manager.get_session_info(assigned_session_id)
                await websocket.send_json({
                    "event_type": "session_info",
                    "session": session_info,
                })

            elif data.get("action") == "terminate_session":
                # Client explicitly wants to end session (e.g., logout)
                await rfid_ws_manager.terminate_session(assigned_session_id)
                await websocket.send_json({
                    "event_type": "session_terminated",
                    "session_id": assigned_session_id,
                })
                # Close the connection after termination
                await websocket.close()
                break

    except WebSocketDisconnect:
        await rfid_ws_manager.disconnect(websocket)
    except Exception:  # noqa: BLE001  # WebSocket cleanup on any error path
        await rfid_ws_manager.disconnect(websocket)


@router.get("/ws/session/{session_id}")
async def get_websocket_session_info(
    session_id: str,
    current_user: User = Depends(require_staff_role),
):
    """Get information about a specific WebSocket session (admin only)."""
    check_admin_access(current_user)
    session_info = rfid_ws_manager.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_info


@router.delete("/ws/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_websocket_session(
    session_id: str,
    current_user: User = Depends(require_staff_role),
):
    """Terminate a WebSocket session (admin only)."""
    check_admin_access(current_user)
    session_info = rfid_ws_manager.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await rfid_ws_manager.terminate_session(session_id)
    return None


@router.get("/ws/stats")
async def websocket_stats(
    current_user: User = Depends(require_staff_role),
):
    """Get WebSocket connection statistics (admin only)."""
    check_admin_access(current_user)
    return rfid_ws_manager.get_subscription_stats()



