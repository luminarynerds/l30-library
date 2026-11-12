# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Emergency Operations API Routes

Comprehensive REST API endpoints for managing library emergency operations including
offline mode, data synchronization, emergency communications, and recovery procedures.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .auth import get_current_user
from .dependencies import is_admin, is_staff_or_admin, require_staff, require_admin
from ...models import User, UserRole
from ...schemas.emergency_operations import (
    # Offline Mode
    OfflineModeCreate, OfflineModeResponse, OfflineModeStatusResponse,
    # Paper Backup
    PaperFormCreate, PaperSubmissionCreate, PaperSubmissionResponse,
    # Data Sync
    DataSyncItemCreate, DataSyncItemResponse, SyncStatisticsResponse,
    # Emergency Contact
    CascadeCreate, CascadeContactCreate, CascadeResponse, CascadeExecutionResponse,
    # Building Closure
    ClosureCreate, ClosureResponse,
    # Service Continuity
    ServicePriorityCreate, ServicePriorityResponse,
    # Collection Recovery
    ProjectCreate, DamagedItemCreate, ProjectResponse, RecoveryStatisticsResponse,
    # Insurance
    InsuranceDocumentationCreate, InsuranceDocumentationResponse,
    # Post-Disaster Assessment
    AssessmentCreate, AssessmentResponse,
    # Community Resource Hub
    HubCreate, HubActivationRequest, HubResponse
)
from ...services.emergency_operations_service import (
    OfflineModeService, PaperBackupService, DataSyncService,
    EmergencyContactService, BuildingClosureService, ServiceContinuityService,
    CollectionRecoveryService, CommunityResourceHubService
)

router = APIRouter(prefix="/emergency-operations", tags=["emergency-operations"])


# ============ OFFLINE MODE ENDPOINTS ============

@router.post("/offline-mode/activate", response_model=OfflineModeResponse)
async def activate_offline_mode(
    data: OfflineModeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate offline mode for library operations"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    offline_mode = await OfflineModeService.activate_offline_mode(
        db=db,
        reason=data.reason,
        affected_services=data.affected_services,
        affected_branches=data.affected_branches,
        activated_by_id=current_user.id,
        recovery_priority=data.recovery_priority,
        estimated_restoration=data.estimated_restoration
    )
    return offline_mode


@router.post("/offline-mode/{mode_id}/deactivate", response_model=OfflineModeResponse)
async def deactivate_offline_mode(
    mode_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate offline mode and prepare for synchronization"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    offline_mode = await OfflineModeService.deactivate_offline_mode(
        db=db,
        offline_mode_id=mode_id,
        deactivated_by_id=current_user.id
    )
    return offline_mode


@router.get("/offline-mode/status", response_model=OfflineModeStatusResponse)
async def get_offline_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current offline mode status"""
    return await OfflineModeService.get_offline_mode_status(db=db)


# ============ PAPER BACKUP ENDPOINTS ============

@router.post("/paper-forms", response_model=dict)
async def create_paper_form(
    data: PaperFormCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a paper backup form template"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    form = await PaperBackupService.create_paper_form_template(
        db=db,
        form_type=data.form_type,
        form_name=data.form_name,
        form_template=data.form_template,
        pages_required=data.pages_required,
        barcode_required=data.barcode_required,
        signature_required=data.signature_required
    )
    return {"id": form.id, "form_name": form.form_name, "form_type": form.form_type}


@router.post("/paper-submissions", response_model=PaperSubmissionResponse)
async def submit_paper_form(
    data: PaperSubmissionCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Submit a completed paper form"""
    submission = await PaperBackupService.submit_paper_form(
        db=db,
        form_id=data.form_id,
        transaction_date=data.transaction_date,
        staff_initials=data.staff_initials,
        form_data=data.form_data,
        patron_id=data.patron_id,
        item_barcode=data.item_barcode,
        patron_name=data.patron_name,
        notes=data.notes,
        created_by_id=staff_user.id
    )
    return submission


@router.get("/paper-submissions/pending", response_model=List[PaperSubmissionResponse])
async def get_pending_submissions(
    form_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paper submissions waiting for synchronization"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    submissions = await PaperBackupService.get_pending_paper_submissions(
        db=db,
        form_type=form_type,
        limit=limit
    )
    return submissions


# ============ DATA SYNC ENDPOINTS ============

@router.post("/sync-queue", response_model=DataSyncItemResponse)
async def queue_sync_item(
    data: DataSyncItemCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Queue an item for synchronization"""
    sync_item = await DataSyncService.queue_sync_item(
        db=db,
        sync_source=data.sync_source,
        entity_type=data.entity_type,
        entity_data=data.entity_data,
        priority=data.priority,
        entity_id=data.entity_id,
        created_by_id=staff_user.id
    )
    return sync_item


@router.get("/sync-queue/pending", response_model=List[DataSyncItemResponse])
async def get_pending_sync_items(
    entity_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending items for synchronization"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    items = await DataSyncService.get_pending_sync_items(
        db=db,
        entity_type=entity_type,
        limit=limit
    )
    return items


@router.post("/sync-queue/{item_id}/complete", response_model=DataSyncItemResponse)
async def mark_sync_complete(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark synchronization item as complete"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    sync_item = await DataSyncService.mark_sync_complete(
        db=db,
        sync_item_id=item_id,
        processed_by_id=current_user.id
    )
    return sync_item


@router.get("/sync-statistics", response_model=SyncStatisticsResponse)
async def get_sync_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get synchronization statistics"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return await DataSyncService.get_sync_statistics(db=db)


# ============ EMERGENCY CONTACT CASCADE ENDPOINTS ============

@router.post("/cascades", response_model=CascadeResponse)
async def create_cascade(
    data: CascadeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an emergency contact cascade"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    cascade = await EmergencyContactService.create_cascade(
        db=db,
        cascade_name=data.cascade_name,
        auto_trigger_events=data.auto_trigger_events,
        message_template=data.message_template,
        manual_approval_required=data.manual_approval_required,
        max_contact_levels=data.max_contact_levels
    )
    return cascade


@router.post("/cascades/{cascade_id}/contacts", response_model=dict)
async def add_cascade_contact(
    cascade_id: int,
    data: CascadeContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a contact to emergency cascade"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    contact = await EmergencyContactService.add_contact_to_cascade(
        db=db,
        cascade_id=cascade_id,
        level=data.level,
        contact_role=data.contact_role,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        contact_method=data.contact_method,
        wait_time_seconds=data.wait_time_seconds,
        retry_attempts=data.retry_attempts
    )
    return {"id": contact.id, "level": contact.level, "contact_name": contact.contact_name}


@router.post("/cascades/{cascade_id}/execute", response_model=CascadeExecutionResponse)
async def execute_cascade(
    cascade_id: int,
    trigger_reason: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute emergency contact cascade"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    execution = await EmergencyContactService.execute_cascade(
        db=db,
        cascade_id=cascade_id,
        trigger_reason=trigger_reason,
        initiated_by_id=current_user.id
    )
    return execution


@router.get("/cascades", response_model=List[CascadeResponse])
async def get_active_cascades(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get active emergency contact cascades (admin only - exposes staff phone numbers)"""
    cascades = await EmergencyContactService.get_active_cascades(db=db)
    return cascades


# ============ BUILDING CLOSURE ENDPOINTS ============

@router.post("/closures", response_model=ClosureResponse)
async def create_closure(
    data: ClosureCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a building closure record"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    closure = await BuildingClosureService.create_closure(
        db=db,
        closure_reason=data.closure_reason,
        reason_details=data.reason_details,
        closure_start=data.closure_start,
        estimated_reopening=data.estimated_reopening,
        branches_affected=data.branches_affected,
        areas_affected=data.areas_affected,
        severity_level=data.severity_level,
        created_by_id=current_user.id
    )
    return closure


@router.post("/closures/{closure_id}/notify", response_model=ClosureResponse)
async def notify_about_closure(
    closure_id: int,
    message: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send patron notification about closure"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    closure = await BuildingClosureService.notify_patrons(
        db=db,
        closure_id=closure_id,
        message=message
    )
    return closure


@router.get("/closures/active", response_model=List[ClosureResponse])
async def get_active_closures(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active building closures"""
    closures = await BuildingClosureService.get_active_closures(db=db)
    return closures


# ============ SERVICE CONTINUITY ENDPOINTS ============

@router.post("/service-priorities", response_model=ServicePriorityResponse)
async def create_service_priority(
    data: ServicePriorityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create service continuity priority"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    service = await ServiceContinuityService.create_service_priority(
        db=db,
        service_name=data.service_name,
        service_category=data.service_category,
        priority=data.priority,
        rto_minutes=data.rto_minutes,
        rpo_minutes=data.rpo_minutes,
        max_acceptable_downtime=data.max_acceptable_downtime,
        manual_workaround=data.manual_workaround,
        required_staff_roles=data.required_staff_roles,
        critical_forms=data.critical_forms
    )
    return service


@router.get("/service-priorities/{priority}", response_model=List[ServicePriorityResponse])
async def get_services_by_priority(
    priority: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get services by priority level"""
    services = await ServiceContinuityService.get_priority_by_severity(
        db=db,
        priority=priority
    )
    return services


# ============ COLLECTION RECOVERY ENDPOINTS ============

@router.post("/recovery-projects", response_model=ProjectResponse)
async def create_recovery_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a collection recovery project"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    project = await CollectionRecoveryService.create_recovery_project(
        db=db,
        project_name=data.project_name,
        disaster_type=data.disaster_type,
        disaster_date=data.disaster_date,
        affected_areas=data.affected_areas,
        estimated_items_affected=data.estimated_items_affected,
        lead_staff_id=data.lead_staff_id or current_user.id
    )
    return project


@router.post("/recovery-projects/{project_id}/damaged-items", response_model=dict)
async def add_damaged_item(
    project_id: int,
    data: DamagedItemCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db)
):
    """Add a damaged item to recovery project"""
    item = await CollectionRecoveryService.add_damaged_item(
        db=db,
        project_id=project_id,
        item_barcode=data.item_barcode,
        damage_type=data.damage_type,
        damage_severity=data.damage_severity,
        damage_description=data.damage_description,
        title=data.title,
        author=data.author
    )
    return {"id": item.id, "barcode": item.item_barcode, "status": item.assessment_status}


@router.get("/recovery-projects/{project_id}/statistics", response_model=RecoveryStatisticsResponse)
async def get_recovery_statistics(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recovery statistics for a project"""
    stats = await CollectionRecoveryService.get_project_recovery_statistics(
        db=db,
        project_id=project_id
    )
    return stats


# ============ COMMUNITY RESOURCE HUB ENDPOINTS ============

@router.post("/community-hubs", response_model=HubResponse)
async def create_hub(
    data: HubCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a community resource hub"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    hub = await CommunityResourceHubService.create_hub(
        db=db,
        hub_name=data.hub_name,
        branch_id=data.branch_id,
        location_description=data.location_description,
        hub_purposes=data.hub_purposes,
        emergency_types=data.emergency_types,
        max_capacity=data.max_capacity,
        volunteer_coordinator_id=data.volunteer_coordinator_id
    )
    return hub


@router.post("/community-hubs/{hub_id}/activate", response_model=HubResponse)
async def activate_hub(
    hub_id: int,
    data: HubActivationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate a community resource hub"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    hub = await CommunityResourceHubService.activate_hub(
        db=db,
        hub_id=hub_id,
        activation_reason=data.activation_reason,
        activation_message=data.activation_message,
        activated_by_id=current_user.id
    )
    return hub


@router.post("/community-hubs/{hub_id}/deactivate", response_model=HubResponse)
async def deactivate_hub(
    hub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a community resource hub"""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    hub = await CommunityResourceHubService.deactivate_hub(db=db, hub_id=hub_id)
    return hub


@router.get("/community-hubs/active", response_model=List[HubResponse])
async def get_active_hubs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active community resource hubs"""
    hubs = await CommunityResourceHubService.get_active_hubs(db=db)
    return hubs
