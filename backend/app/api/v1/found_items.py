# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Found items management API endpoints.

Endpoints for:
- Logging and managing found items
- Managing storage locations
- Auto-matching to lost reports
- Filing and verifying claims
- Searching and filtering found items
"""

from app.core.logging import get_logger
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, status, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.file_validation import validate_file_type, validate_file_size

logger = get_logger(__name__)
from app.models.user import User, UserRole
from app.schemas.found_items import (
    AutoMatchFoundItemRequest,
    AutoMatchResult,
    ConfirmMatchRequest,
    DisposeFoundItemRequest,
    FileClaimRequest,
    FoundItemCreateRequest,
    FoundItemListResponse,
    FoundItemMatchResponse,
    FoundItemResponse,
    FoundItemSearchRequest,
    FoundItemUpdateRequest,
    MarkPickupRequest,
    ReviewClaimRequest,
    StorageLocationCreateRequest,
    StorageLocationListResponse,
    StorageLocationResponse,
    StorageLocationUpdateRequest,
    SuccessResponse,
    UpdateStorageLocationRequest,
    VerifyClaimRequest,
)
from app.services.found_item_service import (
    ClaimVerificationService,
    FoundItemService,
    StorageLocationService,
)
from app.services.storage_service import get_storage
from app.api.v1.auth import get_current_user
from app.api.v1.dependencies import require_staff, require_patron


router = APIRouter(prefix="/found-items", tags=["found-items"])


# ============================================================================
# Storage Location Endpoints
# ============================================================================


@router.post(
    "/storage-locations",
    response_model=StorageLocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
async def create_storage_location(
    request: StorageLocationCreateRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StorageLocationResponse:
    """Create a new storage location for found items."""
    service = StorageLocationService(db)

    # Check if location code already exists
    existing = await db.execute(
        "SELECT id FROM found_item_storage_locations WHERE location_code = %s"
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location code must be unique",
        )

    location = await service.create_storage_location(
        location_name=request.location_name,
        location_code=request.location_code,
        description=request.description,
        branch=request.branch,
        max_items=request.max_items,
        is_secure_storage=request.is_secure_storage,
        requires_verification=request.requires_verification,
        access_restricted=request.access_restricted,
    )

    await db.commit()
    # Refresh to reload server-default columns (e.g. current_item_count) so
    # response serialization doesn't trigger sync lazy-load outside the async
    # greenlet (matches PR #1233 pattern in blog.py).
    await db.refresh(location)
    return StorageLocationResponse.model_validate(location)


@router.get(
    "/storage-locations",
    response_model=StorageLocationListResponse,
    dependencies=[Depends(require_staff)],
)
async def list_storage_locations(
    is_secure_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StorageLocationListResponse:
    """List all storage locations."""
    service = StorageLocationService(db)
    locations, total = await service.list_storage_locations(
        is_secure_only=is_secure_only,
        limit=limit,
        offset=offset,
    )

    return StorageLocationListResponse(
        items=[StorageLocationResponse.model_validate(loc) for loc in locations],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/storage-locations/{location_id}",
    response_model=StorageLocationResponse,
    dependencies=[Depends(require_staff)],
)
async def update_storage_location(
    location_id: int,
    request: StorageLocationUpdateRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> StorageLocationResponse:
    """Update a storage location."""
    service = StorageLocationService(db)

    location = await service.update_storage_location(
        location_id,
        **request.model_dump(exclude_unset=True),
    )

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage location not found",
        )

    await db.commit()
    # Refresh to reload server-side state before serialization (matches PR
    # #1233 pattern in blog.py) so we don't trigger sync lazy-load on
    # expired attrs outside the async greenlet.
    await db.refresh(location)
    return StorageLocationResponse.model_validate(location)


# ============================================================================
# Found Item Endpoints
# ============================================================================


@router.post(
    "",
    response_model=FoundItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
async def log_found_item(
    request: FoundItemCreateRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> FoundItemResponse:
    """Log a new found item."""
    service = FoundItemService(db)

    found_item = await service.create_found_item(
        description=request.description,
        category=request.category,
        location_found=request.location_found,
        date_found=request.date_found,
        found_by=user,
        logged_by=user,
        color=request.color,
        brand_or_label=request.brand_or_label,
        size=request.size,
        condition=request.condition,
        additional_details=request.additional_details,
        location_details=request.location_details,
        storage_location_id=request.storage_location_id,
        secure_storage_flag=request.secure_storage_flag,
        estimated_value=request.estimated_value,
        retention_period_days=request.retention_period_days,
        staff_notes=request.staff_notes,
    )

    await db.commit()
    # Re-fetch with relationships eagerly loaded so response serialization
    # doesn't trigger sync lazy-load outside the async greenlet (matches PR
    # #1233 pattern in blog.py; service.get_found_item_by_id selectinloads
    # photos, matches, claim, storage_location).
    found_item = await service.get_found_item_by_id(found_item.id)
    return FoundItemResponse.model_validate(found_item)


@router.get(
    "/{found_item_id}",
    response_model=FoundItemResponse,
)
async def get_found_item(
    found_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FoundItemResponse:
    """Get a found item by ID."""
    service = FoundItemService(db)
    found_item = await service.get_found_item_by_id(found_item_id)

    if not found_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    return FoundItemResponse.model_validate(found_item)


@router.put(
    "/{found_item_id}",
    response_model=FoundItemResponse,
    dependencies=[Depends(require_staff)],
)
async def update_found_item(
    found_item_id: int,
    request: FoundItemUpdateRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> FoundItemResponse:
    """Update a found item."""
    service = FoundItemService(db)

    found_item = await service.update_found_item(
        found_item_id,
        **request.model_dump(exclude_unset=True),
    )

    if not found_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    await db.commit()
    # Re-fetch with relationships eagerly loaded so response serialization
    # doesn't trigger sync lazy-load outside the async greenlet (PR #1233).
    found_item = await service.get_found_item_by_id(found_item_id)
    return FoundItemResponse.model_validate(found_item)


@router.get(
    "",
    response_model=FoundItemListResponse,
)
async def list_found_items(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location_found: Optional[str] = Query(None),
    secure_storage_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FoundItemListResponse:
    """List found items with optional filtering."""
    service = FoundItemService(db)

    items, total = await service.list_found_items(
        status=status,
        category=category,
        location_found=location_found,
        secure_storage_only=secure_storage_only,
        limit=limit,
        offset=offset,
    )

    return FoundItemListResponse(
        items=[FoundItemResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/search",
    response_model=FoundItemListResponse,
)
async def search_found_items(
    request: FoundItemSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FoundItemListResponse:
    """Search found items with advanced filtering."""
    service = FoundItemService(db)

    items, total = await service.search_found_items(
        search_query=request.search_query,
        category=request.category,
        status=request.status,
        location_found=request.location_found,
        date_found_from=request.date_found_from,
        date_found_to=request.date_found_to,
        secure_storage_only=request.secure_storage_only,
        limit=request.limit,
        offset=request.offset,
    )

    return FoundItemListResponse(
        items=[FoundItemResponse.model_validate(item) for item in items],
        total=total,
        limit=request.limit,
        offset=request.offset,
    )


@router.post(
    "/{found_item_id}/move-storage",
    response_model=FoundItemResponse,
    dependencies=[Depends(require_staff)],
)
async def move_to_storage(
    found_item_id: int,
    request: UpdateStorageLocationRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> FoundItemResponse:
    """Move a found item to a different storage location."""
    service = FoundItemService(db)

    found_item = await service.move_to_storage(found_item_id, request.storage_location_id)

    if not found_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    await db.commit()
    # Re-fetch with relationships eagerly loaded so response serialization
    # doesn't trigger sync lazy-load outside the async greenlet (PR #1233).
    found_item = await service.get_found_item_by_id(found_item_id)
    return FoundItemResponse.model_validate(found_item)


@router.post(
    "/{found_item_id}/photos",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
async def upload_photo(
    found_item_id: int,
    file: UploadFile = File(...),
    photo_notes: Optional[str] = Query(None),
    is_primary: bool = Query(False),
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a photo for a found item."""
    service = FoundItemService(db)

    # Read file content
    content = await file.read()

    # Magic-byte validation: reject files whose content doesn't match an allowed image type
    content_start = content[:16]
    detected_mime = validate_file_type(content_start, file.filename or "photo.jpg")
    if detected_mime is None or not detected_mime.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image. Accepted types: PNG, JPEG, GIF, WebP",
        )

    # Validate file size using centralized limits
    if not validate_file_size(len(content), 'image'):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)",
        )

    logger.info(
        "Upload audit: user_id=%s filename=%s size=%s mime=%s found_item_id=%s timestamp=%s",
        user.id,
        file.filename,
        len(content),
        detected_mime,
        found_item_id,
        datetime.now(timezone.utc).isoformat(),
    )

    # Upload to storage
    storage = get_storage()
    photo_url = await storage.upload(
        file_data=BytesIO(content),
        key=f"found-items/{found_item_id}/{file.filename}",
        content_type=file.content_type,
    )

    # Add photo to database
    photo = await service.add_photo(
        found_item_id=found_item_id,
        photo_url=photo_url,
        photo_key=f"found-items/{found_item_id}/{file.filename}",
        uploaded_by=user,
        is_primary=is_primary,
        photo_notes=photo_notes,
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    await db.commit()
    return {
        "success": True,
        "message": "Photo uploaded successfully",
        "photo_url": photo_url,
    }


# ============================================================================
# Auto-Matching Endpoints
# ============================================================================


@router.post(
    "/{found_item_id}/auto-match",
    response_model=AutoMatchResult,
    dependencies=[Depends(require_staff)],
)
async def auto_match_item(
    found_item_id: int,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> AutoMatchResult:
    """Trigger auto-matching for a found item."""
    service = FoundItemService(db)

    found_item = await service.get_found_item_by_id(found_item_id)
    if not found_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    matches = await service.auto_match_found_item(found_item_id)
    await db.commit()

    best_match = None
    if matches:
        best_match = max(matches, key=lambda m: float(m.match_score))

    return AutoMatchResult(
        found_item_id=found_item_id,
        matches=[
            FoundItemMatchResponse.model_validate(match)  # type: ignore
            for match in matches
        ],
        best_match=(
            FoundItemMatchResponse.model_validate(best_match)  # type: ignore
            if best_match
            else None
        ),
        total_matches=len(matches),
    )


@router.put(
    "/matches/{match_id}",
    response_model=dict,
    dependencies=[Depends(require_staff)],
)
async def confirm_match(
    match_id: int,
    request: ConfirmMatchRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm or reject a match between found and lost items."""
    from sqlalchemy import select
    from app.models.found_items import FoundItemMatch

    result = await db.execute(
        select(FoundItemMatch).where(FoundItemMatch.id == match_id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    match.is_confirmed = request.is_confirmed
    match.confirmation_notes = request.confirmation_notes
    match.confirmed_by_id = user.id

    await db.commit()

    return {
        "success": True,
        "message": "Match confirmed" if request.is_confirmed else "Match rejected",
    }


# ============================================================================
# Claim Verification Endpoints
# ============================================================================


@router.post(
    "/{found_item_id}/claim",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_patron)],
)
async def file_claim(
    found_item_id: int,
    request: FileClaimRequest,
    user: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """File a claim for a found item."""
    service = ClaimVerificationService(db)

    claim = await service.file_claim(
        found_item_id=found_item_id,
        patron=user,
        claim_statement=request.claim_statement,
        distinctive_features=request.distinctive_features,
    )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot file claim for this item",
        )

    await db.commit()
    return {
        "success": True,
        "message": "Claim filed successfully",
        "claim_id": claim.id,
    }


@router.post(
    "/claims/{claim_id}/verify-identity",
    response_model=dict,
    dependencies=[Depends(require_staff)],
)
async def verify_identity(
    claim_id: int,
    request: VerifyClaimRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify patron identity for a claim."""
    service = ClaimVerificationService(db)

    claim = await service.verify_identity(
        claim_id=claim_id,
        verification_method=request.verification_method,
    )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    if request.item_confirmed:
        await service.confirm_item(
            claim_id=claim_id,
            confirmation_notes=request.confirmation_notes,
        )

    await db.commit()

    return {
        "success": True,
        "message": "Identity verified",
    }


@router.post(
    "/claims/{claim_id}/review",
    response_model=dict,
    dependencies=[Depends(require_staff)],
)
async def review_claim(
    claim_id: int,
    request: ReviewClaimRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Review and approve/reject a claim."""
    service = ClaimVerificationService(db)

    claim = await service.review_claim(
        claim_id=claim_id,
        approval_decision=request.approval_decision,
        reviewer=user,
        rejection_reason=request.rejection_reason,
    )

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    await db.commit()

    return {
        "success": True,
        "message": "Claim approved" if request.approval_decision else "Claim rejected",
    }


@router.post(
    "/claims/{claim_id}/mark-pickup",
    response_model=dict,
    dependencies=[Depends(require_staff)],
)
async def mark_pickup(
    claim_id: int,
    request: MarkPickupRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a verified claim as picked up."""
    from sqlalchemy import select
    from app.models.user import User as UserModel

    service = ClaimVerificationService(db)

    # Get the user who's marking pickup
    result = await db.execute(
        select(UserModel).where(UserModel.id == request.picked_up_by_id)
    )
    picked_up_by = result.scalar_one_or_none()

    if not picked_up_by:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    claim = await service.mark_picked_up(claim_id=claim_id, picked_up_by=picked_up_by)

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark claim as picked up",
        )

    await db.commit()

    return {
        "success": True,
        "message": "Item marked as picked up",
    }


# ============================================================================
# Retention and Disposal Endpoints
# ============================================================================


@router.post(
    "/{found_item_id}/dispose",
    response_model=FoundItemResponse,
    dependencies=[Depends(require_staff)],
)
async def dispose_found_item(
    found_item_id: int,
    request: DisposeFoundItemRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> FoundItemResponse:
    """Mark a found item as disposed."""
    service = FoundItemService(db)

    found_item = await service.dispose_found_item(
        found_item_id=found_item_id,
        disposal_method=request.disposal_method,
        disposal_notes=request.disposal_notes,
    )

    if not found_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found item not found",
        )

    await db.commit()
    # Re-fetch with relationships eagerly loaded so response serialization
    # doesn't trigger sync lazy-load outside the async greenlet (PR #1233).
    found_item = await service.get_found_item_by_id(found_item_id)
    return FoundItemResponse.model_validate(found_item)


@router.get(
    "/checkin/retention",
    response_model=FoundItemListResponse,
    dependencies=[Depends(require_staff)],
)
async def get_retention_checkin_items(
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> FoundItemListResponse:
    """Get found items approaching or past retention end date."""
    service = FoundItemService(db)

    items = await service.get_checkin_items_for_retention()

    return FoundItemListResponse(
        items=[FoundItemResponse.model_validate(item) for item in items],
        total=len(items),
        limit=len(items),
        offset=0,
    )
