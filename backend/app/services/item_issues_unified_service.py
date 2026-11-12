# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple, Literal

from sqlalchemy import and_, or_, func, select, union_all, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.lost_damaged import (
    LostItemRecord, LostItemStatus, LostItemType,
    DamagedItemRecord, DamagedItemStatus,
    ClaimsReturnedDispute, ClaimDisputeStatus,
)
from ..models.catalog import CatalogItem
from ..models.inventory import ItemCopy
from ..models.user import User


@dataclass
class UnifiedItemIssue:
    id: int
    issue_type: Literal["lost", "damaged", "claims"]  # lost, damaged, claims
    status: str  # reported, claimed (for claims), resolved, etc.
    patron_id: Optional[int]
    patron_name: Optional[str]
    item_title: Optional[str]
    item_copy_id: Optional[int]
    reported_at: datetime
    reported_by_id: Optional[int]
    reported_by_name: Optional[str]

    # Lost-specific
    lost_type: Optional[str] = None
    replacement_cost: Optional[Decimal] = None

    # Damaged-specific
    severity: Optional[str] = None
    is_patron_responsible: Optional[bool] = None

    # Claims-specific
    claimed_return_date: Optional[datetime] = None

    # Status progression metadata
    days_since_reported: int = 0
    resolved_at: Optional[datetime] = None

    # For contact patron
    patron_email: Optional[str] = None

    # Raw record references
    lost_record: Optional[LostItemRecord] = None
    damaged_record: Optional[DamagedItemRecord] = None
    claims_record: Optional[ClaimsReturnedDispute] = None


class ItemIssuesUnifiedService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_unified_issues(
        self,
        issue_types: Optional[List[str]] = None,  # ["lost", "damaged", "claims"]
        statuses: Optional[List[str]] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "reported_at",  # reported_at, status
        sort_order: str = "desc",  # asc, desc
    ) -> Tuple[List[UnifiedItemIssue], int]:
        # Default to all types if not specified
        if not issue_types:
            issue_types = ["lost", "damaged", "claims"]

        issues = []
        total_count = 0

        # Query lost items if requested
        if "lost" in issue_types:
            lost_issues, lost_count = await self._get_lost_issues(
                statuses=statuses,
                patron_id=patron_id,
                days_ago=days_ago,
            )
            issues.extend(lost_issues)
            total_count += lost_count

        # Query damaged items if requested
        if "damaged" in issue_types:
            damaged_issues, damaged_count = await self._get_damaged_issues(
                statuses=statuses,
                patron_id=patron_id,
                days_ago=days_ago,
            )
            issues.extend(damaged_issues)
            total_count += damaged_count

        # Query claims if requested
        if "claims" in issue_types:
            claims_issues, claims_count = await self._get_claims_issues(
                statuses=statuses,
                patron_id=patron_id,
                days_ago=days_ago,
            )
            issues.extend(claims_issues)
            total_count += claims_count

        # Sort combined results
        issues = self._sort_issues(issues, sort_by, sort_order)

        # Calculate days since reported for all
        now = datetime.now(timezone.utc)
        for issue in issues:
            if issue.reported_at:
                issue.days_since_reported = (now - issue.reported_at.replace(tzinfo=timezone.utc)).days

        # Paginate
        paginated = issues[offset:offset + limit]

        return paginated, total_count

    async def _get_lost_issues(
        self,
        statuses: Optional[List[str]] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
    ) -> Tuple[List[UnifiedItemIssue], int]:
        query = select(LostItemRecord).options(
            selectinload(LostItemRecord.patron),
            selectinload(LostItemRecord.catalog_item),
            selectinload(LostItemRecord.item_copy),
            selectinload(LostItemRecord.reported_by),
        )

        conditions = []

        # Filter by status (excluding resolved = written off or found)
        if statuses:
            # Map unified statuses to lost item statuses
            lost_statuses = []
            if "reported" in statuses:
                lost_statuses.extend([LostItemStatus.REPORTED, LostItemStatus.CONFIRMED])
            if "claimed" in statuses:
                lost_statuses.append(LostItemStatus.CHARGED)
            if "resolved" in statuses:
                lost_statuses.extend([LostItemStatus.FOUND, LostItemStatus.WRITTEN_OFF])

            if lost_statuses:
                conditions.append(LostItemRecord.status.in_(lost_statuses))

        if patron_id:
            conditions.append(LostItemRecord.patron_id == patron_id)

        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(LostItemRecord.reported_at >= cutoff)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        records = result.scalars().all()

        # Convert to unified issues
        issues = []
        for record in records:
            issue = UnifiedItemIssue(
                id=record.id,
                issue_type="lost",
                status=str(record.status),
                patron_id=record.patron_id,
                patron_name=record.patron.full_name if record.patron else None,
                patron_email=record.patron.email if record.patron else None,
                item_title=record.catalog_item.title if record.catalog_item else None,
                item_copy_id=record.item_copy_id,
                reported_at=record.reported_at,
                reported_by_id=record.reported_by_id,
                reported_by_name=record.reported_by.full_name if record.reported_by else None,
                lost_type=str(record.lost_type) if record.lost_type else None,
                replacement_cost=record.replacement_cost,
                resolved_at=record.found_at or record.written_off_at,
                lost_record=record,
            )
            issues.append(issue)

        return issues, len(records)

    async def _get_damaged_issues(
        self,
        statuses: Optional[List[str]] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
    ) -> Tuple[List[UnifiedItemIssue], int]:
        query = select(DamagedItemRecord).options(
            selectinload(DamagedItemRecord.patron),
            selectinload(DamagedItemRecord.catalog_item),
            selectinload(DamagedItemRecord.item_copy),
            selectinload(DamagedItemRecord.reported_by),
        )

        conditions = []

        # Filter by status
        if statuses:
            # Map unified statuses to damaged item statuses
            damaged_statuses = []
            if "reported" in statuses:
                damaged_statuses.extend([
                    DamagedItemStatus.REPORTED,
                    DamagedItemStatus.ASSESSMENT_PENDING
                ])
            if "claimed" in statuses:
                damaged_statuses.extend([
                    DamagedItemStatus.REPAIRABLE,
                    DamagedItemStatus.IN_MENDING,
                ])
            if "resolved" in statuses:
                damaged_statuses.extend([
                    DamagedItemStatus.REPAIRED,
                    DamagedItemStatus.WITHDRAWN,
                    DamagedItemStatus.CHARGED,
                ])

            if damaged_statuses:
                conditions.append(DamagedItemRecord.status.in_(damaged_statuses))

        if patron_id:
            conditions.append(DamagedItemRecord.patron_id == patron_id)

        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(DamagedItemRecord.reported_at >= cutoff)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        records = result.scalars().all()

        # Convert to unified issues
        issues = []
        for record in records:
            issue = UnifiedItemIssue(
                id=record.id,
                issue_type="damaged",
                status=str(record.status),
                patron_id=record.patron_id,
                patron_name=record.patron.full_name if record.patron else None,
                patron_email=record.patron.email if record.patron else None,
                item_title=record.catalog_item.title if record.catalog_item else None,
                item_copy_id=record.item_copy_id,
                reported_at=record.reported_at,
                reported_by_id=record.reported_by_id,
                reported_by_name=record.reported_by.full_name if record.reported_by else None,
                severity=str(record.severity) if record.severity else None,
                is_patron_responsible=record.is_patron_responsible,
                resolved_at=record.resolved_at,
                damaged_record=record,
            )
            issues.append(issue)

        return issues, len(records)

    async def _get_claims_issues(
        self,
        statuses: Optional[List[str]] = None,
        patron_id: Optional[int] = None,
        days_ago: Optional[int] = None,
    ) -> Tuple[List[UnifiedItemIssue], int]:
        query = select(ClaimsReturnedDispute).options(
            selectinload(ClaimsReturnedDispute.patron),
            selectinload(ClaimsReturnedDispute.item_copy),
            selectinload(ClaimsReturnedDispute.filed_by),
            selectinload(ClaimsReturnedDispute.lost_item_record).selectinload(
                LostItemRecord.catalog_item
            ),
        )

        conditions = []

        # Filter by status - map unified to claim statuses
        if statuses:
            claim_statuses = []
            if "reported" in statuses:
                claim_statuses.append(ClaimDisputeStatus.PENDING)
            if "claimed" in statuses:
                claim_statuses.extend([
                    ClaimDisputeStatus.UNDER_REVIEW,
                    ClaimDisputeStatus.SEARCH_IN_PROGRESS,
                ])
            if "resolved" in statuses:
                claim_statuses.extend([
                    ClaimDisputeStatus.APPROVED,
                    ClaimDisputeStatus.DENIED,
                    ClaimDisputeStatus.ITEM_FOUND,
                ])

            if claim_statuses:
                conditions.append(ClaimsReturnedDispute.status.in_(claim_statuses))

        if patron_id:
            conditions.append(ClaimsReturnedDispute.patron_id == patron_id)

        if days_ago:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)
            conditions.append(ClaimsReturnedDispute.filed_at >= cutoff)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        records = result.scalars().all()

        # Convert to unified issues
        issues = []
        for record in records:
            # Get item title from lost_item_record if available
            item_title = None
            if record.lost_item_record and record.lost_item_record.catalog_item:
                item_title = record.lost_item_record.catalog_item.title

            issue = UnifiedItemIssue(
                id=record.id,
                issue_type="claims",
                status=str(record.status),
                patron_id=record.patron_id,
                patron_name=record.patron.full_name if record.patron else None,
                patron_email=record.patron.email if record.patron else None,
                item_title=item_title,
                item_copy_id=record.item_copy_id,
                reported_at=record.filed_at,
                reported_by_id=record.filed_by_id,
                reported_by_name=record.filed_by.full_name if record.filed_by else None,
                claimed_return_date=record.claimed_return_date,
                resolved_at=record.resolved_at,
                claims_record=record,
            )
            issues.append(issue)

        return issues, len(records)

    def _sort_issues(
        self,
        issues: List[UnifiedItemIssue],
        sort_by: str,
        sort_order: str,
    ) -> List[UnifiedItemIssue]:
        reverse = sort_order.lower() == "desc"

        if sort_by == "reported_at":
            return sorted(issues, key=lambda x: x.reported_at or datetime.min, reverse=reverse)
        elif sort_by == "status":
            return sorted(issues, key=lambda x: x.status, reverse=reverse)
        elif sort_by == "issue_type":
            return sorted(issues, key=lambda x: x.issue_type, reverse=reverse)
        else:
            return issues

    async def update_lost_item_status(
        self,
        lost_record_id: int,
        new_status: str,
        notes: Optional[str] = None,
    ) -> bool:
        result = await self.db.execute(
            select(LostItemRecord).where(LostItemRecord.id == lost_record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            return False

        try:
            record.status = LostItemStatus(new_status)
            if notes:
                record.resolution_notes = notes

            if new_status == "written_off":
                record.written_off_at = datetime.now(timezone.utc)
            elif new_status == "found":
                record.found_at = datetime.now(timezone.utc)

            await self.db.commit()
            return True
        except SQLAlchemyError:
            await self.db.rollback()
            return False

    async def update_damaged_item_status(
        self,
        damaged_record_id: int,
        new_status: str,
        notes: Optional[str] = None,
    ) -> bool:
        result = await self.db.execute(
            select(DamagedItemRecord).where(DamagedItemRecord.id == damaged_record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            return False

        try:
            record.status = DamagedItemStatus(new_status)
            if notes:
                record.repair_notes = notes

            if new_status == "repaired":
                record.repair_completed_at = datetime.now(timezone.utc)
            elif new_status == "withdrawn":
                record.withdrawn_at = datetime.now(timezone.utc)

            await self.db.commit()
            return True
        except SQLAlchemyError:
            await self.db.rollback()
            return False

    async def update_claim_status(
        self,
        claim_record_id: int,
        new_status: str,
        notes: Optional[str] = None,
    ) -> bool:
        result = await self.db.execute(
            select(ClaimsReturnedDispute).where(ClaimsReturnedDispute.id == claim_record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            return False

        try:
            record.status = ClaimDisputeStatus(new_status)
            if notes:
                record.investigation_notes = notes

            if new_status in ["approved", "denied", "item_found"]:
                record.resolved_at = datetime.now(timezone.utc)
            elif new_status == "under_review":
                record.reviewed_at = datetime.now(timezone.utc)

            await self.db.commit()
            return True
        except SQLAlchemyError:
            await self.db.rollback()
            return False

    async def bulk_update_statuses(
        self,
        issue_updates: List[dict],  # [{id, issue_type, status}, ...]
    ) -> dict:
        results = {
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for update in issue_updates:
            try:
                issue_id = update.get("id")
                issue_type = update.get("issue_type")
                new_status = update.get("status")
                notes = update.get("notes")

                if issue_type == "lost":
                    success = await self.update_lost_item_status(issue_id, new_status, notes)
                elif issue_type == "damaged":
                    success = await self.update_damaged_item_status(issue_id, new_status, notes)
                elif issue_type == "claims":
                    success = await self.update_claim_status(issue_id, new_status, notes)
                else:
                    success = False

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to update {issue_type} issue {issue_id}")

            except Exception as e:  # noqa: BLE001 - per-iteration boundary — must not crash bulk update loop
                results["failed"] += 1
                results["errors"].append(str(e))

        return results
