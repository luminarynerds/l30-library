# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board audit log read API - role-gated access to governance audit trail."""

import csv
import io
import json as json_lib
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.audit_log import audit_log_event
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import BoardAuditLogResponse
from ..auth import get_current_user

router = APIRouter(prefix="/board/audit-logs", tags=["board-audit"])


@router.get("/legal-discovery")
async def legal_discovery_export(
    date_range_start: Optional[datetime] = Query(None, description="Start of date range"),
    date_range_end: Optional[datetime] = Query(None, description="End of date range"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user who performed action"),
    format: str = Query("json", pattern="^(csv|json)$", description="Export format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Legal discovery export of board audit records.

    Produces a forensic-grade export with metadata envelope documenting who
    exported, when, what filters were applied, and total record count.
    Includes a note about the HMAC-signed backup audit trail for verification.

    Requires ADMIN or SUPER_ADMIN role.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required for legal discovery exports")

    query = select(BoardAuditLog)
    filters = []
    filter_description = {}

    if date_range_start:
        filters.append(BoardAuditLog.created_at >= date_range_start)
        filter_description["date_range_start"] = date_range_start.isoformat()
    if date_range_end:
        filters.append(BoardAuditLog.created_at <= date_range_end)
        filter_description["date_range_end"] = date_range_end.isoformat()
    if entity_type:
        filters.append(BoardAuditLog.entity_type == entity_type)
        filter_description["entity_type"] = entity_type
    if entity_id is not None:
        filters.append(BoardAuditLog.entity_id == entity_id)
        filter_description["entity_id"] = entity_id
    if action_type:
        filters.append(BoardAuditLog.action == action_type)
        filter_description["action_type"] = action_type
    if user_id is not None:
        filters.append(BoardAuditLog.user_id == user_id)
        filter_description["user_id"] = user_id

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    # Get all matching records (no pagination for legal discovery)
    query = query.order_by(BoardAuditLog.created_at.asc())
    result = await db.execute(query)
    logs = result.scalars().all()

    now = datetime.now(timezone.utc)
    export_metadata = {
        "export_type": "legal_discovery",
        "exported_by_user_id": current_user.id,
        "exported_by_email": current_user.email,
        "exported_at": now.isoformat(),
        "filters_applied": filter_description if filter_description else "none",
        "total_records": total_count,
        "data_source": "BoardAuditLog (PostgreSQL database)",
        "hmac_backup_note": "A tamper-evident HMAC-signed copy of audit events is maintained at /var/log/l30/audit.log. Cross-reference this export with the HMAC log for forensic verification.",
    }

    # Log the export itself
    audit_log_event(
        event_type="BOARD_LEGAL_DISCOVERY_EXPORT",
        user_id=current_user.id,
        email=current_user.email,
        severity="CRITICAL",
        details={"filters": filter_description, "total_records": total_count, "format": format},
    )

    today = date.today().isoformat()

    if format == "json":
        data = []
        for log in logs:
            data.append({
                "id": log.id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "user_id": log.user_id,
                "action": log.action.value if hasattr(log.action, "value") else log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "meeting_id": log.meeting_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "notes": log.notes,
            })

        envelope = {
            "metadata": export_metadata,
            "records": data,
        }

        return Response(
            content=json_lib.dumps(envelope, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="legal-discovery-{today}.json"'},
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)

        # Metadata comment rows at top
        writer.writerow(["# LEGAL DISCOVERY EXPORT"])
        writer.writerow([f"# Exported by: {current_user.email} (user_id={current_user.id})"])
        writer.writerow([f"# Exported at: {now.isoformat()}"])
        writer.writerow([f"# Filters: {json_lib.dumps(filter_description) if filter_description else 'none'}"])
        writer.writerow([f"# Total records: {total_count}"])
        writer.writerow([f"# Data source: BoardAuditLog (PostgreSQL database)"])
        writer.writerow(["# HMAC backup: Tamper-evident HMAC-signed copy at /var/log/l30/audit.log"])
        writer.writerow([])

        # Header row
        writer.writerow(["id", "created_at", "user_id", "action", "entity_type", "entity_id", "meeting_id", "details", "ip_address", "notes"])

        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.isoformat() if log.created_at else "",
                log.user_id,
                log.action.value if hasattr(log.action, "value") else log.action,
                log.entity_type,
                log.entity_id,
                log.meeting_id,
                json_lib.dumps(log.details) if log.details else "",
                log.ip_address,
                log.notes,
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="legal-discovery-{today}.csv"'},
        )


@router.get("/export")
async def export_board_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    meeting_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export board audit logs as CSV or JSON file (director/admin only)."""
    if current_user.role not in [UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director or admin access required")

    query = select(BoardAuditLog)

    filters = []
    if entity_type:
        filters.append(BoardAuditLog.entity_type == entity_type)
    if entity_id is not None:
        filters.append(BoardAuditLog.entity_id == entity_id)
    if action:
        filters.append(BoardAuditLog.action == action)
    if user_id is not None:
        filters.append(BoardAuditLog.user_id == user_id)
    if meeting_id is not None:
        filters.append(BoardAuditLog.meeting_id == meeting_id)
    if date_from:
        filters.append(BoardAuditLog.created_at >= date_from)
    if date_to:
        filters.append(BoardAuditLog.created_at <= date_to)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(BoardAuditLog.created_at.desc()).limit(10000)

    result = await db.execute(query)
    logs = result.scalars().all()

    today = date.today().isoformat()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "created_at", "user_id", "action", "entity_type", "entity_id", "meeting_id", "details", "ip_address", "notes"])
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.isoformat() if log.created_at else "",
                log.user_id,
                log.action.value if hasattr(log.action, "value") else log.action,
                log.entity_type,
                log.entity_id,
                log.meeting_id,
                json_lib.dumps(log.details) if log.details else "",
                log.ip_address,
                log.notes,
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="board-audit-log-{today}.csv"'},
        )
    else:
        data = [
            {
                "id": log.id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "user_id": log.user_id,
                "action": log.action.value if hasattr(log.action, "value") else log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "meeting_id": log.meeting_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "notes": log.notes,
            }
            for log in logs
        ]
        return Response(
            content=json_lib.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="board-audit-log-{today}.json"'},
        )


@router.get("", response_model=List[BoardAuditLogResponse])
async def get_board_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user who performed action"),
    meeting_id: Optional[int] = Query(None, description="Filter by related meeting"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query board audit logs (director/admin only)."""
    if current_user.role not in [UserRole.DIRECTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director or admin access required")

    query = select(BoardAuditLog)

    filters = []
    if entity_type:
        filters.append(BoardAuditLog.entity_type == entity_type)
    if entity_id is not None:
        filters.append(BoardAuditLog.entity_id == entity_id)
    if action:
        filters.append(BoardAuditLog.action == action)
    if user_id is not None:
        filters.append(BoardAuditLog.user_id == user_id)
    if meeting_id is not None:
        filters.append(BoardAuditLog.meeting_id == meeting_id)
    if date_from:
        filters.append(BoardAuditLog.created_at >= date_from)
    if date_to:
        filters.append(BoardAuditLog.created_at <= date_to)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(BoardAuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
