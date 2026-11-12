# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Z39.50 Source Admin CRUD endpoints."""
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...models.z3950_source import Z3950Source
from .dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/z3950-sources", tags=["admin-z3950"])


class Z3950SourceCreate(BaseModel):
    name: str = Field(..., max_length=100)
    host: str = Field(..., max_length=255)
    port: int = 210
    database_name: str = Field(..., max_length=100)
    syntax: str = "USMARC"
    encoding: str = "UTF-8"
    sru_url: Optional[str] = None
    requires_auth: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    is_enabled: bool = True
    display_order: int = 0
    notes: Optional[str] = None


class Z3950SourceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    syntax: Optional[str] = None
    encoding: Optional[str] = None
    sru_url: Optional[str] = None
    requires_auth: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_enabled: Optional[bool] = None
    display_order: Optional[int] = None
    notes: Optional[str] = None


class Z3950SourceResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    database_name: str
    syntax: str
    encoding: str
    sru_url: Optional[str] = None
    requires_auth: bool
    username: Optional[str] = None
    password_set: bool = False
    is_enabled: bool
    display_order: int
    last_tested_at: Optional[datetime] = None
    last_test_success: Optional[bool] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TestResult(BaseModel):
    success: bool
    message: str
    response_time_ms: Optional[int] = None


def _to_response(source: Z3950Source) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "host": source.host,
        "port": source.port,
        "database_name": source.database_name,
        "syntax": source.syntax,
        "encoding": source.encoding,
        "sru_url": source.sru_url,
        "requires_auth": source.requires_auth,
        "username": source.username,
        "password_set": bool(source.password_hash),
        "is_enabled": source.is_enabled,
        "display_order": source.display_order,
        "last_tested_at": source.last_tested_at.isoformat() if source.last_tested_at else None,
        "last_test_success": source.last_test_success,
        "notes": source.notes,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
    }


@router.get("", response_model=List[Z3950SourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all Z39.50 sources."""
    result = await db.execute(
        select(Z3950Source).order_by(Z3950Source.display_order, Z3950Source.name)
    )
    sources = result.scalars().all()
    return [_to_response(s) for s in sources]


@router.post("", response_model=Z3950SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: Z3950SourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new Z39.50 source."""
    source = Z3950Source(
        name=payload.name,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        syntax=payload.syntax,
        encoding=payload.encoding,
        sru_url=payload.sru_url,
        requires_auth=payload.requires_auth,
        username=payload.username,
        password_hash=payload.password if payload.password else None,
        is_enabled=payload.is_enabled,
        display_order=payload.display_order,
        notes=payload.notes,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _to_response(source)


@router.put("/{source_id}", response_model=Z3950SourceResponse)
async def update_source(
    source_id: int,
    payload: Z3950SourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update a Z39.50 source."""
    source = await db.get(Z3950Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = payload.model_dump(exclude_unset=True)
    password = update_data.pop("password", None)
    if password:
        source.password_hash = password

    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return _to_response(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a Z39.50 source."""
    source = await db.get(Z3950Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/test", response_model=TestResult)
async def test_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Test connection to a Z39.50 source."""
    source = await db.get(Z3950Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    start = datetime.now(timezone.utc)
    success = False
    message = ""

    try:
        if source.sru_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(source.sru_url, params={"operation": "explain", "version": "1.1"})
                if resp.status_code == 200:
                    success = True
                    message = f"SRU connection successful ({resp.status_code})"
                else:
                    message = f"SRU returned status {resp.status_code}"
        else:
            message = "No SRU URL configured; native Z39.50 test not available"
    except Exception as e:  # noqa: BLE001  # connection test — surface failure as message
        message = f"Connection failed: {str(e)}"

    elapsed = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

    source.last_tested_at = datetime.now(timezone.utc)
    source.last_test_success = success
    await db.commit()

    return TestResult(success=success, message=message, response_time_ms=elapsed)


@router.post("/seed", response_model=List[Z3950SourceResponse])
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Seed default Z39.50 sources (LOC + OCLC)."""
    defaults = [
        Z3950Source(
            name="Library of Congress",
            host="lx2.loc.gov",
            port=210,
            database_name="LCDB",
            syntax="USMARC",
            encoding="UTF-8",
            sru_url="https://lx2.loc.gov/sru/lcdb",
            requires_auth=False,
            is_enabled=True,
            display_order=1,
        ),
        Z3950Source(
            name="OCLC WorldCat",
            host="z3950.oclc.org",
            port=210,
            database_name="OLUCWorldCat",
            syntax="USMARC",
            encoding="UTF-8",
            requires_auth=True,
            is_enabled=False,
            display_order=2,
            notes="Requires OCLC authentication/subscription",
        ),
    ]

    created = []
    for src in defaults:
        existing = await db.execute(
            select(Z3950Source).where(Z3950Source.host == src.host, Z3950Source.database_name == src.database_name)
        )
        if not existing.scalar_one_or_none():
            db.add(src)
            await db.flush()
            await db.refresh(src)
            created.append(src)

    await db.commit()
    return [_to_response(s) for s in created]
