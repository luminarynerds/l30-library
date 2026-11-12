# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Segmentation API Endpoints

This module provides endpoints for:
- Tag management (CRUD, assign/remove from patrons)
- Patron group management (CRUD, member management)
- Group operations (statistics, messaging, export)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.circulation import Checkout, CheckoutStatus
from ...models.fine import Fine, FineStatus
from ...models.patron_segmentation import (
    SYSTEM_TAGS, PatronGroup, PatronGroupMember, PatronTag, Tag, TagColor
)
from ...models.user import User, UserRole
from .dependencies import is_admin, require_admin, require_staff
from app.core.datetime_utils import utc_now

router = APIRouter(prefix="/staff", tags=["patron-segmentation"])


# =============================================================================
# Pydantic Schemas - Tags
# =============================================================================


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default=TagColor.BLUE.value)
    description: Optional[str] = Field(None, max_length=255)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    description: Optional[str]
    is_custom: bool
    is_active: bool
    patron_count: int = 0

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    tags: list[TagResponse]
    total: int


class PatronTagAssignment(BaseModel):
    patron_id: int
    tag_id: int
    notes: Optional[str] = Field(None, max_length=255)


class BulkTagAssignment(BaseModel):
    patron_ids: list[int]
    tag_id: int
    notes: Optional[str] = Field(None, max_length=255)


class PatronTagResponse(BaseModel):
    id: int
    tag_id: int
    tag_name: str
    tag_color: str
    assigned_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class BulkTagAssignmentResponse(BaseModel):
    assigned: int = Field(..., description="Number of patrons successfully assigned the tag")
    skipped: int = Field(..., description="Number of patrons skipped (not found or already tagged)")
    total_requested: int = Field(..., description="Total number of patron IDs in the request")


# =============================================================================
# Pydantic Schemas - Groups
# =============================================================================


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    allow_self_join: bool = False
    max_members: Optional[int] = Field(None, ge=1)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    allow_self_join: Optional[bool] = None
    max_members: Optional[int] = Field(None, ge=1)


class GroupMemberAdd(BaseModel):
    patron_id: int
    role: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=255)


class BulkGroupMemberAdd(BaseModel):
    patron_ids: list[int]
    role: Optional[str] = Field(None, max_length=50)


class GroupMemberResponse(BaseModel):
    id: int
    patron_id: int
    patron_name: str
    patron_email: str
    joined_at: datetime
    role: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    allow_self_join: bool
    max_members: Optional[int]
    member_count: int = 0
    created_at: Optional[datetime] = None
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class GroupListResponse(BaseModel):
    groups: list[GroupResponse]
    total: int


class GroupDetailResponse(GroupResponse):
    members: list[GroupMemberResponse] = []


class GroupStatsResponse(BaseModel):
    group_id: int
    group_name: str
    member_count: int
    total_checkouts: int
    active_checkouts: int
    total_fines: Decimal
    unpaid_fines: Decimal


class GroupMessageRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)


class GroupExportResponse(BaseModel):
    group_name: str
    exported_at: datetime
    member_count: int
    members: list[dict]


class BulkMemberAddResponse(BaseModel):
    added: int = Field(..., description="Number of patrons successfully added to the group")
    skipped: int = Field(..., description="Number of patrons skipped (not found, already member, or capacity reached)")
    total_requested: int = Field(..., description="Total number of patron IDs in the request")


class GroupMessageResponse(BaseModel):
    status: str = Field(..., description="Status of the message operation")
    group_id: int = Field(..., description="ID of the group")
    group_name: str = Field(..., description="Name of the group")
    recipient_count: int = Field(..., description="Number of recipients the message will be sent to")
    subject: str = Field(..., description="Subject of the message")
    message_preview: str = Field(..., description="Preview of the message content")


# =============================================================================
# Tag Endpoints
# =============================================================================


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    search: Optional[str] = Query(None, description="Search by tag name"),
    include_inactive: bool = Query(False, description="Include inactive tags"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all tags with patron counts."""
    offset = (page - 1) * limit
    query = select(Tag)
    count_query = select(func.count(Tag.id))

    if not include_inactive:
        query = query.where(Tag.is_active == True)
        count_query = count_query.where(Tag.is_active == True)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Tag.name.ilike(f"%{safe_search}%"))
        count_query = count_query.where(Tag.name.ilike(f"%{safe_search}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get tags with patron counts in a single query via LEFT JOIN + GROUP BY
    tags_with_counts_query = (
        select(Tag, func.count(PatronTag.id).label("patron_count"))
        .outerjoin(PatronTag, PatronTag.tag_id == Tag.id)
    )
    if not include_inactive:
        tags_with_counts_query = tags_with_counts_query.where(Tag.is_active == True)
    if search:
        safe_search_q = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        tags_with_counts_query = tags_with_counts_query.where(Tag.name.ilike(f"%{safe_search_q}%"))
    tags_with_counts_query = tags_with_counts_query.group_by(Tag.id).order_by(Tag.name).offset(offset).limit(limit)

    result = await db.execute(tags_with_counts_query)
    rows = result.all()

    tag_responses = []
    for tag, patron_count in rows:
        tag_responses.append(TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            is_custom=tag.is_custom,
            is_active=tag.is_active,
            patron_count=patron_count,
        ))

    return TagListResponse(tags=tag_responses, total=total)


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_tag(
    request: Request,
    tag_data: TagCreate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom tag (admin only)."""
    # Check for duplicate name
    existing = await db.execute(select(Tag).where(Tag.name.ilike(tag_data.name)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tag with this name already exists",
        )

    # Validate color
    valid_colors = [c.value for c in TagColor]
    if tag_data.color not in valid_colors:
        tag_data.color = TagColor.BLUE.value

    tag = Tag(
        name=tag_data.name,
        color=tag_data.color,
        description=tag_data.description,
        is_custom=True,
        created_by_id=staff_user.id,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        description=tag.description,
        is_custom=tag.is_custom,
        is_active=tag.is_active,
        created_at=tag.created_at,
        patron_count=0,
    )


@router.put("/tags/{tag_id}", response_model=TagResponse)
@limiter.limit("30/minute")
async def update_tag(
    request: Request,
    tag_id: int,
    tag_data: TagUpdate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a tag (admin only)."""
    tag = await get_or_404(db, Tag, tag_id, "Tag not found")

    # Check for duplicate name if changing
    if tag_data.name and tag_data.name != tag.name:
        existing = await db.execute(
            select(Tag).where(Tag.name.ilike(tag_data.name), Tag.id != tag_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A tag with this name already exists",
            )

    update_data = tag_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)

    await db.commit()
    await db.refresh(tag)

    # Get patron count
    count_result = await db.execute(
        select(func.count(PatronTag.id)).where(PatronTag.tag_id == tag.id)
    )
    patron_count = count_result.scalar() or 0

    return TagResponse(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        description=tag.description,
        is_custom=tag.is_custom,
        is_active=tag.is_active,
        created_at=tag.created_at,
        patron_count=patron_count,
    )


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_tag(
    request: Request,
    tag_id: int,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom tag (admin only). System tags cannot be deleted."""
    tag = await get_or_404(db, Tag, tag_id, "Tag not found")

    if not tag.is_custom:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System tags cannot be deleted",
        )

    await db.delete(tag)
    await db.commit()


@router.post("/tags/seed", response_model=TagListResponse)
async def seed_system_tags(
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed system tags if they don't exist (admin only)."""
    created_tags = []

    for tag_data in SYSTEM_TAGS:
        existing = await db.execute(select(Tag).where(Tag.name == tag_data["name"]))
        if not existing.scalar_one_or_none():
            tag = Tag(**tag_data)
            db.add(tag)
            created_tags.append(tag)

    await db.commit()

    # Refresh and return all system tags
    result = await db.execute(select(Tag).where(Tag.is_custom == False).order_by(Tag.name))
    tags = result.scalars().all()

    tag_responses = []
    for tag in tags:
        count_result = await db.execute(
            select(func.count(PatronTag.id)).where(PatronTag.tag_id == tag.id)
        )
        patron_count = count_result.scalar() or 0
        tag_responses.append(TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            is_custom=tag.is_custom,
            is_active=tag.is_active,
            patron_count=patron_count,
        ))

    return TagListResponse(tags=tag_responses, total=len(tag_responses))


# =============================================================================
# Patron Tag Assignment Endpoints
# =============================================================================


@router.get("/patrons/{patron_id}/tags", response_model=list[PatronTagResponse])
async def get_patron_tags(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all tags assigned to a patron."""
    # Verify patron exists
    patron_result = await db.execute(select(User).where(User.id == patron_id))
    if not patron_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patron not found")

    result = await db.execute(
        select(PatronTag, Tag)
        .join(Tag, PatronTag.tag_id == Tag.id)
        .where(PatronTag.patron_id == patron_id)
        .order_by(Tag.name)
    )

    return [
        PatronTagResponse(
            id=pt.id,
            tag_id=tag.id,
            tag_name=tag.name,
            tag_color=tag.color,
            assigned_at=pt.assigned_at,
            notes=pt.notes,
        )
        for pt, tag in result.all()
    ]


@router.post("/patrons/{patron_id}/tags", response_model=PatronTagResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def assign_tag_to_patron(
    request: Request,
    patron_id: int,
    assignment: PatronTagAssignment,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign a tag to a patron."""
    # Verify patron exists
    patron_result = await db.execute(select(User).where(User.id == patron_id))
    if not patron_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Patron not found")

    # Verify tag exists and is active
    tag_result = await db.execute(select(Tag).where(Tag.id == assignment.tag_id, Tag.is_active == True))
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found or inactive")

    # Check if already assigned
    existing = await db.execute(
        select(PatronTag).where(
            PatronTag.patron_id == patron_id,
            PatronTag.tag_id == assignment.tag_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already assigned to this patron",
        )

    patron_tag = PatronTag(
        patron_id=patron_id,
        tag_id=assignment.tag_id,
        assigned_by_id=staff_user.id,
        notes=assignment.notes,
    )
    db.add(patron_tag)
    await db.commit()
    await db.refresh(patron_tag)

    return PatronTagResponse(
        id=patron_tag.id,
        tag_id=tag.id,
        tag_name=tag.name,
        tag_color=tag.color,
        assigned_at=patron_tag.assigned_at,
        notes=patron_tag.notes,
    )


@router.delete("/patrons/{patron_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.get("/patrons/{patron_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def remove_tag_from_patron(
    request: Request,
    patron_id: int,
    tag_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Remove a tag from a patron."""
    result = await db.execute(
        select(PatronTag).where(
            PatronTag.patron_id == patron_id,
            PatronTag.tag_id == tag_id,
        )
    )
    patron_tag = result.scalar_one_or_none()

    if not patron_tag:
        raise HTTPException(status_code=404, detail="Tag assignment not found")

    await db.delete(patron_tag)
    await db.commit()


@router.post("/tags/bulk-assign", response_model=BulkTagAssignmentResponse)
@router.get("/tags/bulk-assign", response_model=BulkTagAssignmentResponse)
@limiter.limit("10/minute")
async def bulk_assign_tag(
    request: Request,
    assignment: BulkTagAssignment,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Assign a tag to multiple patrons at once."""
    # Verify tag exists and is active
    tag_result = await db.execute(select(Tag).where(Tag.id == assignment.tag_id, Tag.is_active == True))
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found or inactive")

    # Bulk load: find which patron_ids actually exist
    valid_patrons_result = await db.execute(
        select(User.id).where(User.id.in_(assignment.patron_ids))
    )
    valid_patron_ids = {row[0] for row in valid_patrons_result.all()}

    # Bulk load: find which patron_ids already have this tag
    existing_result = await db.execute(
        select(PatronTag.patron_id).where(
            PatronTag.patron_id.in_(assignment.patron_ids),
            PatronTag.tag_id == assignment.tag_id,
        )
    )
    already_assigned_ids = {row[0] for row in existing_result.all()}

    # Compute set of patron_ids to assign (exist AND not already assigned)
    to_assign_ids = valid_patron_ids - already_assigned_ids

    # Bulk insert new assignments
    for patron_id in to_assign_ids:
        db.add(PatronTag(
            patron_id=patron_id,
            tag_id=assignment.tag_id,
            assigned_by_id=staff_user.id,
            notes=assignment.notes,
        ))

    assigned_count = len(to_assign_ids)
    skipped_count = len(assignment.patron_ids) - assigned_count

    await db.commit()

    return BulkTagAssignmentResponse(
        assigned=assigned_count,
        skipped=skipped_count,
        total_requested=len(assignment.patron_ids),
    )


# =============================================================================
# Group Endpoints
# =============================================================================


@router.get("/patron-groups", response_model=GroupListResponse)
async def list_groups(
    search: Optional[str] = Query(None, description="Search by group name"),
    include_inactive: bool = Query(False, description="Include inactive groups"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all patron groups with member counts."""
    query = select(PatronGroup)
    count_query = select(func.count(PatronGroup.id))

    if not include_inactive:
        query = query.where(PatronGroup.is_active == True)
        count_query = count_query.where(PatronGroup.is_active == True)

    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(PatronGroup.name.ilike(f"%{safe_search}%"))
        count_query = count_query.where(PatronGroup.name.ilike(f"%{safe_search}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get groups with member counts in a single query via LEFT JOIN + GROUP BY
    groups_with_counts_query = (
        select(PatronGroup, func.count(PatronGroupMember.id).label("member_count"))
        .outerjoin(PatronGroupMember, PatronGroupMember.group_id == PatronGroup.id)
    )
    if not include_inactive:
        groups_with_counts_query = groups_with_counts_query.where(PatronGroup.is_active == True)
    if search:
        safe_search_g = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        groups_with_counts_query = groups_with_counts_query.where(PatronGroup.name.ilike(f"%{safe_search_g}%"))
    groups_with_counts_query = (
        groups_with_counts_query
        .options(selectinload(PatronGroup.created_by))
        .group_by(PatronGroup.id)
        .order_by(PatronGroup.name)
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(groups_with_counts_query)
    rows = result.all()

    group_responses = []
    for group, member_count in rows:
        group_responses.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            is_active=group.is_active,
            allow_self_join=group.allow_self_join,
            max_members=group.max_members,
            member_count=member_count,
            created_at=getattr(group, "created_at", None),
            created_by_name=f"{group.created_by.first_name} {group.created_by.last_name}" if group.created_by else None,
        ))

    return GroupListResponse(groups=group_responses, total=total)


@router.post("/patron-groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_group(
    request: Request,
    group_data: GroupCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new patron group."""
    group = PatronGroup(
        name=group_data.name,
        description=group_data.description,
        allow_self_join=group_data.allow_self_join,
        max_members=group_data.max_members,
        created_by_id=staff_user.id,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        allow_self_join=group.allow_self_join,
        max_members=group.max_members,
        member_count=0,
        created_at=getattr(group, "created_at", None),
        created_by_name=f"{staff_user.first_name} {staff_user.last_name}",
    )


@router.get("/patron-groups/{group_id}", response_model=GroupDetailResponse)
async def get_group_detail(
    group_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get group details including all members."""
    result = await db.execute(
        select(PatronGroup)
        .options(selectinload(PatronGroup.created_by))
        .where(PatronGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get members with patron info
    members_result = await db.execute(
        select(PatronGroupMember, User)
        .join(User, PatronGroupMember.patron_id == User.id)
        .where(PatronGroupMember.group_id == group_id)
        .order_by(User.last_name, User.first_name)
    )

    members = [
        GroupMemberResponse(
            id=member.id,
            patron_id=patron.id,
            patron_name=f"{patron.first_name} {patron.last_name}",
            patron_email=patron.email,
            joined_at=member.joined_at,
            role=member.role,
            notes=member.notes,
        )
        for member, patron in members_result.all()
    ]

    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        allow_self_join=group.allow_self_join,
        max_members=group.max_members,
        member_count=len(members),
        created_at=getattr(group, "created_at", None),
        created_by_name=f"{group.created_by.first_name} {group.created_by.last_name}" if group.created_by else None,
        members=members,
    )


@router.put("/patron-groups/{group_id}", response_model=GroupResponse)
@limiter.limit("30/minute")
async def update_group(
    request: Request,
    group_id: int,
    group_data: GroupUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a patron group."""
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)

    # Get member count
    count_result = await db.execute(
        select(func.count(PatronGroupMember.id)).where(PatronGroupMember.group_id == group.id)
    )
    member_count = count_result.scalar() or 0

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        allow_self_join=group.allow_self_join,
        max_members=group.max_members,
        member_count=member_count,
        created_at=getattr(group, "created_at", None),
        created_by_name=None,
    )


@router.delete("/patron-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_group(
    request: Request,
    group_id: int,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a patron group (admin only)."""
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    await db.delete(group)
    await db.commit()


# =============================================================================
# Group Member Endpoints
# =============================================================================


@router.post("/patron-groups/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
@router.get("/patron-groups/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def add_group_member(
    request: Request,
    group_id: int,
    member_data: GroupMemberAdd,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add a patron to a group."""
    # Verify group exists and is active
    group_result = await db.execute(select(PatronGroup).where(PatronGroup.id == group_id, PatronGroup.is_active == True))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or inactive")

    # Check max members
    if group.max_members:
        count_result = await db.execute(
            select(func.count(PatronGroupMember.id)).where(PatronGroupMember.group_id == group_id)
        )
        current_count = count_result.scalar() or 0
        if current_count >= group.max_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group has reached maximum capacity of {group.max_members} members",
            )

    # Verify patron exists
    patron = await get_or_404(db, User, member_data.patron_id, "Patron not found")

    # Check if already a member
    existing = await db.execute(
        select(PatronGroupMember).where(
            PatronGroupMember.group_id == group_id,
            PatronGroupMember.patron_id == member_data.patron_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron is already a member of this group",
        )

    member = PatronGroupMember(
        group_id=group_id,
        patron_id=member_data.patron_id,
        added_by_id=staff_user.id,
        role=member_data.role,
        notes=member_data.notes,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return GroupMemberResponse(
        id=member.id,
        patron_id=patron.id,
        patron_name=f"{patron.first_name} {patron.last_name}",
        patron_email=patron.email,
        joined_at=member.joined_at,
        role=member.role,
        notes=member.notes,
    )


@router.post("/patron-groups/{group_id}/members/bulk", response_model=BulkMemberAddResponse)
@router.get("/patron-groups/{group_id}/members/bulk", response_model=BulkMemberAddResponse)
@limiter.limit("10/minute")
async def bulk_add_group_members(
    request: Request,
    group_id: int,
    member_data: BulkGroupMemberAdd,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add multiple patrons to a group at once."""
    # Verify group exists and is active
    group_result = await db.execute(select(PatronGroup).where(PatronGroup.id == group_id, PatronGroup.is_active == True))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or inactive")

    # Check current count for max members
    current_count = 0
    if group.max_members:
        count_result = await db.execute(
            select(func.count(PatronGroupMember.id)).where(PatronGroupMember.group_id == group_id)
        )
        current_count = count_result.scalar() or 0

    # Bulk load: find which patron_ids actually exist
    valid_patrons_result = await db.execute(
        select(User.id).where(User.id.in_(member_data.patron_ids))
    )
    valid_patron_ids = {row[0] for row in valid_patrons_result.all()}

    # Bulk load: find which patron_ids are already members of this group
    existing_members_result = await db.execute(
        select(PatronGroupMember.patron_id).where(
            PatronGroupMember.group_id == group_id,
            PatronGroupMember.patron_id.in_(member_data.patron_ids),
        )
    )
    already_member_ids = {row[0] for row in existing_members_result.all()}

    # Compute set of patron_ids to add (exist AND not already member)
    to_add_ids = valid_patron_ids - already_member_ids

    added_count = 0
    skipped_count = 0

    for patron_id in to_add_ids:
        # Check max members capacity
        if group.max_members and (current_count + added_count) >= group.max_members:
            skipped_count += len(to_add_ids) - added_count
            break

        db.add(PatronGroupMember(
            group_id=group_id,
            patron_id=patron_id,
            added_by_id=staff_user.id,
            role=member_data.role,
        ))
        added_count += 1

    # Count patrons that were invalid or already members
    skipped_count += len(member_data.patron_ids) - len(to_add_ids)

    await db.commit()

    return BulkMemberAddResponse(
        added=added_count,
        skipped=skipped_count,
        total_requested=len(member_data.patron_ids),
    )


@router.delete("/patron-groups/{group_id}/members/{patron_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.get("/patron-groups/{group_id}/members/{patron_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def remove_group_member(
    request: Request,
    group_id: int,
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Remove a patron from a group."""
    result = await db.execute(
        select(PatronGroupMember).where(
            PatronGroupMember.group_id == group_id,
            PatronGroupMember.patron_id == patron_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found in group")

    await db.delete(member)
    await db.commit()


# =============================================================================
# Group Features Endpoints
# =============================================================================


@router.get("/patron-groups/{group_id}/stats", response_model=GroupStatsResponse)
async def get_group_stats(
    group_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a patron group."""
    # Verify group exists
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    # Get member IDs
    members_result = await db.execute(
        select(PatronGroupMember.patron_id).where(PatronGroupMember.group_id == group_id)
    )
    member_ids = [row[0] for row in members_result.all()]

    if not member_ids:
        return GroupStatsResponse(
            group_id=group.id,
            group_name=group.name,
            member_count=0,
            total_checkouts=0,
            active_checkouts=0,
            total_fines=Decimal("0.00"),
            unpaid_fines=Decimal("0.00"),
        )

    # Get checkout stats
    total_checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.user_id.in_(member_ids))
    )
    total_checkouts = total_checkouts_result.scalar() or 0

    active_checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.user_id.in_(member_ids),
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    active_checkouts = active_checkouts_result.scalar() or 0

    # Get fines stats
    total_fines_result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount), 0)).where(Fine.user_id.in_(member_ids))
    )
    total_fines = Decimal(str(total_fines_result.scalar() or 0))

    unpaid_fines_result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
            Fine.user_id.in_(member_ids),
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
        )
    )
    unpaid_fines = Decimal(str(unpaid_fines_result.scalar() or 0))

    return GroupStatsResponse(
        group_id=group.id,
        group_name=group.name,
        member_count=len(member_ids),
        total_checkouts=total_checkouts,
        active_checkouts=active_checkouts,
        total_fines=total_fines,
        unpaid_fines=unpaid_fines,
    )


@router.post("/patron-groups/{group_id}/message", response_model=GroupMessageResponse)
@router.get("/patron-groups/{group_id}/message", response_model=GroupMessageResponse)
@limiter.limit("5/minute")
async def send_group_message(
    request: Request,
    group_id: int,
    message_data: GroupMessageRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to all members of a group (placeholder for notification system)."""
    # Verify group exists
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    # Get member emails
    members_result = await db.execute(
        select(User.email)
        .join(PatronGroupMember, PatronGroupMember.patron_id == User.id)
        .where(PatronGroupMember.group_id == group_id)
    )
    emails = [row[0] for row in members_result.all()]

    # In a real implementation, this would queue notifications
    # For now, return a summary of what would be sent
    return GroupMessageResponse(
        status="queued",
        group_id=group_id,
        group_name=group.name,
        recipient_count=len(emails),
        subject=message_data.subject,
        message_preview=message_data.message[:100] + "..." if len(message_data.message) > 100 else message_data.message,
    )


@router.get("/patron-groups/{group_id}/export", response_model=GroupExportResponse)
async def export_group_members(
    group_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Export group member list with patron details."""
    # Verify group exists
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    # Get members with full patron info
    members_result = await db.execute(
        select(PatronGroupMember, User)
        .join(User, PatronGroupMember.patron_id == User.id)
        .where(PatronGroupMember.group_id == group_id)
        .order_by(User.last_name, User.first_name)
    )

    members = []
    for member, patron in members_result.all():
        members.append({
            "id": patron.id,
            "first_name": patron.first_name,
            "last_name": patron.last_name,
            "email": patron.email,
            "phone": patron.phone,
            "library_card": patron.library_card,
            "joined_group_at": member.joined_at.isoformat() if member.joined_at else None,
            "role": member.role,
        })

    return GroupExportResponse(
        group_name=group.name,
        exported_at=utc_now(),
        member_count=len(members),
        members=members,
    )


# =============================================================================
# Patron Search with Tags/Groups Filter
# =============================================================================


@router.get("/patrons/by-tag/{tag_id}")
async def get_patrons_by_tag(
    tag_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all patrons with a specific tag."""
    # Verify tag exists
    tag = await get_or_404(db, Tag, tag_id, "Tag not found")

    # Count total
    count_result = await db.execute(
        select(func.count(PatronTag.id)).where(PatronTag.tag_id == tag_id)
    )
    total = count_result.scalar() or 0

    # Get patrons
    result = await db.execute(
        select(User)
        .join(PatronTag, PatronTag.patron_id == User.id)
        .where(PatronTag.tag_id == tag_id)
        .order_by(User.last_name, User.first_name)
        .offset(offset)
        .limit(limit)
    )
    patrons = result.scalars().all()

    return {
        "tag": {"id": tag.id, "name": tag.name, "color": tag.color},
        "patrons": [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "email": p.email,
                "library_card": p.library_card,
                "is_active": p.is_active,
            }
            for p in patrons
        ],
        "total": total,
    }


@router.get("/patrons/by-group/{group_id}")
async def get_patrons_by_group(
    group_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all patrons in a specific group."""
    # Verify group exists
    group = await get_or_404(db, PatronGroup, group_id, "Group not found")

    # Count total
    count_result = await db.execute(
        select(func.count(PatronGroupMember.id)).where(PatronGroupMember.group_id == group_id)
    )
    total = count_result.scalar() or 0

    # Get patrons
    result = await db.execute(
        select(User, PatronGroupMember)
        .join(PatronGroupMember, PatronGroupMember.patron_id == User.id)
        .where(PatronGroupMember.group_id == group_id)
        .order_by(User.last_name, User.first_name)
        .offset(offset)
        .limit(limit)
    )

    return {
        "group": {"id": group.id, "name": group.name},
        "patrons": [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "email": p.email,
                "library_card": p.library_card,
                "is_active": p.is_active,
                "role_in_group": m.role,
            }
            for p, m in result.all()
        ],
        "total": total,
    }
