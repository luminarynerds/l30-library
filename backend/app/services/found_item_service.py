# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.found_items import (
    FoundItem,
    FoundItemClaimVerification,
    FoundItemMatch,
    FoundItemPhoto,
    FoundItemStatus,
    FoundItemStorageLocation,
    ClaimVerificationStatus,
    DisposalMethod,
    MatchConfidenceLevel,
)
from app.models.lost_damaged import LostItemRecord
from app.models.user import User
from app.core.datetime_utils import utc_now


class FoundItemService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_found_item(
        self,
        description: str,
        category: str,
        location_found: str,
        date_found: datetime,
        found_by: User,
        logged_by: User,
        color: Optional[str] = None,
        brand_or_label: Optional[str] = None,
        size: Optional[str] = None,
        condition: Optional[str] = None,
        additional_details: Optional[str] = None,
        location_details: Optional[str] = None,
        storage_location_id: Optional[int] = None,
        secure_storage_flag: bool = False,
        estimated_value: Optional[Decimal] = None,
        retention_period_days: int = 30,
        staff_notes: Optional[str] = None,
    ) -> FoundItem:
        retention_end_date = date_found + timedelta(days=retention_period_days)

        found_item = FoundItem(
            description=description,
            category=category,
            color=color,
            brand_or_label=brand_or_label,
            size=size,
            condition=condition,
            additional_details=additional_details,
            location_found=location_found,
            location_details=location_details,
            date_found=date_found,
            storage_location_id=storage_location_id,
            secure_storage_flag=secure_storage_flag,
            estimated_value=estimated_value,
            retention_period_days=retention_period_days,
            retention_end_date=retention_end_date,
            found_by_id=found_by.id,
            logged_by_id=logged_by.id,
            staff_notes=staff_notes,
            status=FoundItemStatus.LOGGED,
        )

        self.db.add(found_item)
        await self.db.flush()
        await self.db.refresh(found_item)

        # Trigger auto-matching
        await self.auto_match_found_item(found_item.id)

        return found_item

    async def get_found_item_by_id(self, found_item_id: int) -> Optional[FoundItem]:
        result = await self.db.execute(
            select(FoundItem)
            .where(FoundItem.id == found_item_id)
            .options(
                selectinload(FoundItem.photos),
                selectinload(FoundItem.matches),
                selectinload(FoundItem.claim),
                selectinload(FoundItem.storage_location),
            )
        )
        return result.scalar_one_or_none()

    async def update_found_item(
        self,
        found_item_id: int,
        **kwargs
    ) -> Optional[FoundItem]:
        found_item = await self.get_found_item_by_id(found_item_id)
        if not found_item:
            return None

        # Only allow updating specific fields
        allowed_fields = {
            "description",
            "category",
            "color",
            "brand_or_label",
            "size",
            "condition",
            "additional_details",
            "location_found",
            "location_details",
            "secure_storage_flag",
            "estimated_value",
            "staff_notes",
        }

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(found_item, field, value)

        await self.db.flush()
        await self.db.refresh(found_item)
        return found_item

    async def list_found_items(
        self,
        status: Optional[FoundItemStatus] = None,
        category: Optional[str] = None,
        location_found: Optional[str] = None,
        secure_storage_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FoundItem], int]:
        query = select(FoundItem)

        if status:
            query = query.where(FoundItem.status == status)
        if category:
            safe_cat = category.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(FoundItem.category.ilike(f"%{safe_cat}%"))
        if location_found:
            safe_loc = location_found.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(FoundItem.location_found.ilike(f"%{safe_loc}%"))
        if secure_storage_only:
            query = query.where(FoundItem.secure_storage_flag == True)

        # Get total count using the same filters as the main query
        count_query = select(func.count(FoundItem.id))
        if status:
            count_query = count_query.where(FoundItem.status == status)
        if category:
            count_query = count_query.where(FoundItem.category.ilike(f"%{safe_cat}%"))
        if location_found:
            count_query = count_query.where(FoundItem.location_found.ilike(f"%{safe_loc}%"))
        if secure_storage_only:
            count_query = count_query.where(FoundItem.secure_storage_flag == True)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = (
            query.options(
                selectinload(FoundItem.storage_location),
                selectinload(FoundItem.photos),
                selectinload(FoundItem.matches),
                selectinload(FoundItem.claim),
            )
            .order_by(FoundItem.date_found.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def search_found_items(
        self,
        search_query: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[FoundItemStatus] = None,
        location_found: Optional[str] = None,
        date_found_from: Optional[datetime] = None,
        date_found_to: Optional[datetime] = None,
        secure_storage_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FoundItem], int]:
        conditions = []

        if search_query:
            # Search across description, category, color, brand
            safe_sq = search_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_pattern = f"%{safe_sq}%"
            conditions.append(
                or_(
                    FoundItem.description.ilike(search_pattern),
                    FoundItem.category.ilike(search_pattern),
                    FoundItem.color.ilike(search_pattern),
                    FoundItem.brand_or_label.ilike(search_pattern),
                    FoundItem.location_found.ilike(search_pattern),
                )
            )

        if category:
            safe_cat = category.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(FoundItem.category.ilike(f"%{safe_cat}%"))
        if status:
            conditions.append(FoundItem.status == status)
        if location_found:
            safe_loc = location_found.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(FoundItem.location_found.ilike(f"%{safe_loc}%"))
        if date_found_from:
            conditions.append(FoundItem.date_found >= date_found_from)
        if date_found_to:
            conditions.append(FoundItem.date_found <= date_found_to)
        if secure_storage_only:
            conditions.append(FoundItem.secure_storage_flag == True)

        where_clause = and_(*conditions) if conditions else None

        # Get total count
        count_query = select(func.count(FoundItem.id))
        if where_clause is not None:
            count_query = count_query.where(where_clause)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = select(FoundItem)
        if where_clause is not None:
            query = query.where(where_clause)

        query = (
            query.options(
                selectinload(FoundItem.storage_location),
                selectinload(FoundItem.photos),
                selectinload(FoundItem.matches),
                selectinload(FoundItem.claim),
            )
            .order_by(FoundItem.date_found.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def move_to_storage(
        self,
        found_item_id: int,
        storage_location_id: int,
    ) -> Optional[FoundItem]:
        found_item = await self.get_found_item_by_id(found_item_id)
        if not found_item:
            return None

        found_item.storage_location_id = storage_location_id
        found_item.storage_moved_at = utc_now()

        await self.db.flush()
        await self.db.refresh(found_item)
        return found_item

    async def add_photo(
        self,
        found_item_id: int,
        photo_url: str,
        photo_key: str,
        uploaded_by: User,
        is_primary: bool = False,
        photo_notes: Optional[str] = None,
    ) -> Optional[FoundItemPhoto]:
        found_item = await self.get_found_item_by_id(found_item_id)
        if not found_item:
            return None

        # If marking as primary, unmark any existing primary photo
        if is_primary:
            result = await self.db.execute(
                select(FoundItemPhoto).where(
                    and_(
                        FoundItemPhoto.found_item_id == found_item_id,
                        FoundItemPhoto.is_primary == True,
                    )
                )
            )
            existing_primary = result.scalar_one_or_none()
            if existing_primary:
                existing_primary.is_primary = False

        photo = FoundItemPhoto(
            found_item_id=found_item_id,
            photo_url=photo_url,
            photo_key=photo_key,
            is_primary=is_primary,
            photo_notes=photo_notes,
            uploaded_by_id=uploaded_by.id,
        )

        self.db.add(photo)
        await self.db.flush()
        await self.db.refresh(photo)
        return photo

    async def get_checkin_items_for_retention(self) -> List[FoundItem]:
        now = utc_now()
        result = await self.db.execute(
            select(FoundItem)
            .where(
                and_(
                    FoundItem.status == FoundItemStatus.WAITING_CLAIM,
                    FoundItem.retention_end_date <= now,
                )
            )
            .options(selectinload(FoundItem.photos))
        )
        return result.scalars().all()

    async def dispose_found_item(
        self,
        found_item_id: int,
        disposal_method: DisposalMethod,
        disposal_notes: Optional[str] = None,
    ) -> Optional[FoundItem]:
        found_item = await self.get_found_item_by_id(found_item_id)
        if not found_item:
            return None

        found_item.disposal_method = disposal_method
        found_item.disposal_notes = disposal_notes
        found_item.disposed_at = utc_now()

        if found_item.status == FoundItemStatus.WAITING_CLAIM:
            found_item.status = FoundItemStatus.DISPOSED

        await self.db.flush()
        await self.db.refresh(found_item)
        return found_item

    async def auto_match_found_item(self, found_item_id: int) -> List[FoundItemMatch]:
        found_item = await self.get_found_item_by_id(found_item_id)
        if not found_item:
            return []

        # Find recent lost items that haven't been found yet
        result = await self.db.execute(
            select(LostItemRecord).where(
                and_(
                    LostItemRecord.status.in_(["reported", "confirmed"]),
                    LostItemRecord.reported_at >= utc_now() - timedelta(days=90),
                )
            )
        )
        lost_items = result.scalars().all()

        matches = []
        for lost_item in lost_items:
            match_score = self._calculate_match_score(found_item, lost_item)
            if match_score >= 25:  # Only create matches with 25%+ score
                confidence = self._score_to_confidence(match_score)
                matching_factors = self._get_matching_factors(found_item, lost_item)

                match = FoundItemMatch(
                    found_item_id=found_item_id,
                    lost_item_record_id=lost_item.id,
                    confidence_level=confidence,
                    match_score=Decimal(str(match_score)),
                    matching_factors=matching_factors,
                )

                self.db.add(match)
                matches.append(match)

        if matches:
            await self.db.flush()

        return matches

    def _calculate_match_score(self, found_item: FoundItem, lost_item: LostItemRecord) -> float:
        score = 0.0
        weight_sum = 0.0

        # Category match (40% weight)
        if lost_item.catalog_item:
            if found_item.category.lower() in lost_item.catalog_item.title.lower():
                score += 40
            weight_sum += 40

        # Color match if mentioned (20% weight)
        if found_item.color and lost_item.report_notes:
            if found_item.color.lower() in lost_item.report_notes.lower():
                score += 20
            weight_sum += 20

        # Size match if relevant (15% weight)
        if found_item.size and lost_item.report_notes:
            if found_item.size.lower() in lost_item.report_notes.lower():
                score += 15
            weight_sum += 15

        # Brand/label match if present (15% weight)
        if found_item.brand_or_label and lost_item.report_notes:
            if found_item.brand_or_label.lower() in lost_item.report_notes.lower():
                score += 15
            weight_sum += 15

        # Location proximity (10% weight) - if lost in similar area
        if found_item.location_found and lost_item.last_known_location:
            if found_item.location_found.lower() in lost_item.last_known_location.lower():
                score += 10
            weight_sum += 10

        return (score / weight_sum * 100) if weight_sum > 0 else 0

    def _score_to_confidence(self, score: float) -> MatchConfidenceLevel:
        if score >= 90:
            return MatchConfidenceLevel.VERY_HIGH
        elif score >= 75:
            return MatchConfidenceLevel.HIGH
        elif score >= 50:
            return MatchConfidenceLevel.MEDIUM
        else:
            return MatchConfidenceLevel.LOW

    def _get_matching_factors(
        self,
        found_item: FoundItem,
        lost_item: LostItemRecord,
    ) -> dict:
        factors = {}

        if lost_item.catalog_item:
            if found_item.category.lower() in lost_item.catalog_item.title.lower():
                factors["category"] = 100
            else:
                factors["category"] = 0

        if found_item.color and lost_item.report_notes:
            if found_item.color.lower() in lost_item.report_notes.lower():
                factors["color"] = 100
            else:
                factors["color"] = 0

        if found_item.size and lost_item.report_notes:
            if found_item.size.lower() in lost_item.report_notes.lower():
                factors["size"] = 100
            else:
                factors["size"] = 0

        return factors


class StorageLocationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_storage_location(
        self,
        location_name: str,
        location_code: str,
        description: Optional[str] = None,
        branch: Optional[str] = None,
        max_items: Optional[int] = None,
        is_secure_storage: bool = False,
        requires_verification: bool = False,
        access_restricted: bool = False,
    ) -> FoundItemStorageLocation:
        location = FoundItemStorageLocation(
            location_name=location_name,
            location_code=location_code,
            description=description,
            branch=branch,
            max_items=max_items,
            is_secure_storage=is_secure_storage,
            requires_verification=requires_verification,
            access_restricted=access_restricted,
        )

        self.db.add(location)
        await self.db.flush()
        await self.db.refresh(location)
        return location

    async def get_storage_location_by_id(
        self, location_id: int
    ) -> Optional[FoundItemStorageLocation]:
        result = await self.db.execute(
            select(FoundItemStorageLocation).where(FoundItemStorageLocation.id == location_id)
        )
        return result.scalar_one_or_none()

    async def list_storage_locations(
        self,
        is_secure_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FoundItemStorageLocation], int]:
        query = select(FoundItemStorageLocation).where(
            FoundItemStorageLocation.is_active == True
        )

        if is_secure_only:
            query = query.where(FoundItemStorageLocation.is_secure_storage == True)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(FoundItemStorageLocation.id)).where(
                FoundItemStorageLocation.is_active == True
            )
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(FoundItemStorageLocation.location_name).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def update_storage_location(
        self,
        location_id: int,
        **kwargs
    ) -> Optional[FoundItemStorageLocation]:
        location = await self.get_storage_location_by_id(location_id)
        if not location:
            return None

        allowed_fields = {
            "location_name",
            "description",
            "max_items",
            "is_secure_storage",
            "requires_verification",
            "access_restricted",
            "is_active",
        }

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(location, field, value)

        await self.db.flush()
        await self.db.refresh(location)
        return location


class ClaimVerificationService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def file_claim(
        self,
        found_item_id: int,
        patron: User,
        claim_statement: str,
        distinctive_features: Optional[dict] = None,
    ) -> Optional[FoundItemClaimVerification]:
        found_item = await self.db.execute(
            select(FoundItem).where(FoundItem.id == found_item_id)
        )
        found_item = found_item.scalar_one_or_none()
        if not found_item or found_item.status != FoundItemStatus.WAITING_CLAIM:
            return None

        claim = FoundItemClaimVerification(
            found_item_id=found_item_id,
            patron_id=patron.id,
            claim_statement=claim_statement,
            distinctive_features_mentioned=distinctive_features,
            status=ClaimVerificationStatus.PENDING,
        )

        self.db.add(claim)
        found_item.status = FoundItemStatus.CLAIMED
        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def verify_identity(
        self,
        claim_id: int,
        verification_method: str,
    ) -> Optional[FoundItemClaimVerification]:
        claim = await self._get_claim_by_id(claim_id)
        if not claim:
            return None

        claim.identity_verified = True
        claim.verification_method = verification_method
        claim.verification_timestamp = utc_now()

        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def confirm_item(
        self,
        claim_id: int,
        confirmation_notes: Optional[str] = None,
    ) -> Optional[FoundItemClaimVerification]:
        claim = await self._get_claim_by_id(claim_id)
        if not claim:
            return None

        claim.item_confirmed = True
        claim.confirmation_notes = confirmation_notes
        claim.status = ClaimVerificationStatus.UNDER_REVIEW

        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def review_claim(
        self,
        claim_id: int,
        approval_decision: bool,
        reviewer: User,
        rejection_reason: Optional[str] = None,
    ) -> Optional[FoundItemClaimVerification]:
        claim = await self._get_claim_by_id(claim_id)
        if not claim:
            return None

        claim.approval_decision = approval_decision
        claim.reviewed_by_id = reviewer.id
        claim.reviewed_at = utc_now()

        if approval_decision:
            claim.status = ClaimVerificationStatus.APPROVED
            claim.found_item.status = FoundItemStatus.VERIFIED
        else:
            claim.status = ClaimVerificationStatus.REJECTED
            claim.rejection_reason = rejection_reason
            claim.found_item.status = FoundItemStatus.WAITING_CLAIM

        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def mark_picked_up(
        self,
        claim_id: int,
        picked_up_by: User,
    ) -> Optional[FoundItemClaimVerification]:
        claim = await self._get_claim_by_id(claim_id)
        if not claim or claim.status != ClaimVerificationStatus.APPROVED:
            return None

        claim.picked_up_at = utc_now()
        claim.picked_up_by_id = picked_up_by.id
        claim.found_item.status = FoundItemStatus.VERIFIED

        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    async def _get_claim_by_id(self, claim_id: int) -> Optional[FoundItemClaimVerification]:
        result = await self.db.execute(
            select(FoundItemClaimVerification)
            .where(FoundItemClaimVerification.id == claim_id)
            .options(selectinload(FoundItemClaimVerification.found_item))
        )
        return result.scalar_one_or_none()
