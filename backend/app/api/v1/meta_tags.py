# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for meta tags: admin CRUD and social sharing generation.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.page_meta_tag import PageMetaTag
from ...models.user import User
from ...schemas.meta_tags import MetaTagsResponse, MetaTagsNotFoundResponse
from ...services import meta_tags_service
from .auth import get_current_user
from .dependencies import check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/meta-tags", tags=["meta-tags"])


# ---------------------------------------------------------------------------
# Pydantic schemas for admin CRUD
# ---------------------------------------------------------------------------

class PageMetaTagCreate(BaseModel):
    page_path: str
    page_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_card: Optional[str] = "summary_large_image"
    canonical_url: Optional[str] = None
    robots: Optional[str] = "index, follow"


class PageMetaTagOut(BaseModel):
    id: int
    page_path: str
    page_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_card: Optional[str] = None
    canonical_url: Optional[str] = None
    robots: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Admin CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
@limiter.limit("120/minute")
async def list_or_generate_meta_tags(
    request: Request,
    resource_type: Optional[str] = Query(
        None,
        description="Type of resource for social sharing generation",
        pattern="^(book|event|author|reading-list)$",
    ),
    resource_id: Optional[int] = Query(None, description="ID of the resource", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """List admin meta tags, or generate social sharing tags if resource_type/resource_id provided."""
    # Social sharing generation mode
    if resource_type and resource_id:
        try:
            meta_tags = await meta_tags_service.generate_meta_tags(
                resource_type=resource_type.lower(),
                resource_id=resource_id,
                db=db,
                base_url=str(request.base_url).rstrip("/"),
            )
            return meta_tags.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception:
            logger.error(f"Error generating meta tags for {resource_type}:{resource_id}", exc_info=True)
            return meta_tags_service._get_default_meta_tags(
                resource_type.lower(), resource_id, str(request.base_url).rstrip("/")
            ).model_dump()

    # Admin list mode
    query = select(PageMetaTag).order_by(PageMetaTag.page_path)
    result = await db.execute(query)
    tags = result.scalars().all()
    return {
        "tags": [PageMetaTagOut.model_validate(t).model_dump() for t in tags]
    }


@router.post("", response_model=PageMetaTagOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_meta_tag(
    request: Request,
    data: PageMetaTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a page meta tag. Admin only."""
    check_staff_access(current_user)

    existing = await db.execute(
        select(PageMetaTag).where(PageMetaTag.page_path == data.page_path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Meta tag for this path already exists")

    tag = PageMetaTag(**data.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=PageMetaTagOut)
@limiter.limit("60/minute")
async def update_meta_tag(
    request: Request,
    tag_id: int,
    data: PageMetaTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a page meta tag. Admin only."""
    check_staff_access(current_user)

    result = await db.execute(select(PageMetaTag).where(PageMetaTag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Meta tag not found")

    for field, value in data.model_dump().items():
        setattr(tag, field, value)
    tag.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_meta_tag(
    request: Request,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a page meta tag. Admin only."""
    check_staff_access(current_user)

    result = await db.execute(select(PageMetaTag).where(PageMetaTag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Meta tag not found")

    await db.delete(tag)
    await db.commit()


# ---------------------------------------------------------------------------
# Social sharing preview (kept from original)
# ---------------------------------------------------------------------------

@router.get(
    "/preview",
    response_model=dict,
    summary="Get HTML meta tags preview",
)
@limiter.limit("120/minute")
async def get_meta_tags_preview(
    request: Request,
    resource_type: str = Query(..., description="Type of resource"),
    resource_id: int = Query(..., description="ID of the resource", ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a preview of meta tags as HTML elements."""
    try:
        meta_tags = await meta_tags_service.generate_meta_tags(
            resource_type=resource_type.lower(),
            resource_id=resource_id,
            db=db,
            base_url=str(request.base_url).rstrip("/"),
        )

        tags_dict = meta_tags.model_dump()
        html_elements = []

        og_fields = [
            ("og:title", tags_dict.get("og_title")),
            ("og:description", tags_dict.get("og_description")),
            ("og:image", tags_dict.get("og_image")),
            ("og:url", tags_dict.get("og_url")),
            ("og:type", tags_dict.get("og_type")),
            ("og:site_name", tags_dict.get("og_site_name")),
        ]

        for property_name, content in og_fields:
            if content:
                escaped_content = content.replace('"', "&quot;")
                html_elements.append(
                    f'<meta property="{property_name}" content="{escaped_content}">'
                )

        twitter_fields = [
            ("twitter:card", tags_dict.get("twitter_card")),
            ("twitter:title", tags_dict.get("twitter_title")),
            ("twitter:description", tags_dict.get("twitter_description")),
            ("twitter:image", tags_dict.get("twitter_image")),
        ]

        for name, content in twitter_fields:
            if content:
                escaped_content = content.replace('"', "&quot;")
                html_elements.append(
                    f'<meta name="{name}" content="{escaped_content}">'
                )

        if tags_dict.get("twitter_creator"):
            html_elements.append(
                f'<meta name="twitter:creator" content="{tags_dict.get("twitter_creator")}">'
            )

        if tags_dict.get("twitter_site"):
            html_elements.append(
                f'<meta name="twitter:site" content="{tags_dict.get("twitter_site")}">'
            )

        return {
            "html_meta_tags": html_elements,
            "html_preview": "\n".join(html_elements),
            "meta_tags": tags_dict,
        }

    except Exception:
        logger.error("Error generating meta tags preview", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate meta tags preview",
        ) from None
