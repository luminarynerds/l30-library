# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin endpoints for managing public computer inventory."""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.computer import Computer, ComputerType, ComputerStatus
from ...models.user import User
from ...schemas.computer import ComputerResponse, ComputerListResponse
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/computers", tags=["admin-computers"])


# --- Schemas ---

class ComputerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    computer_number: str = Field(..., min_length=1, max_length=50)
    computer_type: str = Field(default="adult")
    location: str = Field(default="")
    description: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    os_type: Optional[str] = None
    has_internet: bool = True
    has_print_release: bool = True
    max_session_minutes: int = Field(default=60, ge=15, le=480)
    installed_software: Optional[list[str]] = None
    is_active: bool = True


class ComputerUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    computer_number: Optional[str] = Field(default=None, min_length=1, max_length=50)
    computer_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    os_type: Optional[str] = None
    has_internet: Optional[bool] = None
    has_print_release: Optional[bool] = None
    max_session_minutes: Optional[int] = Field(default=None, ge=15, le=480)
    installed_software: Optional[list[str]] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    map_x: Optional[float] = None
    map_y: Optional[float] = None
    map_floor: Optional[str] = None


class ComputerStatusUpdate(BaseModel):
    status: str


# --- Endpoints ---

@router.get("", response_model=ComputerListResponse)
async def list_computers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
    include_inactive: bool = True,
    skip: int = 0,
    limit: int = 100,
):
    """List all computers for admin management (includes inactive)."""
    from sqlalchemy import func as sqlfunc

    query = select(Computer)
    if not include_inactive:
        query = query.where(Computer.is_active == True)
    query = query.order_by(Computer.name).offset(skip).limit(limit)

    result = await db.execute(query)
    computers = list(result.scalars())

    count_q = select(sqlfunc.count(Computer.id))
    if not include_inactive:
        count_q = count_q.where(Computer.is_active == True)
    total = (await db.execute(count_q)).scalar() or 0

    return ComputerListResponse(
        total=total, skip=skip, limit=limit,
        items=[ComputerResponse.model_validate(c) for c in computers],
    )


@router.post("", response_model=ComputerResponse, status_code=status.HTTP_201_CREATED)
async def create_computer(
    data: ComputerCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new computer in inventory."""
    existing = await db.execute(select(Computer).where(Computer.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Computer '{data.name}' already exists")

    existing_num = await db.execute(select(Computer).where(Computer.computer_number == data.computer_number))
    if existing_num.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Computer number '{data.computer_number}' already exists")

    computer = Computer(
        name=data.name,
        computer_number=data.computer_number,
        computer_type=ComputerType(data.computer_type),
        location=data.location,
        description=data.description,
        branch_id=data.branch_id,
        branch_name=data.branch_name,
        os_type=data.os_type,
        has_internet=data.has_internet,
        has_print_release=data.has_print_release,
        max_session_minutes=data.max_session_minutes,
        installed_software=data.installed_software or [],
        is_active=data.is_active,
        status=ComputerStatus.available,
    )
    db.add(computer)
    await db.commit()
    await db.refresh(computer)
    return ComputerResponse.model_validate(computer)


@router.patch("/{computer_id}", response_model=ComputerResponse)
async def update_computer(
    computer_id: int,
    data: ComputerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a computer's details."""
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    update_data = data.model_dump(exclude_unset=True)

    if "computer_type" in update_data and update_data["computer_type"] is not None:
        update_data["computer_type"] = ComputerType(update_data["computer_type"])
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = ComputerStatus(update_data["status"])

    if "name" in update_data and update_data["name"] != computer.name:
        existing = await db.execute(
            select(Computer).where(Computer.name == update_data["name"], Computer.id != computer_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Computer '{update_data['name']}' already exists")

    for key, value in update_data.items():
        setattr(computer, key, value)

    await db.commit()
    await db.refresh(computer)
    return ComputerResponse.model_validate(computer)


@router.patch("/{computer_id}/status", response_model=ComputerResponse)
async def update_computer_status(
    computer_id: int,
    data: ComputerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Quick status update for a computer (staff can mark maintenance/available from the floor)."""
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    computer.status = ComputerStatus(data.status)
    await db.commit()
    await db.refresh(computer)

    try:
        from ...services import floor_view_bus
        await floor_view_bus.publish(
            "computer_status_changed",
            computer_id=computer_id,
            status=computer.status.value if hasattr(computer.status, "value") else computer.status,
        )
    except Exception:  # noqa: BLE001
        pass

    return ComputerResponse.model_validate(computer)


@router.delete("/{computer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Soft-delete a computer by marking it inactive."""
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    computer.is_active = False
    computer.status = ComputerStatus.offline
    await db.commit()
