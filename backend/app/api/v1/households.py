# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Household Management API Endpoints

Enables family account linking, parent-child relationships, and unified household views.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.user import User, email_blind_hash
from ...models.household import HouseholdLink, HouseholdLinkStatus
from ...schemas.household import (
    LinkRequestCreate,
    LinkApprovalRequest,
    HouseholdLinkResponse,
    HouseholdLinkListResponse,
    HouseholdOverviewResponse,
    LinkedAccountInfo,
    FamilyAccountInfo,
)
from .auth import get_current_user
from .feature_guards import require_family_card_enabled

router = APIRouter(
    prefix="/households",
    tags=["households"],
    dependencies=[Depends(require_family_card_enabled)],
)


# =============================================================================
# Helper Functions
# =============================================================================


async def get_approved_household_links(
    user_id: int,
    db: AsyncSession
) -> list[HouseholdLink]:
    result = await db.execute(
        select(HouseholdLink).filter(
            and_(
                HouseholdLink.requester_id == user_id,
                HouseholdLink.status == HouseholdLinkStatus.APPROVED
            )
        ).options(
            selectinload(HouseholdLink.requester),
            selectinload(HouseholdLink.target_parent)
        )
    )
    return result.scalars().all()


async def get_household_members(
    household_id: int,
    db: AsyncSession
) -> list[User]:
    result = await db.execute(
        select(User).filter(User.household_id == household_id)
    )
    return result.scalars().all()


async def get_child_accounts(
    parent_id: int,
    db: AsyncSession
) -> list[User]:
    result = await db.execute(
        select(User).filter(
            User.id.in_(
                select(HouseholdLink.requester_id).filter(
                    and_(
                        HouseholdLink.target_parent_id == parent_id,
                        HouseholdLink.status == HouseholdLinkStatus.APPROVED
                    )
                )
            )
        )
    )
    return result.scalars().all()


async def calculate_household_aggregates(
    household_id: int,
    db: AsyncSession
) -> tuple[list, list, list]:
    # Get all users in household
    household_users = await get_household_members(household_id, db)
    user_ids = [u.id for u in household_users]

    if not user_ids:
        return [], [], []

    # Import models here to avoid circular imports
    from ...models.circulation import Hold, Checkout
    from ...models.fine import Fine

    # Query all holds for household users in one query (no N+1)
    holds_result = await db.execute(
        select(Hold)
        .where(Hold.user_id.in_(user_ids))
        .options(selectinload(Hold.user), selectinload(Hold.item))
        .order_by(Hold.created_at.desc())
    )
    holds = holds_result.scalars().all()

    # Query all checkouts for household users in one query (no N+1)
    checkouts_result = await db.execute(
        select(Checkout)
        .where(Checkout.user_id.in_(user_ids))
        .options(selectinload(Checkout.user), selectinload(Checkout.item))
        .order_by(Checkout.checked_out_at.desc())
    )
    checkouts = checkouts_result.scalars().all()

    # Query all fines for household users in one query (no N+1)
    fines_result = await db.execute(
        select(Fine)
        .where(Fine.user_id.in_(user_ids))
        .options(selectinload(Fine.user))
        .order_by(Fine.created_at.desc())
    )
    fines = fines_result.scalars().all()

    return holds, checkouts, fines


def format_link_response(link: HouseholdLink) -> HouseholdLinkResponse:
    return HouseholdLinkResponse(
        id=link.id,
        requester_id=link.requester_id,
        requester_name=link.requester.full_name,
        target_parent_id=link.target_parent_id,
        target_parent_name=link.target_parent.full_name,
        status=link.status.value,
        message=link.message,
        decline_reason=link.decline_reason,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def _redact_teen_holds(holds: list, teen_user_ids: set[int]) -> list:
    redacted = []
    for hold in holds:
        if hold.user_id in teen_user_ids and hold.item:
            hold.item.title = "Title hidden (teen privacy)"
            hold.item.author = None
        redacted.append(hold)
    return redacted


def _redact_teen_checkouts(checkouts: list, teen_user_ids: set[int]) -> list:
    redacted = []
    for checkout in checkouts:
        if checkout.user_id in teen_user_ids and checkout.item:
            checkout.item.title = "Title hidden (teen privacy)"
            checkout.item.author = None
        redacted.append(checkout)
    return redacted


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/link-request", response_model=HouseholdLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link_request(
    request: LinkRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a household link request.

    A child account uses this to request a link to their parent's account.
    The parent must approve the request before the accounts are linked.

    Args:
        request: LinkRequestCreate with parent_email and optional message
        current_user: The user making the request (requester/child)
        db: Database session

    Returns:
        HouseholdLinkResponse: Details of the created link request

    Raises:
        HTTPException 404: If parent email not found
        HTTPException 400: If trying to link to own account or duplicate request exists
    """
    # Get parent by email
    parent_result = await db.execute(
        select(User).filter(User.email_hash == email_blind_hash(request.parent_email))
    )
    parent = parent_result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent account with email '{request.parent_email}' not found"
        )

    # Cannot link to own account
    if parent.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link account to itself"
        )

    # Check if link already exists
    existing = await db.execute(
        select(HouseholdLink).filter(
            and_(
                HouseholdLink.requester_id == current_user.id,
                HouseholdLink.target_parent_id == parent.id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link request already exists for this parent"
        )

    # Create new link request
    link = HouseholdLink(
        requester_id=current_user.id,
        target_parent_id=parent.id,
        message=request.message,
        status=HouseholdLinkStatus.PENDING
    )

    db.add(link)
    await db.commit()
    await db.refresh(link)

    # Reload relationships
    await db.refresh(link, ["requester", "target_parent"])

    return format_link_response(link)


@router.patch("/{link_id}/approve-link", response_model=HouseholdLinkResponse)
async def approve_link(
    link_id: int,
    request: LinkApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve or decline a household link request.

    Only the target parent can approve/decline a link request.

    Args:
        link_id: ID of the household link to approve/decline
        request: LinkApprovalRequest with approved flag and optional decline_reason
        current_user: The user approving/declining (must be parent)
        db: Database session

    Returns:
        HouseholdLinkResponse: Updated link details

    Raises:
        HTTPException 404: If link not found
        HTTPException 403: If current user is not the target parent
        HTTPException 400: If link is not pending
    """
    link = await get_or_404(db, HouseholdLink, link_id)

    # Only parent can approve/decline
    if link.target_parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the target parent can approve this link"
        )

    # Can only approve/decline pending requests
    if link.status != HouseholdLinkStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify a {link.status} link request"
        )

    # Update link status
    if request.approved:
        link.status = HouseholdLinkStatus.APPROVED
        # Assign child to parent's household
        requester = await get_or_404(db, User, link.requester_id)

        # If parent has no household, create one
        if current_user.household_id is None:
            # Use parent's ID as household_id
            current_user.household_id = current_user.id
            db.add(current_user)

        # Assign child to same household
        requester.household_id = current_user.household_id
        db.add(requester)
    else:
        link.status = HouseholdLinkStatus.DECLINED
        link.decline_reason = request.decline_reason

    link.updated_at = datetime.now(timezone.utc)
    db.add(link)
    await db.commit()
    await db.refresh(link)

    # Reload relationships
    await db.refresh(link, ["requester", "target_parent"])

    return format_link_response(link)


@router.get("/me", response_model=HouseholdOverviewResponse)
async def get_household_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's household overview.

    Returns comprehensive household information including:
    - Linked accounts (parent/children)
    - Pending link requests (if viewing as parent)
    - Aggregated holds, checkouts, and fines for household

    Args:
        current_user: The authenticated user
        db: Database session

    Returns:
        HouseholdOverviewResponse: Household details and aggregated data
    """
    household_members: list[LinkedAccountInfo] = []
    pending_requests: list[HouseholdLinkResponse] = []
    relationship = "self"

    # If user has household_id, they're part of a family
    if current_user.household_id:
        # Get all household members
        members = await get_household_members(current_user.household_id, db)

        # Efficiently load all parent-child relationships in one query (no N+1)
        member_ids = [m.id for m in members]
        parent_ids_result = await db.execute(
            select(HouseholdLink.target_parent_id)
            .where(
                and_(
                    HouseholdLink.target_parent_id.in_(member_ids),
                    HouseholdLink.status == HouseholdLinkStatus.APPROVED
                )
            )
            .distinct()
        )
        parent_ids_set = set(parent_ids_result.scalars().all())

        # Load link timestamps for all household members
        links_result = await db.execute(
            select(HouseholdLink)
            .where(
                and_(
                    or_(
                        HouseholdLink.requester_id.in_(member_ids),
                        HouseholdLink.target_parent_id.in_(member_ids),
                    ),
                    HouseholdLink.status == HouseholdLinkStatus.APPROVED,
                )
            )
        )
        links = links_result.scalars().all()
        # Map member_id -> linked_at timestamp
        linked_at_map: dict[int, datetime | None] = {}
        for link in links:
            linked_at_map[link.requester_id] = link.updated_at
            linked_at_map[link.target_parent_id] = link.updated_at

        for member in members:
            # Determine relationship
            if member.id == current_user.id:
                member_relationship = "self"
            else:
                # Check if member is a parent (efficient lookup from already-loaded data)
                if member.id in parent_ids_set:
                    member_relationship = "parent"
                    relationship = "child"
                else:
                    member_relationship = "child"
                    relationship = "parent"

            household_members.append(
                LinkedAccountInfo(
                    id=member.id,
                    first_name=member.first_name,
                    last_name=member.last_name,
                    email=member.email,
                    relationship=member_relationship,
                    link_status="approved",
                    linked_at=linked_at_map.get(member.id),
                )
            )

        # If viewing as parent, get pending requests
        if relationship == "parent" or relationship == "self":
            pending_links = await db.execute(
                select(HouseholdLink)
                .filter(
                    and_(
                        HouseholdLink.target_parent_id == current_user.id,
                        HouseholdLink.status == HouseholdLinkStatus.PENDING
                    )
                )
                .options(
                    selectinload(HouseholdLink.requester),
                    selectinload(HouseholdLink.target_parent)
                )
            )
            for link in pending_links.scalars().all():
                pending_requests.append(format_link_response(link))

        # Get aggregated household data
        holds, checkouts, fines = await calculate_household_aggregates(
            current_user.household_id, db
        )

        # Teen privacy redaction (ALA guidance):
        # Parents can see that teens (13-17) have checkouts/holds and any
        # associated fines/due dates, but specific titles are redacted.
        # Children under 13 remain fully visible per COPPA parental rights.
        if relationship == "parent":
            teen_user_ids = {m.id for m in members if m.is_teen}
            holds = _redact_teen_holds(holds, teen_user_ids)
            checkouts = _redact_teen_checkouts(checkouts, teen_user_ids)
    else:
        # User not in a household yet
        holds, checkouts, fines = [], [], []

    # Calculate totals
    total_holds = len(holds)
    total_checkouts = len(checkouts)
    total_fines_amount = sum(f.amount for f in fines) if fines else 0.0

    return HouseholdOverviewResponse(
        viewing_as_user_id=current_user.id,
        viewing_as_name=current_user.full_name,
        relationship=relationship,
        household_id=current_user.household_id,
        household_members=household_members,
        pending_requests=pending_requests,
        holds=holds,
        checkouts=checkouts,
        fines=fines,
        total_holds=total_holds,
        total_checkouts=total_checkouts,
        total_fines_amount=total_fines_amount,
    )


@router.get("/pending-requests", response_model=HouseholdLinkListResponse)
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending link requests for the current user (as parent).

    Returns all pending link requests sent by children to this parent.

    Args:
        current_user: The authenticated user (parent)
        db: Database session

    Returns:
        HouseholdLinkListResponse: List of pending link requests
    """
    result = await db.execute(
        select(HouseholdLink)
        .filter(
            and_(
                HouseholdLink.target_parent_id == current_user.id,
                HouseholdLink.status == HouseholdLinkStatus.PENDING
            )
        )
        .options(
            selectinload(HouseholdLink.requester),
            selectinload(HouseholdLink.target_parent)
        )
        .order_by(HouseholdLink.created_at.desc())
    )

    links = result.scalars().all()
    formatted_links = [format_link_response(link) for link in links]

    return HouseholdLinkListResponse(
        links=formatted_links,
        total=len(formatted_links)
    )


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_household_link(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a household link.

    Both the requester (child) and target parent can delete a link.
    When a link is deleted, the child is removed from the household.

    Args:
        link_id: ID of the household link to delete
        current_user: The authenticated user
        db: Database session

    Raises:
        HTTPException 404: If link not found
        HTTPException 403: If current user is not requester or target parent
    """
    link = await get_or_404(db, HouseholdLink, link_id)

    # Only requester or parent can delete
    if link.requester_id != current_user.id and link.target_parent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this link"
        )

    # If approved link, remove child from household
    if link.status == HouseholdLinkStatus.APPROVED:
        child = await get_or_404(db, User, link.requester_id)
        child.household_id = None
        db.add(child)

    await db.delete(link)
    await db.commit()
