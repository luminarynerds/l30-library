# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


# ============================================================================
# Enums as string literals for API documentation
# ============================================================================

class LostItemStatusEnum:
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    CHARGED = "charged"
    FOUND = "found"
    WRITTEN_OFF = "written_off"
    DISPUTE_PENDING = "dispute_pending"


class LostItemTypeEnum:
    LOST_BY_PATRON = "lost_by_patron"
    LOST_IN_TRANSIT = "lost_in_transit"
    OVERDUE_CONVERSION = "overdue_conversion"
    CLAIMS_RETURNED = "claims_returned"
    MISSING_INVENTORY = "missing_inventory"


class DamagedItemStatusEnum:
    REPORTED = "reported"
    ASSESSMENT_PENDING = "assessment_pending"
    REPAIRABLE = "repairable"
    IN_MENDING = "in_mending"
    REPAIRED = "repaired"
    WITHDRAWN = "withdrawn"
    CHARGED = "charged"


class DamageSeverityEnum:
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    TOTAL_LOSS = "total_loss"


class ClaimDisputeStatusEnum:
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    SEARCH_IN_PROGRESS = "search_in_progress"
    APPROVED = "approved"
    DENIED = "denied"
    ITEM_FOUND = "item_found"


# ============================================================================
# Lost Item Schemas
# ============================================================================

class ReplacementCostBreakdownResponse(BaseModel):
    item_price: MoneyDecimal
    processing_fee: MoneyDecimal
    total: MoneyDecimal
    source: str

    class Config:
        from_attributes = True


class MarkItemLostRequest(StrictInputSchema):
    checkout_id: int = Field(..., description="ID of the checkout to mark as lost")
    lost_type: str = Field(..., description="Type of loss: lost_by_patron, lost_in_transit, claims_returned, missing_inventory")
    report_notes: Optional[str] = Field(None, description="Notes about the lost item report")
    custom_replacement_cost: Optional[MoneyDecimal] = Field(None, gt=0, description="Override replacement cost")
    send_notification: bool = Field(True, description="Send notification to patron")


class LostItemRecordResponse(BaseModel):
    id: int
    item_copy_id: Optional[int]
    checkout_id: Optional[int]
    catalog_item_id: Optional[int]
    patron_id: Optional[int]
    status: str
    lost_type: str
    item_price: Optional[MoneyDecimal]
    processing_fee: Optional[MoneyDecimal]
    replacement_cost: Optional[MoneyDecimal]
    credit_amount: Optional[MoneyDecimal]
    days_overdue_at_loss: Optional[int]
    report_notes: Optional[str]
    resolution_notes: Optional[str]
    reported_at: datetime
    confirmed_at: Optional[datetime]
    charged_at: Optional[datetime]
    found_at: Optional[datetime]
    written_off_at: Optional[datetime]
    last_known_location: Optional[str]
    # Related data
    patron_name: Optional[str] = None
    item_title: Optional[str] = None
    fine_amount: Optional[MoneyDecimal] = None
    fine_status: Optional[str] = None

    class Config:
        from_attributes = True


class LostItemWorkflowResponse(BaseModel):
    success: bool
    message: str
    lost_item_record: Optional[LostItemRecordResponse] = None
    replacement_cost: Optional[ReplacementCostBreakdownResponse] = None
    fine_id: Optional[int] = None
    notification_sent: bool = False


class ProcessFoundItemRequest(StrictInputSchema):
    lost_record_id: int = Field(..., description="ID of the lost item record")
    found_condition: str = Field("good", description="Condition of found item: new, good, fair, poor, damaged")
    resolution_notes: Optional[str] = Field(None, description="Notes about finding the item")
    send_notification: bool = Field(True, description="Send notification to patron")


class FoundItemResponse(BaseModel):
    success: bool
    message: str
    lost_item_record: Optional[LostItemRecordResponse] = None
    credit_amount: MoneyDecimal = Decimal("0.00")
    item_restored: bool = False
    notification_sent: bool = False


class LostItemListRequest(StrictInputSchema):
    status: Optional[str] = None
    lost_type: Optional[str] = None
    patron_id: Optional[int] = None
    days_ago: Optional[int] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class LostItemListResponse(BaseModel):
    items: List[LostItemRecordResponse]
    total: int
    limit: int
    offset: int


class AutoConvertOverdueRequest(StrictInputSchema):
    threshold_days: Optional[int] = Field(None, ge=1, le=365, description="Days overdue before marking lost")
    dry_run: bool = Field(False, description="Preview only, don't make changes")


class AutoConvertOverdueResponse(BaseModel):
    processed_count: int
    dry_run: bool
    results: List[LostItemWorkflowResponse]


# ============================================================================
# Damaged Item Schemas
# ============================================================================

class ReportDamageRequest(StrictInputSchema):
    item_copy_id: int = Field(..., description="ID of the damaged item copy")
    damage_types: List[str] = Field(..., description="Types of damage: torn_pages, water_damage, etc.")
    damage_description: str = Field(..., min_length=10, description="Description of the damage")
    severity: str = Field(..., description="Severity: minor, moderate, severe, total_loss")
    checkout_id: Optional[int] = Field(None, description="Associated checkout if applicable")
    patron_id: Optional[int] = Field(None, description="Patron ID if known")
    is_patron_responsible: bool = Field(False, description="Is the patron responsible for damage")
    photo_urls: Optional[List[str]] = Field(None, description="URLs to damage photos")
    send_notification: bool = Field(True, description="Send notification if patron charged")


class DamageAssessmentResponse(BaseModel):
    is_repairable: bool
    severity: str
    estimated_repair_cost: MoneyDecimal
    recommended_action: str
    patron_charge_amount: MoneyDecimal
    charge_percentage: MoneyDecimal


class DamagedItemRecordResponse(BaseModel):
    id: int
    item_copy_id: Optional[int]
    checkout_id: Optional[int]
    catalog_item_id: Optional[int]
    patron_id: Optional[int]
    status: str
    severity: str
    damage_types: Optional[List[str]]
    damage_description: str
    photo_urls: Optional[List[str]]
    assessment_notes: Optional[str]
    is_patron_responsible: bool
    estimated_repair_cost: Optional[MoneyDecimal]
    actual_repair_cost: Optional[MoneyDecimal]
    replacement_cost: Optional[MoneyDecimal]
    charge_amount: Optional[MoneyDecimal]
    repair_priority: Optional[int]
    repair_notes: Optional[str]
    reported_at: datetime
    assessed_at: Optional[datetime]
    resolved_at: Optional[datetime]
    # Related data
    patron_name: Optional[str] = None
    item_title: Optional[str] = None
    fine_status: Optional[str] = None

    class Config:
        from_attributes = True


class DamagedItemWorkflowResponse(BaseModel):
    success: bool
    message: str
    damaged_item_record: Optional[DamagedItemRecordResponse] = None
    assessment: Optional[DamageAssessmentResponse] = None
    fine_id: Optional[int] = None
    mending_entry_id: Optional[int] = None
    notification_sent: bool = False


class CompleteAssessmentRequest(StrictInputSchema):
    damage_record_id: int = Field(..., description="ID of the damage record")
    is_repairable: bool = Field(..., description="Can the item be repaired")
    charge_patron: bool = Field(False, description="Charge the patron for damage")
    charge_amount: Optional[MoneyDecimal] = Field(None, gt=0, description="Amount to charge")
    assessment_notes: Optional[str] = Field(None, description="Assessment notes")
    patron_responsibility_reason: Optional[str] = Field(None, description="Why patron is responsible")
    send_notification: bool = Field(True, description="Send notification to patron")


class SendToMendingRequest(StrictInputSchema):
    damage_record_id: int = Field(..., description="ID of the damage record")
    priority: int = Field(3, ge=1, le=5, description="Repair priority (1=urgent, 5=low)")
    repair_type: Optional[str] = Field(None, description="Type of repair needed")
    repair_instructions: Optional[str] = Field(None, description="Repair instructions")
    materials_needed: Optional[str] = Field(None, description="Materials required")
    estimated_time_hours: Optional[MoneyDecimal] = Field(None, gt=0, description="Estimated repair time")
    estimated_cost: Optional[MoneyDecimal] = Field(None, gt=0, description="Estimated repair cost")
    assigned_to_id: Optional[int] = Field(None, description="Staff member to assign repair")


class MendingQueueEntryResponse(BaseModel):
    id: int
    # Nullable FK in the DB (ON DELETE CASCADE leaves orphan-safe rows / older
    # entries hold NULL); declaring it required 500s the GET list.
    damaged_item_record_id: Optional[int] = None
    item_copy_id: Optional[int]
    priority: int
    queue_position: Optional[int]
    repair_type: Optional[str]
    repair_instructions: Optional[str]
    materials_needed: Optional[str]
    estimated_time_hours: Optional[MoneyDecimal]
    estimated_cost: Optional[MoneyDecimal]
    actual_cost: Optional[MoneyDecimal]
    is_in_progress: bool
    is_completed: bool
    added_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    completion_notes: Optional[str]
    # Related data
    item_title: Optional[str] = None
    assigned_to_name: Optional[str] = None

    class Config:
        from_attributes = True


class CompleteRepairRequest(StrictInputSchema):
    mending_entry_id: int = Field(..., description="ID of the mending queue entry")
    actual_cost: Optional[MoneyDecimal] = Field(None, ge=0, description="Actual repair cost")
    completion_notes: Optional[str] = Field(None, description="Notes about completed repair")
    new_condition: str = Field("good", description="Condition after repair: new, good, fair")


class RepairCompletionResponse(BaseModel):
    success: bool
    message: str
    damaged_item_record: Optional[DamagedItemRecordResponse] = None
    item_restored: bool = False
    actual_cost: MoneyDecimal = Decimal("0.00")


class WithdrawDamagedItemRequest(StrictInputSchema):
    damage_record_id: int = Field(..., description="ID of the damage record")
    withdrawal_reason: Optional[str] = Field(None, description="Reason for withdrawal")
    charge_patron: bool = Field(False, description="Charge patron replacement cost")
    charge_amount: Optional[MoneyDecimal] = Field(None, gt=0, description="Amount to charge")
    send_notification: bool = Field(True, description="Send notification to patron")


class DamagedItemListRequest(StrictInputSchema):
    status: Optional[str] = None
    severity: Optional[str] = None
    patron_id: Optional[int] = None
    is_patron_responsible: Optional[bool] = None
    days_ago: Optional[int] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class DamagedItemListResponse(BaseModel):
    items: List[DamagedItemRecordResponse]
    total: int
    limit: int
    offset: int


class MendingQueueListRequest(StrictInputSchema):
    include_completed: bool = Field(False, description="Include completed repairs")
    assigned_to_id: Optional[int] = None
    priority: Optional[int] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class MendingQueueListResponse(BaseModel):
    items: List[MendingQueueEntryResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Claims Returned Schemas
# ============================================================================

class FileClaimRequest(StrictInputSchema):
    checkout_id: int = Field(..., description="ID of the checkout")
    patron_statement: str = Field(..., min_length=10, description="Patron's statement about returning the item")
    claimed_return_date: Optional[date] = Field(None, description="Date patron claims they returned item")
    claimed_return_location: Optional[str] = Field(None, description="Location patron claims they returned to")
    send_notification: bool = Field(True, description="Send notification to staff")


class ClaimsReturnedDisputeResponse(BaseModel):
    id: int
    # Nullable FK in the DB (claims can be filed without a linked lost-item
    # record); declaring it required 500s the GET list on those rows.
    lost_item_record_id: Optional[int] = None
    item_copy_id: Optional[int]
    checkout_id: Optional[int]
    patron_id: Optional[int]
    status: str
    patron_statement: str
    claimed_return_date: Optional[date]
    claimed_return_location: Optional[str]
    investigation_notes: Optional[str]
    search_locations: Optional[List[str]]
    resolution: Optional[str]
    resolution_reason: Optional[str]
    credit_amount: Optional[MoneyDecimal]
    patron_previous_claims_count: int
    filed_at: datetime
    reviewed_at: Optional[datetime]
    resolved_at: Optional[datetime]
    # Related data
    patron_name: Optional[str] = None
    item_title: Optional[str] = None
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClaimsReturnedWorkflowResponse(BaseModel):
    success: bool
    message: str
    dispute: Optional[ClaimsReturnedDisputeResponse] = None
    notification_sent: bool = False


class StartReviewRequest(StrictInputSchema):
    dispute_id: int = Field(..., description="ID of the dispute")
    initial_notes: Optional[str] = Field(None, description="Initial review notes")


class StartSearchRequest(StrictInputSchema):
    dispute_id: int = Field(..., description="ID of the dispute")
    search_locations: List[str] = Field(..., min_length=1, description="Locations to search")
    search_notes: Optional[str] = Field(None, description="Search notes")


class ResolveClaimRequest(StrictInputSchema):
    dispute_id: int = Field(..., description="ID of the dispute")
    approved: bool = Field(..., description="Approve or deny the claim")
    resolution_reason: str = Field(..., min_length=10, description="Reason for resolution")
    item_found: bool = Field(False, description="Was the item found")
    credit_amount: Optional[MoneyDecimal] = Field(None, ge=0, description="Credit amount if applicable")
    send_notification: bool = Field(True, description="Send notification to patron")


class ClaimResolutionResponse(BaseModel):
    success: bool
    message: str
    dispute: Optional[ClaimsReturnedDisputeResponse] = None
    credit_amount: MoneyDecimal = Decimal("0.00")
    item_found: bool = False
    notification_sent: bool = False


class PatronClaimsHistoryResponse(BaseModel):
    patron_id: int
    total_claims: int
    claims_this_year: int
    approved_claims: int
    denied_claims: int
    pending_claims: int
    items_later_found: int
    is_at_risk: bool
    max_claims_allowed: int


class ClaimsListRequest(StrictInputSchema):
    status: Optional[str] = None
    patron_id: Optional[int] = None
    days_ago: Optional[int] = None
    unresolved_only: bool = Field(False, description="Show only unresolved claims")
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class ClaimsListResponse(BaseModel):
    items: List[ClaimsReturnedDisputeResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Reports Schemas
# ============================================================================

class FinancialSummaryResponse(BaseModel):
    total_charges: MoneyDecimal
    total_collected: MoneyDecimal
    total_outstanding: MoneyDecimal
    total_waived: MoneyDecimal
    total_credits: MoneyDecimal
    collection_rate: float
    period_start: datetime
    period_end: datetime


class ChargesByTypeResponse(BaseModel):
    lost_item_charges: MoneyDecimal
    damaged_item_charges: MoneyDecimal
    processing_fees: MoneyDecimal
    total: MoneyDecimal


class FinancialDetailResponse(BaseModel):
    lost_record_id: int
    patron_name: str
    item_title: str
    charge_date: datetime
    charge_amount: MoneyDecimal
    amount_paid: MoneyDecimal
    amount_waived: MoneyDecimal
    balance: MoneyDecimal
    status: str
    is_found: bool


class InventorySummaryResponse(BaseModel):
    total_lost: int
    lost_by_patron: int
    lost_in_transit: int
    claims_returned: int
    total_damaged: int
    damaged_repairable: int
    damaged_withdrawn: int
    in_mending: int
    items_found: int
    period_start: datetime
    period_end: datetime


class LostByCategoryResponse(BaseModel):
    item_type: str
    count: int
    total_value: MoneyDecimal
    percentage_of_total: float


class LostByLocationResponse(BaseModel):
    location: str
    count: int
    total_value: MoneyDecimal
    percentage_of_total: float


class TrendDataResponse(BaseModel):
    period: str
    lost_count: int
    damaged_count: int
    charges: MoneyDecimal
    credits: MoneyDecimal
    net: MoneyDecimal


class PatronRiskReportResponse(BaseModel):
    patron_id: int
    patron_name: str
    patron_email: Optional[str]
    lost_item_count: int
    damaged_item_count: int
    claims_returned_count: int
    total_charges: MoneyDecimal
    outstanding_balance: MoneyDecimal
    risk_score: int


class ReportDateRangeRequest(StrictInputSchema):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None


# ============================================================================
# Settings Schemas
# ============================================================================

class LostDamagedSettingsResponse(BaseModel):
    id: Optional[int] = None
    branch_id: Optional[int] = None
    branch_location: Optional[str] = None  # deprecated; use branch_id
    lost_item_processing_fee: MoneyDecimal
    default_replacement_cost: MoneyDecimal
    overdue_to_lost_days: int
    auto_convert_overdue_enabled: bool
    found_item_full_credit: bool
    found_item_credit_percentage: MoneyDecimal
    found_item_grace_period_days: int
    minor_damage_charge_percentage: MoneyDecimal
    moderate_damage_charge_percentage: MoneyDecimal
    severe_damage_charge_percentage: MoneyDecimal
    total_loss_charge_percentage: MoneyDecimal
    claims_returned_review_days: int
    max_claims_per_patron_year: int
    notify_patron_on_lost: bool
    notify_patron_on_damaged_charge: bool
    notify_patron_on_found: bool
    notify_staff_on_claims: bool
    is_active: bool

    class Config:
        from_attributes = True


class UpdateSettingsRequest(StrictInputSchema):
    lost_item_processing_fee: Optional[MoneyDecimal] = Field(None, ge=0)
    default_replacement_cost: Optional[MoneyDecimal] = Field(None, ge=0)
    overdue_to_lost_days: Optional[int] = Field(None, ge=1, le=365)
    auto_convert_overdue_enabled: Optional[bool] = None
    found_item_full_credit: Optional[bool] = None
    found_item_credit_percentage: Optional[MoneyDecimal] = Field(None, ge=0, le=100)
    found_item_grace_period_days: Optional[int] = Field(None, ge=0)
    minor_damage_charge_percentage: Optional[MoneyDecimal] = Field(None, ge=0, le=100)
    moderate_damage_charge_percentage: Optional[MoneyDecimal] = Field(None, ge=0, le=100)
    severe_damage_charge_percentage: Optional[MoneyDecimal] = Field(None, ge=0, le=100)
    total_loss_charge_percentage: Optional[MoneyDecimal] = Field(None, ge=0, le=100)
    claims_returned_review_days: Optional[int] = Field(None, ge=1, le=365)
    max_claims_per_patron_year: Optional[int] = Field(None, ge=1, le=100)
    notify_patron_on_lost: Optional[bool] = None
    notify_patron_on_damaged_charge: Optional[bool] = None
    notify_patron_on_found: Optional[bool] = None
    notify_staff_on_claims: Optional[bool] = None
