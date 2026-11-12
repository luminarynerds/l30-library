# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unified Item Issues Endpoint

Provides a consolidated view of lost items, damaged items, and claims-returned disputes
with unified filtering, searching, and bulk operations.

Performance target: <1s load for 1000+ items with pagination.
"""

from app.core.logging import get_logger
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.item_issues_unified import (
    UnifiedItemIssuesListResponse,
    UnifiedItemIssueResponse,
    UpdateStatusRequest,
    BulkUpdateStatusRequest,
    BulkUpdateStatusResponse,
    ContactPatronRequest,
)
from ....services.item_issues_unified_service import ItemIssuesUnifiedService
from ..auth import get_current_user
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.get("/item-issues", response_model=UnifiedItemIssuesListResponse)
async def list_unified_item_issues(
    issue_types: Optional[str] = Query(
        None,
        description="Comma-separated issue types: lost,damaged,claims"
    ),
    statuses: Optional[str] = Query(
        None,
        description="Comma-separated statuses: reported,claimed,resolved"
    ),
    patron_id: Optional[int] = Query(None, description="Filter by patron ID"),
    days_ago: Optional[int] = Query(None, ge=1, description="Items from last X days"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("reported_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get unified list of all item issues (lost, damaged, claims).

    Provides consolidated view for operational management with filtering and pagination.
    Performance optimized for <1s load with 1000+ items.
    """
    # Parse comma-separated values
    issue_types_list = None
    if issue_types:
        issue_types_list = [t.strip() for t in issue_types.split(",")]

    statuses_list = None
    if statuses:
        statuses_list = [s.strip() for s in statuses.split(",")]

    service = ItemIssuesUnifiedService(db)

    try:
        items, total = await service.get_unified_issues(
            issue_types=issue_types_list,
            statuses=statuses_list,
            patron_id=patron_id,
            days_ago=days_ago,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Convert to response models
        item_responses = [
            UnifiedItemIssueResponse(
                id=item.id,
                issue_type=item.issue_type,
                status=item.status,
                patron_id=item.patron_id,
                patron_name=item.patron_name,
                patron_email=item.patron_email,
                item_title=item.item_title,
                item_copy_id=item.item_copy_id,
                reported_at=item.reported_at,
                reported_by_id=item.reported_by_id,
                reported_by_name=item.reported_by_name,
                lost_type=item.lost_type,
                replacement_cost=item.replacement_cost,
                severity=item.severity,
                is_patron_responsible=item.is_patron_responsible,
                claimed_return_date=item.claimed_return_date,
                days_since_reported=item.days_since_reported,
                resolved_at=item.resolved_at,
            )
            for item in items
        ]

        return UnifiedItemIssuesListResponse(
            items=item_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Error listing unified item issues: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving item issues: {str(e)}"
        ) from e


@router.patch("/item-issues/{issue_id}/status")
async def update_item_issue_status(
    issue_id: int,
    issue_type: str = Query(..., description="Issue type: lost, damaged, or claims"),
    request: UpdateStatusRequest = Body(...),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of an item issue.

    Supports status transitions for lost, damaged, and claims-returned items.
    """
    service = ItemIssuesUnifiedService(db)

    try:
        if issue_type == "lost":
            success = await service.update_lost_item_status(issue_id, request.status, request.notes)
        elif issue_type == "damaged":
            success = await service.update_damaged_item_status(issue_id, request.status, request.notes)
        elif issue_type == "claims":
            success = await service.update_claim_status(issue_id, request.status, request.notes)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid issue type: {issue_type}"
            )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{issue_type} issue {issue_id} not found"
            )

        return {
            "success": True,
            "message": f"Status updated to {request.status}",
            "issue_id": issue_id,
            "issue_type": issue_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating issue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating status: {str(e)}"
        ) from e


@router.post("/item-issues/bulk-update-status", response_model=BulkUpdateStatusResponse)
async def bulk_update_issue_statuses(
    request: BulkUpdateStatusRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk update statuses for multiple item issues.

    Useful for batch operations like marking multiple items as resolved
    or updating multiple claims at once.
    """
    service = ItemIssuesUnifiedService(db)

    try:
        results = await service.bulk_update_statuses(request.updates)
        return BulkUpdateStatusResponse(**results)

    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk update: {str(e)}"
        ) from e


@router.post("/item-issues/{issue_id}/contact-patron")
async def contact_patron_about_issue(
    issue_id: int,
    issue_type: str = Query(..., description="Issue type: lost, damaged, or claims"),
    request: ContactPatronRequest = Body(...),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Contact patron about an item issue.

    Links to messaging system for staff communication with patron.
    Supports email and SMS notifications.
    """
    # For now, this endpoint returns the patron contact info
    # Actual messaging is handled by the messaging system

    service = ItemIssuesUnifiedService(db)

    try:
        # Get the issue
        issues, _ = await service.get_unified_issues(
            issue_types=[issue_type],
            limit=1,
            offset=0,
        )

        # Find the matching issue
        issue = None
        for i in issues:
            if i.id == issue_id:
                issue = i
                break

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue {issue_id} not found"
            )

        if not issue.patron_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Issue has no associated patron"
            )

        # Return patron contact info and messaging link
        return {
            "success": True,
            "patron_id": issue.patron_id,
            "patron_name": issue.patron_name,
            "patron_email": issue.patron_email,
            "message": f"Ready to contact patron about {issue_type} issue #{issue_id}",
            "messaging_url": f"/staff/messaging/patron/{issue.patron_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error contacting patron: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        ) from e


@router.get("/item-issues/stats/summary")
async def get_item_issues_summary(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for all item issues.

    Returns counts by type and status for dashboard overview.
    """
    service = ItemIssuesUnifiedService(db)

    try:
        # Get all issues
        all_issues, total = await service.get_unified_issues(
            limit=1000,  # Get up to 1000 for stats
        )

        # Count by type and status
        stats = {
            "total": total,
            "by_type": {
                "lost": 0,
                "damaged": 0,
                "claims": 0,
            },
            "by_status": {
                "reported": 0,
                "claimed": 0,
                "resolved": 0,
            },
        }

        for issue in all_issues:
            stats["by_type"][issue.issue_type] += 1

            if issue.status in ["reported", "claimed", "resolved"]:
                stats["by_status"][issue.status] += 1

        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        ) from e
