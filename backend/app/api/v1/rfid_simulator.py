# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
RFID Simulator API Routes.

Endpoints for testing RFID functionality without physical hardware.
Only available in development/testing environments.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...models.rfid import RFIDReaderType, RFIDReaderStatus
from ...models.user import User
from ...services.rfid_simulator import rfid_simulator
from .dependencies import check_admin_access, require_staff as require_staff_role

router = APIRouter(prefix="/rfid/simulator", tags=["rfid-simulator"])




def require_development():
    settings = get_settings()
    if settings.environment not in ["development", "testing", "local"]:
        raise HTTPException(
            status_code=403,
            detail="Simulator only available in development/testing environments"
        )


# ============ Request/Response Schemas ============


class CreateReaderRequest(BaseModel):
    name: str = Field(default="Test Reader", min_length=1, max_length=100)
    reader_type: RFIDReaderType = RFIDReaderType.CIRCULATION_DESK
    location: str = Field(default="Test Location", max_length=200)


class SimulateTagReadRequest(BaseModel):
    session_id: int
    tag_id: Optional[str] = Field(None, description="Specific tag ID, or random if omitted")
    signal_strength: Optional[float] = Field(None, ge=-100, le=0)
    found_at_location: Optional[str] = None


class SimulateBatchReadRequest(BaseModel):
    session_id: int
    count: int = Field(default=5, ge=1, le=50)
    include_registered: bool = True
    include_unregistered: bool = True
    delay_ms: int = Field(default=200, ge=0, le=5000)


class SimulateSecurityAlertRequest(BaseModel):
    reader_id: int
    tag_id: Optional[str] = None
    use_registered_tag: bool = True


class SimulateReaderStatusRequest(BaseModel):
    reader_id: int
    status: RFIDReaderStatus
    error_message: Optional[str] = None


class AutoScanRequest(BaseModel):
    session_id: int
    interval_ms: int = Field(default=1000, ge=100, le=10000)
    include_registered: bool = True
    include_unregistered: bool = False


class CreateTestTagsRequest(BaseModel):
    reader_id: int
    count: int = Field(default=10, ge=1, le=100)


# ============ Endpoints ============


@router.post("/readers")
async def create_simulated_reader(
    request: CreateReaderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create a simulated RFID reader for testing."""
    check_admin_access(current_user)
    require_development()

    reader = await rfid_simulator.create_simulated_reader(
        db=db,
        name=request.name,
        reader_type=request.reader_type,
        location=request.location,
    )
    await db.commit()
    await db.refresh(reader)

    return {
        "message": "Simulated reader created",
        "reader_id": reader.id,
        "name": reader.name,
        "serial_number": reader.serial_number,
    }


@router.post("/scan")
async def simulate_tag_read(
    request: SimulateTagReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Simulate a single RFID tag being read."""
    check_admin_access(current_user)
    require_development()

    result = await rfid_simulator.simulate_tag_read(
        db=db,
        session_id=request.session_id,
        tag_id=request.tag_id,
        signal_strength=request.signal_strength,
        found_at_location=request.found_at_location,
    )
    await db.commit()
    return result


@router.get("/batch-scan", response_model=dict)
async def get_batch_scan_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get information about batch scan simulation."""
    check_admin_access(current_user)
    require_development()

    return {
        "description": "Simulate multiple RFID tags being read (stack of items)",
        "max_count": 100,
        "supports_delay": True,
        "supports_filtering": True,
        "available_filters": ["include_registered", "include_unregistered"],
        "requires_session_id": True,
    }


@router.post("/batch-scan")
async def simulate_batch_read(
    request: SimulateBatchReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Simulate multiple RFID tags being read (stack of items)."""
    check_admin_access(current_user)
    require_development()

    results = await rfid_simulator.simulate_batch_read(
        db=db,
        session_id=request.session_id,
        count=request.count,
        include_registered=request.include_registered,
        include_unregistered=request.include_unregistered,
        delay_ms=request.delay_ms,
    )
    await db.commit()

    return {
        "message": f"Simulated {len(results)} tag reads",
        "scans": results,
    }


@router.post("/security-alert")
async def simulate_security_alert(
    request: SimulateSecurityAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Simulate a security gate alert."""
    check_admin_access(current_user)
    require_development()

    result = await rfid_simulator.simulate_security_alert(
        db=db,
        reader_id=request.reader_id,
        tag_id=request.tag_id,
        use_registered_tag=request.use_registered_tag,
    )
    await db.commit()
    return result


@router.post("/reader-status")
async def simulate_reader_status(
    request: SimulateReaderStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Simulate a reader status change (online/offline/error)."""
    check_admin_access(current_user)
    require_development()

    result = await rfid_simulator.simulate_reader_status_change(
        db=db,
        reader_id=request.reader_id,
        status=request.status,
        error_message=request.error_message,
    )
    await db.commit()
    return result


@router.get("/auto-scan/start", response_model=dict)
async def get_auto_scan_start_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Get information about starting auto scan."""
    check_admin_access(current_user)
    require_development()

    return {
        "description": "Start continuous automatic scanning simulation",
        "default_interval_ms": 1000,
        "min_interval_ms": 100,
        "max_interval_ms": 60000,
        "supports_filtering": True,
        "requires_session_id": True,
    }


@router.post("/auto-scan/start")
async def start_auto_scan(
    request: AutoScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Start continuous automatic scanning simulation."""
    check_admin_access(current_user)
    require_development()

    await rfid_simulator.start_auto_scan(
        db=db,
        session_id=request.session_id,
        interval_ms=request.interval_ms,
        include_registered=request.include_registered,
        include_unregistered=request.include_unregistered,
    )

    return {
        "message": f"Auto-scan started for session {request.session_id}",
        "interval_ms": request.interval_ms,
    }


@router.get("/auto-scan/stop/{session_id}", response_model=dict)
async def get_stop_scan_info(
    session_id: int,
    current_user: User = Depends(require_staff_role),
):
    """Get information about stopping auto scan for a session."""
    check_admin_access(current_user)
    require_development()

    return {
        "session_id": session_id,
        "action": "stop",
        "description": "Stop automatic scanning for a specific session",
    }


@router.post("/auto-scan/stop/{session_id}")
async def stop_auto_scan(
    session_id: int,
    current_user: User = Depends(require_staff_role),
):
    """Stop automatic scanning for a session."""
    check_admin_access(current_user)
    require_development()

    await rfid_simulator.stop_auto_scan(session_id)
    return {"message": f"Auto-scan stopped for session {session_id}"}


@router.get("/auto-scan/stop-all", response_model=dict)
async def get_stop_all_info(
    current_user: User = Depends(require_staff_role),
):
    """Get information about stopping all auto scans."""
    check_admin_access(current_user)
    require_development()

    return {
        "action": "stop-all",
        "description": "Stop all automatic scanning tasks",
    }


@router.post("/auto-scan/stop-all")
async def stop_all_auto_scans(
    current_user: User = Depends(require_staff_role),
):
    """Stop all automatic scanning tasks."""
    check_admin_access(current_user)
    require_development()

    await rfid_simulator.stop_all_auto_scans()
    return {"message": "All auto-scans stopped"}


@router.get("/auto-scan/status")
async def get_auto_scan_status(
    current_user: User = Depends(require_staff_role),
):
    """Get status of all auto-scan tasks."""
    check_admin_access(current_user)
    require_development()

    return rfid_simulator.get_auto_scan_status()


@router.post("/test-tags")
async def create_test_tags(
    request: CreateTestTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_role),
):
    """Create test RFID tags linked to existing items."""
    check_admin_access(current_user)
    require_development()

    tags = await rfid_simulator.create_test_tags(
        db=db,
        reader_id=request.reader_id,
        user_id=current_user.id,
        count=request.count,
    )
    await db.commit()

    return {
        "message": f"Created {len(tags)} test RFID tags",
        "tags": [
            {
                "tag_id": tag.tag_id,
                "item_barcode": tag.item_barcode,
            }
            for tag in tags
        ],
    }
