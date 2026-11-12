# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""EZproxy stanza import endpoints."""
from app.core.logging import get_logger
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.database_subscription import (
    DatabaseSubscription,
    SubscriptionStatus,
)
from ...models.user import User, UserRole
from ...services.stanza_importer import parse_stanza_file
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)
router = APIRouter(prefix="/databases/import", tags=["database-import"])


class StanzaPreviewItem(BaseModel):
    title: str
    url: str
    hosts: list[str]
    domains: list[str]
    line_number: int


class StanzaWarningItem(BaseModel):
    line_number: int
    directive: str
    content: str
    reason: str


class StanzaParseResponse(BaseModel):
    parsed_count: int
    skipped_count: int
    warning_count: int
    total_lines: int
    stanzas: list[StanzaPreviewItem]
    warnings: list[StanzaWarningItem]


class StanzaImportRequest(BaseModel):
    stanzas: list[StanzaPreviewItem]
    proxy_config_id: Optional[int] = None
    set_active: bool = True


class StanzaImportResponse(BaseModel):
    created_count: int
    skipped_duplicates: int
    subscription_ids: list[int]


class StanzaParseTextRequest(BaseModel):
    content: str


@router.post("/ezproxy/parse", response_model=StanzaParseResponse)
async def parse_ezproxy_config(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parse an EZproxy config file and return preview of importable stanzas.

    Upload a config.txt file. Returns parsed stanzas for review before import.
    """
    await require_staff(current_user)

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    result = parse_stanza_file(text)

    return StanzaParseResponse(
        parsed_count=len(result.stanzas),
        skipped_count=result.skipped_lines,
        warning_count=len(result.warnings),
        total_lines=result.total_lines,
        stanzas=[
            StanzaPreviewItem(
                title=s.title,
                url=s.url,
                hosts=s.hosts,
                domains=s.domains,
                line_number=s.line_number,
            )
            for s in result.stanzas
        ],
        warnings=[
            StanzaWarningItem(
                line_number=w.line_number,
                directive=w.directive,
                content=w.content,
                reason=w.reason,
            )
            for w in result.warnings
        ],
    )


@router.post("/ezproxy/parse-text", response_model=StanzaParseResponse)
async def parse_ezproxy_text(
    body: StanzaParseTextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parse pasted EZproxy config text (alternative to file upload)."""
    await require_staff(current_user)

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="No content provided")

    result = parse_stanza_file(body.content)

    return StanzaParseResponse(
        parsed_count=len(result.stanzas),
        skipped_count=result.skipped_lines,
        warning_count=len(result.warnings),
        total_lines=result.total_lines,
        stanzas=[
            StanzaPreviewItem(
                title=s.title, url=s.url, hosts=s.hosts,
                domains=s.domains, line_number=s.line_number,
            )
            for s in result.stanzas
        ],
        warnings=[
            StanzaWarningItem(
                line_number=w.line_number, directive=w.directive,
                content=w.content, reason=w.reason,
            )
            for w in result.warnings
        ],
    )


@router.post("/ezproxy/commit", response_model=StanzaImportResponse)
async def commit_stanza_import(
    import_request: StanzaImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Commit parsed stanzas as DatabaseSubscription records.

    Call this after reviewing the parse results. Creates subscriptions
    for each stanza, skipping duplicates by URL.
    """
    if current_user.role not in [
        UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR,
    ]:
        raise HTTPException(status_code=403, detail="Only admins can import subscriptions")

    created_ids: list[int] = []
    skipped = 0

    for stanza in import_request.stanzas:
        existing = await db.execute(
            select(DatabaseSubscription).where(
                DatabaseSubscription.access_url == stanza.url
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        subscription = DatabaseSubscription(
            name=stanza.title,
            access_url=stanza.url,
            proxy_config_id=import_request.proxy_config_id,
            requires_proxy=True,
            is_active=import_request.set_active,
            status=SubscriptionStatus.ACTIVE.value,
            notes=_build_import_notes(stanza),
            created_by_id=current_user.id,
            subscription_start=date.today(),
            subscription_end=date.today().replace(year=date.today().year + 1),
        )
        db.add(subscription)
        await db.flush()
        created_ids.append(subscription.id)

    await db.commit()

    logger.info(
        "EZproxy stanza import completed",
        extra={
            "created": len(created_ids),
            "skipped_duplicates": skipped,
            "user_id": current_user.id,
        },
    )

    return StanzaImportResponse(
        created_count=len(created_ids),
        skipped_duplicates=skipped,
        subscription_ids=created_ids,
    )


def _build_import_notes(stanza: StanzaPreviewItem) -> str:
    parts = [f"Imported from EZproxy config (line {stanza.line_number})"]
    if stanza.hosts:
        parts.append(f"Hosts: {", ".join(stanza.hosts)}")
    if stanza.domains:
        parts.append(f"Domains: {", ".join(stanza.domains)}")
    return "\n".join(parts)
