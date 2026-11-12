# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ============ OFFLINE MODE ============

class OfflineModeCreate(StrictInputSchema):
    reason: str = Field(..., description="Reason for offline mode activation")
    affected_services: List[str] = Field(..., description="List of affected services")
    affected_branches: Optional[List[int]] = Field(None, description="Branch IDs affected, null for all")
    recovery_priority: str = Field("normal", description="Recovery priority level")
    estimated_restoration: Optional[datetime] = Field(None, description="Estimated restoration time")


class OfflineModeResponse(BaseModel):
    id: int
    status: str
    activated_at: datetime
    deactivated_at: Optional[datetime]
    reason: Optional[str]
    affected_services: Optional[List[str]]
    affected_branches: Optional[List[int]]
    estimated_restoration_time: Optional[datetime]

    class Config:
        from_attributes = True


class OfflineModeStatusResponse(BaseModel):
    is_offline: bool
    status: str
    activated_at: Optional[datetime] = None
    reason: Optional[str] = None
    affected_services: Optional[List[str]] = None
    affected_branches: Optional[List[int]] = None
    estimated_restoration: Optional[datetime] = None
    recovery_priority: Optional[str] = None
    pending_sync_items: int = 0
    paper_submissions_pending: int = 0
    mode_details: Optional[Dict[str, Any]] = None


# ============ PAPER BACKUP ============

class PaperFormCreate(StrictInputSchema):
    form_type: str
    form_name: str
    form_template: str
    pages_required: int = 1
    barcode_required: bool = True
    signature_required: bool = True


class PaperSubmissionCreate(StrictInputSchema):
    form_id: int
    transaction_date: datetime
    staff_initials: str
    form_data: Dict[str, Any]
    patron_id: Optional[int] = None
    item_barcode: Optional[str] = None
    patron_name: Optional[str] = None
    notes: Optional[str] = None


class PaperSubmissionResponse(BaseModel):
    id: int
    form_id: int
    form_type: str
    transaction_date: datetime
    staff_initials: str
    patron_id: Optional[int]
    item_barcode: Optional[str]
    synced: bool
    synced_at: Optional[datetime]
    sync_resolution: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ DATA SYNC ============

class DataSyncItemCreate(StrictInputSchema):
    sync_source: str
    entity_type: str
    entity_data: Dict[str, Any]
    priority: int = 0
    entity_id: Optional[str] = None


class DataSyncItemResponse(BaseModel):
    id: int
    sync_source: str
    entity_type: str
    entity_id: Optional[str]
    status: str
    priority: int
    retry_count: int
    last_error: Optional[str]
    created_at: datetime | None = None
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncStatisticsResponse(BaseModel):
    total_items: int
    pending: int
    synced: int
    failed: int
    pending_percentage: float


# ============ EMERGENCY CONTACT CASCADE ============

class CascadeCreate(StrictInputSchema):
    cascade_name: str
    auto_trigger_events: List[str]
    message_template: str
    manual_approval_required: bool = True
    max_contact_levels: int = 5


class CascadeContactCreate(StrictInputSchema):
    level: int
    contact_role: str
    contact_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_method: str = "email"
    wait_time_seconds: int = 0
    retry_attempts: int = 2


class CascadeContactResponse(BaseModel):
    id: int
    level: int
    contact_role: str
    contact_name: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    contact_method: str
    is_active: bool

    class Config:
        from_attributes = True


class CascadeResponse(BaseModel):
    id: int
    cascade_name: str
    cascade_description: Optional[str]
    is_active: bool
    auto_trigger_events: Optional[List[str]]
    manual_approval_required: bool
    max_contact_levels: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class CascadeExecutionResponse(BaseModel):
    id: int
    cascade_id: int
    trigger_reason: str
    initiated_at: datetime
    completed_at: Optional[datetime]
    total_contacts_to_reach: int
    total_contacts_reached: int
    contacts_not_reached: int

    class Config:
        from_attributes = True


# ============ BUILDING CLOSURE ============

class ClosureCreate(StrictInputSchema):
    closure_reason: str
    reason_details: str
    closure_start: datetime
    estimated_reopening: Optional[datetime] = None
    branches_affected: Optional[List[int]] = None
    areas_affected: Optional[List[str]] = None
    severity_level: str = "moderate"


class ClosureResponse(BaseModel):
    id: int
    closure_reason: str
    reason_details: str
    closure_start: datetime
    estimated_reopening: Optional[datetime]
    actual_reopening: Optional[datetime]
    is_active: bool
    severity_level: str
    patrons_notified: bool
    staff_notified: bool
    services_affected: Optional[List[str]]
    interim_services: Optional[str]
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ SERVICE CONTINUITY ============

class ServicePriorityCreate(StrictInputSchema):
    service_name: str
    service_category: str
    priority: str
    rto_minutes: int = Field(..., description="Recovery Time Objective in minutes")
    rpo_minutes: int = Field(..., description="Recovery Point Objective in minutes")
    max_acceptable_downtime: int
    manual_workaround: Optional[str] = None
    required_staff_roles: Optional[List[str]] = None
    critical_forms: Optional[List[str]] = None


class ServicePriorityResponse(BaseModel):
    id: int
    service_name: str
    service_description: Optional[str]
    service_category: str
    priority: str
    rto_minutes: int
    rpo_minutes: int
    max_acceptable_downtime: int
    has_paper_process: bool
    has_phone_process: bool
    manual_workaround: Optional[str]
    estimated_manual_capacity: Optional[str]
    required_staff_roles: Optional[List[str]]
    required_equipment: Optional[List[str]]
    critical_forms: Optional[List[str]]

    class Config:
        from_attributes = True


# ============ COLLECTION RECOVERY ============

class ProjectCreate(StrictInputSchema):
    project_name: str
    disaster_type: str
    disaster_date: datetime
    affected_areas: List[str]
    estimated_items_affected: Optional[int] = None
    lead_staff_id: Optional[int] = None


class DamagedItemCreate(StrictInputSchema):
    item_barcode: str
    damage_type: str
    damage_severity: str
    damage_description: str
    title: Optional[str] = None
    author: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    project_name: str
    project_description: Optional[str]
    disaster_type: str
    disaster_date: datetime
    affected_areas: List[str]
    estimated_items_affected: Optional[int]
    total_items_assessed: int
    items_salvaged: int
    items_lost: int
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class RecoveryStatisticsResponse(BaseModel):
    total_items: int
    salvageable: int
    unsalvageable: int
    total_repair_cost: float
    total_replacement_cost: float
    salvage_rate: float


# ============ INSURANCE DOCUMENTATION ============

class InsuranceDocumentationCreate(StrictInputSchema):
    incident_date: datetime
    incident_type: str
    incident_description: str
    incident_location: Optional[str] = None
    claim_number: Optional[str] = None
    insurance_company: str
    agent_name: str
    agent_phone: str
    agent_email: str
    initial_damage_estimate: float


class InsuranceDocumentationResponse(BaseModel):
    id: int
    incident_date: datetime
    incident_type: str
    incident_description: str
    claim_number: Optional[str]
    insurance_company: str
    agent_name: str
    initial_damage_estimate: float
    final_damage_amount: Optional[float]
    claimed_amount: Optional[float]
    approved_amount: Optional[float]
    reimbursed_amount: Optional[float]
    documentation_complete: bool
    claim_submitted: bool
    claim_approved: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ POST-DISASTER ASSESSMENT ============

class AssessmentCreate(StrictInputSchema):
    disaster_type: str
    disaster_date: datetime
    phase: str
    areas_assessed: List[str]
    assessment_team: List[int]
    building_exterior_damage: int = 0
    building_interior_damage: int = 0
    hazards_identified: Optional[List[str]] = None
    collection_damage_estimate_percent: Optional[float] = None
    mold_presence: bool = False


class AssessmentResponse(BaseModel):
    id: int
    assessment_date: datetime
    disaster_type: str
    disaster_date: datetime
    phase: str
    areas_assessed: List[str]
    building_exterior_damage: int
    building_interior_damage: int
    structural_integrity: Optional[str]
    hazards_identified: Optional[List[str]]
    collection_damage_estimate_percent: Optional[float]
    mold_presence: bool
    estimated_property_damage: Optional[float]
    estimated_content_loss: Optional[float]
    estimated_recovery_cost: Optional[float]
    assessment_complete: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============ COMMUNITY RESOURCE HUB ============

class HubCreate(StrictInputSchema):
    hub_name: str
    branch_id: int
    location_description: str
    hub_purposes: List[str]
    emergency_types: List[str]
    max_capacity: int
    volunteer_coordinator_id: Optional[int] = None


class HubActivationRequest(StrictInputSchema):
    activation_reason: str
    activation_message: str


class HubResponse(BaseModel):
    id: int
    hub_name: str
    branch_id: int
    location_description: str
    hub_purposes: List[str]
    emergency_types: List[str]
    max_capacity: int
    is_active: bool
    activated_at: Optional[datetime]
    deactivated_at: Optional[datetime]
    activation_reason: Optional[str]
    activation_message: Optional[str]
    current_capacity_used: int
    visitors_served_count: int
    supplies_stocked: bool
    equipment_tested: bool
    staff_trained: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True
