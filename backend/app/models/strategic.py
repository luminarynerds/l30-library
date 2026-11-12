# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Numeric,
    Date,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .mixins import TimestampMixin


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GoalStatus(StrEnum):
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    DELAYED = "delayed"
    COMPLETED = "completed"


class InitiativeStatus(StrEnum):
    PLANNING = "planning"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(StrEnum):
    IDENTIFIED = "identified"
    ASSESSING = "assessing"
    MITIGATING = "mitigating"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


class KPIFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class StrategicAlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class BudgetStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    CLOSED = "closed"


class BudgetTransactionType(StrEnum):
    ALLOCATION = "allocation"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    REFUND = "refund"


class ReportFrequency(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class StrategicPlan(Base):
    __tablename__ = "strategic_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Plan basics
    title = Column(String(300), nullable=False)
    description = Column(Text)

    # Time period (e.g., 2025-2028)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Strategic framework
    mission = Column(Text)  # Library's mission statement
    vision = Column(Text)  # Future vision
    values = Column(JSONB, default=list)  # Core values as list of strings

    # Status - using String to avoid enum complexity
    status = Column(String(20), default="draft", nullable=False)

    # Review tracking
    last_reviewed = Column(DateTime(timezone=True))
    next_review = Column(DateTime(timezone=True))

    # === NEW: Public display fields ===
    hero_image_url = Column(String(500))  # Hero image for public page
    story_intro = Column(Text)  # Narrative intro for public "Our Story" page
    # History timeline - key moments in library history
    # Format: [{"year": 1952, "title": "Founded", "description": "...", "image_url": "..."}]
    history_timeline = Column(JSONB, default=list)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    goals = relationship("StrategicGoal", back_populates="plan", cascade="all, delete-orphan")
    milestones = relationship(
        "StrategicMilestone", back_populates="plan", cascade="all, delete-orphan"
    )
    initiatives = relationship(
        "StrategicInitiative", back_populates="plan", cascade="all, delete-orphan"
    )
    kpis = relationship("StrategicKPI", back_populates="plan", cascade="all, delete-orphan")
    budgets = relationship("StrategicBudget", back_populates="plan", cascade="all, delete-orphan")
    risks = relationship("StrategicRisk", back_populates="plan", cascade="all, delete-orphan")
    dashboards = relationship(
        "ExecutiveDashboard", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicPlan {self.title}>"


# ============================================================================
# PHASE 1: Strategic Initiatives & Board Linkage
# ============================================================================


class StrategicInitiative(Base):
    __tablename__ = "strategic_initiatives"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # Initiative details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    business_case = Column(Text)  # Justification
    expected_outcomes = Column(JSONB, default=list)  # List of expected outcomes

    # Status and timeline
    status = Column(String(50), default="planning", nullable=False)
    start_date = Column(DateTime(timezone=True))
    target_completion_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))

    # Resources
    estimated_budget = Column(Numeric(12, 2))
    actual_cost = Column(Numeric(12, 2))
    assigned_leader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    team_members = Column(JSONB, default=list)  # List of user IDs

    # Priority and impact
    priority = Column(Integer, default=3)  # 1=highest, 5=lowest
    strategic_alignment_score = Column(Integer)  # 1-10 score

    # Board linkage
    board_approved = Column(Boolean, default=False)
    board_approval_date = Column(DateTime(timezone=True))
    board_meeting_reference = Column(String(200))

    # Progress tracking
    completion_percentage = Column(Integer, default=0)

    # Relationships
    plan = relationship("StrategicPlan", back_populates="initiatives")
    assigned_leader = relationship("User", foreign_keys=[assigned_leader_id])
    milestones = relationship(
        "InitiativeMilestone", back_populates="initiative", cascade="all, delete-orphan"
    )
    board_decisions = relationship(
        "BoardDecisionLink", back_populates="initiative", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicInitiative {self.title}>"


class InitiativeMilestone(Base):
    __tablename__ = "initiative_milestones"

    id = Column(Integer, primary_key=True, index=True)
    initiative_id = Column(
        Integer, ForeignKey("strategic_initiatives.id", ondelete="CASCADE"), nullable=False
    )

    # Milestone details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    target_date = Column(DateTime(timezone=True))
    completion_date = Column(DateTime(timezone=True))

    # Dependencies
    dependencies = Column(JSONB, default=list)  # List of milestone IDs

    # Status
    completed = Column(Boolean, default=False)
    completion_notes = Column(Text)

    # Deliverables
    deliverables = Column(JSONB, default=list)

    # Relationships
    initiative = relationship("StrategicInitiative", back_populates="milestones")

    def __repr__(self):
        return f"<InitiativeMilestone {self.title}>"


class BoardDecisionLink(Base):
    __tablename__ = "board_decision_links"

    id = Column(Integer, primary_key=True, index=True)
    initiative_id = Column(
        Integer, ForeignKey("strategic_initiatives.id", ondelete="CASCADE"), nullable=False
    )

    # Board meeting details
    meeting_date = Column(DateTime(timezone=True), nullable=False)
    meeting_reference = Column(String(200))  # e.g., "Board Meeting 2025-03"

    # Decision details
    decision_type = Column(String(50))  # approval, funding, amendment, closure
    decision_summary = Column(Text)
    vote_result = Column(String(100))  # e.g., "Unanimous", "5-2", "Approved"

    # Documentation
    minutes_url = Column(String(500))
    resolution_number = Column(String(100))

    # Relationships
    initiative = relationship("StrategicInitiative", back_populates="board_decisions")

    def __repr__(self):
        return f"<BoardDecisionLink {self.meeting_reference}>"


# ============================================================================
# PHASE 2: KPI Tracking & Performance Dashboards
# ============================================================================


class StrategicKPI(Base):
    __tablename__ = "strategic_kpis"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # KPI definition
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # Financial, Operational, Customer, Learning

    # Measurement
    unit_of_measure = Column(String(50))  # %, count, $, hours, etc.
    target_value = Column(Numeric(12, 2))
    baseline_value = Column(Numeric(12, 2))
    current_value = Column(Numeric(12, 2))

    # Thresholds for color coding
    threshold_red = Column(Numeric(12, 2))  # Below this = red
    threshold_yellow = Column(Numeric(12, 2))  # Below this = yellow
    threshold_green = Column(Numeric(12, 2))  # Above this = green

    # Tracking
    frequency = Column(String(20), default="monthly")  # daily, weekly, monthly, quarterly, annually
    data_source = Column(String(200))
    responsible_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Impact-layer linkage (Phase 1). When the KPI tracks a
    # community-level outcome managed in the impact_measurement layer,
    # link it here. Nullable: most KPIs are still output/program-level.
    outcome_indicator_id = Column(
        Integer,
        ForeignKey("outcome_indicators.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True))

    # Trend analysis
    trend_direction = Column(String(20))  # up, down, stable
    variance_percentage = Column(Numeric(5, 2))

    # Relationships
    plan = relationship("StrategicPlan", back_populates="kpis")
    responsible_person = relationship("User", foreign_keys=[responsible_person_id])
    outcome_indicator = relationship("OutcomeIndicator", foreign_keys=[outcome_indicator_id])
    values = relationship("KPIValue", back_populates="kpi", cascade="all, delete-orphan")
    alerts = relationship("KPIAlert", back_populates="kpi", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StrategicKPI {self.name}>"


class KPIValue(Base):
    __tablename__ = "kpi_values"

    id = Column(Integer, primary_key=True, index=True)
    kpi_id = Column(Integer, ForeignKey("strategic_kpis.id", ondelete="CASCADE"), nullable=False)

    # Value and timestamp
    value = Column(Numeric(12, 2), nullable=False)
    recorded_date = Column(DateTime(timezone=True), nullable=False)

    # Context
    notes = Column(Text)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Data quality
    is_estimated = Column(Boolean, default=False)
    data_quality_score = Column(Integer)  # 1-10

    # Relationships
    kpi = relationship("StrategicKPI", back_populates="values")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    def __repr__(self):
        return f"<KPIValue {self.kpi_id}: {self.value}>"


class KPIDashboard(Base):
    __tablename__ = "kpi_dashboards"

    id = Column(Integer, primary_key=True, index=True)

    # Dashboard details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    audience = Column(String(100))  # Board, Staff, Public, Executive

    # Configuration
    kpi_ids = Column(JSONB, default=list)  # List of KPI IDs to display
    layout = Column(JSONB, default=dict)  # Dashboard layout configuration
    refresh_interval = Column(Integer, default=3600)  # Seconds

    # Access control
    is_public = Column(Boolean, default=False)
    allowed_roles = Column(JSONB, default=list)

    # Owner
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<KPIDashboard {self.name}>"


class KPIAlert(Base):
    __tablename__ = "kpi_alerts"

    id = Column(Integer, primary_key=True, index=True)
    kpi_id = Column(Integer, ForeignKey("strategic_kpis.id", ondelete="CASCADE"), nullable=False)

    # Alert details
    severity = Column(String(20), nullable=False)  # info, warning, critical
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False)

    # Context
    threshold_violated = Column(String(50))  # red, yellow, target_missed
    actual_value = Column(Numeric(12, 2))
    expected_value = Column(Numeric(12, 2))

    # Status
    acknowledged = Column(Boolean, default=False)
    acknowledged_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)

    # Relationships
    kpi = relationship("StrategicKPI", back_populates="alerts")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])

    def __repr__(self):
        return f"<KPIAlert {self.severity}: {self.message}>"


# ============================================================================
# PHASE 3: Budget Tracking & Financial Planning
# ============================================================================


class StrategicBudget(Base):
    __tablename__ = "strategic_budgets"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # Budget details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    fiscal_year = Column(Integer, nullable=False)

    # Financial summary
    total_budget = Column(Numeric(12, 2), nullable=False)
    allocated_amount = Column(Numeric(12, 2), default=0)
    spent_amount = Column(Numeric(12, 2), default=0)
    committed_amount = Column(Numeric(12, 2), default=0)
    available_amount = Column(Numeric(12, 2), default=0)

    # Status
    status = Column(String(20), default="draft")
    approved_date = Column(DateTime(timezone=True))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Ownership
    budget_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    plan = relationship("StrategicPlan", back_populates="budgets")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    budget_owner = relationship("User", foreign_keys=[budget_owner_id])
    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")
    allocations = relationship(
        "BudgetAllocation", back_populates="budget", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "BudgetTransaction", back_populates="budget", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicBudget {self.name} FY{self.fiscal_year}>"


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(
        Integer, ForeignKey("strategic_budgets.id", ondelete="CASCADE"), nullable=False
    )

    # Item details
    category = Column(String(100), nullable=False)  # Personnel, Technology, Facilities, etc.
    subcategory = Column(String(100))
    description = Column(Text)

    # Amounts
    budgeted_amount = Column(Numeric(12, 2), nullable=False)
    allocated_amount = Column(Numeric(12, 2), default=0)
    spent_amount = Column(Numeric(12, 2), default=0)
    remaining_amount = Column(Numeric(12, 2), default=0)

    # Tracking
    account_code = Column(String(50))
    department = Column(String(100))
    initiative_id = Column(Integer, ForeignKey("strategic_initiatives.id", ondelete="SET NULL"))

    # Notes
    justification = Column(Text)

    # Relationships
    budget = relationship("StrategicBudget", back_populates="items")
    initiative = relationship("StrategicInitiative")

    def __repr__(self):
        return f"<BudgetItem {self.category}: ${self.budgeted_amount}>"


class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(
        Integer, ForeignKey("strategic_budgets.id", ondelete="CASCADE"), nullable=False
    )

    # Allocation details
    description = Column(String(300), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    allocation_date = Column(DateTime(timezone=True), nullable=False)

    # Purpose
    purpose = Column(Text)
    initiative_id = Column(Integer, ForeignKey("strategic_initiatives.id", ondelete="SET NULL"))
    department = Column(String(100))

    # Authorization
    authorized_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    budget = relationship("StrategicBudget", back_populates="allocations")
    initiative = relationship("StrategicInitiative")
    authorized_by = relationship("User", foreign_keys=[authorized_by_id])

    def __repr__(self):
        return f"<BudgetAllocation ${self.amount}>"


class BudgetTransaction(Base):
    __tablename__ = "budget_transactions"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(
        Integer, ForeignKey("strategic_budgets.id", ondelete="CASCADE"), nullable=False
    )

    # Transaction details
    transaction_type = Column(String(50), nullable=False)
    description = Column(String(300), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)

    # Categorization
    category = Column(String(100))
    initiative_id = Column(Integer, ForeignKey("strategic_initiatives.id", ondelete="SET NULL"))

    # Documentation
    invoice_number = Column(String(100))
    vendor = Column(String(200))
    receipt_url = Column(String(500))

    # Authorization
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    budget = relationship("StrategicBudget", back_populates="transactions")
    initiative = relationship("StrategicInitiative")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    def __repr__(self):
        return f"<BudgetTransaction {self.transaction_type}: ${self.amount}>"


# ============================================================================
# PHASE 4: Risk Management
# ============================================================================


class StrategicRisk(Base):
    __tablename__ = "strategic_risks"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # Risk identification
    title = Column(String(300), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # Financial, Operational, Strategic, Compliance, Reputational

    # Risk assessment
    likelihood = Column(String(20))  # low, medium, high
    impact = Column(String(20))  # low, medium, high
    risk_level = Column(String(20))  # Calculated: low, medium, high, critical

    # Risk score (likelihood × impact)
    risk_score = Column(Integer)  # 1-25

    # Context
    triggers = Column(JSONB, default=list)  # What could trigger this risk
    indicators = Column(JSONB, default=list)  # Early warning signs

    # Status
    status = Column(String(20), default="identified")
    identified_date = Column(DateTime(timezone=True))

    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Linked entities
    initiative_id = Column(Integer, ForeignKey("strategic_initiatives.id", ondelete="SET NULL"))

    # Relationships
    plan = relationship("StrategicPlan", back_populates="risks")
    owner = relationship("User", foreign_keys=[owner_id])
    initiative = relationship("StrategicInitiative")
    assessments = relationship(
        "RiskAssessment", back_populates="risk", cascade="all, delete-orphan"
    )
    mitigation_strategies = relationship(
        "RiskMitigationStrategy", back_populates="risk", cascade="all, delete-orphan"
    )
    reviews = relationship("RiskReview", back_populates="risk", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StrategicRisk {self.title}>"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    risk_id = Column(Integer, ForeignKey("strategic_risks.id", ondelete="CASCADE"), nullable=False)

    # Assessment details
    assessment_date = Column(DateTime(timezone=True), nullable=False)
    assessed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Updated ratings
    likelihood = Column(String(20))
    impact = Column(String(20))
    risk_score = Column(Integer)

    # Analysis
    assessment_notes = Column(Text)
    changes_since_last = Column(Text)

    # Recommendations
    recommended_actions = Column(JSONB, default=list)

    # Relationships
    risk = relationship("StrategicRisk", back_populates="assessments")
    assessed_by = relationship("User", foreign_keys=[assessed_by_id])

    def __repr__(self):
        return f"<RiskAssessment for Risk {self.risk_id}>"


class RiskMitigationStrategy(Base):
    __tablename__ = "risk_mitigation_strategies"

    id = Column(Integer, primary_key=True, index=True)
    risk_id = Column(Integer, ForeignKey("strategic_risks.id", ondelete="CASCADE"), nullable=False)

    # Strategy details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50))  # avoid, reduce, transfer, accept

    # Implementation
    action_steps = Column(JSONB, default=list)
    responsible_person_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    target_completion_date = Column(DateTime(timezone=True))

    # Status
    status = Column(String(20), default="planned")  # planned, in_progress, completed, cancelled
    implementation_date = Column(DateTime(timezone=True))
    completion_date = Column(DateTime(timezone=True))

    # Effectiveness
    effectiveness_rating = Column(Integer)  # 1-10
    cost_estimate = Column(Numeric(12, 2))
    actual_cost = Column(Numeric(12, 2))

    # Relationships
    risk = relationship("StrategicRisk", back_populates="mitigation_strategies")
    responsible_person = relationship("User", foreign_keys=[responsible_person_id])

    def __repr__(self):
        return f"<RiskMitigationStrategy {self.title}>"


class RiskReview(Base):
    __tablename__ = "risk_reviews"

    id = Column(Integer, primary_key=True, index=True)
    risk_id = Column(Integer, ForeignKey("strategic_risks.id", ondelete="CASCADE"), nullable=False)

    # Review details
    review_date = Column(DateTime(timezone=True), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Status update
    current_status = Column(String(20))
    risk_level_change = Column(String(50))  # increased, decreased, unchanged

    # Review findings
    review_notes = Column(Text)
    mitigation_effectiveness = Column(Text)

    # Recommendations
    recommendations = Column(JSONB, default=list)
    next_review_date = Column(DateTime(timezone=True))

    # Relationships
    risk = relationship("StrategicRisk", back_populates="reviews")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<RiskReview for Risk {self.risk_id}>"


# ============================================================================
# PHASE 5: Executive Dashboards & Reporting
# ============================================================================


class ExecutiveDashboard(Base):
    __tablename__ = "executive_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # Dashboard details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    dashboard_type = Column(String(50))  # overview, financial, operations, risks

    # Configuration
    widget_ids = Column(JSONB, default=list)  # List of widget IDs
    layout_config = Column(JSONB, default=dict)  # Layout settings

    # Access control
    audience = Column(String(100))  # Board, Executive, Department Heads
    is_default = Column(Boolean, default=False)

    # Refresh settings
    auto_refresh = Column(Boolean, default=True)
    refresh_interval_minutes = Column(Integer, default=15)

    # Owner
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    last_modified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    plan = relationship("StrategicPlan", back_populates="dashboards")
    created_by = relationship("User", foreign_keys=[created_by_id])
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])
    widgets = relationship(
        "DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ExecutiveDashboard {self.name}>"


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(
        Integer, ForeignKey("executive_dashboards.id", ondelete="CASCADE"), nullable=False
    )

    # Widget details
    title = Column(String(200), nullable=False)
    widget_type = Column(String(50), nullable=False)  # chart, kpi, table, metric, alert

    # Data source
    data_source_type = Column(String(50))  # kpi, initiative, budget, risk
    data_source_ids = Column(JSONB, default=list)  # IDs of related entities

    # Configuration
    config = Column(JSONB, default=dict)  # Widget-specific configuration

    # Position and size
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)

    # Display options
    display_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)

    # Relationships
    dashboard = relationship("ExecutiveDashboard", back_populates="widgets")

    def __repr__(self):
        return f"<DashboardWidget {self.title}>"


class ExecutiveReport(Base):
    __tablename__ = "executive_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report details
    title = Column(String(300), nullable=False)
    report_type = Column(String(50), nullable=False)  # monthly, quarterly, annual, ad_hoc
    description = Column(Text)

    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Content
    executive_summary = Column(Text)
    key_findings = Column(JSONB, default=list)
    recommendations = Column(JSONB, default=list)

    # Sections
    report_sections = Column(JSONB, default=list)  # Structured report content

    # Data snapshots
    kpi_snapshot = Column(JSONB, default=dict)
    initiative_snapshot = Column(JSONB, default=dict)
    budget_snapshot = Column(JSONB, default=dict)
    risk_snapshot = Column(JSONB, default=dict)

    # Status
    status = Column(String(20), default="draft")  # draft, published, archived
    published_date = Column(DateTime(timezone=True))

    # Distribution
    distributed_to = Column(JSONB, default=list)  # List of user IDs or roles

    # File attachments
    pdf_url = Column(String(500))
    supporting_docs = Column(JSONB, default=list)

    # Author
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    schedules = relationship(
        "ReportSchedule", back_populates="report_template", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ExecutiveReport {self.title}>"


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)
    report_template_id = Column(
        Integer, ForeignKey("executive_reports.id", ondelete="CASCADE"), nullable=False
    )

    # Schedule details
    name = Column(String(200), nullable=False)
    frequency = Column(String(20), nullable=False)  # weekly, monthly, quarterly, annually

    # Timing
    day_of_week = Column(Integer)  # For weekly (0=Monday, 6=Sunday)
    day_of_month = Column(Integer)  # For monthly (1-31)
    month_of_year = Column(Integer)  # For annually (1-12)
    time_of_day = Column(String(5))  # HH:MM format

    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True))
    next_run = Column(DateTime(timezone=True))

    # Distribution
    recipients = Column(JSONB, default=list)  # List of email addresses or user IDs
    email_subject = Column(String(300))
    email_body_template = Column(Text)

    # Relationships
    report_template = relationship("ExecutiveReport", back_populates="schedules")

    def __repr__(self):
        return f"<ReportSchedule {self.name}>"


# ============================================================================
# Existing models (keeping for compatibility)
# ============================================================================


class StrategicGoal(Base):
    __tablename__ = "strategic_goals"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)

    # Goal details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "Community Engagement", "Collections", "Technology"

    # Timeline
    target_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))

    # Progress - using String to avoid enum complexity
    progress = Column(Integer, default=0)  # 0-100 percentage
    status = Column(String(20), default="not_started", nullable=False)

    # Key metrics (JSON array)
    # Format: [{"name": "Circulation increase", "current": 5000, "target": 7500, "unit": "items/month"}]
    metrics = Column(JSONB, default=list)

    # Progress updates (JSON array for history)
    # Format: [{"date": "2025-01-15", "progress": 25, "note": "Completed phase 1"}]
    updates = Column(JSONB, default=list)

    # Assignment
    owner = Column(String(200))  # Person responsible
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Priority (1=highest)
    priority = Column(Integer, default=3)

    # === NEW: Public and staff fields ===
    public_description = Column(Text)  # Simplified description for public view
    department = Column(
        String(100)
    )  # Which staff department owns this (e.g., "Youth Services", "Technical Services")
    staff_can_update = Column(Boolean, default=False)  # Allow staff to contribute progress updates
    is_public = Column(Boolean, default=True)  # Show on public page

    # Sub-goals hierarchy
    parent_goal_id = Column(
        Integer, ForeignKey("strategic_goals.id", ondelete="SET NULL"), nullable=True
    )
    display_order = Column(Integer, default=0)  # Order within parent/plan

    # Approval workflow
    approval_status = Column(String(20), default="approved", nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    plan = relationship("StrategicPlan", back_populates="goals")
    owner_user = relationship("User", foreign_keys=[owner_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    milestones = relationship("StrategicMilestone", back_populates="goal")
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent_goal = relationship(
        "StrategicGoal", remote_side="StrategicGoal.id", back_populates="sub_goals", lazy="select"
    )
    sub_goals = relationship("StrategicGoal", back_populates="parent_goal", lazy="select")
    comments = relationship("StrategicComment", back_populates="goal", cascade="all, delete-orphan")
    attachments = relationship(
        "StrategicAttachment", back_populates="goal", cascade="all, delete-orphan"
    )
    strategic_metrics = relationship(
        "StrategicMetric", back_populates="goal", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicGoal {self.title}>"


class StrategicMilestone(Base):
    __tablename__ = "strategic_milestones"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("strategic_plans.id", ondelete="CASCADE"), nullable=False)
    goal_id = Column(Integer, ForeignKey("strategic_goals.id", ondelete="SET NULL"), nullable=True)

    # Milestone details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    achieved_date = Column(DateTime(timezone=True))

    # Public celebration content
    celebration_text = Column(Text)  # Public-facing celebration message (e.g., "We did it!")
    impact_story = Column(Text)  # Community impact narrative
    photo_url = Column(String(500))  # Optional celebration image

    # Display settings
    is_public = Column(Boolean, default=True)  # Show on public page
    is_featured = Column(Boolean, default=False)  # Highlight on homepage
    display_order = Column(Integer, default=0)  # Order in timeline

    # Type of milestone
    milestone_type = Column(
        String(50), default="achievement"
    )  # achievement, anniversary, event, launch

    # Approval workflow
    approval_status = Column(String(20), default="approved", nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    plan = relationship("StrategicPlan", back_populates="milestones")
    goal = relationship("StrategicGoal", back_populates="milestones")
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    attachments = relationship(
        "StrategicAttachment", back_populates="milestone", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicMilestone {self.title}>"


class StrategicComment(Base, TimestampMixin):
    __tablename__ = "strategic_comments"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("strategic_goals.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(
        Integer, ForeignKey("strategic_comments.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    goal = relationship("StrategicGoal", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent = relationship(
        "StrategicComment",
        remote_side="StrategicComment.id",
        back_populates="replies",
        lazy="select",
    )
    replies = relationship(
        "StrategicComment", back_populates="parent", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self):
        return f"<StrategicComment {self.id} on goal {self.goal_id}>"


class StrategicNotification(Base):
    __tablename__ = "strategic_notifications"
    __table_args__ = (
        Index("idx_user_unread", "user_id", "is_read"),  # Fast unread count queries
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification content
    notification_type = Column(
        String(50), nullable=False
    )  # goal_risk, deadline, milestone, progress
    title = Column(String(300), nullable=False)
    message = Column(Text)
    link = Column(String(500))  # URL to related item

    # Related entities
    related_goal_id = Column(
        Integer, ForeignKey("strategic_goals.id", ondelete="SET NULL"), nullable=True
    )
    related_milestone_id = Column(
        Integer, ForeignKey("strategic_milestones.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    related_goal = relationship("StrategicGoal", foreign_keys=[related_goal_id])
    related_milestone = relationship("StrategicMilestone", foreign_keys=[related_milestone_id])

    def __repr__(self):
        return f"<StrategicNotification {self.id} for user {self.user_id}>"


class StrategicAttachment(Base):
    __tablename__ = "strategic_attachments"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("strategic_goals.id", ondelete="CASCADE"), nullable=True)
    milestone_id = Column(
        Integer, ForeignKey("strategic_milestones.id", ondelete="CASCADE"), nullable=True
    )

    # File details
    filename = Column(String(300), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(100))  # MIME type
    file_size = Column(Integer)  # Size in bytes

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Audit
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    goal = relationship("StrategicGoal", back_populates="attachments")
    milestone = relationship("StrategicMilestone", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<StrategicAttachment {self.filename}>"


class StrategicMetric(Base):
    __tablename__ = "strategic_metrics"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("strategic_goals.id", ondelete="CASCADE"), nullable=False)

    # Metric definition
    name = Column(String(200), nullable=False)
    description = Column(Text)
    unit = Column(String(50))  # e.g., "items/month", "%", "count"

    # Values
    target_value = Column(Float)
    current_value = Column(Float)
    baseline_value = Column(Float)

    # Data tracking
    data_source = Column(String(200))  # Where the data comes from
    update_frequency = Column(String(50))  # daily, weekly, monthly, quarterly
    last_updated = Column(DateTime(timezone=True))

    # Relationships
    goal = relationship("StrategicGoal", back_populates="strategic_metrics")
    history = relationship(
        "StrategicMetricHistory", back_populates="metric", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StrategicMetric {self.name}>"


class StrategicMetricHistory(Base):
    __tablename__ = "strategic_metric_history"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(
        Integer, ForeignKey("strategic_metrics.id", ondelete="CASCADE"), nullable=False
    )

    # Recorded value
    value = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    metric = relationship("StrategicMetric", back_populates="history")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    def __repr__(self):
        return f"<StrategicMetricHistory {self.metric_id} at {self.recorded_at}>"


class StrategicGoalTemplate(Base):
    __tablename__ = "strategic_goal_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "Community Engagement", "Collections"

    # Default configuration
    default_metrics = Column(JSONB, default=list)  # Pre-defined metrics structure
    suggested_timeline_months = Column(Integer)  # Suggested duration

    # Template type
    is_system_template = Column(Boolean, default=False)  # Built-in vs user-created

    def __repr__(self):
        return f"<StrategicGoalTemplate {self.name}>"


class StrategicAuditLog(Base):
    __tablename__ = "strategic_audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Entity tracking
    entity_type = Column(String(100), nullable=False)  # e.g., "goal", "milestone", "plan"
    entity_id = Column(Integer, nullable=False)

    # Change details
    action = Column(String(50), nullable=False)  # create, update, delete, approve, etc.
    changes = Column(JSONB)  # Before/after values

    # User tracking
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45))  # IPv4 or IPv6

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<StrategicAuditLog {self.action} on {self.entity_type} {self.entity_id}>"
