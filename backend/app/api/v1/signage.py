# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Signage Control System API Endpoints

Provides RESTful API for managing digital signage displays, content,
scheduling, and analytics without printing.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...models import User
from .dependencies import get_current_user, require_staff, require_admin, require_director
from ...services.signage_service import (
    SignageService,
    SignageContentService,
    SignageTemplateService,
    SignageScheduleService,
    SignageEmergencyService,
    SignageAnalyticsService,
    SignageWayfinderService,
    SignageEventPromotionService,
    SignageBranchContentService,
)

# ============================================================================
# Pydantic Schemas
# ============================================================================


class SignageDisplayCreate(BaseModel):

    name: str
    location_description: str
    display_type: str
    branch_id: Optional[int] = None
    device_identifier: Optional[str] = None
    mac_address: Optional[str] = None
    width_pixels: int = 1920
    height_pixels: int = 1080
    brightness_level: int = 100
    refresh_interval_seconds: int = 30


class SignageDisplayUpdate(BaseModel):

    name: Optional[str] = None
    status: Optional[str] = None
    brightness_level: Optional[int] = None
    refresh_interval_seconds: Optional[int] = None


class SignageDisplayResponse(BaseModel):

    id: int
    name: str
    location_description: str
    display_type: str
    status: str
    is_online: bool
    last_heartbeat: Optional[datetime] = None
    branch_id: Optional[int] = None

    class Config:
        from_attributes = True


class SignageContentCreate(BaseModel):

    title: str
    content_type: str
    description: Optional[str] = None
    branch_id: Optional[int] = None
    template_id: Optional[int] = None
    html_content: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    live_data_source: Optional[str] = None
    display_duration_seconds: int = 30
    transition_effect: str = "fade"


class SignageContentUpdate(BaseModel):

    title: Optional[str] = None
    description: Optional[str] = None
    html_content: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None


class SignageContentResponse(BaseModel):

    id: int
    title: str
    content_type: str
    approval_status: str
    created_by_user_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SignageTemplateCreate(BaseModel):

    name: str
    html_template: str
    category: Optional[str] = None
    is_public: bool = False
    css_styles: Optional[str] = None
    template_variables: Optional[dict] = None


class SignageTemplateResponse(BaseModel):

    id: int
    name: str
    category: Optional[str] = None
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SignageScheduleCreate(BaseModel):

    display_id: int
    content_id: int
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    schedule_type: str = "one_time"
    event_id: Optional[int] = None
    display_priority: int = 100


class SignageScheduleResponse(BaseModel):

    id: int
    display_id: int
    content_id: int
    schedule_type: str
    start_datetime: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SignageEmergencyMessageCreate(BaseModel):

    message_title: str
    message_content: str
    display_id: Optional[int] = None
    applies_to_all: bool = False
    message_type: str = "warning"
    background_color: str = "#FF0000"
    text_color: str = "#FFFFFF"
    flash_enabled: bool = False
    sound_alert_enabled: bool = False


class SignageEmergencyMessageResponse(BaseModel):

    id: int
    message_title: str
    is_active: bool
    applies_to_all_displays: bool
    activated_at: datetime

    class Config:
        from_attributes = True


class SignageAnalyticsResponse(BaseModel):

    display_id: Optional[int] = None
    content_id: Optional[int] = None
    total_views: int
    total_display_time: int
    total_interactions: int


class SignageWayfinderNodeCreate(BaseModel):

    location_name: str
    display_id: Optional[int] = None
    location_type: Optional[str] = None
    floor_number: Optional[int] = None
    services_available: Optional[str] = None
    room_info: Optional[dict] = None


class SignageWayfinderNodeResponse(BaseModel):

    id: int
    location_name: str
    location_type: Optional[str] = None
    floor_number: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/signage", tags=["signage"])


# ============================================================================
# Display Management Endpoints
# ============================================================================


@router.post("/displays", response_model=SignageDisplayResponse, status_code=status.HTTP_201_CREATED)
async def create_signage_display(
    request: SignageDisplayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new signage display."""
    service = SignageService(db)
    display = await service.create_display(
        name=request.name,
        location_description=request.location_description,
        display_type=request.display_type,
        branch_id=request.branch_id,
        device_identifier=request.device_identifier,
        mac_address=request.mac_address,
        width_pixels=request.width_pixels,
        height_pixels=request.height_pixels,
        brightness_level=request.brightness_level,
        refresh_interval_seconds=request.refresh_interval_seconds,
        user_id=current_user.id,
    )
    await db.commit()
    return display


@router.get("/displays/{display_id}", response_model=SignageDisplayResponse)
async def get_display(
    display_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a signage display by ID."""
    service = SignageService(db)
    display = await service.get_display(display_id)
    if not display:
        raise HTTPException(status_code=404, detail="Display not found")
    return display


@router.get("/displays", response_model=dict)
async def list_displays(
    status: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    display_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List signage displays with optional filtering."""
    service = SignageService(db)
    displays, total = await service.list_displays(
        status=status,
        branch_id=branch_id,
        display_type=display_type,
        limit=limit,
        offset=offset,
    )
    return {"displays": displays, "total": total, "limit": limit, "offset": offset}


@router.put("/displays/{display_id}", response_model=SignageDisplayResponse)
async def update_display(
    display_id: int,
    request: SignageDisplayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a signage display."""
    service = SignageService(db)
    updates = {k: v for k, v in request.dict().items() if v is not None}
    display = await service.update_display(display_id, **updates)
    if not display:
        raise HTTPException(status_code=404, detail="Display not found")
    await db.commit()
    return display


@router.delete("/displays/{display_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_display(
    display_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a signage display."""
    service = SignageService(db)
    if not await service.delete_display(display_id):
        raise HTTPException(status_code=404, detail="Display not found")
    await db.commit()


@router.post("/displays/{display_id}/heartbeat")
async def record_heartbeat(
    display_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Record a heartbeat from a display device."""
    service = SignageService(db)
    display = await service.record_heartbeat(display_id)
    if not display:
        raise HTTPException(status_code=404, detail="Display not found")
    await db.commit()
    return {"status": "ok", "is_online": display.is_online}


# ============================================================================
# Content Management Endpoints
# ============================================================================


@router.post("/content", response_model=SignageContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    request: SignageContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create new signage content."""
    service = SignageContentService(db)
    content = await service.create_content(
        title=request.title,
        content_type=request.content_type,
        description=request.description,
        branch_id=request.branch_id,
        template_id=request.template_id,
        html_content=request.html_content,
        image_url=request.image_url,
        video_url=request.video_url,
        live_data_source=request.live_data_source,
        display_duration_seconds=request.display_duration_seconds,
        transition_effect=request.transition_effect,
        user_id=current_user.id,
    )
    await db.commit()
    return content


@router.get("/content/{content_id}", response_model=SignageContentResponse)
async def get_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get content by ID."""
    service = SignageContentService(db)
    content = await service.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("/content", response_model=dict)
async def list_content(
    approval_status: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List signage content with optional filtering."""
    service = SignageContentService(db)
    content, total = await service.list_content(
        approval_status=approval_status,
        content_type=content_type,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
    )
    return {"content": content, "total": total, "limit": limit, "offset": offset}


@router.put("/content/{content_id}", response_model=SignageContentResponse)
async def update_content(
    content_id: int,
    request: SignageContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update content (draft only)."""
    service = SignageContentService(db)
    updates = {k: v for k, v in request.dict().items() if v is not None}
    content = await service.update_content(content_id, **updates)
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Content not found or not in draft status",
        )
    await db.commit()
    return content


@router.post("/content/{content_id}/submit-for-approval", response_model=SignageContentResponse)
async def submit_for_approval(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Submit content for approval workflow."""
    service = SignageContentService(db)
    content = await service.submit_for_approval(content_id)
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Content not found or not in draft status",
        )
    await db.commit()
    return content


@router.post("/content/{content_id}/approve", response_model=SignageContentResponse)
async def approve_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director),
):
    """Approve content for display."""
    service = SignageContentService(db)
    content = await service.approve_content(content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.commit()
    return content


@router.post("/content/{content_id}/reject", response_model=SignageContentResponse)
async def reject_content(
    content_id: int,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director),
):
    """Reject content with reason."""
    service = SignageContentService(db)
    content = await service.reject_content(content_id, current_user.id, reason)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.commit()
    return content


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete content (unscheduled only)."""
    service = SignageContentService(db)
    if not await service.delete_content(content_id):
        raise HTTPException(
            status_code=400,
            detail="Content not found or is scheduled",
        )
    await db.commit()


# ============================================================================
# Template Library Endpoints
# ============================================================================


@router.post("/templates", response_model=SignageTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: SignageTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new signage template."""
    service = SignageTemplateService(db)
    template = await service.create_template(
        name=request.name,
        html_template=request.html_template,
        category=request.category,
        is_public=request.is_public,
        css_styles=request.css_styles,
        template_variables=request.template_variables,
        user_id=current_user.id,
    )
    await db.commit()
    return template


@router.get("/templates/{template_id}", response_model=SignageTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a template by ID."""
    service = SignageTemplateService(db)
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/templates", response_model=dict)
async def list_templates(
    category: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List templates with optional filtering."""
    service = SignageTemplateService(db)
    templates, total = await service.list_templates(
        category=category,
        is_public=is_public,
        limit=limit,
        offset=offset,
    )
    return {"templates": templates, "total": total, "limit": limit, "offset": offset}


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a template."""
    service = SignageTemplateService(db)
    if not await service.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    await db.commit()


# ============================================================================
# Scheduling Endpoints
# ============================================================================


@router.post("/schedules", response_model=SignageScheduleResponse, status_code=status.HTTP_201_CREATED)
async def schedule_content(
    request: SignageScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Schedule content on a display."""
    service = SignageScheduleService(db)
    schedule = await service.schedule_content(
        display_id=request.display_id,
        content_id=request.content_id,
        start_datetime=request.start_datetime,
        end_datetime=request.end_datetime,
        schedule_type=request.schedule_type,
        event_id=request.event_id,
        display_priority=request.display_priority,
        user_id=current_user.id,
    )
    await db.commit()
    return schedule


@router.get("/schedules/{display_id}", response_model=dict)
async def get_display_schedule(
    display_id: int,
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get schedules for a display."""
    service = SignageScheduleService(db)
    schedules = await service.list_schedules_for_display(display_id, is_active)
    return {"display_id": display_id, "schedules": schedules}


@router.get("/displays/{display_id}/current-content")
async def get_current_content(
    display_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active content for a display."""
    service = SignageScheduleService(db)
    content = await service.get_active_content_for_display(display_id)
    if not content:
        return {"display_id": display_id, "current_content": None}
    return {
        "display_id": display_id,
        "current_content": {
            "id": content.id,
            "title": content.title,
            "html_content": content.html_content,
            "display_duration_seconds": content.display_duration_seconds,
        },
    }


@router.put("/schedules/{schedule_id}", response_model=SignageScheduleResponse)
async def update_schedule(
    schedule_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a schedule."""
    service = SignageScheduleService(db)
    schedule = await service.update_schedule(schedule_id, **request)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.commit()
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a schedule."""
    service = SignageScheduleService(db)
    if not await service.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.commit()


# ============================================================================
# Emergency Message Endpoints
# ============================================================================


@router.post("/emergency-messages", response_model=SignageEmergencyMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_emergency_message(
    request: SignageEmergencyMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create an emergency message (overrides all content)."""
    service = SignageEmergencyService(db)
    message = await service.create_emergency_message(
        message_title=request.message_title,
        message_content=request.message_content,
        display_id=request.display_id,
        applies_to_all=request.applies_to_all,
        message_type=request.message_type,
        background_color=request.background_color,
        text_color=request.text_color,
        flash_enabled=request.flash_enabled,
        sound_alert_enabled=request.sound_alert_enabled,
        user_id=current_user.id,
    )
    await db.commit()
    return message


@router.get("/emergency-messages")
async def get_active_emergency_messages(
    display_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active emergency messages."""
    service = SignageEmergencyService(db)
    messages = await service.get_active_emergency_messages(display_id)
    return {"messages": messages}


@router.post("/emergency-messages/{message_id}/deactivate")
async def deactivate_emergency_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Deactivate an emergency message."""
    service = SignageEmergencyService(db)
    message = await service.deactivate_emergency_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.commit()
    return {"status": "deactivated", "message_id": message.id}


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.post("/analytics/event")
async def record_analytics_event(
    display_id: int = Query(...),
    content_id: int = Query(...),
    event_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Record an analytics event from a display."""
    service = SignageAnalyticsService(db)
    await service.record_event(display_id, content_id, event_type)
    await db.commit()
    return {"status": "recorded"}


@router.get("/analytics/display/{display_id}", response_model=dict)
async def get_display_analytics(
    display_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics for a display."""
    service = SignageAnalyticsService(db)
    analytics = await service.get_display_analytics(display_id, days)
    return analytics


@router.get("/analytics/content/{content_id}", response_model=dict)
async def get_content_analytics(
    content_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get performance analytics for content."""
    service = SignageAnalyticsService(db)
    analytics = await service.get_content_performance(content_id, days)
    return analytics


# ============================================================================
# Wayfinding Endpoints
# ============================================================================


@router.post("/wayfinding/nodes", response_model=SignageWayfinderNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_wayfinding_node(
    request: SignageWayfinderNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a wayfinding node for directory displays."""
    service = SignageWayfinderService(db)
    node = await service.create_wayfinder_node(
        location_name=request.location_name,
        display_id=request.display_id,
        location_type=request.location_type,
        floor_number=request.floor_number,
        services_available=request.services_available,
        room_info=request.room_info,
        user_id=current_user.id,
    )
    await db.commit()
    return node


@router.get("/wayfinding/nodes", response_model=dict)
async def list_wayfinding_nodes(
    floor_number: Optional[int] = Query(None),
    location_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List wayfinding nodes."""
    service = SignageWayfinderService(db)
    nodes = await service.list_wayfinder_nodes(floor_number, location_type)
    return {"nodes": nodes}


@router.get("/wayfinding/nodes/{node_id}", response_model=SignageWayfinderNodeResponse)
async def get_wayfinding_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a wayfinding node."""
    service = SignageWayfinderService(db)
    node = await service.get_wayfinder_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


# ============================================================================
# System Status Endpoints
# ============================================================================


@router.get("/status")
async def signage_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get overall signage system status."""
    service = SignageService(db)
    displays, total = await service.list_displays(limit=1000, offset=0)

    online_count = sum(1 for d in displays if d.is_online)
    offline_count = total - online_count

    return {
        "total_displays": total,
        "online_displays": online_count,
        "offline_displays": offline_count,
        "system_status": "operational" if online_count > 0 else "degraded",
    }


# ============================================================================
# Event Promotion Schemas
# ============================================================================


class SignageEventPromotionCreate(BaseModel):

    event_id: int
    content_id: int
    display_id: Optional[int] = None
    promotion_start: Optional[datetime] = None
    promotion_end: Optional[datetime] = None
    auto_schedule: bool = True
    priority: int = 50


class SignageEventPromotionUpdate(BaseModel):

    display_id: Optional[int] = None
    promotion_start: Optional[datetime] = None
    promotion_end: Optional[datetime] = None
    auto_schedule: Optional[bool] = None
    priority: Optional[int] = None


class SignageEventPromotionResponse(BaseModel):

    id: int
    event_id: int
    content_id: int
    display_id: Optional[int] = None
    promotion_start: Optional[datetime] = None
    promotion_end: Optional[datetime] = None
    auto_schedule: bool
    priority: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Branch Content Schemas
# ============================================================================


class SignageBranchContentCreate(BaseModel):

    branch_id: int
    content_id: int
    override_content: Optional[str] = None
    is_localized: bool = False
    display_priority: int = 100


class SignageBranchContentUpdate(BaseModel):

    override_content: Optional[str] = None
    is_localized: Optional[bool] = None
    display_priority: Optional[int] = None


class SignageBranchContentResponse(BaseModel):

    id: int
    branch_id: int
    content_id: int
    override_content: Optional[str] = None
    is_localized: bool
    display_priority: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Event Promotion Endpoints
# ============================================================================


@router.post("/event-promotions", response_model=SignageEventPromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_event_promotion(
    request: SignageEventPromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create an event promotion linking an event to signage content."""
    service = SignageEventPromotionService(db)
    promotion = await service.create_promotion(
        event_id=request.event_id,
        content_id=request.content_id,
        display_id=request.display_id,
        promotion_start=request.promotion_start,
        promotion_end=request.promotion_end,
        auto_schedule=request.auto_schedule,
        priority=request.priority,
        user_id=current_user.id,
    )
    await db.commit()
    return promotion


@router.get("/event-promotions/{promotion_id}", response_model=SignageEventPromotionResponse)
async def get_event_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an event promotion by ID."""
    service = SignageEventPromotionService(db)
    promotion = await service.get_promotion(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Event promotion not found")
    return promotion


@router.get("/event-promotions", response_model=dict)
async def list_event_promotions(
    event_id: Optional[int] = Query(None),
    display_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List event promotions with optional filtering."""
    service = SignageEventPromotionService(db)
    promotions, total = await service.list_promotions(
        event_id=event_id,
        display_id=display_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return {"promotions": promotions, "total": total, "limit": limit, "offset": offset}


@router.get("/events/{event_id}/promotions", response_model=dict)
async def get_promotions_for_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all active promotions for a specific event."""
    service = SignageEventPromotionService(db)
    promotions = await service.get_promotions_for_event(event_id)
    return {"event_id": event_id, "promotions": promotions}


@router.put("/event-promotions/{promotion_id}", response_model=SignageEventPromotionResponse)
async def update_event_promotion(
    promotion_id: int,
    request: SignageEventPromotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an event promotion."""
    service = SignageEventPromotionService(db)
    updates = {k: v for k, v in request.dict().items() if v is not None}
    promotion = await service.update_promotion(promotion_id, **updates)
    if not promotion:
        raise HTTPException(status_code=404, detail="Event promotion not found")
    await db.commit()
    return promotion


@router.post("/event-promotions/{promotion_id}/deactivate")
async def deactivate_event_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Deactivate an event promotion."""
    service = SignageEventPromotionService(db)
    promotion = await service.deactivate_promotion(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Event promotion not found")
    await db.commit()
    return {"status": "deactivated", "promotion_id": promotion.id}


@router.delete("/event-promotions/{promotion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete an event promotion."""
    service = SignageEventPromotionService(db)
    if not await service.delete_promotion(promotion_id):
        raise HTTPException(status_code=404, detail="Event promotion not found")
    await db.commit()


# ============================================================================
# Branch Content Endpoints
# ============================================================================


@router.post("/branch-content", response_model=SignageBranchContentResponse, status_code=status.HTTP_201_CREATED)
async def create_branch_content(
    request: SignageBranchContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a branch-specific content override."""
    service = SignageBranchContentService(db)
    branch_content = await service.create_branch_content(
        branch_id=request.branch_id,
        content_id=request.content_id,
        override_content=request.override_content,
        is_localized=request.is_localized,
        display_priority=request.display_priority,
        user_id=current_user.id,
    )
    await db.commit()
    return branch_content


@router.get("/branch-content/{branch_content_id}", response_model=SignageBranchContentResponse)
async def get_branch_content(
    branch_content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get branch content by ID."""
    service = SignageBranchContentService(db)
    branch_content = await service.get_branch_content(branch_content_id)
    if not branch_content:
        raise HTTPException(status_code=404, detail="Branch content not found")
    return branch_content


@router.get("/branch-content", response_model=dict)
async def list_branch_content(
    branch_id: Optional[int] = Query(None),
    content_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List branch content with optional filtering."""
    service = SignageBranchContentService(db)
    items, total = await service.list_branch_content(
        branch_id=branch_id,
        content_id=content_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return {"branch_content": items, "total": total, "limit": limit, "offset": offset}


@router.get("/branches/{branch_id}/content", response_model=dict)
async def get_content_for_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all active content overrides for a branch."""
    service = SignageBranchContentService(db)
    items = await service.get_content_for_branch(branch_id)
    return {"branch_id": branch_id, "content": items}


@router.put("/branch-content/{branch_content_id}", response_model=SignageBranchContentResponse)
async def update_branch_content(
    branch_content_id: int,
    request: SignageBranchContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update branch content."""
    service = SignageBranchContentService(db)
    updates = {k: v for k, v in request.dict().items() if v is not None}
    branch_content = await service.update_branch_content(branch_content_id, **updates)
    if not branch_content:
        raise HTTPException(status_code=404, detail="Branch content not found")
    await db.commit()
    return branch_content


@router.delete("/branch-content/{branch_content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_content(
    branch_content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete branch content override."""
    service = SignageBranchContentService(db)
    if not await service.delete_branch_content(branch_content_id):
        raise HTTPException(status_code=404, detail="Branch content not found")
    await db.commit()
