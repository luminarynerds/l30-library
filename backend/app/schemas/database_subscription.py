# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.schemas._base import MoneyDecimal, StrictInputSchema


# ============ ENUMS ============

class ProxyType(str):
    EZPROXY = "ezproxy"
    OPENATHENS = "openathens"
    DIRECT = "direct"
    REFERRER = "referrer"
    SHIBBOLETH = "shibboleth"


class SubscriptionStatus(str):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"
    TRIAL = "trial"


class DatabaseCategory(str):
    GENERAL_REFERENCE = "general_reference"
    ACADEMIC = "academic"
    NEWSPAPERS = "newspapers"
    MAGAZINES = "magazines"
    EBOOKS = "ebooks"
    AUDIOBOOKS = "audiobooks"
    GENEALOGY = "genealogy"
    BUSINESS = "business"
    LEGAL = "legal"
    HEALTH = "health"
    CHILDREN = "children"
    TEEN = "teen"
    LANGUAGE_LEARNING = "language_learning"
    TEST_PREP = "test_prep"
    STREAMING_VIDEO = "streaming_video"
    STREAMING_MUSIC = "streaming_music"
    DIY_CRAFTS = "diy_crafts"
    AUTOMOTIVE = "automotive"
    OTHER = "other"


# ============ PROXY CONFIGURATION ============

class ProxyConfigurationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    proxy_type: str = Field(default="ezproxy")

    # EZproxy settings
    ezproxy_base_url: Optional[str] = None
    ezproxy_login_path: str = "/login"
    ezproxy_url_param: str = "url"

    # OpenAthens settings
    openathens_org_id: Optional[str] = None
    openathens_entity_id: Optional[str] = None
    openathens_wayfless_url: Optional[str] = None

    # Shibboleth settings
    shibboleth_entity_id: Optional[str] = None
    shibboleth_discovery_url: Optional[str] = None

    # IP ranges for on-site detection
    onsite_ip_ranges: List[str] = Field(default_factory=list)

    # Authentication settings
    requires_library_card: bool = True
    allows_guest_access: bool = False

    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None


class ProxyConfigurationCreate(StrictInputSchema, ProxyConfigurationBase):
    pass


class ProxyConfigurationUpdate(StrictInputSchema):
    name: Optional[str] = None
    proxy_type: Optional[str] = None
    ezproxy_base_url: Optional[str] = None
    ezproxy_login_path: Optional[str] = None
    ezproxy_url_param: Optional[str] = None
    openathens_org_id: Optional[str] = None
    openathens_entity_id: Optional[str] = None
    openathens_wayfless_url: Optional[str] = None
    shibboleth_entity_id: Optional[str] = None
    shibboleth_discovery_url: Optional[str] = None
    onsite_ip_ranges: Optional[List[str]] = None
    requires_library_card: Optional[bool] = None
    allows_guest_access: Optional[bool] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None


class ProxyConfigurationResponse(ProxyConfigurationBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ============ DATABASE VENDOR ============

class DatabaseVendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    short_name: Optional[str] = Field(None, max_length=50)

    # Contact information
    website: Optional[str] = None
    support_url: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None

    # Account information
    account_number: Optional[str] = None
    account_rep_name: Optional[str] = None
    account_rep_email: Optional[str] = None
    account_rep_phone: Optional[str] = None

    # Admin portal
    admin_portal_url: Optional[str] = None
    admin_username: Optional[str] = None

    notes: Optional[str] = None


class DatabaseVendorCreate(StrictInputSchema, DatabaseVendorBase):
    pass


class DatabaseVendorUpdate(StrictInputSchema):
    name: Optional[str] = None
    short_name: Optional[str] = None
    website: Optional[str] = None
    support_url: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    account_number: Optional[str] = None
    account_rep_name: Optional[str] = None
    account_rep_email: Optional[str] = None
    account_rep_phone: Optional[str] = None
    admin_portal_url: Optional[str] = None
    admin_username: Optional[str] = None
    notes: Optional[str] = None


class DatabaseVendorResponse(DatabaseVendorBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DatabaseVendorBrief(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    support_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============ SUSHI CREDENTIAL ============

class SUSHICredentialBase(BaseModel):
    vendor_id: int = Field(..., gt=0)
    label: str = Field(..., min_length=1, max_length=150)
    base_url: str = Field(..., min_length=1, max_length=1000)
    customer_id: str = Field(..., min_length=1, max_length=200)
    requestor_id: Optional[str] = Field(None, max_length=200)
    platform: Optional[str] = Field(None, max_length=200)
    is_active: bool = True
    notes: Optional[str] = None

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class SUSHICredentialCreate(StrictInputSchema, SUSHICredentialBase):
    api_key: Optional[str] = Field(None, max_length=1000)


class SUSHICredentialUpdate(StrictInputSchema):
    label: Optional[str] = Field(None, min_length=1, max_length=150)
    base_url: Optional[str] = Field(None, min_length=1, max_length=1000)
    customer_id: Optional[str] = Field(None, min_length=1, max_length=200)
    requestor_id: Optional[str] = Field(None, max_length=200)
    platform: Optional[str] = Field(None, max_length=200)
    api_key: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class SUSHICredentialResponse(BaseModel):
    id: int
    vendor_id: int
    label: str
    base_url: str
    customer_id: str
    requestor_id: Optional[str] = None
    platform: Optional[str] = None
    has_api_key: bool
    is_active: bool
    last_harvest_at: Optional[datetime] = None
    last_harvest_status: Optional[str] = None
    last_harvest_error: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ DATABASE SUBSCRIPTION ============

class DatabaseSubscriptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    short_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

    # Categorization
    category: str = Field(default="general_reference")
    subjects: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    # Access URLs
    access_url: str = Field(..., min_length=1)
    mobile_url: Optional[str] = None
    admin_url: Optional[str] = None
    help_url: Optional[str] = None

    # Proxy configuration
    proxy_type: str = Field(default="ezproxy")
    custom_proxy_url: Optional[str] = None
    requires_proxy: bool = True

    # Authentication
    auth_method: Optional[str] = None
    auth_notes: Optional[str] = None

    # Subscription dates
    subscription_start: date
    subscription_end: date
    trial_end: Optional[date] = None

    # Status
    auto_renew: bool = False
    renewal_reminder_days: int = Field(default=60, ge=0, le=365)
    renewal_contact_email: Optional[str] = None
    renewal_notes: Optional[str] = None

    # Cost
    annual_cost: Optional[MoneyDecimal] = None
    cost_per_use: Optional[MoneyDecimal] = None
    payment_frequency: str = "annual"

    # Contract
    contract_number: Optional[str] = None
    purchase_order: Optional[str] = None
    invoice_number: Optional[str] = None

    # Access restrictions
    simultaneous_users: Optional[int] = None
    session_ttl_minutes: Optional[int] = None
    patron_types_allowed: List[str] = Field(default_factory=list)
    branch_restrictions: List[str] = Field(default_factory=list)

    # Display
    is_active: bool = True
    is_featured: bool = False
    display_order: int = 0
    logo_url: Optional[str] = None

    # Usage tracking
    usage_stats_url: Optional[str] = None

    notes: Optional[str] = None
    internal_notes: Optional[str] = None

    # Several columns are nullable in the DB but carry a non-null default in this
    # schema (older/seeded rows hold NULL). from_attributes hands pydantic the
    # explicit None, which the declared default does NOT cover, so the response
    # 500s with a ResponseValidationError. Coerce None back to each field's
    # intended default at the boundary; fixes existing NULL rows without a
    # migration. Keep keys in sync with the field defaults above.
    _NULL_DEFAULTS: ClassVar[dict] = {
        "category": "general_reference",
        "subjects": [],
        "keywords": [],
        "proxy_type": "ezproxy",
        "requires_proxy": True,
        "auto_renew": False,
        "renewal_reminder_days": 60,
        "payment_frequency": "annual",
        "patron_types_allowed": [],
        "branch_restrictions": [],
        "is_featured": False,
        "display_order": 0,
    }

    @field_validator(
        "category", "subjects", "keywords", "proxy_type", "requires_proxy",
        "auto_renew", "renewal_reminder_days", "payment_frequency",
        "patron_types_allowed", "branch_restrictions", "is_featured", "display_order",
        mode="before",
    )
    @classmethod
    def _coerce_null_to_default(cls, v, info):
        if v is None:
            return cls._NULL_DEFAULTS.get(info.field_name)
        return v

    @field_validator('subscription_end')
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if 'subscription_start' in info.data and v < info.data['subscription_start']:
            raise ValueError('subscription_end must be after subscription_start')
        return v

    @field_validator("session_ttl_minutes")
    @classmethod
    def validate_session_ttl(cls, v):
        if v is not None and (v < 5 or v > 480):
            raise ValueError("session_ttl_minutes must be between 5 and 480")
        return v


class DatabaseSubscriptionCreate(StrictInputSchema, DatabaseSubscriptionBase):
    vendor_id: Optional[int] = None
    proxy_config_id: Optional[int] = None


class DatabaseSubscriptionUpdate(StrictInputSchema):
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subjects: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    vendor_id: Optional[int] = None
    access_url: Optional[str] = None
    mobile_url: Optional[str] = None
    admin_url: Optional[str] = None
    help_url: Optional[str] = None
    proxy_config_id: Optional[int] = None
    proxy_type: Optional[str] = None
    custom_proxy_url: Optional[str] = None
    requires_proxy: Optional[bool] = None
    auth_method: Optional[str] = None
    auth_notes: Optional[str] = None
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None
    trial_end: Optional[date] = None
    status: Optional[str] = None
    auto_renew: Optional[bool] = None
    renewal_reminder_days: Optional[int] = None
    renewal_contact_email: Optional[str] = None
    renewal_notes: Optional[str] = None
    annual_cost: Optional[MoneyDecimal] = None
    cost_per_use: Optional[MoneyDecimal] = None
    payment_frequency: Optional[str] = None
    contract_number: Optional[str] = None
    purchase_order: Optional[str] = None
    invoice_number: Optional[str] = None
    simultaneous_users: Optional[int] = None
    session_ttl_minutes: Optional[int] = None
    patron_types_allowed: Optional[List[str]] = None
    branch_restrictions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    logo_url: Optional[str] = None
    usage_stats_url: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None

    @field_validator("session_ttl_minutes")
    @classmethod
    def validate_session_ttl(cls, v):
        if v is not None and (v < 5 or v > 480):
            raise ValueError("session_ttl_minutes must be between 5 and 480")
        return v


class DatabaseSubscriptionResponse(DatabaseSubscriptionBase):
    id: int
    vendor_id: Optional[int] = None
    proxy_config_id: Optional[int] = None
    status: str
    last_renewal_reminder: Optional[datetime] = None
    last_usage_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    # Computed fields
    is_expired: bool
    is_expiring_soon: bool
    days_until_expiry: int

    model_config = ConfigDict(from_attributes=True)


class DatabaseSubscriptionWithVendor(DatabaseSubscriptionResponse):
    vendor: Optional[DatabaseVendorBrief] = None


class DatabaseSubscriptionPublic(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    description: Optional[str] = None
    category: str
    subjects: List[str] = []

    # Access
    proxy_url: str  # Pre-generated proxy URL
    mobile_url: Optional[str] = None
    help_url: Optional[str] = None

    # Display
    is_featured: bool = False
    logo_url: Optional[str] = None

    # Restrictions (patron-relevant)
    patron_types_allowed: List[str] = []
    simultaneous_users: Optional[int] = None
    session_ttl_minutes: Optional[int] = None

    # Authentication requirement (for frontend lock icon / login prompt)
    requires_authentication: bool = False

    model_config = ConfigDict(from_attributes=True)


class DatabaseAZListResponse(BaseModel):
    databases: List[DatabaseSubscriptionPublic]
    total: int
    categories: List[str]


# ============ USAGE STATISTICS ============

class DatabaseUsageStatsBase(BaseModel):
    stat_year: int = Field(..., ge=2000, le=2100)
    stat_month: int = Field(..., ge=1, le=12)

    # COUNTER metrics
    total_item_requests: int = 0
    unique_item_requests: int = 0
    total_item_investigations: int = 0
    unique_item_investigations: int = 0

    # Search metrics
    searches_regular: int = 0
    searches_federated: int = 0
    searches_automated: int = 0

    # Session metrics
    total_sessions: int = 0
    unique_users: int = 0

    # Turnaways
    no_license: int = 0

    # Access location
    onsite_sessions: int = 0
    offsite_sessions: int = 0

    data_source: Optional[str] = None


class DatabaseUsageStatsCreate(StrictInputSchema, DatabaseUsageStatsBase):
    subscription_id: int


class DatabaseUsageStatsUpdate(StrictInputSchema):
    total_item_requests: Optional[int] = Field(None, ge=0)
    unique_item_requests: Optional[int] = Field(None, ge=0)
    total_item_investigations: Optional[int] = Field(None, ge=0)
    unique_item_investigations: Optional[int] = Field(None, ge=0)
    searches_regular: Optional[int] = Field(None, ge=0)
    searches_federated: Optional[int] = Field(None, ge=0)
    searches_automated: Optional[int] = Field(None, ge=0)
    total_sessions: Optional[int] = Field(None, ge=0)
    unique_users: Optional[int] = Field(None, ge=0)
    no_license: Optional[int] = Field(None, ge=0)
    onsite_sessions: Optional[int] = Field(None, ge=0)
    offsite_sessions: Optional[int] = Field(None, ge=0)
    data_source: Optional[str] = None


class DatabaseUsageStatsResponse(DatabaseUsageStatsBase):
    id: int
    subscription_id: int
    imported_at: datetime
    cost_per_use: Optional[MoneyDecimal] = None

    model_config = ConfigDict(from_attributes=True)


class UsageReportRow(BaseModel):
    subscription_id: int
    database: str
    publisher: Optional[str] = None
    platform: Optional[str] = None
    searches_regular: int = 0
    searches_federated: int = 0
    searches_automated: int = 0
    total_item_requests: int = 0
    unique_item_requests: int = 0
    total_item_investigations: int = 0
    unique_item_investigations: int = 0
    no_license: int = 0
    annual_cost: Optional[MoneyDecimal] = None
    cost_per_use: Optional[MoneyDecimal] = None


class UsageReportPreview(BaseModel):
    year: int
    institution_name: str
    rows: list[UsageReportRow]
    totals: dict  # column name -> sum across all databases


class DatabaseUsageSummary(BaseModel):
    subscription_id: int
    subscription_name: str
    total_uses: int
    total_sessions: int
    unique_users: int
    cost_per_use: Optional[MoneyDecimal] = None
    trend: str = "stable"  # "up", "down", "stable"


# ============ ACCESS LOGGING ============

class DatabaseAccessLogCreate(StrictInputSchema):
    subscription_id: int
    patron_type: Optional[str] = None
    is_onsite: bool = False
    access_method: Optional[str] = None
    referrer_type: Optional[str] = None


class DatabaseAccessLogResponse(BaseModel):
    id: int
    subscription_id: int
    accessed_at: datetime
    patron_type: Optional[str] = None
    is_onsite: bool
    access_method: Optional[str] = None
    success: bool

    model_config = ConfigDict(from_attributes=True)


# ============ RENEWAL NOTIFICATIONS ============

class RenewalNotificationResponse(BaseModel):
    id: int
    subscription_id: int
    sent_at: datetime
    notification_type: str
    sent_to: str
    delivered: bool
    error_message: Optional[str] = None
    responded_at: Optional[datetime] = None
    response_action: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============ DASHBOARD / REPORTS ============

class SubscriptionExpirationAlert(BaseModel):
    id: int
    name: str
    vendor_name: Optional[str] = None
    subscription_end: date
    days_until_expiry: int
    status: str
    annual_cost: Optional[MoneyDecimal] = None
    renewal_contact_email: Optional[str] = None


class SubscriptionDashboard(BaseModel):
    total_active: int
    total_expired: int
    total_expiring_soon: int
    total_annual_cost: MoneyDecimal
    expiring_alerts: List[SubscriptionExpirationAlert]
    recently_renewed: List[DatabaseSubscriptionResponse]
    top_used: List[DatabaseUsageSummary]


class ProxyUrlRequest(StrictInputSchema):
    database_id: int


class ProxyUrlResponse(BaseModel):
    database_id: int
    database_name: str
    original_url: str
    proxy_url: str
    requires_authentication: bool
